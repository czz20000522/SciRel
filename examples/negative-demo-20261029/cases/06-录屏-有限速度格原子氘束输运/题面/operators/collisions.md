# Atomic collision and source statement

This statement specifies a steady, one-dimensional slab model with an axisymmetric two-dimensional velocity distribution. It is a static reconstruction of the model rules, not numerical validation. No solver, rate evaluator, capture, replay, or scientific calculation was run to prepare it.

The finite candidate uses the explicit options: electron ionization and radiative recombination fits given below; Maxwellian-weighted charge exchange enabled; all three elastic relaxation terms disabled; recombination enabled; ion-density correction enabled with zero molecular-ion density; side-wall diameter zero. Its spatial/velocity mesh, inflow, plasma profiles, generation procedure, and requested observables must also be specified. This collision statement and the linked mesh projection supply all active local rate coefficients and distribution rules for that candidate. It does not close the default table-driven model or the complete elastic-collision family.

## Coordinates, units, and quadrature

Let isotope factor `mu=1` for hydrogen and `mu=2` for deuterium, atomic mass `m=mu*m0`, `m0=1.6726231e-27 kg`, and charge magnitude `e=1.602177e-19 C`. Temperatures are in eV. For a positive reference temperature `T0`, define

`v0=sqrt(2*e*T0/m)`.

Velocity coordinates `r_i>0` and `u_j` are dimensionless: physical perpendicular speed is `v0*r_i` and physical slab velocity is `v0*u_j`. No axial node is zero; the axial nodes are symmetric, with negative and positive halves. A distribution `f[i,j,k]` integrates directly to density in `m^-3`; it is a density per dimensionless velocity volume. A source distribution `s[i,j,k]` integrates to a source in `m^-3 s^-1`.

Use midpoint cell boundaries. The first radial left boundary is zero; internal radial boundaries are `(r_i+r_(i+1))/2`; the last is `(3*r_last-r_previous)/2`. Axial end boundaries are `(3*u_first-u_second)/2` and `(3*u_last-u_previous)/2`, with midpoint internal boundaries. Write

`dr_i=r_right_i-r_left_i`, `R_i=pi*(r_right_i^2-r_left_i^2)`, `du_j=u_right_j-u_left_j`, `q_ij=R_i*du_j`, and `<g>=sum_i,j q_ij*g_ij`.

Thus `n=<f>`, physical mean velocity `U=v0*<u*f>/n`, and atomic temperature `T=m*v0^2*<(r^2+(u-U/v0)^2)*f>/(3*e*n)`. Molecular moments use the same `v0` and a mass factor `2*m` in the temperature. Cells of nonpositive molecular density retain mean velocity zero and temperature 1 eV. These are discrete moment definitions; replacing the cell measures by pointwise `2*pi*r*dr*du` changes the model.

## Normalized transport operator

At each position the normalized equation is

`u*d(f)/dx = S + beta_cx - alpha*f + omega_a*M_a + omega_i*M_i + omega_m*M_m`,

where the physical collision/source operator is `v0` times the right-hand side. The fixed source and loss are

`S=s/v0 + I_recomb*F_i*n_i*n_e*K_rec/v0`,

`alpha=n_e*K_ion/v0 + I_cx*alpha_cx + omega_a+omega_i+omega_m + gamma_wall`.

`F_i` is the discrete unit-density Maxwell distribution specified below, with temperature `T_i` and physical mean speed `U_i`. Ion density is `n_i=n_e` by default. If correction is explicitly enabled, it is `max(n_e-n_mion,0.01*n_e)`. The same floor is applied in the uncorrected case. The molecular-ion temperature is accepted as an input by the source interface but does not enter these atomic operators.

With all collision flags off, electron ionization still acts; recombination follows its own flag. A missing user source or molecular distribution means a zero array. The three elastic frequencies are zero if any position has atomic density `<=0`, before any local elastic-frequency calculation. The finite candidate has zero side-wall loss. A formal positive-diameter wall loss would be `gamma_wall=2*r/D` in normalized units, but the source implementation's array assignment does not define a general rectangular-grid realization reliably; positive-diameter cases remain on hold.

## Electron ionization and radiative recombination for the finite candidate

