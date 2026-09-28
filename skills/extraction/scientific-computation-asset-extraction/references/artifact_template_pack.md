# Artifact Template Pack

This pack is the maintained template and operating method for the D1 boundary in the
[scientific stage contract](stage_boundary_contract.md). Copy `assets/artifact_template_pack/`; do not invent
another layout or heading order. This reference defines the observable L1 intake shape; it does not authorize later
normalization, expert approval, or release.

## Authority

Use this order when instructions overlap:

1. explicit user delivery requirements;
2. the shared scientific stage boundary contract;
3. this pack for the current layout, file names, cardinality, heading order, and working method;
4. framework production manuals and `scientific_operator.md` for scientific decomposition and evidence quality;
5. `intake_directory_contract.md`, validators, and explanatory examples as implementation aids.

Record every user-required format deviation in `extraction_ledger.md` with its reason and bundle impact.

## Canonical Single-Project Layout

Instantiate one bundle per project or independent extraction universe:

```text
<bundle_root>/
  operators/
    <operator_name>/
      operator.md
      scientific_operator.py
      test_scientific_operator.py
  task_graphs/
    <task_graph_name>/
      task_graph.md
      task_graph.yaml
      graph.py
      test_task_graph.py
  configs/                         # optional reusable schemas
    schemas/
      <schema_name>.md
  docker/                          # reusable asset-runtime metadata
    <project_name>/
      asset_runtime.md
  program_framework_map.md              # project extraction context
  extraction_report.md                  # project extraction context
  extraction_ledger.md                  # project extraction context
  asset_entry.py                   # required at full_freeze; discovery-only, no scientific logic
```

Rules:

- A project bundle contains at least one of `operators/` or `task_graphs/`. Their direct children are packages; do not add another project-name directory.
- Each operator package may freeze into project staging as soon as its own contract, implementation, exact
  dependencies, provenance, and extraction evidence close. Project-sidecar or sibling-candidate incompleteness does
  not delay that internal freeze; the project extraction remains incomplete until whole-project `full_freeze`.
- A TaskGraph package freezes only after the exact operator/nested-graph versions it binds and its local
  composition evidence are ready. It does not wait for unrelated project candidates before project staging.
- Preserve source-backed specialization. Cross-project generalization, deduplication, public namespace
  design, and library refactoring are not template-completion requirements.
- `program_framework_map.md`, `extraction_report.md`, `extraction_ledger.md`, `configs/`, and `docker/` are project context. They bind the project commit and are never standalone candidate packages.
- Create the root `extraction_report.md` once the project scope, first frontier, and first validated snapshot
  are available, with an honest `active` or other current claim ceiling. Update it from the latest validated snapshot as the run advances;
  complete the root report before requesting final freeze review, not after declaring `full_freeze`.
- Run-local process notes and private worker drafts are resumable working material outside frozen candidate
  packages. Editing them does not invalidate already bound source, candidate, or execution evidence unless a
  cited claim or digest-bound input changes. The coordinator alone integrates their proven conclusions into
  shared sidecars and creates a new bound snapshot when the evidence or current claim changes.
- A new-project `bounded_delivery` report may include a `Deferred Source Capability Register` section in
  `extraction_report.md`. Each row records only a source-anchored capability locator, likely target path or
  scientific family, current disposition (`deferred_source_capability`, `support_or_non_candidate`, or
  `unresolved`), and an explicit reopen condition. These rows are internal capability-repository metadata; they do
  not create an operator, TaskGraph, package directory, or `asset_ref`, and are not sent as expert-review items.
- A package contains only its contract, implementation, runtime-required package data, and tests. No package-local reports, checklists, validation JSON, probes, or source copies.
- Python is the default operator profile. Use the C profile only when source-faithful delivery requires it and record the reason in the ledger.
- `configs/schemas/` declares identifiers, types, shapes, axes, units, ranges, default policies, and owners. Concrete case values belong to calls or outbound glue, never hidden global configuration.
- Scientific relations are recorded in the framework map, package contracts, and ledger. Do not add root `relations/`, `adapters/`, or `capability_claims/` directories.
- Runtime adapters required by an asset live inside that package or graph; outbound-only adapters stay outside the formal bundle.
- `docker/<project_name>/asset_runtime.md` records the reusable fixed `asset_runtime` image/digest and source-free test commands. It must require a read-only bundle, no source mount, and no host-specific paths. Project-specific `source_runtime` Docker configuration stays with the external validation/source workcopy and is never reused as the asset runtime.
- Final gate JSON, source probes, golden-output parsers, captured runtime state, and large oracle files are temporary external evidence attachments. Generate one bounded final set at extraction freeze, retain it only through the extraction gates that consume it, write its durable conclusions into the formal contracts/report/ledger, then retire the raw attachments under `evidence_persistence_boundary.md`.
- Do not add a root README, catalog, counts file, duplicate template, or backup copy.

