---
name: scirel-capability-discovery
description: Discover SciRel public capabilities through the host-provided MCP tools or the bundled standard-library fallback, then read complete contracts before selecting an API.
---

# SciRel capability discovery

Use this skill before choosing a SciRel API. It is the discovery layer for the
other SciRel outbound skills; it does not execute scientific calls.

Search after the physical method is written, for the steps where a reusable
operator would save work or add confidence. Many steps have no matching operator,
and NumPy, SciPy or ordinary code is a normal way to do them. Do not reshape the
physics to fit an operator, or map every step to one.

## Entry

The host should load this plugin's `.mcp.json`. That registers the bundled
read-only server from `scripts/server.py`. If the host cannot register MCP, use
`scripts/query.py` directly. Both paths use the same dispatcher and response
envelope.

Call `scirel_describe` first. Save `snapshot_sha256` and
`runtime.wheel_sha256`. Every later `scirel_browse`, `scirel_search` and
`scirel_get` call must carry both pins.

## Query sequence

1. Use `scirel_search` with one to three English physics words for one physical
   step, or `scirel_browse` with metadata filters. All terms must match. On a zero
   hit, read `gap.closest_terms` and `gap.retry_hint` and try fewer words or a
   synonym.
2. Treat returned cards as candidates, not proof of applicability.
3. Call `scirel_get` for each selected `asset_id`.
4. Read the complete contract before coding: inputs, outputs, units, shapes,
   model, geometry, boundary, device scope, aliases and failure semantics.
5. Record the asset IDs and identity pins in the task evidence.

A zero lexical hit is an unresolved discovery result. It does not prove that a
capability is absent. A query or integrity error is an access failure, not an
empty catalog. On `identity_mismatch`, describe again and explicitly select the
new runtime before continuing.

## MCP registration

From the plugin root, the stdio entry is:

```sh
python skills/scirel-capability-discovery/scripts/server.py --root . --transport stdio
```

For a loopback HTTP host:

```sh
python skills/scirel-capability-discovery/scripts/server.py --root . --transport streamable-http --host 127.0.0.1 --port 8765
```

The server advertises only `scirel_describe`, `scirel_browse`,
`scirel_search` and `scirel_get`. It reads public contracts and never executes
user code or SciRel functions. Install `mcp-requirements.txt` in the adapter
environment, separate from the scientific wheel environment.

## CLI fallback

```sh
python skills/scirel-capability-discovery/scripts/query.py --root . describe
python skills/scirel-capability-discovery/scripts/query.py --root . search \
  --q '<short scientific phrase>' --limit 5 \
  --expected-snapshot-sha256 <snapshot_sha256> \
  --expected-wheel-sha256 <wheel_sha256>
python skills/scirel-capability-discovery/scripts/query.py --root . get <asset_id> \
  --expected-snapshot-sha256 <snapshot_sha256> \
  --expected-wheel-sha256 <wheel_sha256>
```

The scientific wheel is installed separately from `wheel/`; the discovery
adapter only tells the agent which public API and contract to use.
