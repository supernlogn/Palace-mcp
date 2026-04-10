# Palace MCP Server - Requirements Specification

## 1. MCP Server & Core Functionality

### 1.1 Server Architecture
- The system consists of a single Python-based MCP server.
- The server communicates over HTTP (Streamable HTTP transport) so that it can be reached by an OpenClaw agent.
- The server is single-user, local-only (no authentication required). It runs on the same host machine where simulations execute.

### 1.2 Palace Installation & Access
- Palace (latest stable release) must be installed on the host machine as a build-from-source dependency. The MCP server invokes the `palace` binary via subprocess to run simulations.
- The Python project (MCP server and all Python tooling) must be managed with the `uv` package manager (`pyproject.toml`, `uv.lock`).
- Gmsh (and its Python bindings `gmsh`) must be installed as a Python dependency alongside the MCP server so it is available for meshing operations.

### 1.3 Simulation Construction
- Simulation construction (geometry definition, meshing, material assignment, boundary conditions, solver configuration) must be performed through MCP server tool calls.
- Users must be able to write Python scripts (using vtk) that define geometry, generate meshes, and assign material attributes. The MCP server provides tools to execute these scripts and collect the resulting mesh files.
- Users must be able to download all generated files (meshes, Palace JSON configs, simulation results) via MCP tool calls.

