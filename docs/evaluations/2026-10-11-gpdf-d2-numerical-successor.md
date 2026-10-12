# Bounded GPDF D2 numerical successor

The rejected candidate lost the Maxwellian cold response through cancellation
in `1 + z Z(z)` and admitted small-wave-number seeds using an absolute
`k² epsilon` tolerance. At normalized frequency 2, the physical dielectric
tends to 0.75. The successor evaluates the large-phase susceptibility through
Gaussian moments, preserves the reflected lower-plane exponential, and checks
the balance between vacuum and susceptibility independently of `k²`.
Numerical error is estimated, rather than certified. A successful seeded solve
does not establish uniqueness or choose the least damped branch.

Whole-line adaptive Cauchy quadrature missed narrow shifted Gaussian support
and returned a false zero with zero estimated error. A finite collection of
callback samples cannot distinguish the zero function from a smooth bump
placed away from every sampled point. The successor therefore changes the
input contract: callers supply resolved finite bounds or a feature mesh;
whole-line mode integrates both tails and requires those tails to contain no
unresolved features. Component estimates remain conditional quadrature
indicators. They exclude callback error, omitted finite tails and unseen
features. Optional finite-support lower-plane continuation crosses only the
strict interior of the declared support.

The original four scientific assertions and tolerances remain intact. Added
regressions cover the four recorded small-wave-number counterexamples,
successful physical roots, explicit nonconvergence, three shifted Gaussian
cases, matrix shape, support-crossing behavior and invalid inputs. Independent
90-digit calculations cover the asymptotic transition and complex angular
sectors as well as Gaussian moments, roots and centered real-contour integrals.

The existing analytic plasma-dispersion wrapper is reused without changing its
scientific implementation. Source Weideman truncation orders, J-pole tables,
symbolic distribution cases and MATLAB root trajectories have different
contracts and are not absorbed into these APIs. Private source-derived repairs
remain outside the selected Python package because the upstream GPDF source
redistribution grant is not established.

`scripts/build_gpdf_selected.py` builds an explicit five-module Python closure
with minimal initializers and dependency notices. It does not package workflow
or plugin code or the rest of the maintained scientific library. Kernel
filesystem and socket restrictions were used for the empty-environment wheel
installation and installed scientific tests, independent probes and examples.
Those development results do not confer human approval or public release
authority. SciRel has not declared a public distribution license.
