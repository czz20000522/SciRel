# SciRel development-skill operating contract

This contract is the shared operating entry for the SciRel development package.
It covers candidate modification, D2 integration, D3 project delivery, review
preparation and release handoff. It never loads or references the decomposition
package; decomposition outputs arrive as exact input artifacts. Mode triggers,
versioning and artifact closure are canonical in
[the development lifecycle](development-lifecycle.md).

## Invocation binding

Bind only the identities required by the selected lifecycle mode. Ordinary
`development` binds the task, Git base/head, owned change scope, primary claim
and the tests or benchmark that can decide it. Bind owner, consumer, next
owner and handoff custody only for a checkpoint, handoff or release. Bind an
exact runtime or dependency only when the task actually executes it. A missing
required identity stops that claim as `blocked` or `NOT_RUN` with a concrete
reopen condition; do not manufacture a denominator or a release packet to fill
an unused field. Never replace an exact candidate with `latest` or infer a
scientific oracle from a summary.

- In `development`, bind the Git base/head (or the current source revision),
  changed scope, affected API/test/benchmark target and claim. Bind exact
  runtime or dependency identities only when the task actually executes a
  scientific runtime, installed package or consumer case. A source-only
  change does not need a release candidate or a complete denominator.
- In `integration_checkpoint`, bind the current working-tree for source-only
  smoke or an exact clean development candidate for any installable artifact;
  if a dirty artifact is explicitly requested, mark it `source_dirty` and
  `unbound` and do not use it as revision-bound evidence. Also bind its
  dependency/runtime identities when exercised, the current manifest scope and
  reverse dependencies.
- In `release_freeze`, bind one exact Git revision, complete manifest and
  denominator, dependency/runtime identities, selected scope and all release
  evidence before making candidate or publication claims.

Before choosing tests or artifacts, bind the work to one lifecycle mode. The
default is `development`; `integration_checkpoint` and `release_freeze` require
an explicit task or owner decision. Read [the development lifecycle](development-lifecycle.md)
for transition triggers, versioning, closure and artifact gates; do not duplicate
those rules in a task-specific route.

## Product-development loop

SciRel follows a standard-library product loop: one Git source tree is the
development truth while public API, implementation, tests, documentation,
benchmarks and CI evolve together. Use the affected selector and the smallest
checks that support the claim for ordinary source work. A direct product
change does not enter the D1 handoff loop unless it is consuming an exact D1
packet.

SciRel is the correctness boundary for each public operator and TaskGraph.
Keep the implementation, scientific input/output contract, failure semantics
and direct regression evidence in SciRel. Agent glue may discover, select,
compose and adapt a capability, but it does not reimplement domain mathematics
or use a successful composition as a substitute for direct capability
correctness.

Use a complete related change set as the unit of work. Inspect the Git base and
worktree before editing, capture an affected baseline when behavior or
performance is difficult to attribute, and keep unrelated edits out of the
commit. Public API or behavior changes carry their callable docstring and a
focused regression/contract test; add a user-facing page or example when the
scope warrants it. Performance claims carry a comparable benchmark with a
before/after observation. These are development checks, not a request to build
a wheel or regenerate release projections.

After the edit, rerun the affected selector and reverse dependencies. Unknown
ownership fails closed to a wider test layer. Finish with a reviewable diff and
the checks that support the claim. Create a Git commit when the requested
handoff or repository workflow calls for one; a continuation, status request or
unchanged evidence does not justify a new commit. A commit may contain several
compatible fixes, but it must not mix unrelated work.

Batch compatible local fixes into one reviewable change set when they share a
contract or dependency boundary. If one task touches several siblings in the
same domain or affected closure, keep them in one stable batch and perform the
final selector, work-management update and AOCI maintenance once. Split only
when ownership, risk, dependency boundary or stop condition differs; do not
turn each function-level improvement into a separate setup or maintenance
cycle. Git history preserves intermediate states, and no version or release
cycle is created for those improvements.

During development, docstrings, comments and draft notes are sufficient for
an evolving contract. Create or refresh exact asset documents and the catalog
when producing or binding a named artifact, discovery handoff, integration
checkpoint or review needs them; a stable batch or changed count alone is not a
trigger. Do not rebuild the complete
catalog for every edit. Keep one current working-tree representation and use
Git history for prior wording or code; do not copy full wheel, document or
catalog trees into version directories.

For packaging changes, measure the actual capability dependency and native/ABI
closure before changing the distribution shape. Keep a common wheel when the
same Python sources and runtime closure support the target platforms; introduce
platform-specific wheels only for a demonstrated platform or native boundary,
with a focused install check for that boundary.

Without an exact D1 packet, keep product work on this direct development path.
Do not manufacture a D1 manifest or complete denominator to enter the
correctness or normalization sub-skills for a local API, import, performance or
packaging change.

AOCI is a repository-maintenance aid, not a development gate. For a local
source or skill change, read only the related evidence. If the final change
touches an AOCI-managed object, perform one applicable `aoci_maintain` after
the batch reaches its final stable state, following the repository's AOCI
closeout rules; do not repeat it for every commit or intermediate edit. This
does not start a full Overview/Attestation unless the task actually requires
complete repository cognition.

Use the lifecycle reference's minimal execution and stop rule for ordinary
development; do not repeat that policy in a routed skill.

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
