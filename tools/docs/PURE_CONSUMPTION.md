# Portable scientific consumption

SciRel's consumer runtime supplies complete original public contract JSON, a
lightweight discovery index, the self-contained `scirel-solving` skill, query
tools and an exact Python wheel. Contracts are derived from the code and carried
verbatim to the consumer. Discovery is derived from their metadata rather than a
second classification table. Human API pages, tutorials and the bilingual site
have a separate documentation pipeline.

The consumer is a static asset for general agents. The outbound agent owns the
program and task graph it creates for a user request; the consumer runtime does
not collect, execute or report that private graph to SciReL. See the project
boundary and graph-role rules in [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Source queries during development

Daily queries read the current public source layer without a wheel or export:

```bash
.venv/bin/python scripts/scirel_docs.py query --source-root . --describe
.venv/bin/python scripts/scirel_docs.py query --source-root . --q coulomb --limit 3
.venv/bin/python scripts/scirel_docs.py query --source-root . --asset scirel.physics.coulomb-ee
```

`--source-root` and `--snapshot` are mutually exclusive. Source queries read
public contracts and bound Chinese readers, using HOLD only to exclude withheld
assets. `--reader ASSET_ID` returns the Chinese reader. Responses bind HEAD,
dirty state and public-input digests; reuse `source_identity_sha256` through
`--expected-digest` to reject drift. `wheel_binding: not_bound` excludes an
installed-wheel or scientific-execution claim. Malformed inputs produce
`metadata_error`. Relevant authored tutorials live in `tools/docs/manual/` and
`tools/docs/manual/en/`.

## CLI and optional MCP

The exported `skills/scirel-capability-discovery/scripts/query.py` is the standard-library CLI. It requires
neither an MCP connection nor its SDK. Source `scripts/query.py` is copied to
that path unchanged; the repository keeps no skill-side source copy. Without
`--root`, the current working directory must be the package root. The CLI derives its commands and arguments from the same
registry and calls the same dispatcher as MCP:

```sh
python <package>/skills/scirel-capability-discovery/scripts/query.py --root <package> describe
python <package>/skills/scirel-capability-discovery/scripts/query.py --root <package> search --q coulomb --limit 3 --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
python <package>/skills/scirel-capability-discovery/scripts/query.py --root <package> get <asset-id> --expected-snapshot-sha256 <snapshot_sha256> --expected-wheel-sha256 <wheel_sha256>
```

`--root` precedes the command. Take both pins from `describe`, then preserve them
through selection and reading. CLI errors are JSON envelopes with a nonzero exit
status; parser errors also return nonzero. Query operations do not run science.
Use the installed wheel's ordinary public Python functions in the task program.
Install the wheel named by `describe.runtime.wheel` with `python -m pip install <package>/wheel/<wheel>` in the declared Python runtime. Scientific requirements are also in `runtime-requirements.txt`; optional MCP uses `mcp-requirements.txt`.

| CLI command | MCP tool | result |
| --- | --- | --- |
| `describe` | `scirel_describe` | identity, limits, schemas and runtime declarations |
| `browse` | `scirel_browse` | bounded capability cards |
| `search` | `scirel_search` | ranked candidates with match/conflict reasons |
| `get` | `scirel_get` | one complete original JSON contract, byte digest and path |

These are the only runtime query operations. Contracts use their original
English fields; retrieval has no language selector or tutorial collection.

MCP adds the official pinned SDK as a transport adapter. For stdio the client
launches `python skills/scirel-capability-discovery/scripts/server.py --root <package> --transport stdio` and owns its
lifecycle. For loopback Streamable HTTP, start the same server with
`--transport streamable-http --host 127.0.0.1 --port 8765`; its endpoint is
`http://127.0.0.1:8765/mcp`. Keep the server and client in the selected execution
environment. Record actual negotiated SDK/protocol versions when checking a
host; a local smoke test does not establish another platform's acceptance.

## Runtime identity and bounded retrieval

`runtime.json` uses `schema: scirel.consumer-runtime`. It is generated from the
selected public source and actual output bytes: source revision, asset count,
wheel metadata/hash, retrieval declarations and the member integrity map.
`snapshot_sha256` hashes its canonical JSON with that field omitted. This small
runtime identity supports selection, continuation and byte integrity. Consumer
execution does not require delivery manifests, build receipts or development
evidence. An input hash establishes consistency, not scientific qualification.

Responses use `schema: scirel.consumer-response`, command, source revision,
`snapshot_sha256` and `wheel_sha256`. `describe` optionally checks a supplied
wheel pin. All other commands require `expected_snapshot_sha256` and
`expected_wheel_sha256`; a mismatch returns `identity_mismatch`. The server
checks its selected runtime bytes, not the client's installed Python environment.
Record the actual installed wheel separately when making execution claims.

Capability cards are bounded by count and core JSON bytes: default limit 5,
range 1..100; `max_bytes` defaults to 32768, range 4096..65536. Whole cards are
deferred with explicit continuation rather than shortening scientific limits.
A single over-budget card returns `response_too_large`. Follow a returned cursor
with the same pins/query; omit an explicit offset when following the cursor.
The card budget applies to `browse` and `search`. `get` returns the complete
selected contract even when it exceeds 65536 bytes; it does not truncate fields
or introduce pagination. MCP framing/text duplication exceeds the card
core-envelope byte budget.

Filters cover capability, operation, model, geometry, boundary, device scope,
taxonomy and aliases. Discovery keeps `retrieval.completeness: unknown` and
`scientific_applicability: not_assessed`. `match` describes indexed metadata;
`near_miss` is not an applicable substitute. `no_candidates` is a bounded
retrieval result, not proof of scientific absence. Corrupt or malformed metadata
returns `metadata_error`, while caller mistakes return `invalid_request`.
Missing metadata stays unknown. `get.document` preserves the selected complete
original contract; `paths.contract` identifies its runtime-relative file and
`digests` reports that file's byte digest. Generated human reading is not
embedded in the structured response.

The initial backend uses deterministic lexical AND and weighted ranking. A
score measures indexed-text relevance, not physical suitability or probability.
A later backend must preserve filtering, identity, bounded continuation and
failure semantics and establish its own measured retrieval baseline.

## Skill and scientific use

The sole method source is `skills/development/usage/scirel-solving/`. Its concise
`SKILL.md` links to scientific guidance and the optional CSV delivery helper.
Export copies the reachable files unchanged under `skills/scirel-solving/`,
retaining `references/` and `scripts/`. Local links must resolve inside that
single skill; cross-skill references, missing helpers and symlink inputs fail
export. Unlinked source-local files are not runtime inputs. Captured bytes are
rechecked before return and again during export, and those same bytes are used
for hashing and output. Editing an exported package is never a source update.

Start from the requested scientific relations, then select a few candidates and
read their complete contracts. Check model, geometry,
boundary, units, normalization, signs and shapes before composing calls. Make
supplementary science explicit, executable, checked and disclosed. Distinguish
candidate recall, connection correctness, numerical checks and the designated
scientific owner's final applicability decision. Relevant human API pages and
tutorials are optional supplementary reading when separately supplied.

`describe.human_documentation` is
`{"status":"unconfigured","locator":"asset_id"}`. An asset ID supplies a
logical lookup key; it does not imply a site URL. Use only an actual supplied base,
version and generated page map to locate human reading, and check their binding
before claiming that they describe the selected wheel. The runtime neither
fetches a site nor assumes that “latest” denotes the installed release.

## Export and maintenance

Development normally changes source and runs affected tests. At an explicitly
authorized delivery checkpoint, supply one exact wheel:

```bash
.venv/bin/python scripts/build_pure_delivery.py \
  --wheel <exact-wheel.whl> --output <new-agent-root>
```

The builder reads the public contract set, bound Chinese sidecars and HOLD
selection directly from source to derive the index. It refuses overwrites and
mismatched source/catalog identities, checks exact public asset coverage and
wheel RECORD/content/notices, and binds the actual runtime inputs and output
bytes. Runtime requirements come from that wheel's metadata; MCP requirements
remain separate. Python and scientific dependencies are installed in the
selected host environment. Pure Python does not mean dependency-free.

Runtime export does not build or load a documentation snapshot, import Sphinx,
or require a generated HTML tree. API/tutorial Markdown, tutorial indexes,
images and site download assets are not runtime members. The skill states the
minimal installation command using the actual wheel and requirement files;
CLI help supplies the command syntax.

Build human documentation independently with the existing documentation tool:

```bash
.venv/bin/python scripts/scirel_docs.py build --language en --output dist/docs-en
.venv/bin/python scripts/scirel_docs.py build --language zh --output dist/docs-zh
```

Its contract/reader bindings, source signatures, authored examples, local links
and generated resource checks remain documentation responsibilities. Preserve
the authored guides, Chinese readers, API rendering and site sources. Build
checks and scientific review evidence remain with their existing development
or task authorities; they are not consumer execution prerequisites. Building a
site or hashing its inputs does not establish manual page review.

Change canonical contracts and implementation together with bound Chinese
readers and affected authored tutorials. Keep stable scientific asset identities
when moving Python symbols; do not add aliases to hide an incomplete migration.
Unknown or unavailable tutorial dependencies fail closed or become explicit
subset placeholders, never runnable examples that silently require hidden code.
Generated hashes do not prove semantic page review or scientific validation.

Select tests by changed paths. When a delivery is authorized, validate its actual
installed wheel and real CLI/MCP operations, preserving failures and platform
limits. Retrieval probes and synthetic scale tests have their stated scope;
they do not prove complete recall or scientific correctness. Publication,
rights decisions and host-specific acceptance require their own evidence.
Repository record retention and cleanup follow `catalog/RECORDS.md`.
