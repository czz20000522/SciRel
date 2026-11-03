# Capability discovery method

Use this reference whenever a task needs SciRel capability lookup. It converts the
MCP/CLI adapter into an explicit skill step. The adapter only reads public
contracts; it never runs scientific code.

## Trigger and boundary

Trigger when a step of the physical method might have a reusable operator. The method is
valid for a packaged public runtime whose `runtime.json`, catalog and wheel are
in the same public bundle. Do not use source history, benchmark answers or
private acceptance material as discovery input.

## How to search

Search after the physical method is written, for the steps where a reusable
operator would save work. Many steps have no operator, and NumPy, SciPy or ordinary
code is a normal way to do them. Do not reshape the physics to fit an operator.

- Search one physical step at a time, not the whole question.
- Use one to three English physics words, such as `circular coil` or `plasma
  dispersion`. All terms must match, and contract text is mainly English, so long
  phrases and other languages often return nothing.
- On a zero hit, read `gap.closest_terms` and `gap.retry_hint`, drop a word, try a
  synonym, or browse by taxonomy. Two or three tries are enough.
- A zero hit does not prove absence. If nothing applies, write the step yourself
  and test it.
- Check the complete contract for the sign, normalization, units and applicability
  your physics needs.
- In the report, mention an operator in one short clause where a step happens to
  use it. Do not add an operator list or a mapping table.

## MCP path

The host must register `skills/scirel-capability-discovery/scripts/server.py` from the public bundle. The adapter
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
python skills/scirel-capability-discovery/scripts/server.py --root . --transport stdio
```

For a host that needs HTTP, use:

```sh
python skills/scirel-capability-discovery/scripts/server.py --root . --transport streamable-http --host 127.0.0.1 --port 8765
```

Connect to `http://127.0.0.1:8765/mcp`.

## CLI path

If MCP cannot be registered, use `skills/scirel-capability-discovery/scripts/query.py`. It is the same dispatcher
and response envelope, so the discovery semantics do not change:

```sh
python skills/scirel-capability-discovery/scripts/query.py --root . describe
python skills/scirel-capability-discovery/scripts/query.py --root . search --q '<short scientific phrase>' --limit 5 \
  --expected-snapshot-sha256 <snapshot_sha256> \
  --expected-wheel-sha256 <wheel_sha256>
python skills/scirel-capability-discovery/scripts/query.py --root . get <asset_id> \
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

