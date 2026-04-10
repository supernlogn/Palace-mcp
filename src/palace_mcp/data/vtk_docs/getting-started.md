# Getting Started with VTK in Python

## Installation

VTK is available on PyPI:

```bash
pip install vtk
```

Verify the installation:

```python
>>> import vtk
>>> print(vtk.__version__)
```

## Overview

VTK (Visualization Toolkit) is an open-source software system for image processing, 3D graphics, volume rendering, and visualization. It includes advanced algorithms such as surface reconstruction, implicit modelling, and decimation, along with rendering techniques like hardware-accelerated volume rendering and LOD control.

## Key Concepts

### Pipeline Architecture

VTK uses a pipeline architecture for data processing:

1. **Source** — generates or reads data (e.g., `vtkXMLUnstructuredGridReader`)
2. **Filter** — processes data (e.g., `vtkGeometryFilter`, `vtkCompositeDataGeometryFilter`)
3. **Mapper** — maps data to graphics primitives (e.g., `vtkDataSetMapper`, `vtkCompositePolyDataMapper`)
4. **Actor** — represents an object in the scene (e.g., `vtkActor`)
5. **Renderer** — renders the scene
6. **RenderWindow** — displays the rendered output

### Basic Rendering Example

```python
import vtk

# Create a sphere source
sphere = vtk.vtkSphereSource()
sphere.SetRadius(1.0)
sphere.SetThetaResolution(32)
sphere.SetPhiResolution(32)

# Create mapper
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(sphere.GetOutputPort())

# Create actor
actor = vtk.vtkActor()
actor.SetMapper(mapper)

# Create renderer and render window
renderer = vtk.vtkRenderer()
renderer.AddActor(actor)

render_window = vtk.vtkRenderWindow()
render_window.AddRenderer(renderer)
render_window.SetSize(800, 600)
render_window.Render()
```

### Offscreen Rendering

For server-side rendering without a display:

```python
import vtk

render_window = vtk.vtkRenderWindow()
render_window.SetOffScreenRendering(1)
render_window.SetSize(800, 600)

renderer = vtk.vtkRenderer()
render_window.AddRenderer(renderer)

# ... add actors ...

render_window.Render()

# Capture to image
window_to_image = vtk.vtkWindowToImageFilter()
window_to_image.SetInput(render_window)
window_to_image.Update()

# Write to PNG
writer = vtk.vtkPNGWriter()
writer.SetFileName("output.png")
writer.SetInputConnection(window_to_image.GetOutputPort())
writer.Write()
```

## Useful Links

- VTK Home: https://vtk.org/
- VTK Documentation: https://docs.vtk.org/
- VTK Examples: https://examples.vtk.org/site/Python/
- VTK Source: https://gitlab.kitware.com/vtk/vtk
- PyVista (high-level Python interface): https://docs.pyvista.org/
