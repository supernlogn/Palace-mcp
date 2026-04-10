"""Palace MCP Server — main entry point.

Exposes all Palace simulation tools over Streamable HTTP transport.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from palace_mcp.config import ServerConfig
from palace_mcp.palace import PalaceRunner, SimulationStatus
from palace_mcp.palace.config_builder import build_config, load_config, write_config
from palace_mcp.palace.config_builder import (
    build_farfield_boundaries,
    build_phased_array_ports,
    verify_impedance_match,
)
from palace_mcp.palace.result_parser import parse_palace_error, parse_results
from palace_mcp.palace.validator import validate_config, validate_config_file
from palace_mcp.tools import docs as docs_tools
from palace_mcp.tools import materials as mat_tools
from palace_mcp.tools import mesh as mesh_tools
from palace_mcp.tools import project as proj_tools
from palace_mcp.tools import templates as tpl_tools
from palace_mcp.tools import visualization as viz_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Globals initialised in main()
# ---------------------------------------------------------------------------
_cfg = ServerConfig()
_runner = PalaceRunner(_cfg.palace_binary, _cfg.max_cores)
_docs_index = docs_tools.DocsIndex(_cfg.docs_dir)

mcp = FastMCP(
    "Palace MCP Server",
    instructions=(
        "MCP server for building and running AWS Palace electromagnetic "
        "simulations. Provides tools for project management, mesh generation, "
        "material selection, simulation execution, result analysis, and "
        "visualization."
    ),
)


# ============================================================================
# Resources — Palace & VTK documentation
# ============================================================================

_PALACE_DOCS_DIR = Path(__file__).parent / "data" / "docs"
_VTK_DOCS_DIR = Path(__file__).parent / "data" / "vtk_docs"


def _register_doc_resources() -> None:
    """Register every bundled doc file as an MCP resource."""
    for docs_dir, uri_prefix, label in [
        (_PALACE_DOCS_DIR, "palace-docs", "Palace"),
        (_VTK_DOCS_DIR, "vtk-docs", "VTK"),
    ]:
        if not docs_dir.is_dir():
            continue
        for md_file in sorted(docs_dir.rglob("*.md")):
            rel = md_file.relative_to(docs_dir).as_posix()
            uri = f"docs://{uri_prefix}/{rel}"
            # Extract first heading as title
            title = rel
            try:
                text = md_file.read_text(encoding="utf-8", errors="replace")
                for line in text.splitlines():
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
            except OSError:
                text = ""

            # Capture text in closure
            _content = text

            def _make_reader(content: str) -> Any:
                def _read() -> str:
                    return content
                return _read

            mcp.resource(
                uri,
                name=f"{label}: {title}",
                description=f"{label} documentation — {rel}",
                mime_type="text/markdown",
            )(_make_reader(_content))


_register_doc_resources()


# ============================================================================
# 1. Project Management
# ============================================================================


@mcp.tool()
def create_project(
    name: str,
    description: str = "",
    palace_version: str = "",
) -> dict[str, Any]:
    """Create a new simulation project with standard directory structure."""
    _cfg.ensure_dirs()
    return proj_tools.create_project(
        _cfg.projects_dir, name, description, palace_version
    )


@mcp.tool()
def list_projects() -> list[dict[str, Any]]:
    """List all simulation projects."""
    _cfg.ensure_dirs()
    return proj_tools.list_projects(_cfg.projects_dir)


@mcp.tool()
def get_project(name: str) -> dict[str, Any]:
    """Get project details including manifest and file listing."""
    return proj_tools.get_project(_cfg.projects_dir, name)


@mcp.tool()
def get_project_file(project_name: str, relative_path: str) -> str:
    """Download/read a file from a project. Returns file content as text or base64."""
    path = proj_tools.get_file(_cfg.projects_dir, project_name, relative_path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return base64.b64encode(path.read_bytes()).decode("ascii")


# ============================================================================
# 2. Materials
# ============================================================================


@mcp.tool()
def list_materials() -> list[dict[str, Any]]:
    """List all materials in the built-in database."""
    return mat_tools.list_materials()


@mcp.tool()
def get_material(material_id: str) -> dict[str, Any]:
    """Get a specific material by ID with all Palace-compatible properties."""
    return mat_tools.get_material(material_id)


@mcp.tool()
def search_materials(query: str) -> list[dict[str, Any]]:
    """Search the materials database by name or keyword."""
    return mat_tools.search_materials(query)


@mcp.tool()
def add_material(
    material_id: str,
    name: str,
    permittivity: float = 1.0,
    permeability: float = 1.0,
    loss_tan: float = 0.0,
    conductivity: float = 0.0,
    london_depth: float | None = None,
) -> dict[str, Any]:
    """Add a custom material to the database."""
    return mat_tools.add_material(
        material_id, name, permittivity, permeability,
        loss_tan, conductivity, london_depth
    )


@mcp.tool()
def material_to_palace_config(
    material_id: str, attributes: list[int]
) -> dict[str, Any]:
    """Convert a material from the database to a Palace config entry."""
    return mat_tools.material_to_palace_config(material_id, attributes)


# ============================================================================
# 3. Geometry & Mesh
# ============================================================================


@mcp.tool()
def list_geometry_templates() -> list[dict[str, Any]]:
    """List all available parameterized geometry templates."""
    return tpl_tools.list_templates()


@mcp.tool()
def get_geometry_template(template_id: str) -> dict[str, Any]:
    """Get details for a specific geometry template including parameters."""
    return tpl_tools.get_template(template_id)


@mcp.tool()
def generate_geometry_script(
    template_id: str, parameters: dict[str, float] | None = None
) -> str:
    """Generate a Python/Gmsh script from a geometry template.

    Returns the script content which can be executed with run_geometry_script.
    """
    return tpl_tools.generate_template_script(template_id, parameters)


@mcp.tool()
def run_geometry_script(
    project_name: str, script_content: str
) -> dict[str, Any]:
    """Execute a Python geometry script to generate mesh files.

    The script runs in a subprocess with PALACE_MESH_OUTPUT_DIR set to
    the project's mesh/ directory. Use Gmsh or VTK to create meshes.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    mesh_dir = project_dir / "mesh"
    return mesh_tools.run_geometry_script(
        script_content, mesh_dir, timeout=_cfg.script_timeout
    )


