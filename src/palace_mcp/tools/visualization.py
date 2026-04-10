"""Visualization tools using VTK and Plotly."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any


def render_mesh_to_image(
    mesh_path: str,
    width: int = 800,
    height: int = 600,
    scalar_field: str | None = None,
) -> dict[str, Any]:
    """Render a mesh to a PNG image using VTK offscreen rendering.

    Returns base64-encoded PNG data.
    """
    import vtk

    # Read mesh
    ext = Path(mesh_path).suffix.lower()
    if ext == ".vtu":
        reader = vtk.vtkXMLUnstructuredGridReader()
    elif ext == ".pvd":
        reader = vtk.vtkPVDReader()
    elif ext == ".vtk":
        reader = vtk.vtkUnstructuredGridReader()
    else:
        return {"error": f"Unsupported format: {ext}"}

    reader.SetFileName(mesh_path)
    reader.Update()

    data = reader.GetOutput()
    if data is None:
        return {"error": "Failed to read mesh file"}

    # Create mapper and actor
    if hasattr(data, "GetBlock"):
        # Multi-block dataset (PVD)
        mapper = vtk.vtkCompositePolyDataMapper()
        geo_filter = vtk.vtkCompositeDataGeometryFilter()
        geo_filter.SetInputData(data)
        geo_filter.Update()
        mapper.SetInputConnection(geo_filter.GetOutputPort())
    else:
        geometry_filter = vtk.vtkGeometryFilter()
        geometry_filter.SetInputData(data)
        geometry_filter.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(geometry_filter.GetOutputPort())

    if scalar_field and data.GetPointData().GetArray(scalar_field):
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray(scalar_field)
        arr = data.GetPointData().GetArray(scalar_field)
        mapper.SetScalarRange(arr.GetRange())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    # Renderer
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(0.1, 0.1, 0.1)
    renderer.ResetCamera()

    # Offscreen render window
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.SetSize(width, height)
    render_window.AddRenderer(renderer)
    render_window.Render()

    # Capture to PNG
    window_to_image = vtk.vtkWindowToImageFilter()
    window_to_image.SetInput(render_window)
    window_to_image.Update()

    writer = vtk.vtkPNGWriter()
    writer.WriteToMemoryOn()
    writer.SetInputConnection(window_to_image.GetOutputPort())
    writer.Write()

    png_data = bytes(writer.GetResult())
    b64_data = base64.b64encode(png_data).decode("ascii")

    return {
        "image_base64": b64_data,
        "width": width,
        "height": height,
        "format": "png",
    }


def list_fields_in_result(result_dir: str) -> dict[str, Any]:
    """List available scalar/vector fields in Palace VTU output files."""
    import vtk

    paraview_dir = Path(result_dir) / "paraview"
    if not paraview_dir.is_dir():
        paraview_dir = Path(result_dir)

    vtu_files = list(paraview_dir.glob("*.vtu"))
    pvd_files = list(paraview_dir.glob("*.pvd"))

    fields: dict[str, list[str]] = {"point_data": [], "cell_data": []}
    files_found: list[str] = []

    for vtu_file in vtu_files[:5]:  # Sample first few
        files_found.append(str(vtu_file.name))
        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(str(vtu_file))
        reader.Update()
        data = reader.GetOutput()
        if data:
            for i in range(data.GetPointData().GetNumberOfArrays()):
                name = data.GetPointData().GetArrayName(i)
                if name not in fields["point_data"]:
                    fields["point_data"].append(name)
            for i in range(data.GetCellData().GetNumberOfArrays()):
                name = data.GetCellData().GetArrayName(i)
                if name not in fields["cell_data"]:
                    fields["cell_data"].append(name)

    return {
        "files": files_found,
        "pvd_files": [f.name for f in pvd_files],
        "fields": fields,
    }


def generate_s_parameter_plot(
    s_params: list[dict[str, Any]],
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate S-parameter plot using Plotly."""
    import plotly.graph_objects as go

    fig = go.Figure()

    freqs = [sp.get("frequency_hz", 0) for sp in s_params]
    freq_ghz = [f / 1e9 for f in freqs]

    # Find all S-parameter columns
    s_keys = set()
    for sp in s_params:
        for key in sp:
            if key.startswith("V_") or key.startswith("S"):
                s_keys.add(key)

    for key in sorted(s_keys):
        values = [sp.get(key, 0) for sp in s_params]
        fig.add_trace(go.Scatter(
            x=freq_ghz,
            y=values,
            mode="lines",
            name=key,
        ))

    fig.update_layout(
        title="S-Parameters",
        xaxis_title="Frequency (GHz)",
        yaxis_title="Magnitude (dB)",
        template="plotly_dark",
    )

    result: dict[str, Any] = {"plot_type": "s_parameters"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result


def generate_eigenmode_plot(
    eigenfrequencies: list[dict[str, Any]],
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate eigenmode spectrum plot."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Eigenfrequencies", "Quality Factors"))

    freqs = [ef.get("frequency_hz", 0) / 1e9 for ef in eigenfrequencies]
    modes = list(range(1, len(freqs) + 1))
    q_factors = [ef.get("quality_factor", 0) for ef in eigenfrequencies]

    fig.add_trace(
        go.Bar(x=modes, y=freqs, name="Frequency"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=modes, y=q_factors, name="Q Factor"),
        row=1, col=2,
    )

    fig.update_xaxes(title_text="Mode", row=1, col=1)
    fig.update_yaxes(title_text="Frequency (GHz)", row=1, col=1)
    fig.update_xaxes(title_text="Mode", row=1, col=2)
    fig.update_yaxes(title_text="Quality Factor", row=1, col=2)
    fig.update_layout(template="plotly_dark")

    result: dict[str, Any] = {"plot_type": "eigenmode"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result


def generate_field_energy_plot(
    domain_energies: list[dict[str, Any]],
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate energy vs. step plot for any problem type."""
    import plotly.graph_objects as go

    fig = go.Figure()

    steps = list(range(len(domain_energies)))

    for key in domain_energies[0] if domain_energies else []:
        try:
            values = [float(de.get(key, 0)) for de in domain_energies]
            fig.add_trace(go.Scatter(
                x=steps,
                y=values,
                mode="lines",
                name=key,
            ))
        except (ValueError, TypeError):
            pass

    fig.update_layout(
        title="Field Energies",
        xaxis_title="Step",
        yaxis_title="Energy (J)",
        template="plotly_dark",
    )

    result: dict[str, Any] = {"plot_type": "field_energy"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result


def generate_comparison_plot(
    datasets: list[dict[str, Any]],
    labels: list[str],
    x_key: str,
    y_key: str,
    title: str = "Comparison",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate overlay comparison plot of multiple datasets."""
    import plotly.graph_objects as go

    fig = go.Figure()

    for data, label in zip(datasets, labels):
        x_values = data.get(x_key, [])
        y_values = data.get(y_key, [])
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines+markers",
            name=label,
        ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
    )

    result: dict[str, Any] = {"plot_type": "comparison"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result
