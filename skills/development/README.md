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

Choose the mode before choosing artifacts or gates:

- **development**: improve the Git tree and run impact-matched checks. This is
  the default when there is no named consumer or release decision.
- **integration_checkpoint**: build a bounded development report or installed
  wheel only for a named consumer, handoff, or owner-requested checkpoint.
- **release_freeze**: freeze one revision for an explicitly named candidate or
  public release and run the declared release gates.
- **public release**: publish only after the separate human, rights and release
  decisions are complete.

No source change, new capability, performance claim, document edit, clean
worktree or buildable wheel changes mode by itself. A current capability count
is a property of the checked-out tree, not a permanent gate.

## Pre-publication guard

Until the owner explicitly decides to make the first public release, treat the
repository as an incubation tree. An existing `project.version` or historical
`devN` label is metadata left by an earlier checkpoint; do not increment it,
create another `devN` release note, or update a release pointer for routine
development. A request to “continue”, “finish”, “review” or “verify” does not
change the mode. It remains `development` unless the task names a consumer,
handoff or release decision.

The first public release chooses its initial public version from the actual
capability and compatibility boundary at that time. Earlier development labels
do not constrain that choice. After publication, compatible fixes can accumulate
as a maintenance batch on the same line; a broad capability or compatibility
boundary can start the next line.

## SciPy-style repository boundary

Keep one Git source tree for `src/scirel/`, `docs/`, build/test tooling and
`pyproject.toml`. Generate wheels, rendered documentation, catalogs and receipts
from an exact ref into task-local or external output directories; do not copy a
full source, handbook or catalog tree into versioned directories. Keep only
short release notes in `docs/release/`; Git history and tags provide older
source and wording. Separate core runtime dependencies, user-selected extras
and development/test groups in packaging metadata. These are repository
invariants for the future release path, not reasons to run release gates during
ordinary development.

The repository documents are the public, handoff-friendly source for project
and development methods. Skills are personal routing and method overlays; they
may point to the canonical documents or add a narrowly scoped working habit,
but must not hide or duplicate the general policy.

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
