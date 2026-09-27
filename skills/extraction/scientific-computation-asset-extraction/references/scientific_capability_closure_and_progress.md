# Scientific Capability Closure and Progress

Use this reference before Level 0/Level 1 package projection and throughout a long extraction run. It
adds an equation-centered scientific capability web to the existing framework views, defines the
discovery denominator, target-path priority, current progress projection, and active frontier. It does
not add a formal asset type or replace Level 0/Level 1.

## 1. Discover scientific closure, not source structure

Before freezing the denominator, make a source-first terminal-output inventory independently of the current
candidate list. Follow public callable returns, physically meaningful diagnostics, tested/example call paths,
model selectors, and versioned or archived source trees included in the bound source digest. For each named output
or branch, point to its source anchor and either a target path, an asset that already covers the same relation,
or a specific non-candidate/version disposition. A whole archive, public routine group, or selector cannot be
dismissed by a broad label such as `harness`, `external producer`, or `default not used` when it contains executable
physics. A distinct source version may have its own freeze claim, but then the current source scope and completion
claim must say so explicitly. Conversely, an alternate hard-coded parameter fixture of an already source-supported
generic relation is not automatically a new capability. An independent reviewer repeats this source-first pass
without deriving its search denominator from the candidate's target list; compare the two inventories before M0
or `full_freeze` is accepted. A structural index helps find anchors but does not decide the scientific disposition.

Start from each inventoried terminal scientific output or state. Identify the governing equation or coupled
equation system, place it at the center, and expand outward to the smallest well-posed closure slice that
can produce the target under one declared case:

```text
governing relation or scientific rule
+ constitutive/empirical closure
+ initial and boundary conditions
+ geometry, coordinates, units and normalization
+ discretization or stochastic/optimization transition
+ state lifecycle, update order and coupling
+ declared terminal diagnostic
```

Only include a term when the target consumes it or changing it changes the scientific result. A boundary,
geometry transform, table, interpolation, update order, or lifecycle policy is scientific semantics when
it changes the model or discrete result; do not demote it to glue merely because it is not the central
equation.

Not every scientific program is equation-shaped. Admit these normalized anchor kinds:

- `governing_equation`
- `constitutive_closure`
- `boundary_or_initial_condition`
- `geometry_or_coordinate_relation`
- `stochastic_law`
- `optimization_objective_or_constraint`
- `table_or_empirical_relation`
- `numerical_state_transition`
- `cross_relation_coupling`
- `diagnostic_definition`

The central equation is an identity anchor, not automatically an operator. The surrounding reusable
directed scientific mappings are nodes, and every canonical leaf node projects to an operator. A stable
ordered subweb may project to a task graph, but the task graph is the executable description of that
local piece of the web rather than another scientific leaf. It must identify the participating nodes and
edges and express their order, branch, feedback, iteration, convergence, and state lifecycle. A progress
or overview view may collapse the subweb as a macro only when it retains those underlying identities.
Runtime edges carry explicit ports and bounded glue. They may perform only
information-preserving unit, axis, index, shape, storage, or selector adaptation. If an edge performs
interpolation, boundary synthesis, closure, discretization, scientific normalization, or state update,
promote that computation to a node. Task graphs own the required order, branch, feedback, convergence, and
state lifecycle.

Keep serialization, plotting, logging, process launch, storage layout, and lossless port conversion outside
the scientific closure graph unless source evidence proves that they encode one of those semantics.

## 2. Target-path and capability records

For each declared target, record:

```text
target_id
terminal_scientific_output_or_state
primary_state
required_capability_ids
material_branch_or_domain_partitions
semantic_completion_marker
terminal_output_state_contract
```

For each central equation, record:

```text
equation_id
equation_role
compact_equation_or_system_identity
target_paths
authority_refs
```

For each scientific node, record:

```text
capability_id
anchor_kind
equation_anchor_ids
implemented_direction
primary_inputs_and_outputs
model_and_domain
geometry_coordinates_units
initial_boundary_closure_policy
discretization_or_transition_semantics
state_lifecycle_and_owner
source_anchors
required_for_target_paths
asset_projection
```

For each local task-graph subweb, record:

```text
subweb_id
equation_anchor_ids
participating_node_ids
participating_edge_ids
order_branch_feedback_iteration_convergence
state_lifecycle_and_owner
required_for_target_paths
asset_projection
```

The external progress snapshot places both record types in `work_units` and uses `node_role` values
`operator_node` and `task_graph_subweb` to distinguish them. That normalized progress field does not make
the subweb a scientific leaf.