@mcp.tool()
def validate_mesh(project_name: str, mesh_file: str) -> dict[str, Any]:
    """Validate mesh quality (aspect ratio, skewness, element sizes)."""
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    mesh_path = (project_dir / "mesh" / mesh_file).resolve()
    if not str(mesh_path).startswith(str(project_dir.resolve())):
        return {"error": "Path traversal detected"}
    return mesh_tools.validate_mesh_quality(str(mesh_path))


@mcp.tool()
def get_mesh_info(project_name: str, mesh_file: str) -> dict[str, Any]:
    """Get information about a mesh file (bounds, cell count, etc.)."""
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    mesh_path = project_dir / "mesh" / mesh_file
    return mesh_tools.get_mesh_info(str(mesh_path))


@mcp.tool()
def convert_mesh(
    project_name: str, input_file: str, output_file: str
) -> dict[str, Any]:
    """Convert a mesh between formats (e.g. .msh to .vtu)."""
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    in_path = project_dir / "mesh" / input_file
    out_path = project_dir / "mesh" / output_file
    return mesh_tools.convert_mesh(str(in_path), str(out_path))


# ============================================================================
# 4. Palace Configuration
# ============================================================================


@mcp.tool()
def list_problem_types() -> list[dict[str, str]]:
    """List all Palace problem types with descriptions."""
    return [
        {
            "type": "Eigenmode",
            "description": "Compute electromagnetic eigenmodes (resonant frequencies, Q-factors, EPRs).",
        },
        {
            "type": "Driven",
            "description": "Frequency domain driven simulation with port excitations (S-parameters).",
        },
        {
            "type": "Transient",
            "description": "Time domain electromagnetic simulation.",
        },
        {
            "type": "Electrostatic",
            "description": "Solve for electrostatic fields and extract capacitance matrices.",
        },
        {
            "type": "Magnetostatic",
            "description": "Solve for magnetostatic fields and extract inductance matrices.",
        },
    ]


