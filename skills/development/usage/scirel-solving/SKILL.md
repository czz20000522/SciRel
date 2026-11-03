---
name: scirel-solving
description: Answer scientific questions by reasoning from the physics, computing and checking the result, and writing a short technical report with figures, using SciRel capabilities where they apply. Use for scientific problem solving, not library development or qualification.
---

# Solve with SciRel

Use the supplied public capabilities and authorized task inputs. Keep outputs in the task workspace. This skill shares one method between internal SciRel capability testing and external user solving; its linked references and helper stay inside this skill.

The goal is a correct, understandable answer to the user's physics question. SciRel is a tool for that, not the point of the report. For capability discovery, load the `scirel-capability-discovery` skill before selecting an API. Its `scripts/` directory contains the transport helpers; they are not a second scientific API and do not replace this skill.

## Priority execution card

This skill is the agent's task protocol. Start by writing the user requirement,
expected inputs/outputs, assumptions and physical approach, then the capabilities
that apply, glue surface, tests and stop condition. The real user does not provide a reference
oracle. Use public contracts, physical constraints, invariants, diagnostics and
tests generated for the task to decide whether the program behaves correctly.
Reference answers belong only to separate benchmark evaluation.

First classify the run as `internal` or `external`.

After discovery finds no directly applicable public contract, read [public
capability gap intake](references/capability-gap-intake.md) and write one gap
card before choosing a fallback. The card is the handoff between outbound and
maintenance; it prevents an absent API, a task-specific glue step and a runtime
failure from being reported as the same `HOLD`.

- `internal`: the owner is evaluating or extending SciRel itself. This is an
  adversarial diagnostic line: a missing public capability, weak discovery,
  boundary failure or misleading result is a useful finding. Record the gap,
  stop the affected claim at the capability boundary, and route the finding to
  merge/intake for a reusable capability decision. Do not quietly implement
  missing scientific core as task glue.
- `external`: the owner is a user of a distributed SciRel package. SciRel is an
  optional accelerator, not a prerequisite for a solvable programming task. This
  is a completion line: if discovery finds no applicable public capability,
  continue with ordinary programming, numerical libraries and explicit glue
  when the user request and environment permit it. Record the missing
  capability as a task-level gap and test the replacement. Do not turn the
  user's task into a SciRel intake hold.

The mode is selected from the task owner and package context, not from a
keyword in the scientific request. An internal run has a SciRel development or
benchmark owner and may write intake evidence; an external run has a user
deliverable and must keep its solution in the user workspace.

For every user task, generate at least normal, lower-bound and upper-bound
tests. Add degenerate, branch, failure and composition tests when the contract
permits them. Test both SciRel calls and the glue around them. Keep the glue
ordinary, visible and reproducible: data preparation, control flow, format
conversion and presentation may be implemented by the agent, while reusable
scientific relations remain in SciRel contracts.

Before claiming completion, read back outputs, failures and test results. The
result package must include the generated entrypoint, API trace, task tests,
boundary coverage and uncovered relations. A result can be useful with a
typed failure or a non-convergence state when that is the declared behavior;
do not turn it into a success label.

For a benchmark challenge, record every requested case as `ATTEMPTED`,
`UNATTEMPTED`, `RUNTIME_GAP`, `CONTRACT_MISMATCH`, or `COMPLETED`; never
inherit a missing run as a public capability gap. Keep the reference answer and
hidden oracle outside the worker context and compare only after the clean run.
A parseable output proves only that the task reached its output path; completion
still requires generated tests, readback, failure semantics and the stated
boundary matrix.

When a public capability gap is found, record the full gap card before acting.
Internal runs route reusable scientific relations to merge/intake and may stop
the affected claim. External runs disclose the gap and may continue with
ordinary, visible, tested glue; ask the user only when choosing glue versus a
SciRel addition changes scope or scientific meaning. A glue success never
retroactively proves that SciRel owns the missing relation.

## Batch entry gate

Before a new user run, apply the canonical baseline/outbound gate described in repository `RULES.md` section 12: record the current input/runtime identity and owner, keep evidence states explicit, and stop on an integrity failure or missing scientific assumption. The worker sees only the request and public contracts/docs. Follow **clarify → physical method → confirm → compute and check, using discovery where it helps → report → independent acceptance**; keep source identity, hidden oracle, and private acceptance material outside the task. This entry does not authorize package rebuilds, publication, or acceptance decisions.

## Choose the supplied access

For a source checkout, query its public contracts without building a package:

```sh
python -B scripts/scirel_docs.py query --source-root . --describe
python -B scripts/scirel_docs.py query --source-root . --q '<scientific relation>' --limit 5
python -B scripts/scirel_docs.py query --source-root . --asset <asset-id>
```

Reuse `source_identity_sha256` as `--expected-digest` to detect edits. Source identity does not bind an installed wheel. Read the selected complete contract before using its public API.

Treat pagination, omitted sections and host truncation as delivery limits: retrieve the missing contract clauses
before relying on the capability. Query, integrity or access failure is not an empty capability set. A complete
response may still be a bounded search, so a zero hit does not prove absence. After an identity mismatch, stop the
affected run. Rebind from a current description only when the task permits selecting a new input/runtime;
do not use an older contract or reading page as proof of current availability.

