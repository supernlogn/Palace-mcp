"""Mesh generation, quality validation, and export tools using VTK."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def run_geometry_script(
    script_content: str,
    output_dir: Path,
    timeout: int = 300,
) -> dict[str, Any]:
    """Execute a user-provided Python geometry script in a subprocess.

    The script is expected to use VTK or gmsh to generate mesh files in output_dir.
    The output_dir path is passed to the script via the PALACE_MESH_OUTPUT_DIR
    environment variable.
    """
    import os

    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=str(output_dir)
    ) as f:
        f.write(script_content)
        script_path = f.name

    try:
        env = os.environ.copy()
        env["PALACE_MESH_OUTPUT_DIR"] = str(output_dir)

        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(output_dir),
            env=env,
        )

        output_files = [
            str(p.relative_to(output_dir))
            for p in output_dir.rglob("*")
            if p.is_file() and p.name != Path(script_path).name
        ]

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:5000],
            "output_files": output_files,
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Script timed out after {timeout} seconds",
            "output_files": [],
            "return_code": -1,
        }
    finally:
        Path(script_path).unlink(missing_ok=True)


def validate_mesh_quality(mesh_path: str) -> dict[str, Any]:
    """Validate mesh quality using VTK's mesh quality filter.

    Computes aspect ratio, skewness, and element size statistics.
    """
    import vtk

    # Determine reader based on extension
    ext = Path(mesh_path).suffix.lower()
    if ext == ".vtu":
        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(mesh_path)
    elif ext in (".vtk",):
        reader = vtk.vtkUnstructuredGridReader()
        reader.SetFileName(mesh_path)
    elif ext == ".msh":
        # Use gmsh to convert, then read
        return _validate_gmsh_mesh(mesh_path)
    else:
        return {"error": f"Unsupported mesh format: {ext}"}

    reader.Update()
    mesh = reader.GetOutput()

    if mesh is None or mesh.GetNumberOfCells() == 0:
        return {"error": "Failed to read mesh or mesh is empty"}

    # Compute quality metrics
    quality_filter = vtk.vtkMeshQuality()
    quality_filter.SetInputData(mesh)

    metrics = {}

    # Aspect ratio
    quality_filter.SetTetQualityMeasureToAspectRatio()
    quality_filter.SetTriangleQualityMeasureToAspectRatio()
    quality_filter.Update()
    quality_data = quality_filter.GetOutput()
    quality_array = quality_data.GetCellData().GetArray("Quality")

    if quality_array:
        values = [quality_array.GetValue(i) for i in range(quality_array.GetNumberOfTuples())]
        arr = np.array(values)
        metrics["aspect_ratio"] = {
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
        }

    # Skewness
    quality_filter.SetTetQualityMeasureToSkew()
    quality_filter.SetTriangleQualityMeasureToMaxAngle()
    quality_filter.Update()
    quality_data = quality_filter.GetOutput()
    quality_array = quality_data.GetCellData().GetArray("Quality")

    if quality_array:
        values = [quality_array.GetValue(i) for i in range(quality_array.GetNumberOfTuples())]
        arr = np.array(values)
        metrics["skewness"] = {
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
        }

    # Warnings
    warnings = []
    if "aspect_ratio" in metrics and metrics["aspect_ratio"]["max"] > 10:
        warnings.append(
            f"High aspect ratio detected (max={metrics['aspect_ratio']['max']:.2f}). "
            "Consider refining the mesh in regions with elongated elements."
        )
    if "skewness" in metrics and metrics["skewness"]["max"] > 0.9:
        warnings.append(
            f"High skewness detected (max={metrics['skewness']['max']:.2f}). "
            "Consider improving mesh quality in skewed regions."
        )

    return {
        "num_cells": mesh.GetNumberOfCells(),
        "num_points": mesh.GetNumberOfPoints(),
        "bounds": list(mesh.GetBounds()),
        "quality_metrics": metrics,
        "warnings": warnings,
        "valid": len(warnings) == 0,
    }


def _validate_gmsh_mesh(mesh_path: str) -> dict[str, Any]:
    """Validate a Gmsh .msh mesh using gmsh Python API."""
    try:
        import gmsh
    except ImportError:
        return {"error": "gmsh Python package not installed"}

    gmsh.initialize()
    try:
        gmsh.open(mesh_path)

        # Get mesh statistics
        node_tags, _, _ = gmsh.model.mesh.getNodes()
        element_types, element_tags, _ = gmsh.model.mesh.getElements()

        total_elements = sum(len(tags) for tags in element_tags)

        # Get quality metrics from gmsh
        qualities = []
        warnings = []
        for dim in range(1, 4):
            for etype in element_types:
                try:
                    q = gmsh.model.mesh.getElementQualities(
                        list(element_tags[0]) if element_tags else [], "minSICN"
                    )
                    qualities.extend(q)
                except Exception:
                    pass

        metrics = {}
        if qualities:
            arr = np.array(qualities)
            metrics["quality_sicn"] = {
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "mean": float(np.mean(arr)),
            }
            if np.min(arr) < 0.1:
                warnings.append(
                    f"Low element quality detected (min SICN={np.min(arr):.4f}). "
                    "Consider remeshing with refined size fields."
                )

        return {
            "num_nodes": len(node_tags),
            "num_elements": total_elements,
            "quality_metrics": metrics,
            "warnings": warnings,
            "valid": len(warnings) == 0,
        }
    finally:
        gmsh.finalize()


def get_mesh_info(mesh_path: str) -> dict[str, Any]:
    """Get basic information about a mesh file."""
    import vtk

    ext = Path(mesh_path).suffix.lower()
    if ext == ".vtu":
        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(mesh_path)
    elif ext in (".vtk",):
        reader = vtk.vtkUnstructuredGridReader()
        reader.SetFileName(mesh_path)
    elif ext == ".msh":
        return _get_gmsh_info(mesh_path)
    else:
        return {"error": f"Unsupported format: {ext}"}

    reader.Update()
    mesh = reader.GetOutput()

    if mesh is None:
        return {"error": "Failed to read mesh"}

    bounds = mesh.GetBounds()
    cell_types: dict[str, int] = {}
    for i in range(mesh.GetNumberOfCells()):
        ctype = mesh.GetCell(i).GetClassName()
        cell_types[ctype] = cell_types.get(ctype, 0) + 1

    return {
        "num_points": mesh.GetNumberOfPoints(),
        "num_cells": mesh.GetNumberOfCells(),
        "bounds": {
            "x": [bounds[0], bounds[1]],
            "y": [bounds[2], bounds[3]],
            "z": [bounds[4], bounds[5]],
        },
        "cell_types": cell_types,
        "point_data_arrays": [
            mesh.GetPointData().GetArrayName(i)
            for i in range(mesh.GetPointData().GetNumberOfArrays())
        ],
        "cell_data_arrays": [
            mesh.GetCellData().GetArrayName(i)
            for i in range(mesh.GetCellData().GetNumberOfArrays())
        ],
    }


def _get_gmsh_info(mesh_path: str) -> dict[str, Any]:
    """Get info from a Gmsh mesh file."""
    try:
        import gmsh
    except ImportError:
        return {"error": "gmsh not installed"}

    gmsh.initialize()
    try:
        gmsh.open(mesh_path)
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        element_types, element_tags, _ = gmsh.model.mesh.getElements()

        coords_arr = np.array(coords).reshape(-1, 3)
        total_elements = sum(len(tags) for tags in element_tags)

        # Get physical groups
        groups = []
        for dim in range(4):
            for tag in gmsh.model.getPhysicalGroups(dim):
                name = gmsh.model.getPhysicalName(tag[0], tag[1])
                groups.append({"dim": tag[0], "tag": tag[1], "name": name})

        return {
            "num_nodes": len(node_tags),
            "num_elements": total_elements,
            "bounds": {
                "x": [float(coords_arr[:, 0].min()), float(coords_arr[:, 0].max())],
                "y": [float(coords_arr[:, 1].min()), float(coords_arr[:, 1].max())],
                "z": [float(coords_arr[:, 2].min()), float(coords_arr[:, 2].max())],
            },
            "physical_groups": groups,
        }
    finally:
        gmsh.finalize()


def convert_mesh(
    input_path: str,
    output_path: str,
) -> dict[str, Any]:
    """Convert a mesh between formats using VTK or Gmsh."""
    in_ext = Path(input_path).suffix.lower()
    out_ext = Path(output_path).suffix.lower()

    if in_ext == ".msh" and out_ext == ".vtu":
        return _convert_gmsh_to_vtu(input_path, output_path)
    elif in_ext == ".vtu" and out_ext == ".vtk":
        return _convert_vtu_to_vtk(input_path, output_path)
    else:
        return {"error": f"Conversion from {in_ext} to {out_ext} not supported"}


def _convert_gmsh_to_vtu(input_path: str, output_path: str) -> dict[str, Any]:
    """Convert Gmsh .msh to VTK .vtu."""
    try:
        import gmsh
    except ImportError:
        return {"error": "gmsh not installed"}

    import vtk

    gmsh.initialize()
    try:
        gmsh.open(input_path)
        # Export as msh4, then read with VTK
        temp_path = str(Path(output_path).with_suffix(".msh"))
        gmsh.write(temp_path)

        reader = vtk.vtkGmshReader()
        reader.SetFileName(temp_path)
        reader.Update()

        writer = vtk.vtkXMLUnstructuredGridWriter()
        writer.SetFileName(output_path)
        writer.SetInputData(reader.GetOutput())
        writer.Write()

        return {"success": True, "output": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        gmsh.finalize()


def _convert_vtu_to_vtk(input_path: str, output_path: str) -> dict[str, Any]:
    """Convert VTU to legacy VTK format."""
    import vtk

    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(input_path)
    reader.Update()

    writer = vtk.vtkUnstructuredGridWriter()
    writer.SetFileName(output_path)
    writer.SetInputData(reader.GetOutput())
    writer.Write()

    return {"success": True, "output": output_path}
