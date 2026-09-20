# Shared Asset Contract

This is the canonical cross-skill boundary for scientific asset extraction, scientific-relation implementation, review, and paper-lead work. Other skills should reference it instead of restating these rules.

## Composition layers

- `program_framework_map`: owns project-wide node boundaries and cross-node scientific/state dependencies.
- `scientific_task_graph`: owns one executable framework slice and may nest operators or task graphs from the same framework node.
- `scientific_operator`: owns one reusable directed scientific or numerical mapping.

A whole user goal, work plan, or outbound run is not a scientific operator graph. `TaskGraph(T) ⊆ FrameworkNode(N)`: a task graph must not nest a task graph whose `primary_pfm_node` differs. Cross-node dependencies, including non-interchangeable handoffs, belong to `program_framework_map` edges and explicit producer/consumer ports; retain each node-scoped task graph as an independently callable asset.

The framework map does not execute or inject values. Every operator and task graph is a
self-contained callable contract: callers compose outputs into downstream inputs and provide
all other declared values. Do not use a framework edge, source common block, source file
layout, lexical call order, final output, or array shape as an implicit input channel. Declare
each required value's schema, units, axes, index base, selector/provenance, and RNG state where
applicable; return the produced values needed for subsequent composition.

## Multi-project dependencies

A target bundle must never require another uploaded project, its source directory, or its asset
bundle at runtime. A foreign project is evidence for a dependency contract, not an implicit
runtime dependency.

- If the foreign result is static/exogenous for the target run, declare that result as an explicit
  target input with its value schema, units, axes/indexing, provenance, initialization and timing.
- If the target consumes a new foreign state each target step, extract the smallest transitive
  foreign producer/projection slice and vendor it source-free into the target bundle. Package
  every scientific mapping in that bridge as a testable operator or a same-framework-node task
  graph; `graph.py` may schedule it but may not hide its formulas or numerical updates.
- Preserve the foreign source/version provenance, state ownership, initial state, step ordering,
  selectors and RNG/scheduler semantics. Validate dynamic bridges against a coupled source trace
  or independent equation/invariant evidence. A bridge spanning multiple foreign framework nodes
  remains visible as explicit target framework-map boundaries; it cannot justify an oversized
  target task graph.

## Canonical gap kinds

- `extraction_gap`: missing core scientific or source-specific numerical behavior.
- `configuration_or_schema_need`: missing values, shapes, axes, field mappings, units, variant selectors, or initialization schema.
- `ai_completable_glue`: missing generic parsing, conversion, dispatch, scheduling, error handling, or adapter code.
- `validation_oracle_gap`: missing source/intermediate run, fixture provenance, or numerical oracle.
- `cannot_complete`: evidence is too damaged or incomplete without inventing science, data, or authority.

Older labels such as `implementation_gap`, `operatorization_gap`, `graph_node_gap`, and `closure_data_gap` are technical subtypes only.

## Evidence boundary

Use these validation tiers consistently:

1. direct source parity;
2. compiled/source-derived intermediate fixture;
3. equation or standard-library oracle;
4. invariant/conservation/boundary check;
5. boundary-only probe;
6. blocker or unexecuted validation plan.

A validation plan is not executed evidence. Source probes, golden parsers, random-history replay, and harnesses remain outside formal asset packages.

Edge probes used to discover or close a missing framework state/port transform are extraction evidence. Later parity strengthening, replay, and oracle expansion are validation work unless they reveal an unprocessed scientific mapping.

## Runtime and packaging boundary

Keep two runtimes distinct:

- `source_runtime`: one project-specific Docker environment for running that project's original source and source probes. Project A and project B must have separate source runtimes; never reuse one project's source runtime as another project's asset runtime, and never mount it into outbound bundle validation.
- `asset_runtime`: the fixed, cross-project Docker image used to load and test extracted operators/task graphs. It is a reusable platform asset for A, B, and later projects; use it with a read-only bundle and no source mount. If a bundle carries Docker metadata under `docker/<project>/`, that metadata describes `asset_runtime`, not the project's source runtime.

The formal deliverable is a source-free asset bundle, not a polished library or public API. It must be loadable by path/lightweight entrypoint, bind declared configuration/schema, and run in `asset_runtime` without reading the original source implementation. Keep host-specific mount paths, creator-machine paths, and long harness commands out of `operator.md` and formal scientific contracts; record image/digest and commands in test evidence.

Do not create frozen operators from paper-only evidence, do not claim runtime evidence from a plan, and do not invent host review/publication metadata.
