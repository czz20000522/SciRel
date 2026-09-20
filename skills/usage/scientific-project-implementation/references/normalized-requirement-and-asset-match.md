# Normalized Requirement and Asset Match Records

Read this reference when creating or revising a `NormalizedScientificRequirement` or
`AssetMatchReport`. Use the user's project-native representation; the names below define logical fields,
not a required language, file type, platform API, or database schema.

## NormalizedScientificRequirement

Minimum fields:

| Field | Required content |
| --- | --- |
| `requirement_id` | Stable identity across revisions. |
| `revision` / `parent_revision` | Immutable revision chain. |
| `state` | `draft`, `normalized`, `reuse_checked`, `frozen`, `reopened`, `superseded`, or `blocked`. |
| `raw_intent` | The user's original words and constraints without reinterpretation. |
| `normalized_summary` | Given which explicit state, use which model/capability to produce which observable over which domain and boundaries, under which claim ceiling. |
| `scientific_target` | Observable, relation direction, physical domain, model/branch, applicability, and exclusions. |
| `callable_contract` | Inputs, outputs, units, axes, shapes, indexing, boundaries, lifecycle, and failures. Runtime case values may remain open parameters. |
| `claim_records` | Result-affecting claims, primary provenance, parent claims, and semantic anchors. |
| `claim_ceiling` | Strongest result the authorized evidence could currently support. |
| `route` | Reuse, adapter, composition, scientific modification, new relation, or blocked. |
| `decision_register` | Only unresolved choices that materially change science, safety, irreversible cost, or claim. |
| `implementation_binding` | Requirement, resource, adapter, composition, and exact revision refs consumed. |
| `validation_binding` | Requirement, claim ceiling, register, fixtures, evidence, and runtime consumed. |
| `reopen_policy` | Semantic changes that invalidate downstream bindings. |
| `risk_tier` | Ordinary reuse, research candidate, or high-risk production. |

Each claim uses one primary provenance:

| Provenance | Treatment |
| --- | --- |
| `user_asserted` | Authoritative for user intent, not automatically for physical truth. |
| `authoritative_source` | Exact paper, equation, reviewed asset contract, source semantics, or expert ruling. |
| `physically_derived` | Derived consequence with parent claims and derivation recorded. |
| `ai_recommended_default` | Reversible recommendation that does not silently select material physics. |
| `exploratory_hypothesis` | Unaccepted candidate with applicability, uncertainty, and discriminating evidence. |
| `unresolved_decision` | Material choice that blocks only the scope depending on it. |

Do not use `assumed` to hide a governing equation, closure, boundary physics, state lifecycle, or nonlinear
update rule.

## AssetMatchReport

When an authorized scientific catalog is available, the catalog-specific
search and loading procedure is owned by
`scientific-asset-navigation`. This record is the coordinator's binding of
that report into the user project. It must not duplicate a second search
algorithm. When no catalog is supplied, the coordinator records the absence
and continues with the user's source, ordinary libraries, or a new relation.

### Query identity

Record:

- relation family and implemented direction;
- primary output and required observables;
- physical domain, coordinates, geometry, axes, and applicability;
- model, branch, closure, boundary policy, state lifecycle, and ownership;
- normalization, signs, units, shapes, indexing, dtype, and validity domain;
- requested claim and required composition pattern;
- requirement identity and revision.

Also preserve the navigation report's exact binding when it exists:

- catalog ID, release version, root digest, and coverage declaration;
- route, summary, and exact-material load audit;
- selected asset IDs and dependency asset IDs;
- task-local adapter and composition descriptions;
- evidence ceilings per candidate; and
- unsearched regions and metadata gaps.

### Search order

1. Exact normalized scientific identity and implemented direction.
2. Source-local names, scientific synonyms, and domain aliases.
3. Information-preserving field, unit, dtype, axis, index, shape, storage, and file-format adaptations.
4. Compatible resource composition under explicit ordering, same-snapshot, feedback, and lifecycle contracts.
5. Scientifically different near misses and their disqualifying dimensions.
6. Missing metadata or contract evidence that prevents an applicability decision.
7. Only after steps 1–6, `asset_unavailable`.

