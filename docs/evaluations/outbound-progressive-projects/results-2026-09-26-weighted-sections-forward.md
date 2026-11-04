# Weighted-section saved-grid project: forward evaluation

A fresh Claude Code 2.1.281 session used a synthetic two-section winding with
nonuniform filament shares, two drive settings, a 3-by-3 R-Z grid, and sites
added over successive user turns. The third turn explicitly requested site
readouts from the displayed grid rather than new pointwise coil calculations.
The solver received the user files, an unapproved SciRel `0.1.0.dev24` wheel,
the matching 74/74 development catalog, and scientific skills. Examiner
integrals and earlier case records were outside the solver project. The
[manifest](manifests/2026-09-26-weighted-sections-forward.json) binds the
fixture, exact loaded skill, six raw traces, six stage archives, review
feedback, and findings. The CLI reported `claude-fable-5`; assistant messages
reported `GLM-5.3-Flash`. The underlying model was not independently
confirmed, and no call or budget limit was set.

The **first autonomous turn** invoked the SciRel multi-coil vacuum TaskGraph
and returned correct grid values, but its alleged independent formula reused
the production current mapping. An isolated `1e3` to `1e4` kA-to-A mutation
left all four internal checks green and produced a tenfold wrong field. The
**second autonomous turn** preserved the first CSV, PNG, and HTML bytes, added
both settings' pointwise site values, left the outside site empty, and
correctly rejected a continuous numerical-error-bound claim. It changed the
first run summary, so not all prior output files were untouched. Direct
TaskGraph reevaluation at sites was scientifically valid for this ideal
vacuum model but did not demonstrate grid sampling. The **third autonomous
turn** reopened asset discovery, invoked SciRel's
`bilinear-grid-sampling` Operator for grid readouts, and kept both previous
views. Six in-grid setting-site values matched an examiner's raw-input grid
integral and bilinear calculation within `4.887e-13 T`; eight second-stage
files remained byte-identical. However, appending a valid `edge` site after
the `outside` row made the ordinary entrypoint exit 1 because its check
assumed the last row was outside. The false-green current check remained.
The three autonomous archives were frozen before any reviewer feedback.

Three explicit review turns repaired distinct failures. First, the project
removed the row-order assumption and changed misleading "released" wording
for the unapproved development assets. Second, it added a raw-file-to-port
current check: the same wrong-scale mutation now failed, but the failure had
already overwritten previously valid CSV, PNG, and HTML results. Third, the
project changed its relevant entrypoints so a failed scientific check keeps
last successful user-facing files and records the failure separately. The
original errors, exact reviewer messages, and each intermediate archive remain
available; the final result is **three-review-assisted**, not autonomous
complete delivery. The present solving-skill revision was genuinely loaded
in this new session but did not prevent the first-turn false-green check.

The [final reviewed archive](../../../build/verification/weighted-sections-forward/stage6-reviewed-final.tgz)
has SHA-256 `3834b335146ee63821ea2bbc9156b2343eb52ff0c6fa500188c50e5d961e9cc6`.
In a separate extraction, its bundled wheel was force-installed into a fresh
source-free virtual environment. The ordinary `run.bat` exited 0 and all 13
result files stayed byte-identical on the first no-change rerun. Independent
raw-table angular integration matched eight pointwise values within
`3.146e-13 T`; raw-table nine-node grid integration followed by bilinear
sampling matched eight grid readouts within `4.887e-13 T`. The initial grid
CSV and PNG retained their first-stage bytes; the HTML changed deliberately
to correct trust wording. With a wrong current scale, `run.bat` exited 1,
reported expected 4800 A versus actual 48000 A for the inner section, left
12 previous result files untouched, removed its reuse marker, and wrote a
separate failure explanation. Restoring code recovered all 13 baseline
files. Adding an ordinary in-grid probe succeeded in both comparison views
without changing the original grid CSV, PNG, or HTML; removing the probe
restored baseline bytes. All three unchanged paths subsequently reused
results.

This is a reproducible synthetic ideal-vacuum project, not physical device
validation. It establishes a bounded, review-assisted TaskGraph-to-Operator
composition and rerun-recovery path. It does not establish stable autonomous
generalization, expert approval, a trusted/public SciRel release, a
continuous-domain error bound, strict examiner isolation, or CodeFusion
integration. The repeated first-turn fact-to-port false-green result remains
a method-adherence gap for a further unseen-structure test; no SciRel-specific
harness kernel change follows from this evidence alone.
