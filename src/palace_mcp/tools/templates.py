"""Parameterized geometry templates for common EM structures using VTK."""

from __future__ import annotations

from typing import Any


TEMPLATES: dict[str, dict[str, Any]] = {
    "split_ring_resonator": {
        "name": "Split-Ring Resonator (SRR)",
        "description": (
            "A planar split-ring resonator for metamaterial unit cells. "
            "Commonly used for negative permeability media."
        ),
        "parameters": {
            "outer_radius": {"default": 3.0, "unit": "mm", "description": "Outer ring radius"},
            "inner_radius": {"default": 2.0, "unit": "mm", "description": "Inner ring radius"},
            "gap_width": {"default": 0.5, "unit": "mm", "description": "Gap width in the ring"},
            "ring_width": {"default": 0.5, "unit": "mm", "description": "Metal ring width"},
            "substrate_size": {"default": 10.0, "unit": "mm", "description": "Substrate side length"},
            "substrate_thickness": {"default": 1.6, "unit": "mm", "description": "Substrate thickness"},
            "metal_thickness": {"default": 0.035, "unit": "mm", "description": "Metal layer thickness"},
            "mesh_size": {"default": 0.3, "unit": "mm", "description": "Target mesh element size"},
        },
    },
    "patch_antenna": {
        "name": "Rectangular Patch Antenna",
        "description": (
            "A rectangular microstrip patch antenna on a grounded dielectric substrate."
        ),
        "parameters": {
            "patch_length": {"default": 30.0, "unit": "mm", "description": "Patch length (resonant dimension)"},
            "patch_width": {"default": 38.0, "unit": "mm", "description": "Patch width"},
            "substrate_length": {"default": 60.0, "unit": "mm", "description": "Substrate length"},
            "substrate_width": {"default": 60.0, "unit": "mm", "description": "Substrate width"},
            "substrate_thickness": {"default": 1.6, "unit": "mm", "description": "Substrate height"},
            "feed_offset": {"default": 8.0, "unit": "mm", "description": "Feed point offset from center"},
            "mesh_size": {"default": 1.0, "unit": "mm", "description": "Target mesh element size"},
        },
    },
    "coplanar_waveguide": {
        "name": "Coplanar Waveguide (CPW)",
        "description": (
            "A coplanar waveguide transmission line on a dielectric substrate."
        ),
        "parameters": {
            "center_width": {"default": 1.0, "unit": "mm", "description": "Center conductor width"},
            "gap_width": {"default": 0.5, "unit": "mm", "description": "Gap between center and ground"},
            "ground_width": {"default": 5.0, "unit": "mm", "description": "Ground plane width"},
            "length": {"default": 20.0, "unit": "mm", "description": "Waveguide length"},
            "substrate_thickness": {"default": 0.5, "unit": "mm", "description": "Substrate thickness"},
            "metal_thickness": {"default": 0.035, "unit": "mm", "description": "Metal thickness"},
            "mesh_size": {"default": 0.2, "unit": "mm", "description": "Target mesh element size"},
        },
    },
    "microstrip_line": {
        "name": "Microstrip Transmission Line",
        "description": (
            "A microstrip transmission line on a grounded dielectric substrate."
        ),
        "parameters": {
            "strip_width": {"default": 3.0, "unit": "mm", "description": "Strip width"},
            "strip_length": {"default": 30.0, "unit": "mm", "description": "Strip length"},
            "substrate_width": {"default": 15.0, "unit": "mm", "description": "Substrate width"},
            "substrate_length": {"default": 40.0, "unit": "mm", "description": "Substrate length"},
            "substrate_thickness": {"default": 1.6, "unit": "mm", "description": "Substrate height"},
            "metal_thickness": {"default": 0.035, "unit": "mm", "description": "Metal thickness"},
            "mesh_size": {"default": 0.5, "unit": "mm", "description": "Target mesh element size"},
        },
    },
}


