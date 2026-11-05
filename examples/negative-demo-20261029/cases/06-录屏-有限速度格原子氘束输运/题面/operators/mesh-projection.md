# Atomic slab transport: mesh and velocity projection statement

This statement specifies a finite velocity discretization, its profile-dependent spatial mesh, and the moment adjustment used to represent a shifted Maxwellian. It contains no numerical reference result. Its evidence status is static specification only: no model import, execution, capture, replay, or new scientific calculation was performed.

## 1. Scope, coordinates, and required rate functions

The active slab problem uses an atom mass $m=\mu m_H$, $\mu=2$, $m_H=1.6726231\times10^{-27}\,\mathrm{kg}$, and $q=1.602177\times10^{-19}\,\mathrm{J/eV}$. The input coordinate is $x$ in metres; temperatures are in eV, density in $\mathrm{m}^{-3}$, and physical axial velocity in $\mathrm{m/s}$. The profile-dependent mesh construction below takes the prescribed ionization coefficient $I(T_e)$ and charge-exchange coefficient $C(T_i,E)$, both in $\mathrm{m^3/s}$, as mathematical function inputs. Their complete public numerical definitions belong to the accompanying collision-rate statement; no private table or source callable is an implicit input here.

For the fixed candidate, the original profile has 50 uniformly spaced points from 0 to 0.05 m, $T_i=T_e$ rising linearly from 5 to 100 eV, $n_e$ rising linearly from $10^{19}$ to $5\times10^{19}\,\mathrm{m}^{-3}$, and zero plasma flow. The settings are $N_v=6$, spatial factor $F=0.3$, and added energy list $E_0=[3]$ eV. There is no pipe-wall loss in this candidate. A generic pipe-diameter term is given below only to make the mesh rule explicit.

Write $r_i=v_{r,i}$ and $z_j=v_{x,j}$ for dimensionless radial and axial velocity coordinates. Their physical values are $v_*r_i$ and $v_*z_j$, where

\[
v_* = \sqrt{\frac{2qT_*}{\mu m_H}}.
\]

A distribution array has axis order **radial velocity, axial velocity, space**, $f_{ijk}=f[r_i,z_j,x_k]$. A single velocity slice is $f_{ij}$. Radial centres are positive and increasing. Axial centres are increasing, even in number, have no zero, and are exactly symmetric about zero. The velocity integration convention is

\[
\mathcal N(f)=\sum_{ij}V_{ij}f_{ij},\qquad
\mathcal U(f;h)=\frac{h}{\mathcal N(f)}\sum_{ij}V_{ij}z_j f_{ij},\qquad
\mathcal E(f;h)=\frac{h^2}{\mathcal N(f)}\sum_{ij}V_{ij}(r_i^2+z_j^2)f_{ij}.
\]

In physical moments $h=v_*$. In intermesh temperature-scaled moment correction $h=\sqrt{T_*}$, so that the two target moments there have units $\sqrt{\mathrm{eV}}$ and eV. The distribution amplitude is defined by this discrete integration convention; an extra factor $v_*^3$ is not inserted into these sums.

## 2. Velocity centres and normalization temperature

Given a temperature list $L$, append every strictly positive entry of $E_0$ to $L$. If a positive temperature ceiling $T_{\max}$ is requested, retain only entries strictly below it; the active problem has no ceiling. Let

\[
T_{\min}=\min L,\quad T_{\max,L}=\max L,\quad T_*=\operatorname{nanmean}(L),\quad v_{\max}=3.5.
\]

The mean is the unweighted arithmetic mean of the retained profile samples and appended energies, ignoring NaNs. It is not a spatially weighted average. For $\ell=0,\ldots,N_v$, construct

\[
v_\ell = \begin{cases}
3.5\ell/N_v,&T_{\max,L}-T_{\min}\le0.1T_{\max,L},\\
(gb)\ell+b\ell^2,&\text{otherwise},
\end{cases}
\]

where

\[
g=\frac{2N_v\sqrt{T_{\min}/T_{\max,L}}}{1-\sqrt{T_{\min}/T_{\max,L}}},\qquad
b=\frac{3.5}{N_v(N_v+g)}.
\]

