# Portable private consumption

SciRel's consumer protocol is independent of the number of assets and the search
backend. A delivery is a read-only snapshot of public contracts, their generated
reading layers, one flat `scirel-solving` skill and one exact Python wheel. The
contracts are the only scientific truth. Discovery is generated from their
reviewed `discovery`, identity, aliases and port fields; consumers never maintain
a parallel classification. Missing metadata stays unknown. There is no graph or
Operator/TaskGraph classification inferred from the current contracts.

## Stable MCP protocol

MCP is the formal Agent entry. The official Python SDK adapts one transport-neutral
registry/dispatch to a client-launched stdio process or Streamable HTTP. Local and
remotely hosted modes use the same five directory tools and public snapshot. They
never register every scientific function as a tool or execute arbitrary user
code. Computation uses the installed scientific wheel in the user's Python
program. SDK dependencies are pinned separately. No public service is deployed
by this build; Famou protocol/transport/authentication support remains `NOT_RUN`.

JSON envelopes use `schema: scirel.consumer-response`, command, source revision,
snapshot ID, exact manifest digest and wheel digest. There are no version suffixes
or compatibility aliases. Precision reading remains tools-accessible even if a
future host additionally exposes MCP resources.

| Command | Input | Result |
| --- | --- | --- |
| `scirel_describe` | optional expected_wheel_sha256 | Identity, filters, schemas, backend limits, public count and runtime declarations |
| `scirel_browse` | identity pins, filters, offset/limit/cursor/max_bytes | Stable ID ordered cards and continuation |
| `scirel_search` | identity pins, q, filters, offset/limit/cursor/max_bytes | Ranked cards, hit reasons, conflicts and continuation |
| `scirel_get` | identity pins, asset_id, language en/zh | Exact contract plus generated API Markdown and digests |
| `scirel_get_tutorial` | identity pins, chapter_id, language, offset/limit_chars | Bounded tutorial text and continuation |

The developer-only `python tools/query.py verify` checks every member, the manifest's own
digest, path containment, missing/extra files and selected index identity. It is
not scientific qualification. Limits are 1..100, default 5. Structured filters
are capability, operation, model, geometry, boundary, device_scope, taxonomy and alias.
Taxonomy matches exact contract labels. Missing fields remain unknown; a module
name does not become another manually maintained scientific domain list.
The authoritative query schemas are exported from the same portable core, not
retyped in another implementation. Assets have stable `asset_id` identities;
snapshot/source/digest identify which content that ID meant in a delivery.

Discovery responses carry `retrieval.completeness: unknown` and
`scientific_applicability: not_assessed`. `match` means every supplied lexical or
structured filter matched indexed metadata. `near_miss` lists matched and missed
constraints and is not a permissible substitute. MCP `outcome: no_candidates`
means no candidate satisfied the query; its retrieval scope remains incomplete
(`retrieval_incomplete`), so it does not establish scientific absence.
`metadata_error` denotes malformed or corrupt data; it must never be presented
as an absent scientific capability. Caller mistakes use `invalid_request`.

Subsequent tools require `expected_snapshot_sha256` (the exact manifest digest
returned by describe) and `expected_wheel_sha256`. Mismatch yields
`identity_mismatch`; the server never assumes its latest docs match an installed
wheel. Cursors bind the manifest and query, preventing pages from different
snapshots being joined. The source/contracts/wheel content ID is distinct from
the manifest digest, which also binds tools, skill and reading layers.

Candidate count and core-envelope UTF-8 JSON bytes are bounded (`max_bytes`, default 32768,
range 4096..65536). Whole cards are deferred with an explicit reason and
continuation; scientific boundary text is never shortened to fit. One card over
budget returns `response_too_large`. Tutorials report slices and next offsets;
read the complete selected passage before executing a code example. `get`
retrieves one complete selected contract and API layer, preserving its boundary.
The official SDK also emits a text representation beside structured content;
the full MCP wire response has duplication and framing overhead beyond this
envelope budget. Hosts should set their wire budgets accordingly.

The initial backend is deterministic lexical AND with weighted lexical ranking,
case-insensitive phrase filters and exact device-scope enums. Reasons and score
are evidence about indexed text, not probabilities or physical suitability.
Ranking method is an implementation declaration, not a permanent protocol enum.
Later lexical, vector or service implementations must preserve these envelope,
identity, filtering, bounds, conflict and failure semantics. A backend change
requires a newly identified snapshot and a measured retrieval baseline; callers
must not infer correctness from a backend name. No remote server or vector
database is required by this delivery.

## Scientific use

Decompose a request into relationships, required inputs/outputs, units, shapes,
model, geometry, boundary conditions and device scope. Search each relationship,
read only selected contracts/Markdown, reject near misses, and verify connections
(units, normalization, shape, sign/index conventions, models and applicability).
Unknown ports or relations remain unknown until established. Do not enumerate
all possible compositions or load the entire catalog into the prompt. Candidate
recall and composition correctness are separate acceptance questions. Any glue
science must be explicit, tested and disclosed. The designated scientific owner
accepts the result's applicability.

## Deployment choices