@mcp.tool()
def get_problem_template(problem_type: str) -> dict[str, Any]:
    """Get a starter Palace JSON config template for a problem type."""
    template_file = (
        Path(__file__).parent / "data" / "templates" / f"{problem_type.lower()}.json"
    )
    if not template_file.is_file():
        return {"error": f"No template for problem type: {problem_type}"}
    return json.loads(template_file.read_text())


@mcp.tool()
def create_palace_config(
    project_name: str,
    problem_type: str,
    mesh_file: str,
    materials: list[dict[str, Any]],
    boundaries: dict[str, Any] | None = None,
    solver: dict[str, Any] | None = None,
    config_name: str = "palace.json",
) -> dict[str, Any]:
    """Build and save a Palace JSON configuration file for a project."""
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    config = build_config(
        problem_type=problem_type,
        mesh_file=f"../mesh/{mesh_file}",
        materials=materials,
        boundaries=boundaries,
        solver=solver,
    )
    config_path = project_dir / "config" / config_name
    write_config(config, config_path)
    return {
        "config_path": str(config_path),
        "config": config,
    }


@mcp.tool()
def validate_palace_config(
    project_name: str, config_file: str = "palace.json"
) -> dict[str, Any]:
    """Validate a Palace JSON configuration file.

    Checks mesh existence, material attributes, boundary conditions, and
    solver settings. Returns structured errors and warnings.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    config_path = project_dir / "config" / config_file
    result = validate_config_file(config_path)
    return result.to_dict()


# ============================================================================
# 5. Simulation Lifecycle
# ============================================================================


@mcp.tool()
async def run_simulation(
    project_name: str,
    config_file: str = "palace.json",
    num_procs: int = 1,
) -> dict[str, Any]:
    """Launch a Palace simulation for a project.

    Returns a run_id for tracking progress. The simulation runs asynchronously.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    config_path = project_dir / "config" / config_file
    output_dir = project_dir / "results"

    # Validate first
    validation = validate_config_file(config_path)
    if not validation.valid:
        return {
            "error": "Configuration validation failed",
            "validation": validation.to_dict(),
        }

    run_id = str(uuid.uuid4())[:8]

    # Register in manifest
    proj_tools.add_run_to_manifest(project_dir, run_id, config_file)

    run = await _runner.start_simulation(
        run_id=run_id,
        config_path=config_path,
        output_dir=output_dir,
        num_procs=num_procs,
        timeout=_cfg.simulation_timeout,
    )

    return {
        "run_id": run_id,
        "status": run.progress.status.value,
        "message": f"Simulation started. Use get_simulation_status('{run_id}') to track progress.",
    }


@mcp.tool()
def get_simulation_status(run_id: str) -> dict[str, Any]:
    """Get the current status and progress of a running simulation."""
    progress = _runner.get_status(run_id)
    if progress is None:
        return {"error": f"No simulation found with run_id '{run_id}'"}
    return {
        "run_id": run_id,
        "status": progress.status.value,
        "progress_pct": round(progress.progress_pct, 1),
        "elapsed_seconds": round(progress.elapsed_seconds, 1),
        "eta_seconds": round(progress.eta_seconds, 1) if progress.eta_seconds else None,
        "current_step": progress.current_step,
        "total_steps": progress.total_steps,
        "return_code": progress.return_code,
        "error_message": progress.error_message,
        "log_tail": progress.log_tail[-20:],
    }


@mcp.tool()
async def cancel_simulation(run_id: str) -> dict[str, Any]:
    """Cancel a running simulation."""
    success = await _runner.cancel_simulation(run_id)
    return {"cancelled": success}