For each positive energy $E$ in the given order, insert $\sqrt{E/T_*}$ immediately before the first existing centre strictly greater than it, or append it if there is no greater centre. This insertion does not deduplicate equal centres and can extend past 3.5. Remove the initial zero to obtain $r$; form $z=(-r_{N_r-1},\ldots,-r_0,r_0,\ldots,r_{N_r-1})$. Consequently $N_v$ is a base resolution, not necessarily the final radial count. The return ordering is $z,r,T_*$.

The active positive temperatures, one positive added energy, and no ceiling avoid empty-temperature and negative-square-root cases. The general constructor does not provide explicit input validation for those cases or for nonpositive $N_v$.

## 3. Finite velocity cells

At least two centres on each velocity axis are needed by the endpoint expressions. Define radial edges

\[
r^-_0=0,\quad r^-_i=\tfrac12(r_{i-1}+r_i)\ (i>0),\qquad
r^+_i=\tfrac12(r_i+r_{i+1})\ (i<N_r-1),\quad
r^+_{N_r-1}=r_{N_r-1}+\tfrac12(r_{N_r-1}-r_{N_r-2}).
\]

For the axial edges use interior midpoints and finite exterior half-cells:

\[
z^-_0=z_0-\tfrac12(z_1-z_0),\quad
z^-_j=\tfrac12(z_{j-1}+z_j)\ (j>0),
\]
\[
z^+_j=\tfrac12(z_j+z_{j+1})\ (j<N_x^v-1),\quad
z^+_{N_x^v-1}=z_{N_x^v-1}+\tfrac12(z_{N_x^v-1}-z_{N_x^v-2}).
\]

Then

\[
\Delta r_i=r^+_i-r^-_i,\quad \Delta z_j=z^+_j-z^-_j,\quad
W_i=\pi[(r^+_i)^2-(r^-_i)^2],\quad V_{ij}=W_i\Delta z_j.
\]

An additional stored radial quantity is $W_i^{(1)}=\frac{4\pi}{3}[(r^+_i)^3-(r^-_i)^3]$. The first radial cell is an annular disk from zero to its midpoint edge, even though its centre is strictly positive. The final cells are finite; they do not reach infinity. In all moments in this statement, the integrand is evaluated at the cell centre and multiplied by $V_{ij}$.

## 4. Profile-dependent spatial mesh

All one-dimensional profile interpolations in this section are piecewise linear with extrapolation enabled. Given original points $x_a$, first set $R_a=n_a I(T_{e,a})$, and form a cumulative optical-depth estimate

\[
y_0=0,\qquad
y_a=y_{a-1}-\frac{(x_a-x_{a-1})(R_a+R_{a-1})}{2v_{10}},\qquad
v_{10}=\sqrt{\frac{2q(10\,\mathrm{eV})}{\mu m_H}}.
\]

Let $y_t=\max(-5,\min_a y_a)$. Interpolate $x$ as a function of $y$ at $y_t$, and set $x_{\mathrm{end}}=\min(x(y_t),\max_a x_a)$, $x_{\mathrm{start}}=x_0$. This is a mesh-range heuristic corresponding to an $e^{-5}$ attenuation estimate. It does not itself impose the far-end transport boundary condition. The positive-rate active profiles give a strictly decreasing $y$. General inputs with repeated $y$ values do not acquire a special inverse-interpolation rule in this statement.

Construct 1001 uniformly spaced fine points on $[x_{\mathrm{start}},x_{\mathrm{end}}]$, clipped to $[x_{\mathrm{start}},\max x]$, and linearly interpolate $T_i,T_e,n_e,D$ onto them. First run the velocity-centre construction on this fine ion-temperature list, giving preliminary $r,z,T_*^{\mathrm{fine}},v_*^{\mathrm{fine}}$. Define

\[
E_{\min}=\frac{m_H(v_*^{\mathrm{fine}}\min r)^2}{2q},\qquad
\Gamma_{\mathrm{wall}}(x)=\begin{cases}2(\max r)v_*^{\mathrm{fine}}/D(x),&D(x)>0,\\0,&D(x)\le0.\end{cases}
\]

The factor in $E_{\min}$ is $m_H$, exactly as written, even when $\mu=2$. It must not silently be replaced by $\mu m_H$. In the active candidate $D=0$, so the wall term vanishes. The fine-grid interaction estimate is

\[
R_f(x)=n_e(x)\{I(T_e(x))+C(T_i(x),E_{\min})\}+\Gamma_{\mathrm{wall}}(x).
\]

