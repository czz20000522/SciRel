# Extraction Workflow Optimization

Use this reference to reduce repeated D1 extraction cost without changing the scientific scope or freeze meaning.
It describes run methodology, not candidate-bundle content. Keep indexes, telemetry, experiments, and comparison
receipts in the run-owned evidence area; do not export them as L1 assets.

## Preserve the quality boundary

Freeze the source/evidence universe, declared scope, target paths, runtime conditions, skill bundle digest, and
current `full_freeze` contract before comparing workflows. The candidate workflow must still account for the same
source scope and pass the same candidate, dependency, source-free, canonical, sealed-holdout, and capability-progress
gates. Do not trade an unresolved scientific relation, material branch, state lifecycle, or terminal output for a
lower cost metric.

Efficiency measures are diagnostic only. Select the smallest useful set for the suspected mechanism, such as wall
time, model turns, tool calls, repeated source bytes inspected, failed queries, retries, candidate reopenings, or
manual handoffs. No universal score or fixed improvement threshold is required.

## Structural evidence index

A preprocessor may emit a digest-bound, run-local index with:

- source files, languages, parse status, and excluded paths;
- symbols and source spans with stable anchors;
- static references, call edges, imports/includes, and explicit state reads/writes;
- candidate entry points, tests, examples, fixtures, and documents;
- tool/version/query provenance, unresolved dynamic edges, failures, and confidence limits.

This layer automates navigation and inventory only. It must not label a relation as scientifically public, decide an
operator or TaskGraph boundary, resolve Fortran common state or dynamic callbacks without evidence, determine a
document's scientific authority, or claim coverage. The extraction agent must be able to open the indexed source,
challenge the index, and run a bounded source/runtime probe. Prefer a tool-neutral intermediate shape so CodeGraph,
Joern, tree-sitter, language servers, compiler indexes, or repository-native tools can be compared without changing
the scientific method or making any one dependency mandatory.

## Bounded comparison

Record a baseline and one selected candidate workflow using comparable inputs and environments. Account for
differences in model/provider, cache state, concurrency, available dependencies, prior artifacts, and source runtime.
When practical, verify that the evaluation distinguishes an intentionally incomplete or stale index from a valid one;
otherwise a cheaper run may only demonstrate a blind evaluator.

Compare quality first: source census and dispositions, target-path and branch coverage, port/state completeness,
candidate claim ceilings, canonical and sealed-holdout reassembly, provenance, and unresolved gaps. Then compare the
selected efficiency observations. Inspect whether apparent savings came from scope shrinkage, unrecorded reuse,
evidence leakage, deferred work, or reduced oracle independence.

Choose the best currently supported workflow and stop the optimization pass. A single project is a bounded pilot,
not proof of universal improvement. Record the conditions, result, regressions, confounders, and next evidence that
would justify another revision; do not keep iterating in search of an absolute optimum.
