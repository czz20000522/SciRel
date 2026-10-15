---
name: scientific-asset-navigation
description: Find, compare, shortlist, adapt or compose existing scientific assets for an already normalized requirement using one bound catalog snapshot.
---

# Scientific asset navigation

Read [the shared operating contract](../../references/scirel-development-core.md).
This D3-facing skill returns a bounded, auditable shortlist. It does not define the requirement, implement or
validate new science, curate/admit/publish assets or make human decisions.

## Discovery boundary

Bind the current harness connector/mounted catalog snapshot, release identity and runtime. The bound catalog is the
sole discovery and applicability surface for this run. Do not search exports, source trees, tests, provenance,
historical admission records or wheel-private manifests for undocumented capabilities. An importable callable
without an exact catalog record is unavailable; a catalog/runtime mismatch is an environment gap.

## Progressive route

1. Read the normalized requirement: relation/direction, model, geometry, coordinates, units, axes, boundaries,
   inputs/outputs, failure semantics and evidence ceiling. Search summary/index records first.
2. Return a small shortlist with exact IDs/versions, contract match, mismatches, applicability, evidence ceiling and
   inspected scope. Read full documents only for serious candidates and scientific near misses. Partial pagination is
   an inspected-scope gap, not proof of release-wide absence.
3. For each selected candidate, run preflight against actual adapter/catalog operations and declared ports. Do not
   invoke rejected near misses or guess connector envelopes. If the selected task requires an adapter, use its actual
   `catalog.discover -> asset.read(detail=document) -> callable.invoke` path and retain compact operation receipts.
4. Compose only compatible ports. Check units, shapes, axes, coordinates, normalization, state/order, branches and
   failure propagation. Iteration needs explicit state, stop/convergence condition and bound.
5. Hand the selected plan to project implementation or validation. A per-request run instance is not a catalog asset.

A missing capability is a release capability gap only when the complete bound catalog is known and inspected. Never
replace an incompatible asset with a weaker model. Load [navigation audit](references/navigation-search-audit.md) only
when a search/audit receipt is requested.
