# Cauchy kernel resolution near the real axis

For a constant density on [-1,1], the defining integral is
`log(1-z)-log(-1-z)`. At `z=1e-12j` this is approximately `i*pi`.
The previous direct real-coordinate quadrature returned about
`2.75e-9j` with zero imaginary error estimate. This is a missed known kernel
peak, even for a density with no unresolved features. A density feature mesh
cannot excuse that defect.

Write `z=x+i*y`, `h=abs(y)`, and substitute `v=x+h*sinh(t)`. Direct algebra gives
`dv/(v-z) = [tanh(t)+i*sign(y)*sech(t)] dt`. The transformed kernel is bounded,
and subintervals of bounded t length cover the central peak and its cross-scale
tails. Products involving h and sinh are evaluated with logarithmic scaling,
so tiny h does not require an overflowing sinh. Finite far panels use the
original coordinate when their distance from x is at least twice their width;
there is no hidden narrow kernel feature there, and this avoids cancellation
of nearly equal transformed endpoints. Whole-line mode adds finite anchors
around x and integrates the two outer tails in the original coordinate.

The density callback and feature-resolution contract, shapes, both half-plane
signs and strict-interior finite-support continuation policy are unchanged.
The integrator handles the known kernel scale internally. Summed component
quadrature indicators include an accumulation allowance and the continuation
contribution; callback/analytic-extension error, domain truncation and unseen
density features remain outside those conditional indicators.

Validation uses independent affine-density complex-log antiderivatives,
Gaussian/Faddeeva identities and a Lorentzian residue identity. Cases cover
heights from 1 to 1e-300, both half-planes, near/exact endpoints and exterior
points, multi-point output, continuation boundaries, panel refinement and a
projection outside the caller mesh. Previous Maxwellian and PDF evidence is
reused with unchanged implementations and assertions.

This implementation was derived from the displayed defining identity. No
upstream GPDF MATLAB, GPL implementation, or unknown-license source was copied.
The selected Python runtime depends on NumPy and SciPy and carries their notices.
Private source repairs and their provenance remain separate from this package.
Raw execution records and exact candidate identity accompany the handoff;
implementation checks do not confer independent acceptance, human approval or
release authority.