The prescribed maximum spacing is

\[
d(x)=\min\left[F(0.8)\frac{2v_*^{\mathrm{fine}}\min r}{R_f(x)},\;0.02F\right].
\]

First evaluate $d$ at all 1001 fine-grid points. Every subsequent $d(p)$ and $d(t)$ below is piecewise-linear interpolation of that already computed spacing array, with extrapolation enabled; do not interpolate profiles to $p$ or $t$ and recompute the nonlinear spacing expression. Build nodes backward. Start $p_0=x_{\mathrm{end}}$. At a retained point $p>x_{\mathrm{start}}$, let $d_1=d(p)$, $t=p-d_1$, and $d_2=d(t)$ if $t>x_{\mathrm{start}}$, otherwise $d_2=d_1$. The next trial point is $p-\min(d_1,d_2)$. Retain trial points only while they exceed $x_{\mathrm{start}}$. Reverse the retained points and prepend exactly $x_{\mathrm{start}}$. The final list includes $x_{\mathrm{end}}$ once.

Interpolate the four fine-grid profiles onto these spatial nodes. Run the velocity-centre construction again on the resulting ion-temperature list, with the same $N_v,E_0$. **These final velocity centres and $T_*$ are the transport mesh.** The spacing estimate used the preliminary fine-grid velocity mesh; it is not recomputed after the final velocity normalization changes.

No iteration count or minimum positive-step guard is specified for this backward mesh loop. The active problem prescribes positive temperatures, positive rates, $F>0$, and a nondegenerate interval. There is no automatic mesh-refinement retry around a subsequent solver failure.

## 5. Solver spacing acceptance and the spatial stencil

Let $\alpha_{ijk}$ be the solver's total normalized loss coefficient, with units $\mathrm{m}^{-1}$ because the streaming coordinate $z_j$ is dimensionless. At each spatial node, form

\[
L_k=\min\left(10^{32},\;\left\{\frac{2z_j}{\alpha_{ijk}}:z_j>0,\ \frac{2z_j}{\alpha_{ijk}}\text{ finite and strictly positive}\right\}\right).
\]

An empty candidate set leaves $L_k=10^{32}$. For every interval $\Delta x_k=x_{k+1}-x_k$, require $\Delta x_k\le\min(L_k,L_{k+1})$. Equality passes. A violation prints diagnostics and raises an exception with message `x mesh spacing is too large`. This check uses positive axial velocities only; invalid and nonpositive candidate ratios are discarded. It does not request or perform a finer mesh.

For completeness, given normalized source $S_{ijk}$, the stencil coefficients on interval $k$ are

\[
D^+_{ijk}=2z_j+\Delta x_k\alpha_{ij,k+1},\quad
A_{ijk}=\frac{2z_j-\Delta x_k\alpha_{ijk}}{D^+_{ijk}},\quad
B_{ijk}=\frac{\Delta x_k}{D^+_{ijk}},\quad
F_{ijk}=B_{ijk}(S_{ijk}+S_{ij,k+1})\quad(z_j>0),
\]

\[
D^-_{ij,k+1}=-2z_j+\Delta x_k\alpha_{ijk},\quad
C_{ij,k+1}=\frac{-2z_j-\Delta x_k\alpha_{ij,k+1}}{D^-_{ij,k+1}},\quad
D_{ij,k+1}=\frac{\Delta x_k}{D^-_{ij,k+1}},\quad
G_{ij,k+1}=D_{ij,k+1}(S_{ijk}+S_{ij,k+1})\quad(z_j<0).
\]

Unused coefficient slots are zero. Boundary conditions, collision generations, recombination, and reported transport moments are specified in the companion slab statement.

## 6. Discrete shifted Maxwellian and its correction

For each spatial slice, prescribe positive temperature $T$, physical shift $u$, molecular factor $M=1$ for the active atom, and $v_*$ from the final mesh. Start with

\[
a_{ij}=-\frac{M T_*}{T}\left[r_i^2+(z_j-u/v_*)^2\right],\qquad
\widetilde a_{ij}=\begin{cases}a_{ij},&-80<a_{ij}<0,\\-80,&\text{otherwise},\end{cases}
\]

