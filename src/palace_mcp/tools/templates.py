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
    "dipole_antenna": {
        "name": "Dipole Antenna Array",
        "description": (
            "A linear array of thin-wire dipole antennas with parameterized "
            "spacing. Each dipole has an explicit feed-point gap for lumped "
            "port excitation. Suitable for driven (frequency-domain) "
            "simulations in Palace."
        ),
        "parameters": {
            "dipole_length": {"default": 150.0, "unit": "mm", "description": "Total dipole length (tip to tip)"},
            "wire_radius": {"default": 1.0, "unit": "mm", "description": "Wire cross-section radius"},
            "feed_gap": {"default": 2.0, "unit": "mm", "description": "Gap at the feed point of each dipole"},
            "num_dipoles": {"default": 5, "unit": "", "description": "Number of dipoles in the array"},
            "spacing": {"default": 150.0, "unit": "mm", "description": "Center-to-center spacing between adjacent dipoles"},
            "air_box_margin": {"default": 200.0, "unit": "mm", "description": "Distance from array to air-box boundary"},
            "mesh_size": {"default": 5.0, "unit": "mm", "description": "Target mesh element size"},
            "mesh_size_feed": {"default": 1.0, "unit": "mm", "description": "Refined mesh size near feed gaps"},
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
        "dipole_antenna": _gen_dipole,
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


def _gen_dipole(p: dict[str, float]) -> str:
    num = int(p["num_dipoles"])
    return f'''"""Dipole Antenna Array geometry generation using Gmsh.

Creates a linear array of {num} parallel thin-wire dipole antennas
with explicit feed-point gaps for lumped-port excitation.
"""
import gmsh
import os

gmsh.initialize()
gmsh.model.add("dipole_array")

# Parameters
dipole_length = {p["dipole_length"]}   # total tip-to-tip (mm)
wire_radius   = {p["wire_radius"]}
feed_gap      = {p["feed_gap"]}
num_dipoles   = {num}
spacing       = {p["spacing"]}
air_margin    = {p["air_box_margin"]}
lc            = {p["mesh_size"]}
lc_feed       = {p["mesh_size_feed"]}

half_len = dipole_length / 2.0
half_gap = feed_gap / 2.0

# Total array width along x
array_width = (num_dipoles - 1) * spacing

# ---- Build dipoles along the x-axis, oriented along z ----
wire_volumes = []
feed_volumes = []

for i in range(num_dipoles):
    cx = i * spacing  # centre x of dipole i
    cy = 0.0

    # Lower arm: cylinder from z = -half_len to z = -half_gap
    lower = gmsh.model.occ.addCylinder(
        cx, cy, -half_len,
        0, 0, half_len - half_gap,
        wire_radius,
    )

    # Upper arm: cylinder from z = +half_gap to z = +half_len
    upper = gmsh.model.occ.addCylinder(
        cx, cy, half_gap,
        0, 0, half_len - half_gap,
        wire_radius,
    )

    wire_volumes.extend([lower, upper])

    # Feed-gap volume (thin cylinder across the gap for lumped port)
    feed = gmsh.model.occ.addCylinder(
        cx, cy, -half_gap,
        0, 0, feed_gap,
        wire_radius,
    )
    wire_volumes.append(feed)
    feed_volumes.append(feed)

gmsh.model.occ.synchronize()

# ---- Air box surrounding the array ----
x_min = -air_margin
x_max = array_width + air_margin
y_min = -air_margin
y_max = air_margin
z_min = -half_len - air_margin
z_max = half_len + air_margin

air = gmsh.model.occ.addBox(
    x_min, y_min, z_min,
    x_max - x_min, y_max - y_min, z_max - z_min,
)

gmsh.model.occ.synchronize()

# ---- Physical groups ----
gmsh.model.addPhysicalGroup(3, wire_volumes, 1, "conductors")
gmsh.model.addPhysicalGroup(3, [air], 2, "air")
# Individual feed-gap volumes: attribute 10+i for port i
for i, fv in enumerate(feed_volumes):
    gmsh.model.addPhysicalGroup(3, [fv], 10 + i, f"feed_{{i+1}}")

# ---- Mesh sizing ----
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)

# Refine around feed gaps
for fv in feed_volumes:
    bb = gmsh.model.occ.getBoundingBox(3, fv)
    mid = [(bb[0]+bb[3])/2, (bb[1]+bb[4])/2, (bb[2]+bb[5])/2]
    gmsh.model.occ.addPoint(mid[0], mid[1], mid[2], lc_feed)

gmsh.model.occ.synchronize()
gmsh.model.mesh.generate(3)

output_dir = os.environ.get("PALACE_MESH_OUTPUT_DIR", ".")
gmsh.write(os.path.join(output_dir, "model.msh"))
gmsh.finalize()
'''
