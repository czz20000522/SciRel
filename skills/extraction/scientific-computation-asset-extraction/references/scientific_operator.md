# Scientific Computation Asset Reference

## Definition

First principle: extracted assets are the source-backed scientific capabilities that a production system can reconfigure, reinitialize, and recompose. They are not a copy of the source program's default run shell. Treat case-specific initialization, file layouts, concrete benchmark values, and representation adapters as configuration or glue unless they encode source-specific scientific or numerical semantics.

A `scientific_relation` is a source- or document-evidenced semantic/model-layer asset. It names a stable governing equation, closure law, diagnostic definition, state transition family, model family, or scientific constraint. It does not execute. It should record variables or state, assumptions, applicability, known directions, evidence, and links to implementing operators or task graphs when they exist.

A scientific_operator is a governed, reusable, implementation-backed scientific computation identity.

For whole-project extraction, a scientific_operator must be derived from an `operator_candidate` framework node or from
a stable sub-boundary inside a `nested_task_graph` framework node. It is not the program framework map itself, not a
whole user task, not an unexpanded task node, and not an IO/config/support action.

It must have:

- independent scientific meaning
- a stable external contract
- a plausible role as a reusable/composable capability node
- concrete source-code evidence
- an executable implementation draft
- validation checks that prove behavior rather than file shape

A scientific_operator implements one direction of a scientific relation. It is not merely a relation description, source function, helper, wrapper, workflow label, utility transform, file IO helper, plot helper, notebook cell, API adapter, broad research task, or review decision. A stable numerical calculation alone does not qualify: a one-line `abs`/real-or-imaginary-part extraction, special-function invocation, scalar scale, cache lookup, loop helper, or local array transform has no independent scientific handoff and must remain internal to the nearest operator that owns the complete directed scientific mapping. Do not manufacture an asset only to make a graph structurally formula-free.

A `scientific_task_graph` is a governed, reusable, implementation-backed composite scientific computation identity. From the outside it is a black-box capability with explicit inputs and outputs; from the inside it expands into `scientific_operator` nodes, nested task graphs, IO/config actions, support actions, diagnostics, controlled glue, state-contract nodes, and evidence-bounded gaps. This skill may emit task-graph candidate packages only when the composite boundary is stable, source-backed, callable, and testable. A candidate graph contract or standard-case oracle harness may support discovery and validation, but it must stay in the report or validation evidence until a callable entrypoint computes, dispatches, or safely wraps the composite behavior. Do not collapse a task graph into one operator merely because it is meaningful, and do not split a framework node below the point where the scientific mapping disappears. Do not flatten a nested task graph by default when the child graph has a stable reusable identity; preserve it as a node and expose the expansion through `task_graph.yaml`.

### TaskGraph Extraction Eligibility Gate

Emit a task graph only if it makes a source-backed composite relation executable that cannot be represented by independently invoking its nodes in arbitrary order. The required relation may be a producer-to-consumer state handoff, a non-commutative normalization or reduction, a branch/selector that changes the downstream model, a feedback/update order, a shared-state ownership transfer, a failure/convergence gate, or another ordering/coordination rule that changes scientific or numerical meaning.

Do not treat lexical source-call order as evidence by itself. Do not emit a task graph solely because it calls one operator, forwards unchanged inputs/outputs, groups freely reorderable parallel operators, exposes a validation fixture, or gives a convenient entrypoint. Keep such assets as independent operators plus framework-map/ledger relations; merge a thin existing graph into its operator or mark it as a removal candidate. Before emission, record the non-interchangeable relation, the relevant node outputs/inputs, the consequence of reordering/omitting it, and a test that would fail if the relation drifted.

### Task-Graph Implementation Purity

Independent callable contract does not mean an implementation must duplicate every scientific
node. A task graph is self-contained through its declared dependency references and the bundle
entrypoint, not through copied scientific code. Each scientific/numerical node in
`task_graph.yaml` must carry an `asset_ref` to an operator or a same-primary-node nested task graph;
`graph.py` resolves that reference through the bundle loader or an injected resolver and forwards
declared ports.

`graph.py` may perform orchestration work: contract/port validation, explicit state storage,
branch and feedback scheduling, convergence/failure control, declared adapter dispatch, and
diagnostic collection. It may also execute a bounded, declared `controlled_glue` node when the
ports of two independent assets need a non-scientific representation adaptation that no operator
owns: unit or index-base conversion, shape/axis conversion, index mapping, storage embedding or
boundary padding, block concatenation, component selection, real/imaginary projection, or scalar
affine conversion. The YAML node must name a graph-local glue callable distinct from `run_graph`,
its input and output ports, its permitted adaptation category, and its ownership; it has no
`asset_ref` and is reviewed as glue, not as a scientific operator. It must not directly implement source-specific
formulas, interpolation or special-function calls, matrix/RHS/stencil assembly, quadrature,
discretization, numerical state update, or physics-specific clipping/normalization. Move such behavior into an independently
meaningful operator. A numerical fragment is independently meaningful only when it carries a
named scientific relation or a complete source-specific discretized scientific handoff; do not
promote `abs`, one real/imaginary projection, a special-function call, a scalar scale, a cache, or
loop plumbing solely to satisfy graph purity. If it has no independent scientific handoff, merge it
into the nearest operator that owns the complete directed mapping. A task graph with one forwarding node is not
admissible and must be merged or removed.

An `orchestration_only` task graph is the narrow exception for a source-backed cadence/counter
state machine that publishes only explicit feedback state and an action plan. It has no scientific
asset node or scientific payload mapping. Each node must be a named `support_action` with a bounded
control contract (`cadence_gate`, `counter_state_transition`, or `action_plan_publication`), and
the implementation may not call NumPy/SciPy or hide field/matrix/RHS/diagnostic physics. It is not
an arbitrary payload channel: action-plan publication is limited to literal action names and
control metadata and may not echo caller-provided values. It is not
`controlled_glue`: do not use this exception for port adaptation, and do not use it to exempt a
scientific calculation from operator/nested-graph extraction.

Task-graph tests must prove both layers: YAML node references and required order/feedback drift
fail closed, and the executable graph invokes the declared assets through the bundle entrypoint.
`validate_import_intake_package.py` enforces this structurally: every `graph.py` requires at least
one declared scientific `asset_ref`; `internal_kernel`, direct SciPy/NumPy numerical calls, direct
arithmetic mappings, and dynamic sibling imports fail the package gate. This is intentionally
conservative: move disputed logic into an operator instead of seeking a graph-level exemption.

A framework node is not a package-type declaration. One framework node may project to an operator family, one operator, a nested task graph, an assembly recipe, support-only work, or a terminal gap. In particular, diagnostics that independently consume the same state and produce unrelated moments remain separate operators when no required join exists. They become a task graph only when a source-backed same-snapshot, shared-normalization, atomic fan-in, or other non-interchangeable coordination contract makes the composite result scientifically meaningful. Apply `asset_projection_decision_manual.md` before candidate emission.