and normalize $f_{ij}=\exp(\widetilde a_{ij})/\mathcal N(\exp\widetilde a)$. Notice the strict inequalities: an exactly zero exponent becomes $-80$. This does not occur for the active positive radial centres. A nonpositive target temperature leaves the entire slice zero and skips correction.

The physical correction targets are

\[
u_{\mathrm{target}}=u,\qquad
e_{\mathrm{target}}=u^2+\frac{3qT}{M\mu m_H}.
\]

The active ion distribution uses $T=T_i(x_k)$, $u=v_{xi}(x_k)=0$, $M=1$. The following full correction rule is part of the specification; matching only these two target numbers does not determine the same discrete distribution.

For a slice of density factor $n_b$, define weighted populations $H_{ij}=f_{ij}V_{ij}/n_b$, and

\[
t_{ij}=H_{ij}/\Delta z_j,\quad b_{ij}=H_{ij}z_j/\Delta z_j,\quad c_{ij}=H_{ij}r_i/\Delta r_i.
\]

Here $n_b=1$ for a normalized Maxwellian. Extend $t,b,c$ with one layer of zero cells on all sides. Define

\[
A^+_{ij}=t_{i,j-1}-t_{ij},\qquad A^-_{ij}=t_{ij}-t_{i,j+1}.
\]

Let $p$ be the first positive axial index and $q=p-1$ the last negative index. The axial contributions to $B^+$ and $B^-$ are exactly the following, using zero exterior values:

| Axial index | $B^+$ axial part | $B^-$ axial part |
|---|---|---|
| $j<q$ | $b_{ij}-b_{i,j+1}$ | $b_{i,j-1}-b_{ij}$ |
| $j=q$ | $b_{iq}$ | $b_{i,q-1}$ |
| $j=p$ | $-b_{ip}$ | $-b_{i,p+1}$ |
| $j>p$ | $b_{i,j-1}-b_{ij}$ | $b_{ij}-b_{i,j+1}$ |

Add $c_{i-1,j}-c_{ij}$ to $B^+_{ij}$. For $B^-$, add $-c_{1j}$ at $i=0$, and $c_{ij}-c_{i+1,j}$ at $i\ge1$, with $c_{N_r,j}=0$. These endpoint rules are deliberate parts of the recorded discrete algorithm.

Compute present moments with the chosen velocity scale $h$:

\[
u_0=\frac{h}{n_b}\sum_{ij}V_{ij}z_jf_{ij},\qquad
e_0=\frac{h^2}{n_b}\sum_{ij}V_{ij}(r_i^2+z_j^2)f_{ij}.
\]

For a selected pair $A=A^\sigma,B=B^\tau$, let

\[
T_{A1}=h\sum_{ij}z_jA_{ij},\quad T_{A2}=h^2\sum_{ij}(r_i^2+z_j^2)A_{ij},\quad
T_{B1}=h\sum_{ij}z_jB_{ij},\quad T_{B2}=h^2\sum_{ij}(r_i^2+z_j^2)B_{ij}.
\]

Use $h=v_*$ for the Maxwellian. Set $\Delta u=u_{\mathrm{target}}-u_0$, $\Delta e=e_{\mathrm{target}}-e_0$, $d=T_{A2}T_{B1}-T_{A1}T_{B2}$. If $d\ne0$ and $T_{A1}\ne0$, set

\[
\beta=\frac{T_{A2}\Delta u-T_{A1}\Delta e}{d},\qquad
\alpha=\frac{\Delta u-T_{B1}\beta}{T_{A1}};
\]

otherwise set both scalars to zero. Enumerate $(\sigma,\tau)=(+,+),(+,-),(-,+),(-,-)$, stopping at the first pair satisfying $\alpha\,\operatorname{sgn}(\sigma)>0$ and $\beta\,\operatorname{sgn}(\tau)>0$. If no pair passes, use the fourth pair and its computed scalars. No exception is raised for the absence of a passing sign pair. The correction is $\delta H=\alpha A+\beta B$.

For the active Maxwellian, apply the full step $f'_{ij}=n_b(H_{ij}+\delta H_{ij})/V_{ij}$, then renormalize by its discrete density. There is one correction call, followed by this normalization, rather than iteration to a moment tolerance. No post-correction positivity clipping or residual tolerance check is prescribed for this branch. Finite-tail leakage, degeneracy of the two-moment linear solve, and the final renormalization mean that exact density, energy, drift, and positivity must not all be asserted as proven properties from this static specification. They are the intent and the explicit algorithm, with the limits stated here.

