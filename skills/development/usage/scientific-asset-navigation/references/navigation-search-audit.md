# Scientific Asset Navigation Report

The navigation report is an AI-authored, project-native record. It must bind
the requirement and catalog snapshot used for the search and distinguish route
selection from executable compatibility.

## Required fields

```text
requirement_binding:
  requirement_id
  requirement_revision
  requirement_digest
catalog_snapshot_binding:
  catalog_id
  release_version
  root_digest
  coverage
route_facets:
  output
  implemented_direction
  relation_or_model
  branch
  geometry
  coordinates
  boundary
  lifecycle
  ports
  applicability
  requested_claim
aliases_considered: [...]
route_records_loaded: [...]
summary_records_loaded: [...]
exact_records_loaded: [selected and dependency asset IDs]
exact_match_audit: [...]
lossless_adapter_audit: [...]
composition_audit: [...]
scientific_near_misses: [...]
metadata_gaps: [...]
shortlist: [...]
selected_asset_ids: [...]
selected_dependency_asset_ids: [...]
evidence_ceiling_per_candidate: {...}
unsearched_regions_and_bounds: [...]
navigation_outcome
```

For each selected or rejected exact asset, record its stable asset ID, exact-record path,
the compared fields, and the reason for the result. The enclosing release root digest binds
the record content. Do not add a second per-asset revision or digest contract. A route record
or summary without exact material is not enough for an `asset_exact_match` or
`asset_adapter_compatible` result.

## Loading audit

Record the sequence and count, not only the final list. The minimum audit is:

```text
route index loaded first: yes/no
summary loaded only after route filtering: yes/no
exact material loaded only after shortlist: yes/no
summary count
exact count
budget
```

If any answer is `no` or cannot be established, preserve that as a navigation
method gap. Do not reconstruct the sequence from timestamps or from the final
answer.

## Adapter audit

Each proposed adapter records:

- source and target ports;
- unit, dtype, axis, index, shape, storage, or file-format change;
- why information is preserved;
- failure behavior; and
- adapter digest.

Interpolation, extrapolation, closure, boundary completion, geometry
reconstruction, missing-state production, and physics-specific normalization
are not lossless adapters.

## Composition audit

Each proposed composition records:

- stable dependency asset IDs from the pinned release;
- typed input/output ports;
- execution order;
- state and lifecycle ownership;
- feedback and convergence contract;
- same-snapshot requirement, when applicable;
- failure propagation; and
- composition depth, pruning basis, and unsearched branches.

An absent leaf output does not justify `asset_unavailable` until compatible
composition has been audited within the declared search bound.

## Coverage boundary

Record whether pagination was exhausted and copy the release coverage declaration. Exhausting the inspected pages
or every included record in a partial catalog supports only an inspected-scope gap. `asset_unavailable` requires a
complete visible release and an exhausted search order.

## Outcome ceiling

The report must return exactly one navigation outcome:

```text
asset_exact_match
asset_adapter_compatible
asset_composition_match
asset_near_miss_scientific
asset_metadata_gap
asset_unavailable
needs_scientific_input
```

The report must preserve every selected asset's evidence ceiling and may
only lower it. It cannot produce `expert_approved`, `released`, or `published` as a
navigation outcome.