def list_templates() -> list[dict[str, Any]]:
    """List all available geometry templates."""
    return [
        {
            "id": tid,
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for tid, t in TEMPLATES.items()
    ]


def get_template(template_id: str) -> dict[str, Any]:
    """Get a specific geometry template."""
    t = TEMPLATES.get(template_id)
    if t is None:
        raise KeyError(f"Template '{template_id}' not found")
    return {"id": template_id, **t}


def generate_template_script(
    template_id: str,
    parameters: dict[str, float] | None = None,
) -> str:
    """Generate a Python/Gmsh script for a geometry template.

    Returns the script content as a string.
    """
    t = TEMPLATES.get(template_id)
    if t is None:
        raise KeyError(f"Template '{template_id}' not found")

    # Merge defaults with user parameters
    params: dict[str, float] = {}
    for key, info in t["parameters"].items():
        params[key] = info["default"]
    if parameters:
        for key, val in parameters.items():
            if key in params:
                params[key] = val

    generators = {
        "split_ring_resonator": _gen_srr,
        "patch_antenna": _gen_patch,
        "coplanar_waveguide": _gen_cpw,
        "microstrip_line": _gen_microstrip,
    }

    gen = generators.get(template_id)
    if gen is None:
        raise NotImplementedError(f"Generator for '{template_id}' not implemented")

    return gen(params)


def _gen_srr(p: dict[str, float]) -> str:
    return f'''"""Split-Ring Resonator geometry generation using Gmsh."""
import gmsh
import os

gmsh.initialize()
gmsh.model.add("srr")

outer_r = {p["outer_radius"]}
inner_r = {p["inner_radius"]}
gap = {p["gap_width"]}
ring_w = {p["ring_width"]}
sub_size = {p["substrate_size"]}
sub_h = {p["substrate_thickness"]}
metal_h = {p["metal_thickness"]}
lc = {p["mesh_size"]}

# Substrate
sub = gmsh.model.occ.addBox(
    -sub_size/2, -sub_size/2, 0,
    sub_size, sub_size, sub_h
)

# Outer ring (approximated as annular region minus gap)
outer_disk = gmsh.model.occ.addDisk(0, 0, sub_h, outer_r, outer_r)
inner_disk = gmsh.model.occ.addDisk(0, 0, sub_h, outer_r - ring_w, outer_r - ring_w)
ring_2d = gmsh.model.occ.cut([(2, outer_disk)], [(2, inner_disk)])[0]

# Create gap by cutting a small rectangle
gap_rect = gmsh.model.occ.addRectangle(
    outer_r - ring_w - 0.1, -gap/2, sub_h,
    ring_w + 0.2, gap
)
if ring_2d:
    ring_with_gap = gmsh.model.occ.cut(ring_2d, [(2, gap_rect)])[0]

gmsh.model.occ.synchronize()

# Physical groups
gmsh.model.addPhysicalGroup(3, [sub], 1, "substrate")

# Mesh
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
gmsh.model.mesh.generate(3)

output_dir = os.environ.get("PALACE_MESH_OUTPUT_DIR", ".")
gmsh.write(os.path.join(output_dir, "model.msh"))
gmsh.finalize()
'''


def _gen_patch(p: dict[str, float]) -> str:
    return f'''"""Rectangular Patch Antenna geometry generation using Gmsh."""
import gmsh
import os

gmsh.initialize()
gmsh.model.add("patch_antenna")

patch_l = {p["patch_length"]}
patch_w = {p["patch_width"]}
sub_l = {p["substrate_length"]}
sub_w = {p["substrate_width"]}
sub_h = {p["substrate_thickness"]}
feed_off = {p["feed_offset"]}
lc = {p["mesh_size"]}

# Substrate
sub = gmsh.model.occ.addBox(
    -sub_l/2, -sub_w/2, 0,
    sub_l, sub_w, sub_h
)

# Air box above
air_height = sub_h * 10
air = gmsh.model.occ.addBox(
    -sub_l/2, -sub_w/2, 0,
    sub_l, sub_w, air_height
)

gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(3, [sub], 1, "substrate")
gmsh.model.addPhysicalGroup(3, [air], 2, "air")

# Mesh
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
gmsh.model.mesh.generate(3)

output_dir = os.environ.get("PALACE_MESH_OUTPUT_DIR", ".")
gmsh.write(os.path.join(output_dir, "model.msh"))
gmsh.finalize()
'''


def _gen_cpw(p: dict[str, float]) -> str:
    return f'''"""Coplanar Waveguide geometry generation using Gmsh."""
import gmsh
import os

gmsh.initialize()
gmsh.model.add("cpw")

center_w = {p["center_width"]}
gap_w = {p["gap_width"]}
gnd_w = {p["ground_width"]}
length = {p["length"]}
sub_h = {p["substrate_thickness"]}
metal_h = {p["metal_thickness"]}
lc = {p["mesh_size"]}

total_w = 2*gnd_w + 2*gap_w + center_w

# Substrate
sub = gmsh.model.occ.addBox(0, -total_w/2, 0, length, total_w, sub_h)

# Air box
air_h = sub_h * 8
air = gmsh.model.occ.addBox(0, -total_w/2, sub_h, length, total_w, air_h)

gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(3, [sub], 1, "substrate")
gmsh.model.addPhysicalGroup(3, [air], 2, "air")

# Mesh
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
gmsh.model.mesh.generate(3)

output_dir = os.environ.get("PALACE_MESH_OUTPUT_DIR", ".")
gmsh.write(os.path.join(output_dir, "model.msh"))
gmsh.finalize()
'''


def _gen_microstrip(p: dict[str, float]) -> str:
    return f'''"""Microstrip Transmission Line geometry generation using Gmsh."""
import gmsh
import os

gmsh.initialize()
gmsh.model.add("microstrip")

strip_w = {p["strip_width"]}
strip_l = {p["strip_length"]}
sub_w = {p["substrate_width"]}
sub_l = {p["substrate_length"]}
sub_h = {p["substrate_thickness"]}
metal_h = {p["metal_thickness"]}
lc = {p["mesh_size"]}

# Substrate
sub = gmsh.model.occ.addBox(
    -sub_l/2, -sub_w/2, 0,
    sub_l, sub_w, sub_h
)

# Air box
air_h = sub_h * 8
air = gmsh.model.occ.addBox(
    -sub_l/2, -sub_w/2, sub_h,
    sub_l, sub_w, air_h
)

gmsh.model.occ.synchronize()

gmsh.model.addPhysicalGroup(3, [sub], 1, "substrate")
gmsh.model.addPhysicalGroup(3, [air], 2, "air")

# Mesh
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)
gmsh.model.mesh.generate(3)

output_dir = os.environ.get("PALACE_MESH_OUTPUT_DIR", ".")
gmsh.write(os.path.join(output_dir, "model.msh"))
gmsh.finalize()
'''
