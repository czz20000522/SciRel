# SciRel development skills

This directory is the independent development package for D2 integration, D3
project delivery, correction, normalization, review preparation and
development-only claim validation. Its inputs are exact decomposition packets;
it does not load or link to the decomposition package.

These skills produce candidates, project artifacts and review packets. They do
not grant human endorsement, redistribution rights or release authority.
The core and lifecycle references are the canonical development rules; read
them once per task mode, then load only the sub-skill reference needed for the
current scope. Do not duplicate the full lifecycle contract in every route.

Daily work runs in `development` mode by default. Capability counts, documents
and the development catalog may change with the current Git tree. Candidate
and public release work is an explicit `release_freeze` mode; it derives a new
manifest and exact closure once, instead of making every development change
advance a wheel version or run the full platform matrix.

Treat a long-running goal as a queue of possible claims, not as a scheduler.
Each development turn owns one bounded change set, one primary claim and one
stop condition. When that claim reaches its supported result, report the
reviewable diff and evidence; a later optimization or a repeated gate needs a
new claim or an explicit owner request.

Choose the mode before choosing artifacts or gates:

- **development**: improve the Git tree and run impact-matched checks. This is
  the default when there is no named consumer or release decision.
- **integration_checkpoint**: build a bounded development report or installed
  wheel only for a named consumer, handoff, or owner-requested checkpoint.
- **release_freeze**: freeze one revision for an explicitly named candidate or
  public release and run the declared release gates.
- **public release**: publish only after the separate human, rights and release
  decisions are complete.

Within ordinary `development`, use one of two routes:

- **direct product development (default)**: change the SciRel Git tree itself
  (`src/`, tests, public docs, benchmarks, CI or packaging metadata), then run
  the affected selector and claim-matched checks. Do not invent a D1 packet or
  rebuild release projections for this route.
- **D1 integration**: consume an exact D1 packet and use the D2 correctness,
  normalization and integration skills. The packet's denominator and evidence
  remain bound to that route; they do not become a requirement for ordinary
  product edits.

Batch compatible fixes into one reviewable Git change set. A changed function,
document or capability count does not require its own version or acceptance
cycle; use Git history to preserve earlier states and create a new release
projection only when a named checkpoint or release decision needs one.

Mode triggers, version handling, closure binding and the pre-publication guard
are canonical in [the development lifecycle](references/development-lifecycle.md);
use that reference instead of repeating release rules in each route.

## SciPy-style repository boundary

Keep one Git source tree for `src/scirel/`, `docs/`, build/test tooling and
`pyproject.toml`. Generate wheels, rendered documentation, catalogs and receipts
from an exact clean ref into task-local or external output directories; do not
copy a full source, handbook or catalog tree into versioned directories. A
named checkpoint may run source-only smoke from the current working tree. If it
explicitly asks for an installable artifact from dirty sources, mark it
`source_dirty` and `unbound`; it cannot serve as a revision-bound closure.
Keep only short release notes in `docs/release/`; Git history and tags provide
older source and wording. Separate core runtime dependencies, user-selected
extras and development/test groups in packaging metadata. These are repository
invariants for the future release path, not reasons to run release gates during
ordinary development.

The same-revision rule applies only when a wheel, exact document selection,
catalog or receipt is actually produced. Ordinary development may leave those
projections absent while the current Git tree and its dynamic capability set
continue to evolve.

The repository documents are the public, handoff-friendly source for project
and development methods. Skills are personal routing and method overlays; they
may point to the canonical documents or add a narrowly scoped working habit,
but must not hide or duplicate the general policy.

Adopt SciPy's structural ideas only where they fit SciRel: keep each scientific
domain self-contained with explicit public exports, direct tests and callable
documentation; keep the top-level namespace small; and separate runtime,
optional and development dependencies. Use the existing affected selector as
the daily test entry point. Do not add a native build system, platform wheel
matrix or release automation until measured ABI/native evidence requires it.

For non-trivial edits, validation or artifact/gate work, use the lifecycle
reference's work-triage, evidence-reuse and stop rules before selecting tools
or gates. Simple known edits and read-only status queries can use the routing
shortcut directly.

Delegation keeps one editing owner per mutable path. Parallelize independent
inspection or measurement only, and serialize source-bound maintenance. For
continuation and scope rules, use the lifecycle reference rather than adding a
second copy here.

## Correctness ownership

SciRel is the correctness boundary for every public operator and TaskGraph. A
capability change keeps its scientific contract, input/output validation,
failure behavior and direct regression evidence in the SciRel tree. Agent code
may discover, select, compose and adapt those capabilities, but it must not
reimplement domain mathematics or turn a passing integration path into proof
that an individual capability is correct.

When an optimization changes imports, dependencies or execution structure,
preserve the public API and numerical/failure behavior and measure only the
claim supported by the affected checks. If the change exposes a platform or
native boundary, first measure the actual runtime/ABI closure; do not create
per-platform wheels merely because multiple platforms are possible.

Lifecycle route: [post-acceptance-runtime-cleanup](post-acceptance-runtime-cleanup/SKILL.md)
routes acceptance-owned cleanup to the repository's runtime-asset policy.

For the mode boundary and transition triggers, read [the development lifecycle](references/development-lifecycle.md).

Routing shortcut:

- Changes to `src/`, public API, tests, documentation, benchmarks, CI or packaging metadata use `development`.
- A task that consumes an exact D1 packet uses D2 integration methods.
- A real user scientific request uses the usage skills and an already selected capability.
- A named candidate cut, publication or release approval uses `release_freeze`.

An ordinary documentation edit stays in `development`; mentioning a document,
wheel or catalog does not by itself trigger a release check.
