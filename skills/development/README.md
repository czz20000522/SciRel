# SciRel development skills

This directory is the independent development package for D2 integration, D3
project delivery, correction, normalization, review preparation and
development-only claim validation. Its inputs are exact decomposition packets;
it does not load or link to the decomposition package. Repeated guidance may
be duplicated here deliberately so each package can be shipped and pinned
without a cross-package dependency.

These skills produce candidates, project artifacts and review packets. They do
not grant human endorsement, redistribution rights or release authority.

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