@mcp.tool()
def get_simulation_results(
    project_name: str, problem_type: str = ""
) -> dict[str, Any]:
    """Parse and return structured simulation results for a project.

    Automatically parses Palace CSV output files and returns summaries
    appropriate to the problem type (S-parameters, eigenfrequencies, etc.).
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    results_dir = project_dir / "results"
    results = parse_results(results_dir, problem_type)
    return results.to_dict()


@mcp.tool()
def diagnose_simulation_failure(run_id: str) -> dict[str, Any]:
    """Get actionable diagnostics for a failed simulation.

    Parses Palace error output and suggests fixes.
    """
    run = _runner.runs.get(run_id)
    if run is None:
        return {"error": f"No simulation found with run_id '{run_id}'"}

    if run.progress.status != SimulationStatus.FAILED:
        return {"message": "Simulation has not failed", "status": run.progress.status.value}

    stderr = "\n".join(run._log_lines[-100:])
    diagnostics = parse_palace_error(stderr)
    diagnostics["run_id"] = run_id
    diagnostics["return_code"] = run.progress.return_code
    return diagnostics


# ============================================================================
# 6. Documentation
# ============================================================================


@mcp.tool()
def search_palace_docs(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search Palace documentation for a query.

    Returns relevant documentation snippets matching the search terms.
    """
    results = _docs_index.search(query, max_results)
    return [r.to_dict() for r in results]


@mcp.tool()
def list_palace_doc_topics() -> list[dict[str, str]]:
    """List all available Palace documentation topics."""
    return _docs_index.list_topics()


@mcp.tool()
def get_palace_doc(file_path: str) -> dict[str, Any]:
    """Get the full content of a Palace documentation page."""
    content = _docs_index.get_document(file_path)
    if content is None:
        return {"error": f"Document not found: {file_path}"}
    return {"file": file_path, "content": content}


# ============================================================================
# 7. Visualization
# ============================================================================


@mcp.tool()
def render_mesh_image(
    project_name: str,
    mesh_file: str,
    scalar_field: str | None = None,
    width: int = 800,
    height: int = 600,
) -> dict[str, Any]:
    """Render a mesh or simulation result to a PNG image.

    Returns base64-encoded PNG. Supports VTU, VTK, and PVD files.
    The file is looked up in the project's mesh/ or results/paraview/ directory.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)

    # Search in mesh/ first, then results/paraview/
    for subdir in ("mesh", "results/paraview", "results"):
        candidate = project_dir / subdir / mesh_file
        if candidate.is_file():
            return viz_tools.render_mesh_to_image(
                str(candidate), width, height, scalar_field
            )

    return {"error": f"File not found: {mesh_file}"}


@mcp.tool()
def list_result_fields(project_name: str) -> dict[str, Any]:
    """List available visualization fields in simulation results."""
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    return viz_tools.list_fields_in_result(str(project_dir / "results"))


@mcp.tool()
def generate_plot(
    project_name: str,
    plot_type: str,
    save_to_file: bool = False,
) -> dict[str, Any]:
    """Generate a metric plot from simulation results.

    plot_type: 's_parameters', 'eigenmode', 'field_energy',
               'radiation_pattern', 'radiation_pattern_3d', 'impedance'
    Returns interactive HTML or saves to the project results directory.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    results = parse_results(project_dir / "results")

    output_path = None
    if save_to_file:
        output_path = str(project_dir / "results" / f"{plot_type}_plot.html")

    if plot_type == "s_parameters":
        return viz_tools.generate_s_parameter_plot(results.s_parameters, output_path)
    elif plot_type == "eigenmode":
        return viz_tools.generate_eigenmode_plot(results.eigenfrequencies, output_path)
    elif plot_type == "field_energy":
        return viz_tools.generate_field_energy_plot(results.domain_energies, output_path)
    elif plot_type == "radiation_pattern":
        return viz_tools.generate_radiation_pattern_plot(results.far_field, output_path, "polar")
    elif plot_type == "radiation_pattern_3d":
        return viz_tools.generate_radiation_pattern_plot(results.far_field, output_path, "3d")
    elif plot_type == "impedance":
        return viz_tools.generate_impedance_plot(results.impedances, output_path=output_path)
    else:
        return {
            "error": f"Unknown plot type: {plot_type}. Use: s_parameters, "
            "eigenmode, field_energy, radiation_pattern, radiation_pattern_3d, impedance"
        }


# ============================================================================
# 8. Batch / Parameter Sweeps
# ============================================================================


