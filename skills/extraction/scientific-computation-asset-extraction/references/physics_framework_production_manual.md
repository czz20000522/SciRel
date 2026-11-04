# Level 0 Physics Framework Production Manual

Use this manual to produce the expert-facing physics view. This is a production procedure, not only an acceptance checklist. Do not derive Level 0 nodes from folders, files, routines, or lexical call order.

Level 0 preserves the whole project's physical process: primary-state production and change, data flow,
solve/update responsibilities, and terminal diagnostics. It is not the operator inventory. The
equation-centered scientific capability web separately expands from governing equations into reusable
scientific nodes and glue edges. The two views must agree on physical dependencies, but Level 0 may fold
many operator nodes and local task-graph subwebs into one readable project-scale mechanism.

## Inputs

Use the same frozen evidence set for every producer:

- declared project purpose and principal solved/advanced/reconstructed state;
- algorithm/model documentation, papers, and manuals;
- public scientific inputs and outputs;
- documented standard cases and diagnostics;
- source-visible physical module names only as supporting evidence.

Record missing or conflicting evidence before drawing the graph.

## Production sequence

1. **Name the primary state.** Record what is solved, advanced, constrained, reconstructed, or diagnosed; include axes and time dependence when known.
2. **Name the target relations.** List the governing balance, residual, transition, objective, inversion, or diagnostic relations that define project success.
3. **List direct state-changing mechanisms.** Include sources, sinks, transport, collisions, fields, waves, reactions, losses, boundary effects, and feedback only when evidenced.
4. **List required scientific state producers.** Include geometry, equilibrium, mesh, species state, closures, coefficients, or external physical state only when a target relation consumes them.
5. **List solver/update responsibilities.** Separate assembly, state advancement, constraint enforcement, convergence, and conservation when they have different scientific roles.
6. **List observer responsibilities.** Diagnostics and public reductions may read state but must not be shown as modifying it unless source evidence proves feedback.
7. **Create edges from physical dependency.** Draw `produced scientific state -> consuming mechanism/update/diagnostic`; never use call order alone.
8. **Normalize names and order.** Name nodes by scientific role or state transformation, then order them as state producers, state-changing terms, assembly/solve/update, diagnostics.
9. **Reconcile with the equation-centered web.** For each Level 0 target relation, identify the central equation anchor and required local subwebs. Record any Level 0 mechanism that has no traced scientific nodes, or any discovered node that has no Level 0 target-path role, as a coverage conflict rather than silently changing either view.

## Node extraction eligibility and stopping rules

Admit a Level 0 node only when it does at least one of the following:

- changes the primary scientific state;
- produces an indispensable scientific state for a target relation;
- performs a distinct solve, closure, constraint, or state transition;
- produces a declared principal diagnostic or scientific output.

Stop splitting when a node can be named as one stable physical mechanism, scientific state producer, solve/update responsibility, or diagnostic family. Continue splitting when one node mixes different primary outputs, different model choices, different state ownership, or independently replaceable scientific responsibilities.

Exclude IO, serialization, logging, plotting, build/runtime setup, generic numerical libraries, validation harnesses, and default case initialization unless they encode source-specific scientific semantics.

## Canonical Level 0 record

Produce one record per node:

```text
node_key
scientific_role
primary_state_read
primary_state_written
target_relation
principal_outputs
assumptions_or_model_branch
evidence_refs
```

Produce one record per edge:

```text
from_node.output -> to_node.input
physical_dependency
required_model_or_state
evidence_refs
```

`node_key` must be derived from the scientific role and primary output, not a source symbol. Presentation labels may vary; normalized keys may not.

## Deterministic tie-breakers

When two decompositions are plausible, apply this order:

1. preserve distinct target relations;
2. preserve distinct state ownership or model branches;
3. preserve independently replaceable scientific responsibilities;
4. merge implementation-only substeps;
5. mark unresolved physical ambiguity as `needs_domain_ruling` rather than guessing.

## Acceptance condition

Two Level 0 graphs are equivalent when their normalized primary state, target relations, node keys, state-changing mechanisms, required producers, diagnostic families, and physical dependencies agree. Labels, layout, visual grouping, and the number of operator leaves folded into a Level 0 mechanism may differ when the equation-centered web preserves those leaf identities.
