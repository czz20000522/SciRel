# TORAX bootstrap and finite-volume increment

The retained increment provides Sauter and Redl bootstrap coefficients, explicit
parallel-current assembly, cell/face reconstruction, conservative diffusion and
power-law convection, and a single-channel linear theta step. The two bootstrap
fits remain separate models and share the same current assembly. The accepted
nine TORAX relations retain their scientific implementations.

The bootstrap current uses total poloidal flux in Wb, so the factor 2π is
required. Pressures are Pa, F is T m, B0 is T, and output parallel current density
is A/m². The magnetic-axis face is zero. Collisionalities, trapped fraction,
pressure and logarithmic gradients are caller inputs; the API does not infer an
equilibrium or claim empirical calibration beyond the inspected fit equations.

The source squared ion collisionality before forming a bounded rational alpha.
Finite values near the binary64 ceiling consequently produced NaN. Binary
exponent scaling now evaluates the same ratio using either the product or its
reciprocal. Independent Decimal checks also rejected an initial logarithmic
repair when very small trapped fraction cancelled a very large collisionality;
that rejected revision remains evidence. The corrected calculation preserves the
Sauter and Redl limits 2.1 and −0.5, including the tiny-fraction product case.
Redl's shared-expression L34 equals L31. Current-cell averaging reuses the
accepted overflow-safe arithmetic midpoint.

The source convection positive-Péclet branch evaluated (p−1)/p even when the
ratio had overflowed. It now uses the equivalent 1−1/p and reaches the finite
upwind limit. Diffusion and convection share internal face fluxes; width-weighted
residual sums equal the selected boundary flux difference. Boundary gradients
mean du/dx in the increasing-coordinate direction at both ends, rather than an
outward-normal derivative. Ghost and semi-implicit convection boundaries can
use a numerical face value different from a supplied Dirichlet value.

Independent verification covers nonzero boundary-flux conservation, source
coefficient/boundary-mode comparison, constant and linear states, uniform and
smoothly stretched manufactured diffusion convergence, and theta-step boundary
causality. The uniform pure-upwind quadratic test has first-order spatial error.
No arbitrary distorted-grid convergence, nonlinear coupled solver, adaptive
stability, or complete tokamak simulation qualification is claimed.

The decision surface is the seven exact scientific documents and this corrected
numerical behavior. The selected development wheel retains only their runtime
closure and the accepted nine APIs. This increment carries no human approval or
release decision; unrelated TORAX families remain saved for later owners.

## Neumann face-gradient correction

For faces [0, 0.1, 0.4, 1] and midpoint samples of u=x², prescribed
end gradients 0 and 2 previously produced internal derivatives [0.2, 0.74]
instead of [0.2, 0.8]. Equal terminal widths masked the error. The former
last-face stencil used a linear boundary-value extrapolation as if it were
a quadratic point value.

With final centers x0,x1, right boundary b, internal face f and secant s,
the unique quadratic satisfying the two values and q′(b)=g has
q′(f)=s+(g−s)(2f−x0−x1)/(2b−x0−x1). For midpoint cells its weight is
(w0−w1)/(w0+3w1); widths are scaled before summing. This also covers two
cells and reduces to the adjacent secant when the two widths coincide.

The repair changes only the unmasked final internal Neumann derivative.
Dirichlet stencils, endpoint derivatives, face-value interpolation and the
conservative diffusion/convection matrices keep their original definitions.
Regression evidence covers quadratic, linear and constant profiles on both
unequal-width and prior equal-width meshes, N=2, boundary values and masks;
the independent unequal-width counterexample is retained. This is a discrete
polynomial reproduction result, not a general distorted-mesh convergence or
nonlinear transport-solver qualification.