@mcp.tool()
async def run_parameter_sweep(
    project_name: str,
    config_file: str,
    parameter_path: str,
    values: list[float],
    num_procs: int = 1,
) -> dict[str, Any]:
    """Run a batch of simulations sweeping a single parameter.

    parameter_path: dot-separated path into the Palace config JSON,
                    e.g. 'Solver.Driven.MinFreq' or 'Domains.Materials.0.Permittivity'
    values: list of values to sweep over
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    config_path = project_dir / "config" / config_file
    base_config = load_config(config_path)

    sweep_results: list[dict[str, Any]] = []

    for value in values:
        # Create modified config
        sweep_config = json.loads(json.dumps(base_config))  # deep copy
        _set_nested(sweep_config, parameter_path, value)

        sweep_id = f"sweep_{parameter_path}_{value}"
        sweep_config_name = f"sweep_{len(sweep_results)}.json"
        sweep_config_path = project_dir / "config" / sweep_config_name
        write_config(sweep_config, sweep_config_path)

        run_id = str(uuid.uuid4())[:8]
        proj_tools.add_run_to_manifest(
            project_dir, run_id, sweep_config_name,
            parameters={parameter_path: value},
        )

        sweep_results.append({
            "run_id": run_id,
            "parameter_value": value,
            "config_file": sweep_config_name,
            "status": "queued",
        })

    # Start simulations sequentially
    for sr in sweep_results:
        run = await _runner.start_simulation(
            run_id=sr["run_id"],
            config_path=project_dir / "config" / sr["config_file"],
            output_dir=project_dir / "results" / sr["run_id"],
            num_procs=num_procs,
            timeout=_cfg.simulation_timeout,
        )
        sr["status"] = run.progress.status.value

    return {
        "parameter": parameter_path,
        "num_runs": len(sweep_results),
        "runs": sweep_results,
    }


def _set_nested(d: dict, path: str, value: Any) -> None:
    """Set a value in a nested dict using dot-separated path."""
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        if key.isdigit():
            current = current[int(key)]
        else:
            current = current[key]
    final_key = keys[-1]
    if final_key.isdigit():
        current[int(final_key)] = value
    else:
        current[final_key] = value


# ============================================================================
# 9. Resource Estimation
# ============================================================================


@mcp.tool()
def estimate_resources(
    project_name: str, mesh_file: str, solver_order: int = 2
) -> dict[str, Any]:
    """Estimate memory and CPU requirements for a simulation.

    Based on mesh element count and polynomial order.
    """
    import psutil

    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    mesh_path = project_dir / "mesh" / mesh_file

    info = mesh_tools.get_mesh_info(str(mesh_path))
    if "error" in info:
        return info

    num_cells = info.get("num_cells", info.get("num_elements", 0))
    num_points = info.get("num_points", info.get("num_nodes", 0))

    # Rough estimate: ~100 bytes per DOF per unknown field component
    # With order p, DOFs scale roughly as num_cells * p^3 for 3D
    estimated_dofs = num_cells * (solver_order ** 3)
    # Each DOF needs ~500 bytes for sparse matrix storage (rough)
    estimated_memory_bytes = estimated_dofs * 500
    estimated_memory_gb = estimated_memory_bytes / (1024 ** 3)

    available_memory = psutil.virtual_memory()
    available_gb = available_memory.available / (1024 ** 3)

    warnings = []
    if estimated_memory_gb > available_gb * 0.8:
        warnings.append(
            f"Estimated memory ({estimated_memory_gb:.1f} GB) exceeds 80% of "
            f"available memory ({available_gb:.1f} GB). Consider reducing mesh "
            "density or solver order."
        )
    if _cfg.max_memory_gb > 0 and estimated_memory_gb > _cfg.max_memory_gb:
        warnings.append(
            f"Estimated memory ({estimated_memory_gb:.1f} GB) exceeds configured "
            f"limit ({_cfg.max_memory_gb:.1f} GB)."
        )

    return {
        "num_cells": num_cells,
        "num_points": num_points,
        "solver_order": solver_order,
        "estimated_dofs": estimated_dofs,
        "estimated_memory_gb": round(estimated_memory_gb, 2),
        "available_memory_gb": round(available_gb, 2),
        "cpu_count": psutil.cpu_count(logical=False) or 1,
        "warnings": warnings,
    }


# ============================================================================
# 10. Antenna / Phased-Array Helpers
# ============================================================================


@mcp.tool()
def create_phased_array_config(
    project_name: str,
    mesh_file: str,
    num_ports: int,
    port_attributes: list[int],
    amplitudes: list[float] | None = None,
    phases_deg: list[float] | None = None,
    impedance: float = 50.0,
    direction: str = "+Z",
    freq_min: float = 0.8e9,
    freq_max: float = 1.2e9,
    freq_step: float = 10e6,
    absorbing_attributes: list[int] | None = None,
    config_name: str = "palace.json",
) -> dict[str, Any]:
    """Create a full Palace driven-simulation config for a phased antenna array.

    Combines phased-array lumped-port excitation with absorbing boundary
    conditions and a frequency sweep.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)

    boundaries = build_phased_array_ports(
        num_ports=num_ports,
        port_attributes=port_attributes,
        amplitudes=amplitudes,
        phases_deg=phases_deg,
        impedance=impedance,
        direction=direction,
    )

    if absorbing_attributes:
        ff_bounds = build_farfield_boundaries(absorbing_attributes)
        boundaries.update(ff_bounds)

    materials = [{"Attributes": [1], "Permeability": 1.0, "Permittivity": 1.0}]

    config = build_config(
        problem_type="Driven",
        mesh_file=f"../mesh/{mesh_file}",
        materials=materials,
        boundaries=boundaries,
        solver={
            "Driven": {
                "MinFreq": freq_min,
                "MaxFreq": freq_max,
                "FreqStep": freq_step,
            },
        },
    )

    config_path = project_dir / "config" / config_name
    write_config(config, config_path)
    return {"config_path": str(config_path), "config": config}


