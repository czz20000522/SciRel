# Stable outbound readiness (2026-09-29)

This is a read-only development acceptance record, not a scientific approval or
public release. The earlier check at SciRel Git
`ac299ceeafbc25545760974943620c5c972d643b` saw one r43 `candidate` and two
`development` entries. The D2-maintained `provenance/release-index.dev.json` is
now the single current unpublished-candidate index. At `21cb40f`, its current
r43 reviewer candidate is `candidate:1d02ae5282f0947a40f5e15bb30df1ca9613fdd491d5012ab7b204f88d6c2218`;
it has no `released` entry. The old 52-item snapshot is historical and is not
an acceptance prerequisite.

For normal SciRel integration handoff, the frozen D2 development candidate is
SciRel `274f2e6378d1f349be2a81449ed4021cd2a0679e` on
`codex/initial-library`. Its unified index has 14 entries and no `released`
entry; the current r43 candidate and both new review-selection and
ordinary-user recovery evidence entries remain `pending_unapproved`, with
zero approved review items. D2 reports `scripts/check.ps1 -Mode affected` at
1840 passed, 83 skipped, and three expected numerical warnings. This is a
technical handoff baseline, not a scientific approval, license decision, or
same-tuple dual-chain acceptance. The development index can evolve during
integration; its formal contracts converge to `v1` before public release.

## Earlier authenticated review readback

CodeFusion Git `e532153990bec33103721138b742df4ecdb94b21` exposes the
development reviewer workbench for project
`prj_76550806f8a8827a1ca8d2aaec2d4c6e7be3`. A reviewer-authenticated,
read-only call to its `items` endpoint returned all 13 r43 items on one page:
12 `review_pending`, one `needs_evidence`, zero `approved`. For every item, an
authenticated `open` call matched the listed item ref and revision, identified
its current Artifact, and returned the same status. The two distinct current
Artifacts were downloaded from the project Artifact API; both raw SHA-256
digests matched their listed revisions. A second `items` call returned the same
13 item-ref/revision pairs. The temporary local SSH forward was closed.
The `open` response's `snapshot.digest` identifies a detail projection;
`snapshot.body.current_artifact.digest` identifies the review Artifact and
must match the item revision.

The Weideman successor is
`sha256:376899b3d2801fe7452f66086667852f08da98a21a4515d3d07e4fc88d9810ac`.
Its host-stored decision is `needs_evidence` and binds reviewer actor
`usr_71df06d0f947e60ed3fcaba6f0e05b20cef8631d3888fbfd` to the
submitted workflow revision
`sha256:a9099aa88aee7256e1d1e841b28779b458c2f39d192d672a1d6a40e10c82cb6a`.
SciRel's `scirel.review.list_completed` on those exact saved Artifact bytes
returned 0 completed/0 approved for the initial workflow and 1 completed/0
approved for the successor. The live workbench state and the saved Artifact
bytes agree; neither is an approval.

The authenticated readback found per-item `items`, `open`, and Artifact download
endpoints. The deployed product routes did not provide a
host-issued, candidate-wide `scirel.review-completed-results.dev` export.
SciRel's `list_completed` body operation projects one current Artifact at a
time, while `prepare_reviewed_distribution.py` and `finalize_release.py`
consume one aggregate `approved_results` plus exact original and successor
Artifact bytes. A locally assembled JSON array would not establish that all
current revisions, reviewer identities, and decisions came from an authorized
host export. A real approved batch still needs a host-owned export or an
equivalent authenticated, auditable collection protocol that binds every item
ref, current Artifact ref/digest, decision actor, and source review revision.

CodeFusion local `master` at `2d3de66e04d81fcbb94fd069bb7f4d93630cd844`
contained a reviewer `snapshot-exports` route and its follow-up fixes. It had
not been deployed to this older workbench at the time of that readback. A later
isolated product using that source completed a separate r43 development
reviewer run, described below; neither deployment nor export is an approval.

The new route's `codefusion.plugin-review-snapshot-export.v1` is a neutral
host snapshot of item refs, current/source Artifact refs, and applied review
transitions. It is not the `scirel.review-completed-results.dev` projection
accepted by the SciRel distribution scripts. For a selected approved subset,
D2 must verify the exact host Artifact and referenced initial, predecessor,
and current review Artifact bytes, then bind the derived domain projection to
that host snapshot. A route receipt alone cannot satisfy release inputs.

The earlier 2026-09-29 Spark runtime check found CodeFusion `e5321539` on port
18096 and all 13 r43 items on one reviewer index page with no next page. Local
`2d3de66e` changes the product V1 schema, including a review-transition table
and Artifact source constraints, so the existing database with its old V1
checksum could not be used by simply restarting the new service. Deploying to
that old workbench would have required an explicit preservation/reload decision
for its pending r43 review project and other needed inputs, followed by a
new-database acceptance check against the actual source label. No review
action, service replacement, or database rebuild was performed by that check.

## Current development successor

