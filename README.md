# Palace MCP Server

MCP server for building and running AWS Palace electromagnetic simulations.

## Features

- Project management for simulation workflows
- Materials database (conductors, dielectrics, superconductors)
- Mesh generation and quality validation via VTK and Gmsh
- Palace JSON configuration building and validation
- Simulation execution, tracking, and result parsing
- 3D visualization with VTK, metric plots with Plotly
- Documentation search over bundled Palace docs
- Parameterized geometry templates for common EM structures
- Parameter sweep / batch simulation support

## Quick Start

```bash
# Install with uv
uv sync

# Run the MCP server
uv run palace-mcp
```

## Configuration

Set via environment variables:

| Variable | Default | Description |
|---|---|---|
| `PALACE_BINARY` | `palace` | Path to the Palace binary |
| `PALACE_PROJECTS_DIR` | `./projects` | Root directory for projects |
| `PALACE_DOCS_DIR` | (bundled) | Palace documentation directory |
| `PALACE_MCP_HOST` | `0.0.0.0` | Server bind host |
| `PALACE_MCP_PORT` | `8000` | Server bind port |
| `PALACE_SCRIPT_TIMEOUT` | `300` | Geometry script timeout (seconds) |
| `PALACE_SIM_TIMEOUT` | `86400` | Simulation timeout (seconds) |
| `PALACE_MAX_CORES` | `0` (unlimited) | Max CPU cores for simulations |
| `PALACE_MAX_MEMORY_GB` | `0` (unlimited) | Max memory limit (GB) |
