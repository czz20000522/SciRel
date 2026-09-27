# Unseen hydrogen-log project: source claims and result history

This synthetic three-turn user project used a new Claude Code `2.1.281`
session (`337669e6-da68-46ce-80ea-60e65513d580`), the unapproved SciRel
`0.1.0.dev39` wheel and complete 126/126 development catalog. The three
user requests were fixed before solving and revealed incrementally: an
initial hydrogen sample log with conflicting/missing electron-temperature
units; an export-owner eV clarification and added sample E; then the owner's
withdrawal of C=eV in favor of 1.5 keV. Examiner calculations were kept
outside the solver project, but both sides shared the host filesystem, so
this is not a security-isolated blind trial. The [manifest](manifests/2026-09-27-hydrogen-unseen.json)
binds the exact inputs, stage archives, traces, feedback and final artifact.

Before any reviewer feedback, Claude found and called SciRel's hydrogen Saha
population and neutral thermal-speed assets. A/B, stage-2 A-E and stage-3 C
(`571052.3440976143 m^-3` at 1500 eV) matched the independent formulas of
the exact contracts; E's speed remained unavailable because neutral mass
was absent. The first three project suites passed 7, 11 and 13 tests.
Those green tests did **not** make the first pass reliable:

1. Stage 1 placed C's unresolved eV scenario in the primary numerical
   column even while asking the user to resolve eV versus keV. The first
   summary also omitted the conflicting note's digest.
2. Stage 2 retained the earlier CSV but changed the delivered stage-1
   summary from SHA-256 `a8eca787...dcf0` to `060ecb9b...bcc20` during
   a rerun, despite claiming that history was byte-stable.
3. Stage 3 used the latest owner correction and computed the right nominal
   number. In an independent copy, replacing that note with a contrary eV
   claim still let the ordinary entrypoint exit 0 with the 1500-eV result,
   while attaching the changed note's digest to the rewritten summary.

The reviewer supplied symptom-level feedback in three rounds. The first
repair restored the original stage-1 summary, added source-digest checks and
history guards, and created a maintained view that explicitly marks the old
C value as an unsupported scenario. A permission-denied Claude invocation
was interrupted and retried with ordinary project execution available;
both traces are retained. The second review found that the new instruction
to fill E's mass and rerun stage 3 contradicted that history guard, and that
a missing stage-1 conflict note was not rejected. Claude corrected the
guidance to require a new named run/output and made missing declared evidence
fail closed. The diagnostic `2.0 amu` mass used to test that path was **not**
treated as user data or delivered as a new scientific result.

Independent extraction of the second-review snapshot then caught a
regression: changing question wording inside persisted summaries made the
unchanged stage-2 and stage-3 entrypoints exit 1. During the third repair,
Claude briefly broadened equivalence to ignore catalog and input/output
blocks to satisfy a misconfigured test. The evaluator stopped that run and
required exact historical config/path testing; that incomplete trace and
boundary correction are retained. The completed repair permits only
`questions_for_the_user` wording to differ, while keeping all other summary
fields and CSV bytes exact. Finally, the evaluator changed one misleading
no-write CLI message and replaced two vacuous `or True` test assertions.
These interventions mean the final success is **not autonomous**.

The frozen final project is
[`stage6-final-evaluator-corrected.tgz`](../../../build/verification/hydrogen-unseen-20260927/stage6-final-evaluator-corrected.tgz)
(SHA-256 `d4af8a7a32c0442eb2de49687d892b6c8686383b7078753cdcd1f6bb6612a88d`).
The [independent extraction record](../../../build/verification/hydrogen-unseen-20260927/stage6-independent-finding.md)
shows 26/26 tests on the installed wheel outside the SciRel checkout,
stage-2/stage-3 ordinary no-write reruns, and a contrary-note replay that
exited 1 before touching the last successful CSV/summary. The six original
result files retain their exact historical hashes; stage 1 itself now
refuses same-name rerun because its restored summary predates added fields.
The initial misleading C cell remains in the immutable historical file;
`results/MAINTAINED.md` is the current user-facing interpretation, not a
retroactive rewrite. It must be updated for future deliveries by the Agent.

This case demonstrates a useful development workflow for supported partial
answers and source-claim withdrawal, and a repeated failure mode in
preserving history while changing guidance. It does not prove the owner's
statement true, non-transactional two-file writes safe against mid-write
failure, autonomous generalization, physical validation, expert approval,
trusted release, public v1 or CodeFusion integration. No SciRel-specific
CodeFusion kernel change follows from this local Claude trial.
