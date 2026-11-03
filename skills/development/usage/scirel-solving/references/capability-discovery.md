# Capability discovery method

Use this reference whenever a task needs SciRel capability lookup. It converts the
MCP/CLI adapter into an explicit skill step. The adapter only reads public
contracts; it never runs scientific code.

## Trigger and boundary

Trigger before choosing a SciRel API or writing scientific glue. The method is
valid for a packaged public runtime whose `runtime.json`, catalog and wheel are
in the same public bundle. Do not use source history, benchmark answers or
private acceptance material as discovery input.

## MCP path

The host must register `tools/server.py` from the public bundle. The adapter
exposes exactly four read-only tools:

1. `scirel_describe`
2. `scirel_browse`
3. `scirel_search`
4. `scirel_get`

Call `scirel_describe` first. Save the returned `snapshot_sha256` and
`runtime.wheel_sha256`. Send both values with every later `browse`, `search` and
`get` call. On `identity_mismatch`, stop using the old results and describe the
currently selected runtime again.

Use `scirel_search` with a short phrase to recall candidates, or `scirel_browse`
when metadata filters are clearer. Treat the result as a candidate list only.
For each candidate that may be used, call `scirel_get` with its `asset_id` and
both pins. Read the complete contract: inputs, outputs, units, shapes, model,
geometry, boundary, device scope, failure behavior, aliases and evidence. Only
then select an API and write glue.

The host starts stdio from the public directory with:

```sh
python tools/server.py --root . --transport stdio
```

For a host that needs HTTP, use:

```sh
python tools/server.py --root . --transport streamable-http --host 127.0.0.1 --port 8765
```

Connect to `http://127.0.0.1:8765/mcp`.

## CLI path

If MCP cannot be registered, use `tools/query.py`. It is the same dispatcher
and response envelope, so the discovery semantics do not change:

```sh
python tools/query.py --root . describe
python tools/query.py --root . search --q '<short scientific phrase>' --limit 5 \
  --expected-snapshot-sha256 <snapshot_sha256> \
  --expected-wheel-sha256 <wheel_sha256>
python tools/query.py --root . get <asset_id> \
  --expected-snapshot-sha256 <snapshot_sha256> \
  --expected-wheel-sha256 <wheel_sha256>
```

## Evidence and recovery

Record the selected asset IDs, both identity pins, and the complete contracts
actually read. A zero lexical hit is an unresolved discovery result, not proof
that the library lacks the capability. A query or integrity error is an access
failure, not an empty catalog. Refine the phrase, browse by metadata, or report
a task-level gap according to the parent `scirel-solving` skill.

MCP dependencies belong in the adapter environment from `mcp-requirements.txt`;
scientific dependencies and the wheel belong in the separate runtime
environment from `runtime-requirements.txt`. Keep this separation when the host
runs both processes.
