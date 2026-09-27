# Requirement: Thin MCP Adapter Contract

## Status and scope

- Status: development contract
- Owner: SciRel adapter maintainers
- Input authority: one pinned `scirel.catalog-release.v1` snapshot and its canonical asset documents
- Runtime authority: the installed SciRel distribution named by each document's `implementation_version`

This contract defines the smallest framework-neutral core that an MCP server may wrap. It is provided by the lightweight `scirel_adapter` package, separate from the `scirel` scientific runtime namespace so discovery does not import scientific modules. It is not an MCP transport implementation and does not depend on an MCP SDK. The core translates bounded catalog discovery, asset documentation retrieval, callable binding and invocation/result materialization. It does not own or copy scientific semantics.

## Operations

The core accepts exactly four operation envelopes:

| Operation | Request fields | Result |
| --- | --- | --- |
| `catalog.discover` | optional typed `filters`, zero-based `cursor`, bounded `limit` | matching route records, next cursor and exhausted status |
| `asset.read` | bounded `asset_ids`, `detail=summary|document` | catalog summaries or unchanged canonical documents |
| `callable.resolve` | one `asset_id` | verified module, symbol, signature and implementation version |
| `callable.invoke` | one `asset_id`, `arguments` keyed by declared input ports | JSON-compatible scientific result plus the same release/asset binding |

Discovery filters are exact typed facets already present in route records: `kind`, `taxonomy`, `relation`, `direction`, `output`, and the named `facets` mapping. Each of the first five filters is one string, including `taxonomy` even though a route record can contain several taxonomy entries. `facets` maps string names to string values. Filters are not lists and do not provide OR semantics. The adapter does not add inferred tags, synonyms, rankings, vector similarity or natural-language selection. Exhausting a page limit returns `exhausted=false` with a continuation cursor; it never means the capability is unavailable.

`asset.read` returns catalog-generated summaries or canonical documents without rewriting their scientific fields. The only detail values are `summary` and `document`; use `document`, not `exact`, to request the canonical exact document. `callable.resolve` imports only the selected module and fails closed unless module, symbol, runtime signature, documented input acceptance, explicit required/default status and SciRel implementation version match the document. Discovery and documentation reads do not import scientific modules.

`callable.invoke` accepts only documented input names and requires every port marked `required`. Ordinary Operator
ports bind directly as Python keyword arguments. A TaskGraph whose public callable declares an `inputs` mapping
receives the complete validated document-port mapping through that parameter; its `**kwargs` remain available for
declared dependency injection and do not receive scientific ports. The callable must bind successfully when the
adapter supplies only the `inputs` mapping; any additional named parameters must therefore be optional. The scientific callable remains responsible for
the documented unit, shape, dtype, applicability and numerical checks because v1 port constraints are human-readable
rather than an executable value schema. The adapter converts mappings, sequences and array-like `tolist()` results
to JSON-compatible values without renaming outputs or changing values. Scientific failures remain the causal
exception of an adapter `invocation_failed` error.

## Common binding and forbidden fields

Every successful response carries:

```json
{
  "schema": "scirel.thin-mcp-response.v1",
  "operation": "catalog.discover",
  "catalog": {
    "catalog_id": "scirel-development-pilot",
    "release_version": "0.1.0.dev5",
    "root_digest": "sha256:<catalog-release-root>",
    "coverage": {"status": "partial", "included_asset_count": 24, "declared_total_asset_count": 71}
  }
}
```

Operation-specific fields are fixed:

| Operation | Additional response fields |
| --- | --- |
| `catalog.discover` | `items`, `cursor`, `next_cursor`, `exhausted` |
| `asset.read` | `detail`, `items` |
| `callable.resolve` | `asset_id`, `implementation_version`, `binding` |
| `callable.invoke` | `asset_id`, `implementation_version`, `evidence_ceiling`, `result` |

`items` is the only collection field used by discovery and reads; there is no `assets` or `total` field. Consumers must follow `next_cursor` until `exhausted=true` when their bounded search requires more pages. They must not infer field names from the scientific documents or adapter implementation.

The root digest is verified together with every partition before operations are served. Content binding remains at catalog release level; the adapter does not create per-asset or per-call source hashes.

Requests fail closed on unknown fields. In particular, `session_id`, `project_id`, `workbench_id`, tenant/user identity, credentials, approval records, admission/case/decision refs, sandbox policy, timeout, audit and cloud job fields are outside this core. An MCP server owns those transport and execution-policy concerns and must not persist them into asset documents, catalog identity or adapter results.

## Example flow

```python
from scirel_adapter import ThinMcpAdapter

adapter = ThinMcpAdapter(
    "/path/to/catalog",
    expected_root_digest="sha256:<catalog-release-root>",
)

adapter.handle({
    "operation": "catalog.discover",
    "filters": {
        "kind": "operator",
        "relation": "drive currents and per-current Green responses to physical flux and field"
    },
    "cursor": 0,
    "limit": 5,
})

adapter.handle({
    "operation": "asset.read",
    "asset_ids": ["scirel.field.current-green-superposition"],
    "detail": "document",
})

adapter.handle({
    "operation": "callable.invoke",
    "asset_id": "scirel.field.current-green-superposition",
    "arguments": {
        "currents": [2.0, -1.0],
        "gpsi": [[1.0, 3.0], [4.0, 5.0]],
        "gBR": [[2.0, 1.0], [0.0, 6.0]],
        "gBZ": [[-1.0, 2.0], [3.0, 4.0]]
    },
})
```

`scirel_adapter` exports the `ThinMcpAdapter` class and `ThinMcpAdapterError`; it does not expose a module-level
`handle` function. A consumer constructs one adapter for the pinned snapshot and sends all four operation envelopes
through that instance.

The final response reports the selected `asset_id`, catalog root digest, implementation version, evidence ceiling and result. It does not claim admission, approval, new scientific verification or general applicability.

## Deferred boundaries

This slice does not provide JSON-RPC transport, MCP tool registration, authentication/authorization, process isolation, resource limits, cancellation, streaming, audit storage, arbitrary object serialization, natural-language routing, cross-framework conformance, a complete 62-asset catalog or publication authorization. Those capabilities require separate owners and evidence.