### Uniform frozen-bundle entry

For `full_freeze`, provide root `asset_entry.py` with
`load_asset_bundle(root=None)` and an
`AssetBundle` exposing `list_assets`, `describe_asset`, `find_assets`, `operator_callable`,
`task_graph_callable`, and `asset_callable`. The operator resolver returns the callable declared
by the package syntax (or an explicit `callable_name`); the task-graph resolver defaults only to
`run_graph`. Root `load_operator` and `load_task_graph` are convenience aliases. This contract
standardizes extraction-bundle loading only; it is not a generalized public API and never upgrades
an unproved scientific relation or source-parity claim. Active, bounded, or otherwise incomplete
working snapshots may omit the entry; the final frozen bundle may not. Execute
`scripts/validate_asset_entry.py` in the fixed source-free asset sandbox before deriving
`closure_signal.kind=full_freeze`.

## Canonical Operator Reference Layer

An intake package uses the fixed `zh-CN` profile, declared in YAML front matter as `language: zh-CN`. Do not put translations or public documentation in a candidate package.

An operator reference covers the information a reader must understand before opening implementation:

- title and concise summary;
- callable syntax, description, and scientific/numerical definition;
- input/output argument meaning;
- one relation-sensitive validation case in the bound tests or evidence;
- supported, excluded, and failure boundaries;
- validation conclusion and evidence meaning.

Equations, callable names, identifiers, signatures, shapes, units, source paths, metrics, and YAML keys retain the same value across language editions. Do not add language labels such as `中文审查说明` or `English reviewer note`. Do not include PFM membership, parent task graphs, source-program call order, or recommended composition in an operator reference; those are project/catalog relationships, not callable prerequisites.

These package-document requirements apply to the emitted bundle before `full_freeze`. During implementation,
retain the source version and scope, physical definition, necessary input/output meanings, and validation anchors;
the finished `operator.md` and `task_graph.md` may be generated after code and tests stabilize. Separate agents
may draft distinct package pages in parallel, with one coordinator integrating them against the exact code digest.
The package contract must then be understandable before a reviewer opens implementation or source. A reviewer must
be able to identify the scientific relation, callable signature, every real input/output, axes/units/constraints,
source-specific normalization/index/branch/boundary rules, evidence anchors, and validation route from the contract
alone. Never use placeholders or deferrals such as `input_detail_1`, `output_detail_1`, `return_value`, `arguments`,
`See the package implementation entrypoint`, or `Source-backed operator`.

One asset has one canonical internal scientific contract page; do not maintain a skeletal summary beside it or
turn the extraction contract into a usage tutorial. Write the internal page like
a compact scientific contract: first state the physical problem and result, then the relation and assumptions,
then the callable contract and its validation basis. Put source paths, lineage, oracle construction and
machine-readable audit metadata in `验证与溯源`, where it supports extraction audit without being required to
understand the science.

The field descriptions are a hard semantic gate, not a documentation decoration. Every port description
must name the physical or numerical quantity, explain its role in the relation, and state the applicable
unit/normalization, axes/index order, ownership/lifecycle, and relevant domain or boundary rule. Reusing
one generic description for several fields does not satisfy that contract even when headings and
shape/unit keywords are present. An unresolved port is a declared gap, not an implicit caller
responsibility.

For an operator with a formula, discrete relation, interpolation, matrix/stencil, update rule, or diagnostic definition, state the compact equation, algorithm, or pseudocode and define the symbols that matter for configuration or review. Do not reproduce implementation line by line. For a task graph, state the black-box relation, real external ports, stateful/order-sensitive edges, branch/feedback/failure policy, and the distinction between scientific nodes, nested graphs, and caller-owned glue. Its YAML is the machine-readable projection of that same contract, not a decorative node list.

