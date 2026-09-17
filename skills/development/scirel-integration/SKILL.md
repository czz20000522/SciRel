---
name: scirel-integration
description: Integrate already-admitted scientific operators or TaskGraphs into SciRel, including identity comparison, incremental compatibility, affected-graph checks, and source-free wheel verification. Do not use it to approve candidates or publish releases.
---

# SciRel Integration

Use this workflow only after the exact input has a final human admission. Read [the architecture contract](../../../docs/architecture.md), [the development process](../../../docs/development-process.md), the relevant implementation/tests, and the selected records in `provenance/admitted-assets.json`. Admission evidence is an input; this skill grants no review or publication authority.

## Establish the integration decision

Bind the current Git/release baseline and each exact admission revision before editing. Compare the incoming asset both with the maintained library and with the rest of its batch. Decide whether to reuse an identity, add a new capability, retain a scientific variant, introduce a lossless adapter, compose exact assets, make a compatible replacement, or leave the relation unresolved.

Compare scientific meaning before code shape: direction, assumptions, model, geometry, boundary/closure, ports, units, axes, shape/dtype, state lifecycle, feedback, numerical method, applicability, failures, evidence ceiling, provenance, and license obligations. Hashes, names, lexical similarity, or a few equal results are discovery evidence only. Keep uncertain or materially different relations separate.

Record the decision once in the current task or existing assembly evidence. Do not create a parallel approval record, rewrite frozen provenance, or rerun a bulk import over maintained source.

Create or update the asset's `scirel.asset-document.v1` exact document only from verified contract evidence. Keep public provenance framework-neutral and exclude private admission/case/tenant refs. A TaskGraph document must bind exact dependency asset IDs/digests and declare ports, ordinary DAG edges, controlled feedback, stopping and failure propagation. If required scientific metadata is unavailable, preserve a metadata gap instead of synthesizing a complete-looking record.

## Implement incrementally

Keep the public surface as a domain-organized Python callable. Preserve compatible signatures, defaults, numerical assertions, tolerances, and failure behavior. If scientific behavior must change, first add a failing regression and identify whether a new candidate/review is required.

For a TaskGraph, bind exact node dependencies and declare typed edges, state ownership, ordering, feedback bounds, convergence, and failure propagation. Ordinary dependencies are acyclic; iteration is an explicit bounded feedback contract. Glue may perform only declared non-scientific transformations.

Trace reverse dependencies from every changed operator and test the affected graphs. Shared code may be deduplicated when its contract is truly shared, but implementation reuse does not merge scientific identities. Re-read the baseline before finalizing so concurrent changes are incorporated rather than overwritten.

## Verify at the appropriate level

Use `pwsh ./scripts/check.ps1 -Mode affected -ChangedPath <path>` during the ordinary inner loop. Its selected closure must include the changed asset, transitive TaskGraph consumers, shared implementation tests, and admission consistency. Use `-Mode focused -TestPath <tests>` only for a specific failing regression, then rerun the computed affected closure; do not manually narrow that closure. Unmapped SciRel source must fail closed to the full suite.

Run `-Mode full` when the affected surface or merge policy requires the repository baseline. For a release candidate, use `-Mode release -OutputRoot <new-directory>` and retain its wheel, manifest, acceptance report, tool versions, and hashes as the evidence for that candidate.

Source-free verification must install only the produced wheel into an isolated environment, clear `PYTHONPATH`, and prove imports resolve under that environment. A passing wheel does not expand scientific applicability or create admission/publication facts. Report actual changed files, checks run, compatibility impact, evidence limits, and unresolved decisions.

Before catalog projection, run `python scripts/validate_asset_documents.py <documents> --check-runtime --execute-examples`. Catalog/MCP/CLI/cloud adapters consume the validated document and wheel; they may not copy or alter its scientific semantics.
