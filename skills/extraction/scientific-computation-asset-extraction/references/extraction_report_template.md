# Project Extraction Sidecars

`references/artifact_template_pack.md` and `assets/artifact_template_pack/` are the only canonical copy source for delivered layout, file names, and heading order. This file supplies detailed field guidance; if an example differs, the artifact template pack takes precedence.

Use these sidecars for whole-project, source-snapshot, or extraction-universe runs. Asset packages remain the primary deliverable. Sidecars explain the run; they do not replace `operator.md`, `task_graph.md`, implementation files, or tests.

## Run Layout

```text
<run_dir>/
  program_framework_map.md
  extraction_report.md       # executive summary
  extraction_ledger.md       # engineering detail
  configs/schemas/           # optional reusable schemas, never case values
  operators/<operator>/
  task_graphs/<task_graph>/
  docker/<project>/asset_runtime.md  # reusable fixed asset-runtime metadata
```

For multiple independent universes, instantiate one canonical bundle per universe. A lightweight run index may live above those bundles, but it is not part of any bundle. Validation harnesses, probes, golden-output parsers, runtime captures, and final gate JSON live in an external evidence directory. The machine-readable equation-web census and `capability_progress.json` also live there as discovery/checkpoint evidence; they are not formal asset kinds and must not contain case arrays. `program_framework_map.md` carries the human-readable equation-web projection beside Level 0 and Level 1.

## extraction_report.md

Audience: leadership, project owner, downstream reviewer triage.

Purpose: summarize what was delivered, what was validated, and what the top risks are. Do not put full candidate tables, line-by-line validation matrices, or detailed rework analysis here; point to `extraction_ledger.md`.

Required shape:

```markdown
# <project> scientific computation asset extraction report

## Executive Status
- delivery_status: <complete | discovery_only | incomplete>
- extraction_phase: <candidate_map_only | partial_extraction | final_extraction>
- completion_claim: <not_claimed | confident_no_remaining_valuable_candidates>
- primary_assets: <relation/operator/task-graph inventory count summary; never a progress numerator or denominator>
- asset_tree: `<relations path>`, `<operators path>`, `<task_graphs path>`
- support_assets: `<configs path>`, `<adapters path>`, `<capability_claims path>` when present
- engineering_detail: `extraction_ledger.md`
- framework_map: `program_framework_map.md`
- state_flow_map: `<path or none>`
- capability_progress: <external validated snapshot path>
- census_status: <provisional | frozen>
- progress_vector: <census maturity, extraction resolution, usable core closure, composition-edge closure, branch/domain coverage, target-path reassembly; overall only for a frozen census>
- active_frontier: <earliest unresolved node or edge per incomplete target path, summarized>
- closure_signal: <active | bounded_delivery | blocked_external | full_freeze, with claim ceiling, owner, evidence refs, and exact reopen condition>

<one paragraph summary>

## Scope Summary
- source_snapshot: <path, archive, commit, or label>
- documentation_basis: <manuals/docs used or none>
- standard_case_basis: <fixtures/data/oracles or none>
- source_mutation: <none or explanation>

## Delivered Asset Summary
- relations: <count and grouping; semantic only, not executable>
- operators: <inventory count and grouping; not progress>
- task_graphs: <inventory count and grouping; not progress>
- config_schemas_adapters_claims: <supporting asset summary or none>
- package_quality: <short statement>

## Validation Summary
- operator_tests: <summary>
- task_graph_tests: <summary>
- source_parity: <direct/fallback/blocker summary>
- cleanup: <cleaned or blocker>

## Coverage Summary
- <central equations/coupled systems and target paths discovered>
- <relation families and implemented directions covered>
- <high-value areas covered>
- <high-value areas intentionally not covered, summarized only>

## Leadership Risks
- <top 3-5 risks only>
```

Rules:

- Keep the report concise and summary-level.
- Use it to route readers to the assets, framework map, and ledger.
- A report alone is never completed extraction.
- Counts and historical prose are not current progress. The report must quote one validated external progress snapshot bound to the current source scope and bundle revision.
- Every current report must quote the snapshot's `closure_signal`; `active`, `bounded_delivery`, and `blocked_external` are finite status handoffs, while only `full_freeze` can support the final-extraction claim.
- `final_extraction` is allowed only when the census is frozen, the ledger shows no package-worthy candidate remains merely unprocessed, every target path is resolved, and the same-revision progress snapshot passes validation.

## extraction_ledger.md

Audience: producing agent, machine checker, AI reviewer, human technical reviewer.

Purpose: preserve engineering detail that should not bloat the executive report.

Recommended shape:

```markdown
# <project> extraction engineering ledger

## Delivered Candidate Assets
### scientific_operator packages
- `<path>/`

### scientific_task_graph packages
- `<path>/`

### scientific_relation anchors
- `<path>/`

### supporting assets
- `<path or none>`

## Equation-Centered Capability Web Reconciliation
| Equation anchor | Target paths | Scientific nodes | Glue edges | Local task-graph subwebs | Level 0/Level 1 evidence | Coverage conflict |
| --- | --- | --- | --- | --- | --- | --- |

Canonical leaves in this table are operators. A task graph is a local subweb containing named nodes and edges plus their order, branches, feedback, iteration, convergence, and state lifecycle; it is not a leaf.

## Progress Snapshot History
| Snapshot | Scope/census status | Source and target census | Progress vector | Active frontier | Bundle revision | Validator result |
| --- | --- | --- | --- | --- | --- | --- |

## Candidate Ledger
| Candidate | Source anchors | Status | Classification | Relation/direction | Output package | Rationale |
| --- | --- | --- | --- | --- | --- | --- |

## Rework Queue Or Terminal Non-Emitted Decisions

Use this section by phase:

- `partial_extraction`: list candidates still pending deep extraction or rework, with the next extraction action.
- `final_extraction`: do not leave a rework queue. List only terminal non-emitted decisions and downstream validation needs, with why they are not package-worthy candidates.

| Candidate | Source anchors | Status | Why not emitted | Next extraction or validation step | Required oracle |
| --- | --- | --- | --- | --- | --- |

## Framework Edge Closure Ledger
| Edge | Source anchors | From output | To input | State/config needed | Producer closure state | Implemented in | Why closure is sufficient | Probe/test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Controlled Completion Register
| Asset | Supplemented implementation work | Not inferred |
| --- | --- | --- |

## Source-Faithfulness Audit
| Asset | Cited source behavior checked | Required factors/branches/state contracts | Implementation or contract location | Test sensitivity |
| --- | --- | --- | --- | --- |

## Validation Matrix
| Scope | Command pattern | Result |
| --- | --- | --- |

## Cleanup Status
- <what was removed, what remains intentionally, or blocker>
```

Rules:

- Put detailed accepted/merged/downgraded/rejected decisions here.
- Put missing implementation, missing oracle, missing node/edge, missing framework-edge closure, and operatorization gaps here.
- Use the framework edge closure ledger for high-value Level 1 edges. Accepted closure states are emitted asset, controlled task-graph glue/kernel, post-extraction AI-completable glue from emitted contracts, configuration demand, validation-only need, terminal non-emitted decision, or extraction gap.
- Append semantic events to the ledger, but use the latest validated progress snapshot as the current-state projection. Historical final claims remain history after a new source or bundle revision appears.
- Put detailed controlled-completion boundaries here, but still annotate the actual code and asset contract.
- Put source-faithfulness checks here for package-worthy assets: formula terms, weights, normalization/post-processing, branches, boundary handling, state-dependent schemas, units, signs, and tests that would catch omissions.
- Put actual numeric deltas here or in test headers; do not use final full-flow outputs as fake parity for intermediate operators.
- Keep system-owned fields out: no review IDs, publication states, storage refs, host review metadata, package-format versions, or schema versions.

