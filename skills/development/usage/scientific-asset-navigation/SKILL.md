---
name: scientific-asset-navigation
description: Route a normalized scientific request through SciRel topic cards, candidate summaries and exact contracts; distinguish reusable capabilities from genuine gaps.
---

# Progressive SciRel discovery

Search the documents bound to the installed wheel. A lookup is mandatory before writing a new scientific kernel, but reading all documents is not. Existing applicable capability must be reused. Names and search hits only route attention; exact contracts determine applicability.

## One path, with shortcuts

Use the bundled standard-library [query tool](scripts/query.py); it never imports scientific modules. It finds `docs/manual` beside the bundled `skills` directory, independent of the delivery root's name or current working directory. Else supply `--snapshot PATH` before the command. Substitute this skill's actual directory for `<skill>`:

CLI responses are complete compact JSON records. Do not trim a selected call contract with line/character slices; diagnostic meanings and coverage may occur after the signature. If the host truncates a response, retrieve the missing relevant sections before interpreting results.

```sh
python3 <skill>/scripts/query.py routes
python3 <skill>/scripts/query.py routes --chapter <chapter-id>
python3 <skill>/scripts/query.py search --topic <topic-id> --limit 5
python3 <skill>/scripts/query.py show <asset-id>
# Only when inspecting graph wiring or provenance:
python3 <skill>/scripts/query.py show <asset-id> --view graph
python3 <skill>/scripts/query.py show <asset-id> --view full
```

- **Known ID/API or topic:** go directly to `show` or filtered `search --q`; skip already known levels. Whitespace keywords use literal AND; use scientific synonyms and Chinese/English terms when needed.
- **Recognizable scientific term:** one bounded keyword search can precede chapter browsing. Choose the smallest compatible entry; stop after its contract resolves the request. TaskGraph-first ordering is a retrieval order, not a reason to choose a larger workflow. Only widen the search for an explicit mismatch, ambiguity or missing coverage.
- **Unknown domain:** read chapter cards, then relevant topic cards. Search returns five short cards by default, TaskGraphs first. Follow `next_offset` when needed; graph ordering does not imply compatibility. Widen topics or remove `--kind` before declaring a gap.
- **Shortlist:** `show` copies exact public sections, including every port, applicability, failure, example and verification clause plus graph execution rules. Graph wiring and provenance are explicitly deferred, never silently summarized. Load exact contracts only for serious candidates and near misses. Check direction, model, domains, input/output units, axes, boundaries, defaults and failures. A suitable graph's public contract is enough to call it; read node contracts when inspecting an unresolved edge, composing a new graph or diagnosing a mismatch.
- **Reuse:** keep the chosen IDs, snapshot identity and mismatch reasons in the current task. Re-read only after a request/identity change or new uncertainty. Do not print `index.json`, scrape HTML, recursively cat contracts, import a registry or load the tool source just to query it.

An existing connector may supply the same layers; use its actual operations. Do not load adapter guidance for an ordinary Python call. Missing/corrupt documents, mismatched runtime or unavailable tools mean **environment/metadata gap**, not permission to invent science.

## Before declaring capability absent

Review the relevant topic summaries without keyword filtering, plausible synonyms/neighboring topics and possible compositions. Read scientific near misses to determine why they cannot satisfy the request. A zero-hit query or an unvisited page cannot establish absence. State the inspected snapshot/scope and remaining uncertainty; never infer release-wide absence from a partial collection.

If no suitable existing relation or composition covers a specific subproblem within that established scope, state the gap and implement only that missing part when required by the task. Label it new/unvalidated science, keep it separate from SciRel-backed results, and validate it independently. Do not silently weaken a model or rewrite an existing kernel. Unresolved applicability needs scientific input, not a guessed substitute.

Normally a short selection/gap note is sufficient. Read [navigation audit](references/navigation-search-audit.md) only when a formal search receipt is requested. This skill selects capabilities; it does not approve assets or prove the user's problem was translated correctly.
