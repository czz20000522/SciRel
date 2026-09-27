# Stix per-shot project: progressive Claude Code evaluation

A fresh Claude Code `2.1.281` session received a nested synthetic JSON
manifest with two shots, three frequencies, SI magnetic-field/species inputs
and a declared GHz frequency unit. A later user turn supplied collision rates,
another frequency and a third shot, requesting the minimum eigenvalue of
`K = (epsilon - epsilon^H)/(2i)` while keeping the first delivery openable.
The solver directory contained the unapproved SciRel `0.1.0.dev24` wheel,
complete 74/74 development catalog and four usage skills. Exact source inputs,
skill hashes, four project archives, raw traces and reviewer feedback are
bound by the [manifest](manifests/2026-09-26-stix-per-shot-forward.json).
No model flag or call/fee cap was passed. Assistant events said
`GLM-5.3-Flash`; the underlying model was not independently confirmed.
Examiner material was outside the solver project, without OS-level isolation.

The first **autonomous** turn selected
`scirel.dielectric.cold-plasma-tensor`, invoked the SciRel Python callable
from the ordinary project entrypoint, converted GHz to Hz and delivered three
CSV rows with all 3x3 real/imaginary entries and a readable summary. Its own
collisionless fluid-momentum oracle tests passed. The second **autonomous**
turn extended that same asset call to five collisional rows, computed K as a
project-local matrix diagnostic, and did not infer absorbed power without a
wave electric field. Numerical comparison to its fluid-momentum oracle passed.
This is a useful contrast to the CodeFusion Stix case where the second-turn
ordinary script initially replaced SciRel with handwritten terms; the cases
use different input structures and cannot be scored as identical.

The autonomous second delivery was **not** history-safe or failure-safe. A
test run overwrote the first result pair; the model noticed and reconstructed
it, but the first summary's frozen SHA-256 was
`7abc51377ee4bedb1826d053919213c539ef268856ee3d8e9e48e831d5a05bf0`
while its reconstructed file was
`94eee783d77c8c8f214821f69ff44553d2e6ef49cca88b3ebaede7eb71e00511`
(missing final newline). Its preservation test compared against the already
changed file at test start. Separately, an isolated `cross_C` electron mass
of `1.0e-310 kg` passed manifest validation but made SciRel reject row five
with `ColdPlasmaOverflowError`; the ordinary command exited 1 **after**
overwriting the previous five-row CSV and summary with a four-success,
one-error delivery. Both first failures remain in the frozen stage-2 archive.

The [first reviewer message](../../../build/verification/stix-per-shot-forward-review-feedback-1.txt)
asked for exact first-delivery recovery and validate-before-replace behavior.
Claude restored the frozen bytes, moved tests off live result paths, and made
failed scientific rows retain the last successful result pair with a separate
`failed_rows.txt`. A [second review](../../../build/verification/stix-per-shot-forward-review-feedback-2.txt)
narrowed an overclaim: each file is individually replaced via a temp file and
`os.replace`, but the CSV and summary are **not** a multi-file transaction.
The final [reviewed archive](../../../build/verification/stix-per-shot-forward-stage4-reviewed-final.tgz)
has SHA-256 `e6ad637d6b9b832c5dfff629459ea80005326cef159a87636a50fff52a24e8e8`.

The final archive was extracted outside the SciRel checkout. Its Python
environment imported SciRel from the dev24 wheel in `site-packages`; 31/31
project tests passed. The ordinary follow-up command returned five successful
rows and a no-change rerun kept the two first and two follow-up user files
byte-identical. A separate [raw-input checker](../../../build/verification/stix-per-shot-forward-independent-check.py)
read only the JSON and CSV and called the installed SciRel relation: all 45
tensor components and five K minima agreed with maximum observed absolute
difference `0`; the smallest sampled K eigenvalue was
`6.66288136728e-06`. In another source-free extraction, the same rejected
fifth row exited 1, kept both last-success files byte-identical and wrote
`failed_rows.txt`. The [test](../../../build/verification/stix-per-shot-forward-final-source-free-tests.txt),
[numeric](../../../build/verification/stix-per-shot-forward-final-numeric-check.txt) and
[failure](../../../build/verification/stix-per-shot-forward-final-failure-check.txt)
records retain the checks. The project's separate cold-fluid oracle provides
a second derivation for these synthetic rows; it is still author-written test
code, not an external physics validation.

This is a **two-review-assisted bounded development delivery**, not autonomous
end-to-end reliability, a trusted/public v1 asset, expert approval, real-device
science, a heating calculation, strict examiner isolation or CodeFusion
integration. The final pair of result files is not atomically committed
together; a process crash between replacements can leave a mixed pair. The
catalog-location wording added to SciRel skills after the CodeFusion case was
**not** in this solver's frozen skill copies and is not validated by this run.
