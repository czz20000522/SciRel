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
- **integration_checkpoint**: serve a named consumer, handoff or
  owner-requested checkpoint. Recompute document/catalog closure only when that
  artifact is needed. The denominator is the current manifest, not a historical
  count. Build an installed development wheel only for the declared consumer
  or D3 case.
- **release_freeze**: freeze one exact Git revision for a real candidate or
  public release. Generate the manifest at that revision, derive its operator,
  TaskGraph and document counts, build wheel/document/catalog artifacts, bind
  platform receipts and run the release gates. Only this mode advances the
  public version or writes the current release tuple.

Read [the development lifecycle](development-lifecycle.md) for transition
triggers and the complete mode boundary.

Lifecycle, version, closure and artifact-binding policy is canonical in
[the development lifecycle](development-lifecycle.md). Read that reference
when packaging, documents, catalogs, wheels, native resources or release state
are in scope; do not duplicate its gates in a task-specific route.

## Product-development loop

SciRel follows a standard-library product loop: one Git source tree is the
development truth while public API, implementation, tests, documentation,
benchmarks and CI evolve together. Use the affected selector and the smallest
checks that support the claim for ordinary source work. A direct product
change does not enter the D1 handoff loop unless it is consuming an exact D1
packet.

Use a complete related change set as the unit of work. Inspect the Git base and
worktree before editing, capture an affected baseline when behavior or
performance is difficult to attribute, and keep unrelated edits out of the
commit. Public API or behavior changes carry their callable docstring and a
focused regression/contract test; add a user-facing page or example when the
scope warrants it. Performance claims carry a comparable benchmark with a
before/after observation. These are development checks, not a request to build
a wheel or regenerate release projections.

After the edit, rerun the affected selector and reverse dependencies. Unknown
ownership fails closed to a wider test layer. A clean diff and a Git commit for
the coherent change set are part of the development record; a commit may
contain several compatible fixes, but it must not mix unrelated work.

During development, docstrings, comments and draft notes are sufficient for
an evolving contract. Create or refresh exact asset documents and the catalog
when a discovery handoff, integration checkpoint or review needs them; a stable
batch or changed count alone is not a trigger. Do not rebuild the complete
catalog for every edit. Keep one current working-tree representation and use
Git history for prior wording or code; do not copy full wheel, document or
catalog trees into version directories.

Without an exact D1 packet, keep product work on this direct development path.
Do not manufacture a D1 manifest or complete denominator to enter the
correctness or normalization sub-skills for a local API, import, performance or
packaging change.

AOCI is a repository-maintenance aid, not a development gate. For a local
source or skill change, read only the related evidence; after the batch reaches
its final stable state, perform one applicable `aoci_maintain` and do not repeat
it for every commit or intermediate edit. A full Overview/Attestation is only
for a task that actually requires complete repository cognition.

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
separate when those evidence classes are in scope. Use explicit `passed`,
`failed`, `blocked`, `NOT_RUN`, `inapplicable`, `pending_human` and `no_changes`.
Preserve exact failure, exit status, target identity and command. A repaired
checker or candidate creates a successor receipt; never relabel the original
observation.

For scientific claims and D1-D3 handoffs, carry the complete received
denominator, original grids, thresholds, failure rows and applicability reasons.
Packaging, API glue, dependency and document tasks record their changed scope
and relevant checks without inventing a scientific denominator. A digest proves
bytes and a manifest proves membership; neither proves scientific correctness.
Never shrink scope, loosen a tolerance, hide a failure behind a warning, or
treat one D3 case as library-wide acceptance.

## Compact output and evolution

In `development`, return changed scope, checks actually executed, exact
failures or unknowns, and the claim ceiling when one exists. At a named
checkpoint add the current manifest, dynamic counts and consumer receipt when
needed. At `release_freeze`, return complete identities, hashes, receipts,
limitations, next owner and reopen condition. Measure context, specialist
calls, retries, rework or handoff size only when evaluating this skill, a
repeated failure, or a long-running route; do not turn every small edit into a
governance report. Promote a route change only when the accepted result is
preserved at lower or better-bounded total cost. A retro records one reusable
invariant, route, validator or retirement decision; it does not accumulate case
stories.

Use the version and batching policy in
[the development lifecycle](development-lifecycle.md) and
[`docs/design/scirel-release-batching.md`](../../../docs/design/scirel-release-batching.md).
A Git commit, changed count or buildable wheel never advances a version by
itself.