All polynomial coefficients below are in ascending power order: `P(z;c)=sum_l c[l]*z^l`; use natural logarithms unless marked `log10`. `clip(x,a,b)=min(max(x,a),b)` is applied before logarithms.

For electron-impact ionization, set `t=clip(T_e,0.1,2.01e4)` and

`I(T_e)=K_ion(T_e)=1e-6*exp(P(ln(t);b))` in `m^3 s^-1`, with

```text
b = [-3.271396786375e1,  1.353655609057e1,
     -5.739328757388e0,  1.563154982022e0,
     -2.877056004391e-1, 3.482559773737e-2,
     -2.631976175590e-3, 1.119543953861e-4,
     -2.039149852002e-6]
```

For recombination to the atomic ground state, use the same clipped `t`, `B=13.58/t`, and

`K_rec(T_e)=3.92e-20*B^(3/2)/(B+0.35)` in `m^3 s^-1`.

The physical integrated recombination source is `n_i*n_e*K_rec`. Its injected velocity distribution is `F_i`. The electron-ionization sink is independent of neutral velocity.

## Maxwellian-weighted charge exchange for the finite candidate

Define the hydrogen-reference energy and scaled ion temperature at every velocity node:

`E=clip(m0*v0^2*(r_i^2+(u_j-U_i/v0)^2)/(2*e),0.1,2.0e4)` and `theta=T_i/mu`.

The rate itself clips each argument again to `[0.1,2.01e4]`. With `L_E=ln(clip(E,0.1,2.01e4))` and `L_T=ln(clip(theta,0.1,2.01e4))`, define

`C(theta,E)=K_cx(theta,E)=1e-6*exp(sum_a=0..8 sum_b=0..8 A[a,b]*L_T^a*L_E^b)` in `m^3 s^-1`.

Rows of the following complete coefficient matrix are powers of temperature; columns are powers of energy:

```text
A = [
[-1.829079581680e1,  1.640252721210e-1,  3.364564509137e-2,  9.530225559189e-3, -8.519413589968e-4, -1.247583860943e-3,  3.014307545716e-4, -2.499323170044e-5,  6.932627237765e-7],
[ 2.169137615703e-1,-1.106722014459e-1, -1.382158680424e-3,  7.348786286628e-3, -6.343059502294e-4, -1.919569450380e-4,  4.075019351738e-5, -2.850044983009e-6,  6.966822400446e-8],
[ 4.307131243894e-2, 8.948693624917e-3, -1.209480567154e-2, -3.675019470470e-4,  1.039643390686e-3, -1.553840717902e-4,  2.670827249272e-6,  7.695300597935e-7, -3.783302281524e-8],
[-5.754895093075e-4, 6.062141761233e-3,  1.075907881928e-3, -8.119301728339e-4,  8.911036876068e-6,  3.175388949811e-5, -4.515123641755e-6,  2.187439283954e-7, -2.911233951880e-9],
[-1.552077120204e-3,-1.210431587568e-3,  8.297212635856e-4,  1.361661816974e-4, -1.008928628425e-4,  1.080693990468e-5,  5.106059413591e-7, -1.299275586093e-7,  5.117133050290e-9],
[-1.876800283030e-4,-4.052878751584e-5, -1.907025662962e-4,  1.141663041636e-5,  1.775681984457e-5, -3.149286923815e-6,  3.105491554749e-8,  2.274394089017e-8, -1.130988250912e-9],
[ 1.125490270962e-4, 2.875900435985e-5,  1.338839628570e-5, -4.340802793033e-6, -7.003521917385e-7,  2.318308730487e-7, -6.030983538280e-9, -1.755944926274e-9,  1.005189187279e-10],
[-1.238982763007e-5,-2.616998139678e-6, -1.171762874107e-7,  3.517971869029e-7, -4.928692832866e-8,  1.756388998863e-10,-1.446756795654e-10, 7.143183138281e-11,-3.989884105603e-12],
[ 4.163596197181e-7, 7.558092849125e-8, -1.328404104165e-8, -9.170850253981e-9,  3.208853883734e-9, -3.952740758950e-10, 2.739558475782e-11,-1.693040208927e-12, 6.388219930167e-14]
]
```

