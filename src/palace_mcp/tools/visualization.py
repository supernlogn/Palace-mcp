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


def generate_radiation_pattern_plot(
    far_field: list[dict[str, Any]],
    output_path: str | None = None,
    plot_style: str = "polar",
) -> dict[str, Any]:
    """Generate a radiation pattern plot from far-field data.

    Args:
        far_field: List of dicts with theta/phi/gain (or similar) keys.
        output_path: Optional path to save interactive HTML.
        plot_style: 'polar' for 2-D polar cut, '3d' for 3-D surface.

    Returns base64 PNG (polar) or interactive HTML (3d).
    """
    import math

    import plotly.graph_objects as go

    if not far_field:
        return {"error": "No far-field data to plot"}

    sample = far_field[0]
    theta_key = _find_viz_key(sample, ("theta",))
    phi_key = _find_viz_key(sample, ("phi",))
    gain_key = _find_viz_key(sample, ("gain", "directivity", "power", "e_total", "etotal"))

    if gain_key is None:
        return {"error": "Cannot identify gain column in far-field data"}

    if plot_style == "3d":
        return _radiation_pattern_3d(far_field, theta_key, phi_key, gain_key, output_path)

    # ---- 2-D polar plot (phi = 0 cut and phi = 90 cut) ----
    cuts: dict[str, list[tuple[float, float]]] = {"phi=0": [], "phi=90": []}

    for row in far_field:
        theta = float(row.get(theta_key, 0)) if theta_key else 0.0
        phi = float(row.get(phi_key, 0)) if phi_key else 0.0
        gain = float(row.get(gain_key, 0))

        if abs(phi) < 1.0 or abs(phi - 360) < 1.0:
            cuts["phi=0"].append((theta, gain))
        if abs(phi - 90) < 1.0:
            cuts["phi=90"].append((theta, gain))

    # Fall back to all data if no clear cut could be extracted
    if not cuts["phi=0"] and not cuts["phi=90"]:
        cuts = {"all": [(float(row.get(theta_key, 0)) if theta_key else i, float(row.get(gain_key, 0)))
                        for i, row in enumerate(far_field)]}

    fig = go.Figure()
    for label, points in cuts.items():
        if not points:
            continue
        points.sort()
        thetas = [p[0] for p in points]
        gains = [p[1] for p in points]
        fig.add_trace(go.Scatterpolar(
            r=gains,
            theta=thetas,
            mode="lines",
            name=label,
        ))

    fig.update_layout(
        title="Radiation Pattern",
        polar=dict(radialaxis=dict(title="Gain")),
        template="plotly_dark",
    )

    result: dict[str, Any] = {"plot_type": "radiation_pattern"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result


def _radiation_pattern_3d(
    far_field: list[dict[str, Any]],
    theta_key: str | None,
    phi_key: str | None,
    gain_key: str,
    output_path: str | None,
) -> dict[str, Any]:
    """Render a 3-D radiation pattern surface."""
    import math

    import numpy as np
    import plotly.graph_objects as go

    thetas = []
    phis = []
    gains = []

    for row in far_field:
        theta = math.radians(float(row.get(theta_key, 0)) if theta_key else 0.0)
        phi = math.radians(float(row.get(phi_key, 0)) if phi_key else 0.0)
        gain = max(float(row.get(gain_key, 0)), 1e-10)
        thetas.append(theta)
        phis.append(phi)
        gains.append(gain)

    # Convert spherical → Cartesian with r = gain
    x = [g * math.sin(t) * math.cos(p) for g, t, p in zip(gains, thetas, phis)]
    y = [g * math.sin(t) * math.sin(p) for g, t, p in zip(gains, thetas, phis)]
    z = [g * math.cos(t) for g, t in zip(gains, thetas)]

    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z,
        mode="markers",
        marker=dict(size=3, color=gains, colorscale="Jet", colorbar=dict(title="Gain")),
    )])
    fig.update_layout(
        title="3-D Radiation Pattern",
        scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z"),
        template="plotly_dark",
    )

    result: dict[str, Any] = {"plot_type": "radiation_pattern_3d"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result


def generate_impedance_plot(
    impedances: list[dict[str, Any]],
    target_z: float = 50.0,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Plot port impedance vs frequency with a target impedance reference line.

    Args:
        impedances: List of dicts from result_parser._compute_impedances.
        target_z: Target impedance in ohms (plotted as reference).
        output_path: Optional file to save plot.
    """
    import plotly.graph_objects as go

    if not impedances:
        return {"error": "No impedance data to plot"}

    fig = go.Figure()

    freqs = [z.get("frequency_hz", 0) for z in impedances]
    freq_ghz = [f / 1e9 for f in freqs]

    # Discover port keys (Z_*_mag)
    z_keys = sorted({k for z in impedances for k in z if k.endswith("_mag")})

    for key in z_keys:
        values = [z.get(key, 0) for z in impedances]
        fig.add_trace(go.Scatter(
            x=freq_ghz, y=values, mode="lines", name=key.replace("_mag", ""),
        ))

    # Reference line
    fig.add_hline(y=target_z, line_dash="dash", line_color="red",
                  annotation_text=f"Target {target_z} Ω")

    fig.update_layout(
        title="Port Impedance vs Frequency",
        xaxis_title="Frequency (GHz)",
        yaxis_title="|Z| (Ω)",
        template="plotly_dark",
    )

    result: dict[str, Any] = {"plot_type": "impedance"}
    if output_path:
        fig.write_html(output_path)
        result["file"] = output_path
    else:
        result["html"] = fig.to_html(include_plotlyjs="cdn")

    return result


def _find_viz_key(
    sample: dict[str, Any], candidates: tuple[str, ...]
) -> str | None:
    """Find the first key in *sample* whose lowercase form contains a candidate."""
    for key in sample:
        kl = key.strip().lower()
        for c in candidates:
            if c in kl:
                return key
    return None
