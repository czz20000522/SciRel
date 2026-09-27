# Field-to-margin composition with a corrected source sheet

This fresh Claude Code `2.1.281 --bare` session used the pending-unapproved
SciRel `0.1.0.dev49` wheel and 148/148 development catalog. The [manifest](manifests/2026-09-27-field-margin-compose.json)
binds three natural user turns, the three usage methods, raw traces, first-pass
archives, two failure counterexamples, two reviewer prompts, and the final project.
The CLI model label was `claude-fable-5`; assistant events said
`GLM-5.3-Flash`. The underlying model was not confirmed. No call or token cap
was set. Bare mode disabled automatic memory and hooks, but the shared
filesystem was not a strict examiner/solver isolation boundary. CodeFusion
was not used.

Turn 1 supplied two rectangular coils and four out-of-order grid points.
Claude selected `scirel.field.multi-coil-vacuum-field`, adapted total coil
current to equal per-filament weights, and delivered a vacuum poloidal field
CSV. Six project tests passed. The reviewer separately checked the four
rows against the source numbers. The first report used `B_total_T` for the
poloidal magnitude before any toroidal-field premise was stated; that label
was overbroad for the first turn and must not be counted as a clean
scientific explanation.

Turn 2 added an out-of-order pressure table and explicitly assumed zero
toroidal field **only for the synthetic numerical exercise**. Claude reopened
the catalog, rejected the near-miss derivative relation, selected
`scirel.diagnostics.pointwise-firehose-margin`, joined by `point_id`, converted
kPa to Pa, and delivered the sampled `B^2/mu0+p_perp-p_parallel` values without
a stability verdict. Fourteen project tests passed. Independent arithmetic
from the frozen raw tables agreed at every point within six-significant-digit
CSV rounding. The first field CSV remained byte-identical. The project used
`np.hypot` for B magnitude; this proves one TaskGraph plus one Operator and
project glue, **not** a third SciRel asset or multi-graph composition.

Turn 3 corrected only the `outer` coil current from -0.45 to -0.55 kA. Claude
autonomously recalculated both tables, preserved the two old CSV byte streams
under `results/history/`, and passed 18 tests. A separate extraction of the
first-pass archive passed the same tests and a byte-identical unchanged-input
rerun. However, its historical `MANIFEST.csv` assigned the **new** coils
digest `66ea5467...` to both old result files; the old stage-1/2 source digest
was `7a0ed8a4...`. The old result bytes were retained but their source
binding was false. A second external probe changed the coil current to
-0.60 kA and corrupted Q4 pressure. The ordinary entrypoint exited 1 **after**
rewriting the vacuum CSV to SHA-256 `2ba32da3...`, while the margin CSV stayed
at SHA-256 `844c007d...` from -0.55 kA. The
[`stage3-partial-write-counterexample.tgz`](../../../build/verification/field-margin-compose-20260927/stage3-partial-write-counterexample.tgz)
preserves that mixed-input state. These are first-pass failures, not successes.

The first symptom-level reviewer message led the same Claude session to repair the
project. It restored the old source snapshot from the frozen stage-2 archive,
separated verified file digests from the run-lineage attestation associating
them with old results, and changed future preservation to use a prior recorded
delivery or mark source attribution unknown. It also computes and witnesses
both stages before writing, preflights delivery identities, and commits the
two outputs together. During repair, new regression tests initially failed;
the first reviewed project passed 22. The reviewer corrected only two
documentation phrases afterwards: a temporary extraction path was replaced
by the exact frozen stage-2 archive, and an overstrong "all-or-nothing" heading
was narrowed to "prevalidated pair". All 14 Python files have the same hashes
in Claude's first reviewed archive and the documentation-corrected archive.

In a new external extraction of the reviewed code, an installed copy of the
archived wheel resolved from venv `site-packages`; 22/22 tests passed. An
unchanged ordinary run left all 11 result/history files byte-identical. With
-0.60 kA plus the invalid Q4 cell, the entrypoint exited 1 with a readable
error and left the complete result tree unchanged. Repairing that cell and
rerunning produced two new deliveries with the shared input tag `26216e15`;
the -0.45 and -0.55 result bytes remained accessible. Deliberately corrupting
one same-tag identity copy then caused an identity-collision refusal before
any further result/history write. The documentation-corrected archive
was separately extracted, passed 22/22 tests, and had a byte-identical
unchanged-input ordinary rerun.

A further independent sequence exposed a second attribution defect in that
version. Changing only Q4 parallel pressure from 95 to 96 kPa kept the vacuum
CSV byte-identical but recorded a second vacuum delivery under a new input
tag. A subsequent coil-current change preserved the old vacuum bytes under
the *first* tag `3a47aa2f`, although the immediately preceding project run
had used `e7968231`. The
[`stage5-source-ambiguity-counterexample.tgz`](../../../build/verification/field-margin-compose-20260927/stage5-source-ambiguity-counterexample.tgz)
keeps the inputs and manifest showing both tags and the misleading preserved
row. A second symptom-level review made byte-stable outputs reuse their prior
delivery rather than creating a redundant identity, and made genuine
multiple-source cases list all matching tags while choosing the most recent
record. This is **review-assisted** repair, not autonomous provenance handling.

In a fresh extraction of the second reviewed archive, 24/24 tests passed and
an unchanged ordinary rerun kept the result tree byte-identical. The
pressure-only replay left vacuum bytes and its sole delivery row unchanged,
while the margin got a new tag `e7968231`. A later coil change bound the
preserved vacuum bytes to `3a47aa2f` and the replaced margin bytes to
`e7968231`; the earlier -0.45 kA files stayed unchanged. Reverting both
inputs restored the prior result hashes; another coil correction retained
the correct old vacuum association. An invalid Q4 pressure cell and a
deliberately corrupted same-tag identity copy each exited 1 without changing
any result/history file in this final version. The external venv inherited NumPy and pytest
from system site-packages, so this is a **source-free SciRel wheel** check,
not a fully hermetic dependency installation.

The numerical deliverable is only a vacuum-coil field and a sampled arithmetic
quantity under a declared, mutually hypothetical B/pressure combination.
It is not a plasma equilibrium, a firehose stability verdict, a device
prediction, expert approval, trusted release, or public v1. The project still
has a crash window between two final file replacements; identity copies can
support recovery, but crash-atomic pair delivery was not demonstrated. The
historical source/result association for the pre-archiving outputs relies on
preserved run lineage, not a derivation from result bytes. The first-turn
`B_total_T` label remains a scientific wording counterexample. This case
supports structure-specific asset discovery and composition; it does not
establish generalized autonomous reliability.

The final archive is
[`stage6-reviewed.tgz`](../../../build/verification/field-margin-compose-20260927/stage6-reviewed.tgz)
(SHA-256 `e80b298046bd4763e977545c04d505c9ace704ca16008c820c17c0cc0e8f3ca0`).
Recheck frozen file bindings with
`python scripts/verify_outbound_evaluation_manifests.py` and
`python -m pytest tests/test_outbound_evaluation_manifests.py -q`. To replay
the project, extract the final archive outside the SciRel source tree,
install its bundled dev49 wheel into a Python environment with NumPy/SciPy,
and run `python -m pytest -q` and `python run_preview.py` from `solver/`.
SciRel scientific source, exact documents and catalog were not modified by
this evaluation.
