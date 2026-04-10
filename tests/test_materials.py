"""Tests for palace_mcp.tools.materials."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest import mock

import pytest

from palace_mcp.tools import materials as mat_tools


@pytest.fixture()
def materials_db(tmp_path: Path):
    """Create a temporary materials database and patch the module to use it."""
    db = {
        "materials": {
            "vacuum": {"name": "Vacuum", "Permittivity": 1.0, "Permeability": 1.0, "LossTan": 0.0, "Conductivity": 0.0},
            "copper": {"name": "Copper", "Permittivity": 1.0, "Permeability": 1.0, "LossTan": 0.0, "Conductivity": 5.8e7},
            "fr4": {"name": "FR-4", "Permittivity": 4.4, "Permeability": 1.0, "LossTan": 0.02, "Conductivity": 0.0},
        }
    }
    db_path = tmp_path / "materials.json"
    db_path.write_text(json.dumps(db, indent=2))

    with mock.patch.object(mat_tools, "_MATERIALS_FILE", db_path):
        yield db_path


class TestListMaterials:
    def test_returns_all(self, materials_db):
        result = mat_tools.list_materials()
        assert len(result) == 3
        ids = [m["id"] for m in result]
        assert "vacuum" in ids
        assert "copper" in ids
        assert "fr4" in ids

    def test_entries_have_id(self, materials_db):
        result = mat_tools.list_materials()
        for mat in result:
            assert "id" in mat
            assert "name" in mat


class TestGetMaterial:
    def test_existing(self, materials_db):
        mat = mat_tools.get_material("copper")
        assert mat["id"] == "copper"
        assert mat["name"] == "Copper"
        assert mat["Conductivity"] == 5.8e7

    def test_not_found(self, materials_db):
        with pytest.raises(KeyError, match="not found"):
            mat_tools.get_material("unobtainium")


class TestSearchMaterials:
    def test_search_by_name(self, materials_db):
        results = mat_tools.search_materials("copper")
        assert len(results) == 1
        assert results[0]["id"] == "copper"

    def test_search_by_id(self, materials_db):
        results = mat_tools.search_materials("fr4")
        assert len(results) == 1

    def test_case_insensitive(self, materials_db):
        results = mat_tools.search_materials("VACUUM")
        assert len(results) == 1

    def test_no_match(self, materials_db):
        results = mat_tools.search_materials("unobtainium")
        assert results == []


class TestAddMaterial:
    def test_add_new(self, materials_db):
        result = mat_tools.add_material("silicon", "Silicon", permittivity=11.7)
        assert result["id"] == "silicon"
        assert result["Permittivity"] == 11.7
        # Verify persisted
        reloaded = mat_tools.get_material("silicon")
        assert reloaded["Permittivity"] == 11.7

    def test_duplicate_raises(self, materials_db):
        with pytest.raises(ValueError, match="already exists"):
            mat_tools.add_material("copper", "Copper 2")

    def test_with_london_depth(self, materials_db):
        result = mat_tools.add_material(
            "niobium", "Niobium", london_depth=39e-9
        )
        assert result["LondonDepth"] == 39e-9


class TestMaterialToPalaceConfig:
    def test_converts_material(self, materials_db):
        result = mat_tools.material_to_palace_config("fr4", [1, 2])
        assert result["Attributes"] == [1, 2]
        assert result["Permittivity"] == 4.4
        assert result["LossTan"] == 0.02

    def test_zero_conductivity_excluded(self, materials_db):
        result = mat_tools.material_to_palace_config("vacuum", [1])
        assert result["Attributes"] == [1]
        # Zero/falsy values should not appear
        assert "Conductivity" not in result or result["Conductivity"] == 0.0
