# CodeFusion Consumer Contract

## Status and authority

- Status: development handoff contract
- Inbound producer: CodeFusion `ScientificAssetLibraryOwner` handoff exporter
- Inbound consumer: SciRel assembly maintainers
- Downstream consumer: CodeFusion runtime/plugin integration after SciRel release
- Non-goal: redefining CodeFusion review, admission, publication or public-site schemas

This document defines both sides of the integration boundary: the admitted input that SciRel can consume and the release tuple that SciRel can later hand to CodeFusion. It does not copy CodeFusion owner records. The authoritative CodeFusion contracts remain its inbound public-documentation and Python-distribution requirements/designs; the assembly record remains an engineering join record rather than a new governance store.

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

The current producer contract is the single-admission `codefusion.scirel-admitted-input.v1` manifest owned by the CodeFusion `ScientificAssetLibraryOwner` handoff DTO (`domains/inbound/codefusion-scientific-asset-library-owner/src/handoff.rs`) and emitted by the application exporter (`application/codefusion-application-product/src/bin/codefusion_scientific_asset_export.rs`). SciRel does not define a replacement schema and must decode the producer's exact shape. A dependency closure is transferred as separately exported manifests, one per admission; there is no batch `assets` wrapper in v1.

| Current field | Producer source | SciRel handling | Authority |
| --- | --- | --- | --- |
| `schema` | handoff exporter | require exactly `codefusion.scirel-admitted-input.v1` | export metadata |
| `tenant_id` | admission owner scope | retain only in private assembly evidence; never project it into public SciRel documents | governance fact |
| `admission` | admitted case/decision/source/revision record | bind `admission_ref`, kind, exact source, version commit/root digest and operator or TaskGraph revision | admission fact |
| `owner_snapshot_ref` | selected immutable version tree | bind all projected files to the selected owner snapshot | admission/export fact |
| `owner_snapshot_root_digest` | VersionedObjectOwner tree | verify the selected snapshot root; do not rename it to another digest field | admission/export fact |
| `dependency_bindings` | admitted TaskGraph revision bindings | identify exact dependency revisions; export each referenced admission separately | admission fact |
| `scientific_contract_ref` | matching `scientific_contract` file receipt | optional `{path, sha256}` pointer to `operator.md` or `task_graph.md` | admitted content pointer |
| `files` | owner tree plus verified bodies | consume exact `path`, `sha256`, `size_bytes` and producer-defined `role` receipts | admitted content fact |
| `gaps` | exporter-observed missing owner projections | preserve each `{field, reason}` without inventing a replacement fact | explicit absence fact |

The manifest decoder fails closed on an unknown schema/field, unsafe path, invalid digest or inconsistent revision binding. It does not reject a valid admitted-input export merely because `gaps` reports missing information. In particular, `license_evidence`, an independent `source_provenance_ref`, and a missing `scientific_contract_ref` are allowed gap fields in v1 because the current CodeFusion owner does not supply those facts.

SciRel must preserve such gaps rather than treating them as satisfied. A missing scientific contract blocks canonical-document standardization for that asset. Missing license or source-provenance evidence becomes a release/production blocker only when the selected SciRel release policy requires that evidence; it is not a reason to reject or misdecode the admitted-input manifest itself.

The following fields are SciRel-derived and should not be required as CodeFusion admission facts: SciRel `asset_id`, taxonomy, module path, public symbol/signature, package layout, implementation version, catalog facets, summaries and adapter/MCP metadata. SciRel records their mapping during assembly and changes them only under its own compatibility and scientific-review rules.

## Release binding

A runtime integration pins one coherent tuple after admitted-input gaps required by that release policy have been resolved:

1. every selected single-admission handoff's `admission_ref`, `owner_snapshot_ref` and `owner_snapshot_root_digest`, plus a SciRel-recorded digest of the received manifest/file set;
2. SciRel distribution name and `distribution_version`;
3. the SciRel admitted-manifest digest and distribution content lock generated from the selected inputs;
4. wheel SHA-256;
5. catalog `release_version`, root digest and coverage declaration; and
6. parity of the distribution export set, canonical document set and declared complete catalog set.

The received-manifest digest is SciRel assembly evidence, not a new CodeFusion owner field. The catalog builder requires every canonical document's `implementation_version` to equal `release_version`. The thin adapter additionally requires the installed `scirel` distribution version to match the selected document. CodeFusion must reject a mixed tuple; it must not use an unpinned `latest` wheel or catalog. The tuple is a release binding, not another per-asset governance hash.

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