For each web edge, record:

```text
edge_id
from_node_id/from_port
to_node_id/to_port
edge_role (port_binding | controlled_glue)
required_for_target_paths
closure_status (proved | pending | blocked | terminally_classified)
blocker (null only when proved)
```

Every edge endpoint must resolve to a declared work unit. Every `task_graph_subweb` must list its
participating node and edge IDs, and every listed edge must have both endpoints inside that local subweb.

Build these records by backward slicing every target and forward slicing its declared inputs. Reconcile
the slices and bind each capability to Level 1 source/state evidence. Reconcile the web against Level 0's
project-wide scientific process and Level 1's source-anchored data/state flow. Source files, routines, and
call graph nodes are anchors and search partitions, not capability identities or completion units.

## 3. Extraction priority

Assign one priority:

- `P0_primary_solution`: the principal solve, advance, reconstruction, objective, or sampling transition;
- `P1_required_closure`: a boundary, geometry, constitutive, state, or coupling capability required to
  make a P0 path well posed and executable;
- `P2_material_branch_or_lifecycle`: an alternate model/boundary branch, feedback, restart, stochastic,
  parallel, or lifecycle variant that materially changes behavior;
- `P3_principal_diagnostic`: a declared scientific output not already required by P0-P2.

Extract one minimal P0+P1 target path first, including every scientific boundary and state dependency it
actually requires. Then cover P2 branches/lifecycle and P3 diagnostics. Do not chase helper counts or
hidden state unrelated to a declared target merely to increase inventory.

## 4. Milestone extraction order

Use the same five milestones for every large source project:

| Milestone | Completion basis | What it does not prove |
| --- | --- | --- |
| `M0_equation_census` | census is frozen; every source partition is mapped and every declared target path is traced | no asset is necessarily callable |
| `M1_minimal_golden_path` | every target named in `target_ids` has passed source-free functional reassembly from identical explicit inputs | other branches, devices, or target paths |
| `M2_replaceable_scientific_slices` | every selected capability is emitted with all five gates passed and every selected edge is proved | project-wide closure or unknown modifications |
| `M3_branch_lifecycle_expansion` | every selected material branch/lifecycle partition is proved | unselected long-tail partitions |
| `M4_extraction_freeze` | frozen census and conservative `overall=1.0` for one bound bundle revision | behavior or fitness outside the declared source scope |

`M1` closes one executable scientific spine before the extraction expands sideways. `M2` then prioritizes
the scientific owners most likely to be replaced or reused; it must name both nodes and material edges.
`M3` expands only the declared branch/domain denominator. `M4` is the bounded extraction freeze. Behavior outside
the declared source scope must not be recorded as M0--M4 extraction progress.

Milestone completion is ordered: M1 requires M0, M2 requires M1, and M3 requires M2. M2 `edge_ids` must
equal every material edge incident to the selected capabilities within their declared target-path scope;
an empty list is valid only when that derived set is empty. M3 `partition_ids` must equal the complete
declared coverage denominator. A `terminally_classified` target path blocks M4; it is not a passed reassembly.
If source evidence establishes that a path itself cannot execute to its declared terminal result, record its
anchors, exact defect, scientific role, and recoverable subrelations as a non-candidate disposition. An explicit
source-derived scope revision may then remove only that path from the executable target denominator while keeping
it visible in the source census and disposition record. Rebind the manifest, matrix, source scope digest, and fresh
`1.0` snapshot before recomputing M0--M4. Missing dependencies, incomplete extraction, difficult numerics, and
missing tests are not evidence that a source path is non-executable. Every remaining executable core path still
requires canonical and independently sealed-holdout reassembly against the exact frozen bundle.

Schema `1.0` is the sole progress contract. It carries a validator-derived milestone projection and
source-backed target-path reassembly evidence. Superseded meanings and temporary version labels must be
overwritten rather than retained as alternate audit formats. Milestone status is one of
`pending`, `in_progress`, `completed`, or `blocked`; the validator derives it from the referenced target,
capability, edge, partition, and progress records rather than trusting prose or a hand-written percentage.
`1.0` is a stable contract identifier, not an evolution counter. When the extraction standard becomes
stricter, update this `1.0` definition, validator, fixtures, and current run snapshots in place; never
introduce a higher schema label or a compatibility branch for the superseded meaning.

## 5. External progress snapshot

