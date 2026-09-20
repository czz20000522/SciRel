# ImportIntake Directory Contract

`assets/artifact_template_pack/` defines the only package layout, file names, and heading order.
This document defines how that layout becomes a structurally valid extraction bundle. Do not create another template from it.

## Callable Units

Only callable assets freeze as independent package units:

- an `operator` is an atomic reusable scientific or numerical mapping;
- a `TaskGraph` is a composite callable asset whose YAML binds exact operators or nested TaskGraphs.

Both have a complete black-box contract. A TaskGraph remains distinct from an operator because it owns ordered
composition and exact dependency bindings, but a source-free consumer may invoke either through the same
callable-asset surface.

## Project Context

For project extraction, these root files are immutable project context:

```text
program_framework_map.md
extraction_report.md
extraction_ledger.md
configs/
docker/
```

They explain project scope, asset relationships, candidate decisions, runtime evidence, and gaps.
They bind the project commit and may be shown from any asset case in that project. They never form a
separate callable package or whole-project completion shortcut.

## Project Bundle Layout

```text
<bundle_root>/
  operators/                         # present when the project emits operators
    <operator_name>/
      operator.md
      scientific_operator.py | scientific_operator.c + scientific_operator.h
      test_scientific_operator.py | test_scientific_operator.c
  task_graphs/                       # present when the project emits composite assets
    <task_graph_name>/
      task_graph.md
      task_graph.yaml
      graph.py
      test_task_graph.py
  configs/                           # optional project context
  docker/                            # optional project context
  program_framework_map.md
  extraction_report.md
  extraction_ledger.md
  asset_entry.py                     # optional path loader; no scientific logic
```

A project bundle contains at least one operator or TaskGraph package. Do not add a second project
directory under `operators/` or `task_graphs/`. Package directories contain only their callable
contract, implementation, runtime-required data, and tests. Source copies, reports, validation
logs, generated caches, and private probes stay outside the formal package tree.

## Standalone Asset Layout

An independent operator or TaskGraph ZIP has the asset package at its root. It contains no empty
project reports, framework map, ledger, or artificial project folder. It uses the same Chinese
contract, implementation, test, and structural checks as the corresponding package in a project
bundle.

## Contract Rules

- Every Intake Markdown document declares `language: zh-CN`.
- `operator.md` uses the heading order from `artifact_template_pack.md`. It contains no project
  membership, parent TaskGraph, workflow state, storage reference, or run history.
- `task_graph.md` and `task_graph.yaml` use the heading and schema rules from
  `artifact_template_pack.md`. The graph has explicit external ports and only uses
  `scientific_operator`, `nested_task_graph`, `configuration`, `support_action`,
  `io_config_action`, or `blocked_gap` node kinds.
- Scientific formulas and numerical mappings belong to operators. `graph.py` only validates
  ports, dispatches declared assets, schedules branches or feedback, maintains explicit state,
  and collects diagnostics.
- A TaskGraph node that carries scientific or numerical meaning must have an exact `asset_ref` to
  an emitted operator or same-primary-node nested TaskGraph. Do not introduce `internal_kernel`,
  `solver_update`, or `diagnostic_response` as alternate executable asset kinds.
- Project context explains why assets relate. It never supplies omitted operator inputs or turns an
  incomplete package into a callable asset.

## Validation Boundary

`scripts/validate_import_intake_package.py` checks the Chinese document contract, package shape,
TaskGraph structure, exact asset references, and generated-artifact exclusion. It is a structural
gate only. Runtime behavior, scientific meaning, source parity, and oracle strength require their declared
extraction tests and evidence; this structural validator proves none of them.

The validator operates on the immutable package tree selected for the Intake. It must not infer
meaning from a project report, host path, source tree, storage location, or producer prose.
