---
name: scirel-capability-discovery
description: Find SciRel capabilities for a step of a physical method and read their complete public contracts, through the bundled read-only MCP server or its standard-library CLI, before using a SciRel API.
---

# Find and read SciRel capabilities

Use this after the physical method is written (`method.md` comes first), for the steps where a tested operator would save work or add confidence. Many steps have no matching operator; NumPy, SciPy or your own code is a normal way to do them. Do not reshape the physics to fit an operator or map every step to one. If a contract shows that the method needs to change, update `method.md` first, then code.

This skill only reads public contracts. It never runs scientific code; the SciRel wheel is installed and called separately.

## Searching well

- Search one physical step at a time, not the whole question.
- Use one to three English physics words, such as `flux surface` or `plasma dispersion`. All terms must match and contracts are written mainly in English, so long phrases or other languages often return nothing.
- On a zero hit, read `result.gap.closest_terms` and `result.gap.retry_hint`, drop a word, try a synonym, or `browse` by metadata. Two or three tries are usually enough.
- A hit is a candidate, not proof that it applies. A zero hit does not prove the capability is absent; if nothing fits, write the step yourself and test it.
- A query, access or integrity error is a failure to read the catalog, not an empty result.
- Results may be paginated or truncated by a byte budget; fetch the rest (`next_cursor`) before relying on what is missing.

## What the commands return

All commands print one JSON object with `command`, `outcome`, `snapshot_sha256` and `wheel_sha256` at the top level.

- `describe`: catalog facts and `runtime` (`wheel`, `wheel_sha256`, `requires_python`, `requires_dist`).
- `search` and `browse`: `outcome` is `match` or `no_candidates`; hits are in `result.items` (each with `asset_id`, `symbol`, `capability_summary`, model, geometry and boundary tags), the totals and `next_offset` are in `result`, zero-hit advice is in `result.gap`, and `next_cursor`, `truncated` and `response_bytes` are at the top level. Pass `--cursor` to continue; `--max-bytes` sets the budget.
- `get`: the contract is in `document`, with `identity`, `public_api`, `inputs`, `outputs`, `applicability`, `failure_semantics`, `verification`, `example` and, for multi-step assets, `composition`.

## Reading a contract

Some contracts are long, mostly because of their `composition` section. Save each `get` result to a file and read it from there instead of from a terminal that may cut it off.

Call `get` for every candidate you may use and read the contract before writing code, in this order: `identity` and `public_api` (definition and signature), `inputs` and `outputs` (units, shapes, sign and normalisation conventions), `applicability`, `failure_semantics`, `verification.known_limitations`, and `example`. Read `composition` when the asset couples several steps. Check that model, geometry, boundary conditions and range match what your physics needs.

Watch for conventions that differ by a known factor: per element or total (a current per filament or per coil, a flux per radian or total), per unit length or area or integrated, and which reference a potential or energy is measured from. Convert at the call and check the call against a hand value that the factor would change.

## Presets and task geometry

Some assets are device presets with built-in geometry, currents or parameters. When the task specifies its own geometry or parameters, build the inputs from the task and use a generic operator; use a preset only after comparing its definition item by item with the task, and say in the method which you used and why.

Record the asset IDs you used and the identity values below, so the result can be reproduced.

## Identity

`describe` returns `snapshot_sha256` and `runtime.wheel_sha256`. Pass both to every later `browse`, `search` and `get` call so all answers come from the same package. On `identity_mismatch` or an integrity error, stop using earlier results, run `describe` again, and continue only if switching to that package is acceptable for the task.

## CLI

From the package root (the directory that contains `runtime.json`):

`--root` defaults to the current working directory. When running from another directory, pass the package root explicitly.

```sh
python skills/scirel-capability-discovery/scripts/query.py --root . describe
python skills/scirel-capability-discovery/scripts/query.py --root . search --q '<one to three words>' --limit 5 \
  --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
python skills/scirel-capability-discovery/scripts/query.py --root . get <asset_id> \
  --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
```

`browse` takes the same pins plus metadata filters; run `query.py browse --help` for them. Redirect `get` to a file, for example `... get <asset_id> ... > contract.json`.

To run SciRel itself, install the wheel named by `describe.runtime.wheel` into a Python that satisfies `runtime.requires_python`; the discovery scripts themselves need only the standard library.

## Optional MCP server

If the host supports MCP, register the entry in the package's `mcp-connections.json` with the package root as working directory, or start it yourself:

```sh
python -m pip install -r mcp-requirements.txt
python skills/scirel-capability-discovery/scripts/server.py --root . --transport stdio
# or, for an HTTP client: --transport streamable-http --host 127.0.0.1 --port 8765  → http://127.0.0.1:8765/mcp
```

It exposes the same four read-only tools: `scirel_describe`, `scirel_browse`, `scirel_search`, `scirel_get`. Install `mcp-requirements.txt` in the server's environment and keep it separate from the environment where the SciRel wheel and `runtime-requirements.txt` are installed.