### 1.4 Documentation Access
- The MCP server must bundle a local copy of the Palace documentation (scraped or mirrored from https://awslabs.github.io/palace/stable/).
- The server must expose an MCP tool that performs full-text search over this documentation and returns relevant snippets. This allows the connected LLM agent to look up Palace configuration options, boundary condition types, problem types, etc. on demand.

### 1.5 Interactive Guidance
- The MCP server provides MCP tools that an LLM agent (e.g., OpenClaw) can call to guide users through simulation setup. The server itself does not contain conversational logic - it exposes structured tools (list problem types, suggest boundary conditions, validate config, etc.) that the LLM agent orchestrates.

---

## 2. Visualization

### 2.1 3D Geometry & Field Viewer
- The 3D viewer is VTK (https://docs.vtk.org/en/latest/api/python.html), installed as the `vtk` Python package via `uv`.
- Palace natively outputs field data in ParaView format (VTU/PVD files in the `paraview/` directory). Since ParaView is built on VTK, these files are read directly by VTK's Python API (`vtkXMLUnstructuredGridReader`, etc.).
- For geometry preview (before simulation), the MCP server reads Gmsh `.msh` using VTK's `vtkGmshReader` or VTKHDF files using `vtkHDFReader`  or converts them to VTU for rendering.
- Browser-based visualization is provided via `trame` (a VTK-based web framework) or by exporting VTK scenes to static images/interactive HTML. The MCP server hosts the web viewer.

### 2.2 Side-by-Side Comparison
- The web front-end must support a side-by-side 3D viewer mode using VTK, allowing two simulation results to be displayed next to each other for visual comparison.

### 2.3 Metric Plots
- For each problem type, relevant metric plots must be generated and viewable in the browser:
  - **Driven problems**: S-parameter magnitude/phase vs. frequency curves, Smith charts.
  - **Eigenmode problems**: eigenfrequency spectrum, quality factors, energy participation ratios (EPRs).
  - **Electrostatic problems**: capacitance matrix values, electric field energy.
  - **Magnetostatic problems**: inductance matrix values, magnetic field energy.
  - **Transient problems**: time-domain field amplitude plots.
- Plots must be generated using a Python plotting library (e.g., Matplotlib or Plotly) and served as interactive HTML or static images via the MCP server.

---

## 3. Simulation Lifecycle

### 3.1 Configuration Validation
- Before execution, validate Palace JSON configuration files: check that referenced mesh files exist, that boundary condition attributes reference valid mesh boundaries, that material attributes reference valid mesh domains, and that required solver parameters are present.
- Return structured error messages indicating exactly what is wrong and where.

### 3.2 Simulation Tracking
- Track running simulations by tailing the Palace stdout/stderr log in a background thread.
- Parse Palace log output to extract iteration counts, residual norms, and elapsed time. Estimate progress as a percentage of completed frequency steps, time steps, or eigenvalue iterations (depending on problem type).
- Expose current simulation status (running/completed/failed), progress percentage, elapsed wall-clock time, and estimated time remaining via an MCP tool.

### 3.3 Result Parsing & Summarization
- After simulation completes, parse Palace CSV output files (`domain-E.csv`, `port-V.csv`, `port-I.csv`, `surface-F.csv`, `surface-Q.csv`, `probe-E.csv`, `probe-B.csv`) and return structured summaries.
- For driven problems, compute and return S-parameters from port voltages/currents.
- For eigenmode problems, return eigenfrequencies, quality factors, and EPRs.
- For electrostatic/magnetostatic problems, return capacitance/inductance matrices.
- Do not expose raw log files as the primary interface; always provide parsed, structured results.

---

## 4. Mesh & Geometry

### 4.1 VTKHDF Integration
- vtk (python library) is installed as a first-class dependency of the MCP server via `uv` (the `vtk` PyPI package).
- The MCP server provides tools to: generate a mesh from a user-provided python scripts using vtk library, inspect mesh statistics, and export meshes in formats Palace supports (Gmsh `.msh`, Exodus `.exo`, or MFEM mesh format).

### 4.2 Mesh Quality Validation
- Before simulation, validate mesh quality by computing element aspect ratios, skewness, and minimum/maximum element sizes using vtk's built-in mesh quality metrics.
- Warn the user if quality metrics fall below recommended thresholds (e.g., aspect ratio > 10, skewness > 0.9).

### 4.3 Parameterized Geometry Templates
- The MCP server ships with a set of built-in parameterized geometry templates for common metamaterial and electromagnetics structures (e.g., split-ring resonator, patch antenna, coplanar waveguide, microstrip line).
- Templates are Python functions (using the vtk API) that accept dimensional parameters and return a meshed geometry.
- Users can list available templates, instantiate them with custom parameters, and use them as a starting point. The LLM agent can also suggest templates based on the user's problem description.

---
vtk api can be found here: https://docs.vtk.org/en/latest/api/python.html


## 5. Materials & Physics

### 5.1 Materials Database
- Provide a built-in materials database stored as a JSON file.
- Each material entry contains the properties that Palace's `config["Domains"]["Materials"]` accepts: `Permeability` (relative), `Permittivity` (relative), `LossTan`, `Conductivity` (S/m), and optionally `LondonDepth` (for superconductors) and `MaterialAxes` (for anisotropic materials).
- Include common materials: copper, aluminum, gold, silver (conductors); FR-4, Rogers RT/duroid, silicon, silicon dioxide, sapphire (dielectrics); niobium, YBCO (superconductors); air/vacuum.
- The database must be extensible - users can add custom materials via an MCP tool, which appends to the JSON file.

### 5.2 Problem Type Templates
- Offer starter Palace JSON configuration templates for each supported problem type:
  - Driven (frequency domain)
  - Eigenmode
  - Electrostatic
  - Magnetostatic
  - Transient (time domain)
- Each template includes sensible default solver settings, a placeholder mesh reference, and example boundary conditions. The user fills in their specific geometry and material assignments.

---

## 6. Data & Project Management

### 6.1 Project Definition
- A project is a directory on disk with a well-defined structure:
  ```
  project-name/
  ├── scripts/          # User Python/Gmsh geometry scripts
  ├── mesh/             # Generated mesh files (.msh, .e, MFEM format)
  ├── config/           # Palace JSON configuration files
  ├── results/          # Palace output (CSV files, field data)
  │   └── paraview/     # ParaView/VTK output files (VTU/PVD)
  └── project.json      # Project manifest (metadata, parameter history)
  ```
- `project.json` stores: project name, creation date, Palace version used, list of simulation runs with their parameters and status, and references to input/output files.

### 6.2 Save & Reload
- The MCP server provides tools to create, list, open, and archive projects.
- All project state (scripts, meshes, configs, results) is persisted on disk. Reopening a project restores the full context.

### 6.3 Batch Simulations & Parameter Sweeps
- Support running batch simulations over a range of parameter values (e.g., sweeping a geometric dimension or material property).
- For each batch run, store results indexed by parameter values in the project directory.

### 6.4 Comparison Tools
- Side-by-side 3D field visualization using VTK (web) for comparing two simulation results (see Section 2.2).
- Side-by-side metric plots: overlay or juxtapose S-parameter curves, eigenfrequency spectra, capacitance/inductance values, or any other computed metrics from two or more simulation runs.
- Tabular comparison: generate a summary table of key metrics across multiple runs in a parameter sweep.

---

## 7. Reliability & User Experience

### 7.1 Actionable Diagnostics
- When Palace exits with a non-zero status, parse stderr to identify the failure mode (solver divergence, mesh read error, missing config keys, invalid boundary attributes, etc.).
- Return a structured diagnostic message with: the error category, the relevant config section or file, and a suggested fix.

### 7.2 Reproducibility
- Each project records in `project.json` the exact Palace version (git tag or binary version string), the Gmsh version, the VTK version, and all Python dependency versions (captured from `uv.lock`).
- Use the latest stable Palace release. Pin it at the project level so results can be reproduced.

### 7.3 Resource Limits
- Allow users to set CPU core count and memory limits for Palace runs (passed via `mpirun` arguments).
- Before launching a simulation, estimate resource requirements based on mesh size (number of elements and polynomial order) and warn if the estimated memory exceeds the user-specified limit or available system memory.

---

## 8. Security

### 8.1 Script Execution Sandbox
- User-provided Python geometry scripts are executed in a separate subprocess (via `subprocess.run` or `subprocess.Popen`).
- No restricted permissions or container isolation is required - a plain subprocess is sufficient.
- Scripts run with a configurable timeout to prevent infinite loops. The subprocess is killed if the timeout is exceeded.

### 8.2 Input Validation
- All user-provided parameters must be validated before being inserted into Palace JSON config files or passed to shell commands.
- Use structured JSON serialization (not string interpolation) to build Palace config files, preventing injection.
- Validate file paths to prevent path traversal outside the project directory.

---

## 9. Implementation Constraints

- The entire system is a single Python server process.
- Package management uses `uv` (with `pyproject.toml` and `uv.lock`).
- Palace is built from source (CMake) on the host and its binary path is configured in the MCP server settings.
- Gmsh is installed as a Python package via `uv` (`gmsh` on PyPI).
- VTK is installed as a Python package via `uv` (`vtk` on PyPI). Browser-based 3D visualization is provided via `trame` or VTK-exported interactive HTML.
- The MCP server uses the Streamable HTTP transport so it is reachable by remote agents (OpenClaw).
1. MCP Server & Core Functionality
The MCP server must support building and running simulations using AWS Palace.

Palace’s Python environment must be installable and accessible through the MCP server.

Simulation construction must be performed through MCP server commands.

The MCP server must expose Palace documentation to users.

The MCP server must act as an interactive guide, helping users write or refine Palace scripts.

Users must be able to write scripts that define geometry, meshes, and material assignments.

Users must be able to download all generated files (meshes, configs, results).

2. Visualization
A tool must exist to visualize geometry generated by user scripts.

Visualization must be available through a web-based front-end.

3. Simulation Lifecycle
Validate Palace JSON configuration files before execution (mesh references, BCs, materials).

Track running simulations (progress, ETA, resource usage).

Parse and summarize Palace outputs (S‑parameters, fields, eigenvalues) instead of exposing raw logs.

4. Mesh & Geometry
Integrate a meshing tool (e.g., vtk) as a first-class component.

Validate mesh quality (aspect ratio, skewness, etc.) before simulation.

Support parameterized geometry templates to enable dimension sweeps.

5. Materials & Physics
Provide a built‑in database of common materials (conductors, dielectrics, superconductors).

Offer starter templates for common Palace problem types (driven, eigenmode, electrostatic, magnetostatic).

6. Data & Project Management
Allow saving and reloading full project state (geometry, configs, results).

Support batch simulations over parameter ranges with comparison tools.

Visualize simulation results (field plots, S‑parameter curves) in addition to geometry.

7. Reliability & User Experience
Provide actionable diagnostics when Palace solves fail (divergence, mesh issues, config errors).

Ensure reproducibility by pinning Palace version, dependencies, and solver backends (PETSc, MFEM).

Allow users to set CPU/memory limits and warn when simulations may exceed resources.

8. Security
Sandbox execution of user geometry scripts to prevent harmful Python execution.

Validate all user-provided parameters to prevent injection into config files or shell commands.

9. Implementation Constraint
The entire system must be implemented using Python-based servers.