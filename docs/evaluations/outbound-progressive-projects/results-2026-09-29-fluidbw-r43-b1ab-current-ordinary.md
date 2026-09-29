# r43 corrected-wheel ordinary-user successor (2026-09-29)

This [development manifest](manifests/2026-09-29-fluidbw-r43-b1ab-current-ordinary.json)
continues the [source-free installed-wheel check](results-2026-09-29-fluidbw-r43-cc2fa21-outbound-check.md).
It records one real CodeFusion ordinary-user request on an isolated development
service. It is not scientific approval or stable outbound acceptance.

The request used SciRel source `cc2fa21e03fa7e5152c29f0769165863429e1693`,
corrected wheel SHA-256
`b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`,
and catalog release SHA-256
`fece59b88ad39480a58b3c35f7678b2007a578f5918a74533f5b0cae6dfe2d02`
(root `sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`).
The admitted input ZIP has SHA-256
`74bbb6d0ec371361a09c55572f353ae8ead33e3b4f35befcf56b570b8c75e17f`.
SciRel rehashed the saved ZIP and both wheel/catalog members. The qualified
r43 L1 ZIP was imported into the same project; its SHA-256 is
`166021e28d6aa6db71b61daff7e3671837f3dede218b41153b4c0d3186cb83bd`.
The L1 freeze does not approve the scientific assets.

CodeFusion source `2d3de66e04d81fcbb94fd069bb7f4d93630cd844` completed
ordinary request `appreq_f9ab1cd4d20826bb_a76d533b66556885` in project
`prj_38c6934b8953fb6651c4e3797e2c0029d3ce` with 27 completed operations.
The CodeFusion owner inspected that request's first kernel checkpoint: it froze
owner-resolved `scirel-solving` revision content digest
`sha256:9bdb51487d777807914e547fb965c37c832f7cf639c718dc5306cec820015220`,
environment version
`envver_ec473521fb8360a86cc4accc15e89a30e78240fc674677dd28cb9cdfff2929e6`,
and a Tool Plan containing `shell`, revision
`tool-plan@sha256:bddc07f3c1841e72be221bcd2987648966d0bc215f2eb34431892a8576c4e09d`.
All 22 shell calls carried that plan; the input ZIP was mounted read-only
under its exact digest. This closes the preceding record's missing same-request
skill/environment/Tool Plan trace for this development case. The full
owner-scoped skill URI remains in the host's local receipt, not in a SciRel
public science contract.

SciRel rehashed the locally saved project script (SHA-256
`4cb19947a848ee4c71c71f9fa7569d8305ce8a2abda82ffd631e99d4fd161da7`)
and result JSON (SHA-256
`582b6e6508654e5d7410630110ad4cb576126ef1a00128c504750b6ca5e1c823`).
The result records two `catalog.discover` pages covering 132 assets,
`asset.read(detail=document)` for Weideman, and two `callable.invoke` calls.
Both numerical checks against SciPy `wofz` passed, with absolute errors 0 and
`2.482534153247273e-16`. CodeFusion owns authentication, checkpoint and
product-state verification; SciRel's local inspection does not independently
authenticate the live service.

At this ordinary-user acceptance point, the earlier reviewer project's host
export had 13 items, one `needs_evidence`, 12 `review_pending`, and zero
approved. Its review plugin registration's release object contained only a
plugin release ref; CodeFusion's read-only database check found no wheel,
catalog, or runtime dependency refs. The 13-item review workflow remains valid
evidence, but that registration did not bind it to the `b1ab...` wheel. The
ordinary-user trace therefore closed one technical gap without completing a
same-tuple reviewer/ordinary acceptance at that point. An immutable development
registration or equivalent host binding for the exact SciRel tuple was still
needed.

Expert decisions, license clearance, approved-subset wheel/catalog
construction, release checks and `v1` contract convergence remain
prerequisites for stable distribution.

## Later reviewer successor on matching materials

CodeFusion `2d3de66e` subsequently ran a separate isolated reviewer project,
`prj_0b4158c393a55f538dae18802c15770ef756`. Its owner reports a new
development release ref naming the same SciRel source
`cc2fa21e03fa7e5152c29f0769165863429e1693` and wheel SHA-256
`b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`
with catalog snapshot ZIP SHA-256
`afee7fcf2d5bca4e04179aaaa1e1d98bdd689a8439c965f1b1c4580993c097e5`.
The ZIP's `release.json` has SHA-256
`fece59b88ad39480a58b3c35f7678b2007a578f5918a74533f5b0cae6dfe2d02`
and catalog root
`sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`,
matching the ordinary request.
CodeFusion checked the uploaded wheel/catalog Artifacts and ZIP contents;
SciRel checked saved local readback evidence, without independently querying
the product. The [reviewer handoff](r43-b1ab-reviewer-rebind-handoff-2026-09-29.md)
records the product and ZIP readback; D2's exact bindings are in
`provenance/r43-b1ab-review-workflow-acceptance-20260929.json`.

The new workflow
`sha256:0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`
and host export
`sha256:b9e2c8c990f821232f2a912163a8ae03a970faa52c49ced1a701d22e1de9eabd`
are bound to the same D2 development entry
`development:c9a63b3f8068626417895ecfdc45787045a46a2a78ff6972642f6e8164de0463`.
The export has 13 items, one `needs_evidence`, 12 `review_pending`, and zero
approved; D2's check is recorded in
`provenance/r43-b1ab-review-host-acceptance-20260929.json`. Alongside the
ordinary-user request, this establishes a bounded technical dual-chain
comparison of matching source, wheel, and catalog materials across two product
projects. The earlier manifest freezes the old reviewer candidate; it does not
bind the new workflow or show the new project's immutable neutral registration
snapshot ref, digest, and field list. An opaque release ref and matching
material hashes alone do not establish formal same-tuple product acceptance.
The earlier manifest's `not_claims` and reviewer receipts retain their
historical scope; no old review decision is transferred. This wheel/catalog
remains `mixed_unverified` and
`pending_unapproved`, so the technical evidence is not a stable release.

At this acceptance point, the D2-maintained
`provenance/release-index.dev.json` records current reviewer candidate
`candidate:1d02ae5282f0947a40f5e15bb30df1ca9613fdd491d5012ab7b204f88d6c2218`
and host evidence
`evidence:dcb47181bdd4c05e67650d7fd2a66df00bb74ae6c74ec707c0bca0110fa396c7`
alongside the development entry above. New outbound candidate identities and
evidence go to the source-governance/D2 owner for registration in that single
development index; D2 is its sole writer. Later checks must read the index's
then-current entries as development candidate IDs may change. The historical
52-item snapshot needs no catch-up and is not an acceptance target. Development
contracts converge to `v1` before formal release; the indexed technical trace
does not waive scientific approval, distribution licenses, or release checks.
