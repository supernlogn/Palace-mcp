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