For a large catalog, completeness is relative to an authorized catalog/library snapshot, not an
unbounded claim about every possible asset. Record the owner-issued snapshot ref/revision, staged query/filter
plan, candidate counts after each stage, selected and representative near-miss candidates, and
disqualification categories. Composition search records its depth/branch limits, pruning basis, and any
unsearched region. This audit need not enumerate every asset or combination, but it must make the searched
scope reproducible. If the snapshot, index, or pruning coverage cannot support that claim, return
`asset_metadata_gap` rather than `asset_unavailable`.

### Coverage outcome

Return exactly one:

| Outcome | Meaning |
| --- | --- |
| `asset_exact_match` | Scientific identity and callable contract match. |
| `asset_adapter_compatible` | Remaining differences are explicit, lossless, and non-scientific. |
| `asset_composition_match` | Compatible existing resources form the requested capability. |
| `asset_near_miss_scientific` | A material scientific dimension differs. |
| `asset_metadata_gap` | Reuse may exist, but contract evidence is insufficient. |
| `asset_unavailable` | The complete search order was exhausted. |
| `needs_scientific_input` | The normalized request does not select one mapping. |

Separately record selected-resource provenance: `reuse_project`, `reuse_asset`, and/or `reuse_library`.

## Adapter and composition boundary

A non-scientific adapter may rename fields, convert explicitly compatible units or dtypes, permute axes,
translate index bases, select explicit components, preserve information in another shape/storage layout,
or translate file formats. Declare its direction, units, axes, information-preservation argument, and
failure behavior.

Interpolation, extrapolation, boundary completion, geometry reconstruction, closure, dimensional
reduction, missing-state reconstruction, and physics-specific normalization are scientific or numerical
relations. Composition glue may wire ports and declare order, lifecycle, ownership, feedback, convergence,
and failure propagation; it may not produce a scientific formula, matrix/RHS, interpolation,
discretization, or closure.

## Revision binding

Every implementation and validation receipt binds:

```text
requirement_id
requirement_revision
selected project/library revisions, when applicable
catalog ID, release version, root digest, and selected asset IDs, when applicable
task-local adapter and composition bindings
claim ceiling revision
validation register, fixture, and evidence revisions
```

Ordinary records use owner-issued refs and revisions. Do not add hashes for routine requirement,
implementation, or validation confirmation. The catalog root digest is the release integrity boundary; do not add
parallel per-asset hashes. Keep another digest only for a real integrity boundary:
external package/data import or export, cross-device transfer, signed publication, secret lookup, or a
necessary compare-and-set operation.

Create a new requirement revision when the observable, relation direction, model, closure, boundary
physics, regime, normalization, port semantics, branch, state lifecycle, safety boundary, or requested
claim changes. Preserve old evidence without applying it to the changed scope. Case values and output
formatting do not reopen the requirement while they stay inside the callable contract.

## Compact worked example

User intent: “计算一个轴对称磁镜平衡，并输出磁轴上的 `|B|` 和压力分布。”

The normalized requirement selects an axisymmetric mirror, axial coordinate, field magnitude, isotropic
pressure, SI output, and a callable whose concrete geometry/profile values remain runtime inputs. The
catalog contains:

- `mirror-axis-equilibrium-v2`: matching mirror model and outputs with an explicit boundary contract;
- `mirror-field-converter-v1`: field rename plus gauss-to-tesla conversion;
- `tokamak-gs-equilibrium-v4`: a Grad–Shafranov tokamak branch.

The match report:

1. selects `mirror-axis-equilibrium-v2` as `reuse_asset`;
2. rejects the tokamak asset as `asset_near_miss_scientific` because geometry/model identity differs;
3. selects the converter only when the caller supplies the declared gauss/name representation;
4. records the final coverage as `asset_exact_match` without conversion or
   `asset_adapter_compatible` with the lossless converter; and
5. asks no user question because missing concrete case values are callable inputs, not missing science.

The project may now build the user's requested artifact around the frozen asset contract. It does not
implement a new equilibrium relation or claim physical validation beyond the selected asset revision.
