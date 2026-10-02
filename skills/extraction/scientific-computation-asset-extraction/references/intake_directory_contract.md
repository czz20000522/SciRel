# ImportIntake Directory Contract

This is the D1 callable-package layout. The [stage boundary](stage_boundary_contract.md) owns the scientific
handoff; [artifact templates](artifact_template_pack.md) illustrate this layout without adding document gates.

## Callable units and minimum layout

An operator is an independently meaningful scientific or numerical mapping. A TaskGraph is a composite callable
whose YAML declares exact dependencies and scientifically necessary order/state semantics.

```text
<bundle_root>/
  operators/<operator_name>/
    scientific_operator.py | scientific_operator.c + scientific_operator.h
    test_scientific_operator.py | test_scientific_operator.c
  task_graphs/<task_graph_name>/
    task_graph.yaml
    graph.py
    test_task_graph.py
  program_framework_map.md
  extraction_report.md
  extraction_ledger.md
  asset_entry.py                     # required for the existing full_freeze loader contract
  configs/                           # only runtime-required shared schema
  docker/                            # optional legacy runtime-metadata location, not a Docker requirement
```

A project bundle contains at least one actual operator or TaskGraph. Do not discover assets from the presence of
`operator.md` or `task_graph.md`: both are optional inherited material in D1. An independent asset package has its
implementation/test and, for a graph, YAML at its root; it needs no artificial project reports. Python and C profiles
are defined in [language profiles](language_profiles.md).

Packages contain source-free callable code, necessary semantic anchors, tests and runtime-required data.
Source copies, probes, captured answers, logs, build outputs and private working notes remain outside the package.
Do not create another project directory below `operators/` or `task_graphs/`.

## Scientific contract without duplicate pages

The delivered code, YAML, docstrings and linked scientific records jointly identify the relation, every real port,
units/normalization, axes, applicability, boundaries, state ownership, source anchors and validation basis. Where
these facts are reliably recoverable, reference their exact location. State missing or ambiguous facts once in a
compact anchor. A filename or type alone does not define a physical quantity.

For TaskGraphs, YAML retains explicit external ports, node/edge bindings and one of the existing node kinds:
`scientific_operator`, `nested_task_graph`, `configuration`, `support_action`, `io_config_action`, or `blocked_gap`.
Every scientific node resolves to an emitted operator or permitted nested graph. Graph code schedules declared
assets and bounded glue; it does not hide a formula, normalization, scientific state update or source global.
Project context cannot supply omitted callable inputs or turn an incomplete package into a runnable asset.

Formal `operator.md`, `task_graph.md` or canonical scientific asset documents are produced after D2 comparison,
deduplication, correction and assembly stabilize the retained new/changed assets, before final review freeze.
Existing pages may be retained as provenance but their language, heading order or absence is not a D1 gate.

## Project context and validation

The existing root map, report and ledger carry source coverage, dispositions, evidence locators and the truthful
claim ceiling. During execution, keep minimal resumable records and reuse the scientific census rather than
maintaining duplicate tables. Write the concise delivery summary at handoff/freeze; formatting and narrative
polish do not establish source coverage. These files never form a separate callable asset.

`validate_import_intake_package.py` checks package shape, executable entry structure, TaskGraph bindings and
dependency closure, and generated-artifact exclusion. Structural success does not establish source fidelity,
scientific correctness or full source coverage; the D1 scientific gates and independent review own those claims.

For progress/reassembly `bundle_digest` bindings, use the pinned
`validate_capability_progress.py::compute_bundle_digest` before execution and when freezing the handoff.
This digest sorts relative POSIX **strings** case-sensitively, hashes the exact file bytes and excludes its declared
cache directories; native `Path` sorting on Windows is not equivalent. Do not substitute a ZIP hash, skill-bundle
manifest digest or another package format's identity. Keep generated artifacts outside the callable package.

For `full_freeze`, preserve the existing discovery-only `asset_entry.py` contract and validate it in the source-free
runtime. It must enumerate real packages and expose their callable/semantic anchors without requiring formal
Markdown. It cannot contain scientific relations, hidden state construction or project computation.

An attributable result with a bad path, assertion or stale packaging digest is repaired under the stage-boundary
evidence rule. Correcting such a defect does not automatically require repeating valid scientific computation.
