# CodeFusion Consumer Contract

## Status and authority

- Status: development handoff contract
- Producer: SciRel release and catalog maintainers
- Consumer: CodeFusion runtime/plugin integration
- Non-goal: redefining CodeFusion review, admission, publication or public-site schemas

This document lists what SciRel can hand to CodeFusion after library assembly. It does not copy CodeFusion owner records. The authoritative CodeFusion contracts remain its inbound public-documentation and Python-distribution requirements/designs; the assembly record remains an engineering join record rather than a new governance store.

The read-only comparison baseline was the following CodeFusion-owned material:

- `docs/domains/requirements/inbound/scientific-asset-public-documentation.md`
- `docs/domains/design/inbound/scientific-asset-documentation-and-catalog.md`
- `docs/domains/requirements/inbound/scientific-asset-python-distribution.md`
- `docs/domains/design/inbound/scientific-asset-python-distribution.md`
- `skills/development/codefusion-scirel-integration/assets/assembly_record.md`

Four records have separate responsibilities:

| Record | Authority |
| --- | --- |
| reviewer/candidate document | frozen pre-admission scientific review evidence owned by CodeFusion |
| admission/publication records | governance decisions and current published refs owned by CodeFusion |
| `scirel.asset-document.v1` | current SciRel scientific identity, callable, ports, applicability, failures, example and bounded public lineage |
| catalog route/summary records | rebuildable discovery projections derived only from canonical SciRel documents |

Joining them is allowed only at an authorized CodeFusion release or publication boundary using stable IDs. No join may write CodeFusion refs back into SciRel documents or reinterpret a SciRel build as approval or publication.

## Minimum CodeFusion handoff fields

SciRel does not define a replacement CodeFusion schema. The following is the minimum information the CodeFusion-owned handoff should expose, either directly or through immutable referenced records. Structured scientific content stays in one referenced normalized contract instead of being repeated field by field in the handoff manifest.

| Field | Source | Why SciRel needs it | Authority |
| --- | --- | --- | --- |
| `schema` | CodeFusion handoff exporter version | reject an unsupported handoff shape | export metadata |
| `owner_snapshot_ref` and `owner_snapshot_digest` | immutable `ScientificAssetLibraryOwner` export snapshot | pin the exact admitted export set and detect mixed runs | admission/export fact |
| `assets[].admission_ref` | final admission record | correlate assembly evidence without guessing from names or paths | admission fact |
| `assets[].asset_kind` | admitted operator/TaskGraph revision | select the correct normalization and dependency checks | admission fact |
| `assets[].version_commit_ref` and `version_tree_root_digest` | admitted immutable version tree | bind files, contract and dependency material to one accepted version | admission fact |
| `assets[].decision_ref` | final human review decision | prove the handoff did not stop at candidate or machine/AI assessment | governance fact |
| `assets[].dependency_bindings[]` | admitted TaskGraph/operator dependency closure | reconstruct and verify the exact dependency closure before assigning SciRel IDs | admission fact |
| `assets[].files[]` with `path`, `sha256`, `size_bytes` and a normalized `role` | frozen admitted version tree/package manifest | locate implementation, test, graph and contract inputs without filename inference | admitted content fact |
| `assets[].scientific_contract` with `schema`, `path`, `sha256` and `language` | normalized contract selected by the accepted candidate/version | obtain inputs, outputs, units, model, geometry, applicability, failures and source pointers without reusing reviewer prose | admitted content pointer |
| `assets[].source_provenance_ref` | frozen source/provenance record | preserve lineage while keeping private evidence out of public SciRel documents | admission evidence pointer |
| `assets[].license_evidence` with reviewed status and immutable evidence refs | accepted license review material | determine whether a SciRel release may redistribute the maintained implementation and public metadata | governance/evidence fact |

The handoff should fail closed when the contract pointer, file roles, dependency closure or license evidence cannot be resolved inside the same owner snapshot. It should not synthesize missing science from a display name or reviewer Markdown.

The following fields are SciRel-derived and should not be required as CodeFusion admission facts: SciRel `asset_id`, taxonomy, module path, public symbol/signature, package layout, implementation version, catalog facets, summaries and adapter/MCP metadata. SciRel records their mapping during assembly and changes them only under its own compatibility and scientific-review rules.

## Release binding

A runtime integration pins one coherent tuple:

1. distribution name and `distribution_version`;
2. wheel SHA-256;
3. admitted manifest digest and the corresponding distribution content lock;
4. catalog `release_version` and root digest; and
5. the catalog coverage declaration.

The catalog builder requires every canonical document's `implementation_version` to equal `release_version`. The thin adapter additionally requires the installed `scirel` distribution version to match the selected document. CodeFusion must reject a mixed tuple; it must not use an unpinned `latest` wheel or catalog. The tuple is a release binding, not another per-asset governance hash.

## Export set

For a complete release, the canonical document set must be dependency-closed and its asset/callable set must equal the selected distribution manifest export set. Each record supplies stable `asset_id`, kind, module, symbol, signature and stable dependency asset IDs. CodeFusion remains responsible for joining these public identities to the exact admitted or published revisions required by its owner contract.

The current catalog is explicitly `partial` with 4 of 52 admitted assets. It is valid development metadata but cannot demonstrate complete manifest parity, public-site parity or production plugin coverage.

## Documentation entrypoints

Consumers traverse one pinned snapshot in this order:

```text
release.json
  -> routes/*.jsonl
  -> summaries/*.jsonl
  -> records/<prefix>/<asset-id>.json
```

Routes and summaries are bounded projections; the exact record remains the scientific truth. The canonical SciRel record is suitable for maintainer and agent selection, but it is not the independently authored CodeFusion public-site article. A CodeFusion public exporter may project allowed scientific fields only after confirming a current `published` ref and joining its publication metadata and expert document. It must apply its own public redaction and parity rules.

## Public callable and MCP surface

The Python binding is `public_api.python.module`, `symbol` and exact `signature`. Structured inputs declare name, units, shape, dtype, required status, optional JSON-compatible default and constraints. Outputs, applicability, failure semantics, limitations and evidence ceiling remain in the exact document.

The SDK-free adapter exposes these logical requests:

- `catalog.discover`
- `asset.read`
- `callable.resolve`
- `callable.invoke`

Every successful response identifies the catalog root digest. Resolve/invoke additionally bind the selected asset and implementation version. CodeFusion may wrap these operations in its own MCP tools or runtime APIs, but authentication, authorization, session/project/workbench context, sandboxing, timeout, cancellation, audit and result delivery remain CodeFusion-owned fields outside the SciRel request/document schema.

## Error semantics

The thin core returns `ThinMcpAdapterError.code` values that a transport may map without discarding the original cause:

| Code | Meaning |
| --- | --- |
| `invalid_request` | malformed operation, filter or envelope |
| `asset_not_found` | requested ID is outside the pinned catalog |
| `invalid_snapshot` | catalog/document structure violates the contract |
| `snapshot_mismatch` | root or partition content differs from the pin |
| `callable_mismatch` | installed version, binding, signature or input/default contract differs |
| `invalid_arguments` | missing, undocumented or malformed argument names |
| `invocation_failed` | selected scientific callable raised; the scientific exception remains the cause |
| `result_not_serializable` | result cannot be represented by the bounded JSON materializer |

An exhausted discovery page is not `asset_not_found`; it returns a continuation cursor and bounded coverage state. Scientific exceptions, applicability limits and evidence ceilings must not be rewritten as platform approval claims.

## Current cross-project boundaries

The read-only comparison with CodeFusion's accepted inbound contracts identifies these intentional differences:

1. CodeFusion public export consumes only current `published` refs; the SciRel pilot is derived from admitted inputs and contains no publication claim.
2. CodeFusion public-site prose is independently authored by experts; SciRel canonical documents are maintained scientific/callable contracts and must not replace reviewer or public-site prose.
3. SciRel records include a bounded public lineage summary, while CodeFusion's public snapshot forbids provenance bodies. Therefore SciRel exact records cannot be copied unchanged to `/ai/v1/assets/{asset_id}.json`; CodeFusion must make an allowed projection.
4. CodeFusion public artifacts require revision ID, publication timestamp and human/machine URLs. SciRel intentionally excludes governance refs and publication state, so those fields can only be supplied by the CodeFusion owner/exporter join.
5. CodeFusion's frozen distribution design expects publication-bound `scirel/asset.json` entries and projection parity. SciRel currently supplies a four-document development pilot, not evidence that the published manifest/exporter connection exists.

These are integration boundaries, not reasons to duplicate either project's schema. Production handoff remains blocked on complete canonical coverage, owner-authorized publication/release binding, licensing and cross-framework source-free conformance.
