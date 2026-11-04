# CodeFusion Consumer Contract

## Status and authority

- Status: development handoff contract
- Scientific owner: SciRel plugin and SciRel core
- Host: CodeFusion or another neutral Agent harness
- Compatibility policy: no legacy admission-flow compatibility before v1

SciRel owns scientific assets, catalog records, documentation, skills, review semantics, and releases. CodeFusion
owns sessions, identity, permissions, generic artifacts, execution, audit storage, UI containers, and delivery. It
does not need SciRel-specific database tables or scientific state in its kernel.

The host selects one fixed plugin registration for each run. The development example is
[`contracts/examples/scirel-plugin-registration.dev.json`](../../contracts/examples/scirel-plugin-registration.dev.json).
Its neutral `release` object carries an opaque plugin release ref, ArtifactReferences for the skill bundle and catalog,
portable skill entrypoint locators, an optional connector descriptor, and versioned runtime dependency refs. Updating
or uninstalling the plugin affects new runs only; an active run keeps its selected snapshot. The example artifact refs
and digests are placeholders for the wire shape, not upload or release evidence; a real registration uses identities
issued by the host ArtifactOwner.

Release metadata is not execution authority. A connector descriptor does not establish a trusted endpoint, a declared
capability does not grant it, and a skill entrypoint does not request implicit loading. The host resolves each reference
through its owning registry and applies the current permission policy before exposing it to a run.

## Release binding

Only a SciRel release may enter runtime discovery. A runtime binding keeps one coherent tuple:

1. plugin release reference;
2. SciRel distribution version and runtime dependency reference;
3. wheel artifact reference and digest;
4. catalog artifact reference, release version, root digest, and coverage declaration; and
5. SciRel release manifest artifact reference and digest.

The catalog builder requires every canonical document's `implementation_version` to equal its release version. The
thin adapter additionally checks the installed `scirel` distribution version before resolving a callable. The host
rejects a mixed tuple and does not select an unpinned `latest` artifact.

Candidate drafts, expert-review artifacts, L1 bundles, tests passing, and generic Agent run completion do not create
a runtime binding. They remain outside catalog discovery until SciRel approval, baseline integration, and release
gates complete.

## Documentation and discovery

SciRel generates both machine discovery records and the human documentation site from approved
`scirel.asset-document.v1` exact documents:

```text
release.json
  -> routes/*.jsonl
  -> summaries/*.jsonl
  -> records/<prefix>/<asset-id>.json
  -> human documentation projection
```

Routes and summaries support progressive disclosure; the exact record remains scientific truth. CodeFusion may
display or link the human projection, but it does not author a second scientific page or join platform publication
fields into the canonical document. Private review, tenant, candidate, decision, and host audit fields remain outside
public documentation.

The current development catalog is partial. Failure to find an asset in incomplete coverage produces a bounded
search result, not a claim that the capability cannot exist.

## Callable and connector surface

The Python binding is `public_api.python.module`, `symbol`, and exact `signature`. The framework-neutral thin adapter
supports four logical capabilities:

- `catalog.discover`
- `asset.read`
- `callable.resolve`
- `callable.invoke`

CodeFusion may expose them through an MCP connector or another generic tool surface. Authentication, authorization,
session context, sandbox, timeout, cancellation, audit, and artifact delivery remain host concerns outside SciRel
request and document schemas. SciRel remains responsible for scientific input contracts, applicability, failure
semantics, result checks, and evidence ceilings.

## Error semantics

The adapter reports `invalid_request`, `asset_not_found`, `invalid_snapshot`, `snapshot_mismatch`,
`callable_mismatch`, `invalid_arguments`, `invocation_failed`, and `result_not_serializable`. A transport may map
these codes but must preserve the scientific exception cause and must not reinterpret them as approval or physical
truth.

## v1 boundary

Development schemas and media types may use `.dev`. After the first real L1-to-review-to-release workflow and the
scientific request workflow pass independent harness validation, freeze the public plugin, review, and release
contracts as v1. No branch is retained for the retired CodeFusion-owned admission flow.