During a long run, write `capability_progress.json` under the project evidence/checkpoint tree, never under
`operators/` or `task_graphs/`. It is a derived current-state projection; `extraction_ledger.md` remains
the append-only semantic event record.

Minimum shape:

```json
{
  "schema_version": "1.0",
  "snapshot_id": "checkpoint-or-freeze-id",
  "scope": {
    "scope_id": "declared-source-and-target-scope",
    "census_status": "provisional",
    "scope_manifest_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "capability_evidence_matrix_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "ledger_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "bundle_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "source_partitions_mapped": 2,
    "source_partitions_total": 3,
    "target_paths_traced": 1,
    "target_paths_total": 1
  },
  "source_partitions": [
    {
      "partition_id": "S-SCIENCE",
      "material_role": "scientific_source",
      "status": "mapped",
      "evidence_refs": ["manifest:science"]
    },
    {
      "partition_id": "S-SUPPORT",
      "material_role": "support_runtime",
      "status": "mapped",
      "evidence_refs": ["manifest:support"]
    },
    {
      "partition_id": "S-UNTRACED",
      "material_role": "scientific_source",
      "status": "unmapped",
      "evidence_refs": ["manifest:untraced-family"]
    }
  ],
  "equation_anchors": [
    {
      "equation_id": "EQ-EQUILIBRIUM",
      "equation_role": "governing_equation",
      "target_paths": ["T-EQUILIBRIUM"],
      "authority_refs": ["source:eq_solve"]
    }
  ],
  "work_units": [
    {
      "capability_id": "C-EQUILIBRIUM",
      "anchor_kind": "governing_equation",
      "node_role": "task_graph_subweb",
      "equation_anchor_ids": ["EQ-EQUILIBRIUM"],
      "participating_node_ids": ["C-RESIDUAL", "C-UPDATE"],
      "participating_edge_ids": ["E-RESIDUAL-TO-UPDATE"],
      "priority": "P0_primary_solution",
      "disposition": "in_progress",
      "required_for": ["T-EQUILIBRIUM"],
      "gates": {
        "mapped": "passed",
        "contract": "passed",
        "implemented": "pending",
        "source_free": "pending",
        "independent_validation": "pending"
      },
      "blocker": {
        "classification": "extraction_gap",
        "reason": "named producer is not emitted",
        "next_action": "capture the producer call boundary",
        "owner": "scientific-runtime-dataset-construction"
      }
    },
    {
      "capability_id": "C-RESIDUAL",
      "anchor_kind": "governing_equation",
      "node_role": "operator_node",
      "equation_anchor_ids": ["EQ-EQUILIBRIUM"],
      "priority": "P1_required_closure",
      "disposition": "in_progress",
      "required_for": ["T-EQUILIBRIUM"],
      "gates": {
        "mapped": "passed",
        "contract": "pending",
        "implemented": "pending",
        "source_free": "pending",
        "independent_validation": "pending"
      },
      "blocker": {
        "classification": "extraction_gap",
        "reason": "residual port contract is incomplete",
        "next_action": "finish the residual node contract",
        "owner": "scientific-computation-asset-extraction"
      }
    },
    {
      "capability_id": "C-UPDATE",
      "anchor_kind": "numerical_state_transition",
      "node_role": "operator_node",
      "equation_anchor_ids": ["EQ-EQUILIBRIUM"],
      "priority": "P1_required_closure",
      "disposition": "pending",
      "required_for": ["T-EQUILIBRIUM"],
      "gates": {
        "mapped": "passed",
        "contract": "pending",
        "implemented": "pending",
        "source_free": "pending",
        "independent_validation": "pending"
      },
      "blocker": {
        "classification": "extraction_gap",
        "reason": "update mapping is not emitted",
        "next_action": "extract the bounded update mapping",
        "owner": "scientific-computation-asset-extraction"
      }
    }
  ],
  "web_edges": [
    {
      "edge_id": "E-RESIDUAL-TO-UPDATE",
      "from_node_id": "C-RESIDUAL",
      "from_port": "residual",
      "to_node_id": "C-UPDATE",
      "to_port": "residual",
      "edge_role": "port_binding",
      "required_for": ["T-EQUILIBRIUM"],
      "closure_status": "pending",
      "blocker": {
        "classification": "ai_completable_glue",
        "reason": "residual-to-update port binding is not emitted",
        "next_action": "implement and validate the bounded port adapter",
        "owner": "scientific-computation-asset-extraction"
      }
    }
  ],
  "coverage_partitions": [
    {
      "partition_id": "B-PRIMARY",
      "required_for": ["T-EQUILIBRIUM"],
      "status": "pending"
    }
  ],
  "target_paths": [
    {
      "target_id": "T-EQUILIBRIUM",
      "trace_status": "traced",
      "evidence_refs": ["target:equilibrium-contract"],
      "required_capabilities": ["C-EQUILIBRIUM", "C-RESIDUAL", "C-UPDATE"],
      "status": "partial",
      "earliest_unresolved": "C-RESIDUAL"
    }
  ],
  "active_frontier": [
    {
      "target_id": "T-EQUILIBRIUM",
      "capability_or_edge": "C-RESIDUAL",
      "classification": "extraction_gap",
      "reason": "residual port contract is incomplete",
      "next_action": "finish the residual node contract",
      "owner": "scientific-computation-asset-extraction"
    }
  ],
  "closure_signal": {
    "kind": "active",
    "claim_ceiling": "lower-bound checkpoint only",
    "next_action": "finish the residual node contract",
    "reopen_condition": "the next source probe or contract revision",
    "owner": "scientific-computation-asset-extraction",
    "evidence_refs": ["evidence:checkpoint-001"],
    "delivered_target_ids": [],
    "unresolved_ids": ["C-RESIDUAL"]
  },
  "milestones": {
    "M0_equation_census": {"status": "in_progress"},
    "M1_minimal_golden_path": {
      "status": "in_progress",
      "target_ids": ["T-EQUILIBRIUM"]
    },
    "M2_replaceable_scientific_slices": {
      "status": "in_progress",
      "capability_ids": ["C-RESIDUAL", "C-UPDATE"],
      "edge_ids": ["E-RESIDUAL-TO-UPDATE"]
    },
    "M3_branch_lifecycle_expansion": {
      "status": "in_progress",
      "partition_ids": ["B-PRIMARY"]
    },
    "M4_extraction_freeze": {"status": "pending"}
  },
  "progress": {
    "census_maturity": 0.6666666666666666,
    "extraction_resolution": 0.0,
    "usable_core_closure": 0.0,
    "composition_edge_closure": 0.0,
    "branch_domain_coverage": 0.0,
    "target_path_reassembly": 0.0,
    "overall": null
  }
}
```

