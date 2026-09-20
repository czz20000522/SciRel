# Reviewer-Readable Asset Contract

Use this reference whenever an emitted operator or task graph is written or migrated. It teaches how to satisfy the
[scientific stage boundary contract](stage_boundary_contract.md); it does not own or expand the accepted product
contract. The emitted page is an internal contract for machine checks,
AI review, and expert handoff; it is not the final end-user page. Its reader has the bundle but must not need the
original source tree or the producing agent's memory.

## Operator Contract

An operator document must answer, before implementation is opened:

1. What physical quantity, numerical relation, or directed state transform is computed?
2. What compact equation, discrete rule, interpolation, stencil, reduction, or algorithm carries the source-specific meaning?
3. What exact callable is exposed, and what are all real named inputs and outputs?
4. For every port, what are its meaning, shape/axis order, units or explicit unit caveat, validity range, producer/consumer, and index convention?
5. Which source-specific normalizations, signs, table conventions, branches, endpoint rules, ghost rows, clipping rules, or failure semantics are preserved?
6. Which source lines support the claim, and what executed validation/oracle proves it?

Write a compact relation when it matters. For example:

```text
mean_charge = Trilinear[Z_table](log10(T_e), log10(n_0/n_e), log10(n_e*tau))
```

Then define the coordinate clamps, table axes, and output convention. Do not paste code or hide the relation behind a source-routine name.

Use machine-readable ASCII port names as list-item prefixes. Every port entry must state meaning, shape/axis order, units or a source-not-declared caveat, and important constraints. A document may refer to a returned mapping, but it must enumerate the named mapping fields used by downstream assets.

## Task-Graph Contract

A task graph is a black-box scientific capability, not a folder-level grouping. Its Markdown and YAML must jointly state:

1. The input state and final scientific result.
2. The non-interchangeable order, state feedback, branch, normalization, or ownership transfer that makes a graph necessary.
3. Every external input/output port, including axes, units, constraints, and state ownership.
4. Every node's role and whether it is an operator, nested graph, configuration, support action, or caller-owned glue.
5. Every required edge as `producer.output -> consumer.input`, including the carried state, transform, condition, and why reordering or omitting it changes the result.
6. Failure, empty-domain, convergence, and optional-port policies.

The YAML top-level `inputs` and `outputs` are the machine-readable black-box ports. Node ports and edge port names must be non-empty and must match the callable behavior exercised by tests. A graph whose YAML ports are empty while `graph.py` consumes real state is invalid.

## Task-Graph Documentation Style

A task graph uses the fixed `zh-CN` intake profile. It retains framework mapping, coverage, and
nested-graph relationship because these define the owned framework slice. Its page must
nevertheless be a complete black-box contract: a reader can call the graph from declared inputs
without learning the original program call order. Publish a separate language only after review;
do not mix translations in one `task_graph.md`.

`program_framework_map.md` uses the same single-language rule. It is the sole project-level
authority for PFM boundaries and cross-node edges; it is not an extra prerequisite hidden inside
an operator page.

## Operator Documentation Style

An extracted operator is an independent function-level scientific capability. Its `operator.md`
uses the fixed `zh-CN` intake profile. Do not mix translations, bilingual headings, reviewer
notes, project/PFM mapping, parent task graphs, or source-program call order into the function
reference. The title, summary, callable, ports, scientific definition, behavior, and validation
basis must stand on their own for an AI or expert reviewer who has neither the source tree nor the
project map. A later SciRel candidate may use this material as provenance while preparing the canonical exact
document, but extraction does not generate or publish the asset site.

Use the MATLAB-like reference order defined in `artifact_template_pack.md`: syntax, description, input
arguments, output arguments, scientific/numerical definition, behavior and boundaries, and
validation/source basis. A later publication service may render one reviewed semantic contract
as separate `zh-CN` and `en-US` pages. Translation must preserve the callable, ports, units,
boundary behavior, and validation claim; it is not an extraction-time approval or release action.

Never use language labels or migration prose as content: `中文审查说明`, `English reviewer note`,
`input_detail_1`, `output_detail_1`, `return_value`, `Source-backed operator`, `See the package
implementation entrypoint`, and equivalent phrases are forbidden.

## Known Gaps Must Be Visible In The Document

Whenever a claim exceeds the extraction acceptance ceiling — `scientifically_corrected`
candidates, reassembly-vs-source divergences registered instead of reproduced, repairs awaiting
later work, or unresolved correctness questions — the `operator.md` / `task_graph.md` itself must
carry a dedicated `## 已知缺口与待确认事项（Known Gaps and Open Questions）` section naming each
bounded claim, its evidence anchor, and the exact missing evidence or decision. Ledger entries and
evidence sidecars do not substitute for this in-document declaration; a downstream reader who never
opens them must still see the gap. This section records L1 evidence and does not initiate expert
review or assign integration lifecycle state. A document without this section must not contain any
claim beyond `source_fidelity_verified`.

For a scientific correction this section is not only a deferral. It must explain the inspected error,
the evidence that establishes it, what changed and why, the affected domain/dependencies and independent
validation limits. Follow
[scientific correction](../../scientific-relation-implementation/references/scientific-correction.md).
A generic request to “check this later” is not a diagnostic gap record. If D1 cannot complete a
justified repair within its evidence and scope, preserve the observed behavior and record the defect,
claim ceiling, missing basis, and next action explicitly. Do not require a fabricated source citation;
attribute the defect only to the implementation actually inspected.

## Audience Split: The Ledger Is Agent-Facing, The Documents Are Human-Facing

`extraction_ledger.md` is append-only bookkeeping for extraction agents: event history, digests,
gap tracking, and cross-references. It is not a human-facing document, and no reader may be
required to learn anything from it. The human-facing artifacts are the `operator.md` and
`task_graph.md` documents (plus `program_framework_map.md` at project level). Every effective
fact a reviewer, downstream consumer, or expert needs must be present in the document itself:
the complete contract, the claim ceiling, the applicability domain, declared failure behavior,
the validation basis in summary form, and every `## 已知缺口与待确认事项（Known Gaps and Open Questions）`
entry. A fact that exists only in the ledger or evidence sidecars is not disclosed to any human
reader and is a contract defect, not a footnote. The gap section above is part of the L1 contract; any
later expert action or workflow transition is owned by the SciRel integration lifecycle.

## Review Decision

If a reviewer must open implementation or source merely to learn an operator's callable, real ports, scientific relation, or configuration/branch assumptions, the package has a `contract_gap`. If that prevents source-free composition, revise it before D1 freeze.
