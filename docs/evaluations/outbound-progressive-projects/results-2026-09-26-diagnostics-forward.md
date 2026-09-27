# Diagnostics progressive project: forward evaluation

A fresh Claude Code 2.1.281 session received an out-of-order synthetic R-Z
equilibrium table and point requests. The user then added a shuffled comparison
sheet whose two complete loop fluxes were in Wb, followed by a revised sheet
whose owner declared those two entries to be reduced-psi point samples in
Wb/rad under the grid's convention. The solver used the supplied SciRel
0.1.0.dev24 development wheel, 74/74 development catalog and four project
skills. Exact inputs, five frozen project stages, raw traces and reviewer
interventions are bound by the [manifest](manifests/2026-09-26-diagnostics-forward.json).
The CLI model label was `claude-fable-5`; the underlying model was not
independently confirmed. No call or cost limit was set. Examiner files were
outside the solver project, but not OS-isolated from the solver.

The first **autonomous** stage used SciRel's equilibrium-synthesis-diagnostics
graph (including bilinear sampling) and produced four requested rows, ten
scalar values, correct units and original point order. The second **autonomous**
stage reopened asset discovery, selected observation-residuals and compared
eight pressure/density/temperature rows by point ID and channel. It explicitly
excluded the two Wb loop readings: the prediction was reduced psi in Wb/rad,
and neither a validated conversion nor an instrument-response model was
provided. Its uncorrected chi-squared was `2.41015625`. The third **autonomous**
stage used the revised source note to include ten rows and reported
`3.66015625`, with the old Wb comparison still available. An independent
standard-library examiner recomputed all ten predictions and both sheets'
residuals from the raw CSVs. These are synthetic arithmetic checks, not
physical validation.

The autonomous delivery was **not** complete. When F-B in the revised sheet
changed from `0.48` to `0.47` Wb/rad, the ordinary entrypoint reported the new
chi-squared `4.41015625` but overwrote the previous revised result without
archiving it. The third stage had also rewritten the older summary to add
provenance columns, so its exact second-stage bytes survived only in the
earlier frozen archive. A first reviewer message prompted input-digest
ownership, result archiving and pre-write validation. Independent review of
that successor exposed a second failure: changing only the scientific note
from “same psi convention” to “convention unconfirmed” still included flux
and rewrote the output. A **second** reviewer message prompted a small
project-local exact note-digest contract. The initial defects, feedback and
repairs remain in the five archives and five raw traces; the final result is
**two-review-assisted**, not autonomous complete delivery.

The [final frozen project](../../../build/verification/diagnostics-forward/stage5-second-review-final.tgz)
has SHA-256 `1e556e2e785e5c71b5ff6cb4c0f8456ad72e4e1915dca7a7c5154f0ad0175138`.
An [independent check](../../../build/verification/diagnostics-forward/independent-stage5-check.txt)
used an [examiner](../../../build/verification/diagnostics-forward/examiner_raw_check.py)
that imports neither solver code nor SciRel. It checked the 3x3 coordinate
grid, four point requests, ten scalar predictions, ten observations in each
sheet, all residuals, two excluded Wb values, both summaries, the pinned
scientific notes and the sidecar file hashes. In separate final-stage
extractions, the three ordinary entrypoints reran unchanged with seven root
outputs byte-stable. An altered note and an invalid Pa-to-kPa unit each
failed before changing any of those seven outputs or 14 history files. A
valid observation change archived the old result; restoring the old input
restored the original root bytes without changing prior history. The installed
development wheel imported from the project's venv `site-packages`, not the
SciRel source checkout.

The note digest binds the exact declaration used for this comparison; it
does not prove that declaration physically true. The output update is not an
atomic filesystem transaction across archive and new files. This case does
not establish expert approval, trusted/public v1, real-device validation,
strict examiner isolation or a complete CodeFusion user-flow integration.
