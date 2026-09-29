# r43 expert and license decision handoff (2026-09-30)

This is a read-only map of decision inputs, not a review decision, a release
selection, or another candidate index. D2 alone maintains the unified
[`release-index.dev.json`](../../provenance/release-index.dev.json), frozen for
this handoff at SciRel `274f2e6378d1f349be2a81449ed4021cd2a0679e`.
It has 14 entries and no `released` entry. The current r43 candidate is
`candidate:1d02ae5282f0947a40f5e15bb30df1ca9613fdd491d5012ab7b204f88d6c2218`
with `bounded_d1` source qualification and `pending_unapproved` state.
The 13 review items have zero approvals.

The identity map below is from the downloaded CodeFusion `3c69931b` V1
project `prj_06b93ac5f20676cf034d2e8c171eb73e628a` revalidated snapshot:
`cf://artifact/upload_8626eb5a90acbcc0cdc2688423e437e3ddf0faa28616cb2c`,
SHA-256 `5046888289573d540d65f28622aa872d57d1e344c3b1b3b86a2ef81c106c3a7d`.
The exact receipt and verification limits are in
[`r43-current-review-selection-acceptance-20260930.json`](../../provenance/r43-current-review-selection-acceptance-20260930.json).
This is state at capture time, not a live revision lock. CodeFusion
`936e339f9a3fb835466482400fa9702fcc27650c` only adds ZIP projection
integrity checks; it does not replace this reviewer installation or bind its
source fixture to the corrected wheel/catalog tuple.

## Item map

`A0` is the submitted workflow Artifact
`cf://artifact/upload_2e000a0be7e3720fb8f91437587ce911f737b51d4cb94ce0`,
SHA-256 `0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`.
`A1` is the Weideman `request-evidence` successor
`cf://artifact/upload_5c744cb31d7df92f9a66dc01da4e80ceb3d780f68b954aa2`,
SHA-256 `7b02936c800184fea8e8fdc37e26e2155190a35682330789eac4aaf6c9beabc9`.
The table's Artifact column identifies the exact current ref and digest by
these definitions. Short asset names have prefix `scirel.kinetic.`; linked
documents contain the maintained scientific contract, test scope,
limitations, and provenance. For two rows identified below, the linked
maintained document is newer than A0; use the embedded A0 document to inspect
the exact submitted review input. Every item still needs its own scientific
and license decision.