Then

`alpha_cx[i,j]=n_i*K_cx(theta,E[i,j])/v0`,

`beta_cx[f][i,j]=F_i[i,j]*<alpha_cx*f>`.

The source has exactly the ion Maxwell distribution but is normalized by the velocity-integrated charge-exchange loss of the input generation. It must not be replaced with `n_i*K_cx*F_i*n_H/v0` using a single arbitrarily averaged rate. With unit-density `F_i`, the discrete charge-exchange source and sink have equal integrated particle rates.

## Discrete shifted Maxwell distribution

The unique definition of the corrected, unit-density discrete distribution is [mesh projection, section 6](mesh-projection.md). Use it for the ion background with desired physical mean `U_i`, temperature `T_i`, and species multiplier `a=1`, on the same `r,u` nodes, cell measures, reference temperature, and isotope mass defined here. The elastic targets below use the same distribution constructor with `a=1`. Sampling a continuous Maxwell density and normalizing only its density changes the stated discrete model.

That definition includes the initial exponent clamp, density normalization, exact boundary stencils, one correction pass, direction-pair order, strict sign tests, fallback behavior, and final density normalization. The active positive-input construction has no post-correction positivity limiter. Exact final moments and nonnegative values require separate validation on the stated mesh; this static statement makes neither claim.

## Other charge exchange and elastic operators

These definitions keep the complete family visible. They are outside the finite candidate, so a result for that candidate establishes nothing about these branches.

For two velocity cells `p=(i,j)` and `q=(l,h)`, use five angles `phi_t=pi*(t+0.5)/5`, `t=0..4`, with weights `1/5`. Define

`d_r^2=r_i^2+r_l^2-2*r_i*r_l*cos(phi_t)`,

`g^2=d_r^2+(u_j-u_h)^2`, `g=sqrt(g^2)`, `d_u=u_j-u_h`, `W=d_r^2-2*d_u^2`.

The common angular average is an arithmetic mean over these five nodes. The partner-cell quadrature weight is always `q_lh`. Matrix storage may use radial index varying fastest, but physical indices must agree with these expressions.

For the direct charge-exchange branch,

`L_cx[p,q]=q_lh*mean_t(g*sigma_cx(m0*v0^2*g^2/(2*e)))`,

`alpha_cx[p]=sum_q L_cx[p,q]*n_i*F_i[q]`,

`beta_cx[f][p]=n_i*F_i[p]*sum_q L_cx[p,q]*f[q]`.

For ion-atom and molecule-atom momentum transfer, respectively,

`L_i[p,q]=q_lh*d_u*mean_t(g*sigma_i(m0*v0^2*g^2/(2*e)))`,

`L_m[p,q]=q_lh*d_u*mean_t(g*sigma_m(m0*v0^2*g^2/(2*e)))`,

`a_i[p]=sum_q L_i[p,q]*n_i*F_i[q]`, `a_m[p]=sum_q L_m[p,q]*f_m[q]`.

For atom-atom viscosity transfer,

`L_a[p,q]=q_lh*mean_t(W*g*sigma_a(m*v0^2*g^2/(2*e))/8)`, `a_a[p]=sum_q L_a[p,q]*f[q]`.

The cross sections are in `m^2`, despite inverse-area unit labels in some descriptions. All energy fits below return `1e-4*exp(P(ln(E_clipped);c))`:

| Cross section | Energy clip (eV) | Ascending coefficients |
| --- | --- | --- |
| Charge exchange | `[0.1,2.01e4]` | `[-3.274123792568e1,-8.916456579806e-2,-3.016990732025e-2,9.205482406462e-3,2.400266568315e-3,-1.927122311323e-3,3.654750340106e-4,-2.788866460622e-5,7.422296363524e-7]` |
| Atom-atom viscosity | `[0.03,1.01e4]` | `[-3.344860e1,-4.238982e-1,-7.477873e-2,-7.915053e-3,-2.686129e-4]` |
| Atom-molecule momentum transfer | `[0.03,1.01e4]` | `[-3.495671e1,-4.062257e-1,-3.820531e-2,-9.404486e-3,3.963723e-4]` |
| Ion-atom momentum transfer, clipped `E<10` | `[0.001,1.01e5]` | `[-3.233966e1,-1.126918e-1,5.287706e-3,-2.445017e-3,-1.044156e-3,8.419691e-5,3.824773e-5]` |
| Ion-atom momentum transfer, clipped `E>=10` | `[0.001,1.01e5]` | `[-3.231141e1,-1.386002e-1]` |

