---
name: scirel-integration
description: Coordinate D2 integration of saved D1 assets into a runnable scientific development library, routing correctness, normalization, repair and documentation with exact evidence.
---

# SciReL D2 integration

Read [the shared operating contract](../../references/scirel-development-core.md).
Own the D2 queue and the durable development candidate: compare, deduplicate, route correctness, normalize,
assemble and prepare stable documentation. D1 fidelity (including original errors) and D3 application evidence are
separate. This skill cannot grant human approval, rights or release.

## Coordinator loop

When the task consumes an exact D1 packet, run the following coordinator loop.
For direct SciRel product development without a D1 packet, use the product
development path below and do not invent a D1 freeze or a complete project
denominator.

1. Freeze the D1 handoff, complete denominator, target/dependency hashes, source issues, runtime and rights/licence
   evidence. Keep upstream deliveries read-only and preserve every failure/`NOT_RUN` row.
2. Route each issue once: scientific/numerical claim to [asset correctness](../scientific-asset-correctness/SKILL.md);
   selected qualified batch to [normalization](../scientific-asset-normalization/SKILL.md); source-only gap back to D1;
   application/repeatability to D3. Do not send every intermediate choice to a human.
3. For a confirmed determinate defect, use [scientific correction](references/scientific-correction.md):
   diagnose, implement successor, independently validate, then obtain read-only review. A defect list is not
   remediation; temporary runtime failure remains pending with a reopen condition.
4. Assemble only compatible contracts. Preserve ports, units, axes, state ownership, order, convergence, exceptions,
   native/build/ABI and dependency closure. Do not hide science in glue or replace failure with a warning.
5. Reuse evidence by exact identity; rerun affected reverse dependencies after changes. Produce a stable candidate,
   exact integration manifest, evidence matrix, limitations, unresolved owner decisions and next review owner.

Formal asset documents are created once code is stable and before final review freeze. The compact handoff is evidence,
not approval or release; the receiving project supplies lifecycle and distribution policy.

## Direct product-development path

For a source, API, test, documentation or performance change made in the
SciRel tree, bind the Git base/head and the affected public surface, then use
the repository's affected selector and reverse dependencies. Add a regression
before changing scientific behavior, keep existing tolerances and failure
semantics, and update the callable docstring/user-facing example when a public
contract changes. Update benchmarks when making a performance claim and record
a comparable before/after observation. Accumulate complete related changes in
Git; do not mix unrelated work into the same commit. A stable batch, changed
capability count or buildable wheel does not create a checkpoint by itself; do
not build an installed wheel, update `release/CURRENT.json`, generate a release
receipt or run the full platform matrix unless a named consumer,
owner-requested checkpoint or `release_freeze` requires it.

Keep the direct path in `development` unless the task names a consumer,
handoff or release decision. Use the canonical
[development lifecycle](../../references/development-lifecycle.md) for version,
closure and artifact rules; do not reproduce those gates here.
