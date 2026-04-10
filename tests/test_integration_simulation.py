"""End-to-end integration test: mesh generation → Palace config → simulation
result parsing → VTK mesh quality & rendering → Plotly visualisation.

This test exercises the full workflow without requiring the actual Palace
binary.  It:

1. Generates a split-ring resonator geometry script via the template engine.
2. Executes the geometry script *in-process* (via ``exec``) to produce a .msh.
3. Converts the mesh to VTU and validates quality with VTK.
4. Renders the mesh to a PNG image (VTK offscreen).
5. Builds a Palace eigenmode configuration using the config builder.
6. Validates the configuration.
7. Creates synthetic simulation output CSVs (eigenfrequency + domain energy).
8. Parses the results with the result parser.
9. Generates an eigenmode frequency/Q-factor plot and a field-energy plot.
10. Asserts every intermediate artefact is correct and the final plots exist.
"""

from __future__ import annotations

import base64
import csv
import json
import math
import os
from pathlib import Path

import pytest

from palace_mcp.palace.config_builder import build_config, write_config
from palace_mcp.palace.result_parser import parse_results
from palace_mcp.palace.validator import validate_config
from palace_mcp.tools.mesh import (
    get_mesh_info,
    validate_mesh_quality,
)
from palace_mcp.tools.templates import generate_template_script
from palace_mcp.tools.visualization import (
    generate_eigenmode_plot,
    generate_field_energy_plot,
    render_mesh_to_image,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture()
def work_dir(tmp_path: Path) -> Path:
    """Create a project-like directory layout under tmp_path."""
    for sub in ("scripts", "mesh", "config", "results/paraview"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ── Helpers ───────────────────────────────────────────────────────────────


def _run_gmsh_script_in_process(script: str, output_dir: Path) -> None:
    """Execute a Gmsh geometry script in the current process.

    Sets PALACE_MESH_OUTPUT_DIR so the template script writes its mesh to
    *output_dir*, then runs the script via ``exec``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    old_env = os.environ.get("PALACE_MESH_OUTPUT_DIR")
    old_cwd = os.getcwd()
    try:
        os.environ["PALACE_MESH_OUTPUT_DIR"] = str(output_dir)
        os.chdir(str(output_dir))
        exec(compile(script, "<gmsh_template>", "exec"), {"__name__": "__main__"})
    finally:
        os.chdir(old_cwd)
        if old_env is None:
            os.environ.pop("PALACE_MESH_OUTPUT_DIR", None)
        else:
            os.environ["PALACE_MESH_OUTPUT_DIR"] = old_env


def _convert_msh_to_vtu_gmsh(msh_path: Path, vtu_path: Path) -> None:
    """Convert a .msh to .vtu by reading with gmsh and building a VTK grid.

    This avoids reliance on vtkGmshReader which may not be available.
    """
    import gmsh
    import numpy as np
    import vtk

    gmsh.initialize()
    try:
        gmsh.open(str(msh_path))
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        coords = np.array(coords, dtype=np.float64).reshape(-1, 3)

        # Build a VTK unstructured grid
        points = vtk.vtkPoints()
        for pt in coords:
            points.InsertNextPoint(pt[0], pt[1], pt[2])

        grid = vtk.vtkUnstructuredGrid()
        grid.SetPoints(points)

        # Map gmsh node tags (1-based, possibly non-contiguous) → 0-based VTK ids
        tag_to_id = {int(t): i for i, t in enumerate(node_tags)}

        # Element type mapping (gmsh type → VTK cell type)
        gmsh_to_vtk = {
            1: vtk.VTK_LINE,           # 2-node line
            2: vtk.VTK_TRIANGLE,       # 3-node triangle
            3: vtk.VTK_QUAD,           # 4-node quad
            4: vtk.VTK_TETRA,          # 4-node tet
            5: vtk.VTK_HEXAHEDRON,     # 8-node hex
            6: vtk.VTK_WEDGE,          # 6-node prism
            7: vtk.VTK_PYRAMID,        # 5-node pyramid
            15: vtk.VTK_VERTEX,        # 1-node point
        }

        elem_types, elem_tags, elem_nodes = gmsh.model.mesh.getElements()
        for etype, tags, nodes in zip(elem_types, elem_tags, elem_nodes):
            etype = int(etype)
            _, _, _, num_nodes_per, _, _ = gmsh.model.mesh.getElementProperties(etype)
            num_nodes_per = int(num_nodes_per)
            vtk_type = gmsh_to_vtk.get(etype)
            if vtk_type is None:
                continue  # skip higher-order or unknown types
            node_arr = np.array(nodes, dtype=np.int64)
            for i in range(len(tags)):
                cell_nodes = node_arr[i * num_nodes_per : (i + 1) * num_nodes_per]
                id_list = vtk.vtkIdList()
                for n in cell_nodes:
                    id_list.InsertNextId(tag_to_id[int(n)])
                grid.InsertNextCell(vtk_type, id_list)

        writer = vtk.vtkXMLUnstructuredGridWriter()
        writer.SetFileName(str(vtu_path))
        writer.SetInputData(grid)
        writer.Write()
    finally:
        gmsh.finalize()


def _write_synthetic_eigenmode_csvs(results_dir: Path, num_modes: int = 5) -> None:
    """Create fake Palace eigenmode output CSVs so the parser can consume them.

    Palace writes domain-E.csv with columns like:
        freq (Hz),  Q,  E_elec (J),  E_mag (J)
    """
    domain_e = results_dir / "domain-E.csv"
    with open(domain_e, "w", newline="") as fh:
        writer = csv.writer(fh)
        fh.write("# Palace eigenmode output\n")
        writer.writerow(["freq (Hz)", "Q", "E_elec (J)", "E_mag (J)"])
        for i in range(1, num_modes + 1):
            freq_hz = 1e9 * (2.0 + 0.5 * i)  # 2.5, 3.0, … GHz
            q_factor = 500.0 + 100 * i
            e_elec = 1e-12 * i
            e_mag = 1.2e-12 * i
            writer.writerow([freq_hz, q_factor, e_elec, e_mag])


def _write_synthetic_driven_csvs(
    results_dir: Path, num_steps: int = 20
) -> None:
    """Create fake port-V / port-I CSVs for a single-port driven simulation.

    Used to exercise domain-energy plotting (one energy value per step).
    """
    domain_e = results_dir / "domain-E.csv"
    with open(domain_e, "w", newline="") as fh:
        writer = csv.writer(fh)
        fh.write("# Palace driven output\n")
        writer.writerow(["freq (Hz)", "E_elec (J)", "E_mag (J)"])
        for step in range(num_steps):
            freq = 1e9 + step * 0.5e9
            e_elec = 1e-12 * math.exp(-((step - 10) ** 2) / 20)
            e_mag = 0.8e-12 * math.exp(-((step - 10) ** 2) / 25)
            writer.writerow([freq, e_elec, e_mag])


# ── The Test ──────────────────────────────────────────────────────────────


class TestSRREigenmodeWorkflow:
    """Full pipeline: geometry → mesh → config → (synthetic) results → plots."""

    def test_full_eigenmode_pipeline(self, work_dir: Path) -> None:
        # ── 1. Generate geometry script ────────────────────────────────
        script = generate_template_script(
            "split_ring_resonator",
            parameters={
                "outer_radius": 3.0,
                "inner_radius": 2.0,
                "gap_width": 0.5,
                "ring_width": 0.5,
                "substrate_size": 10.0,
                "substrate_thickness": 1.6,
                "metal_thickness": 0.035,
                "mesh_size": 1.5,  # coarser for speed
            },
        )
        assert "gmsh" in script
        assert "model.msh" in script

        # ── 2. Run Gmsh script (in-process) → produce .msh ─────────────
        mesh_dir = work_dir / "mesh"
        _run_gmsh_script_in_process(script, mesh_dir)
        msh_path = mesh_dir / "model.msh"
        assert msh_path.exists(), "model.msh was not created"

        # ── 3. Convert .msh → .vtu ────────────────────────────────────
        vtu_path = mesh_dir / "model.vtu"
        _convert_msh_to_vtu_gmsh(msh_path, vtu_path)
        vtu_path_str = str(vtu_path)
        assert vtu_path.exists(), "model.vtu was not created"

        # ── 4. Validate mesh quality (VTK) ─────────────────────────────
        quality = validate_mesh_quality(vtu_path_str)
        assert "error" not in quality, f"Mesh quality error: {quality}"
        assert quality["num_cells"] > 0
        assert quality["num_points"] > 0
        assert "quality_metrics" in quality

        # ── 5. Get mesh info ───────────────────────────────────────────
        info = get_mesh_info(vtu_path_str)
        assert "error" not in info
        assert info["num_points"] == quality["num_points"]

        # ── 6. Render mesh to PNG (VTK offscreen) ──────────────────────
        render = render_mesh_to_image(vtu_path_str, width=640, height=480)
        assert "error" not in render, f"Render failed: {render}"
        assert render["format"] == "png"
        # Verify it decodes to valid PNG bytes
        png_bytes = base64.b64decode(render["image_base64"])
        assert png_bytes[:4] == b"\x89PNG"

        # ── 7. Build Palace eigenmode config ───────────────────────────
        materials = [
            {
                "Attributes": [1],
                "Permittivity": 4.4,
                "LossTan": 0.02,
                "Description": "FR-4 substrate",
            },
        ]
        boundaries = {"PEC": {"Attributes": [2]}}
        config = build_config(
            problem_type="Eigenmode",
            mesh_file="../mesh/model.msh",
            materials=materials,
            boundaries=boundaries,
            solver={"Order": 1, "Eigenmode": {"N": 5, "Tol": 1e-6}},
        )
        assert config["Problem"]["Type"] == "Eigenmode"
        assert config["Solver"]["Eigenmode"]["N"] == 5

        # Write config to disk
        config_path = work_dir / "config" / "palace.json"
        write_config(config, config_path)
        assert config_path.exists()

        # Round-trip: re-read and compare
        with open(config_path) as fh:
            loaded = json.load(fh)
        assert loaded["Problem"]["Type"] == "Eigenmode"

        # ── 8. Validate config (file-based) ────────────────────────────
        #   The validator resolves Model.Mesh relative to config_dir, so
        #   write the config with a relative path and pass config_dir.
        validation = validate_config(config, config_dir=config_path.parent)
        assert len(validation.errors) == 0, (
            f"Config validation errors: {validation.errors}"
        )

        # ── 9. Create synthetic simulation results ─────────────────────
        results_dir = work_dir / "results"
        _write_synthetic_eigenmode_csvs(results_dir, num_modes=5)

        parsed = parse_results(results_dir, problem_type="Eigenmode")
        assert len(parsed.eigenfrequencies) == 5
        assert all(
            ef["frequency_hz"] > 0 for ef in parsed.eigenfrequencies
        )
        assert all(
            ef["quality_factor"] > 0 for ef in parsed.eigenfrequencies
        )

        # ── 10. Generate eigenmode plot ────────────────────────────────
        eigenplot_path = str(work_dir / "results" / "eigenmode_plot.html")
        eigenplot = generate_eigenmode_plot(
            parsed.eigenfrequencies, output_path=eigenplot_path
        )
        assert eigenplot["plot_type"] == "eigenmode"
        assert eigenplot["file"] == eigenplot_path
        assert Path(eigenplot_path).exists()
        html_content = Path(eigenplot_path).read_text(encoding="utf-8")
        assert "plotly" in html_content.lower()

        # ── 11. Generate field energy plot ─────────────────────────────
        energy_plot_path = str(work_dir / "results" / "energy_plot.html")
        energy_plot = generate_field_energy_plot(
            parsed.domain_energies, output_path=energy_plot_path
        )
        assert energy_plot["plot_type"] == "field_energy"
        assert Path(energy_plot_path).exists()


class TestPatchAntennaDrivenWorkflow:
    """Driven simulation pipeline with a patch antenna mesh."""

    def test_driven_pipeline_with_energy_plot(self, work_dir: Path) -> None:
        # ── 1. Generate patch antenna mesh ─────────────────────────────
        script = generate_template_script(
            "patch_antenna",
            parameters={
                "patch_length": 30.0,
                "patch_width": 38.0,
                "substrate_length": 60.0,
                "substrate_width": 60.0,
                "substrate_thickness": 1.6,
                "feed_offset": 8.0,
                "mesh_size": 3.0,  # coarse for speed
            },
        )
        mesh_dir = work_dir / "mesh"
        _run_gmsh_script_in_process(script, mesh_dir)
        msh_path = mesh_dir / "model.msh"
        assert msh_path.exists()

        # ── 2. Convert & validate ──────────────────────────────────────
        vtu_file = mesh_dir / "model.vtu"
        _convert_msh_to_vtu_gmsh(msh_path, vtu_file)
        vtu_path = str(vtu_file)
        assert vtu_file.exists()

        quality = validate_mesh_quality(vtu_path)
        assert "error" not in quality
        assert quality["num_cells"] > 0

        # ── 3. Render mesh ─────────────────────────────────────────────
        render = render_mesh_to_image(vtu_path)
        assert "error" not in render
        png = base64.b64decode(render["image_base64"])
        assert png[:4] == b"\x89PNG"

        # Save the rendered image to disk for inspection
        image_path = work_dir / "results" / "mesh_render.png"
        image_path.write_bytes(png)
        assert image_path.stat().st_size > 100

        # ── 4. Build driven config ─────────────────────────────────────
        materials = [
            {"Attributes": [1], "Permittivity": 4.4},
            {"Attributes": [2], "Permittivity": 1.0},
        ]
        boundaries = {
            "PEC": {"Attributes": [3]},
            "LumpedPort": [
                {
                    "Index": 1,
                    "Attributes": [4],
                    "R": 50.0,
                    "Direction": "+Z",
                    "Excitation": True,
                    "Active": True,
                }
            ],
        }
        config = build_config(
            problem_type="Driven",
            mesh_file="../mesh/model.msh",
            materials=materials,
            boundaries=boundaries,
            solver={
                "Driven": {
                    "MinFreq": 2e9,
                    "MaxFreq": 4e9,
                    "FreqStep": 100e6,
                },
            },
        )
        assert config["Problem"]["Type"] == "Driven"
        assert config["Solver"]["Driven"]["MinFreq"] == 2e9

        config_path = work_dir / "config" / "palace.json"
        write_config(config, config_path)
        assert config_path.exists()

        # ── 5. Synthetic results & energy plot ─────────────────────────
        results_dir = work_dir / "results"
        _write_synthetic_driven_csvs(results_dir, num_steps=20)

        parsed = parse_results(results_dir, problem_type="Driven")
        assert len(parsed.domain_energies) == 20

        energy_path = str(results_dir / "field_energy.html")
        plot = generate_field_energy_plot(
            parsed.domain_energies, output_path=energy_path
        )
        assert plot["plot_type"] == "field_energy"
        assert Path(energy_path).exists()
        assert "plotly" in Path(energy_path).read_text(encoding="utf-8").lower()
