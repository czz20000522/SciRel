# SciRel development-skill operating contract

This contract is self-contained for the SciRel development package. It covers
candidate modification, D2 integration, D3 project delivery, review
preparation and release handoff. It never loads or references the decomposition
package; decomposition outputs arrive as exact input artifacts.

## Invocation binding

Bind only the identities required by the selected lifecycle mode. Every mode
still binds `task`, owner, writable work root, evidence already received and
the next owner; missing bindings stop the affected claim as `blocked` or
`NOT_RUN` with a concrete reopen condition. Never replace an exact candidate
with `latest` or infer a scientific oracle from a summary.

- In `development`, bind the Git base/head (or the current source revision),
  changed scope, affected API/test/benchmark target and claim. Bind exact
  runtime or dependency identities only when the task actually executes a
  scientific runtime, installed package or consumer case. A source-only
  change does not need a release candidate or a complete denominator.
- In `integration_checkpoint`, bind the current working-tree or exact
  development candidate, its dependency/runtime identities when exercised,
  the current manifest scope and reverse dependencies.
- In `release_freeze`, bind one exact Git revision, complete manifest and
  denominator, dependency/runtime identities, selected scope and all release
  evidence before making candidate or publication claims.

Before choosing tests or artifacts, bind the work to one lifecycle mode. The
default is `development`; `integration_checkpoint` and `release_freeze` require
an explicit task or owner decision. Do not infer a release freeze from a version
string, a document count, a clean worktree or the fact that a wheel can be built.

- **development**: evolve Git, source, tests, benchmarks, draft documents and
  the development catalog. Counts are dynamic. Do affected checks and bounded
  API/scientific checks; do not update `release/CURRENT.json`, create platform
  receipts or run the full release matrix unless a consumer explicitly needs an
  installed development wheel.
- **integration_checkpoint**: close a stable scientific batch or handoff. Check
  the current working-tree document/catalog closure and affected reverse
  dependencies. The denominator is the current manifest, not a historical
  count. Build an installed development wheel only when the declared consumer
  or D3 case requires it.
- **release_freeze**: freeze one exact Git revision for a real candidate or
  public release. Generate the manifest at that revision, derive its operator,
  TaskGraph and document counts, build wheel/document/catalog artifacts, bind
  platform receipts and run the release gates. Only this mode advances the
  public version or writes the current release tuple.

Read [the development lifecycle](development-lifecycle.md) for transition
triggers and the complete mode boundary.

## Product-development loop

SciRel follows a standard-library product loop: one Git source tree is the
development truth while public API, implementation, tests, documentation,
benchmarks and CI evolve together. Use the affected selector and the smallest
checks that support the claim for ordinary source work. A direct product
change does not enter the D1 handoff loop unless it is consuming an exact D1
packet.

During development, docstrings, comments and draft notes are sufficient for
an evolving contract. Create or refresh exact asset documents and the catalog
when a stable batch, discovery handoff, integration checkpoint or review needs
them; do not rebuild the complete catalog for every edit. Keep one current
working-tree representation and use Git history for prior wording or code;
do not copy full wheel, document or catalog trees into version directories.

## Development boundaries

- D2 may correct determinate scientific defects, compare and normalize
  candidates, assemble one development candidate and prepare documents.
- D3 may select an admitted capability, create user project files, execute the
  declared case and explain its bounded result.
- Review preparation freezes a truthful packet for human endorsement and
  release decisions; it cannot approve, grant rights or publish.
- A read-only diagnosis observes one exact snapshot and cannot mutate it.

Decomposition fidelity, source coverage and original source failures are input
evidence here, not claims this package silently re-proves. Human, rights and
release states remain separate from technical success.

## Evidence and state

Keep source/decomposition, runtime, scientific, human and release evidence
separate. Use explicit `passed`, `failed`, `blocked`, `NOT_RUN`, `inapplicable`,
`pending_human` and `no_changes`. Preserve exact failure, exit status, target
identity and command. A repaired checker or candidate creates a successor
receipt; never relabel the original observation.

Carry the complete received denominator, original grids, thresholds, failure
rows and applicability reasons. A digest proves bytes and a manifest proves
membership; neither proves scientific correctness. Never shrink scope, loosen a
tolerance, hide a failure behind a warning, or treat one D3 case as library-wide
acceptance.

The capability denominator is scoped to the current manifest or exact
candidate. A historical closure such as `267 documents = 235 operators + 32
TaskGraphs` is a fact about that snapshot, not a permanent project invariant.
Adding or removing capabilities in development changes the next manifest.

## Compact output and evolution

Return exact identities, selected scope and counts, checks actually executed,
evidence references and hashes, claim ceiling, limitations, changed artifacts,
next owner and reopen condition. For repeated work, measure context loaded,
specialist calls, retries, rework and handoff size against the same claim
boundary. Promote a route change only when the accepted result is preserved at
lower or better-bounded total cost. A retro records one reusable invariant,
route, validator or retirement decision; it does not accumulate case stories.

Do not increment a development `devN` version for ordinary source, test,
document or performance commits. Git identifies development state. Choose the
candidate or public version once at `release_freeze`, and keep the frozen
wheel/document/catalog tuple immutable afterward.

Use the canonical batching policy in
[`docs/design/scirel-release-batching.md`](../../../docs/design/scirel-release-batching.md):
advance the capability line for a broad capability or compatibility boundary;
accumulate compatible fixes, performance work and internal refactors into a
maintenance batch. A Git commit alone never advances `devN`.
