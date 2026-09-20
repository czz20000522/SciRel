# Scientific Catalog Record Contracts

This reference summarizes the records a navigation run actually consumes. Product truth remains in
[`asset-documentation.md`](../../../../docs/requirements/asset-documentation.md),
[`catalog-and-adapters.md`](../../../../docs/design/catalog-and-adapters.md), and the versioned schemas under
`contracts/`. Do not introduce candidate, review, or source-extraction records into release discovery.

## Release record

`release.json` uses `scirel.catalog-release.v1` and binds one catalog snapshot through:

- `catalog_id` and `release_version`;
- `coverage.status`, `included_asset_count`, and `declared_total_asset_count`;
- the disclosure order `routes -> summaries -> exact_records`;
- every record/index partition path, byte count, and SHA-256; and
- one `root_digest` over the release record.

The release root is the content-integrity boundary used by a navigation run. Do not invent a second per-asset
revision scheme or interpret a partial snapshot as complete.

## Route record

A route is a small discovery projection keyed by stable `asset_id`. It contains the asset kind, taxonomy,
relation, implemented direction, outputs, typed routing facets, and the path to its exact record. It supports
bounded filtering only. A route hit is not an applicability decision.

## Summary record

A summary is a bounded shortlist projection keyed by the same `asset_id`. It exposes enough identity, port,
applicability, limitation, public-callable, and evidence-ceiling information to reject unrelated candidates
without loading exact documents. Omitted detail remains unknown; do not infer it from the summary.

## Exact asset document

The exact record uses `scirel.asset-document.v1` and is the scientific authority for a selected released asset.
Read it before selecting or composing the asset. In particular, compare:

- relation, direction, assumptions, model, geometry, coordinates, boundary and closure;
- typed inputs and outputs, including units, shape, dtype, axes, required/default status and constraints;
- applicability, exclusions and failure semantics;
- stable Python module, symbol and exact signature;
- `implementation_version` and stable dependency asset IDs;
- TaskGraph nodes, edges, ordering, state and bounded feedback when present; and
- verification scope, evidence ceiling and known limitations.

Private candidate, reviewer, tenant, session, admission, decision and host fields are forbidden in this document.
The installed callable is usable only when its implementation version and signature match the exact document.

## Reverse dependencies

Reverse-dependency records are a release-derived impact projection. They help inspect a selected asset's consumers;
they do not create a composition or override dependencies declared by exact documents.

## Adapter projection

When using the thin adapter, the only operations are `catalog.discover`, `asset.read`, `callable.resolve`, and
`callable.invoke`. Read [`thin-mcp-adapter.md`](../../../../docs/requirements/thin-mcp-adapter.md) for the exact
request and response envelopes. Discovery and reads return `items`; exact documents use `detail="document"`.
Transport identity, authorization, resource limits and audit stay with the harness.
