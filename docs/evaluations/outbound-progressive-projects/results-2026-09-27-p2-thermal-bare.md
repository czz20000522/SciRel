# P2 source conflict and owner-confirmation follow-up

This is a two-user-turn Claude Code `2.1.281 --bare` development evaluation,
followed by two symptom-level reviewer repairs. The [manifest](manifests/2026-09-27-p2-thermal-bare.json)
binds the unapproved SciRel `0.1.0.dev39` wheel, complete 126/126 catalog, three
usage methods, staged inputs and requests, four raw traces, intermediate archives,
the date counterexample and the final project. The CLI reported model
`claude-fable-5`; assistant events reported `GLM-5.3-Flash`. The underlying
model identity is not confirmed. `--bare` removed Claude auto-memory and hooks,
but the evaluator and solver shared a filesystem; this was not a security-isolated
blind test. No call or token limit was imposed.

The initial JSONL contained two independent DT-temperature series. A had an
eV calibration note; two unsigned B notes conflicted between eV and keV. Claude
selected `scirel.fusion.bosch-hale-reactivity` through the thin catalog adapter,
computed A only, and asked one material B-unit question rather than guessing.
Its A results were `9.319671259461417e-24` and `8.636967284976203e-23`
m3/s for 4500 and 9000 eV. The [first archive](../../../build/verification/p2-thermal-bare-20260927/stage1-autonomous.tgz)
passed ten project tests and a fresh-extracted ordinary rerun. Its runnable code,
however, hardcoded B as pending while promising that the same command would
later compute B. That promise was not true in the first autonomous delivery.

In the second user turn, `b_owner_confirmation.md` explicitly resolved B as keV
only for b1/b2, kept A and B separate, and superseded the unsigned drafts. This
file is a **simulated owner confirmation for a development evaluation**, not a
real laboratory signature or SciRel expert approval. Claude read it, computed
B independently, retained the first A/pending outputs under `outputs/round1/`,
and passed 14 tests. The [second archive](../../../build/verification/p2-thermal-bare-20260927/stage2-autonomous.tgz)
is the autonomous two-turn result, not the reviewed final.

An independent fresh extraction then removed the confirmation before an ordinary
rerun. The command exited 0 and silently replaced three latest files with a B
pending version. The first reviewer request gave only that symptom. Claude added
a pre-write delivery-state guard and 19 tests. A second independent mutation
changed only the confirmation's `Recorded:` date from 2026-09-27 to 2026-09-28.
The [frozen counterexample](../../../build/verification/p2-thermal-bare-20260927/stage3-date-counterexample.tgz)
still exited 0, left all outputs byte-identical and falsely claimed the original
date. The second reviewer request identified that stale provenance. Claude
changed the project to derive source fields from the file, record its SHA-256,
and compare the binding before output writes. Its final source binding equals
`9edc42ecdb387d1c10a199f64dcdf1c72c29ec5d1ab5a136d0a0d968fcb768e9`.

Independent extraction of the [reviewed final project](../../../build/verification/p2-thermal-bare-20260927/stage4-reviewed-final.tgz)
installed only the bound wheel in an external venv. The ordinary entrypoint
left every output byte-identical, 24/24 project tests passed, and an independent
date mutation exited 1 **before any output changed**. The round1 and round2
archives remained accessible. These are reviewed, bounded recovery results;
the source-binding and output-preservation behavior did not emerge autonomously.

The digest proves file identity, not that a simulated owner has scientific
authority. The runnable guard covers B confirmation, not every A/source file;
its one-time migration from an earlier unbound result cannot prove that earlier
file's exact bytes. Text-structure checks remain case-specific and cannot prove
the meaning of arbitrary future prose. This case does not establish physical
correctness, broad autonomous clarification reliability, expert approval, a
trusted release or public v1.
