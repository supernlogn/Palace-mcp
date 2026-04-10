"""Materials database MCP tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent.parent / "data"
_MATERIALS_FILE = _DATA_DIR / "materials.json"


def _load_db() -> dict[str, Any]:
    with open(_MATERIALS_FILE) as f:
        return json.load(f)


def _save_db(db: dict[str, Any]) -> None:
    with open(_MATERIALS_FILE, "w") as f:
        json.dump(db, f, indent=2)


def list_materials() -> list[dict[str, Any]]:
    """List all materials in the database."""
    db = _load_db()
    result = []
    for key, mat in db["materials"].items():
        entry = {"id": key, **mat}
        result.append(entry)
    return result


def get_material(material_id: str) -> dict[str, Any]:
    """Get a specific material by ID."""
    db = _load_db()
    mat = db["materials"].get(material_id)
    if mat is None:
        raise KeyError(f"Material '{material_id}' not found")
    return {"id": material_id, **mat}


def search_materials(query: str) -> list[dict[str, Any]]:
    """Search materials by name or property."""
    db = _load_db()
    query_lower = query.lower()
    results = []
    for key, mat in db["materials"].items():
        name = mat.get("name", "").lower()
        if query_lower in key.lower() or query_lower in name:
            results.append({"id": key, **mat})
    return results


def add_material(
    material_id: str,
    name: str,
    permittivity: float = 1.0,
    permeability: float = 1.0,
    loss_tan: float = 0.0,
    conductivity: float = 0.0,
    london_depth: float | None = None,
    material_axes: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Add a new material to the database."""
    db = _load_db()
    if material_id in db["materials"]:
        raise ValueError(f"Material '{material_id}' already exists")

    mat: dict[str, Any] = {
        "name": name,
        "Permeability": permeability,
        "Permittivity": permittivity,
        "LossTan": loss_tan,
        "Conductivity": conductivity,
    }
    if london_depth is not None:
        mat["LondonDepth"] = london_depth
    if material_axes is not None:
        mat["MaterialAxes"] = material_axes

    db["materials"][material_id] = mat
    _save_db(db)
    return {"id": material_id, **mat}


def material_to_palace_config(
    material_id: str, attributes: list[int]
) -> dict[str, Any]:
    """Convert a material DB entry to a Palace config Materials entry."""
    mat = get_material(material_id)
    palace_mat: dict[str, Any] = {"Attributes": attributes}

    for key in ("Permeability", "Permittivity", "LossTan", "Conductivity",
                "LondonDepth", "MaterialAxes"):
        if key in mat and mat[key]:
            palace_mat[key] = mat[key]

    return palace_mat
