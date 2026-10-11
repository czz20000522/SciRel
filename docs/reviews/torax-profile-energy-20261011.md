# TORAX profile and energy increment

This increment retains three independent scientific assets. The canonical
documents carry their complete contracts; this page records the decisions and
the evidence limits. It is a technical development candidate awaiting a human
decision, with no release approval.

| Asset | Scientific dispute and concrete change | Evidence and decision |
| --- | --- | --- |
| Gaussian profile | Integer widths previously failed by bit-pattern broadcasting in TORAX. The accepted source repair is retained. SciRel now exposes the explicit normalized-radius grid, volume metric and cell widths. A factored difference of squares prevents remote-center cancellation; the source tiny-width denominator floor remains explicit. | Independent Decimal profile values, nonuniform discrete conservation, continuum-moment refinement, integer/tiny/signed widths and remote-center endpoint limits support retention. The API normalizes the supplied discrete measure; it does not claim an exact continuous integral. |
| Exponential profile | `decay_start` cancels under volume normalization; it is retained as a required finite scalar for compatibility, without inventing a cutoff. Signed widths control increasing/decreasing profiles. The repaired source tiny-width floor is preserved. | Independent direct exponential values, cancellation, signed-width endpoint limits, nonuniform conservation and refinement support retention. This radial relation differs from spatial trapezoidal normalization and velocity-space distributions. |
| Stored thermal energy | The source integrates electron, ion and total pressures independently. SciRel retains that algebra and the factor 3/2, without forcing the total to equal the two components. The original extended-precision sum lost a small signed residual; the corrected successor uses exact products and accumulation of converted binary64 inputs, followed by one final rounding. | The original failed permutation case and the correction are detailed in torax-profile-energy-correction-20261011.md; component independence and profile-to-energy conservation remain required. Signed inputs preserve the mathematical source relation; physical stored thermal energy requires nonnegative scalar thermal pressure. |

The three functions use equal-length one-dimensional arrays and scalar profile
parameters, with no inferred geometry, parameter defaults or broadcasting.
Integer, float32 and float64 values are accepted and converted to float64. Zero
or nonfinite real widths return NaN profiles; other malformed inputs raise.
Negligible tails may round to zero, while a profile that loses its requested
integral by more than 64 float64 epsilons relative raises instead of silently
returning a zero source. Profile extreme arithmetic evidence is bounded to the tested
Linux x86_64 NumPy longdouble runtime. Stored-energy accumulation uses exact
dyadic arithmetic and does not depend on the platform longdouble width.

The narrow Extended Lengyel repair makes zero/NaN geometry without a fallback
raise even when optional TORAX diagnostics are disabled. Before: the original
36-test suite passed 34 and failed the two required validation assertions.
After: all 36 original tests and eight added error-mode/JIT regressions pass.
Geometry precedence, configuration fallback and missing-value defaults are
preserved. Independent branch checks support this guard; complete edge-model
physics, negative/infinite geometry policy and arbitrary calibration remain
outside its qualification.

No existing SciRel asset or caller is absorbed or removed. The selected
distribution retains the six prior TORAX mathematical/fast-ion APIs and adds
this family; maintained Pleiades code and its separate selection remain intact.
This finite increment does not complete the remaining TORAX family frontier,
D3 application validation, human review or public release.
