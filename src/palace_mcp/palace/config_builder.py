"""Build and manipulate Palace JSON configuration files."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def build_config(
    problem_type: str,
    mesh_file: str,
    materials: list[dict[str, Any]],
    boundaries: dict[str, Any] | None = None,
    solver: dict[str, Any] | None = None,
    output_dir: str = "results",
    length_unit: float = 1e-3,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Palace JSON configuration dictionary.

    Args:
        problem_type: One of Eigenmode, Driven, Transient, Electrostatic, Magnetostatic.
        mesh_file: Path to the mesh file (relative to config location).
        materials: List of material dicts matching Palace Domains.Materials schema.
        boundaries: Boundaries config section.
        solver: Solver config section overrides.
        output_dir: Directory for Palace output.
        length_unit: Model length unit in meters (default 1mm).
        extra: Additional top-level config keys.
    """
    valid_types = {
        "Eigenmode", "Driven", "Transient", "Electrostatic", "Magnetostatic",
    }
    if problem_type not in valid_types:
        raise ValueError(
            f"Invalid problem type '{problem_type}'. Must be one of {valid_types}"
        )

    config: dict[str, Any] = {
        "Problem": {
            "Type": problem_type,
            "Output": output_dir,
            "Verbose": 2,
        },
        "Model": {
            "Mesh": mesh_file,
            "L0": length_unit,
        },
        "Domains": {
            "Materials": materials,
        },
        "Boundaries": boundaries or {},
        "Solver": _default_solver(problem_type),
    }

    if solver:
        _deep_merge(config["Solver"], solver)

    if extra:
        _deep_merge(config, extra)

    return config


def _default_solver(problem_type: str) -> dict[str, Any]:
    """Return sensible default solver settings per problem type."""
    base: dict[str, Any] = {
        "Order": 2,
        "Device": "CPU",
        "Linear": {
            "Type": "Default",
            "KSPType": "GMRES",
            "Tol": 1e-8,
            "MaxIts": 500,
        },
    }

    if problem_type == "Eigenmode":
        base["Eigenmode"] = {
            "N": 5,
            "Tol": 1e-6,
            "MaxIts": 100,
            "Type": "SLEPc",
        }
    elif problem_type == "Driven":
        base["Driven"] = {
            "MinFreq": 1e9,
            "MaxFreq": 10e9,
            "FreqStep": 100e6,
            "AdaptiveTol": 1e-3,
        }
    elif problem_type == "Transient":
        base["Transient"] = {
            "Type": "Default",
            "MaxTime": 1e-9,
            "TimeStep": 1e-12,
        }
    elif problem_type in ("Electrostatic", "Magnetostatic"):
        pass  # No extra solver section needed

    return base


def write_config(config: dict[str, Any], path: Path) -> Path:
    """Write a Palace config dict to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    return path


def load_config(path: Path) -> dict[str, Any]:
    """Load a Palace config JSON file."""
    with open(path) as f:
        return json.load(f)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, modifying base in-place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def build_phased_array_ports(
    num_ports: int,
    port_attributes: list[int],
    amplitudes: list[float] | None = None,
    phases_deg: list[float] | None = None,
    impedance: float = 50.0,
    direction: str = "+Z",
) -> dict[str, Any]:
    """Build a Boundaries section for a phased-array lumped-port excitation.

    Args:
        num_ports: Number of ports (dipoles).
        port_attributes: Mesh attribute IDs for each port's feed surface.
        amplitudes: Excitation amplitude per port (volts). Defaults to 1 V each.
        phases_deg: Excitation phase per port in degrees. Defaults to 0° each.
        impedance: Reference impedance in ohms (applied to every port).
        direction: Lumped-port orientation (e.g. "+Z", "-Z", "+X").

    Returns:
        A ``Boundaries`` dict ready to merge into a Palace config.
    """
    if len(port_attributes) != num_ports:
        raise ValueError(
            f"port_attributes length ({len(port_attributes)}) must equal "
            f"num_ports ({num_ports})"
        )

    if amplitudes is None:
        amplitudes = [1.0] * num_ports
    if phases_deg is None:
        phases_deg = [0.0] * num_ports

    if len(amplitudes) != num_ports:
        raise ValueError("amplitudes length must equal num_ports")
    if len(phases_deg) != num_ports:
        raise ValueError("phases_deg length must equal num_ports")

    lumped_ports: list[dict[str, Any]] = []
    for i in range(num_ports):
        port: dict[str, Any] = {
            "Index": i + 1,
            "Attributes": [port_attributes[i]],
            "R": impedance,
            "Direction": direction,
            "Excitation": True,
            "Active": True,
        }
        # Palace supports excitation amplitude scaling & phase via
        # "ExcitationAmp" and "ExcitationPhase" (degrees).
        if amplitudes[i] != 1.0:
            port["ExcitationAmp"] = amplitudes[i]
        if phases_deg[i] != 0.0:
            port["ExcitationPhase"] = phases_deg[i]
        lumped_ports.append(port)

    return {"LumpedPort": lumped_ports}


def build_farfield_boundaries(
    absorbing_attributes: list[int],
    farfield_attributes: list[int] | None = None,
    order: int = 1,
) -> dict[str, Any]:
    """Build absorbing / far-field boundary entries for a Palace config.

    Args:
        absorbing_attributes: Mesh boundary attributes for an Absorbing BC
            (first-order or higher ABC).
        farfield_attributes: Optional separate attributes for far-field
            postprocessing surfaces.
        order: ABC order (1 or 2).

    Returns:
        A partial ``Boundaries`` dict to merge into a Palace config.
    """
    boundaries: dict[str, Any] = {
        "Absorbing": {
            "Attributes": absorbing_attributes,
            "Order": order,
        },
    }
    if farfield_attributes:
        boundaries["FarField"] = {"Attributes": farfield_attributes}
    return boundaries


def verify_impedance_match(
    impedances: list[dict[str, Any]],
    target_z: float = 50.0,
    tolerance_pct: float = 10.0,
) -> dict[str, Any]:
    """Check whether computed port impedances match a target value.

    Args:
        impedances: Parsed impedance records (from result_parser).
        target_z: Target impedance in Ohms.
        tolerance_pct: Acceptable deviation in percent.

    Returns:
        Per-port pass/fail summary with deviations.
    """
    results: dict[str, Any] = {
        "target_z": target_z,
        "tolerance_pct": tolerance_pct,
        "ports": {},
        "all_matched": True,
    }

    # Aggregate per port across all frequency steps
    port_z_vals: dict[str, list[float]] = {}
    for row in impedances:
        for key, val in row.items():
            if key.endswith("_mag"):
                port_id = key.replace("_mag", "")
                port_z_vals.setdefault(port_id, []).append(float(val))

    for port_id, values in port_z_vals.items():
        mean_z = sum(values) / len(values) if values else 0.0
        max_z = max(values) if values else 0.0
        min_z = min(values) if values else 0.0
        deviation_pct = abs(mean_z - target_z) / target_z * 100 if target_z else 0.0
        matched = deviation_pct <= tolerance_pct
        if not matched:
            results["all_matched"] = False
        results["ports"][port_id] = {
            "mean_z": round(mean_z, 2),
            "min_z": round(min_z, 2),
            "max_z": round(max_z, 2),
            "deviation_pct": round(deviation_pct, 2),
            "matched": matched,
        }

    return results