SciRel `21cb40f` indexes a distinct r43 workflow version
`sha256:0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`.
CodeFusion `2d3de66e` ran it in a separate isolated product and reviewer
project, with a registered development release binding SciRel source `cc2fa21`,
wheel SHA-256 `b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`
and catalog ZIP SHA-256 `afee7fcf2d5bca4e04179aaaa1e1d98bdd689a8439c965f1b1c4580993c097e5`.
The installed-wheel backend completed L1 intake and review-index runs. One
Weideman `request-evidence` action produced a new successor. The authenticated
host export contains 13 items: one `needs_evidence`, 12 `review_pending`, zero
approved. D2 bound the new workflow and export in
`provenance/r43-b1ab-review-workflow-acceptance-20260929.json` and
`provenance/r43-b1ab-review-host-acceptance-20260929.json`; the old reviewer
candidate is retained through an append-only `superseded` event. This closes
the bounded development reviewer technical trace alongside the corrected-wheel
ordinary-user trace, without transferring old review decisions.

## Release boundary

The first-release subset assembler, exact-item finalizer, and source-free
installed-wheel gate have development fixture coverage. These tests establish
technical checks, not approval of the r43 items. The corrected development
wheel and catalog are `pending_unapproved` and include mixed-source material
outside the 13-item r43 review slice. The new CodeFusion registration uses real
Artifact refs for this development tuple, but it is not a trusted runtime
release. No SciRel reviewed release manifest, approved-only wheel/catalog
tuple, or `released` index entry exists.

CodeFusion master `3c69931b594beec24c319618365ad0bbe2d7cb1f` now contains
reviewer selection exports that bind a release attempt, candidate Artifact,
expected plugin release, and selected item/current Artifact pairs. A new
idempotency key and previous snapshot Artifact support conditional revalidation;
changed item revisions or registration conflict, and the receipt identifies
the new Artifact digest, capture time, and nonce. CodeFusion reports an
independent review and passing Spark ARM64 merge gate. This code has not been
deployed to the earlier acceptance service. A separate V1 development instance
at CodeFusion `3c69931b` has since admitted 13 r43 items in project
`prj_745a23d72d1945738fc15388bdc44232df7d` (run
`run_1bdca62591fbdbc4f4fb5d386a4301f6b6ce0b4da54e759f69fb377f2815907b`)
and applied one `request-evidence` action; it still has zero approved items.
Its workflow revision `sha256:a9099aa88aee7256e1d1e841b28779b458c2f39d192d672a1d6a40e10c82cb6a`
and plugin release
`plugin-release://scirel/0.1.0.dev5/source-manifest-sha256-6185c8f1c973832e12040be19323faaef09668ab94347af7cb348b19d62a14f7`
differ from the current indexed corrected-wheel reviewer version
`sha256:0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`.

That V1 instance returned a selected snapshot SHA-256
`8454ffa614cf0dc40d1aa1511a54be2fe34673f9298c5fedff3f62fe336a349e`
and a previous-snapshot revalidation SHA-256
`af12a9ee1346934cba2f82f900b7869940d2b948a7202db54c614fb5213206f5`;
CodeFusion reports that the downloaded digests matched and a stale current
Artifact returned 409 (CodeFusion
`.runtime/reviewer-selection-r43-export-3c69931b5.json`).
These are development host-protocol receipts for a different review/release
identity, not selection or revalidation of the current D2 candidate. The
earlier `b9e2c8...` export also remains development review evidence. Neither
set is a SciRel approval or `released` entry.

The same CodeFusion source `3c69931b` subsequently ran the current r43
workflow in a new V1 development project
`prj_06b93ac5f20676cf034d2e8c171eb73e628a`. Its source workflow Artifact
has digest `sha256:0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`,
and all 13 item refs match the current indexed candidate. One Weideman
`request-evidence` action left one item `needs_evidence`, 12 `review_pending`,
and zero approved. The selected snapshot Artifact
`cf://artifact/upload_1885f11491ebaa41c4149c4c6f4621b560b4df963dbd8fde`
has SHA-256 `05ee82f0f9fae1a635879ed0a10272b5043dcb2b6ceb69cd72ad9b44dbabce85`.
It binds release attempt `dev-current-r43-3c69931b5`, that source Artifact,
and the Weideman successor as the selected current Artifact. A second export
using the selected snapshot as `previous_snapshot` returned Artifact
`cf://artifact/upload_8626eb5a90acbcc0cdc2688423e437e3ddf0faa28616cb2c`
with SHA-256 `5046888289573d540d65f28622aa872d57d1e344c3b1b3b86a2ef81c106c3a7d`
and a new selection nonce. A stale current Artifact request returned 409.
Downloaded snapshot bytes match both receipt digests (CodeFusion
`.runtime/reviewer-current-r43-3c69931b5.json` and its saved Artifact bodies).

