# Progressive sampled-margin project: Claude and independent review

This is a source-free **development** evaluation, not scientific approval. A
fresh Claude Code `2.1.281` session received three staged requests for a
small reusable project using synthetic `B_mT`, `p_parallel_kPa` and
`p_perp_kPa` tables. The staged SciRel input was the unapproved
`0.1.0.dev39` wheel (SHA-256 `be5a2a2b...1eef9b8`) and complete 126/126
development catalog (root `434249fe...86e3fca`). Four owner skills were
copied into the blank project; the first raw trace shows actual reads of
their bodies. The user supplied no operator names. CLI model label was
`claude-fable-5`, assistant messages said `GLM-5.3-Flash`; the underlying
model was not independently confirmed. No call or token cap was imposed.
The [manifest](manifests/2026-09-27-margin-progressive.json) binds every
request/input, skill, trace and frozen project archive. Examiner and solver
shared a host filesystem, and the project venv reused host NumPy; there was
no OS-level blind isolation or offline dependency proof.

The model discovered and called `firehose-mirror-margins` and
`parallel-pressure-residual`, converting the table's mT/kPa columns to the
exact T/Pa ports. Stage 1 delivered four finite rows, a CSV, a report and an
ordinary command. Direct calls to the installed wheel from independent
literal arrays reproduced all four firehose/mirror margins and residuals.
The first report bounded the flags to the supplied sample set rather than
claiming general plasma stability. Stage 2 added a row whose B duplicated
another sample. Both assets rejected the five-row derivative, and Claude
autonomously kept unit-converted readings with empty check columns and the
first CSV/report unchanged. Stage 3 supplied a corrected, same-named CSV
under `input/revised/`; Claude autonomously separated its result path and
kept the first result bytes. The corrected five-row direct wheel call also
matched the delivered numbers.

Post-freeze applicability audit: this numerical replay does **not** establish
that either diagnostic was scientifically applicable to the synthetic table.
The exact documents require pressures and B to describe one suitable sample
set, and require the caller to select a physically meaningful B-value
coordinate, sampling and interpretation criterion. The initial request and
CSV established units and per-row values, but not those cross-row premises.
The first report's sampled "stable" flags and physical screening language
therefore exceeded the known inputs even though its formula values were
correct and it denied a general stability proof. Treat the output only as a
development calculation of the formulas on supplied numbers, with physical
meaning unresolved; the later review rounds did not resolve this premise.

The three autonomous turns did **not** yield a reliable reusable project.
Stage-2/3 reports said earlier results carried over for unchanged rows,
although B's mirror margin changed from about `+9,554` to `+413,286` Pa and
D's from about `-6,602` to `-899,459` Pa when the full B-sorted set changed.
The stage-3 source marker used an absolute temp path, so an extracted copy
could not rerun. In an isolated extraction, changing one row at the same
source path silently overwrote an older CSV. The [autonomous stage-3 archive](../../../build/verification/margin-progressive-20260927/stage3-autonomous.tgz)
and three original traces preserve these first failures.

Three symptom-level review messages followed, with a separate archive and
raw trace after each. Claude corrected the set-dependent explanation,
made source binding relocatable, and added input-digest refusal. Independent
negative probes then found that an unmarked stage-1 result could still be
claimed and overwritten; the first repair had also silently rewritten two
historical reports. The second repair restored their original bytes and
provided clearly marked `report-corrected.md` successors. A newline-only
change to an older CSV then exposed a write-before-refusal defect. The third
repair preflighted both user-facing files before committing, but its claimed
newline no-op still rewrote bytes on a successful same-input rerun. An
evaluator-added regression failed first; the evaluator then made a one-line
skip for normalized-equal files. This final correction is **not** a Claude
success. All six historical CSV/report files in the final project match
their original SHA-256 values.

The [final runnable archive](../../../build/verification/margin-progressive-20260927/stage3-final-evaluator-corrected-v2.tgz)
has SHA-256 `15090fb5b4b8d53d6b6abf5ab2f7fe58bb638495f6c7ed6e1d6b0d446308d55c`.
After extraction outside the SciRel checkout, the installed wheel came from
`site-packages`, two focused output-preservation tests passed, and all three
stage witness scripts passed. The ordinary entrypoint succeeded with a new
valid table and with a duplicate-B table (mapped data only, scientific check
columns empty). A changed input to an occupied result path exited 1 while
the old CSV/report hashes stayed fixed. An equivalent LF-only CSV rerun
retained its existing bytes. These are bounded software checks, not an
external physics oracle.

Remaining limits: `--bind-existing` is an explicit human assertion, not
proof of historical source identity; the source marker may change on a
refused run; old reports are retained as history and may require the marked
successor for correct interpretation. A historical same-input rerun can
refuse once other result sets change the generated comparison section. The
two-file preflight does not make writes crash-transactional or safe against
concurrent writers. The finite B-sorted derivative is sampling-sensitive,
and this catalog's source qualification, license disposition and expert
scientific review remain open. This case used direct SciRel Python calls,
not the thin adapter; it does not validate CodeFusion's separate adapter
product path or a trusted/public v1.
