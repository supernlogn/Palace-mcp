# [Eigenmodes of a Cylinder](#Eigenmodes-of-a-Cylinder)[]()[](#Eigenmodes-of-a-Cylinder)

The files for this example can be found in the [`examples/cylinder/`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder) directory of the *Palace* source code.

## [Cavity](#Cavity)[]()[](#Cavity)

This example demonstrates *Palace*'s eigenmode simulation type to solve for the lowest frequency modes of a cylindrical cavity resonator. In particular, we consider a cylindrical cavity filled with Teflon ($\varepsilon_r = 2.08$, $\tan\delta = 4\times 10^{-4}$), with radius $a = 2.74\text{ cm}$ and height $d = 2a$. From [[1]](#References), the frequencies of the $\text{TE}_{nml}$ and $\text{TM}_{nml}$ modes are given by

\[\begin{aligned} f_{\text{TE},nml} &= \frac{1}{2\pi\sqrt{\mu\varepsilon}}     \sqrt{\left(\frac{p'_{nm}}{a}\right)^2 +     \left(\frac{l\pi}{d}\right)^2} \\ f_{\text{TM},nml} &= \frac{1}{2\pi\sqrt{\mu\varepsilon}}     \sqrt{\left(\frac{p_{nm}}{a}\right)^2 +     \left(\frac{l\pi}{d}\right)^2} \\ \end{aligned}\]

where  $p_{nm}$ and $p'_{nm}$ denote the $m$-th root ($m\geq 1$) of the $n$-th order Bessel function ($n\geq 0$) of the first kind, $J_n$, and its derivative, $J'_n$, respectively.

In addition, we have analytic expressions for the unloaded quality factors due to dielectric loss, $Q_d$, and imperfectly conducting walls, $Q_c$. In particular,

\[Q_d = \frac{1}{\tan\delta}\]

and, for a surface resistance $R_s$,

\[Q_c = \frac{(ka)^3\eta ad}{4(p'_{nm})^2 R_s}     \left[1-\left(\frac{n}{p'_{nm}}\right)^2\right]     \left\{\frac{ad}{2}         \left[1+\left(\frac{\beta an}{(p'_{nm})^2}\right)^2\right] +         \left(\frac{\beta a^2}{p'_{nm}}\right)^2         \left(1-\frac{n^2}{(p'_{nm})^2}\right)\right\}^{-1}\]

where $k=\omega\sqrt{\mu\varepsilon}$, $\eta=\sqrt{\mu/\varepsilon}$, and $\beta=l\pi/d$.

The initial Gmsh mesh for this problem, from [`mesh/cavity_prism.msh`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/mesh/cavity_prism.msh), is shown below. We use quadratic triangular prism elements. There are also two other included mesh files, [`mesh/cavity_tet.msh`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/mesh/cavity_tet.msh) and [`mesh/cavity_hex.msh`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/mesh/cavity_hex.msh), which use curved tetrahedral and hexahedral elements, respectively.

    

There are two configuration files for this problem, [`cavity_pec.json`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/cavity_pec.json) and [`cavity_impedance.json`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/cavity_impedance.json).

In both, the [`config["Problem"]["Type"]`](../../config/problem/#config%5B%22Problem%22%5D) field is set to `"Eigenmode"`, and we use the mesh shown above. The material properties for Teflon are entered under [`config["Domains"]["Materials"]`](../../config/domains/#domains%5B%22Materials%22%5D). The [`config["Domains"]["Postprocessing"]["Energy]"`](../../config/domains/#domains%5B%22Postprocessing%22%5D%5B%22Energy%22%5D) object is used to extract the quality factor due to bulk dielectric loss; in this problem since there is only one domain this is trivial, but in problems with multiple material domains this feature can be used to isolate the energy-participation ratio (EPR) and associated quality factor due to different domains in the model.

The only difference between the two configuration files is in the `"Boundaries"` object: `cavity_pec.json` prescribes a perfect electric conductor (`"PEC"`) boundary condition to the cavity boundary surfaces, while `cavity_impedance.json` prescribes a surface impedance condition with the surface resistance $R_s = 0.0184\text{ }\Omega\text{/sq}$, for copper at $5\text{ GHz}$.

In both cases, we configure the eigenvalue solver to solve for the $15$ lowest frequency modes above $2.0\text{ GHz}$ (the dominant mode frequencies for both the $\text{TE}$ and $\text{TM}$ cases fall around $2.9\text{ GHz}$ frequency for this problem). A sparse direct solver is used for the solutions of the linear system resulting from the spatial discretization of the governing equations, using in this case a fourth-order finite element space.

The frequencies for the lowest-order $\text{TE}$ and $\text{TM}$ modes computed using the above formula for this problem are listed in the table below.

| $(n,m,l)$ | $f_{\text{TE}}$ | $f_{\text{TM}}$ | 
| $(0,1,0)$ | –– | $2.903605\text{ GHz}$ | 
| $(1,1,0)$ | –– | $4.626474\text{ GHz}$ | 
| $(2,1,0)$ | –– | $6.200829\text{ GHz}$ | 
| $(0,1,1)$ | $5.000140\text{ GHz}$ | $3.468149\text{ GHz}$ | 
| $(1,1,1)$ | $2.922212\text{ GHz}$ | $5.000140\text{ GHz}$ | 
| $(2,1,1)$ | $4.146842\text{ GHz}$ | $6.484398\text{ GHz}$ | 
| $(0,1,2)$ | $5.982709\text{ GHz}$ | $4.776973\text{ GHz}$ | 
| $(1,1,2)$ | $4.396673\text{ GHz}$ | $5.982709\text{ GHz}$ | 
| $(2,1,2)$ | $5.290341\text{ GHz}$ | $7.269033\text{ GHz}$ | 

First, we examine the output of the `cavity_pec.json` simulation. The file `postpro/cavity_pec/eig.csv` contains information about the computed eigenfrequencies and associated quality factors:

```
        m,                Re{f} (GHz),                Im{f} (GHz),                          Q,              Error (Bkwd.),               Error (Abs.)
 1.00e+00,        +2.904769618774e+00,        +5.809539013185e-04,        +2.500000146549e+03,        +1.449387653028e-12,        +7.540036376356e-11
 2.00e+00,        +2.922855211084e+00,        +5.845710181333e-04,        +2.500000152997e+03,        +4.185295099860e-12,        +2.177538890960e-10
 3.00e+00,        +2.922855211091e+00,        +5.845710195602e-04,        +2.500000146900e+03,        +4.066048506139e-12,        +2.115496886932e-10
 4.00e+00,        +3.469124240109e+00,        +6.938248207784e-04,        +2.500000148164e+03,        +3.960668275868e-12,        +2.068678233902e-10
 5.00e+00,        +4.148169830292e+00,        +8.296339324852e-04,        +2.500000151168e+03,        +4.055252705574e-12,        +2.130227517300e-10
 6.00e+00,        +4.148190946584e+00,        +8.296381556649e-04,        +2.500000151405e+03,        +3.532117949409e-12,        +1.855424766261e-10
 7.00e+00,        +4.397102627927e+00,        +8.794204902867e-04,        +2.500000150346e+03,        +5.963739489832e-12,        +3.140103824439e-10
 8.00e+00,        +4.397102627936e+00,        +8.794204906592e-04,        +2.500000149293e+03,        +6.384574319147e-12,        +3.361687121168e-10
 9.00e+00,        +4.628289679544e+00,        +9.256579075853e-04,        +2.500000126496e+03,        +4.034131297928e-10,        +2.128976666858e-08
 1.00e+01,        +4.628289679630e+00,        +9.256578988321e-04,        +2.500000150182e+03,        +7.532518244928e-12,        +3.975219050105e-10
 1.10e+01,        +4.777682694812e+00,        +9.555364959037e-04,        +2.500000162656e+03,        +6.699010720502e-12,        +3.540794316307e-10
 1.20e+01,        +5.001817899805e+00,        +1.000363532126e-03,        +2.500000169544e+03,        +6.629572323678e-12,        +3.512507732283e-10
 1.30e+01,        +5.001819850216e+00,        +1.000363934341e-03,        +2.500000139222e+03,        +8.086591041122e-12,        +4.284471573537e-10
 1.40e+01,        +5.001819850275e+00,        +1.000363930135e-03,        +2.500000149764e+03,        +6.695097439548e-12,        +3.547224598840e-10
 1.50e+01,        +5.291383739403e+00,        +1.058276704615e-03,        +2.500000152208e+03,        +6.672585060726e-12,        +3.546814339449e-10
```

Indeed we can find a correspondence between the analytic modes predicted and the solutions obtained by *Palace*. Since the only source of loss in the simulation is the nonzero dielectric loss tangent, we have $Q = Q_d = 1/0.0004 = 2.50\times 10^3$ in all cases.

Next, we run `cavity_impedance.json`, which  adds the surface impedance boundary condition. Examining `postpro/cavity_impedance/eig.csv` we see that the mode frequencies are roughly unchanged but the quality factors have fallen due to the addition of imperfectly conducting walls to the model:

```
        m,                Re{f} (GHz),                Im{f} (GHz),                          Q,              Error (Bkwd.),               Error (Abs.)
 1.00e+00,        +2.903862041358e+00,        +7.083558859914e-04,        +2.049719770233e+03,        +2.769256476509e-11,        +1.082198395185e-06
 2.00e+00,        +2.922328265274e+00,        +7.051097207574e-04,        +2.072250788998e+03,        +9.267378639727e-12,        +3.644587746684e-07
 3.00e+00,        +2.922328265288e+00,        +7.051097696536e-04,        +2.072250645307e+03,        +7.958633243039e-12,        +3.129896632661e-07
 4.00e+00,        +3.468364344431e+00,        +8.637816541789e-04,        +2.007662720788e+03,        +1.659022572863e-11,        +7.741241553683e-07
 5.00e+00,        +4.147136086696e+00,        +9.783359034379e-04,        +2.119484824957e+03,        +8.273156937920e-11,        +4.614674508459e-06
 6.00e+00,        +4.147136088397e+00,        +9.783356801460e-04,        +2.119485309569e+03,        +7.239668150681e-12,        +4.038206011203e-07
 7.00e+00,        +4.396752371757e+00,        +9.999996589602e-04,        +2.198376992473e+03,        +4.372306548392e-11,        +2.585424359875e-06
 8.00e+00,        +4.396752371793e+00,        +9.999848690982e-04,        +2.198409506673e+03,        +4.857364608511e-11,        +2.872248010230e-06
 9.00e+00,        +4.626848227587e+00,        +1.052954239877e-03,        +2.197079498887e+03,        +1.096181730241e-10,        +6.820723665502e-06
 1.00e+01,        +4.626848230303e+00,        +1.052954469640e-03,        +2.197079020757e+03,        +1.453173123788e-10,        +9.042015614623e-06
 1.10e+01,        +4.777130952885e+00,        +1.125535833506e-03,        +2.122158594719e+03,        +1.058759793365e-10,        +6.801603304626e-06
 1.20e+01,        +5.000482920527e+00,        +1.085153996687e-03,        +2.304043045291e+03,        +7.741624927863e-11,        +5.205577864651e-06
 1.30e+01,        +5.000486073154e+00,        +1.170206827783e-03,        +2.136582222629e+03,        +1.039615939034e-10,        +6.990528731918e-06
 1.40e+01,        +5.000486077199e+00,        +1.170206915364e-03,        +2.136582064451e+03,        +1.033071710792e-11,        +6.946524395317e-07
 1.50e+01,        +5.290573376526e+00,        +1.207021515897e-03,        +2.191582107086e+03,        +2.162885262178e-10,        +1.538634992203e-05
```

However, the bulk dielectric loss postprocessing results, computed from the energies written to `postpro/cavity_impedance/domain-E.csv`, still give $Q_d = 1/0.004 = 2.50\times 10^3$ for every mode as expected.

Focusing on the $\text{TE}_{011}$ mode with $f_{\text{TE},010} = 5.00\text{ GHz}$, we can read the mode quality factor $Q = 2.30\times 10^3$. Subtracting out the contribution of dielectric losses, we have

\[Q_c = \left(\frac{1}{Q}-\frac{1}{Q_d}\right)^{-1} = 2.94\times 10^4\]

which is the same as the analytical result given in Example 6.4 from [[1]](#References) for this geometry.

Finally, a clipped view of the electric field (left) and magnetic flux density magnitudes for the $\text{TE}_{011}$ mode is shown below.

       

### [Mesh convergence](#Mesh-convergence)[]()[](#Mesh-convergence)

The effect of mesh size can be investigated for the cylindrical cavity resonator using [`convergence_study.jl`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/convergence_study.jl). For a polynomial order of solution and refinement level, a mesh is generated using Gmsh using polynomials of the same order to resolve the boundary geometry. The eigenvalue problem is then solved for $f_{\text{TM},010}$ and $f_{\text{TE},111}$, and the relative error, $\frac{f-f_{\text{true}}}{f_{\text{true}}}$, of each mode plotted against $\text{DOF}^{-\frac{1}{3}}$, a notional mesh size. Three different element types are considered: tetrahedra, prisms and hexahedra, and the results are plotted below. The $x$-axis is a notional measure of the overall cost of the solve, accounting for polynomial order.

          

The observed rate of convergence for the eigenvalues are $p+1$ for odd polynomials and $p+2$ for even polynomials. Given the eigenmodes are analytic functions, the theoretical maximum convergence rate is $2p$ [[2]](#References). The figures demonstrate that increasing the polynomial order of the solution will give reduced error, however the effect may only become significant on sufficiently refined meshes.

## [Waveguide](#Waveguide)[]()[](#Waveguide)

This example demonstrates the eigenmode simulation type in  *Palace* to solve for the cutoff-frequencies of a circular waveguide. As with the cavity the interior material to be Silicon ($\varepsilon_r = 2.08$, $\tan\delta = 4\times 10^{-4}$), with cylindrical domain radius $a = 2.74\text{ cm}$, and length $d=2a = 5.48\text{ cm}$, however now periodic boundary conditions are applied in the $z$-direction. According to [[1]](#References), the cutoff frequencies for the transverse electric and magnetic modes are given by the formulae:

\[\begin{aligned} f_{\text{TE},nm} &= \frac{1}{2\pi\sqrt{\mu\varepsilon}} \frac{p'_{nm}}{a}\\ f_{\text{TM},nm} &= \frac{1}{2\pi\sqrt{\mu\varepsilon}} \frac{p_{nm}}{a} \end{aligned}\]

which are identical to those for the cavity modes, in the special case of $l=0$.

In addition to these pure waveguide modes, there are aliasing cavity modes corresponding to a full wavelength in the computational domain ($l=2$). In a practical problem these can be suppressed by choosing a smaller value of $d$ which shifts such modes to higher frequencies. The relevant modes are tabulated as

| $(n,m,l)$ | $f_{\text{TE}}$ | $f_{\text{TM}}$ | 
| $(0,1,0)$ | $4.626481\text{ GHz}$ | $2.903636\text{ GHz}$ | 
| $(1,1,0)$ | $2.223083\text{ GHz}$ | $4.626481\text{ GHz}$ | 
| $(2,1,0)$ | $3.687749\text{ GHz}$ | $6.200856\text{ GHz}$ | 
| $(3,1,0)$ | $5.072602\text{ GHz}$ | $7.703539\text{ GHz}$ | 
| $(0,1,2)$ | $5.982715\text{ GHz}$ | $4.776992\text{ GHz}$ | 
| $(1,1,2)$ | $4.396663\text{ GHz}$ | $5.982715\text{ GHz}$ | 
| $(2,1,2)$ | $5.290372\text{ GHz}$ | $7.269056\text{ GHz}$ | 
| $(3,1,2)$ | $6.334023\text{ GHz}$ | $8.586796\text{ GHz}$ | 

For this problem, we use curved tetrahedral elements from the mesh file [`mesh/cavity_tet.msh`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/mesh/cavity_tet.msh), and the configuration files [`waveguide.json`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/waveguide.json) and [`floquet.json`](https://github.com/awslabs/palace/blob/v0.16.0/examples/cylinder/floquet.json).

The main difference between these configuration files and those used in the cavity example is in the `"Boundaries"` object: `waveguide.json` specifies a perfect electric conductor (`"PEC"`) boundary condition for the exterior surface and a periodic boundary condition (`"Periodic"`) on the cross-sections of the cylinder (in the $z-$ direction). The periodic attribute pairs are defined by `"DonorAttributes"` and `"ReceiverAttributes"`, and the distance between them is given by the `"Translation"` vector in mesh units. In `floquet.json`, an additional `"FloquetWaveVector"` specifies the phase delay between the donor and receiver boundaries in the X/Y/Z directions.

The file `postpro/waveguide/eig.csv` contains information about the computed eigenfrequencies and associated quality factors:

```
        m,                Re{f} (GHz),                Im{f} (GHz),                          Q,              Error (Bkwd.),               Error (Abs.)
 1.00e+00,        +2.223255721650e+00,        +4.446511264136e-04,        +2.500000150733e+03,        +2.210853009235e-12,        +4.449779600279e-10
 2.00e+00,        +2.223255721673e+00,        +4.446511266945e-04,        +2.500000149180e+03,        +2.024520171867e-12,        +4.074747856823e-10
 3.00e+00,        +2.903861940005e+00,        +5.807723648916e-04,        +2.500000149477e+03,        +3.405773584407e-12,        +6.918293917640e-10
 4.00e+00,        +3.688035400885e+00,        +7.376070569822e-04,        +2.500000128615e+03,        +1.594839833556e-12,        +3.283714744706e-10
 5.00e+00,        +3.688035400913e+00,        +7.376070515678e-04,        +2.500000146986e+03,        +1.588485386831e-12,        +3.270631179849e-10
 6.00e+00,        +4.396748741792e+00,        +8.793497288214e-04,        +2.500000105544e+03,        +1.024381602102e-11,        +2.140523838971e-09
 7.00e+00,        +4.396748741829e+00,        +8.793496709514e-04,        +2.500000270090e+03,        +2.469107146396e-11,        +5.159388549143e-09
 8.00e+00,        +4.396843854500e+00,        +8.793687606815e-04,        +2.500000079051e+03,        +3.976553172187e-12,        +8.309330281148e-10
 9.00e+00,        +4.396843854688e+00,        +8.793687158584e-04,        +2.500000206587e+03,        +4.397125640453e-12,        +9.188150554590e-10
 1.00e+01,        +4.626835691343e+00,        +9.253671413707e-04,        +2.500000041619e+03,        +9.936655287438e-12,        +2.087363252044e-09
 1.10e+01,        +4.626835691616e+00,        +9.253671544141e-04,        +2.500000006529e+03,        +1.351955157903e-11,        +2.840011486162e-09
 1.20e+01,        +4.626845256359e+00,        +9.253690423262e-04,        +2.500000074168e+03,        +6.470719086602e-12,        +1.359284777998e-09
 1.30e+01,        +4.777149611499e+00,        +9.554298664957e-04,        +2.500000196018e+03,        +9.308770536101e-12,        +1.962495987580e-09
 1.40e+01,        +4.777237409644e+00,        +9.554473562290e-04,        +2.500000378903e+03,        +1.979632453129e-11,        +4.173514633945e-09
 1.50e+01,        +5.073016461107e+00,        +1.014603274788e-03,        +2.500000092956e+03,        +3.441919582771e-12,        +7.309928051724e-10
```

In common with the PEC cavity $Q = Q_d = 1/0.0004 = 2.50\times 10^3$ in all cases, and all the anticipated waveguide modes are recovered with $\text{TE}_{1,1}$ having the lowest cutoff frequency followed by $\text{TM}_{0,1}$ and $\text{TE}_{2,1}$, while the aliasing mode $\text{TE}_{1,1,2}$ has marginally lower frequency than the waveguide modes $\text{TE}_{0,1}$ and $\text{TM}_{1,1}$ ($4.397\text{ GHz}$ compared to $4.627\text{ GHz}$) and is thus found first.

## [References](#References)[]()[](#References)

[1] D. M. Pozar, *Microwave Engineering*, Wiley, Hoboken, NJ, 2012.
[2] A. Buffa, P. Houston, I. Perugia, Discontinuous Galerkin computation of the Maxwell eigenvalues on simplicial meshes, *Journal of Computational and Applied Mathematics* 204 (2007) 317-333.