Local/platform sandbox: install the separate SDK lock and start
`python tools/server.py --root PATH --transport stdio`; the host owns lifecycle.
Hosted remote: the same entry accepts `--transport streamable-http`; default
binding is loopback. Before exposure, the operator must explicitly choose the
deployment location, TLS termination, authentication/authorization, allowed
origins/hosts, networking, monitoring and immutable snapshot rollout. These are
not inferred from a passing loopback test. Remote status is `NOT_DEPLOYED`;
Famou client integration is `NOT_RUN`.

The SDK negotiates revisions it supports. Record actual SDK/protocol versions
from the real client; do not label an old handshake as a new revision. Official
references: [transports](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports),
[tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools),
[Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Build and acceptance

At an explicitly authorized integration checkpoint, build the exact wheel and
fresh bilingual documentation snapshots from one clean source revision, then:

```bash
.venv/bin/python scripts/build_pure_delivery.py \
  --wheel dist/wheels/scirel-0.1.0.dev11-py3-none-any.whl \
  --docs-en dist/docs-en-NEW --docs-zh dist/docs-zh-NEW \
  --output dist/PRIVATE/agent --html-output dist/PRIVATE/html
```

The builder refuses overwrites and mismatched dirty/source/catalog identities.
It derives the runtime lock from the actual wheel metadata. The repository's
development `uv.lock` is not a consumer runtime lock. Dependencies are downloaded
by the platform; pure Python does not mean dependency-free. Python is currently
`>=3.14,<3.15` and NumPy, SciPy and mpmath remain mandatory.

Agent API/tutorial Markdown is projected from the same rendered, contract-bound
HTML content, retaining code/output and linking selected exact contracts. HTML
is exported separately for human browsing and can be statically hosted without
being an Agent prerequisite. Both manifests bind the same source and contract
content digest. Generated output does not prove individual page review or
scientific runtime validation. Rights/notice statements are preserved; this
checkpoint does not authorize public publication.

Record actual wheel SHA/RECORD/public and withheld exposure, installed import
paths, dependencies, retrieval/get/call/result/failure checks, and environment.
Real cross-domain, Chinese/English, alias, wrong-boundary and missing-capability
probes form a bounded retrieval baseline, not a complete recall benchmark.
Synthetic thousands-card timing/pagination/size checks are resource tests only.
macOS results must never be labelled Linux/Famou acceptance. Platform installation,
native tool adaptation, hosted HTML, composition quality and human acceptance
remain `NOT_RUN` until executed there.

## Maintenance and drift gates

Keep `asset_id` stable when a function is renamed or moved between modules;
scientific identity and taxonomy/handbook placement are maintenance decisions,
not automatic consequences of the Python path. Change the canonical contract
and implementation together, then update its bound Chinese reader, direct tests
and affected authored tutorials. Never add aliases to hide a missed migration.

The unified export starts with the exact current public contract set. Fresh
bilingual docs capture generation-time input hashes (contracts, readers,
handbooks, Sphinx configuration/templates/static assets and generator code),
and reject input changes during generation. Export rejects missing/extra IDs,
stale contracts/API mappings, mixed languages/input hashes, stale sidecars,
unknown tutorial references/imports and local broken links. It reuses precise
runtime signature/input checks and the existing catalog/source/wheel closure,
then compares every installed package source/data member to the selected source
bytes. An old wheel retaining the same version and symbol names is insufficient.
The exact wheel's RECORD, metadata, notice bytes and exposure are also checked.

Both output manifests bind source SHA, contract content, exact wheel, generation
inputs and a common batch identity. The ignored canonical flat skill is a
separate hashed source input; clean Git SHA alone does not reproduce that file.
The skill's tool names must exactly match the registry. New non-overlapping output
directories and exact member inventories prevent old cards/pages from surviving
a rename. The outer batch receipt binds both immutable manifests and ZIP hashes;
acceptance records are sidecars and never silently change already selected pins.

Authored tutorial dependencies are derived from doc references and Python import
blocks. Unknown/renamed public APIs fail closed. A chapter referencing an
unavailable capability is replaced by an explicit subset placeholder in each
language, without publishing unavailable code or an unavailable API page. The
current diagnostics/inference chapter is such a placeholder; it must not count
as a completed runnable tutorial. Standalone magnetostatics and kinetic tutorials
retain existing execution/content bindings, including explicit English
placeholders where English text is unauthored. Other authored RST chapters get
current reference/import/contract hashes with scientific `review_status: NOT_RUN`.
Those hashes are traceability, not automatic natural-language semantic review.

Maintenance sequence: modify canonical truth → check affected readers/tutorials
and imports → build fresh bilingual snapshots and exact wheel from one clean
candidate → unified export/closure check → installed-wheel checks and real stdio
and HTTP smoke → issue a new immutable bundle. Select tests by changed paths;
small changes do not require a scientific full-suite run. Validation success
does not prove every natural-language page scientifically correct.

The delivery maintainer owns this task's build stages, smoke environments and
receipts. Export uses isolated stages and removes them on any failure; incomplete
Agent/HTML directories are never left as deliverables. After a candidate is
replaced and its inputs are no longer used, retain only its minimal failure cause
and regression result, then remove the abandoned wheel/docs/partial package.
After successful handoff remove this task's duplicate environments, test scratch,
build/egg-info and source bytecode caches. Keep the final immutable bundles and
small receipts until explicitly superseded. Read and resolved issue/handoff items
are closed or removed from the current entry; history belongs to Git and the task
record. Do not keep stale open checklists or extra handoff copies.
