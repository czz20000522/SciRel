# Source-to-port witness method: forward trials

Three fresh Claude Code `2.1.281` sessions tested successive SciRel skill
revisions on synthetic, structurally different file-backed projects. The CLI
reported `claude-fable-5`, assistant messages reported `GLM-5.3-Flash`, and the
underlying model was not independently confirmed. No call or fee limit was
set. All three received the same unapproved `0.1.0.dev24` wheel (SHA-256
`a0c665a7d2920650fce832c448c49d4c866260daec0cba0102dd60e3e56c95a0`)
and complete 74/74 development catalog (`release.json` SHA-256
`6e2aa58e731777620d060452354b60aa777996ab3c7e529f0a3fc4ebf69f87df`).
The solver directories did not contain examiner programs or earlier case
notes, but there was no OS-level isolation. Each first delivery was frozen
before fault injection or reviewer feedback.

| First-turn case | Skill revision and session | Correct-input result | Isolated mapping fault |
| --- | --- | --- | --- |
| DD velocity CSV plus detector JSON | `scirel-solving` `938bfda8...7384f10`; `4ee09ad3-52b5-461c-a0fd-3641b9098899` | 3/3 energies equal a raw-file-to-asset checker | Wrong CSV column: ordinary run exit 0 and 15/15 tests pass; `E-17` becomes `2457.272833` instead of `2468.086615` keV. |
| Nested mixed-unit thermal JSON | `scirel-solving` `18e1edc9...05b24c4`; `974a3e02-5474-4b7e-acaf-64367255dc4a` | 4/4 scales equal a raw-JSON closed-form checker | A keV conversion branch divides the 2.4 keV row by 1000: ordinary run exit 0 and 8/8 tests pass; scale becomes `0.003064856665` instead of `0.096919277647`. |
| H/H+ charge-exchange TSV | Same solving skill plus `scientific-project-implementation` `66c32d7d...67a994d4`; `94c01543-41a2-4d34-b7af-bd116659861a` | 4/4 ports and Janev outputs equal a raw-TSV checker | Wrong column is rejected before output write. Wrong shared conversion factor (1000 to 100) still exits 0, reports all checks passed and passes 8/8 tests; 300 eV is fed as 30 eV. |

The frozen skill copies have exact SHA-256 values: DD solving
`938bfda8ef44309debef122d0b05ba53e928cda54bb645524f09ec3c67384f10`;
thermal/CX solving
`18e1edc97edab9018d89776b91296ef1a068a0725cfa4f8d42583557d05b24c4`;
DD/thermal project implementation
`c088544a86e2828961a28fc0aed5ed3a5620ae8caa4479cde57dee0068413ed9`;
CX project implementation
`66c32d7db62080fa8164f0f1ec1eecdc060766f50a5df0561fa8b2b567a994d4`.
All three used navigation
`0f557cebf9518b0a7798d61c8208a5832af02efc4e36f5ab90dac13f1078695d`
and validation
`eb90496efaf5cd6bf8ffc2d624823f59d3c9d8a6dc298a7d5de623b0da66941f`.

The first two outcomes show that putting a raw-to-port instruction in the
plan, and then explicitly including the production parser in the mapping,
did not by itself cause a truly independent check. The third project's
ordinary entrypoint independently re-read the source column, which protected
column selection, but the witness reused the production unit constant.
Thus the observed improvement is **wrong-column rejection in this one new
structure**, not general source-to-port correctness. The independent checkers
are task-specific examiner evidence, not a new SciRel runtime gate.

## Frozen first deliveries

- DD archive: [stage1-autonomous.tgz](../../../build/verification/dd-port-forward/stage1-autonomous.tgz), SHA-256 `0ba35592b3b6c37042d61c50d9ce164469d7878b7a9b517c4349e5fcb4ed0fcf`; [raw trace](../../../build/verification/dd-port-forward/round1-autonomous.jsonl), SHA-256 `fdfbb14385e8264cc54b6213d77956618c1c999efbf8839f967a58f2fc0afe01`; [raw-input checker](../../../build/verification/dd-port-forward/examiner_raw_check.py).
- Thermal archive: [stage1-autonomous.tgz](../../../build/verification/thermal-port-forward/stage1-autonomous.tgz), SHA-256 `587d4d5f268587fef728f10e5d6ce229623ca2917c791023cd5100efb11f736d`; [raw trace](../../../build/verification/thermal-port-forward/round1-autonomous.jsonl), SHA-256 `862e4ba949b1d6a68a6bc83b808ae43485a6cffef3dda80ecb3ec20a28f48f5a`; [raw-input checker](../../../build/verification/thermal-port-forward/examiner_raw_check.py).
- CX archive: [stage1-autonomous.tgz](../../../build/verification/cx-port-forward/stage1-autonomous.tgz), SHA-256 `bb57b86229058507723a6864e061dba498a35e802294728b01a16727b1e36e1f`; [raw trace](../../../build/verification/cx-port-forward/round1-autonomous.jsonl), SHA-256 `af94e8115efd58363a41646bad8c916759e5a28ef0e5141717716a6a86b06265`; [raw-input checker](../../../build/verification/cx-port-forward/examiner_raw_check.py).