When a target path becomes `passed` in schema `1.0`, replace `earliest_unresolved` with `null` and add
`reassembly_evidence`. It binds the source scope and bundle digest, names the executable graph or justified
terminal operator, declares every compared terminal physical output, and records both `canonical` and
`sealed_holdout` cases. Each case carries separate source and bundle input digests, which must be identical,
plus the source oracle, bundle execution, comparison receipt, and tolerance-contract references. A source
oracle may be a bounded source runtime, an authoritative source fixture, or a source-derived reference whose
derivation is itself retained as evidence. Internal package tests or captured intermediate state are not a
substitute for this record.
Every evidence reference carries its SHA-256 digest. Current validation resolves these files relative to the
authoritative run root and rejects missing, escaping, symlinked, or digest-mismatched evidence. Existing
`scirel.extraction-reassembly-comparison.v1` receipts remain historical or working evidence; a current
`bounded_delivery` or `full_freeze` claim uses `scirel.extraction-reassembly-comparison.v2`. The `.v2` JSON
repeats the target, case kind, source-scope digest, bundle digest, identical input digests, tolerance-contract
digest, ordered terminal-output IDs, and one comparison record per output. Each record names the metric and
its finite, non-negative observed and allowed quantities, with the actual comparison passing. It repeats the
same `bundle_execution_ref` and SHA-256 as the case and binds a run-relative
`bundle_execution_receipt_ref` with its SHA-256 digest; that execution receipt must report integer
`exit_code=0`.

Choose the metric from the output and tolerance semantics: use a defined `mismatch_count` for discrete or
Boolean outputs; use a scalar maximum absolute or relative error only when that scalar tolerance applies
uniformly; for mixed per-element tolerances, use a genuine `max_normalized_error` or retain the individual
element comparisons. `max_error <= max_tol` does not prove a mixed-tolerance pass. The independent reviewer
checks the metric against the retained raw outputs, elementwise tolerance contract, and complete source-derived
terminal-output denominator. The deterministic `.v2` checks reject internally inconsistent pass claims but
cannot establish those scientific facts or an appropriate tolerance by themselves.

