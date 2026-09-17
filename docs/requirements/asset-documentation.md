# Requirement: Standardized Scientific Asset Documentation

## Status and scope

- Status: Accepted by user direction
- Owner: SciRel maintainers
- Applies to: every public Operator and TaskGraph
- Consumers: catalog builders, human maintainers, Codex, Claude Code, CodeFusion, MCP adapters, CLI and cloud execution platforms

SciRel must describe each public scientific asset independently of any agent framework. A document is a versioned scientific and callable contract, not a copy of CodeFusion review records, source-project layout, an MCP tool definition, or marketing documentation.

## Required common contract

Every document must bind one stable scientific `asset_id` and declare:

- kind, bilingual title, bounded summary, taxonomy and aliases;
- scientific relation, implemented direction and definition;
- model, assumptions, geometry, coordinates and boundary/closure;
- named input/output ports with meaning, units, shape, dtype, required/default status and constraints;
- applicability preconditions, supported scope and explicit exclusions;
- invalid-input, runtime-failure, nonconvergence and partial-result semantics;
- stable Python module, symbol and exact signature;
- current SciRel implementation version and stable dependency asset IDs;
- one minimal executable example and expected observable result;
- verification scope, executable test paths, evidence ceiling and known limitations; and
- a public provenance summary, source kinds, public references and license status.

Public provenance must preserve useful lineage without exposing tenant IDs, admission/case/decision refs, candidate refs, source-project directories or another platform's internal owner model. Private governance evidence remains in `provenance/` and is joined only inside authorized release engineering. The absence of a public reference must remain explicit; it cannot be filled from a guessed project name.

The formal v1 shape is [`contracts/scientific-asset-document.schema.json`](../../contracts/scientific-asset-document.schema.json). Unknown fields fail closed. Contract evolution requires a schema version change or a backward-compatible documented extension; consumers may not infer missing scientific fields from names or source similarity.

## TaskGraph extension

A TaskGraph shares every common field and additionally declares:

- nodes, node kinds, stable dependency asset IDs and typed input/output ports;
- edges with endpoints, condition, transform, kind and required status; every feedback edge also has a stable `feedback_id`;
- execution mode, observable ordering, branches, state ownership and failure propagation; and
- every controlled feedback loop's state, initialization, update order, continue/stop predicates, finite iteration-bound expression and nonconvergence result. The bound may reference a validated runtime input such as `maxiter`; it cannot be implicit or unbounded.

Ordinary data/control edges must be acyclic. A cycle is valid only through an edge explicitly typed `feedback` and exactly one bounded feedback contract with the same stable ID. Duplicate IDs, feedback edges without contracts and contracts without edges fail closed. Glue nodes may rename, pack, reshape or preserve declared data; they cannot hide interpolation, closure, discretization, geometry reconstruction or another scientific relation.

## Progressive disclosure

Asset documents are exact records. Agents must not load every exact record to discover a capability. A release must support:

```text
route records -> bounded summaries -> selected exact records and dependency closure
```

Route and summary projections may omit detail only when they retain `asset_id`, a path to the canonical record and the enclosing release snapshot binding. They never become an alternative scientific truth. The release manifest binds every record partition by digest once; route, summary and dependency entries do not repeat per-asset content hashes.

## Validation and acceptance

A document is eligible for catalog projection only when:

1. schema and semantic validation pass;
2. its Python callable imports from SciRel and its runtime signature matches;
3. every dependency asset ID resolves to the canonical document in the same release;
4. TaskGraph ports, DAG/feedback and dependency bindings are valid;
5. its example executes against the bound SciRel source/wheel;
6. declared direct tests exist and remain part of affected-test selection; and
7. the catalog release manifest binds the complete record and index partitions by digest.

There is one current canonical document per public `asset_id`. Git and immutable catalog releases retain history; maintainers do not create parallel snapshot documents or require repeated confirmation merely because source bytes changed. `implementation_version` states which SciRel implementation the current contract describes. A scientific contract change is handled through normal compatibility, review and release history rather than a document-local hash.

Current `catalog/examples/` is a dependency-closed 4-of-52 pilot, not a complete catalog. Missing documents remain a metadata gap and cannot be represented by generated placeholder science.

## Release decision

SciRel does not yet have an approved public distribution license. Every pilot document records `pending-human-decision`. Selecting a project license, reconciling input obligations and authorizing public distribution are human release decisions and are not performed by the validator, catalog builder or adapter.
