# Fractional-ring progressive project: forward evaluation

This fresh Claude Code 2.1.281 session tested the revised `scirel-solving`
skill on nonuniform fractional ring shares, rather than the prior equal-filament
bank or saved-grid structures. The user first requested an ideal vacuum axial
field table and plot from CSV rings, one drive setting, and three heights; then
added a second setting and two heights, requested a comparison, and required
the first delivery to remain available. The solver received the user files, a
development SciRel `0.1.0.dev24` wheel, the matching 74/74 development catalog,
and scientific skills. Examiner checkers and prior case records were outside
its project directory. The exact inputs, skill, traces, feedback, and five
archives are bound by the [manifest](manifests/2026-09-26-fractional-rings-forward.json).
The CLI displayed `claude-fable-5`, assistant messages displayed
`GLM-5.3-Flash`, and the underlying model was not independently confirmed. No
call or budget limit was set.

Both **autonomous** turns produced correct values for the declared synthetic
model. An independent standard-library calculation from the raw CSVs matched
the first three values and the second turn's ten setting-height values to at
most `4.919e-10 T`, reflecting six-decimal CSV rounding. The second turn kept
the four first-delivery result files byte-identical and correctly explained
that the largest difference between two finite drive settings is not a
numerical-error bound between sampled heights. The result uses SciRel's dense
axisymmetric Green response and current-response superposition; it does not
validate a physical coil or plasma.

The autonomous self-check was **false-green** for the critical fact-to-port
mapping. Its purported independent formula consumed `case_rings` from the
production `build_case`, including the `bank_share` multiplication. In copies
of both autonomous stages, removing that multiplication made all five and nine
built-in checks respectively pass while the examiner's raw-input calculation
rejected the result. The stage-two comparison PNG also changed bytes on its
first unchanged rerun, stabilizing only on the next rerun. Its README confused
the five current heights with the three first-delivery heights and overstated
development records as reviewed/released. Thus loading the revised skill did
not independently produce a trustworthy mapping discriminator or complete
rerun behavior in this forward trial.

Three reviewer interventions are preserved separately. The first prompted a
raw-file current-share check independent of `build_case`; its wrong-current
mutation then exited 1. Independent review found that, if the old result
directory was missing and nominal current changed from `5.4` to `5.8`
kA-turns, that version regenerated a new result under `output/original/` and
called it the first delivery. The second intervention removed reconstruction:
the entrypoint now reports a history GAP and still produces current comparison
results. The third corrected only the stale height explanation. Comparison of
the fourth and fifth archives shows README is their only changed file; code,
input, wheel, catalog, and all 13 result/history files have identical bytes.

The [final reviewed archive](../../../build/verification/fractional-rings-forward/stage5-reviewed-final.tgz)
has SHA-256 `9b6967a2c634f845e18e429430b0bb003506d80ea697307891cc6a12c850877a`.
In a separate extraction, its bundled wheel was force-installed into a fresh
source-free virtual environment. The ordinary `run.bat` passed 19 checks;
all 13 output files stayed byte-identical on the first unchanged rerun. The
examiner's raw-CSV checker matched all ten values, and the four first-stage
plus four second-stage historical result files matched their frozen archives.
An isolated wrong-current mutation exited 1 at the independent mapping check.
With prior history absent and nominal current changed, an isolated run
reported the GAP without recreating `output/original/`. These final checks
verify the **review-assisted** package, not autonomous completion.

The separation of examiner data from the project directory limits direct
answer exposure, but this is still a synthetic, locally supervised evaluation;
it does not establish cross-model generalization, scientific expert approval,
a trusted/public SciRel release, a continuous field error bound, or CodeFusion
integration. The reproducible user project is useful within its stated ideal
vacuum and supplied-input limits. A further fresh structure is needed before
claiming that the method revision reliably induces an independent fact-to-port
check without reviewer rescue.
