# VTK Python Examples for EM Simulations

## Reading and Visualizing Palace Simulation Results

Palace outputs electromagnetic field data in VTU/PVD format. This guide shows how to work with these results using VTK.

### Reading Eigenmode Results

```python
import vtk

# Palace outputs eigenmodes as separate VTU files or a PVD collection
reader = vtk.vtkXMLUnstructuredGridReader()
reader.SetFileName("results/paraview/eigenmode_000001.vtu")
reader.Update()

data = reader.GetOutput()

# List available field arrays
pd = data.GetPointData()
for i in range(pd.GetNumberOfArrays()):
    name = pd.GetArrayName(i)
    arr = pd.GetArray(i)
    n_comp = arr.GetNumberOfComponents()
    print(f"Field: {name}, Components: {n_comp}, Range: {arr.GetRange()}")
```

### Visualizing E-field Magnitude

```python
import vtk

# Read data
reader = vtk.vtkXMLUnstructuredGridReader()
reader.SetFileName("eigenmode.vtu")
reader.Update()
data = reader.GetOutput()

# Compute field magnitude if needed
calc = vtk.vtkArrayCalculator()
calc.SetInputData(data)
calc.AddVectorArrayName("E")
calc.SetFunction("mag(E)")
calc.SetResultArrayName("E_magnitude")
calc.Update()

# Extract surface for rendering
geo = vtk.vtkGeometryFilter()
geo.SetInputConnection(calc.GetOutputPort())
geo.Update()

# Create color-mapped visualization
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(geo.GetOutputPort())
mapper.SetScalarModeToUsePointFieldData()
mapper.SelectColorArray("E_magnitude")
mapper.SetScalarVisibility(True)

# Add color bar
lut = vtk.vtkLookupTable()
lut.SetHueRange(0.667, 0.0)  # Blue to Red
lut.Build()
mapper.SetLookupTable(lut)

actor = vtk.vtkActor()
actor.SetMapper(mapper)
```

### Creating Cross-Section Slices

```python
import vtk

# Create a cutting plane
plane = vtk.vtkPlane()
plane.SetOrigin(0, 0, 0)
plane.SetNormal(0, 0, 1)  # XY plane

cutter = vtk.vtkCutter()
cutter.SetInputData(data)
cutter.SetCutFunction(plane)
cutter.Update()

mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(cutter.GetOutputPort())

actor = vtk.vtkActor()
actor.SetMapper(mapper)
```

### Extracting Field Data Along a Line

```python
import vtk

# Define a line probe
line = vtk.vtkLineSource()
line.SetPoint1(0, 0, 0)
line.SetPoint2(1, 0, 0)
line.SetResolution(100)

# Probe the dataset
probe = vtk.vtkProbeFilter()
probe.SetInputConnection(line.GetOutputPort())
probe.SetSourceData(data)
probe.Update()

# Extract values
output = probe.GetOutput()
field_array = output.GetPointData().GetArray("E_magnitude")
for i in range(output.GetNumberOfPoints()):
    point = output.GetPoint(i)
    value = field_array.GetValue(i)
    print(f"Position: {point}, Value: {value}")
```

### Mesh Quality Analysis

```python
import vtk

# Read mesh
reader = vtk.vtkXMLUnstructuredGridReader()
reader.SetFileName("mesh.vtu")
reader.Update()

# Compute mesh quality metrics
quality = vtk.vtkMeshQuality()
quality.SetInputData(reader.GetOutput())
quality.SetTetQualityMeasureToAspectRatio()  # For tetrahedral meshes
quality.Update()

# Get quality statistics
quality_data = quality.GetOutput()
quality_array = quality_data.GetCellData().GetArray("Quality")

min_q = quality_array.GetRange()[0]
max_q = quality_array.GetRange()[1]
print(f"Quality range: [{min_q:.3f}, {max_q:.3f}]")
```

### Comparing Two Simulation Results

```python
import vtk

# Read two datasets
reader1 = vtk.vtkXMLUnstructuredGridReader()
reader1.SetFileName("result1.vtu")
reader1.Update()

reader2 = vtk.vtkXMLUnstructuredGridReader()
reader2.SetFileName("result2.vtu")
reader2.Update()

# Interpolate dataset2 onto dataset1's grid
probe = vtk.vtkProbeFilter()
probe.SetInputData(reader1.GetOutput())
probe.SetSourceData(reader2.GetOutput())
probe.Update()

# Now both datasets share the same grid and can be compared
```

## Working with Gmsh Meshes

Palace simulation meshes are typically generated with Gmsh and exported as `.msh` files, then converted to VTU for visualization.

```python
import gmsh
import vtk

# Gmsh generates .msh files
# Convert to VTU for VTK visualization
gmsh.initialize()
gmsh.open("geometry.geo")
gmsh.model.mesh.generate(3)
gmsh.write("mesh.msh")
gmsh.finalize()

# Read the mesh in VTK (if exported as VTU)
reader = vtk.vtkXMLUnstructuredGridReader()
reader.SetFileName("mesh.vtu")
reader.Update()
```
