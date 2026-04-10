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
    impedances: list[dict[str, Any]] = field(default_factory=list)
    far_field: list[dict[str, Any]] = field(default_factory=list)
    directivity: dict[str, Any] = field(default_factory=dict)
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
        if self.impedances:
            result["impedances"] = self.impedances
        if self.far_field:
            result["far_field"] = self.far_field
        if self.directivity:
            result["directivity"] = self.directivity
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

    # Compute port impedances (Z = V / I) for driven problems
    if problem_type == "Driven" and results.port_voltages and results.port_currents:
        results.impedances = _compute_impedances(
            results.port_voltages, results.port_currents
        )

    # Parse far-field data
    farfield_csv = output_dir / "farfield.csv"
    if farfield_csv.is_file():
        results.far_field = _read_csv(farfield_csv)
    # Also check subdirectory
    for ff_candidate in output_dir.rglob("farfield*.csv"):
        if ff_candidate != farfield_csv:
            results.far_field.extend(_read_csv(ff_candidate))

    # Compute directivity from far-field or probe data
    if results.far_field:
        results.directivity = _compute_directivity(results.far_field)

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


def _compute_impedances(
    voltages: list[dict[str, str]], currents: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """Compute port impedances Z = V / I from port voltage/current data.

    Handles both real-valued and complex (Re/Im pair) column conventions.
    Returns one entry per frequency step with Z per port.
    """
    import math

    impedances: list[dict[str, Any]] = []
    for v_row, i_row in zip(voltages, currents):
        entry: dict[str, Any] = {}

        # Detect frequency column
        for key, val in v_row.items():
            k = key.strip()
            if "freq" in k.lower() or k.lower() == "f":
                entry["frequency_hz"] = _to_float(val)
                break

        # Collect voltage and current columns per port
        v_cols: dict[str, complex] = {}
        i_cols: dict[str, complex] = {}

        _collect_complex_columns(v_row, v_cols)
        _collect_complex_columns(i_row, i_cols)

        # Pair V and I columns by port number.
        # Column keys may be "V1"/"I1" or just "1".
        # Normalise to a common port label by stripping leading V/I prefix.
        v_by_port: dict[str, tuple[str, complex]] = {}
        for raw_key, val in v_cols.items():
            port = _strip_vi_prefix(raw_key)
            v_by_port[port] = (raw_key, val)

        i_by_port: dict[str, tuple[str, complex]] = {}
        for raw_key, val in i_cols.items():
            port = _strip_vi_prefix(raw_key)
            i_by_port[port] = (raw_key, val)

        # Compute Z for each port present in both V and I
        for port in v_by_port:
            v_key, v_val = v_by_port[port]
            if port in i_by_port:
                i_key, i_val = i_by_port[port]
                if abs(i_val) > 1e-30:
                    z = v_val / i_val
                    label = f"Z_{v_key}"
                    entry[f"{label}_re"] = z.real
                    entry[f"{label}_im"] = z.imag
                    entry[f"{label}_mag"] = abs(z)
                    entry[f"{label}_phase_deg"] = math.degrees(
                        math.atan2(z.imag, z.real)
                    )

        impedances.append(entry)
    return impedances


def _strip_vi_prefix(key: str) -> str:
    """Strip a leading V or I (case-insensitive) from a port key.

    'V1' → '1', 'I2' → '2', '1' → '1'.
    """
    if len(key) > 1 and key[0] in ("V", "v", "I", "i") and key[1:].isdigit():
        return key[1:]
    return key


def _collect_complex_columns(
    row: dict[str, str], out: dict[str, complex]
) -> None:
    """Extract complex port values from a CSV row.

    Recognises column naming patterns:
      Re_V1 / Im_V1  or  V1_re / V1_im  or  plain V1 (real-only).
    Populates *out* keyed by the port identifier (e.g. "V1", "I2").
    """
    re_vals: dict[str, float] = {}
    im_vals: dict[str, float] = {}
    plain: dict[str, float] = {}

    for key, val in row.items():
        k = key.strip()
        kl = k.lower()
        if "freq" in kl or kl == "f":
            continue

        if kl.startswith("re_"):
            re_vals[k[3:]] = _to_float(val)
        elif kl.startswith("im_"):
            im_vals[k[3:]] = _to_float(val)
        elif kl.endswith("_re"):
            re_vals[k[:-3]] = _to_float(val)
        elif kl.endswith("_im"):
            im_vals[k[:-3]] = _to_float(val)
        else:
            plain[k] = _to_float(val)

    # Merge real/imaginary pairs
    all_ids = set(re_vals) | set(im_vals) | set(plain)
    for pid in all_ids:
        r = re_vals.get(pid, plain.get(pid, 0.0))
        i = im_vals.get(pid, 0.0)
        out[pid] = complex(r, i)


def _compute_directivity(far_field: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute directivity metrics from far-field CSV data.

    Expects rows with columns for theta, phi, and power/gain values.
    Returns boresight directivity, max directivity, and beam solid angle.
    """
    import math

    if not far_field:
        return {}

    # Try to identify columns
    sample = far_field[0]
    theta_key = _find_key(sample, ("theta",))
    phi_key = _find_key(sample, ("phi",))
    gain_key = _find_key(sample, ("gain", "directivity", "power", "e_total", "etotal"))

    if gain_key is None:
        return {"error": "No gain/directivity column found in far-field data"}

    max_gain = -1e30
    max_theta = 0.0
    max_phi = 0.0
    boresight_gain = None
    total_power = 0.0
    num_points = 0

    for row in far_field:
        gain = _to_float(str(row.get(gain_key, 0)))
        theta = _to_float(str(row.get(theta_key, 0))) if theta_key else 0.0
        phi = _to_float(str(row.get(phi_key, 0))) if phi_key else 0.0

        if gain > max_gain:
            max_gain = gain
            max_theta = theta
            max_phi = phi

        # Check boresight (theta ≈ 0)
        if theta_key and abs(theta) < 1.0:
            boresight_gain = gain

        total_power += gain
        num_points += 1

    avg_power = total_power / max(num_points, 1)
    directivity_ratio = max_gain / avg_power if avg_power > 1e-30 else 0.0
    directivity_dbi = 10 * math.log10(max(directivity_ratio, 1e-30))

    result: dict[str, Any] = {
        "max_directivity_dbi": round(directivity_dbi, 2),
        "max_gain_direction": {"theta": max_theta, "phi": max_phi},
        "num_far_field_points": num_points,
    }

    if boresight_gain is not None:
        boresight_ratio = boresight_gain / avg_power if avg_power > 1e-30 else 0.0
        boresight_dbi = 10 * math.log10(max(boresight_ratio, 1e-30))
        result["boresight_directivity_dbi"] = round(boresight_dbi, 2)

    return result


def _find_key(
    sample: dict[str, Any], candidates: tuple[str, ...]
) -> str | None:
    """Find the first key in *sample* whose lowercase form contains a candidate."""
    for key in sample:
        kl = key.strip().lower()
        for c in candidates:
            if c in kl:
                return key
    return None


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
