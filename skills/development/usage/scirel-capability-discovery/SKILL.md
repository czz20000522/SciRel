---
name: scirel-capability-discovery
description: Find SciRel capabilities for a step of a physical method and read their complete public contracts, through the bundled read-only MCP server or its standard-library CLI, before using a SciRel API.
---

# Find and read SciRel capabilities

Use this after the physical method is written, for the steps where a tested operator would save work or add confidence. Many steps have no matching operator; NumPy, SciPy or your own code is a normal way to do them. Do not reshape the physics to fit an operator or map every step to one.

This skill only reads public contracts. It never runs scientific code; the SciRel wheel is installed and called separately.

## Searching well

- Search one physical step at a time, not the whole question.
- Use one to three English physics words, such as `flux surface` or `plasma dispersion`. All terms must match and contracts are written mainly in English, so long phrases or other languages often return nothing.
- On a zero hit, read `gap.closest_terms` and `gap.retry_hint`, drop a word, try a synonym, or `browse` by metadata. Two or three tries are usually enough.
- A hit is a candidate, not proof that it applies. A zero hit does not prove the capability is absent; if nothing fits, write the step yourself and test it.
- A query, access or integrity error is a failure to read the catalog, not an empty result.
- Results may be paginated or truncated by a byte budget; fetch the rest (`next_cursor`) before relying on what is missing.

## Reading a contract

Call `get` for every candidate you may use and read the whole contract before writing code: inputs, outputs, units, shapes, sign and normalisation conventions, model, geometry, boundary conditions, applicability range and failure behaviour. Check that these match what your physics needs.

Record the asset IDs you used and the identity values below, so the result can be reproduced.

## Identity

`describe` returns `snapshot_sha256` and `runtime.wheel_sha256`. Pass both to every later `browse`, `search` and `get` call so all answers come from the same package. On `identity_mismatch` or an integrity error, stop using earlier results, run `describe` again, and continue only if switching to that package is acceptable for the task.

## CLI

From the package root (the directory that contains `runtime.json`):

```sh
python skills/scirel-capability-discovery/scripts/query.py --root . describe
python skills/scirel-capability-discovery/scripts/query.py --root . search --q '<one to three words>' --limit 5 \
  --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
python skills/scirel-capability-discovery/scripts/query.py --root . get <asset_id> \
  --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
```

`browse` takes the same pins plus metadata filters; run `query.py browse --help` for them.

## Optional MCP server

If the host supports MCP, register the entry in the package's `mcp-connections.json` with the package root as working directory, or start it yourself:

```sh
python -m pip install -r mcp-requirements.txt
python skills/scirel-capability-discovery/scripts/server.py --root . --transport stdio
# or, for an HTTP client: --transport streamable-http --host 127.0.0.1 --port 8765  → http://127.0.0.1:8765/mcp
```

It exposes the same four read-only tools: `scirel_describe`, `scirel_browse`, `scirel_search`, `scirel_get`. Install `mcp-requirements.txt` in the server's environment and keep it separate from the environment where the SciRel wheel and `runtime-requirements.txt` are installed.
