---
name: scientific-asset-navigation
description: Use when finding, comparing, shortlisting, adapting, or composing existing scientific assets from a large catalog for an already normalized scientific requirement. Does not define the requirement, implement or validate new science, curate/admit/publish assets, or make human review decisions.
---

# Scientific Asset Navigation

## Purpose and boundary

In any supported harness, a scientific-library release is a plugin-owned published dependency,
not a user-supplied bundle or platform business record. Use the catalog snapshot selected for the
current run to identify matching scientific contracts. Confirm callable availability in the bound
runtime only for assets that survive exact-record comparison and are selected for a solution plan.
Installation or a Python import alone does not prove scientific suitability or release
status. Do not require the user to upload, name, or install a particular named library to start discovery; report an
unavailable authorized catalog or runtime to the coordinator as an environment gap.
First check the current harness's declared connector, mounted snapshot or environment resource for the bound catalog;
it need not live in the user project's files. If a selected environment declares one, inspect that binding before
reporting the catalog unavailable. Do not guess arbitrary filesystem paths or use an import as a substitute.

When an authorized catalog snapshot is present, it is the sole discovery surface and scientific
contract source for that navigation run. Do not search package exports, source trees, tests,
provenance, historical admission records, distribution manifests, or wheel-private manifests to
find capabilities omitted from the catalog or to fill missing catalog fields. Such material may be
used only to diagnose a mismatch for a catalog-selected asset; the mismatch is an environment or
catalog integrity gap, not a new candidate. An importable callable without an exact catalog record
cannot appear in the shortlist or a composition.
Do not enumerate or resolve every runtime callable to prove catalog completeness, and do not invoke
a rejected near miss to demonstrate its documented failure. Its exact record is the authority for
the rejection; runtime probing begins only after scientific applicability has been established.

Find reusable scientific capabilities for a frozen `NormalizedScientificRequirement` and return a
bounded, auditable shortlist. The selected catalog and installed release remain fixed for the run. This
skill reads their projections but never edits them or silently creates a canonical asset.

This skill covers catalog navigation only. It does not perform or control:

- user-intent elicitation or requirement freezing;
- scientific relation implementation, source modification, or numerical method selection;
- scientific validation, oracle construction, or trust-packet freezing;
- candidate merging, expert review, release, or publication; or
- a particular programming language, runtime, platform, or package layout.

An explicitly authorized isolated development/platform trial may bind a supplied unapproved wheel and
its matching catalog instead of a public release. Keep that development status and the catalog's partial
coverage visible; this changes the admitted input, not the applicability or evidence rules. Physical-domain
usage pages help orient the user and explain the problem. They do not admit an importable API omitted from
the bound exact catalog or turn a compatibility reference into a scientific contract.

If no catalog is available, do not block the project. Return control to
`scientific-project-implementation`, which may use supplied source code, ordinary numerical libraries,
or a new relation route independently.

Navigation produces routing evidence only. A catalog match does not create or advance a plugin
candidate, review, catalog, or release record; a missing catalog is an environment gap rather than
permission to invent a replacement asset.

## Inputs and output

Input:

1. one frozen `NormalizedScientificRequirement`;
2. one authorized catalog snapshot and its route index;
3. optional capability summaries and exact records loaded by id; and
4. a context/load budget supplied by the caller, or a bounded budget chosen and recorded before loading.

The requirement must identify, as far as currently known, the requested output, implemented direction,
model, geometry, boundary, lifecycle, ports, units, axes, applicability domain, requested claim, and
composition pattern. Missing case values can remain callable inputs. A missing scientific choice must
remain `needs_scientific_input`; do not fill it with a catalog default.

If the coordinator has only an explicitly draft requirement, this skill may produce a bounded discovery
shortlist to help clarify the requirement, but it must return `needs_scientific_input` and may not emit
`asset_exact_match`, `asset_adapter_compatible`, `asset_composition_match`, or `asset_unavailable`.
Catalog candidates must not become the source of requirement normalization.

Return one `ScientificAssetNavigationReport` with these logical fields:

```text
requirement_binding
catalog_snapshot_binding
route_facets
aliases_considered
route_records_loaded
summary_records_loaded
exact_records_loaded
exact_match_audit
lossless_adapter_audit
composition_audit
scientific_near_misses
metadata_gaps
shortlist
selected_asset_ids
selected_dependency_asset_ids
evidence_ceiling_per_candidate
unsearched_regions_and_bounds
navigation_outcome
```

See [references/navigation-search-audit.md](references/navigation-search-audit.md) for the required
audit shape. The report is a navigation result, not product truth.

## Search strategy and coverage

Prefer the following search progression; adapt ordering to available evidence and record what was actually searched. Skipped or unsearched regions remain explicit, and an `asset_unavailable` claim still requires sufficient scope coverage:

1. exact normalized scientific identity and implemented direction;
2. source-local names, scientific synonyms, and domain aliases;
3. information-preserving adaptations of fields, units, dtype, axes, indices, shape, storage, or file
   format;
4. compatible compositions with explicit order, state ownership, lifecycle, feedback, and failure
   propagation;
5. scientifically different near misses and their disqualifying dimensions;
6. missing metadata or contract evidence that prevents an applicability decision; then
7. `asset_unavailable`, only when the authorized search scope is complete enough to support that claim.