This verifies selection and conditional revalidation for the current workflow
identity in that development project. Its `plugin_release_ref` is
`plugin-release://scirel/0.1.0.dev5/source-manifest-sha256-6185c8f1c973832e12040be19323faaef09668ab94347af7cb348b19d62a14f7`,
which differs from the corrected-wheel `b1abff...` development registration
in `prj_0b4158c393a55f538dae18802c15770ef756`. The matching workflow and
items do not establish a same-tuple wheel/catalog release. D2 has since added
the selection acceptance as an evidence-only index entry, referencing
`provenance/r43-current-review-selection-acceptance-20260930.json`; it remains
`pending_unapproved` and confers no scientific approval, license clearance,
or stable release.

CodeFusion `3c69931b` also ran a separate ordinary-user technical trace in
new V1 development project `prj_294431b895bf39bf55bd8112b8c7f02897cf`.
The qualified r43 L1 transfer ZIP has SHA-256
`166021e28d6aa6db71b61daff7e3671837f3dede218b41153b4c0d3186cb83bd`;
the input supplied the corrected SciRel wheel SHA-256
`b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`
and catalog root
`sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb`.
Three requests in one product session preserved an incomplete-catalog failure,
then successful adapter calls with a result-checker misread, and finally a
corrected check. The final request
`appreq_047e088a383a9767_6c5e6c75c889e84c` completed. Its downloaded
`results-final.json` has SHA-256
`a5864a95f06091f9c90b22fea7ece9f1ca48e564522b246dddecc3e728346100`;
it records Weideman discovery, document readback, and two invocations at
`z=0` and `z=0.5+0.25j`, with absolute errors against SciPy `wofz` of zero
and `2.48253415324727e-16` (CodeFusion
`.runtime/ordinary-current-r43-3c69931b5.json` and
`.runtime/ordinary-current-r43-readback-3c69931b5/`). This is a development
ordinary-user result. D2 rehashed the ZIP members and saved failure/final
results, and recomputed the two SciPy comparisons; it did not independently
query the product timeline for the owner-reported completed status. At this
readback, the D2-maintained unified development index has 14 entries, none
`released`. It adds evidence
`evidence:ab4529a8c518cce484e4f30cf575120f7d60f945a775d33b3157a2205e188b40`
for this recovery trace under the existing corrected-wheel/catalog
`development:c9a63b3f8068626417895ecfdc45787045a46a2a78ff6972642f6e8164de0463`
entry. The record at
`provenance/r43-current-ordinary-recovery-acceptance-20260930.json` retains
its `mixed_unverified` source qualification and `pending_unapproved` approval
state; it creates no separate candidate. On the shared `3c69931b` development
service, the reviewer installation declares a source-manifest plugin release
with `release.artifacts=[]`; its runner backend uses a source fixture without a
binding to the corrected wheel digest (CodeFusion
`.runtime/reviewer-installation-prepare.overrides.json` and
`.runtime/spark-plugin-runner-5420/scirel-backend-fixture/`). Uploading
wheel/catalog Artifacts later would not by itself establish which package
the backend executed. The earlier isolated `2d3de66e` instance declared and
read back corrected wheel/catalog Artifacts, but it is a different CodeFusion
source, project, and registration from the current `3c69931b` selection.
The ordinary-user and reviewer traces therefore retain separate technical
scope; the review batch has zero approved items and no stable release follows.
When a stable SciRel outbound candidate is ready, an isolated instance must
verify the exact SciRel and CodeFusion sources, wheel, catalog, executing
backend, immutable registration, reviewer snapshot, and ordinary-user result
as one pinned tuple.

The exact per-item scientific and license decision inputs, captured Artifact
refs, and selectable dependency closures are mapped in
[r43 expert and license handoff](2026-09-30-r43-expert-license-handoff.md).

Before a stable outbound release, the following inputs are still required:

- Human expert decisions on exact item revisions and their scientific scope;
  the current 13-item batch has no approved item.
- Human distribution-license decisions for the selected code, documents, and
  dependencies, followed by explicit release authorization.
- Resolution or exclusion of gaps in the selected current candidate, including
  unreported exact producer build identifiers where required. The historical
  52-item snapshot is not a census gate for new development acceptance.
- For any approved subset, an authenticated, auditable host export with exact
  current and predecessor Artifact bytes, an auditable action identity, explicit
  candidate/subset binding, and a conditional current-revision recheck before
  finalization so later successors cannot silently replace the selected items.
  Then a clean selected-source build, complete exact documents, catalog, wheel,
  isolated checks, and manifest/index binding for that same subset.
- A CodeFusion registration and consumer readback of the approved-only pinned
  release tuple, including wheel, catalog, runtime dependencies, and SciRel
  release manifest. The current development registration does not supply that
  release. SciRel-owned `.dev` review and release contracts must converge to
  `v1` before formal public release.

Incremental release also needs a real prior trusted baseline whose wheel,
catalog, documents, support modules, and tests can be verified and inherited.
The current index has no such baseline. The release check's development
environment exposes host NumPy/SciPy/Pytest through a `.pth` file; its
source-free result does not establish a fully pinned offline dependency
wheelhouse for formal distribution.
