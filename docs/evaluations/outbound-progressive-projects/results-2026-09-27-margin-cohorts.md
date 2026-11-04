# Cohorted pressure margins: method forward test and reviewed project

This is a synthetic **development** evaluation on Claude Code `2.1.281`,
not expert scientific approval. A fresh session visibly read the four SciRel
method bodies and used an unapproved `0.1.0.dev39` wheel with the complete
126/126 catalog. The solving skill in this experiment had the first narrow
set-dependent applicability edit (`d2e64b...`), not the later pointwise-claim
sentence now in the repository. The CLI model label was `claude-fable-5`;
the underlying model was not confirmed. There was no call or token cap, and
no OS-level examiner/solver read isolation. The [manifest](manifests/2026-09-27-margin-cohorts.json)
binds the exact inputs, skill, raw traces and each project archive.

The input interleaved two synthetic series and explicitly left open whether
each represented a meaningful p(B) profile. In the first autonomous turn,
Claude held both set-dependent SciRel diagnostics, gave a runnable project
with unit-converted and project-local pointwise formula values, and asked for
the missing profile/criterion information. It did not invoke the bundled
SciRel margin asset and hide an inapplicable derivative. This is a narrower
improvement over the earlier cross-rig case. It still described positive
pointwise values as satisfying a physical firehose necessary condition before
the model/criterion premise was confirmed. Algebraic sign was established;
physical applicability was not.

The second user message supplied a setup-group note stating that alpha and
beta are separate synthetic equilibrium-model p(B) profiles, B is the
positive magnitude coordinate within each, and the catalog's sampled margin
criteria are intended as exploratory checks. Without reviewer help, Claude
updated a source-linked declaration and invoked `firehose-mirror-margins`
once per series, never across all six rows. Independent raw-row arithmetic
reproduced all six firehose and mirror values to at most `2.33e-10 Pa`.
Alpha's first sampled mirror margin was about `-65,070 Pa`; beta's sampled
mirror margins were positive. These are coarse three-point formula checks,
not validated device stability. The stage-1 CSV, summary and report were
retained in an archive with their original SHA-256 values.

The two autonomous turns did not yield a portable, fully current project.
An extracted copy initially passed only 8/15 tests because `pandas` was
undeclared in the frozen project environment. Installing the version used by
Claude made 15/15 pass, but the report still embedded original absolute temp
paths. A source-note-only update with identical numerical CSVs returned
"outputs unchanged" while leaving the old interpretation; the report's
source claim was stale. One explicit reviewer message addressed these
symptoms and the stage-1 physical overclaim. The [reviewed archive](../../../build/verification/margin-cohorts-20260927/reviewed-v1.tgz)
is therefore **review-assisted**, not an autonomous pass.

Independent extraction of that reviewed archive ran `bootstrap.ps1` with an
explicit staged wheel path. It installed NumPy, pandas and pytest from the
configured package cache/index, then SciRel from the local wheel; this is
not an offline dependency proof. The wheel imported from the new venv's
`site-packages`. All 19 project tests passed, and an unchanged ordinary run
left the outputs in place. A source-note-only revision archived the old
report and produced a report containing the new note while numerical CSVs
stayed identical. Changing one input row archived the prior result set;
a duplicate B in alpha exited 1 and left current user-facing result bytes
unchanged. The first three deliverables still matched their original hashes
and have an explicitly marked correction alongside the historical report.

Remaining limits: the project depends on an external development wheel and
network or cached package index, with lower-bound rather than locked
dependency versions. Its criteria declaration cites prose but code cannot
prove the prose scientifically; a future conflicting note still needs Agent
reassessment. Multi-file archive/write is not crash-transactional or
concurrent-writer safe. The final repository skill's additional distinction
between pointwise arithmetic and physical criterion has not yet been tested
in a fresh context. This case used direct Python calls, not the thin adapter
or CodeFusion's product path, and does not establish trusted/public v1.