For a consumer package, select its root and inspect the declared runtime:

```sh
python <package>/skills/scirel-capability-discovery/scripts/query.py --root <package> describe
python <package>/skills/scirel-capability-discovery/scripts/query.py --root <package> search --q '<scientific relation>' --limit 5 --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
```

Install the `runtime.wheel` reported by `describe` with `python -m pip install <package>/wheel/<wheel>` in an environment satisfying `runtime.requires_python`; scientific requirements are also in `runtime-requirements.txt`. Optional MCP uses `mcp-requirements.txt`. Take both pins from `describe`; preserve them on `browse`, `search` and `get`. Read the complete original JSON contract with `get <asset-id>`, including its byte digest and path. CLI and optional MCP expose these same four read-only operations. Pins bind supplied wheel bytes, not installed imports; verify the execution environment before claiming that wheel ran. Execute science through the installed public Python API.

### Optional MCP discovery

MCP is an adapter, not an implicit capability. If the host agent supports MCP,
register the supplied `mcp-connections.json` entry with the public bundle as its working directory, or start the adapter yourself:

```sh
cd <public-package>\npython -m pip install -r mcp-requirements.txt\npython skills/scirel-capability-discovery/scripts/server.py --root . --transport stdio
```

Before starting the adapter, install its dependencies into that adapter environment with `python -m pip install -r mcp-requirements.txt`. The stdio server exposes four read-only tools: `scirel_describe`,
`scirel_browse`, `scirel_search` and `scirel_get`. Install
`mcp-requirements.txt` in the adapter environment only; keep the scientific
wheel environment separate. For an HTTP MCP client, start:

```sh
cd <public-package>\npython skills/scirel-capability-discovery/scripts/server.py --root . --transport streamable-http --host 127.0.0.1 --port 8765
```

Then connect to `http://127.0.0.1:8765/mcp`. Call `scirel_describe` first and
copy its `snapshot_sha256` and `runtime.wheel_sha256` into every later
`scirel_browse`, `scirel_search` and `scirel_get` call. A normal discovery
sequence is:

1. `scirel_describe` with no required argument, or with `expected_wheel_sha256` when the wheel was supplied out of band.
2. `scirel_search` with `q` and both identity pins.
3. `scirel_get` for each selected `asset_id` with both identity pins.
4. Inspect units, shapes, model, boundary, applicability and failure semantics before writing glue.

The MCP search is bounded lexical retrieval. A hit does not establish
scientific applicability, and a zero hit does not prove that no capability
exists. If MCP is unavailable, use the `scirel-capability-discovery` skill and its CLI fallback with the
same sequence and identity pins.

Human API pages and tutorials are optional, separately supplied reading. Use an actual configured site/version or supplied generated paths when available; the asset ID is the logical lookup key. Do not infer a URL, fetch a site automatically, or assume that a site's “latest” matches the selected wheel. Their absence does not prevent structured discovery or contract retrieval.

## Work toward the result

Every task follows the same five stages. Read the [workflow](references/workflow.md) for their outputs, exit conditions and branches.

1. **Clarify.** Reuse supplied facts and ask only about what changes the result; see [clarification](references/clarification.md). End when the agreed definitions fix the numbers. Record what remains unknown.
2. **Design the physical method.** Before any code, write the physics: what decides the answer, the model and assumptions, the laws and formulas, the route to the requested quantities and how the result can be checked. See [physical method](references/method-design.md). A reader who knows physics but not the code must be able to follow it. Note a SciRel capability in passing only where a step happens to use one; steps done with NumPy, SciPy or ordinary code need no such note.
3. **Confirm.** Show the user the physical assumptions and method, then wait, unless the user has already confirmed them or waived this step.
4. **Compute and check.** Look for a reusable capability where it saves work, and read the complete contract before using it. Implement the rest as ordinary code and test it; see [supplementary calculations](references/glue-gap.md). For coupled work, a [physical plan](references/graph-model.md) can clarify dependencies, and [vacuum/equilibrium coupling](references/material-coupling.md) needs particular care. Use a discriminating reference, limit, symmetry, conservation or convergence check with tolerances fixed in advance, preserve failures and save results at full precision; see [result checks](references/result-checks.md). Saved CSVs may use the optional [delivery helper](references/delivery-tool.md).
5. **Report.** Write a short technical report following the [report format](references/report-format.md), with a [worked example](references/example-report.md) of the expected style: answer, problem and understanding, physical model and method, results with figures, discussion, conclusion, and numerical tables in an appendix. Do not judge acceptability without a criterion from the user; state the effect in physical terms instead. For a replayable application, deliver the runnable entrypoint, agent-generated regression tests and their results; for handover, keep one concise [outbound record](references/outbound-evidence.md).

Preserve the selected input/runtime identity across the run; stop relying on bytes that fail integrity checks. Use only public inputs, without private implementations, source history or hidden acceptance answers. The host owns permissions and execution lifecycle; this method grants no additional authority.

