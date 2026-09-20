# Design: Framework-Neutral Catalog and Thin Adapters

## Decision

SciRel wheel code and standardized asset documents are the core. The catalog is a deterministic read-only projection for discovery and exact resolution. MCP, Codex, Claude Code, CodeFusion, CLI, cloud batch systems and hosted services are consumers or thin adapters; none owns, rewrites or duplicates scientific semantics.

## Catalog build boundary

`scripts/build_catalog.py` consumes a dependency-closed set of validated `scirel.asset-document.v1` records whose implementation versions match the requested catalog release, and writes a new immutable snapshot. It does not query CodeFusion, import source-project checkouts, fetch the network or read private review refs.

`--execute-examples` executes repository-owned example code for release verification. It is not an evaluator for untrusted uploaded documents; an adapter handling untrusted input must parse values against the exact contract and use its own sandbox rather than passing arbitrary example code to this command.

The snapshot contains:

- `release.json`: schema, release identity, honest coverage, progressive-disclosure order, partition hashes and root digest;
- `routes/*.jsonl`: small typed routing facets and exact-record refs;
- `summaries/*.jsonl`: bounded descriptions, projected input/output/default and identity fields, public callable, applicability, limitations and evidence ceiling;
- `records/<prefix>/<asset-id>.json`: exact standardized documents; and
- `reverse-dependencies/*.jsonl`: direct consumers used for impact and closure analysis.

The v1 release schema is [`contracts/scientific-catalog-release.schema.json`](../../contracts/scientific-catalog-release.schema.json). An output directory must be new; a failed build cannot replace the previous snapshot. `coverage.status=complete` is valid only when included and declared totals match. The pilot must remain `partial` with 14 included assets and 62 declared current assets.

The catalog does not participate in `import scirel` and does not import every module at startup. Exact runtime callable resolution occurs only after selection and must match the selected record's module, symbol, signature and implementation version. Exact content binding belongs to the enclosing catalog release, whose partition and root digests cover the record.

## Neutral adapter operations

Every adapter maps its protocol to the following logical operations. Operation names are a contract vocabulary, not Python asset IDs or mandatory transport names.

| Operation | Input | Result | Scientific mutation |
| --- | --- | --- | --- |
| `open_snapshot` | catalog location and optional expected root digest | immutable snapshot identity and coverage | none |
| `search_routes` | snapshot, typed facets, cursor and bounded limit | route records plus remaining bounds | none |
| `read_summaries` | snapshot and bounded asset IDs | capability summaries | none |
| `read_exact_records` | pinned snapshot and asset IDs | canonical documents and dependency refs | none |
| `resolve_callable` | exact record and installed distribution identity | module, symbol and signature match | none |
| `generate_call` | exact record plus caller-supplied values | reviewable Python call/code | none |
| `execute_call` | exact record, validated values and execution policy | typed result or declared failure | none |

`search_routes` cannot return `asset_unavailable` merely because its limit was exhausted. `resolve_callable` fails closed on catalog snapshot, implementation version or signature mismatch. `generate_call` cannot invent missing scientific inputs or silently select defaults not present in the exact contract. `execute_call` is optional; adapters that lack an approved execution boundary still support discovery and code generation.

## MCP mapping

An MCP server may expose the neutral operations as tools or resources, for example:

```text
scirel_catalog_open
scirel_catalog_search
scirel_catalog_read
scirel_callable_resolve
scirel_call_generate
scirel_call_execute   # optional
```

The server reads a pinned catalog snapshot and installed wheel. MCP transport metadata, sessions, user/project IDs, credentials, approvals, sandbox configuration and cloud job IDs belong to the adapter/platform layer and never enter asset documents or catalog identity.

For execution, the adapter must own authentication, authorization, input serialization, resource/network policy, timeout/cancellation, result materialization and audit. It passes only contract-valid in-memory inputs to the selected Python callable. An MCP response may report the selected `asset_id`, catalog root digest, implementation version and declared evidence ceiling; it may not claim new scientific validation or admission.

Codex and Claude Code can consume files directly or through MCP. A CLI can map the same operations to commands. A cloud batch adapter can resolve once, pin the wheel/catalog digests in a job specification, and execute in its managed environment. CodeFusion may add natural-language orchestration and product projections, but those are consumer behavior rather than SciRel catalog fields.

The implemented development slice is the SDK-free core in the separate `scirel_adapter` package, with the request/response surface defined by the [thin MCP adapter contract](../requirements/thin-mcp-adapter.md). Keeping it outside the `scirel` runtime package prevents discovery from triggering SciRel's public scientific imports. It verifies a catalog release and partitions before serving operations, reads route/summary/document projections, resolves only a selected callable, and materializes JSON-compatible results. A production MCP server remains a separate transport and execution-policy layer.

## Adapter compatibility

Adapters are conforming when the same catalog snapshot and request produce the same selected exact record and callable binding, subject to explicit search bounds. Cross-framework demonstration tests should therefore compare catalog root digest, asset ID, callable signature and scientific output, not UI wording or transport envelopes.

Adapters may add transport-specific errors, but they must preserve the core failure cause. They cannot:

- rename units or ports without a declared lossless mapping;
- insert scientific interpolation, closure, discretization or geometry conversion;
- use an unpinned `latest` document/wheel;
- treat import success as scientific applicability; or
- publish private provenance/governance fields.

## Current implementation and deferred work

Implemented in this slice:

- v1 asset and catalog release schemas;
- semantic/runtime/example validator;
- deterministic progressive catalog builder;
- dependency-closed 14-asset pilot; and
- SDK-free thin MCP adapter core for bounded discovery, documentation retrieval, callable resolution and invocation; and
- regression tests for missing units, private-field leakage, dependency closure, graph cycles, deterministic projections and adapter boundary enforcement.

Deferred until this contract stabilizes:

- documentation of the remaining 48 current assets;
- a production MCP transport/server or separately distributed adapter package;
- a source-free wheel plus catalog conformance run across multiple frameworks;
- catalog pagination/search indexing beyond the single pilot shard; and
- public distribution licensing and publication authorization.

## CodeFusion consumer handoff

The complete integration contract is maintained separately in [CodeFusion consumer contract](../integration/codefusion-consumer-contract.md). It records the release tuple, export-set parity, document entrypoints, callable/MCP surface, errors and current cross-project boundary mismatches without copying CodeFusion owner schemas into SciRel.

CodeFusion does not need to modify SciRel to consume this development contract. Its separate work item is:

1. export or confirm the exact admitted set and release binding used to authorize a complete SciRel catalog;
2. pin SciRel wheel SHA-256 and catalog root digest in its runtime image/configuration;
3. consume route/summary/exact projections without injecting session/project/workbench fields into them;
4. map selected `asset_id` to the exact installed callable and preserve evidence ceiling in user-facing reasoning; and
5. keep execution authorization, sandboxing, resources and result delivery in CodeFusion's own owner boundaries.

Until SciRel has complete documents and a human-approved license/release decision, CodeFusion should treat the pilot as development metadata, not a public catalog release.
