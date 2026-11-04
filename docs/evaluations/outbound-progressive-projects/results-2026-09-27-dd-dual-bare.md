# Bare Claude two-table project: bounded reviewed delivery

This fresh JSON-input variant used Claude Code `2.1.281` with `--bare` and one
resumed session (`e7361f57-1c39-47b5-963d-62926abd337c`). The CLI model
label was `claude-fable-5`; assistant events reported `GLM-5.3-Flash`, so the
underlying model identity is unconfirmed. No call or token cap was set. The
unapproved SciRel `0.1.0.dev39` wheel and complete 126/126 development
catalog were staged with the three usage-method files. `--bare` disabled
Claude's project auto-memory and hooks for this run, but the evaluator and
solver still shared the host filesystem and the same resumed conversation.
This is not an OS-isolated or strict blind test. The [manifest](manifests/2026-09-27-dd-dual-bare.json)
binds the inputs, methods, archives and raw traces.

The first user request supplied independent DT temperature batches (6000 and
14000 eV) and D(d,n)3He velocity pairs (km/s), including non-unit sightline
triples. Claude read the usage methods, found the Bosch-Hale reactivity and
DD neutron-energy exact assets, converted ports, kept the groups separate,
and built a rerunnable Python project. Its first tests failed when the parent
repository's pytest config prepended the source tree; the model added a
project-local config and recovered. The [first snapshot](../../../build/verification/dd-dual-bare-20260927/stage1-initial.tgz)
passed 9 tests. An independent physical calculation from the published DD
constants reproduced both energies exactly (2467.2165124162934 and
2452.2284408255096 keV). Direct wheel calls reproduced both DT reactivities
(2.5538034518523627e-23 and 2.405841927609959e-22 m^3/s). A fresh
unpack and ordinary rerun kept the four table files byte-identical; the
evidence JSON differed only in absolute unpack paths.

The second natural user turn provided only detector efficiency 0.12 and asked
for counts/s. Claude did not invent source strength or detector acceptance:
it returned `needs_scientific_input`, recorded an interpretation of 0.12 for
confirmation, and retained the two tables. The [second snapshot](../../../build/verification/dd-dual-bare-20260927/stage2-initial.tgz)
passed 12 tests. The third user turn corrected the efficiency to 0.20 and
asked to keep the 0.12 version. Claude archived the six old output files and
passed 15 tests, but its [first 0.20 snapshot](../../../build/verification/dd-dual-bare-20260927/stage3-initial.tgz)
still printed `x 0.12` in the counts/s formula. It also claimed all changed
parameters would be archived while its code compared only efficiency. These
are autonomous errors, not accepted behavior.

Two symptom-level reviewer interventions are preserved. The first made the
formula derive its factor from the recorded efficiency and added a regression
over multiple values; it also introduced a digest for the effective
`user_inputs.json` parameters. An independent new-input counterexample then
changed only the first DT observation from 6000 to 6500 eV, leaving
efficiency 0.20 unchanged. The [frozen failure](../../../build/verification/dd-dual-bare-20260927/stage4-new-input-counterexample.tgz)
shows the earlier table was overwritten without an archive. The second
reviewer intervention added observation-input digest comparison and a
normal-entrypoint regression. The [final reviewed snapshot](../../../build/verification/dd-dual-bare-20260927/stage5-reviewed-final.tgz)
is therefore **two-review-assisted**, not an autonomous end-to-end pass.

Independent extraction of that final snapshot ran the ordinary entrypoint
before tests: six runtime checks passed, and five user-visible files matched
the frozen output byte-for-byte. The evidence JSON changed only because it
records the absolute catalog and input paths. Then 22/22 project tests passed.
A separate [mutation replay](../../../build/verification/dd-dual-bare-20260927/stage5-independent-mutation.tgz)
confirmed the 6000 eV table was archived, the 6500 eV table delivered, and
the new evidence named `observation_input` with the previous input digest.
The archived 0.12 six-file output set was byte-identical to the second
snapshot. The review environment imported dev39 from an isolated venv;
the host's global SciRel was restored to its pre-run dev24 version after
Claude's first turn had replaced it with dev39. Exact pre-run installed bytes
cannot be proven, only the version and replacement wheel digest.

This proves a bounded development project can deliver two independent
relations, retain useful partial results on an unanswerable follow-up, and
recover two observed ownership defects after review. It does **not** prove
autonomous general reliability, a count-rate computation, device physics,
expert approval, public licensing, or a trusted v1. The project still cannot
compute counts/s from efficiency alone; source strength, detector acceptance,
emission angular model or an explicitly owned approximation, and the meaning
of efficiency remain unresolved. Its archive identity covers effective user
parameters and observation bytes, not wheel/catalog changes, project-code
changes, missing prior evidence, or files outside its six standard outputs.
An unchanged rerun clears the current record's one-step `archived_previous_run`
pointer, although older archives remain on disk and retain their own evidence;
this is not a complete lineage index. The development venv reused host
dependencies, so offline installation was not established. No CodeFusion
product acceptance is claimed for this local Claude run.
