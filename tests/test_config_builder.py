"""Tests for palace_mcp.palace.config_builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from palace_mcp.palace.config_builder import (
    _deep_merge,
    build_config,
    load_config,
    write_config,
)


# ---------------------------------------------------------------------------
# build_config
# ---------------------------------------------------------------------------

class TestBuildConfig:
    """build_config produces valid Palace JSON structures."""

    MATERIALS = [{"Attributes": [1], "Permittivity": 4.4}]

    def test_required_sections_present(self):
        cfg = build_config("Eigenmode", "mesh.msh", self.MATERIALS)
        for section in ("Problem", "Model", "Domains", "Boundaries", "Solver"):
            assert section in cfg

    def test_problem_type_set(self):
        cfg = build_config("Driven", "mesh.msh", self.MATERIALS)
        assert cfg["Problem"]["Type"] == "Driven"

    def test_mesh_file_set(self):
        cfg = build_config("Eigenmode", "../mesh/model.msh", self.MATERIALS)
        assert cfg["Model"]["Mesh"] == "../mesh/model.msh"

    def test_materials_assigned(self):
        cfg = build_config("Eigenmode", "m.msh", self.MATERIALS)
        assert cfg["Domains"]["Materials"] == self.MATERIALS

    @pytest.mark.parametrize(
        "problem_type",
        ["Eigenmode", "Driven", "Transient", "Electrostatic", "Magnetostatic"],
    )
    def test_valid_problem_types(self, problem_type: str):
        cfg = build_config(problem_type, "m.msh", self.MATERIALS)
        assert cfg["Problem"]["Type"] == problem_type

    def test_invalid_problem_type_raises(self):
        with pytest.raises(ValueError, match="Invalid problem type"):
            build_config("InvalidType", "m.msh", self.MATERIALS)

    def test_eigenmode_has_default_solver_section(self):
        cfg = build_config("Eigenmode", "m.msh", self.MATERIALS)
        assert "Eigenmode" in cfg["Solver"]
        assert cfg["Solver"]["Eigenmode"]["N"] == 5

    def test_driven_has_default_solver_section(self):
        cfg = build_config("Driven", "m.msh", self.MATERIALS)
        assert "Driven" in cfg["Solver"]
        assert "MinFreq" in cfg["Solver"]["Driven"]

    def test_transient_has_default_solver_section(self):
        cfg = build_config("Transient", "m.msh", self.MATERIALS)
        assert "Transient" in cfg["Solver"]

    def test_solver_override_merges(self):
        override = {"Order": 3, "Linear": {"Tol": 1e-10}}
        cfg = build_config("Eigenmode", "m.msh", self.MATERIALS, solver=override)
        assert cfg["Solver"]["Order"] == 3
        assert cfg["Solver"]["Linear"]["Tol"] == 1e-10
        # Original keys should still be present
        assert "KSPType" in cfg["Solver"]["Linear"]

    def test_boundaries_default_empty(self):
        cfg = build_config("Eigenmode", "m.msh", self.MATERIALS)
        assert cfg["Boundaries"] == {}

    def test_boundaries_override(self):
        boundaries = {"PEC": {"Attributes": [2, 3]}}
        cfg = build_config("Eigenmode", "m.msh", self.MATERIALS, boundaries=boundaries)
        assert cfg["Boundaries"]["PEC"]["Attributes"] == [2, 3]

    def test_length_unit(self):
        cfg = build_config("Eigenmode", "m.msh", self.MATERIALS, length_unit=1e-6)
        assert cfg["Model"]["L0"] == 1e-6

    def test_extra_keys_merged(self):
        cfg = build_config(
            "Eigenmode", "m.msh", self.MATERIALS,
            extra={"CustomSection": {"key": "value"}},
        )
        assert cfg["CustomSection"]["key"] == "value"


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------

class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_override_replaces_non_dict(self):
        base = {"a": {"x": 1}}
        override = {"a": 42}
        result = _deep_merge(base, override)
        assert result == {"a": 42}

    def test_modifies_base_in_place(self):
        base = {"a": 1}
        _deep_merge(base, {"b": 2})
        assert base == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# write_config / load_config
# ---------------------------------------------------------------------------

class TestWriteLoadConfig:
    def test_round_trip(self, tmp_path: Path):
        config = {"Problem": {"Type": "Eigenmode"}, "Model": {"Mesh": "m.msh"}}
        path = tmp_path / "config" / "palace.json"
        write_config(config, path)
        loaded = load_config(path)
        assert loaded == config

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "deep" / "nested" / "config.json"
        write_config({"key": "value"}, path)
        assert path.is_file()

    def test_json_is_indented(self, tmp_path: Path):
        path = tmp_path / "c.json"
        write_config({"a": 1}, path)
        text = path.read_text()
        assert "\n" in text  # pretty-printed