Use these exact top-level headings and order for an operator.

| `language` | Required headings |
|---|---|
| `zh-CN` | `语法` → `说明` → `输入参数` → `输出参数` → `科学或数值定义` → `行为与边界` → `验证与溯源` |

Task graph:

| `language` | Required headings |
|---|---|
| `zh-CN` | `概述` → `框架映射` → `科学目的` → `输入` → `输出` → `组成` → `行为与边界` → `验证与溯源` |

A task graph retains its framework mapping because it is the executable composition inside one framework slice. An operator never inherits that project relationship as part of its standalone contract.

## Standalone Asset Package

An independent operator or TaskGraph may be imported without project context. Its ZIP root is the
asset package itself: `operator.md` plus its implementation and test, or `task_graph.md`,
`task_graph.yaml`, `graph.py`, and its tests. Do not add empty project sidecars or an artificial
framework map. The same Chinese contract and structural checks apply.

## Canonical Framework-Map Layer

`program_framework_map.md` also declares `language: zh-CN`. It is a project-level explanation, not an operator reference: it owns framework-node boundaries, cross-node edges, and the reverse PFM-to-asset projection.

Every task graph declares exactly one primary PFM node, a coverage value (`full`, `slice`, or `support`), and any related PFM dependencies. A nested task graph must declare that same primary node; related PFM nodes never permit cross-node nesting. The project framework map contains the reverse PFM-to-task-graph and PFM-to-operator projection ledgers. An operator remains complete without any PFM or parent-graph statement in its own package.

## Required Cardinality

| Item | Cardinality | Rule |
|---|---:|---|
| `program_framework_map.md` | exactly 1 for a project bundle | Project nodes and cross-node dependencies. |
| `extraction_report.md` | exactly 1 for a project bundle | Extraction scope, validation summary, risks, and bounded claim. |
| `extraction_ledger.md` | exactly 1 for a project bundle | Candidate decisions, gaps, detailed validation, deviations, and terminal reasons. |
| Python operator core files | exactly 1 each | `operator.md`, implementation, and test; extra data only when runtime-required and documented. |
| task-graph core files | exactly 1 each | Contract, YAML, entrypoint, and test; extra modules/data only when runtime-required and documented. |
| config schemas | 0 or more | Reusable declarations only; no scenario payloads. |
| asset-runtime metadata | exactly 1 | `docker/<project_name>/asset_runtime.md`; reference the reusable fixed runtime without duplicating it. |

## Instantiation

1. Copy `assets/artifact_template_pack/` to the bundle root.
2. Rename `OPERATOR_NAME`, `TASK_GRAPH_NAME`, `PROJECT_NAME`, and `config_schema.md`; duplicate only package directories required by the framework map.
3. Replace every angle-bracket placeholder. Delete unused optional files/directories.
4. Preserve heading order. Add detail under existing headings before adding a new heading.
5. Write newly proven capability/state/oracle evidence and a truthful current root report as work advances;
   defer only recomputable counts, digests, and roll-ups until their inputs are stable.
6. A stub is not a candidate. Replace every `NotImplementedError`, execute package tests, and write actual results into test headers.

## Bundle Inspection Order

1. `program_framework_map.md`: project boundary, nodes, edges, and split decisions;
2. `extraction_ledger.md`: candidate decisions, gaps, deviations, and open risk;
3. high-risk or changed packages: contract, source anchors, implementation, and tests;
4. `extraction_report.md`: executive validation and bounded completion claim;
5. external final-gate evidence only when a claim needs machine replay.

## Validation Sequence

During extraction, run only changed-package tests and directly dependent graph tests. At delivery freeze:

1. run all package tests in the reusable asset runtime;
2. run `scripts/validate_import_intake_package.py <package-root>` on package roots only;
3. run `scripts/validate_source_free_bundle.py <bundle_root> --require-docker`;
4. run the full source-free composition gate once;
5. remove generated caches/build artifacts and produce one bounded final evidence set outside the bundle;
6. before the final claim, reconcile the root report and ledger with the validated snapshot and final evidence;
   after all evidence-consuming gates finish, record final metrics and cleanup receipt, then retire only
   superseded run-owned evidence/scratch/container resources under the evidence-persistence boundary.

Format validation does not prove scientific correctness; source parity does not permit a format deviation.
