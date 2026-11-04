# Artifact Template Pack

Use the existing templates only when creating an L1 package or project handoff. The
[stage boundary](stage_boundary_contract.md) defines responsibility and the
[intake directory contract](intake_directory_contract.md) defines required executable structure. Templates are
examples, not a requirement to copy every file or preserve prose headings.

## Instantiate only consumed artifacts

1. Create one bundle per declared source universe. Its `operators/<id>` and `task_graphs/<id>` children are
   callable packages; no second project directory is needed inside either tree.
2. Copy only the implementation/test skeletons and graph YAML needed for actual candidates. Use
   [language profiles](language_profiles.md) for Python/C files. Remove unused placeholders.
3. Preserve scientific anchors in code, YAML, docstrings or existing scientific records. Add nonrecoverable units,
   assumptions, conventions, provenance and evidence locators once. Missing semantic facts remain gaps; filling
   a document template does not resolve them.
4. Maintain minimal run-local continuation notes and source coverage records. Derive the final concise root
   report/map/ledger from stable evidence at handoff. Their current claim must agree with the bound snapshot;
   do not recalculate science to update prose or counts.
5. Preserve any existing `operator.md` or `task_graph.md` as optional provenance. Do not generate new formal
   pages at D1. D2 eliminates duplicates, repairs and assembles before retained new/changed assets receive
   the canonical exact document for final review. [Writing guidance](operator_templates.md) explains that route.

Candidate packages hold only callable code, necessary anchors, tests and runtime-required data. External source
workcopies, probes, raw captures, source-oracle parsers and final-gate records remain in owned evidence locations.
Keep their durable provenance and observed metrics discoverable; do not delete evidence still needed by D2 or
review. Follow [evidence persistence](evidence_persistence_boundary.md) when retiring it.

An operator can stage once its own scientific contract, implementation, exact dependencies, provenance and
validation close. A graph additionally requires every bound dependency and its composition evidence. Neither
waits for unrelated candidates, and neither constitutes whole-project `full_freeze`.

## Frozen-bundle entry

For the existing `full_freeze` interface, root `asset_entry.py` provides `load_asset_bundle(root=None)` and an
`AssetBundle` with `list_assets`, `describe_asset`, `find_assets`, `operator_callable`, `task_graph_callable`, and
`asset_callable`. The operator resolver uses the exposed callable or explicit `callable_name`; the graph resolver
defaults to `run_graph`. `load_operator` and `load_task_graph` are convenience aliases.

This entry discovers code-backed packages and semantic anchors, without Markdown as an enumeration prerequisite.
It is not a generalized public library API and contains no scientific calculation or hidden state recovery.
Validate it with `scripts/validate_asset_entry.py` in the source-free runtime and bind the actual result to the
bundle identity. Active or bounded snapshots may omit it; a full-freeze bundle may not.

## Project and graph records

Use [project sidecars](extraction_report_template.md) when producing the actual handoff. Source coverage,
scientific relationships, candidate/disposition mapping and evidence must be complete; a particular prose shape
or duplicate Mermaid/table projection is not evidence. Point to an existing exact record instead of rewriting it.

Retain graph YAML's declared external ports, exact dependencies, order/state/branch/failure semantics and existing
framework bindings. An operator does not inherit project membership as a callable prerequisite. Source-backed
specialization is valid; D1 does not need to generalize names or deduplicate against the library.

Runtime metadata identifies the authorized reproducible runtime, source-free execution restrictions and commands.
The legacy `docker/` template path does not prescribe an engine. Use the task's actual approved runtime and keep
host-specific paths outside shared templates. Case values belong to explicit calls, not hidden global configuration.

## Select validation by impact

During production, validate the changed candidate and affected dependencies. At delivery, verify complete source
coverage, source comparisons and functional reassembly at the declared scope; reuse still-valid exact evidence.
Run the structural dependency-closure and source-free gates and the loader check required by the claimed boundary.
The governing science and claim choose the checks; a green process status or format validator does not prove them.

For unchanged code, inputs and runtime-relevant conditions, repair mechanical wrappers, assertions, paths and
packaging bindings with a traceable supplemental record under [stage boundaries](stage_boundary_contract.md).
Preserve the original observation and failed wrapper; rerun only the affected comparison/check. Do not relax
tolerances, rewrite immutable records or substitute a new seal for missing historical independence.