For positive atom density everywhere, mixed elastic frequencies are

`omega_i=max(<a_i*f>/(n*delta_i),0)`, `delta_i=sign((U-U_i)/v0)*max(abs((U-U_i)/v0),0.01)`,

`omega_m=max(<a_m*f>/(n*delta_m),0)`, `delta_m=sign((U-U_m)/v0)*max(abs((U-U_m)/v0),0.01)`.

For atom-atom scattering, the initial anisotropy is literally

`w_a=<(r^2-2*(u-U)^2)*f>/n`,

using the physical velocity `U` without division by `v0` in this one expression. On later outer passes it is

`w_a=-<(r^2-2*u^2)*(M_a_sum-f)>/n`.

Then `omega_a=max(<a_a*f>/(n*sign(w_a)*max(abs(w_a),0.001)),0)`. These formulae are recorded as present behavior; no scientific correction to their normalization or zero-sign rule is implied. Exact zero drift or anisotropy remains a zero denominator. Nonfinite outcomes are not repaired here.

For an input generation with density `n_g`, mean `U_g`, and atom temperature `T_g`, targets have density `n_g` and the following corrected-Maxwell moments:

| Target | Physical mean speed | Temperature (eV) |
| --- | --- | --- |
| Atom-atom | `U_g` | `T_g` |
| Ion-atom | `(U_g+U_i)/2` | `T_g+(1/2)*(T_i-T_g+m*(U_i-U_g)^2/(6*e))` |
| Molecule-atom | `(U_g+2*U_m)/3` | `T_g+(4/9)*(T_m-T_g+2*m*(U_m-U_g)^2/(6*e))` |

Each normalized elastic contribution is `omega*(M-f)`. The frequency is computed from the current total/seed distribution; target sources are built separately from each previous generation. With no molecular density in the entire supplied distribution, the molecule-atom elastic flag is forced off. Zero generation densities are not guarded in the target moment divisions.

## Rate choices and precise scope of the remaining gaps

The electron-rate selector has four behaviors. The finite candidate explicitly selects the two analytic fits above. The default instead uses density-dependent ionization and recombination tables with cubic interpolation of `log10(rate)` against `log10(n_e in cm^-3)` and `log10(T_e in eV)`, clipped to the table domains, then converts `cm^3 s^-1` to `m^3 s^-1`. The restricted ADAS tables have not been copied, read, evaluated, or replaced. Their admitted numeric contents/domain are required to close that default branch.

A second tabulated collisional-radiative option uses a built-in `15 x 60` ionization table: density coordinate `clip(2*(log10(n_e/1e6)-10),0,14)`, temperature coordinate `clip(10*(log10(T_e)+1.2),0,59)`, bilinear interpolation in natural-log table values, exponentiation, then division by `1e6`. Its recombination remains the analytic ground-state fit. Its table values are source-defined, but not included in this public statement; this is a bounded data-admission gap, not an unknown physical equation.

A third collisional-radiative option evaluates stored tensor-product B-spline coefficients for both rates at clipped `ln(n_e)` and `ln(T_e)`, exponentiating the result. The stored knots, spline order, ionization coefficients, and recombination coefficients are numerical dependencies not admitted here. Their producer is explicitly unavailable in the read implementation; they cannot be silently regenerated or substituted.

The complete family has additional interpretation/validation holds: mixed-frequency exact-zero denominators; physical versus normalized speed in initial self-collision anisotropy; no protection for empty generation target moments; one compensation pass without a positivity guarantee; positive-diameter wall array assignment; and repeat-call molecular-moment invalidation. These are localized to their branches and do not prevent the finite candidate from having a complete static collision/source definition. The finite candidate still needs its transport inputs and a separate validation/acceptance decision; no numeric answer, error estimate, scientific correctness claim, or whole-family closure follows from this static document.