@mcp.tool()
def get_impedance_results(
    project_name: str,
    target_z: float = 50.0,
    tolerance_pct: float = 10.0,
) -> dict[str, Any]:
    """Compute and verify port impedances from simulation results.

    Parses port voltage and current data, computes Z = V / I per port,
    and checks each against a target impedance with tolerance.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    results = parse_results(project_dir / "results", "Driven")

    if not results.impedances:
        return {"error": "No impedance data available. Run a Driven simulation first."}

    verification = verify_impedance_match(
        results.impedances, target_z, tolerance_pct
    )
    verification["impedances"] = results.impedances
    return verification


@mcp.tool()
def get_directivity(project_name: str) -> dict[str, Any]:
    """Compute directivity metrics from simulation far-field results.

    Returns boresight directivity (dBi), maximum directivity, and the
    direction of peak radiation.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    results = parse_results(project_dir / "results", "Driven")

    if not results.directivity:
        return {
            "error": "No far-field / directivity data available. "
            "Ensure the simulation includes far-field postprocessing."
        }
    return results.directivity


@mcp.tool()
def get_radiation_pattern(project_name: str) -> dict[str, Any]:
    """Retrieve the parsed far-field radiation pattern data.

    Returns the full list of (theta, phi, gain) records from the
    simulation far-field output.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    results = parse_results(project_dir / "results", "Driven")

    if not results.far_field:
        return {"error": "No far-field data found in results."}
    return {
        "num_points": len(results.far_field),
        "far_field": results.far_field,
        "directivity": results.directivity,
    }


@mcp.tool()
def measure_feed_point_gaps(
    project_name: str,
    mesh_file: str,
    feed_group_prefix: str = "feed",
) -> dict[str, Any]:
    """Measure the physical gap at each dipole feed point in a mesh.

    Inspects mesh physical groups whose names start with *feed_group_prefix*
    and reports the bounding-box extent along the dipole axis for each.
    """
    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    mesh_path = project_dir / "mesh" / mesh_file
    return mesh_tools.measure_feed_gaps(str(mesh_path), feed_group_prefix)


# ============================================================================
# 11. Multi-Parameter Optimization
# ============================================================================


@mcp.tool()
async def run_optimization(
    project_name: str,
    config_file: str,
    parameters: list[dict[str, Any]],
    objective: str = "directivity",
    target_impedance: float = 50.0,
    impedance_tolerance_pct: float = 10.0,
    num_procs: int = 1,
) -> dict[str, Any]:
    """Run a grid-search optimization over multiple parameters.

    Each entry in *parameters* is::

        {"path": "dot.separated.config.path",
         "values": [v1, v2, ...]}

    The Cartesian product of all parameter values is swept.

    objective:
        - 'directivity': maximise boresight directivity (dBi)
        - 'max_directivity': maximise peak directivity
        - 'impedance_match': minimise impedance deviation from target

    Returns the best configuration and all evaluated points.
    """
    import itertools

    project_dir = proj_tools._resolve_project(_cfg.projects_dir, project_name)
    config_path = project_dir / "config" / config_file
    base_config = load_config(config_path)

    param_names = [p["path"] for p in parameters]
    param_values = [p["values"] for p in parameters]
    grid = list(itertools.product(*param_values))

    evaluated: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    best_score = -1e30

    for combo in grid:
        # Build modified config
        trial_config = json.loads(json.dumps(base_config))
        combo_dict: dict[str, Any] = {}
        for name, val in zip(param_names, combo):
            _set_nested(trial_config, name, val)
            combo_dict[name] = val

        run_id = str(uuid.uuid4())[:8]
        trial_name = f"opt_{run_id}.json"
        trial_path = project_dir / "config" / trial_name
        write_config(trial_config, trial_path)
        trial_output = project_dir / "results" / run_id

        proj_tools.add_run_to_manifest(
            project_dir, run_id, trial_name, parameters=combo_dict,
        )

        run = await _runner.start_simulation(
            run_id=run_id,
            config_path=trial_path,
            output_dir=trial_output,
            num_procs=num_procs,
            timeout=_cfg.simulation_timeout,
        )

        # Parse results
        trial_results = parse_results(trial_output, "Driven")

        score = _evaluate_objective(
            trial_results, objective, target_impedance, impedance_tolerance_pct,
        )

        entry = {
            "run_id": run_id,
            "parameters": combo_dict,
            "status": run.progress.status.value,
            "score": score,
            "directivity": trial_results.directivity,
        }
        evaluated.append(entry)

        if score > best_score:
            best_score = score
            best = entry

    return {
        "objective": objective,
        "num_evaluations": len(evaluated),
        "best": best,
        "all_evaluations": evaluated,
    }


def _evaluate_objective(
    results: Any,
    objective: str,
    target_z: float,
    tol_pct: float,
) -> float:
    """Score a simulation result according to the chosen objective."""
    if objective == "directivity":
        return results.directivity.get("boresight_directivity_dbi", -999.0)
    elif objective == "max_directivity":
        return results.directivity.get("max_directivity_dbi", -999.0)
    elif objective == "impedance_match":
        if not results.impedances:
            return -999.0
        verification = verify_impedance_match(results.impedances, target_z, tol_pct)
        # Score = negative total deviation (higher = better)
        total_dev = sum(
            p["deviation_pct"] for p in verification["ports"].values()
        )
        return -total_dev
    return 0.0


# ============================================================================
# Entry point
# ============================================================================


def main() -> None:
    """Start the Palace MCP Server."""
    global _cfg, _runner, _docs_index

    logging.basicConfig(level=logging.INFO)

    _cfg = ServerConfig()
    _cfg.ensure_dirs()

    _runner = PalaceRunner(_cfg.palace_binary, _cfg.max_cores)
    _docs_index = docs_tools.DocsIndex(_cfg.docs_dir)

    logger.info("Starting Palace MCP Server on %s:%d", _cfg.host, _cfg.port)
    logger.info("Projects directory: %s", _cfg.projects_dir)
    logger.info("Palace binary: %s", _cfg.palace_binary)

    mcp.settings.host = _cfg.host
    mcp.settings.port = _cfg.port
    mcp.settings.streamable_http_path = "/"
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
