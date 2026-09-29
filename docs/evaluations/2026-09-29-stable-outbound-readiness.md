# Stable outbound readiness (2026-09-29)

This is a read-only development acceptance check, not a scientific approval or
public release. SciRel Git `ac299ceeafbc25545760974943620c5c972d643b`
has one r43 `candidate` and two `development` entries in
`provenance/release-index.dev.json`; it has no `released` entry. The index
covers the verified local scope, not an authoritative census of all unpublished
candidates. The old 52-item snapshot is historical.

## Authenticated review readback

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
now contains a reviewer `snapshot-exports` route and its follow-up fixes. That
code integration has not been deployed. The commit itself supplies neither an
authenticated r43 aggregate export nor an approval; the live workbench and
exact current item Artifacts remain the authority for release decisions.

## Release boundary

The first-release subset assembler, exact-item finalizer, and source-free
installed-wheel gate have development fixture coverage. These tests establish
the technical checks, not approval of the r43 items. The development wheel and
catalog consumed by D3 are `pending_unapproved` and include mixed-source
material outside the 13-item r43 review slice. They cannot be registered as a
trusted CodeFusion runtime release. The example plugin registration contains
placeholder Artifact refs; no real SciRel reviewed release manifest, approved
wheel/catalog tuple, or `released` index entry exists.

Before a stable outbound release, the following inputs are still required:

- Human expert decisions on exact item revisions and their scientific scope;
  the current 13-item batch has no approved item.
- Human distribution-license decisions for the selected code, documents, and
  dependencies, followed by explicit release authorization.
- Resolution or exclusion of candidate gaps, including the unpublished-candidate
  census and unreported exact producer build identifiers; a development pass
  does not close these evidence gaps.
- An authenticated, auditable host export of any approved subset with exact
  current and predecessor Artifact bytes, then a clean selected-source build,
  complete exact documents, catalog, wheel, isolated checks, and manifest/index
  binding for that same subset.
- A real CodeFusion registration and consumer readback of one pinned plugin
  release, wheel, catalog, runtime dependencies, and SciRel release manifest.
  The SciRel-owned `.dev` review and release contracts must converge to `v1`
  before formal public release.

Incremental release also needs a real prior trusted baseline whose wheel,
catalog, documents, support modules, and tests can be verified and inherited.
The current index has no such baseline. The release check's development
environment exposes host NumPy/SciPy/Pytest through a `.pth` file; its
source-free result does not establish a fully pinned offline dependency
wheelhouse for formal distribution.
