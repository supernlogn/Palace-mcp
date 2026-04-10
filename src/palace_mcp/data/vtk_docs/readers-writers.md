# VTK Readers and Writers Reference

## Mesh/Grid Readers

### vtkXMLUnstructuredGridReader

Reads VTK XML unstructured grid files (`.vtu`). This is the primary format for Palace simulation meshes.

```python
import vtk

reader = vtk.vtkXMLUnstructuredGridReader()
reader.SetFileName("mesh.vtu")
reader.Update()

data = reader.GetOutput()
print(f"Number of points: {data.GetNumberOfPoints()}")
print(f"Number of cells: {data.GetNumberOfCells()}")

# Access point data arrays
point_data = data.GetPointData()
for i in range(point_data.GetNumberOfArrays()):
    print(f"Array: {point_data.GetArrayName(i)}")
```

### vtkUnstructuredGridReader

Reads legacy VTK unstructured grid files (`.vtk`).

```python
reader = vtk.vtkUnstructuredGridReader()
reader.SetFileName("mesh.vtk")
reader.Update()
data = reader.GetOutput()
```

### vtkPVDReader

Reads ParaView Data Collection files (`.pvd`) — XML files that reference multiple timestep data files. Returns a `vtkMultiBlockDataSet`.

```python
reader = vtk.vtkPVDReader()
reader.SetFileName("results.pvd")
reader.Update()
data = reader.GetOutput()  # vtkMultiBlockDataSet
```

## Geometry Filters

### vtkGeometryFilter

Extracts the surface geometry (boundary faces) from a 3D dataset. Converts volumetric data to surface representation for rendering.

```python
geo_filter = vtk.vtkGeometryFilter()
geo_filter.SetInputData(unstructured_grid)
geo_filter.Update()
surface = geo_filter.GetOutput()  # vtkPolyData
```

### vtkCompositeDataGeometryFilter

Extracts geometry from composite datasets (e.g., `vtkMultiBlockDataSet` from PVD files).

```python
geo_filter = vtk.vtkCompositeDataGeometryFilter()
geo_filter.SetInputData(multi_block_data)
geo_filter.Update()
surface = geo_filter.GetOutput()
```

## Mappers

### vtkDataSetMapper

Maps any type of VTK dataset to graphics primitives for rendering.

```python
mapper = vtk.vtkDataSetMapper()
mapper.SetInputData(unstructured_grid)

# Color by scalar field
mapper.SetScalarModeToUsePointFieldData()
mapper.SelectColorArray("E_field")
mapper.SetScalarVisibility(True)
```

### vtkPolyDataMapper

Maps polygonal data to graphics primitives. Use when you have surface data.

```python
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(geo_filter.GetOutputPort())
```

### vtkCompositePolyDataMapper

Maps composite (multi-block) polygonal data. Used for PVD datasets.

```python
mapper = vtk.vtkCompositePolyDataMapper()
mapper.SetInputConnection(geo_filter.GetOutputPort())
```

## Rendering

### Offscreen Rendering Pipeline

Complete pipeline for server-side mesh visualization:

```python
import vtk
import base64

def render_mesh(mesh_path, width=800, height=600, scalar_field=None):
    # 1. Read the mesh
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(mesh_path)
    reader.Update()
    data = reader.GetOutput()

    # 2. Extract surface geometry
    geo_filter = vtk.vtkGeometryFilter()
    geo_filter.SetInputData(data)
    geo_filter.Update()

    # 3. Create mapper
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(geo_filter.GetOutputPort())

    if scalar_field:
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray(scalar_field)
        mapper.SetScalarVisibility(True)

    # 4. Create actor
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    # 5. Setup renderer
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(0.1, 0.1, 0.1)
    renderer.ResetCamera()

    # 6. Offscreen render
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)
    render_window.SetSize(width, height)
    render_window.AddRenderer(renderer)
    render_window.Render()

    # 7. Capture PNG
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(render_window)
    w2i.Update()

    writer = vtk.vtkPNGWriter()
    writer.SetWriteToMemory(1)
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()

    png_data = writer.GetResult()
    return base64.b64encode(bytes(png_data)).decode()
```

## Image Writers

### vtkPNGWriter

Writes images in PNG format. Supports writing to memory for server-side use.

```python
writer = vtk.vtkPNGWriter()
writer.SetFileName("output.png")
writer.SetInputConnection(w2i.GetOutputPort())
writer.Write()

# Or write to memory
writer.SetWriteToMemory(1)
writer.Write()
png_bytes = bytes(writer.GetResult())
```

## Data Inspection

### Querying Dataset Properties

```python
# For unstructured grids
data = reader.GetOutput()

# Basic info
print(f"Points: {data.GetNumberOfPoints()}")
print(f"Cells: {data.GetNumberOfCells()}")
print(f"Bounds: {data.GetBounds()}")

# Point data arrays (scalar/vector fields)
pd = data.GetPointData()
for i in range(pd.GetNumberOfArrays()):
    arr = pd.GetArray(i)
    print(f"  {pd.GetArrayName(i)}: {arr.GetNumberOfComponents()} components, "
          f"range={arr.GetRange()}")

# Cell data arrays
cd = data.GetCellData()
for i in range(cd.GetNumberOfArrays()):
    print(f"  {cd.GetArrayName(i)}")
```