### Three-Layer Composition Boundary

Use exactly three execution layers. The program framework map is the project-wide authority for framework-node boundaries and dependencies between those nodes. A task graph is the executable composition inside one declared framework slice; its nodes may be scientific operators or nested task graphs, and its node set must be a declared subset/refinement of that framework slice. A scientific operator is an independently reusable leaf computation.

`TaskGraph(T) ⊆ FrameworkNode(N)` is mandatory. A parent may nest a child task graph only when
both declare the same `primary_pfm_node`. If a required scientific/numerical relation crosses
framework nodes, keep both task graphs independently callable, expose the producer output and
consumer input as explicit ports, and record the handoff as a framework-map edge. Do not create a
larger cross-node parent graph; `related_pfm_nodes` records a dependency, not additional graph
ownership.

Required configuration schemas, adapters, benchmark cases, validation oracles, and capability claims are supporting assets. They may be emitted to make packages usable and auditable, but they do not replace executable operator/task-graph packages. Concrete case values belong in configuration bindings or benchmark cases, not in relation/operator defaults.

## Domain Context Examples

This reference is tuned for implementation-backed scientific software. Preserve the domain context evidenced by the supplied materials instead of imposing one. When the source is fusion or plasma software, useful context may include tokamak, stellarator, spherical tokamak, reversed-field pinch, field-reversed configuration (FRC), magnetic mirror, linear plasma devices, equilibrium, MHD/stability, transport, kinetic/Fokker-Planck, fast ions, neutral beams, RF/waves, diagnostics, reconstruction/inversion, atomic/radiation rates, and wall/divertor interactions.

For fusion/plasma sources, strong examples include:

- Grad-Shafranov residuals, equilibrium force-balance terms, magnetic-field Green functions, and field/current response matrices;
- diagnostic forward and inverse response operators, line/volume intersection geometry, detector sightline transforms, and emissivity-to-signal projections;
- density, temperature, current, pressure, or distribution-function profile reconstruction subproblems;
- RF/ray dispersion roots, refractive-index initialization, wave absorption terms, and resonance checks;
- neutral beam deposition, charge-exchange or reaction-rate integrals, distribution-coupled source terms, and radiation/atomic coefficient assemblies with explicit units;
- orbit, gyro-surface, field-line, flux-surface, and particle-to-grid geometry operators;
- MHD/stability terms, transport fluxes, collision coefficients, source terms, and conservation/residual checks.

Reject generic utilities, but do not reject a well-evidenced domain operator merely because it is not shaped like a reference case, not axisymmetric, not R-Z, not Python, or not directly comparable to earlier examples.

## Code Source Roles

Classify source material before selecting candidates. File type is not enough.

- `source_code`: source files, scripts, notebooks, modules, tests, examples, or runtime traces that implement behavior.
- `algorithm_or_model_documentation`: manuals, reports, design notes, derivations, theory sections, equations, variable definitions, numerical-method descriptions, module decompositions, benchmark descriptions, or validation discussions. These identify candidate scientific relations, governing equations, intended physical terms, units, assumptions, and high-value algorithm targets; they do not replace implementation evidence.
- `operational_documentation`: README, installation guide, parameter guide, runbook, usage notes, input-deck documentation, or output-file notes. These clarify setup, units, parameters, runtime modes, failure modes, and use boundaries; they do not replace implementation evidence.
- `data_fixture`: tables, benchmark data, saved arrays, input decks, regression outputs, or reference outputs.
- `reproduction_or_plot`: plotting scripts, figure generators, post-processing scripts, and visual assets. These are usually supplementary unless they contain a distinct computation in scope.

Users may provide a mixed code bundle instead of a curated source list. Resolve scope without asking the user to choose files unless the next action would overwrite, delete, or otherwise destructively modify user data.

For mixed code snapshots:

- infer material roles from content, not from user-supplied labels or file names. A document that explains equations, algorithms, physics terms, variables, benchmark cases, or numerical methods is algorithm/model documentation even if it is named as a report, manual, note, README, or paper;
- treat the provided materials as one source snapshot to be resolved;
- identify source families from imports, examples, tests, folder names, build files, documentation links, and shared fixtures;
- partition unrelated projects or weakly related source families;
- choose the primary extraction universe from the family most directly supported by implementation evidence and the requested output target;
- include shared or core scientific kernels used by that universe and fixtures required for validation;
- treat older folders, alternate examples, demos, figure scripts, GUI wrappers, reproduction notebooks, and orphan data as supplementary unless they contain a distinct strong physical operator in scope;
- if several coherent families remain, extract fewer high-signal non-duplicate operators rather than trying to cover every folder.

For whole-project or source-snapshot extraction, source-scope assumptions belong in the project-level sidecars outside the operator package directory. Summary scope belongs in `extraction_report.md`; detailed assumptions and candidate decisions belong in `extraction_ledger.md`. They are not part of any single `operator.md` and must not be placed inside an operator-only package root.

## Cross-Evidence Alignment

Mixed-material extraction should align documentation, implementation, and validation evidence. Do not choose between "only read code" and "only read documentation"; use each evidence role for what it can prove.

- Documentation-to-code: use algorithm/model documentation to seed `scientific_relation` anchors, primary state variables, governing equations, physical terms, discretizations, boundary conditions, and benchmark signals.
- Code-to-documentation: use source code, call chains, symbols, tests, traces, and runtime behavior to prove which documented candidates are implemented and where their actual boundaries live.
- Validation evidence: use tests, examples, fixtures, traces, benchmark outputs, and source execution to decide oracle strength and numerical comparison duties.
- Conflict handling: if documentation and source disagree on equations, units, normalization, signs, boundary behavior, enabled physics, or validation expectations, preserve current source behavior for extraction and record the mismatch as a review/governance risk. Do not silently repair source behavior to match prose.

Per strong candidate, record one of these evidence-alignment states in the engineering ledger:

- `doc_code_aligned`: documentation identifies the scientific relation and source code implements a mappable boundary.
- `doc_derived_unmapped`: documentation describes a candidate, but no implementation boundary was found in the current source snapshot.
- `code_evidenced_undocumented`: source code contains an implementation-backed candidate that supplied documentation does not explain.
- `doc_code_conflict`: documentation and source appear to disagree materially.
- `validation_only_oracle`: fixtures or benchmark outputs can validate behavior, but documentation or source intent remains incomplete.

Only `doc_code_aligned` or `code_evidenced_undocumented` candidates can become extraction-ready implementation-backed packages, and only after the ordinary definition, contract, and oracle gates pass. Documentation-only candidates may become `scientific_relation` anchors or ledger entries, but not operator/task-graph packages.

## Relation, Direction, Configuration, Adapter

Keep these boundaries explicit:

- Relation: scientific semantics, no execution. Same relation may have several directions.
- Directed operator: one executable direction of one relation.
- Task graph: a directed composite workflow over operators, nested graphs, adapters, configuration nodes, state contracts, and controlled glue.
- Required configuration schema: declares needed values, grids, units, boundary settings, and model-variant selectors. It does not bind source-case values.
- Configuration binding or benchmark case: supplies concrete runtime values for a user run or standard case.
- Adapter: representation conversion such as parsing, field mapping, unit conversion, shape conversion, or package-local dispatch. It is not a scientific operator unless it encodes source-specific scientific or numerical semantics.

Before selecting, omitting, or blocking a candidate, ask:

1. Constancy: does this logic stay the same when user demand or initialization changes?
2. Reconstructability: can a future agent rebuild it from emitted contracts, YAML, tests, sidecars, and runtime schema without source access?
3. Source specificity: does it encode source-specific formulas, branches, weights, normalization, boundary behavior, index maps, units, signs, or table conventions?
4. Case binding: does it only serve a default file format, benchmark value, or source initialization shell?

Use this split for canonical gap labels:

- `extraction_gap`: missing core scientific or source-specific numerical behavior.
- `configuration_or_schema_need`: missing concrete values, shapes, axes, field mappings, units, variant selectors, or initialization schema.
- `ai_completable_glue`: missing generic parsing, conversion, dispatch, loop scheduling, error handling, or adapter code.
- `validation_oracle_gap`: missing source run, intermediate snapshot, fixture provenance, or numerical oracle.
- `cannot_complete`: evidence is too damaged or incomplete without inventing science, data, or authority.

Use older labels such as `direction_gap`, `operatorization_gap`, `implementation_gap`, `graph_node_gap`, or `closure_data_gap` only as optional technical subtypes under one canonical gap kind.

## Granularity And Count

Extraction is definition-driven, not coverage-driven. Do not optimize for "one operator per project", "many operators per project", source-symbol coverage, or package count.

A project may legitimately produce one accepted operator when that is the only independently reusable scientific computation identity and the rest of the code is application orchestration, wrappers, IO, plotting, table plumbing, generic helpers, or duplicate call paths. Another project may legitimately produce several accepted operators when the source contains several distinct physical quantities, governing-equation terms, diagnostic responses, reaction rates, cross sections, coordinate maps, or solver substeps with stable contracts and defensible oracles.

Use the smallest package set that preserves real scientific identities without merging different physics or splitting glue. When in doubt, prefer a slightly broader scientifically coherent operator over many thin packages that are merely wrappers around adjacent helper functions.

## Broad Discovery Before Deep Extraction

Whole-project extraction should not start by deciding which few routines are easiest to package. Start broad, then go deep.

Before candidate census, whole-project extraction must produce `program_framework_map.md`. The map is the stable
project-level decomposition used to make later LLM outputs less random. It contains a Level 0 Physics Mermaid as a
domain-expert readable projection for downstream review and a Level 1 source-anchored map with node ledger, edge ledger,
ledger-derived Mermaid, split decisions, and standard-case fixture plan. The producer generates Level 0 automatically;
it is not an expert-in-the-loop checkpoint. Level 1 drives candidate selection.
Neither diagram proves operator identity by itself; source evidence, node/edge ledgers, and the operator definition do.

The broad pass builds a code-structure map and candidate census:

- identify entry points, imports/includes, public symbols, definitions, calls, call chains, ownership modules, tests/examples, solver loops, and data/control-flow neighborhoods;
- use owner/system-provided AST, call graph, code graph, state lineage, ctags/LSP, parser output, or equivalent structured evidence when available; use systematic text search only as a fallback and record that limitation;
- connect framework/code-graph nodes to task roles and scientific roles: operator candidate, nested task graph, IO/config action, support action, blocked gap, target relation, constituent term, parameter/closure provider, support implementation, or reject/glue;
- record strict candidates, loose or workflow-rework candidates, support kernels, rejected/glue units, unknowns, and duplicate/merged identities.

If coverage is incomplete, state the uncovered source families, symbols, call chains, or material roles and treat the candidate census as incomplete. Do not use incomplete discovery counts as project-level completeness evidence.

The candidate computation graph from this pass is a working hypothesis derived from the program framework map. It helps
the extractor avoid being trapped by helpers or drivers, but it is not an edge-eligibility decision or outbound run plan.
Final extraction emits operator and task-graph candidate packages. Internal task-graph edges belong inside
`task_graph.yaml`; cross-asset relationships may be described in the report as hypotheses for later review.

The deep pass is iterative:

1. choose the highest-priority candidate or small coherent batch from the census;
2. extract its source evidence and stable input/output contract;
3. implement one operator or task-graph candidate package;
4. run tests and source parity or blocker analysis;
5. update the engineering ledger, validation matrix, and executive report summary before continuing.

Do not generate all packages in one unverified burst. The iteration may take multiple internal passes or turns, but whole-project delivery is complete only when the census has been exhausted: every extractor-accepted candidate has an emitted package, and every non-emitted candidate is merged, downgraded, rejected, rework-only, or blocked for a concrete evidence/runtime reason. A final-extraction backlog is not a parking lot for "not done yet" work. Rework-only or blocked task graphs are report entries, not `task_graphs/` packages.

For pressure tests, planning runs, or explicitly partial runs, a candidate-map report may stop before package emission only when it labels that phase and uses report-local processing status such as `candidate_pending_deep_extraction`. That status is not an extraction disposition and must not be used in final completeness claims.

Before a `final_extraction` claim, run an omission sweep from the program framework map back to emitted assets:

- for every high-value state transition, operator/matrix/RHS assembly, diagnostic response, source/output family, or source-documented target relation, ask whether the emitted assets can form a runnable task graph;
- if yes, emit that higher-level task graph only when it owns a required non-interchangeable scientific/numerical relation; otherwise retain the independently callable assets and record their relation in the framework map or ledger;
- if only parser adapters, state projection, shape conversion, loop scheduling, or DAG dispatch are missing, add them as controlled glue inside the graph package rather than dropping the graph;
- if source-specific scientific or numerical semantics are missing, record an evidence-bounded gap instead of relabeling the item as IO/config, downstream validation, or runtime parity;
- if the item is truly generic glue or validation-only work, state the terminal downgrade in the ledger.

## Operator Selection Invariants

Treat these as the general extraction law. Concrete project outcomes should be explained as consequences of these invariants, not as rules in themselves.

