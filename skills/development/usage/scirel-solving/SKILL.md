---
name: scirel-solving
description: Fulfil a user's scientific request through clarification, internal SciRel discovery and execution, then checked results; ask about unclear scientific intent instead of inventing defaults.
---

# From a user's request to a checked result

The user describes a goal, answers necessary clarification and receives useful results. Keep catalog routing, API selection and development bookkeeping internal unless asked. SciRel supplies methods, scientific capabilities and domain contracts, not authority. The host (CodeFusion, Codex, Claude Code or another harness) owns authorization, sandboxing, observability, logs, cancellation and recovery. Do not implement those platform systems here or treat a skill as permission.

## 1. Understand and clarify

Identify the intended result and the supplied physical facts. Reuse information already given. When model, units, boundary conditions, data meaning or success criteria are unclear, ask concise questions in the user's vocabulary **before** dependent computation. Group related questions and explain their effect when useful. Do not resolve unclear user intent using the nearest API's defaults or your preferred model. Do not ask the user to choose internal function names or technical machinery they need not know.

If the facts are sufficient, proceed. Implementation details that cannot change the scientific meaning need no extra interview. When the host provides a question tool, use it; otherwise ask in the conversation and wait for the answer. If the user cannot supply a necessary fact, state what remains unresolved and what bounded result is still possible. Do not invent an answer.

## 2. Find and plan internally

Before writing scientific computation, query SciRel. For a recognizable scientific term, start with one bounded search rather than browsing all directories:

```sh
python3 <this-skill>/../scientific-asset-navigation/scripts/query.py search --q "<scientific term>" --limit 3
python3 <this-skill>/../scientific-asset-navigation/scripts/query.py show <selected-asset-id>
```

Substitute this skill's actual directory. Read the selected call contract completely; do not crop it with `head` or arbitrary slices, which can hide output and diagnostic meanings. Read [navigation guidance](../scientific-asset-navigation/SKILL.md) for unfamiliar domains, ambiguous/empty results or capability gaps. Stop discovery once a contract covers the request; do not load neighboring contracts without a concrete unresolved question. Existing applicable APIs or compatible compositions must be reused. Only an established capability gap permits new implementation of that missing part, kept separate and independently validated; it does not inherit SciRel's evidence. Environment failures and failed checks are not capability gaps. File I/O and serialization need no scientific lookup.

Known IDs can go directly to their contract; reuse already-read material from the same snapshot. Choose the smallest public entry that covers the requested result. Use an existing TaskGraph when it supplies the needed composition; a simple Operator need not acquire an unnecessary grid or workflow. Check actual units, axes, inputs, model assumptions, boundaries and failure propagation. Iteration needs an update order, stopping rule and bound. New interpolation, closure, discretization or scientific conversion cannot be hidden in glue.

## 3. Execute and check

Use the supplied installed runtime directly; inspect or repair installation only on an actual import/runtime failure. Do not silently change the scientific model, units, inputs or tolerances to make a run succeed. Check the requested output against applicable diagnostics or a discriminating reference/limit. Read [result checks](references/result-checks.md) when choosing or interpreting those checks is uncertain. Reuse host execution records; SciRel does not create an audit platform or recover host sessions.

## 3a. Leave a compact process trace for an external consumer

When the result is being shown to another team or platform, keep a short `PROCESS.md` beside the
run. It is a reasoning and reproducibility trace, not a second scientific report. Record the
user's observable goal and supplied facts, the normalized requirements (units, axes, coverage and
acceptance), the bounded query and the exact asset IDs selected, then the graph nodes, edge
adaptations and execution command. Finish with the actual output files, checks and replay status,
unresolved limits, and host-level steps that were not exercised. A name match or a successful
import is not a selection or an execution witness.

For a request that continues an existing source tree, preserve the source baseline and input
files, inspect its tests and public interfaces first, and state which part SciRel covers. Reuse
the installed public API for that part; modify the source only for the remaining request, record
the diff and inherited input identity, and run both the source regression tests and the SciRel
runtime check. The handoff must contain the patch and test results, not only a proposed solution.
Do not expose decomposition or library-development methods to a consumer task.

## 4. Check and render the delivery

For saved numerical tables, use the executable [delivery tool](references/delivery-tool.md). Read that short interface once, write the result specification, then run:

```sh
python3 <this-skill>/scripts/delivery.py build result-spec.json --out checked
python3 <this-skill>/scripts/delivery.py verify result-spec.json --out checked --answer checked/ANSWER.md
```

The tool reads the saved CSVs, computes bounded statements and checks, retains actual coordinate coverage, and creates the report, exact answer and optional plots. Set expected coverage from the request. Quote supplied conditions from their actual text; do not add inferred facts. Use this path instead of hand-writing numbers, validation claims or plot labels. A solver's terminal diagnostic must retain its actual scope. Independent physics validation still needs a scientific reference; a file comparison cannot establish it.

The verify response includes `answer_text` with file links. Use it unchanged as the final response, or deliver the generated report file. When a draft is available, verify that actual draft with `--answer`; checking ANSWER.md does not approve other prose. Any changed output requires successful replay; failed checks stay failed. Do not append optional theory or a second explanation. Unsupported inference requires an applicable scientific method, not free prose inside a verified report. The tool checks bounded data-to-statement consistency; it does not certify the user's translation, arbitrary scientific reasoning or future host messages. SciRel supplies this computation and its limits, while the host retains delivery authority.

## Only when needed

- Persistent multi-file application: [project implementation](../scientific-project-implementation/SKILL.md).
- Independent scientific validation or library qualification: [development validation](../../scientific-computation-validation/SKILL.md).
- Explicit adapter-mediated runtime: [thin adapter operations](references/thin-adapter-run.md).
- Vacuum field feeding equilibrium/material support: [coupling check](references/material-coupling.md).
