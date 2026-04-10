"""Parse Palace simulation output files into structured results."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SimulationResults:
    """Parsed simulation results."""

    problem_type: str = ""
    eigenfrequencies: list[dict[str, Any]] = field(default_factory=list)
    s_parameters: list[dict[str, Any]] = field(default_factory=list)
    capacitance_matrix: list[list[float]] | None = None
    inductance_matrix: list[list[float]] | None = None
    domain_energies: list[dict[str, Any]] = field(default_factory=list)
    port_voltages: list[dict[str, Any]] = field(default_factory=list)
    port_currents: list[dict[str, Any]] = field(default_factory=list)
    surface_flux: list[dict[str, Any]] = field(default_factory=list)
    surface_quality: list[dict[str, Any]] = field(default_factory=list)
    probe_e_field: list[dict[str, Any]] = field(default_factory=list)
    probe_b_field: list[dict[str, Any]] = field(default_factory=list)
    raw_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"problem_type": self.problem_type}
        if self.eigenfrequencies:
            result["eigenfrequencies"] = self.eigenfrequencies
        if self.s_parameters:
            result["s_parameters"] = self.s_parameters
        if self.capacitance_matrix is not None:
            result["capacitance_matrix"] = self.capacitance_matrix
        if self.inductance_matrix is not None:
            result["inductance_matrix"] = self.inductance_matrix
        if self.domain_energies:
            result["domain_energies"] = self.domain_energies
        if self.port_voltages:
            result["port_voltages"] = self.port_voltages
        if self.port_currents:
            result["port_currents"] = self.port_currents
        if self.surface_flux:
            result["surface_flux"] = self.surface_flux
        if self.surface_quality:
            result["surface_quality"] = self.surface_quality
        if self.probe_e_field:
            result["probe_e_field"] = self.probe_e_field
        if self.probe_b_field:
            result["probe_b_field"] = self.probe_b_field
        if self.raw_files:
            result["raw_files"] = self.raw_files
        if self.errors:
            result["errors"] = self.errors
        return result


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a Palace CSV output file, skipping comment lines."""
    rows: list[dict[str, str]] = []
    if not path.is_file():
        return rows
    with open(path) as f:
        # Palace CSVs may have comment/header lines starting with #
        lines = [l for l in f if not l.startswith("#") and l.strip()]
    if not lines:
        return rows
    # Attempt to detect header
    reader = csv.DictReader(lines)
    for row in reader:
        rows.append(dict(row))
    return rows


def _to_float(val: str) -> float:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return 0.0


def parse_results(output_dir: Path, problem_type: str = "") -> SimulationResults:
    """Parse all Palace output CSV files in the given directory."""
    results = SimulationResults(problem_type=problem_type)

    # Enumerate raw output files
    for f in output_dir.rglob("*"):
        if f.is_file():
            results.raw_files.append(str(f.relative_to(output_dir)))

    # Domain energies
    domain_e = output_dir / "domain-E.csv"
    if domain_e.is_file():
        results.domain_energies = _read_csv(domain_e)

    # Port voltages and currents
    port_v = output_dir / "port-V.csv"
    if port_v.is_file():
        results.port_voltages = _read_csv(port_v)

    port_i = output_dir / "port-I.csv"
    if port_i.is_file():
        results.port_currents = _read_csv(port_i)

    # Surface flux
    surface_f = output_dir / "surface-F.csv"
    if surface_f.is_file():
        results.surface_flux = _read_csv(surface_f)

    # Surface quality factors
    surface_q = output_dir / "surface-Q.csv"
    if surface_q.is_file():
        results.surface_quality = _read_csv(surface_q)

    # Probe fields
    probe_e = output_dir / "probe-E.csv"
    if probe_e.is_file():
        results.probe_e_field = _read_csv(probe_e)

    probe_b = output_dir / "probe-B.csv"
    if probe_b.is_file():
        results.probe_b_field = _read_csv(probe_b)

    # Parse eigenfrequencies from domain-E.csv for eigenmode problems
    if problem_type == "Eigenmode" and results.domain_energies:
        for row in results.domain_energies:
            entry: dict[str, Any] = {}
            for key, val in row.items():
                k = key.strip()
                if "freq" in k.lower() or "f" == k.lower():
                    entry["frequency_hz"] = _to_float(val)
                elif "q" in k.lower():
                    entry["quality_factor"] = _to_float(val)
                elif "epr" in k.lower():
                    entry["epr"] = _to_float(val)
                elif k:
                    entry[k] = _to_float(val)
            if entry:
                results.eigenfrequencies.append(entry)

    # Compute S-parameters from port data for driven problems
    if problem_type == "Driven" and results.port_voltages and results.port_currents:
        results.s_parameters = _compute_s_parameters(
            results.port_voltages, results.port_currents
        )

    # Extract capacitance/inductance matrices for static problems
    if problem_type == "Electrostatic" and results.surface_flux:
        results.capacitance_matrix = _extract_matrix(results.surface_flux, "capacitance")
    if problem_type == "Magnetostatic" and results.surface_flux:
        results.inductance_matrix = _extract_matrix(results.surface_flux, "inductance")

    return results