- Scientific centrality: prefer computations that carry the source family's primary scientific transformation from inputs/state to scientifically meaningful outputs. Helpers that merely supply constants, table values, formatting, or plumbing are subordinate unless the source family is itself a coefficient library.
- Framework-node fitness: prefer boundaries that are anchored in `program_framework_map.md`, can become reusable capability nodes with explicit scientific inputs, explicit outputs, artifact-like data handoff, downstream consumption value, and validation checks that let another workflow call, replace, or compose the computation without running the full original application.
- Irreducible identity: choose the smallest boundary that preserves the named physical quantity, governing equation term, residual, source/transport contribution, diagnostic response, or solver step. Do not split below the level where the scientific meaning disappears; do not merge beyond the level where independent review, testing, or reuse is lost.
- Nested graph composability: when several accepted operators or task graphs form a stable larger mapping, treat the larger mapping as a candidate task graph rather than leaving composition only as prose. Its nodes may stay nested; the package should expose black-box reuse first and expansion second.
- Framework edge closure: when a high-value framework edge moves scientific state, coefficients, residual terms, rows, indices, boundary selections, or diagnostics between nodes, the edge itself needs a closure decision. It may be implemented by an emitted asset, controlled internal glue/kernel inside a task graph, post-extraction AI-completable glue from emitted contracts, configuration demand, validation-only need, terminal non-emitted decision, or extraction gap. Endpoint node packages do not prove the edge is covered.
- AI-completable glue boundary: do not emit a standalone asset for generic code an LLM can reasonably recreate without source-specific scientific evidence, such as ordinary IO, parsing, format conversion, array reshaping, loop scheduling, error handling, or DAG dispatch. Keep it as controlled completion inside the nearest task graph or adapter.
- Implementation evidence: the boundary must be backed by concrete code evidence. Documentation, papers, manuals, and benchmarks can point to what matters, but code evidence determines what can become an implementation-backed package.
- Source-faithful implementation: source-backed packages must translate the cited computation, not simplify it. Formula factors, geometric weights, normalization/post-processing, state-dependent weights, branch conditions, boundary handling, table conventions, units, signs, and source-local numerical conventions are part of the computation unless the package explicitly narrows its claim or records a gap.
- Standalone contract: project globals, common blocks, namelists, files, object graphs, and driver state must be converted to explicit inputs/outputs or recorded as blockers.
- Oracle fitness: the boundary must admit meaningful validation: source parity, source-derived fixtures, independent formula checks, conservation/symmetry/monotonicity, convergence/failure semantics, or boundary behavior.
- Accountability boundary: sidecar sets follow the extraction universe that can be reviewed as one source-scope and candidate-ledger decision. User request count, folder count, or project count may suggest sidecar shape, but they do not define it.

## AI-Completable Glue Boundary

Use AI-completable status as a downgrade signal, not as the whole decision.

Separate source-context completion from post-extraction omission. During extraction, controlled completion may use the current source tree, call graph, and traces to materialize bounded glue inside the package. Gap completion may later use supplied source/document context to draft a proposal. But omitting behavior, downgrading it to glue, or leaving it to future reuse must be judged from the post-extraction consumer context. A future agent should be assumed to have only the emitted package, contract, YAML, tests, and sidecar notes. If behavior is only "obvious" while reading the source, it is not safe to omit from the extracted asset.

Usually AI-completable and not standalone assets:

- file readers, namelist parsers, serializers, netCDF/text writers, and format conversion;
- ordinary loops, DAG dispatch, node ordering, retries, error reporting, and status aggregation;
- generic NumPy/SciPy operations, interpolation, sorting, reshaping, packing/unpacking, and linear-algebra calls with no source-specific scientific contract;
- standard numerical adapters such as replacing a legacy ODE driver with a modern integrator or a generic 2D interpolator with a standard interpolation library, when the source already supplies the scientific equations and data contract;
- simple adapters that translate shapes, field names, or storage layouts for an already accepted operator or task graph.

Not safely AI-completable without source evidence:

- domain formulas, closure relations, empirical constants, branch rules, sign/normalization conventions, and boundary conditions;
- geometric weights, state-dependent integration weights, post-processing normalization, source-specific diagnostic factors, and per-region/per-surface state contracts;
- solver stencils, residual maps, matrix/RHS assembly, convergence updates, and source/transport/collision/wave/radiation terms;
- source-specific row/index mappings, branch selectors, scatter/gather rules, RHS/residual builders, state projections, project-specific historical state machines, common-block semantics, table provenance, compressed legacy formats, or non-obvious numerical hacks.

Short code can still be emitted when it locks down a source-specific scientific or numerical convention. The package or ledger must say why the candidate is not merely generic glue. Examples of valid reasons include a named physical quantity, a source-local normalization, a grid or timestep convention consumed by a solver, a boundary rule, a diagnostic contract, or a reusable task-graph node whose behavior reviewers must verify.

Do not block a task graph only because its missing pieces are AI-completable glue or generic numerical infrastructure. Supply those pieces as controlled completion and record the boundary. Coupling through common blocks, callbacks, file formats, external ODE solvers, or interpolation helpers is a reason to explicitize state, not a terminal blocker. A finite source-backed loop, branch table, index map, row emitter, or scatter/gather transform that is too local to be a standalone asset can live as an internal computational kernel inside the nearest task graph. Block only when the missing piece is scientific semantics, source-specific numerical behavior, source data/state needed by the equation, a validation oracle, or implementation evidence that the agent cannot infer safely.

If the future agent could not recreate the behavior from the extracted package and sidecars, either materialize it as controlled completion inside the package, emit it as an operator or internal task-graph node, merge it into a larger accepted task graph, or record an evidence-bounded gap. Do not downgrade it to glue merely because the extractor or gap-completion skill can infer it from source context.

Separate extraction backlog from downstream validation work. Once an operator or task-graph boundary has been emitted, full original-runtime replay, source probes, golden intermediate capture, event-history logs, random-stream replay, and file/runtime harnesses are validation evidence unless they expose a distinct un-emitted scientific mapping. Do not keep them as `final_extraction` rework merely because they would strengthen parity.

For stochastic or Monte Carlo workflows, emit source-backed transition laws, rates, scoring/deposition maps, deterministic expectation maps, or aggregate response maps when they have stable contracts. Sampled event histories, seed streams, and random-walk replay are runtime validation artifacts unless the stochastic transition kernel itself is the asset.

For solver-controlled workflows, emit residuals, operator/matrix/RHS assembly, state updates, convergence diagnostics, closures, and boundary-condition maps. Generic Newton iteration, line search, ODE package invocation, retry scheduling, and driver loops are support/control glue unless the source encodes a source-specific convergence law or scientific update.

## Target Relation And Dependency Hierarchy

Core algorithms are found by tracing what the source is ultimately trying to solve, update, constrain, reconstruct, or diagnose. Start from the target relation as a stable mapping, then walk backward through its dependencies. The target may be a closed formula, but in scientific codes it is often a residual map, matrix/operator assembly, state transition, nonlinear update, objective function, source/transport term, or diagnostic response. Do not start from the easiest directly runnable helper and infer that it is the core.

Use this hierarchy:

1. Target-relation operator: computes the primary solved quantity, state update, residual, balance relation, diagnostic response, inversion target, or governing-equation term. This is the preferred extraction target when implementation-backed and testable.
2. Constituent physics/operator term: computes a force/source/sink/transport/collision/wave/radiation/deposition/geometry term that enters the target relation and has independent scientific meaning over a meaningful grid, phase space, or geometry.
3. Parameter or closure provider: computes a mass, coefficient, cross section, rate, table fit, normalization, profile value, or closure quantity used by a target relation or constituent term.
4. Support implementation: interpolation, parsing, table loading, unit conversion, array reshaping, special functions, IO, plotting, and driver glue.

