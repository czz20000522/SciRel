# Framework-to-Asset Projection Decision Manual

Use this manual after Level 1 node/edge production and before emitting operator or task-graph packages. A framework node is an analysis boundary, not a package-type declaration.

## Contents

- Scientific relation and boundary meaning
- Projection types
- Operator identity
- Task-graph necessity gate
- Parallel diagnostic and nested-graph decisions
- Ruling record and deterministic order
- Boundary reproducibility and ownership

## Scientific relation and boundary meaning

A scientific relation describes evidenced equations, constraints, closures, diagnostic definitions or state
evolution. It can be implicit, coupled, differential or integral; it is not an executable function. An operator
implements a complete directed scientific mapping under explicit assumptions and numerical conventions.
TaskGraph dependencies, ordering and feedback express how such computations compose, not a synonym for the
underlying physical relation. For example, `V = I R` is a relation; `(V, R) -> I` is one direction with its own domain.

There is no unique, context-free "minimal scientific relation" partition. Choose an independently meaningful
computational boundary relative to the declared source scope and required recomposition:

- Name the scientific result or state change and make its inputs, assumptions, units and numerical meaning explicit.
- Identify source-backed independent consumption, replacement or composition value and a meaningful validation
  boundary. Merely being callable or unit-testable as a helper is insufficient.
- Preserve internal subcomputations with those independent contracts when they need separate delivery; represent
  required coordination as a TaskGraph. Do not hide them merely to reduce package count.
- Stop splitting when only algebraic fragments, array plumbing or iteration mechanics would remain without an
  independent scientific contract. Equation count, code length, return-field count and source routine boundaries
  cannot determine this decision.

A primary result may be a vector, tensor, coupled state or structured result with companion diagnostics.
For example, one flux-to-field mapping may return `B_R, B_Z` and field magnitude; this does not require three
operators. A source-specific assembly may return matrix and RHS together under one discretization contract.
Conversely, unrelated diagnostic moments are not one operator merely because a function returns them together.
A named source-backed rate may be one line and still qualify. An elliptic-function call inside a field kernel
does not become an operator solely because it has an input/output signature.

If multiple partitions preserve the same science and required recomposition, keep the existing coherent boundary
and record a short rationale in code or the current task record. Do not wait for a globally smallest partition
or rerun science for a naming/packaging preference. Unresolved physical meaning, omitted computation or unverified
source parity remains substantive. These are decision criteria, not a new required document or numeric gate.

## Projection types

Assign exactly one initial projection to each Level 1 node:

- `single_operator`
- `operator_family`
- `scientific_task_graph`
- `nested_task_graph`
- `assembly_recipe`
- `support_only`
- `terminal_gap`

One framework node may project to several assets. One reusable asset may serve several framework nodes. Record both directions in the ledger.

## Step 1: Identify operator identities

Build a normalized identity for each independently meaningful direction:

```text
scientific_relation_family
implemented_direction
primary_scientific_output
physical_domain_and_axes
model_or_branch
boundary_policy
normalization_and_sign_convention
```

Emit separate operator candidates when identities differ and each has a complete independent scientific contract,
composition/replacement value and meaningful validation. Merge implementation substeps of one identity when they
produce one coherent scientific result and expose no independently meaningful intermediate contract.

Default rules:

- distinct independently meaningful result contracts or relation directions -> separate operators;
- components of one vector/coupled result, companion diagnostics, or branches of one piecewise relation -> not separate merely by field/branch count;
- implementation-only substeps of one mapping -> one operator;
- same identity with alternate source implementations -> one candidate identity plus implementation/convention evidence, not duplicate operators;
- no scientific identity -> support/glue/reject, not an operator.

## Step 2: Apply the task-graph necessity gate

First identify multiple independently meaningful computation contracts. Internal evaluation order, a numerical
recurrence or a loop inside one complete operator is not by itself a TaskGraph.

Emit a scientific task graph only when a composite relation requires at least one evidenced non-interchangeable coordination rule:

- producer-to-consumer state handoff;
- non-commutative normalization, reduction, or boundary transform;
- branch/selector that changes the downstream model;
- sequential state feedback or time-step ownership;
- convergence/failure gate;
- shared-state ownership transfer;
- required fan-out/fan-in with a source-backed join contract;
- same-snapshot consistency whose violation changes scientific meaning.

Do not emit a scientific task graph solely because:

- the source calls routines in one lexical order;
- the routines belong to one module or one PFM node;
- several independent operators share an input;
- parallel results are bundled for convenience;
- a wrapper gives one entrypoint;
- the graph parses or validates golden outputs.

If independently invocable nodes can run in arbitrary order without changing scientific meaning, retain independent operators and represent convenience composition as `assembly_recipe` or an outbound demand graph, not a formal scientific task graph.

## Parallel diagnostic decision

For independent diagnostics consuming the same state:

```text
same input + independent outputs + no required join
    -> operator_family

frozen state snapshot + shared axes/normalization + atomic join contract
    -> scientific_task_graph with fan-out/fan-in
```

The PFM grouping alone never decides this result. A graph claiming snapshot consistency must test mismatched snapshot, axis, or normalization rejection.

## Step 3: Choose nested versus flat composition

Use `nested_task_graph` when a child composite has its own stable black-box contract and oracle and the parent owns a separate required relation. Preserve children as reusable assets. Flatten only when the child has no independent contract or the nesting is merely lexical source structure.

## Step 4: Record the ruling

For every emitted task graph, record:

```text
non_interchangeable_relation
required_nodes_and_ports
ordering_or_coordination_consequence
source_evidence
test_that_fails_on_drift
```

For every operator merge/split, record:

```text
normalized_identity
independent_output_or_intermediate
reuse_boundary
oracle_boundary
merge_or_split_reason
```

## Deterministic decision order

All producers must apply this order:

1. identify primary state and target relation;
2. count normalized scientific relation directions inside the framework node;
3. split distinct independently reusable/verifiable operator identities;
4. merge implementation-only fragments of one identity;
5. test the remaining composition for non-interchangeable coordination;
6. emit a task graph only if the necessity gate passes;
7. otherwise retain operators and use `operator_family` or `assembly_recipe`;
8. record `needs_domain_ruling` when evidence cannot decide scientific identity or coordination semantics,
   not merely because more than one equivalent packaging is possible. The coordinator investigates the scientific
   question; this label does not itself require a human checkpoint.

Default under unresolved scientific ambiguity: do not invent a task graph and do not merge distinct independent
scientific contracts into one operator. This does not require splitting components of one coherent result.

## Boundary reproducibility

When an operator/TaskGraph boundary remains ambiguous and an independent context is available, apply the same
frozen evidence and decision rules again. Compare scientific facts, not labels or layout:

- Level 0 target relations and mechanism nodes;
- Level 1 node identities, roles, ports, and high-value edges;
- operator identity keys and merge/split rulings;
- task-graph necessity rulings and required relations;
- gap classifications and uncovered-source declarations.

Record disagreements as unresolved boundary evidence. The coordinator resolves the extraction ruling from the
contract and source evidence; worker majority is not a scientific argument.

## Ownership boundary

- The caller defines the target scope and any supplied domain ruling.
- The coordinator owns extraction boundaries, evidence integration, and the final bundle claim.
- Workers own only the read or write scope assigned in their packets and cannot declare project completion.
