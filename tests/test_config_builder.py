"""Tests for palace_mcp.palace.config_builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from palace_mcp.palace.config_builder import (
    _deep_merge,
    build_config,
    build_farfield_boundaries,
    build_phased_array_ports,
    load_config,
    verify_impedance_match,
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


# ---------------------------------------------------------------------------
# build_phased_array_ports
# ---------------------------------------------------------------------------

class TestBuildPhasedArrayPorts:
    def test_basic_ports(self):
        result = build_phased_array_ports(3, [10, 11, 12])
        ports = result["LumpedPort"]
        assert len(ports) == 3
        assert all(p["Excitation"] is True for p in ports)
        assert all(p["R"] == 50.0 for p in ports)

    def test_port_indices(self):
        result = build_phased_array_ports(2, [5, 6])
        ports = result["LumpedPort"]
        assert ports[0]["Index"] == 1
        assert ports[1]["Index"] == 2

    def test_custom_phases(self):
        result = build_phased_array_ports(
            3, [10, 11, 12], phases_deg=[0.0, 90.0, 180.0]
        )
        ports = result["LumpedPort"]
        assert "ExcitationPhase" not in ports[0]  # 0 deg is default
        assert ports[1]["ExcitationPhase"] == 90.0
        assert ports[2]["ExcitationPhase"] == 180.0

    def test_custom_amplitudes(self):
        result = build_phased_array_ports(
            2, [10, 11], amplitudes=[1.0, 2.0]
        )
        ports = result["LumpedPort"]
        assert "ExcitationAmp" not in ports[0]  # 1.0 is default
        assert ports[1]["ExcitationAmp"] == 2.0

    def test_custom_impedance(self):
        result = build_phased_array_ports(1, [10], impedance=75.0)
        assert result["LumpedPort"][0]["R"] == 75.0

    def test_mismatched_attributes_raises(self):
        with pytest.raises(ValueError, match="port_attributes length"):
            build_phased_array_ports(3, [10, 11])

    def test_mismatched_phases_raises(self):
        with pytest.raises(ValueError, match="phases_deg"):
            build_phased_array_ports(2, [10, 11], phases_deg=[0.0])

    def test_mismatched_amplitudes_raises(self):
        with pytest.raises(ValueError, match="amplitudes"):
            build_phased_array_ports(2, [10, 11], amplitudes=[1.0])


# ---------------------------------------------------------------------------
# build_farfield_boundaries
# ---------------------------------------------------------------------------

class TestBuildFarfieldBoundaries:
    def test_absorbing_only(self):
        result = build_farfield_boundaries([1, 2, 3])
        assert "Absorbing" in result
        assert result["Absorbing"]["Attributes"] == [1, 2, 3]
        assert result["Absorbing"]["Order"] == 1
        assert "FarField" not in result

    def test_with_farfield_attributes(self):
        result = build_farfield_boundaries([1], farfield_attributes=[4, 5])
        assert "FarField" in result
        assert result["FarField"]["Attributes"] == [4, 5]

    def test_custom_order(self):
        result = build_farfield_boundaries([1], order=2)
        assert result["Absorbing"]["Order"] == 2


# ---------------------------------------------------------------------------
# verify_impedance_match
# ---------------------------------------------------------------------------

class TestVerifyImpedanceMatch:
    def test_matched(self):
        impedances = [
            {"Z_V1_mag": 50.0, "Z_V2_mag": 50.0},
        ]
        result = verify_impedance_match(impedances, target_z=50.0, tolerance_pct=10.0)
        assert result["all_matched"] is True
        assert result["ports"]["Z_V1"]["matched"] is True

    def test_unmatched(self):
        impedances = [
            {"Z_V1_mag": 80.0},
        ]
        result = verify_impedance_match(impedances, target_z=50.0, tolerance_pct=10.0)
        assert result["all_matched"] is False
        assert result["ports"]["Z_V1"]["matched"] is False

    def test_tolerance_boundary(self):
        impedances = [
            {"Z_V1_mag": 55.0},  # 10% deviation
        ]
        result = verify_impedance_match(impedances, target_z=50.0, tolerance_pct=10.0)
        assert result["ports"]["Z_V1"]["matched"] is True

    def test_multi_frequency(self):
        impedances = [
            {"Z_V1_mag": 49.0},
            {"Z_V1_mag": 51.0},
        ]
        result = verify_impedance_match(impedances, target_z=50.0, tolerance_pct=5.0)
        assert result["ports"]["Z_V1"]["mean_z"] == 50.0
        assert result["all_matched"] is True
