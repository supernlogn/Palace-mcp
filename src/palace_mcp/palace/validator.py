"""Validate Palace JSON configuration files before execution."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationError:
    section: str
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [
                {"section": e.section, "message": e.message} for e in self.errors
            ],
            "warnings": [
                {"section": w.section, "message": w.message} for w in self.warnings
            ],
        }


def validate_config(config: dict[str, Any], config_dir: Path) -> ValidationResult:
    """Validate a Palace configuration dictionary.

    Args:
        config: The parsed Palace JSON config.
        config_dir: Directory containing the config file (for resolving relative paths).
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # 1. Check required top-level sections
    for section in ("Problem", "Model", "Domains"):
        if section not in config:
            errors.append(ValidationError(
                section=section,
                message=f"Required section '{section}' is missing.",
            ))

    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # 2. Problem section
    problem = config.get("Problem", {})
    valid_types = {"Eigenmode", "Driven", "Transient", "Electrostatic", "Magnetostatic"}
    problem_type = problem.get("Type")
    if problem_type not in valid_types:
        errors.append(ValidationError(
            section="Problem.Type",
            message=f"Invalid or missing Problem.Type '{problem_type}'. "
                    f"Must be one of {valid_types}.",
        ))

    # 3. Model section — mesh file existence
    model = config.get("Model", {})
    mesh_file = model.get("Mesh")
    if not mesh_file:
        errors.append(ValidationError(
            section="Model.Mesh",
            message="Model.Mesh is required but missing.",
        ))
    else:
        mesh_path = (config_dir / mesh_file).resolve()
        if not mesh_path.is_file():
            errors.append(ValidationError(
                section="Model.Mesh",
                message=f"Mesh file not found: {mesh_file} "
                        f"(resolved to {mesh_path}).",
            ))

    # 4. Domains — materials must have Attributes
    domains = config.get("Domains", {})
    materials = domains.get("Materials", [])
    if not materials:
        warnings.append(ValidationError(
            section="Domains.Materials",
            message="No materials defined. Palace requires at least one material.",
            severity="warning",
        ))
    for i, mat in enumerate(materials):
        if "Attributes" not in mat or not mat["Attributes"]:
            errors.append(ValidationError(
                section=f"Domains.Materials[{i}]",
                message="Material entry missing required 'Attributes' array.",
            ))

    # 5. Boundaries — check for required BCs depending on problem type
    boundaries = config.get("Boundaries", {})
    if problem_type == "Driven":
        has_port = bool(
            boundaries.get("LumpedPort")
            or boundaries.get("WavePort")
            or boundaries.get("SurfaceCurrent")
        )
        if not has_port:
            warnings.append(ValidationError(
                section="Boundaries",
                message="Driven problem has no LumpedPort, WavePort, or "
                        "SurfaceCurrent defined. At least one excitation "
                        "source is typically required.",
                severity="warning",
            ))
    if problem_type in ("Electrostatic", "Magnetostatic"):
        has_terminal = bool(boundaries.get("Terminal"))
        if not has_terminal:
            warnings.append(ValidationError(
                section="Boundaries",
                message=f"{problem_type} problem has no Terminal boundaries "
                        "defined. At least one terminal is typically required "
                        "for capacitance/inductance extraction.",
                severity="warning",
            ))

    # 6. Solver — check eigenmode settings
    solver = config.get("Solver", {})
    if problem_type == "Eigenmode" and "Eigenmode" not in solver:
        warnings.append(ValidationError(
            section="Solver.Eigenmode",
            message="Eigenmode problem but no Solver.Eigenmode section. "
                    "Default values will be used.",
            severity="warning",
        ))
    if problem_type == "Driven" and "Driven" not in solver:
        warnings.append(ValidationError(
            section="Solver.Driven",
            message="Driven problem but no Solver.Driven section with "
                    "frequency range. This is required.",
            severity="warning",
        ))

    valid = len(errors) == 0
    return ValidationResult(valid=valid, errors=errors, warnings=warnings)


def validate_config_file(config_path: Path) -> ValidationResult:
    """Validate a Palace JSON config file on disk."""
    if not config_path.is_file():
        return ValidationResult(
            valid=False,
            errors=[ValidationError(
                section="file",
                message=f"Config file not found: {config_path}",
            )],
        )
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        return ValidationResult(
            valid=False,
            errors=[ValidationError(
                section="file",
                message=f"Invalid JSON: {e}",
            )],
        )
    return validate_config(config, config_path.parent)