Parameter and closure providers may be valid scientific_operator candidates when they have a physical contract and oracle, but they should not displace the target-relation operator. If only dependency providers are emitted, the report must say which target relation they support and why the target relation was not emitted.

## Stable Mapping Discovery

For iterative solvers, coupled workflows, and discretized differential-equation code, a `scientific_operator` is usually a stable mapping rather than a single symbolic equation. A stable mapping has explicit scientific inputs, explicit outputs, a reviewable computational boundary, and a meaningful oracle.

Prefer these mapping types before lower-level scalar helpers:

- residual map: `(state, parameters, grid, boundary_conditions) -> residuals or balance errors`;
- discrete operator or matrix assembly: `(state or coefficients, geometry, grid) -> operator matrix, right-hand side, stencil weights, or coupled coefficients`;
- state or time transition: `(state_n, inputs, step controls) -> state_next and diagnostics`;
- nonlinear, fixed-point, or relaxation update: `(state_k, parameters, controls) -> state_next, residual, convergence diagnostics`;
- source, sink, transport, collision, wave, radiation, or deposition term: `(state, geometry, species, parameters) -> term arrays or weighted contributions`;
- objective, inversion, or reconstruction map: `(state or parameters, observations, weights) -> objective, residual vector, gradient, or reconstructed profile`;
- diagnostic forward response: `(physical state, geometry, instrument model) -> predicted measurement or response`.

Use code signals to find these boundaries: loops over mesh/phase space/time, residual or norm calculations, convergence tests, solve/root/update calls, matrix/Jacobian/stencil assembly, flux/source accumulation, boundary-condition application, and benchmark outputs compared by tests or examples.

Choose the smallest boundary that preserves the stable mapping, not the smallest helper inside it. If the full solver is too coupled or hidden-state-heavy, try to extract the residual map, operator assembly, source term, update step, or diagnostic response that the solver depends on. Only fall back to parameter or closure providers after recording why the higher-value mapping boundary could not be emitted.

If a central solver or workflow is downgraded to `SOLVER_WORKFLOW_REWORK`, treat that downgrade as a prompt for one recursive sub-boundary pass, not as a stopping point. Search inside the workflow for stable residual, conservative flux, source/transport/collision/wave term, matrix-row or operator assembly, state/update, boundary-condition, diagnostic-response, or closure nodes that can stand alone. Accept only nodes with scientific identity, explicit contracts, and meaningful tests; leave generic numerical kernels, interpolation, storage-layout, mesh/profile plumbing, and table helpers as `SUPPORT_KERNEL` unless they are explicitly bound to a named physical quantity, governing-equation term, diagnostic response, or reusable physics coordinate.

In `final_extraction`, a workflow-level rework item is terminal only after the whole task-graph option and all internal package-worthy sub-boundaries have been processed. Source-runtime probes that only strengthen parity should be recorded as downstream validation needs, not as pending extraction.

## Framework Node Fitness

Project extraction should prefer operator candidates anchored in the program framework map that could serve as nodes in a future scientific capability graph. This is not a demand for broad workflows; it is a demand for stable scientific handoff.

A candidate has strong framework-node fitness when it answers all of these:

- node role: what scientific state, field, residual, term, response, objective, profile, coefficient, or diagnostic does this node produce?
- artifact input contract: what arrays, scalars, grids, geometry, boundary conditions, observations, species, profiles, or tables must be explicit inputs?
- artifact output contract: what output can downstream computation consume without inspecting the original project state?
- composition value: which solver step, residual, diagnostic, reconstruction, source update, or higher-level calculation can consume this output?
- replacement boundary: could another implementation with the same contract replace it?
- verification boundary: can tests prove source parity, fixtures, invariants, convergence/failure semantics, or boundary behavior at this node?

Weak framework-node fitness is a downgrade signal even when the code runs. Examples include a routine whose only stable role is formatting, loading, plotting, mutating global state, forwarding to another call, exposing a single unparameterized number, or computing an intermediate whose consumer and scientific role cannot be named.

Scalar or local kernels can still have framework-node fitness when they expose a named physical quantity with units or normalization, domain, source provenance, downstream consumer, and oracle. They are usually lower priority than residual, assembly, update, source/transport, diagnostic, objective, or reconstruction mappings unless the source family is primarily a coefficient/rate library or higher-level mappings are blocked.

## Core Algorithm Priority

`scientific_operator` is the admissible artifact type; `core physical algorithm` is a higher-value subset used for universe-level selection. A valid operator may be local and small, but whole-project extraction should first seek the computations that carry the extraction universe's primary scientific model.

Before selecting files, build an extraction-universe algorithm map from source code and supplementary documentation:

- primary state variables or fields being advanced, solved, reconstructed, or diagnosed;
- code-structure map: entry points, calls/includes/imports, module ownership, tests/examples, and call-chain positions for high-value candidates;
- governing equations, residuals, balance laws, variational objectives, or response models;
- target stable mapping: the specific residual, assembly, update, transition, objective, diagnostic response, or relation that uses prerequisites to compute the primary solved/diagnosed quantity;
- framework node role: how this mapping could be called, consumed, replaced, or composed as a capability node;
- dependency hierarchy: target-relation operators, constituent physics/operator terms, parameter or closure providers, and support implementation;
- solver/update steps, discretizations, finite-difference/finite-volume forms, matrix assemblies, quadratures, and boundary conditions;
- coupled physical terms such as collision, wave-particle interaction, source/sink, transport, radiation, equilibrium, diagnostic response, or deposition terms;
- benchmark or validation quantities that indicate which pieces are central to the project.

Extraction priority:

1. Core equation or solver operators: state update, residual, conservative flux form, implicit/explicit time advance, nonlinear solve, inversion, or reconstruction with structured convergence/failure semantics.
2. High-value component operators: coefficient assemblies, source/sink terms, transport terms, wave/damping terms, collision terms, radiation terms, or geometry/response mappings that feed the core equation over a meaningful grid, phase space, or diagnostic space.
3. Local physics kernels: scalar or pointwise rates, cross sections, table fits, material/atomic coefficients, simple roots, or local response amplitudes.
4. Support kernels: generic interpolation, coordinate conversion, table plumbing, special functions, array helpers, and IO.

Do not satisfy a project extraction with only low-priority local kernels when the source code or documentation identifies higher-level core algorithms. If the core algorithm is too coupled, hidden-state-heavy, unrunnable, or lacks a stable oracle, record that blocker in the engineering ledger and summarize the risk in the executive report.

## Strong Physical Semantics Gate

Before classifying candidates, filter out non-physical and weakly physical software units. The default extraction-eligibility bar is strong physical semantics, not "any useful numeric function".