| Asset document | Item ref | Current Artifact / status | Scientific decision focus |
| --- | --- | --- | --- |
| [kinetic-dispersion-ronnmark](../../catalog/examples/scirel.kinetic.kinetic-dispersion-ronnmark.json) | `scirel-review-item:0d72a89726790d2dda217f52b8ee89b7e433b8de80074ba8545945989b2a7cd6` | A0 / review_pending | J=8 Ronnmark response, complex `kx`, zero `kz`; resolve document revision mismatch below. |
| [plasma-dispersion-weideman](../../catalog/examples/scirel.kinetic.plasma-dispersion-weideman.json) | `scirel-review-item:32db97d7421ba776be0e18137e5cf7be726892f3ba0fda8ec894b1ff4ef2409c` | A1 / needs_evidence | Fixed N=64 branch behavior and source rounding; specify and resolve the requested evidence. |
| [kinetic-dispersion-relation](../../catalog/examples/scirel.kinetic.kinetic-dispersion-relation.json) | `scirel-review-item:4956e12b305ce4bc1b6c4c84a120cfe2379da0ee07d570a85cce3c2935180e2a` | A0 / review_pending | Distinct finite-sum and Ronnmark tensor paths in one DAG. |
| [ronnmark-r-function](../../catalog/examples/scirel.kinetic.ronnmark-r-function.json) | `scirel-review-item:70f123df50f85f7e577b35ee670fe2d7f340c639e457b6542e40d581b7ab4746` | A0 / review_pending | Four-way Taylor/asymptotic/integral selector and complex comparison range. |
| [fluid-dispersion-matrix](../../catalog/examples/scirel.kinetic.fluid-dispersion-matrix.json) | `scirel-review-item:73311c0902bf4fea7a999dcb2f05b398d6839b2e7ba83f3cbef7204bceba6b57` | A0 / review_pending | First-order matrix dimensions and singular resonance behavior. |
| [kinetic-wavevector-roots](../../catalog/examples/scirel.kinetic.kinetic-wavevector-roots.json) | `scirel-review-item:765b51697dfde7549eb64be905d7bfe069c067359b28dc1b8f7e8574a1176338` | A0 / review_pending | Fixed-seed complex roots, exit flags, and signed branches; resolve document revision mismatch below. |
| [kinetic-wavevector-scan](../../catalog/examples/scirel.kinetic.kinetic-wavevector-scan.json) | `scirel-review-item:97b2d568bf22479fa0607ed283031bee18ede42f0af50d35cea9807cf3f73861` | A0 / review_pending | Internally derived frequency ladder and root-scan DAG. |
| [dielectric-tensor-diagnostic](../../catalog/examples/scirel.kinetic.dielectric-tensor-diagnostic.json) | `scirel-review-item:a4cb5bcde3c211b89538069142ed795eccaa9fccda4fa30dfa33f6785b35fd63` | A0 / review_pending | Full tensor, default `lmx=15`, complex `kx`, and no near-zero `kz` clamp. |
| [gamma-lpole-coefficients](../../catalog/examples/scirel.kinetic.gamma-lpole-coefficients.json) | `scirel-review-item:a7390a0bde779cc2369267d712f7a1f662a54a68da9db7f09096e8be986153d5` | A0 / review_pending | Source L-pole tables and `abs(n)+1` indexing. |
| [kinetic-dispersion-sum-fluidbw](../../catalog/examples/scirel.kinetic.kinetic-dispersion-sum-fluidbw.json) | `scirel-review-item:aff9acd9190c72756012f8e024d2acdf5a3b6d94e3154c32167652ed2ece3e72` | A0 / review_pending | Finite harmonic sum and positive `1e-10` near-zero `kz` clamp. |
| [fluid-wavevector-eigensolve](../../catalog/examples/scirel.kinetic.fluid-wavevector-eigensolve.json) | `scirel-review-item:cd36240e581126c52b8ba503ba40f4430fd18ae72e1986427210337e7669c3a0` | A0 / review_pending | General complex `zgeev` and positive-real/least-damped branch selection. |
| [fluid-wavevector-scan](../../catalog/examples/scirel.kinetic.fluid-wavevector-scan.json) | `scirel-review-item:d785c16d2176aee3c613ca8ece45a6bd068147aa5682bb6a069e02539e253373` | A0 / review_pending | Internal frequency ladder, scale normalization, and fluid DAG. |
| [z-pole-coefficients](../../catalog/examples/scirel.kinetic.z-pole-coefficients.json) | `scirel-review-item:e15fcd9f1e0bd55bfb243bdb6cee3a86aff0caa9f746c58f4b213adbcc5c70fe` | A0 / review_pending | Source J=8/12 residues and conjugate pole completion. |

The [D2 comparison](2026-09-29-fluidbw-r43-d2-comparison.md) identifies the
scientific distinction and tested limits for every row. The candidate's
original source workflow is saved at CodeFusion
`.runtime/reviewer-current-r43-source-3c69931b5.json`; the A1 successor and
revalidated host snapshot are saved beside it. The separately saved CodeFusion
`.runtime/m3-r43-b1ab-review-prep/workflow.json` is 1,606,003 bytes and has
the same A0 SHA-256. An authorized reviewer must
refresh the current item/revision in the host before acting. The bounded
ordinary-user recovery is recorded separately in
[`r43-current-ordinary-recovery-acceptance-20260930.json`](../../provenance/r43-current-ordinary-recovery-acceptance-20260930.json);
it does not turn the reviewer fixture into an installed-wheel backend.

