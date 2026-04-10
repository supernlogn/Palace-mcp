"""Build and manipulate Palace JSON configuration files."""

from __future__ import annotations

import json
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