Keep a candidate only when it directly computes, transforms, solves, diagnoses, validates, or constrains a named physical or scientific-computation quantity, such as fields, fluxes, pressure, density, temperature, current, energy, particle state, source terms, equilibrium residuals, diagnostic geometry, or governing-equation terms.

Strong examples include Green function kernels, field/current projections, source-term discretizations with physical weights, material or particle response kernels, velocity-space integrals, diagnostic geometry intersections, and solver substeps with structured residual or convergence semantics.

Reject or report as a non-operator gap:

- file loading, parsing, serialization, logging, packaging, plotting, UI, API, or CLI wrappers
- generic array reshaping, table formatting, cache helpers, path helpers, or config glue
- repository orchestration, job control, review workflow, prompt handling, or database adapters
- ordinary code-completion glue that only makes an accepted operator/task graph runnable and does not encode source-specific scientific or numerical behavior
- functions whose only purpose is to call another routine without adding a stable scientific contract

Support kernels such as coordinate transforms, interpolation, finite differences, mesh construction, or matrix assembly only become accepted operators when they are narrowed to a specific physical quantity or diagnostic and are independently reviewable. Otherwise classify them as `SUPPORT_KERNEL` and record the downgrade in the engineering ledger for whole-project/source-snapshot extraction.

Special-function approximations, generic mathematical kernels, and preprocessing maps are support kernels by default. Examples include scaled Bessel/Macdonald approximations, interpolation-only flux maps, generic coordinate conversions, array-conditioned polynomial evaluators, and source-table plumbing. Upgrade them only when the operator contract names the physical quantity or diagnostic response they compute, the code evidence supports that identity, and tests cover the physics-facing contract rather than only the helper's numerical self-consistency.

## Scalar And Local Physics Kernels

Do not reject a candidate merely because one call returns a scalar. A scalar-valued evaluator can be a scientific_operator when it maps explicit inputs to a named physical or scientific-computation quantity with a stable domain, units or normalization, source-backed formula/table provenance, and a meaningful oracle. Examples include reaction-rate coefficients, cross sections, residual components, dispersion roots, local source terms, response amplitudes, and material or atomic coefficients.

For whole-project extraction, scalar and pointwise kernels are usually lower priority than core equation, solver, source/transport, collision, wave, diagnostic, or coefficient-assembly operators. Accept them as standalone packages when the source family is primarily a coefficient/rate library, the user explicitly requests that layer, they are indispensable high-value components of a selected core algorithm, or higher-level core candidates are blocked and the report says why.

Reject or downgrade scalar candidates when they are:

- hard-coded constants or configuration values rather than parameterized computations;
- raw coefficient-table plumbing without a physics-facing contract;
- generic interpolation or polynomial evaluation with no named physical quantity;
- hidden-state lookups whose inputs, units, species/model regime, or table provenance are not explicit;
- numerically correct helpers that have no independent downstream scientific role.

Judge "core" by project-level scientific role, not by location in the application. A local physics kernel may be acceptable but still low value for project extraction; a broad application driver may fail operator extraction eligibility when it lacks a stable side-effect-free contract and structured diagnostics.

## Multi-Language Code Snapshots

Large scientific-code snapshots often mix Fortran, Python, IDL, generated tables, compiled objects, regression inputs, and documentation. Treat source files as evidence; ignore compiled or cache artifacts such as `.o`, `.mod`, `.pyc`, and generated build outputs unless the user explicitly asks to inspect binary fixtures.

Source language is evidence language, not necessarily output language. Accepted executable operator packages must use either the Python profile or the C profile from `language_profiles.md`. Fortran, C++, IDL, MATLAB/Octave, notebooks, and other languages may supply formulas, loops, tables, tests, and source anchors, but the extracted operator must be rewritten into Python or C unless the user explicitly changes the project standard.

For legacy language code:

- Evidence references should use concrete source-root-relative line ranges such as `src/ray_initialization.f:22-597` or `src/diagnostic_geometry.f90:120-210`.
- A subroutine is not automatically a standalone operator. Many subroutines mutate common blocks, write files, print diagnostics, or depend on global namelist state.
- Do not choose the easiest directly runnable scalar routine while ignoring hidden-state-heavy but central solver, coefficient-assembly, or update routines. If those central routines cannot be emitted, report their blockers.
- Prefer side-effect-free representations of central computations. When a central solver or coefficient assembly is too coupled to emit, smaller formulas, table interpolation, rate coefficients, coordinate transforms, dispersion relation roots, geometry intersections, normalized distributions, and velocity-space integrals may be extracted only with priority/blocker rationale.
- Classify large driver loops, namelist readers, file writers, plotting routines, regression harnesses, and coupled simulation workflows as workflow rework or reject unless they can be converted into a stable input/output contract with structured diagnostics.
- If a computation depends on data tables or coefficient files, include those tables as evidence and either embed the minimal coefficients in the implementation artifact or require them as explicit inputs. Hidden file reads are not standalone operator behavior.
- When rewriting legacy code into Python or C, preserve and test array layout, index base, loop bounds, precision, units, sign conventions, and boundary behavior. A rewrite that only compiles or imports is not accepted.
- For Fortran rewrites, check numeric literal kind and promotion rules. Unsuffixed real literals such as `1.0`, `2.864E-04`, or `3.14159` may be default `REAL` before assignment to `REAL*8`; if source parity shows small systematic deltas, emulate or justify that literal precision instead of silently using target-language double literals.

## Source Fidelity And Cross-Source Conventions

Extraction proves fidelity to the current source snapshot; it does not decide whether that source is physically more correct than another source family. When separate codebases implement apparently similar quantities, they may intentionally or accidentally differ in units, normalization, sign convention, constants, coordinate orientation, boundary handling, or validity domain.

For the current source snapshot itself, fidelity means the emitted implementation preserves the cited source behavior over the package's declared domain. Do not replace a cited source formula with a simpler phase-space integral, reduced coefficient expression, averaged model, default normalization, missing branch subset, or minimal runnable approximation while keeping the broad source-backed name. If the source includes multiplicative factors, quadrature weights, geometry factors, state-dependent arrays, table lookups, boundary branches, post-processing normalization, or unit/sign conventions, the package must do one of these:

- implement them in the operator or task-graph code;
- expose them as explicit inputs, configuration schema, state contract, or task-graph edge transform;
- narrow the title, relation direction, inputs/outputs, boundaries, and tests to the actually implemented subcase;
- record an evidence-bounded extraction gap instead of emitting an accepted package.

Tests must be strong enough to catch omission of source-specific factors that materially affect outputs. Small synthetic tests may be useful, but they cannot be the only evidence when a standard case, source-derived fixture, or direct source comparison would expose missing weights, normalization, branches, or state contracts.

For such cases:

- preserve the current source formula and convention unless the current source itself provides evidence for a correction;
- state units, normalization, sign convention, and validity domain as source-local assumptions or caveats;
- do not rescale, flip signs, or change constants merely to match another source family;
- do not claim two candidates are the same operator identity when their conventions or validation oracles differ materially;
- record cross-source mismatch as a review/governance risk in the engineering ledger when it is discovered, not as an extraction-time source repair.

