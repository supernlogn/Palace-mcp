"""Tests for palace_mcp.palace.validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from palace_mcp.palace.validator import (
    ValidationResult,
    validate_config,
    validate_config_file,
)


_DEFAULT_MATERIALS = [{"Attributes": [1], "Permittivity": 1.0}]


def _minimal_config(
    problem_type: str = "Eigenmode",
    mesh_file: str = "mesh.msh",
    materials: list | None = None,
) -> dict:
    """Return a minimal valid Palace config dict."""
    return {
        "Problem": {"Type": problem_type},
        "Model": {"Mesh": mesh_file},
        "Domains": {
            "Materials": _DEFAULT_MATERIALS if materials is None else materials
        },
        "Boundaries": {},
        "Solver": {"Order": 2},
    }


class TestValidateConfig:
    """validate_config checks structural correctness."""

    def test_valid_minimal_config(self, tmp_path: Path):
        # Create mesh so the file-existence check passes
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config()
        result = validate_config(cfg, tmp_path)
        assert result.valid
        assert result.errors == []

    def test_missing_problem_section(self, tmp_path: Path):
        cfg = _minimal_config()
        del cfg["Problem"]
        result = validate_config(cfg, tmp_path)
        assert not result.valid
        assert any("Problem" in e.message for e in result.errors)

    def test_missing_model_section(self, tmp_path: Path):
        cfg = _minimal_config()
        del cfg["Model"]
        result = validate_config(cfg, tmp_path)
        assert not result.valid
        assert any("Model" in e.message for e in result.errors)

    def test_missing_domains_section(self, tmp_path: Path):
        cfg = _minimal_config()
        del cfg["Domains"]
        result = validate_config(cfg, tmp_path)
        assert not result.valid

    def test_invalid_problem_type(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(problem_type="FooBar")
        result = validate_config(cfg, tmp_path)
        assert not result.valid
        assert any("Problem.Type" in e.section for e in result.errors)

    def test_mesh_file_not_found(self, tmp_path: Path):
        cfg = _minimal_config(mesh_file="nonexistent.msh")
        result = validate_config(cfg, tmp_path)
        assert not result.valid
        assert any("Mesh" in e.section for e in result.errors)

    def test_mesh_file_exists(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config()
        result = validate_config(cfg, tmp_path)
        assert result.valid

    def test_no_materials_warning(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(materials=[])
        result = validate_config(cfg, tmp_path)
        # valid=True but should have a warning about no materials
        assert result.valid
        assert any(
            "Materials" in w.section or "material" in w.message.lower()
            for w in result.warnings
        )

    def test_material_missing_attributes(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(materials=[{"Permittivity": 4.4}])
        result = validate_config(cfg, tmp_path)
        assert not result.valid
        assert any("Attributes" in e.message for e in result.errors)

    def test_driven_no_port_warning(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(problem_type="Driven")
        result = validate_config(cfg, tmp_path)
        assert any(
            "LumpedPort" in w.message or "excitation" in w.message
            for w in result.warnings
        )

    def test_driven_with_port_no_warning(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(problem_type="Driven")
        cfg["Boundaries"]["LumpedPort"] = [{"Attributes": [5]}]
        result = validate_config(cfg, tmp_path)
        assert not any("LumpedPort" in w.message for w in result.warnings)

    def test_electrostatic_no_terminal_warning(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(problem_type="Electrostatic")
        result = validate_config(cfg, tmp_path)
        assert any("Terminal" in w.message for w in result.warnings)

    def test_eigenmode_no_solver_warning(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config(problem_type="Eigenmode")
        cfg.pop("Solver", None)
        result = validate_config(cfg, tmp_path)
        assert any("Eigenmode" in w.section for w in result.warnings)


class TestValidationResultToDict:
    def test_to_dict_structure(self):
        result = ValidationResult(valid=True, errors=[], warnings=[])
        d = result.to_dict()
        assert d["valid"] is True
        assert d["errors"] == []
        assert d["warnings"] == []


class TestValidateConfigFile:
    def test_file_not_found(self, tmp_path: Path):
        result = validate_config_file(tmp_path / "nope.json")
        assert not result.valid
        assert any("not found" in e.message for e in result.errors)

    def test_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json !!!")
        result = validate_config_file(bad)
        assert not result.valid
        assert any("Invalid JSON" in e.message for e in result.errors)

    def test_valid_config_file(self, tmp_path: Path):
        mesh = tmp_path / "mesh.msh"
        mesh.write_text("")
        cfg = _minimal_config()
        cfg_path = tmp_path / "palace.json"
        cfg_path.write_text(json.dumps(cfg))
        result = validate_config_file(cfg_path)
        assert result.valid
