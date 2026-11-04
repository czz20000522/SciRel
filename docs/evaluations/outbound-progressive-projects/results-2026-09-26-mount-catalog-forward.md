# Host-mounted catalog discovery: progressive Claude Code evaluation

This synthetic D(d,n)3He project tested whether an ordinary solver could find
SciRel when the wheel and full development catalog were **outside** the user
project, in a host-declared location. The user supplied NDJSON event velocities
in m/s and unit detector directions, then added two events and asked to keep
the first CSV and summary exactly as delivered. The frozen
[manifest](manifests/2026-09-26-mount-catalog-forward.json) binds the input,
skills, mounted resources, four project archives, raw traces and two review
messages. No model flag or call/fee cap was passed. Claude Code was `2.1.281`;
assistant events said `GLM-5.3-Flash`, but the underlying model was not
independently confirmed. The first three turns shared session
`0973175e-3eb4-457e-bfed-122f100f430e`; the final narrow review used a
fresh session. Examiner files were outside the solver project, without OS-level
isolation.

The first **autonomous** turn read the updated SciRel usage skills, discovered
`SCIREL_EVAL_ASSETS_ROOT`, searched the mounted 74/74 development catalog,
read the exact document for `scirel.fusion.dd-neutron-lab-energy`, and called
the installed relation from a reusable Python CLI. It converted the user's
m/s velocities to the asset's cm/s ports by a factor of 100, produced three
event energies and a readable summary, and did not infer a flux, angular
weighting or spectrum. The second **autonomous** turn added a separate
follow-up output directory: `reverse_D` yielded
`2450.8409457957396 keV`; `nonunit_E` had detector-vector norm 0.95 and was
rejected by the relation without an invented normalization. The follow-up CSV
kept both rows, with `status` and `rejection_reason`; exit 0 means a report
was produced, **not** that every scientific row succeeded. Consumers must
inspect row status. The first delivery's two files remained byte-identical
after this second turn.

The autonomous result still had two delivery defects. Its follow-up summary
called the rejected vector a unit direction; the [first review
message](../../../build/verification/mount-catalog-forward/review-feedback-1.txt)
corrected that label and clarified partial-success exit semantics. Independent
replay of that stage-3 archive then found that invoking the default CLI again
silently overwrote the historical first delivery with the newer CSV schema.
The original CSV digest `b111475a...25737b` changed to
`a6c13111...c900f2`; the summary digest `f6ecb83f...4bc7f` changed to
`e4a5eb93...36380` in an isolated verification copy. The original archive
was retained. The [second review
message](../../../build/verification/mount-catalog-forward/review-feedback-2.txt)
requested a narrow output-ownership correction, not a scientific change.

In the [final reviewed
archive](../../../build/verification/mount-catalog-forward/stage4-reviewed-final.tgz),
an ordinary run now refuses before writing when either delivery file already
exists; CLI exit 2 explains the collision. A new `--output-dir` succeeds,
while `--overwrite` makes replacement explicit. Five regression tests cover
this behavior, alongside the original 14 tests. The README distinguishes the
preserved first-delivery five-column CSV from the current seven-column schema.
The historical output itself is deliberately not rewritten; callers handling
both deliveries need to account for that schema difference.

Independent verification installed the pinned dev24 wheel in a venv outside
the SciRel checkout, installed the project from the reviewed copy, and ran
19/19 tests. The real console entrypoint refused a default repeat with exit
2; all four archived user output files retained their original SHA-256 values.
A fresh first-batch CLI run and a separate raw-NDJSON checker agreed with the
installed SciRel callable for all three energies (`max error = 0`). A fresh
follow-up run again produced one accepted and one rejected row, with CSV bytes
matching the archived follow-up CSV. The independent follow-up checker
recomputed the accepted energy, matched the relation's rejection message and
confirmed the first-delivery hashes. These checks establish adapter and
delivery behavior for this synthetic fixture, not independent physical
validation.

This is a **two-autonomous-turn, two-review-assisted bounded development
delivery**. The mounted-resource discovery is positive evidence for this
declared host configuration only; it does not establish generalized discovery
across harnesses. The dev24 wheel/catalog remain unapproved development
resources, with their scientific evidence ceiling unchanged. There was no
expert approval, real-device validation, strict examiner isolation, public v1
release or CodeFusion integration. The existence check is not an atomic
multi-process lock; concurrent writers are outside this single-user project
test. A rejected event remains a reported row, not a successful computation.