## Candidate Classification

Classify every possible operator before writing files. For project/source-snapshot extraction, record this classification in the project-level candidate ledger. The ledger makes omissions reviewable; it is not a package-count or source-symbol coverage target.

Separate two concepts in engineering ledgers:

- Processing status: where the candidate is in the current run queue, such as `candidate_pending_deep_extraction`, `candidate_in_progress`, `emitted`, `merged`, `downgraded`, `rejected`, or `blocked`.
- Scientific/extraction disposition: what the candidate is after evidence review, using `ACCEPT_OPERATOR`, `SUPPORT_KERNEL`, `SOLVER_WORKFLOW_REWORK`, or `REJECT`.

Do not use `SOLVER_WORKFLOW_REWORK` as a placeholder for "not processed yet." A strong component or target-relation candidate can be `candidate_pending_deep_extraction` while its classification remains unset or provisional in a non-final report. In a final extraction report, no candidate may remain merely pending or in progress.

### ACCEPT_OPERATOR

Use only for implementation-backed candidates that pass all extraction-eligibility gates and deserve an operator package.

Meaningful but incomplete source may become `ACCEPT_OPERATOR` only through controlled completion. The source must already identify the physical quantity, core formula/objective, required data semantics, and evidence anchor. Completion may turn partial, legacy, project-coupled, side-effectful, or runtime-incompatible code into a standalone operator by preserving the evidenced computation and making the contract explicit. It cannot invent the science.

### SUPPORT_KERNEL

Use for useful helper kernels such as interpolation, coordinate conversion, mesh generation, central differences, source-point table construction, simple matrix helpers, file-format adapters, or plotting support.

Do not create a top-level scientific_operator package by default. Mention it as a dependency of a higher-level accepted operator or record the downgrade in the engineering ledger. In strict one-off operator-only delivery, summarize the downgrade in the final response.

Direct source parity does not upgrade a support kernel. A source-perfect special-function approximation, preprocessing coordinate map, interpolation helper, or generic numerical table lookup remains `SUPPORT_KERNEL` until it is bound to an independently reviewable physical operator identity.

### SOLVER_WORKFLOW_REWORK

Use for multi-step solvers or iterative workflows that have scientific identity but are not yet extraction-ready as emitted assets. This is a rework classification, not a stopping point.

Examples include equilibrium iteration loops, reconstruction workflows, optimization loops, coupled solver recipes, or workflows that still print, plot, mutate external state, or return only raw arrays.

First try to make the workflow itself an `ACCEPT_TASK_GRAPH`: define the black-box inputs/outputs, expose `task_graph.yaml`, and provide a runnable entrypoint that safely wraps or replays the composite computation. If the whole workflow is too coupled, recursively split it into package-worthy sub-boundaries before downgrading it:

- residual or error maps
- matrix, RHS, row, or operator assembly
- source, transport, collision, wave, loss, or boundary-condition terms
- state or time-step updates
- diagnostic forward responses
- closure, mesh/grid, or time-step contracts

Runtime limits, missing compilers, large compute needs, external input files, hard-to-build source, external solver libraries, generic interpolation calls, or common-block coupling are validation/operatorization blockers only. They do not justify dropping a source-backed workflow or replacing it with low-level kernels. Use controlled replacements, explicit state contracts, source-derived fixtures, standard-case captures, invariants, formulas, or boundary tests when direct source parity is unavailable.

Solver workflows require structured diagnostics before extraction freeze:

- `converged`
- `iterations`
- `residual` or equivalent error measure
- `failure_reason`
- side-effect-free execution

Without those, report the downgrade instead of emitting an operator package. A workflow downgrade is terminal only after checking whether the whole workflow can be a task graph and whether its internal graph contains package-worthy sub-boundary nodes; otherwise the extractor may hide real operators behind an over-broad rework label. When diagnostics or glue can be added without changing the scientific objective, the workflow may be upgraded into a task-graph or solver-operator candidate.

### REJECT

Use when evidence is too weak, the candidate is only glue, or the proposed operator would be invented rather than extracted.

## Candidate Operator Packages

Create language-profile implementation/test artifacts only for source-backed candidates that pass all
extraction-eligibility gates. Necessary science is anchored in code, YAML, docstrings and existing evidence;
D1 does not require `operator.md`. Formal pages are generated after D2 deduplication, correction and assembly,
only for retained new/changed assets before final review freeze. See [stage boundaries](stage_boundary_contract.md).
A documentation correction alone does not rerun science when code, inputs and relevant environment remain
attributable and unchanged; preserve old observations and repair the affected binding or comparison.

- the candidate maps to a concrete source path, symbol, line range, or cohesive source routine;
- the delivered scientific anchors make physical semantics, scientific role and physical relevance explicit;
- the candidate has stable typed inputs and outputs with machine-readable ASCII identifiers;
- the candidate has independent scientific computation meaning beyond utility glue;
- the implementation artifact is an implementation-backed extraction or adaptation whose behavior is proven by its own executed tests;
- the implementation artifact uses the Python profile or C profile unless the user explicitly changed the project language standard;
- the test artifact is an executable verification artifact, not merely a file-shape requirement;
- the producing LLM has run the tests in the available environment and recorded the command/result before final output;
- solver candidates expose structured convergence or failure semantics before extraction freeze.

Extraction dispositions and source labels are internal D1 decisions. Do not print them as headings in `operator.md`; reviewer-facing files should describe the scientific contract and evidence, not the owner workflow.

Candidate package emission has two gates:

- Definition and granularity gate: the candidate must satisfy the `scientific_operator` definition at the right scientific computation granularity.
- Implementation standard gate: the emitted package must be standalone, profile-conformant, evidence-anchored, explicitly contracted, independently runnable/buildable, and behavior-tested.

Controlled completion can help pass the implementation standard gate only when the source already fixes the scientific intent, core computation, data semantics, and validation oracle. It cannot rescue a candidate that fails the definition and granularity gate.

## Project-Level Extraction Report

A complete whole-project extraction accounts for every source-backed capability with candidates or evidence-based dispositions, plus a concise handoff summary outside asset directories. Reuse exact source-coverage and validation records; do not maintain duplicate narrative tables during implementation. Use `extraction_report_template.md` only at handoff.

Report granularity follows the accountability boundary of the extraction universe:

- one coherent extraction universe with one source-scope decision and candidate ledger: write one full sidecar set;
- several independent extraction universes in one user request: write one lightweight run index plus one full extraction report per universe;
- mixed but coupled materials: one report is acceptable only if the algorithm map, source manifest, candidate ledger, validation matrix, and blockers remain clearly partitioned by internal family/module.

The report must cover:

