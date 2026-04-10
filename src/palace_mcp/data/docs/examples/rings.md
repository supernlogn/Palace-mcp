# [Inductance Matrix for a Pair of Concentric Rings](#Inductance-Matrix-for-a-Pair-of-Concentric-Rings)[]()[](#Inductance-Matrix-for-a-Pair-of-Concentric-Rings)

The files for this example can be found in the [`examples/rings/`](https://github.com/awslabs/palace/blob/v0.16.0/examples/rings) directory of the *Palace* source code.

This example seeks to compute the inductance matrix for a system of two concentric current-carrying rings of radii $r_a$ and $r_b$, each with width $w$. As with the previous example, the permeability of the surrounding medium is assumed to be the permeability of free space. The mutual inductance, $M_{ab}$, can be easily computed for the case where $r_a\ll r_b$ and $w = 0$ using the Biot-Savart law as

\[M_{ab} = \frac{\mu_0\pi r_b^2}{2 r_a} \,.\]

Analytic expressions for the self inductance of this configuration can also be derived, for example from [[1]](#References) we have

\[\begin{aligned} M_{aa} &= \mu_0 r_a \left(\log{\frac{16 r_a}{w}}-1.75\right) \\ M_{bb} &= \mu_0 r_b \left(\log{\frac{16 r_b}{w}}-1.75\right) \,. \end{aligned}\]

We take in this case $r_a = 10 \text{ μm}$, $r_b = 100 \text{ μm}$, and $w = 1 \text{ μm}$. The `mesh.jl` script in the [`mesh/`](https://github.com/awslabs/palace/blob/v0.16.0/examples/rings/mesh) directory is used to generate an unstructured tetrahedral mesh with Gmsh, saved to [`mesh/rings.msh`](https://github.com/awslabs/palace/blob/v0.16.0/examples/rings/mesh/rings.msh), and a depiction is shown below.

    

The configuration file for the *Palace* simulation is [`rings.json`](https://github.com/awslabs/palace/blob/v0.16.0/examples/rings/rings.json). The simulation `"Type"` is `"Magnetostatic"`, and we add `"SurfaceCurrent"` boundaries for applying a surface current to drive the inner or outer ring. The rest of the ring boundaries are labeled as `"PEC"` boundaries, which prescribes a zero magnetic flux, or magnetic insulation, boundary condition. The farfield is also prescribed the `"PEC"` boundary condition. We seek a second-order solution and use the geometric multigrid AMS solver.

The computed inductance matrix is saved to disk as `postpro/terminal-M.csv`, and below we show its contents:

```
        i,                M[i][1] (H),                M[i][2] (H)
 1.00e+00,        +4.273875790210e-11,        +1.960237983953e-12
 2.00e+00,        +1.960237983953e-12,        +7.141029007109e-10
```

According to the analytic expressions above, for this geometry we should have

\[M_{ab} = 1.973921\text{ pH}\]

for the mutual inductance, and

\[\begin{aligned} M_{aa} &= 41.78537\text{ pH}\\ M_{bb} &= 707.2050\text{ pH} \end{aligned}\]

for the self inductances. Thus, the *Palace* solution has percent-level errors in the self inductances versus the analytic solutions.

The typical approach used by *Palace* for lumped parameter extraction uses the computed field energies, but one can also compute the inductance by explicitly integrating the magnetic flux through a surface and dividing by the excitation current. This is configured under [`config["Boundaries"]["Postprocessing"]["Inductance"]`](../../config/boundaries/#boundaries%5B%22Postprocessing%22%5D%5B%22Inductance%22%5D) in the configuration file. The postprocessed magnetic flux values are written to `postpro/surface-F.csv`:

```
        i,              Φ_mag[1] (Wb),              Φ_mag[2] (Wb)
 1.00e+00,        +2.195684773071e-12,        +9.763834553259e-14
 2.00e+00,        +1.007646802433e-13,        +3.678646800217e-11
```

Combining with the values in `postpro/terminal-I.csv` we can compute the inductance matrix in this alternative fashion,

```
        i,               I_inc[i] (A)
 1.00e+00,        +5.152105132308e-02
 2.00e+00,        +5.152105132308e-02
```

we arrive at

```
    @printf(
        " %.2e,        %+.12e,        %+.12e\n",
        result[i, 1],
        result[i, 2],
        result[i, 3]
```

```
        i,                M[i][1] (H),                M[i][2] (H)
 1.00e+00,        +4.261723541514e-11,        +1.895115550347e-12
 2.00e+00,        +1.955796274642e-12,        +7.140084889085e-10
```

The values computed using the flux integral method are in close agreement to those above, as expected. This method of calculating the inductance matrix directly from flux values is in general less accurate than using the energy method, due to convergence properties of finite element functional outputs, but serves as a validation of the energy calculation.

Lastly, we visualize the magnitude of the magnetic flux density field for the excitations of the inner and outer rings. The files for this visualization are again saved to the `postpro/paraview` directory.

       

## [References](#References)[]()[](#References)

[1] M. R. Alizadeh Pahlavani and H. A. Mohammadpour, Inductance comparison of the solenoidal coil of modular toroidal coils using the analytical and finite element method, *Progress in Electromagnetics Research* 20 (2010) 337-352.
