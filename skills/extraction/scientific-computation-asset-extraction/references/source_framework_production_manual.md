# Level 1 Source-Anchored Framework Production Manual

Use this manual to produce the extraction-facing framework map. Level 1 is derived from source evidence and Level 0; it is not a call graph, file inventory, or hand-written architecture sketch.

Level 1 explains where the equation-centered web's scientific nodes and glue edges live in source and
state flow. It does not replace the readable Level 0 process or define nodes merely from routines. Every
scientific leaf remains an operator candidate; a task graph is a local subweb of named nodes and edges,
while Level 1 supplies their source anchors, ports, hidden state, branch guards, and lifecycle evidence.

## Contents

- Required normalized evidence
- Production sequence
- Split and merge rules
- Allowed Level 1 roles
- Canonical node and edge records
- Deterministic ordering, ambiguity, and acceptance

## Required normalized evidence

Reuse existing source indexes, code/YAML and scientific records for these facts; the names below are information
roles, not a requirement for one new file or table per role. Supplement only missing facts. A final human-readable
map is a projection produced at handoff, not an extra document to rewrite during every implementation iteration.

Freeze one evidence package before comparing or combining AI results:

```text
source_manifest
material_role_inventory
entry_points
symbol_inventory
call_graph_or_search_fallback
state_read_write_table
public_input_output_inventory
tests_examples_and_standard_cases
runtime_trace_inventory
level_0_node_records
equation_anchor_and_capability_web_records
coverage_and_conflict_log
```

Different evidence packages are different extraction runs and must not be used to measure AI consistency.

## Production sequence

1. **Freeze the universe.** Partition primary source, shared kernels, third-party dependencies, tests/examples, obsolete variants, UI/IO shells, and external programs.
2. **Locate authoritative targets.** Identify public outputs, primary state updates, solver/assembly sites, documented diagnostics, and standard-case terminal signals.
3. **Run a backward target slice.** Trace each target to its state producers, physical terms, closures, geometry, boundary rules, and configuration selectors.
4. **Run a forward input slice.** Trace case/config inputs through state projection, scientific producers, consumers, state updates, and diagnostics.
5. **Intersect and reconcile slices.** High-value nodes lie on a target path; side branches require an explicit secondary target, reusable relation, or terminal classification.
6. **Cluster by scientific/state identity.** Cluster symbols by primary scientific output, state read/write ownership, physical mechanism, invocation cycle, boundary/normalization convention, downstream consumer, and oracle.
7. **Apply split and merge rules.** Do not use files, modules, or subroutines as default boundaries.
8. **Reconcile scientific identity.** Bind every equation anchor and scientific node to source/state evidence and every glue edge to its source port movement. Promote an apparent edge to a node whenever it computes interpolation, boundary synthesis, closure, discretization, scientific normalization, or a state update.
9. **Emit normalized node records.** Assign one allowed node role and one asset-projection status. A task-graph candidate denotes a required local subweb, not an indivisible scientific leaf; retain its participating node and edge identities.
10. **Emit state/port edges.** Create edges only from evidenced data/state movement; attach shape, axes, units, sign, normalization, index base, branch selector, and hidden state.
11. **Project a map when needed.** At handoff, derive a diagram from existing records if it helps its reader. A drawing is not the sole source of scientific truth and is not a D1 formatting gate.
12. **Record coverage and ambiguity.** Uncovered source families, unbound web nodes/edges, and unresolved split decisions remain visible; do not force a green completeness result.

## Split rules

Split a cluster when any condition holds:

- it produces different primary scientific outputs or relation directions;
- it owns independent state transitions or feedback boundaries;
- it implements different physical models, branches, boundary policies, units, signs, or normalization conventions;
- it has an independently callable port contract, consumer, replacement boundary, or oracle;
- its output fans out to multiple scientific consumers and has stable meaning outside the current caller.

## Merge rules

Merge implementation fragments when all material conditions hold:

- they implement one scientific relation and one primary output;
- intermediates have no independent scientific consumer or oracle;
- separation would expose only array plumbing, iteration mechanics, or storage layout;
- they share state ownership, branch policy, boundary convention, and validation boundary.

Do not merge merely because symbols are in one module. Do not split merely because they are separate routines.

## Allowed Level 1 roles

Use only:

- `operator_candidate`
- `nested_task_graph_candidate`
- `state_or_schema_producer`
- `io_or_config_action`
- `support_kernel`
- `validation_only`
- `blocked_gap`
- `terminal_non_emitted`

## Canonical node record

```text
node_key
level_0_parent
role
scientific_relation
primary_output
visible_inputs
visible_outputs
hidden_state_read
hidden_state_written
configuration_and_branch_selectors
source_anchors
downstream_consumers
oracle_or_validation_boundary
asset_projection
ambiguity_status
```

Canonical edge records use:

```text
from_node.output -> to_node.input
shape_axes_units
sign_normalization_index_policy
branch_or_schedule_condition
hidden_state_or_schema_needed
closure_status
source_anchors
```

## Deterministic ordering and ambiguity

Order nodes by Level 0 parent, target-relation priority, primary output, then normalized `node_key`. Apply split rules before merge rules. When evidence supports more than one scientific boundary after tie-breaking, emit `needs_domain_ruling` with both bounded alternatives and the evidence that would decide them.

## Fallbacks and scale

When AST/call/state tooling fails, use systematic source search plus runtime traces and record coverage. For very large projects, slice from target relations first and move dense hidden state into `state_flow_map.md`; never flatten every symbol into Level 1.

## Acceptance condition

Two Level 1 maps are equivalent when normalized equation bindings, node identities, local task-graph subweb membership, roles, primary ports, high-value edge contracts, asset projections, terminal gaps, and uncovered-source declarations agree. Source-symbol grouping and diagram layout may differ when they preserve the same normalized contracts.