When the original source and candidate execution, explicit inputs, per-output results, tolerances, and bound
source/bundle digests are retained and unchanged, derive a `.v2` receipt from that evidence without rerunning
the physics solely because the receipt shape changed. Record the derivation and new digest; do not infer missing
raw values, independence, or a passing comparison from a `.v1` status flag alone. If the retained data cannot
support the required metric or execution binding, leave the affected gate open and rerun only the necessary
slice with a fresh attempt.

The identical-input requirement is within each case: source and candidate receive the same explicit inputs.
Canonical and sealed-holdout evidence must remain independently prepared and sealed from candidate tuning.
When a candidate-aware coordinator has already seen comparison results, a hash written before the next probe
proves only that the case was fixed for that probe. To establish independence for a new variable-input case,
use a source-only author or a source-derived selection rule insulated from candidate code, digests, prior results,
known failing branches, and target-output hints that could steer the choice. Give the author the source's
admissible input domain without those candidate-specific cues. Retain the exact case bytes, selection rationale,
and a commitment made before that case's source/candidate comparison or tolerance/harness adjustment. After the
author exits, seal an independently owned copy that the author cannot rewrite; verify its digest and chronology
before candidate-aware reassembly. If choosing from several sealed cases after seeing candidate results,
predeclare the selection rule or compare the whole sealed set rather than selecting a convenient pass.
An independently fixed case or source-derived reference established before candidate feedback need not use a
separate author when its origin and immutable seal are verifiable. If the runtime cannot isolate case authoring
or seal its output, leave independence open while continuing other source-led work.
If the source exposes only one fixed admissible input, do not invent a tunable parameter or label an identical
rerun as a new holdout case. A separately established, source-derived reference or independent observation may
support a holdout for that fixed domain only when its origin, sealing, and distinct evidentiary role are recorded;
otherwise keep the holdout gate open as `validation_oracle_gap`. This does not extend the claim to other inputs.

Use only the canonical gap labels for `classification`. For every non-passed target path, record exactly
one earliest unresolved capability or edge with reason, next action, and owner. This answers “why is the
run not finished?” without replaying the entire ledger. The frontier ID must resolve to a capability or
edge required by that same target path. Declare at least one coverage partition (use an explicit base
partition when no material alternate branch exists); an empty branch denominator is not 100% coverage.

## 6. Derived progress rules

Run:

```text
python scripts/validate_capability_progress.py <capability_progress.json> \
  --scope-manifest <frozen-scope-manifest> \
  --capability-evidence-matrix <capability-evidence-matrix> \
  --ledger <extraction-ledger> \
  --bundle-root <formal-bundle-root>
```

For a current snapshot that is intended to close a work turn or hand off a user-facing bounded
slice, add `--require-closure-signal`.

The CLI rejects progress files above 10 MiB; progress is a compact evidence index, not an array store.
It recomputes the three supplied file hashes and the canonical bundle-tree digest. The bundle digest is
`sha256(sorted(relative_posix_path + tab + file_sha256 + newline))`, excluding cache directories. Calling
`validate_progress_document(...)` directly checks only schema and derived values; it is useful for draft
tests but is not the complete binding gate.

The validator first checks the four SHA-256 bindings, enumerated source-partition identities, target-path
identities, and all cross-references. The numeric source/target totals and mapped/traced counts must equal
the array-derived counts; they cannot define their own denominator. It then recomputes:

- `census_maturity`: the minimum of mapped source partitions and traced target paths;
- `extraction_resolution`: emitted or terminally classified work units divided by all discovered units;
- `usable_core_closure`: emitted P0/P1 units with every gate passed divided by all P0/P1 units;
- `composition_edge_closure`: proved web edges divided by all declared web edges (an edge-free single-node target is not penalized);
- `branch_domain_coverage`: proved material partitions divided by all declared partitions;
- `target_path_reassembly`: passed target paths divided by all declared target paths.

When the census is provisional, `overall` must be `null`: the vector is a lower-bound checkpoint, not a
percentage of an unknown whole. When the census is frozen and fully mapped, `overall` is the minimum of
the six ratios. This conservative number cannot be increased by adding easy packages or terminal gap
records.

A terminal classification contributes to extraction resolution because the source fact has been handled,
but it never contributes to usable core closure, branch proof, or target-path reassembly.

## 7. Closure signals and finite stopping conditions

Every current snapshot should carry a `closure_signal`, and final/current validation should run with
`--require-closure-signal`. The signal is a stopping/status contract, not a replacement for the
M0--M4 milestone projection or the conservative progress vector:

