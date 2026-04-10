Task:  
Use MCP commands to generate a VTK mesh of a dipole‑antenna array, run electromagnetic simulations using the Palace MCP server, evaluate the radiation pattern, and optimize antenna parameters.

1. Geometry Generation (VTK)
Create a Python script (via MCP) that uses VTK to construct the geometry of a single dipole antenna designed to radiate at f = 1 GHz.

Requirements:

The dipole must be modeled as a thin wire (cylindrical segments).

The feed point must be explicitly represented.

The script must output a VTK mesh file suitable for Palace.

Then:

Replicate this dipole so that five dipoles exist in total.

Their centers must lie on a straight line, all parallel, and all oriented identically.

The spacing between dipoles must be parameterized.

2. Simulation Setup (Palace MCP Server)
Using the generated VTK mesh, configure and run a Palace simulation that:

Excites each dipole with 1 V amplitude.

Allows the phase of each dipole to be independently controlled.

Ensures each feed point is matched to 50 Ω input impedance.

Computes the far‑field radiation pattern at 1 GHz.

3. Tests and Measurements
Implement MCP‑driven tests for:

A. Directivity Measurement
Compute the full 3D radiation pattern.

Extract directivity at 0° (boresight).

Provide a metric for “how directive” the pattern is.

B. Feed‑Point Gap Measurement
Measure the physical gap at each dipole’s feed point from the VTK geometry.

Report the gap for all five dipoles.

C. Impedance Verification
For each dipole, compute the input impedance at the feed.

Confirm it is 50 Ω ± tolerance.

Report any deviations.

4. Optimization Tasks
Use MCP commands to run parameter sweeps or optimization loops over:

Dipole length

Wire radius

Spacing between dipoles

Relative phase of each dipole (amplitude fixed at 1 V)

Optimization goals:

Maximize directivity at 0°

Maintain 50 Ω feed impedance

Preserve manufacturable geometry (reasonable wire radius and spacing)

5. Output Requirements
The agent must return:

The generated VTK mesh file(s)

The Palace simulation configuration used

Radiation pattern plots and directivity values

Optimal geometric and phase parameters

Feed‑point gap measurements

Impedance results for each dipole

A summary of the best‑performing configuration