Route primarily by discriminating typed scientific facets, using this progression where useful:

```text
requested output
  -> implemented direction
  -> relation/model and branch
  -> geometry and coordinates
  -> boundary and closure
  -> state lifecycle and ownership
  -> ports, units, axes, shape, dtype, and indexing
  -> applicability domain and evidence ceiling
```

Project provenance, lexical similarity, embeddings, and source file names may improve recall only. They
cannot override a typed incompatibility or establish scientific equivalence.

## Progressive disclosure

Do not load a large catalog into context. Record positive, bounded summary and exact-record budgets before reading records and
respect caller/catalog limits. Report any remaining coverage gap instead of converting an exhausted budget into
`asset_unavailable`.
An exhausted page or every included record inspected does not override `coverage.status=partial` or a larger
declared asset count. In that case the outcome remains an inspected-scope gap, never `asset_unavailable`.

Use this disclosure sequence. Keep intermediate material small, and preserve every load and snapshot binding:

```text
route index
  -> bounded capability summaries
  -> exact material for the final shortlist
```

The route and summary projections are sufficient to reject clearly unrelated records. Do not read every exact record
to prove that a capability is absent. Load exact material only for the final shortlist and near misses whose detailed
contract is needed to support the rejection.

Record every load and every rejected candidate. If a route index is absent, stale, or not bound to an
owner-issued ref or revision,
return `asset_metadata_gap`; do not claim the catalog has no matching asset.

An exact-detail request is not an exact match. Until the exact record is loaded and its contract is
checked, the result is only a shortlist or `asset_metadata_gap`.
For an executable selection, `exact_records_loaded` must contain every selected asset ID and every dependency
asset ID needed to validate the plan. A name mentioned only in the final answer is not a binding.

## Compatibility decisions

For each shortlisted candidate compare the requirement with the exact contract field by field:

- relation identity and implemented direction;
- model, branch, geometry, coordinates, and boundary/closure;
- state lifecycle, update order, ownership, and terminal/failure behavior;
- input/output ports, units, axes, shape, dtype, indexing, and normalization;
- applicability domain and requested claim; and
- stable asset ID, implementation version, dependency asset IDs, and the enclosing catalog release/root digest.

Classify differences explicitly:

- `asset_exact_match`: identity and callable contract match;
- `asset_adapter_compatible`: all remaining changes are declared, information-preserving, and
  non-scientific;
- `asset_composition_match`: existing resources form the capability under explicit contracts;
- `asset_near_miss_scientific`: at least one material scientific dimension differs;
- `asset_metadata_gap`: a decision is blocked by missing contract/evidence;
- `asset_unavailable`: the bounded search order is exhausted; or
- `needs_scientific_input`: the requirement itself does not select one mapping.

Do not hide these scientific relations in an adapter or composition edge:

```text
interpolation, extrapolation, boundary completion, geometry reconstruction,
closure, dimensional reduction, missing-state reconstruction, physics-specific
normalization, discretization, matrix/RHS production, or scientific update rules
```

They require a scientific relation implementation and validation route.

Lossless adapters may only rename fields, convert explicitly compatible units or dtypes, permute axes,
translate index bases, select explicitly declared components, preserve information in another storage
layout, or translate a file format. Record the direction, proof of information preservation, and failure
behavior.

Composition may connect typed ports and declare order, lifecycle, ownership, feedback, convergence, and
failure propagation. It must bind stable dependency asset IDs from the same pinned catalog release.
Search compatible composition before returning `asset_unavailable`, but keep composition depth and
unsearched branches explicit.

## Evidence ceiling

Copy each candidate's recorded evidence ceiling into the report. Never upgrade it because the candidate
looks similar, is selected, or has a source comparison. In particular:

- source parity proves source behavior only;
- implementer tests are not independent validation;
- a bounded candidate is not a universally correct physical model; and
- missing evidence lowers the claim or produces `asset_metadata_gap`.

The navigation skill may recommend a candidate and state its bounded evidence. It may not call a
upgrade an asset's evidence ceiling, merge variants, approve it, or release it.

## Fail-closed behavior

Return a bounded shortlist with gaps when the exact contract is unavailable. Preserve separate variants
when units, axes, boundary, model, geometry, lifecycle, or claim differ. Preserve conflicting provenance
until an authorized scientific decision exists. A failed navigation query is not permission to synthesize
an equation or invent a bridge.

Do not emit `asset_unavailable` until the report contains explicit audits for:

```text
exact identity, aliases, lossless adapters, compatible compositions,
scientific near misses, metadata gaps, search bounds, and catalog snapshot identity
```

## Handoff

`scientific-project-implementation` consumes this report and may preserve or lower its conclusion. It
must bind the selected requirement revision, catalog ID/release version/root digest, selected asset and
dependency IDs, task-local adapter/composition descriptions, evidence ceilings, metadata gaps, and unsearched bounds. It may proceed with a
source-native or ordinary-library implementation when the report has no usable catalog result.

When the selected path changes a scientific relation, send the frozen candidate and its gaps to
`scientific-relation-implementation` and `scientific-computation-validation`. Navigation does not
replace those skills.

## Contract records

When exact record fields are needed, read
[references/catalog-record-contracts.md](references/catalog-record-contracts.md). The records are
release-bound projections. They do not create review, approval, or publication authority.