| Kind | Meaning | Required evidence and next action |
| --- | --- | --- |
| `active` | work remains actionable in the current scope | non-empty `active_frontier`, named owner and next action |
| `bounded_delivery` | an independent subagent has reviewed a finite, source-backed delivery slice under an explicit claim ceiling; remaining scope is not silently included | non-empty `delivered_target_ids`; digest-bound bounded-delivery review receipt with `verdict=pass`; reviewed targets and canonical/sealed-holdout evidence; unresolved IDs or an explicit empty remainder; and a reopen condition |
| `blocked_external` | no safe action remains under the current snapshot | non-empty frontier, named external/human/source dependency, and exact reopen condition |
| `full_freeze` | the declared scope is fully extracted | frozen census, `progress.overall=1.0`, completed M4, empty frontier, and a fixed-sandbox-validated root `asset_entry.py` |

Use `bounded_delivery` when a useful source-free slice can be handed to users without pretending that
the project is complete. A separate read-only subagent must review the source-derived census, selected bundle,
reassembly evidence, and deferred register and issue the pass receipt. It is not valid to place the missing science
only in `extraction_report.md`: the delivered target must execute from the bundle and pass the same reassembly
contract used by `full_freeze`. The review receipt must list the closure signal's evidence references and the
source-oracle, bundle-execution, comparison, and tolerance references for every delivered case. Its
`claim_ceiling` and `reopen_condition` must match the closure signal.
Use `blocked_external` when the remaining work cannot advance until a source
revision, external producer, missing schema, or human decision arrives. A task may stop at either
signal; it must not continue indefinitely with an unqualified “still working” status. The signal must
state the claim ceiling and the exact condition that reopens work.

`closure_signal.kind` is the authoritative current extraction state. If a snapshot also
contains `state`, it must equal the signal kind (or be `reopened` while the signal is
`active`) and carry a new `state_digest`; a reopened snapshot records
`reopened_from_digest`. The deterministic progress validator, rather than a model or
worker, derives eligibility for `full_freeze`. The project intake gate must also resolve
every machine-readable `task_graphs/...` and `operators/...` asset reference and reject
nested TaskGraph cycles; package-local tests do not establish this cross-package closure.
External binding validation rejects a `full_freeze` bundle without a regular, non-symlinked
root `asset_entry.py`. Before freezing, execute `scripts/validate_asset_entry.py` in the fixed
source-free asset sandbox with the expected operator and TaskGraph counts. Bind its JSON execution receipt
under `closure_signal.asset_entry_validation` by run-relative path and SHA-256. The receipt records
`validator=validate_asset_entry.py`, `sandbox=CODEFUSION_ASSET_SANDBOX=1`, integer `exit_code=0`, the exact
`asset_entry_sha256`, `bundle_digest`, `operators`, and `task_graphs`. This final-delivery gate does not
require an entry from ordinary active or incomplete snapshots.

Deterministic validation is intentionally incomplete. It protects stable structural invariants and binds evidence;
it does not attempt to encode an exhaustive scientific understanding of every source language or implementation
shortcut. For `bounded_delivery`, an independent subagent owns the semantic exit review. The same delegation pattern
may be used for non-enumerable checks during `full_freeze`, alongside its unchanged deterministic gates. Record the
review as evidence, but do not treat a subagent verdict as expert approval or release.

Use the shared [stage boundary contract](stage_boundary_contract.md) for structured
`boundary_event` records. Provider/worker failures and validator defects are recoverable
operational events; reserve `blocked_external` for a named dependency with an exact reopen
condition and continue independent frontier work.

## 8. Update and reporting rules

Generate a fresh snapshot whenever any of these changes:

- the source/evidence universe or declared target scope;
- a capability identity, priority, projection, or disposition;
- a material branch/domain partition;
- a target path's earliest unresolved edge;
- an implementation, source-free, independent-validation, or reassembly gate.

Do not edit an older snapshot in place; create a new snapshot identity and retain the old one as evidence.
The executive report cites the latest validated snapshot and repeats only its vector and active frontier.
Historical completion claims remain in the event ledger and may not override the current snapshot.
Keep a current root report during extraction, then reconcile it with the validated final snapshot before a
`full_freeze` claim. Process notes or private drafts can change for resumption without rebinding scientific
evidence; a changed cited claim, source scope, candidate revision, or consumed evidence requires the relevant
new snapshot and affected-slice revalidation.

Package/file/test totals remain freeze diagnostics. They are never the numerator or denominator of
scientific extraction progress.