## program_framework_map.md

Required for whole-project/source-snapshot extraction. It is a sidecar evidence map, not an asset package.

Required layers:

- Level 0 Physics Mermaid: expert-readable physical mechanism overview.
- Equation-Centered Scientific Capability Web: central equations, scientific operator nodes, glue edges, local task-graph subwebs, target paths, material branches, and uncovered partitions.
- Level 1 Program Framework Map: source-anchored node ledger, edge/port ledger, visible input/output ledger, hidden/runtime state ledger, ledger-derived Mermaid, split decisions, and standard-case fixture plan.

Level 0 can fold details for readability. The equation-centered web preserves scientific leaf and local subweb identities. Level 1 anchors those identities to source and state evidence. None may contradict the others. Level 1 Mermaid must be derived from ledgers, not hand-written alone. If Level 1 becomes too dense, keep the readable framework map and add `state_flow_map.md` as the deep state/port ledger.

Production procedure:

- Produce Level 0 with `physics_framework_production_manual.md`, the equation-centered web and progress records with `scientific_capability_closure_and_progress.md`, and Level 1 with `source_framework_production_manual.md`; the required fields below are acceptance criteria, not a substitute for those procedures.
- Freeze the Level 1 normalized evidence package before drawing the framework map or comparing different AI runs.
- Project Level 1 nodes into operator, task-graph, assembly, support, or gap decisions with `asset_projection_decision_manual.md`. Framework membership alone does not determine package type.

Minimum Level 1 method:

- For each node, record scientific role, source anchors, visible inputs, visible outputs, hidden/runtime state read or written, `asset_projection`, and `ambiguity_status` (`resolved`, `needs_domain_ruling`, or `evidence_missing`).
- For each high-value edge, record `from.output -> to.input`, required state/config fields, whether the bridge is emitted asset, internal kernel, controlled task-graph glue, AI-completable glue, configuration/schema need, validation-only need, terminal non-emission, or extraction gap.
- For producer-to-public edges, split the contract into `producer terms -> normalization/scale -> boundary/post-transform -> public tensor`; record the scale fields, boundary indices, floor/sign policy, and one oracle for each stage. Never compare a raw producer capture directly with a normalized public array.
- For each primary path, probe whether the emitted contracts can compose from case/config inputs through state update and diagnostics without re-reading source implementation. A probe may be a small synthetic path, source-derived fixture, or documented demand; it must not replace package tests.

## state_flow_map.md

Use this optional sidecar when hidden state, global arrays, callbacks, mutable solver state, or multi-stage coefficient flow would make `program_framework_map.md` unreadable.

Recommended shape:

```markdown
# <project> state and port flow map

## State Variables
| State | Meaning | Shape/unit | Written by | Read by | Source anchors | Asset/contract location |
| --- | --- | --- | --- | --- | --- | --- |

## Node Ports
| Node | Input ports | Output ports | Hidden/runtime state | Configuration/schema fields | Emitted asset |
| --- | --- | --- | --- | --- | --- |

## Edge Contracts
| From | To | Data contract | Required adapter/glue | Gap label if missing |
| --- | --- | --- | --- | --- |
```

Do not turn case values, file paths, or default initialization decks into core state. Record them as configuration/schema fields unless they encode source-specific scientific semantics.

## Report Rules

- Do not inflate package count with reports, maps, checklists, or harnesses.
- Do not use the report to carry engineering detail that belongs in `extraction_ledger.md`.
- Do not hide shallow extraction behind a polished report.
- Do not leave package-worthy candidates as `candidate_pending_deep_extraction` in a `final_extraction` report.
- Do not leave source-runtime replay, probes, random-stream replay, golden-intermediate capture, file harnesses, or parity strengthening as final-extraction rework unless they expose an unprocessed scientific mapping.
- Do not modify source files to make `direct_source_runnable` true.
- Do not leave validation byproducts in final asset packages.
