"""Tests for palace_mcp.tools.templates."""

from __future__ import annotations

import pytest

from palace_mcp.tools.templates import (
    TEMPLATES,
    generate_template_script,
    get_template,
    list_templates,
)


class TestListTemplates:
    def test_returns_all_templates(self):
        result = list_templates()
        assert len(result) == len(TEMPLATES)

    def test_entries_have_required_keys(self):
        result = list_templates()
        for t in result:
            assert "id" in t
            assert "name" in t
            assert "description" in t
            assert "parameters" in t

    def test_known_templates_present(self):
        ids = [t["id"] for t in list_templates()]
        assert "split_ring_resonator" in ids
        assert "patch_antenna" in ids
        assert "coplanar_waveguide" in ids
        assert "microstrip_line" in ids
        assert "dipole_antenna" in ids


class TestGetTemplate:
    def test_valid_template(self):
        t = get_template("split_ring_resonator")
        assert t["id"] == "split_ring_resonator"
        assert "parameters" in t
        assert "outer_radius" in t["parameters"]

    def test_invalid_template(self):
        with pytest.raises(KeyError, match="not found"):
            get_template("nonexistent_template")


class TestGenerateTemplateScript:
    def test_generates_script(self):
        script = generate_template_script("split_ring_resonator")
        assert isinstance(script, str)
        assert len(script) > 0
        # Should contain gmsh or geometry-related code
        assert "gmsh" in script.lower() or "import" in script

    def test_with_custom_parameters(self):
        script = generate_template_script(
            "split_ring_resonator",
            parameters={"outer_radius": 5.0, "mesh_size": 0.5},
        )
        assert "5.0" in script or "5" in script

    def test_invalid_template_raises(self):
        with pytest.raises(KeyError):
            generate_template_script("nonexistent")

    def test_all_templates_generate_scripts(self):
        for tid in TEMPLATES:
            script = generate_template_script(tid)
            assert isinstance(script, str)
            assert len(script) > 100  # non-trivial script


class TestDipoleAntennaTemplate:
    def test_template_exists(self):
        t = get_template("dipole_antenna")
        assert t["id"] == "dipole_antenna"
        assert "dipole_length" in t["parameters"]
        assert "wire_radius" in t["parameters"]
        assert "feed_gap" in t["parameters"]
        assert "num_dipoles" in t["parameters"]
        assert "spacing" in t["parameters"]

    def test_generates_script(self):
        script = generate_template_script("dipole_antenna")
        assert "dipole_array" in script
        assert "gmsh" in script
        assert "feed" in script.lower()

    def test_custom_parameters(self):
        script = generate_template_script(
            "dipole_antenna",
            parameters={"num_dipoles": 3, "spacing": 200.0, "dipole_length": 140.0},
        )
        assert "num_dipoles   = 3" in script
        assert "spacing       = 200.0" in script
        assert "dipole_length = 140.0" in script

    def test_feed_gap_volumes_created(self):
        script = generate_template_script("dipole_antenna")
        assert "feed_volumes" in script
        # Should create physical groups for feeds
        assert "feed_" in script

    def test_default_five_dipoles(self):
        script = generate_template_script("dipole_antenna")
        assert "num_dipoles   = 5" in script