- source scope manifest and source-preservation stance;
- source-preservation/mutation audit, including validation shims outside the source tree;
- candidate ledger for accepted, merged, downgraded, and rejected candidates;
- reasons for choosing the accepted granularity;
- controlled completion and source repair decisions;
- source execution attempts, oracle choice, and numerical metrics or blockers.
- extraction completion status: complete only when no package-worthy candidate remains merely unprocessed.

The report is a global sidecar artifact. It does not replace scientific anchors, implementation files or tests; not a gap note inside the operator package root; and not a place to invent system-owned lifecycle metadata. A report-only or candidate-map-only run is discovery/partial output unless the user explicitly requested that phase.

## Required Operator Package Content

Each operator candidate package should explain the independent function-level capability, without
requiring the reader to know its source program, PFM node, or task-graph parents:

- stable title or code-like name
- one-line description and complete scientific/numerical definition
- normalized signature or callable shape
- concrete evidence references such as `relative/path.py:20-30` and relevant source symbols
- inputs and outputs with physical meaning, units, shape/scalar status, validity constraints, and device/geometry/coordinate context when relevant
- boundaries:
  - assumptions: facts treated as true by the calculation
  - use boundaries: when the operator should and should not be used
  - boundary conditions: encoded numerical or mathematical edge handling
- a relation-sensitive independently runnable validation using declared ports only
- validation and source basis: concrete source anchors plus the proof obligations a reviewer can expect from the test artifact
- controlled-completion notes under boundaries only for supplementation, non-obvious numerical choices, or reviewer-relevant limitations
- for controlled completions, the source-backed core, each Agent-supplemented repair, where the supplement appears, why it was needed, and any physics or data the agent explicitly did not infer

Keep D1 workflow dispositions in project records, not in the callable's scientific definition. Use
[documentation routing](operator_templates.md) for the later formal document and
[language profiles](language_profiles.md) for implementation/test files. No D1 gate depends on page headings.

## Evidence References

Accepted code-backed operators need concrete source anchors. Prefer source-root-relative file and line ranges:

```markdown
- `src/fields.py:222-307` (`compute_field_greens`): Green 函数公式、轴线处理和非有限值处理。
- `src/cross_sections.f:116-220` (`charge_exchange_xs`): 电荷交换截面表选择和速度单位处理。
- `src/rate_integrals.py:6-48` (`make_rate_coefficient`): 截面与目标分布的速度空间积分。
```

Do not write `Evidence Chunk IDs: not provided`. If a source index exposes real chunk ids, append them to the relevant line reference; do not create an empty standalone section.

## Test Requirements

The test artifact is the candidate producer's executable proof obligation.

The producing LLM must run the test file in the available environment before final output. If the tests fail, the candidate must be fixed or downgraded; do not present an unverified operator package as accepted output just because files exist.

Tests must explain and exercise the comparison logic:

- compare the extracted operator against the original source routine when it is safe to build, import, or call;
- when a standard full-program case exists, use it to anchor validation. Full-flow outputs validate the framework or a high-level task graph only when that task graph's declared output is the full-flow result; intermediate operator and internal-node tests may use source-derived golden fixtures captured from that case only when the capture command, source arrays, fixture provenance, and numeric metrics are recorded;
- do not treat final full-program outputs as direct parity for an intermediate operator unless the operator's output is actually the observed final output;
- when the original program cannot run, use this fallback priority:
  1. source-derived golden fixtures
  2. independently computed formulas or hand-checkable small examples
  3. numerical or physical invariants such as conservation, symmetry, monotonicity, boundedness, dimensional consistency, or convergence semantics
  4. boundary and failure behavior
- for solver operators, check convergence or non-convergence semantics, not only returned arrays;
- for controlled completions, test the supplemented behavior directly, such as repaired shapes, structured residuals, side-effect removal, invalid-input rejection, rank detection, or failure reason;
- when the candidate repairs a source crash, undefined branch, or boundary bug, state the source-runnable parity domain in the test header and add a separate test for the repaired path;
- for array operators, check representative values, shapes, and invalid-shape behavior;
- for physical transforms, check units, conserved quantities, monotonicity, symmetry, bounds, or other domain invariants when the source evidence supports them.
- record actual numerical metrics for each important output, not just pass/fail status or tolerance thresholds. Use `max_abs`, `max_rel`, and one aggregate norm when direct source parity or numerical fixtures are available.

The test artifact must not stop at:

- module imports
- public entrypoint exists
- docstring exists
- `assert True`

Record validation intent with the test or existing scientific anchor; bind executed commands, source identity,
actual per-output metrics and runtime conditions in the existing evidence record. Do not duplicate these facts
in a mandatory test-header format or an extra Markdown page. Use `direct_source_runnable` when the test actually
imports, compiles or subprocess-runs source and compares candidate values; compiled parity needs no new token.

If direct parity only covers a source-runnable subdomain because the original source crashes or is undefined on another path, do not invent a new source status. Keep `direct_source_runnable` only when the source is actually run, state the subdomain and correction in the scientific/evidence anchor, and test the repaired path separately.

## Hard Reject Rules

Reject or report as downgraded when the candidate is:

- a broad physics statement without concrete computation
- a non-physical software utility such as IO, plotting, parsing, logging, API, CLI, prompt, or database glue
- a helper too small to have independent operator identity
- a coordinate conversion, interpolation, derivative, mesh constructor, loader, plotter, or adapter with no clear scientific operator role
- a special-function approximation, preprocessing map, or generic numerical helper that is not bound to a named physics-facing operator contract
- a thin wrapper around source code with smoke tests only
- a candidate whose tests were not run successfully by the producing LLM before final output
- a workflow that lacks structured convergence or failure semantics
- an incomplete source fragment whose missing physics, coefficients, data tables, objective, normalization/sign convention, closure relation, or boundary condition would have to be invented by the agent
- a candidate whose tests only check importability or public entrypoint existence

Do not extract these as accepted operators:

- Fortran/IDL/Python file readers, namelist parsers, NetCDF/HDF5 writers, table loaders, logging helpers, plotting routines, command-line wrappers, or build scripts.
- Top-level simulation drivers when the output is a broad coupled workflow instead of a stable single computation contract.
- Subroutines whose main behavior is mutating common blocks, global module state, namelist state, random global reservoirs, or output files without an explicit input/output contract.
- Regression harnesses, batch scripts, sample input decks, and machine-specific compiler or cluster scripts.
- Generic math utilities with no scientific role in the extracted context, such as array fill/broadcast helpers, date helpers, path checks, or formatting helpers.
- Large workflow rework candidates without structured diagnostics: `converged`, `iterations`, `residual` or equivalent, `failure_reason`, and side-effect-free execution.

## Negative Example

A named equilibrium, reconstruction, transport, or solver iteration should not receive the `ACCEPT_OPERATOR` extraction disposition when it is only a wrapper around a broader source routine, has smoke-only or unexecuted tests, inherits print/plot side effects, and lacks structured convergence or failure semantics.

Classify the workflow as `SOLVER_WORKFLOW_REWORK` until those issues are resolved.
