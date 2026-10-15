# Thin adapter run reference

Use this only when the selected task calls for adapter-mediated SciRel execution.
The authoritative development contract is
`docs/requirements/thin-mcp-adapter.md` when mounted. The SDK-free Python core
is `scirel_adapter.ThinMcpAdapter`; it is not an MCP server or a substitute for
the host's execution policy.

Construct one adapter with the admitted catalog directory and the expected
`root_digest` supplied independently by the selected environment or admitted
resource. Do not treat a digest read from that same catalog as an independent
pin. The installed SciRel wheel must match the selected document's
`implementation_version`.

Call `adapter.handle(...)` with these envelopes, selecting IDs and port values
from the request and returned records rather than this reference:

```python
from scirel_adapter import ThinMcpAdapter

adapter = ThinMcpAdapter(catalog_dir, expected_root_digest=expected_root_digest)
routes = adapter.handle({
    "operation": "catalog.discover", "filters": typed_facets,
    "cursor": 0, "limit": bounded_page_size,
})
document = adapter.handle({
    "operation": "asset.read", "asset_ids": [selected_asset_id],
    "detail": "document",
})
value = adapter.handle({
    "operation": "callable.invoke", "asset_id": selected_asset_id,
    "arguments": documented_port_values,
})
```

Discovery filters are exact typed facets, not free-text similarity. Read
`items`, `next_cursor` and `exhausted`; continue a bounded search when another
page matters. The exact document is `document["items"][0]`. Invoke only after
its applicability, ports and failure behavior match the normalized problem.
Responses contain `operation` and `catalog.root_digest`; invocation adds
`asset_id`, `implementation_version`, `evidence_ceiling` and `result`.
`ThinMcpAdapterError.code` preserves a failed adapter boundary.

For an acceptance run requiring observable adapter use, leave a bounded host
tool record derived from these returned envelopes. Record the operation and
catalog root for all three steps, selected ID for read/invoke, and version,
status and checks for invoke. Do not dump canonical documents, raw user data
or credentials into the trace. A direct `scirel` Python call or a text claim
that these operations ran is not equivalent evidence.
