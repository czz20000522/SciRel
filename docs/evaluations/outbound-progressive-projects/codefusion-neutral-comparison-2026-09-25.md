# P1 neutral-harness comparison handoff

Status: ready for a controlled CodeFusion user-path comparison, not a product
release or science approval. This is a task-specific handoff, not a new SciRel
or CodeFusion runtime contract. The independent Codex result and its permission
interruption are recorded in
[`2026-09-25-unseen-p1-coil-codex.json`](manifests/2026-09-25-unseen-p1-coil-codex.json).

## Exact inputs

- Initial project material: `build/verification/p1-coil-variant-evaluation/stage0-inputs.tgz`, SHA-256 `09fdd32919721d9eeb2d2fb801de1e1808733649c6dad361ffcd6854a9650f9e`. Its `input/` contains a synthetic coil-layout TSV, baseline-drive CSV and source note. Its `resources/` contains the wheel, matching catalog and SciRel-owned skills. Do not expose examiner-private files to the solver.
- First user message: `build/verification/p1-coil-variant-evaluation/examiner-private/opening.txt`, SHA-256 `2904ddc1123b8dfbe8ca5c74f4a760191309d155bfd052e4931e89074ec7c772`.
- Later file, withheld until the first delivery is recorded: `build/verification/p1-coil-variant-evaluation/examiner-private/drive-more.csv`, SHA-256 `6eee80b67ec8b6143fa5931dfab9a3bfb0d7034d835710971a30e25daafc7ab8`. Place it alongside the baseline CSV as an ordinary new user file.
- Later user message: `build/verification/p1-coil-variant-evaluation/examiner-private/followup.txt`, SHA-256 `da7e4c489ea24db3bea2f2b2cff34552689d50687e797a87c74d229ff424b38f`.
- Scientific runtime: SciRel `0.1.0.dev15` development wheel SHA-256 `7b9c0b17d2fc24650055edda4e6cab6aa67c75df1b458abccfb43059a1d204af`; catalog `release.json` SHA-256 `aa8c19884887682713a99c7cc9d33ded3acc99b2356254e8191af93ee0ba8d20` (68/68 documents, `pending_unapproved`); `scirel-solving/SKILL.md` SHA-256 `d0a30da09b0b757307754c4e7a4e1f04d6603b42583a17285ad04def813092b3`.

These development inputs may be mounted or preinstalled through ordinary
project/runtime facilities. The user must not install Python packages, select
an asset ID, supply a plan, or operate intermediate tools. CodeFusion owns
chat, project files, tool execution, permissions and artifact presentation;
the SciRel wheel, catalog and skill own the scientific meaning.

## Two-stage user sequence

1. Give the solver only the initial `input/` files and ordinary access to the fixed SciRel runtime. Send the first message unchanged. Let the Agent inspect the data and build a reusable project. Record its first answer, actual tool calls, output files, questions, failures and any maintainer intervention before continuing.
2. Add `drive-more.csv` and send the later message in the **same user project**. Do not provide the examiner's expected values or suggested callable. Let the Agent handle complete and incomplete cases, preserve the first delivery, and give a normal user-facing rerun entry. Record whether the second stage is actually writable and persisted, not merely calculated in memory.

An essential scientific clarification is acceptable if the supplied materials
really leave one unresolved. Repeated requests for facts already in the files,
expert answers supplied by a maintainer, permission rescue, and reviewer code
feedback must be counted separately. Different project code or plots are fine;
the comparison concerns the user's task and scientific contract, not exact
source text.

## Bounded acceptance

- The first delivery has a readable central-field plot, exportable numeric data and a runnable project/ordinary rerun path. The supplied values are **whole-pack ampere-turns**, not current per representative filament; pack IDs, not row order, determine association. An independent circular-loop reference gives baseline axis-center `B_Z = 0.004222044322677252 T` and `Z=+/-0.08 m` gives `0.00414542476028215 T` for these synthetic inputs. Compare numerically within export precision, not by chart color alone.
- The result is described as an axisymmetric ideal-filament **vacuum** field before discharge. It must not be called a plasma equilibrium, measured field, conductor-engineering validation or heating result. The `psi` convention in this wheel is `R A_phi`, `Wb/rad`.
- The second stage narrows the view to `R=5..30 cm`, `Z=-10..10 cm`, compares complete `baseline`, `tilt` and `off` cases, and identifies `draft` as missing an explicit `lower` drive without silently setting it to zero or stopping the complete cases. `off` should have zero field. The first plot and numeric export remain separately openable.
- A normal user can rerun after editing a drive sheet without selecting run IDs or editing Python. From the delivered entry, repeat an unchanged run and confirm that previous results remain attributed to their original inputs. Do not require byte-identical chart files across different plotting stacks; inspect values, labels, source binding and artifact accessibility.
- When a stage fails, deliver the supported part and a specific limitation. A tool or permission failure is a harness result; a wrong unit, field sign, chosen relation or physical claim is a scientific/method result. A green project test alone proves neither.

The Codex comparator's first stage produced 3,479 grid rows and four project
tests; its second writable stage produced 2,091 rows per complete case and six
tests. Its first second-stage continuation was read-only and **did not deliver
new files**; a permission-only recovery was needed. The independent archive
replay and Biot-Savart checks are in the manifest and
[`results-2026-09-25.md`](results-2026-09-25.md). Those quantities are comparator
evidence, not a mandatory CodeFusion code shape or performance threshold.

## Reporting boundary

Return the actual harness/model/runtime versions, initial and later file
identities, user questions, first failed attempt, any rescue, project entry,
output files, checks and remaining science gaps. The test uses a development
wheel and synthetic inputs: it cannot establish expert approval, public v1,
real-device accuracy or stable generalization. No SciRel-specific task graph,
asset state, review status or science decision belongs in CodeFusion kernel.