## Selectable closure

These are minimal **runtime/document dependency** closures for a target asset,
not approved release subsets. Names below carry the `scirel.kinetic.` prefix.
The maintained `version.dependencies` and package-local imports determine
the transitive closure; every member needs an exact current document,
scientific decision, and distribution-license decision.

- One-item closures: `plasma-dispersion-weideman`, `ronnmark-r-function`,
  `fluid-dispersion-matrix`, `dielectric-tensor-diagnostic`,
  `gamma-lpole-coefficients`, `kinetic-dispersion-sum-fluidbw`,
  `fluid-wavevector-eigensolve`, or `z-pole-coefficients`. Weideman is currently
  `needs_evidence`; none is approved.
- `kinetic-dispersion-ronnmark`: itself plus `ronnmark-r-function`.
- `kinetic-wavevector-roots`: itself, `kinetic-dispersion-ronnmark`, and
  `ronnmark-r-function`.
- `kinetic-dispersion-relation`: itself, `species-equilibrium-scales`,
  `kinetic-dispersion-sum-fluidbw`, `kinetic-dispersion-ronnmark`, and
  `ronnmark-r-function`.
- `kinetic-wavevector-scan`: itself, `species-equilibrium-scales`,
  `kinetic-wavevector-roots`, `kinetic-dispersion-ronnmark`, and
  `ronnmark-r-function`.
- `fluid-wavevector-scan`: itself, `species-equilibrium-scales`,
  `gamma-lpole-coefficients`, `z-pole-coefficients`,
  `fluid-dispersion-matrix`, and `fluid-wavevector-eigensolve`.

`species-equilibrium-scales` was absorbed in D2 and has an
[existing document](../../catalog/examples/scirel.kinetic.species-equilibrium-scales.json),
but it is outside these 13 review items, has no released baseline, and remains
`pending-human-decision` for license. The three graphs that depend on it
cannot form a first public release from this 13-item batch alone. D2 must
bring an exact selected version through the same unified index and review
path, or exclude those graphs. The other absorbed r43 input, `bessel-gamma`,
is not a declared member of these closures.

## Differences To Resolve

The A0 review item and unified index bind the original SciRel `cc2fa21`
documents. Eleven maintained documents still match their indexed canonical
digests. Two were changed later in SciRel `d794fdc` to declare real module
dependencies and do **not** match the exact documents currently before the
reviewer:

| Item | Indexed A0 document digest | Maintained document digest | Missing A0 dependency |
| --- | --- | --- | --- |
| `kinetic-dispersion-ronnmark` | `sha256:1e46df1ba8b7cd17edb6eaf4687be11ce527a03b5f63d8ffd22cec59c1369396` | `sha256:2c79d1dc3ace5516f57b212eab2794e4118e42139daa69234d5d9a888b166033` | `ronnmark-r-function` |
| `kinetic-wavevector-roots` | `sha256:8771407744edb8adb71fa64276e9cdfd6ce824b076c32c263dc5ad08d6e7885e` | `sha256:6d9e7459db7f6f768bcdae3a0a690eb91c315252851cf0d0ac3d2a7d1d2d5aa7` | `kinetic-dispersion-ronnmark` |

The corresponding maintained modules import those dependencies. Do not ask
the expert to approve the newer document as though it were A0. D2 checked
the saved 1,606,003-byte original workflow body against the host receipt and
indexed `initial_revision`; its SHA-256 matches A0. Both submitted documents
and the draft dependency list are empty for these edges, and SciRel's review
adapter yields `dependency_asset_ids=[]` for both exact item refs. The index
is faithful to that frozen submission. Neither item has a corrected successor
in the saved 13-item export; this does not establish its live host state.
A corrected review path needs host-issued exact successors with the maintained
documents and dependency lists, or a newly submitted workflow and candidate
that D2 registers with an append-only lifecycle event. Neither frozen
candidate version is rewritten. Until then, these two items and their
dependent graphs are not closed release selections. Release checks require
the approved item dependency list to match its exact document and every
selected dependency to be present.