## 7. Optional intermesh projection: separate scope

This operation is not called by the active lightweight slab solve. It is specified here to expose the wider mesh-transfer behavior without making it a requirement for that fixed candidate.

For source mesh $a$, target mesh $b$, let $s_v=\sqrt{T_{*,b}/T_{*,a}}$. First require at least one target centre within the source centre range on each axis: $r_a$ versus $s_vr_b$, $z_a$ versus $s_vz_b$, and $x_a$ versus $x_b$. Absence on any axis raises a no-values-within-range exception. These centre bounds are also used for optional warnings; they do not mask every velocity-cell weight.

For every target velocity cell $IJ$ and source cell $ij$, intersect source finite cells with target cells scaled by $s_v$:

\[
\ell_r=\max(s_vr^-_{b,I},r^-_{a,i}),\quad u_r=\min(s_vr^+_{b,I},r^+_{a,i}),\quad
\ell_z=\max(s_vz^-_{b,J},z^-_{a,j}),\quad u_z=\min(s_vz^+_{b,J},z^+_{a,j}).
\]

The recorded weight is

\[
\mathcal W_{IJ,ij}=\begin{cases}
\displaystyle\frac{2\pi(u_r^2-\ell_r^2)(u_z-\ell_z)}{W_{b,I}\Delta z_{b,J}},&u_r>\ell_r\ \text{and}\ u_z>\ell_z,\\0,&\text{otherwise}.
\end{cases}
\]

The prefactor is $2\pi$, exactly as recorded. No extra cube of a velocity-scale ratio is applied. Flatten and unflatten velocity arrays with radial index varying fastest: flattened index $i+N_rj$. Apply this matrix independently on every source spatial slice. On target spatial points inside the source coordinate range, linearly interpolate those mapped slices between the surrounding source points; outside that spatial range the initialized output remains zero.

At source spatial points with positive source density, compute target drift and energy using $h_a=\sqrt{T_{*,a}}$; zero-density slices have zero moment targets. Interpolate these two normalized moments linearly in $x$, independently of the mapped distribution's density. For each target slice of positive mapped density $n_b$, call the correction of section 6 with $h_b=\sqrt{T_{*,b}}$ and the following additional rules.

Before forming the difference operators, zero weighted entries satisfying $0<|H|<10^{-6}\max H$. Allow signed redistribution if the maximum entry of radial row $i=1$ is nonpositive. In that signed case, additionally subtract $c_{0j}$ from the radial part of $B^-_{0j}$ and add it to $B^-_{1j}$. Otherwise set the correction step to

\[
s=\min\left(\frac{1}{\max_{H_{ij}\ne0}(-\delta H_{ij}/H_{ij})},1\right),
\]

if any $H\ne0$; use $s=1$ otherwise. There is no lower clipping of $s$. Update $f'=n_b(H+s\delta H)/V$. Repeat correction until the returned $s\ge1$, with no iteration limit or residual stopping test.

Finally, linearly interpolate the source density onto target spatial points. Find the smallest strictly positive entry of the whole output array. On an in-range spatial slice, multiply its distribution by desired density divided by current density only when its current density exceeds that smallest positive array entry. This threshold compares a density integral with a distribution entry; the rule is recorded without a dimensional repair. If the output has no positive entries, skip all density rescaling.

Optional boundary warnings compare values at the overlap-centre boundary with a specified fraction of the global maximum output, and only inspect a lower/upper boundary when its target centre bound is truncated. Warnings are issued before final density scaling. They do not change the result. They inspect positive exceedances, not absolute magnitudes.

Two implementation limits must remain explicit for this optional scope. Disabling moment correction also bypasses creation of the mapped/interpolated values, leaving a zero output. Also, finite cell overlap can yield nonzero velocity entries whose centres lie outside the source centre range; zero outside the entire centre-defined phase-space box is not a general guarantee. Neither branch is activated by the fixed candidate.

## 8. Validation boundary

The active grid, finite-bin measure, shifted Maxwellian generation, full moment-adjustment operators, spacing test, and stencil are explicitly determined once the public rate functions are supplied. This document does not certify numerical accuracy, positivity, convergence, source parity, or a reference answer. Those require independently accepted scientific evidence and are not implied by static closure or by an earlier run of a different case.
