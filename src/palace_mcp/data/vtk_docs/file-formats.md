# VTK File Formats

## Overview

VTK provides three styles of file formats: Legacy, XML, and VTKHDF.

## Legacy Format (.vtk)

The legacy format is a simple serial format that is easy to read and write by hand or programmatically.

### Structure

Legacy VTK files consist of five parts:
1. File version and identifier
2. Header (256 characters max)
3. File format (ASCII or BINARY)
4. Dataset structure (STRUCTURED_POINTS, STRUCTURED_GRID, UNSTRUCTURED_GRID, POLYDATA, RECTILINEAR_GRID)
5. Dataset attributes (SCALARS, VECTORS, NORMALS, TENSORS, etc.)

### Example: Unstructured Grid

```
# vtk DataFile Version 3.0
My unstructured grid example
ASCII
DATASET UNSTRUCTURED_GRID
POINTS 4 float
0.0 0.0 0.0
1.0 0.0 0.0
1.0 1.0 0.0
0.0 1.0 0.0
CELLS 1 5
4 0 1 2 3
CELL_TYPES 1
9
```

### Reading Legacy Files

```python
import vtk

reader = vtk.vtkUnstructuredGridReader()
reader.SetFileName("mesh.vtk")
reader.Update()
data = reader.GetOutput()
```

## XML Format (.vtu, .vtp, .vti, .vtr, .vts, .pvd)

XML formats are more flexible than the legacy format. They support random access, parallel I/O, and portable data compression.

### Common XML File Types

| Extension | Dataset Type | Reader Class |
|-----------|-------------|--------------|
| `.vtu` | Unstructured Grid | `vtkXMLUnstructuredGridReader` |
| `.vtp` | PolyData | `vtkXMLPolyDataReader` |
| `.vti` | ImageData | `vtkXMLImageDataReader` |
| `.vtr` | RectilinearGrid | `vtkXMLRectilinearGridReader` |
| `.vts` | StructuredGrid | `vtkXMLStructuredGridReader` |
| `.pvtu` | Parallel Unstructured Grid | `vtkXMLPUnstructuredGridReader` |
| `.pvd` | ParaView Data Collection | `vtkPVDReader` |

### Reading XML Unstructured Grid (.vtu)

```python
import vtk

reader = vtk.vtkXMLUnstructuredGridReader()
reader.SetFileName("mesh.vtu")
reader.Update()
data = reader.GetOutput()

# Get basic info
print(f"Points: {data.GetNumberOfPoints()}")
print(f"Cells: {data.GetNumberOfCells()}")
```

### ParaView Data Collection (.pvd)

PVD files are XML files that reference multiple VTK data files, typically used for time series data. Palace outputs results in PVD format.

```xml
<?xml version="1.0"?>
<VTKFile type="Collection" version="0.1">
  <Collection>
    <DataSet timestep="0" file="result_000000.vtu"/>
    <DataSet timestep="1" file="result_000001.vtu"/>
  </Collection>
</VTKFile>
```

Reading a PVD file:

```python
import vtk

reader = vtk.vtkPVDReader()
reader.SetFileName("results.pvd")
reader.Update()
data = reader.GetOutput()  # returns vtkMultiBlockDataSet
```

## VTKHDF Format (.vtkhdf)

A newer format based on HDF5 that provides good I/O performance and robust parallel I/O. It uses the same concepts as the XML formats but relies on HDF5 for storage.