Technical route check on 2026-09-30: the installed SciRel review action contract
offers only approve, request-evidence, and reject. Its successor copies the
submitted `asset` and `dependency_asset_ids`, so an action on either A0 item
cannot carry the corrected document. An intake using the old `candidate_id`,
`draft_id`, asset order, and asset IDs would regenerate the same item refs;
CodeFusion `admit-index` only replays identical source Artifacts and rejects a
different binding for an existing ref. A new `draft_id` (or candidate identity)
is therefore required for a new workflow. The standardization gate also
requires complete accounting of the original source assets, matching candidate
and source digests, the exact SciRel Git base and skill digest, and internally
consistent review units. For these two units, both `asset_document` and the
embedded `candidate_document` must reflect the maintained exact document, with
updated embedded digest and `dependency_asset_ids`; code, tests, and evidence
must be checked against the new frozen base. Reusing the old submission JSON
with only its document fields patched is not a valid new review handoff.

The local CodeFusion endpoint `127.0.0.1:18096` refused a connection during
this check, so live item state, project authorization, and any new intake could
not be revalidated. No corrected successor, new host receipt, or new candidate
Artifact was produced. The next technical owner must first restore the
reviewer host and refresh both item revisions, then prepare and validate a new
complete standardization submission from a frozen SciRel base. After an
authenticated intake and index admission, give D2 the exact workflow Artifact,
digest, item refs, dependency lists, host receipt, and Git revision. D2 alone
registers the new candidate and then appends the old candidate's `superseded`
lifecycle event with exact evidence. Neither step implies scientific or license
approval.

The A1 Weideman item is `needs_evidence`, not approved. Its successor retains
general census, producer-build, scientific-approval, and license gaps; the
decision notes do not specify a narrower scientific question. The reviewer
must state what evidence is requested and review a new exact current revision.
Across the batch, the D1 source-scope freeze, D2 finite numerical oracles,
direct tests, installed-wheel checks, and ordinary-user results have the
scope stated in each document's `verification` field. They do not prove
arbitrary-input parity or substitute for a scientific decision. Exact
producer model/harness build identifiers are still unreported; record a
specific need for them where they affect a selected decision.

All 13 candidate documents have `provenance.license_status` set to
`pending-human-decision` and no public reference entries. The license owner
must decide distribution rights and conditions for each selected code and
document, plus the actual runtime dependencies; a scientific decision does
not grant those rights. The whole corrected development wheel/catalog has
`mixed_unverified` source material outside the 13-item slice, so its ordinary
execution cannot be treated as an approved-only package. The current shared
reviewer installation declares `release.artifacts=[]` and a source-manifest
fixture; CodeFusion's later ZIP integrity fix at `936e339f9` does not close
the same-wheel/catalog/backend/registration gap.

The historical 52-item snapshot and inaccessible old project are not a
census or completeness gate for this selected r43 slice. Its earlier
`admission` labels are not approvals. If a selected asset's source scope or
rights cannot be established from the bounded r43 and current SciRel records,
request that **asset-specific** evidence; do not reconstruct the old pool.

For each item, request a host-authenticated scientific disposition on the
exact refreshed `item_ref` and current Artifact, including accepted scope or
the specific missing evidence. Separately request the license owner's
documented decision for every selected closure member. D2 then binds only
the resulting exact decisions and artifacts in the existing unified
development index; outbound owners hand D2 changed Artifacts, dependencies,
and review evidence rather than making another authoritative pool. Its `.dev`
structure may evolve during integration and must converge to `v1` before
formal public release. This map makes no approval or publication claim.