def _compute_s_parameters(
    voltages: list[dict[str, str]], currents: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """Compute S-parameters from port voltage/current data."""
    s_params: list[dict[str, Any]] = []
    # Palace outputs complex-valued port voltages/currents per frequency step
    for v_row, i_row in zip(voltages, currents):
        entry: dict[str, Any] = {}
        for key, val in v_row.items():
            k = key.strip()
            if "freq" in k.lower() or "f" == k.lower():
                entry["frequency_hz"] = _to_float(val)
            else:
                entry[f"V_{k}"] = _to_float(val)
        for key, val in i_row.items():
            k = key.strip()
            if "freq" not in k.lower() and k.lower() != "f":
                entry[f"I_{k}"] = _to_float(val)
        s_params.append(entry)
    return s_params


def _extract_matrix(
    flux_data: list[dict[str, str]], matrix_type: str
) -> list[list[float]]:
    """Extract a matrix from surface flux data."""
    # Simplified: each row of flux data corresponds to a terminal excitation
    matrix: list[list[float]] = []
    for row in flux_data:
        values = [_to_float(v) for k, v in row.items() if k.strip().lower() != "index"]
        if values:
            matrix.append(values)
    return matrix


def parse_palace_error(stderr: str) -> dict[str, str]:
    """Parse Palace stderr output to produce actionable diagnostics."""
    diagnostics: dict[str, str] = {
        "category": "unknown",
        "message": stderr[:500] if stderr else "No error output captured",
        "suggestion": "",
    }

    lower = stderr.lower()

    if "diverge" in lower or "ksp" in lower and "not converged" in lower:
        diagnostics["category"] = "solver_divergence"
        diagnostics["suggestion"] = (
            "Try increasing Solver.Linear.MaxIts, decreasing Solver.Linear.Tol, "
            "or refining the mesh. Check that boundary conditions are well-posed."
        )
    elif "mesh" in lower and ("not found" in lower or "error" in lower):
        diagnostics["category"] = "mesh_error"
        diagnostics["suggestion"] = (
            "Verify that Model.Mesh points to an existing mesh file in "
            "a supported format (Gmsh .msh, Exodus .exo, MFEM mesh)."
        )
    elif "json" in lower or "parse" in lower or "config" in lower:
        diagnostics["category"] = "config_error"
        diagnostics["suggestion"] = (
            "Check the Palace JSON config for syntax errors or missing "
            "required fields. Run the validate_config tool first."
        )
    elif "attribute" in lower or "boundary" in lower:
        diagnostics["category"] = "boundary_error"
        diagnostics["suggestion"] = (
            "A boundary attribute in the config does not match any boundary "
            "in the mesh. Verify mesh boundary IDs match config attributes."
        )
    elif "memory" in lower or "alloc" in lower:
        diagnostics["category"] = "memory_error"
        diagnostics["suggestion"] = (
            "The simulation ran out of memory. Try reducing mesh density, "
            "lowering Solver.Order, or increasing available memory."
        )

    return diagnostics
