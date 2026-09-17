# Requirement: Standardized Scientific Asset Documentation

## Status and scope

- Status: Accepted by user direction
- Owner: SciRel maintainers
- Applies to: every public Operator and TaskGraph revision
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
- asset revision, SciRel implementation version/digest and exact dependency locks;
- one minimal executable example and expected observable result;
- verification scope, executable test paths, evidence ceiling and known limitations; and
- a public provenance summary, source kinds, public references and license status.

Public provenance must preserve useful lineage without exposing tenant IDs, admission/case/decision refs, candidate refs, source-project directories or another platform's internal owner model. Private governance evidence remains in `provenance/` and is joined only inside authorized release engineering. The absence of a public reference must remain explicit; it cannot be filled from a guessed project name.

The formal v1 shape is [`contracts/scientific-asset-document.schema.json`](../../contracts/scientific-asset-document.schema.json). Unknown fields fail closed. Contract evolution requires a schema version change or a backward-compatible documented extension; consumers may not infer missing scientific fields from names or source similarity.

## TaskGraph extension

A TaskGraph shares every common field and additionally declares:

- nodes, node kinds, stable dependency asset IDs and typed input/output ports;
- edges with endpoints, condition, transform, kind and required status;
- execution mode, observable ordering, branches, state ownership and failure propagation; and
- every controlled feedback loop's state, initialization, update order, continue/stop predicates, finite iteration-bound expression and nonconvergence result. The bound may reference a validated runtime input such as `maxiter`; it cannot be implicit or unbounded.

Ordinary data/control edges must be acyclic. A cycle is valid only through an edge explicitly typed `feedback` and a matching bounded feedback contract. Glue nodes may rename, pack, reshape or preserve declared data; they cannot hide interpolation, closure, discretization, geometry reconstruction or another scientific relation.

## Progressive disclosure

Asset documents are exact records. Agents must not load every exact record to discover a capability. A release must support:

```text
route records -> bounded summaries -> selected exact records and dependency closure
```

Route and summary projections may omit detail only when they retain `asset_id`, release snapshot binding and an exact-record digest. They never become an alternative scientific truth.

## Validation and acceptance

A document is eligible for catalog projection only when:

1. schema and semantic validation pass;
2. its Python callable imports from SciRel and its runtime signature matches;
3. its normalized source digest matches the declared implementation digest;
4. every dependency is present with an exact revision and digest;
5. TaskGraph ports, DAG/feedback and dependency bindings are valid;
6. its example executes against the bound SciRel source/wheel; and
7. declared tests exist and remain part of affected-test selection.

Current `catalog/examples/` is a dependency-closed 4-of-52 pilot, not a complete catalog. Missing documents remain a metadata gap and cannot be represented by generated placeholder science.

## Release decision

SciRel does not yet have an approved public distribution license. Every pilot document records `pending-human-decision`. Selecting a project license, reconciling input obligations and authorizing public distribution are human release decisions and are not performed by the validator, catalog builder or adapter.