## Reviewed CX project

One explicit [review message](../../../build/verification/cx-port-forward/review-feedback-1.txt)
identified the shared conversion factor. Claude separated the raw-source
witness from the production parser and constant. The resulting
[stage-2 archive](../../../build/verification/cx-port-forward/stage2-reviewed.tgz)
had SHA-256 `ad29ae6d56901ba4b59928c98c1ce168ae285457c97296ed8070619b8d96f489`;
its [raw review trace](../../../build/verification/cx-port-forward/round2-reviewed.jsonl)
had SHA-256 `35668bb7ffd9667b25de0690496187940c530823a76abfcf138cabd547ee7aac`.
Independent source-free replay imported SciRel from a new venv's
`site-packages`, matched all four raw TSV rows and passed 10 focused tests.
Changing only the production conversion factor or energy column in separate
copies made the ordinary entrypoint exit 1 before changing the frozen CSV,
PNG or run report; all three files retained their own frozen SHA-256 bytes.

A valid fifth row then passed the ordinary entrypoint and raw-file checker,
but two tests failed because they expected exactly four source rows. A second
[review message](../../../build/verification/cx-port-forward/review-feedback-2.txt)
led to the [stage-3 reviewed archive](../../../build/verification/cx-port-forward/stage3-reviewed-final.tgz),
SHA-256 `0f6e0bd35630ff9bdeab6e7fbaf39f9dc6630e01e18c6251695039d1063787b4`.
Its [third-turn raw trace](../../../build/verification/cx-port-forward/round3-reviewed.jsonl)
has SHA-256 `69358f6d8a9b6c24220520e8ab4be1b3190132081cca6cd1fa17b46db026261c`.
The stage-3 archive was extracted separately: the four-row entrypoint, 10/10
tests and the raw-TSV checker passed. In another extraction, appending
`B-12, 8.00 keV` produced five checked results and 10/10 tests passed.
`run_scan.py` and `witness.py` are byte-identical between the independently
checked stage-2 and stage-3 archives, so the prior wrong-column and
wrong-factor rejection applies to the stage-3 production code; stage 3 changed
the project tests, not that execution path.

Two further independent user-facing reviews found overlapping chart labels,
stale fixed-row explanation and an unsupported particle-speed inference, then
an explanation that attributed optional test-suite checks to each ordinary
rerun. The exact [third](../../../build/verification/cx-port-forward/review-feedback-3.txt)
and [fourth](../../../build/verification/cx-port-forward/review-feedback-4.txt)
review messages and [round-4](../../../build/verification/cx-port-forward/round4-reviewed.jsonl)
and [round-5](../../../build/verification/cx-port-forward/round5-reviewed.jsonl)
raw traces are retained. Their trace SHA-256 values are
`8cf57e7f88bf93d19fcc8102fdd4f9b2c509d2f9dfc13090da7c43b54dbb67a1`
and `fc172723c7c4a66232b0f2188e725bcdabf25b3b5e38bc652517095c8fa1f047`.
The [stage-4 reviewed archive](../../../build/verification/cx-port-forward/stage4-reviewed-final.tgz)
has SHA-256 `a532e9b70f4c45e6311f370cf8fd9f8600cbeb9fdee63c4c02a06ff15ae27860`.

## Independent stage-4 replay

The stage-4 archive was extracted into separate four-row, five-row, wrong-factor
and wrong-column copies. An external venv imported SciRel from its own
`site-packages`, not this source checkout. Its bundled dev24 wheel and 74/74
catalog have the same hashes stated above. The four- and five-row ordinary
entrypoints exited 0; the [raw-TSV checker](../../../build/verification/cx-port-forward/examiner_raw_check.py)
matched all four and five ports and cross sections respectively. Each copy's
focused project suite passed 13/13 tests. The five-row CSV, generated
explanation and PNG include `B-12` at 8 keV; visual inspection found all five
IDs and values readable, though the two rightmost annotations are close.
The four-row rerun reproduced the archived CSV, PNG and explanation byte for
byte. Its JSON report differed only in the absolute input path of the new
extraction; result arrays matched.

Changing only the production keV-to-eV factor from 1000 to 100, or reading
the display-error column as energy, made the ordinary entrypoint exit 1 at the
source-to-port witness. Each mutation also failed the expected focused
conversion test (12/13 passed), but the entrypoint failure is the relevant
user-rerun evidence. In both failure copies, all four archived user outputs
(CSV, PNG, explanation and JSON report) retained their exact SHA-256 bytes.
This is a **four-review-assisted, synthetic development project**, not an
autonomous complete delivery, trusted SciRel release, expert approval,
external validation of the Janev fit, proof for other parsers/unit paths, or
CodeFusion integration. The witness's separate TSV text parsing is adequate
for this fixture, not a general TSV parsing contract. A failed rerun after a
changed input deliberately leaves the last successful files in place; the
generated explanation's phrase that it matches the "current" input is then
too broad unless the reader checks the run report's input path and the last
successful run. Quoted TSV fields, changed baseline rows and explicit
last-success ownership would need their own checks. No global script gate is
inferred from these trials.
