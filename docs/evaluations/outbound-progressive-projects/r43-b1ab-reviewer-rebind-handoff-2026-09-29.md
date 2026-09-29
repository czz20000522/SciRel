# r43 corrected-wheel reviewer rebind handoff (2026-09-29)

This is a development handoff for a new technical reviewer run. It does not
authorize a release or change the existing 13-item review project's identity.
`provenance/release-index.dev.json` is the D2-maintained single current index
for unpublished development candidates; D2 is its sole writer. Later outbound
and reviewer checks must use the index's current exact identity and state,
not this dated handoff as a status pointer. The old 52-item snapshot is
historical and is not a prerequisite for this acceptance. Development `.dev`
contracts converge to `v1` before formal release.

## Exact SciRel inputs

| Input | Identity | Local evidence |
| --- | --- | --- |
| Source | Git `cc2fa21e03fa7e5152c29f0769165863429e1693` | Corrected development index entry |
| Distribution | `scirel` `0.1.0.dev5`, wheel SHA-256 `b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684` | `build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/wheels/scirel-0.1.0.dev5-py3-none-any.whl` |
| Catalog | `release.json` SHA-256 `fece59b88ad39480a58b3c35f7678b2007a578f5918a74533f5b0cae6dfe2d02`; root `sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb` | `build/verification/fluidbw-r43-development-delivery-20260929/bundle/catalog/release.json` |
| Catalog snapshot ZIP | SHA-256 `afee7fcf2d5bca4e04179aaaa1e1d98bdd689a8439c965f1b1c4580993c097e5`; 703,217 bytes; media type `application/vnd.scirel.catalog-snapshot+zip` | `build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/catalog-snapshot.zip` |
| Development index | `development:c9a63b3f8068626417895ecfdc45787045a46a2a78ff6972642f6e8164de0463` | `provenance/release-index.dev.json`; retained at `21cb40f` |
| Current reviewer candidate | `candidate:1d02ae5282f0947a40f5e15bb30df1ca9613fdd491d5012ab7b204f88d6c2218`, workflow `sha256:0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b` | `provenance/release-index.dev.json` at `21cb40f` |
| Ordinary-user evidence | `evidence:f61f5487b357c2009707d3fd852e5507b882de3fa070b7c7952ddbd6763ed895`; manifest SHA-256 `4e85873f9a8280a139158937f9bc9531c5f1b6ea67be2ed5762a16abf2aeea1f` | `manifests/2026-09-29-fluidbw-r43-b1ab-current-ordinary.json` |

The wheel and catalog release file were rehashed locally for this handoff.
Their source qualification is `mixed_unverified` and approval state is
`pending_unapproved`. The 132-document development catalog includes material
outside the 13 retained r43 review items.

`scripts/package_catalog_snapshot.py` packages the fixed catalog directory
above without rebuilding its scientific contents:

```powershell
python scripts/package_catalog_snapshot.py build/verification/fluidbw-r43-development-delivery-20260929/bundle/catalog --output build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/catalog-snapshot.zip
```

The ZIP contains exactly `release.json` and its 135 declared partitions, with
no extra members. Independent ZIP readback checked every partition's byte
count and SHA-256 against `release.json`, the release root calculation, the
exact member set, and ZIP integrity. The ZIP SHA-256 identifies the compressed
upload bytes; `release.json` SHA-256 identifies that file's bytes; the catalog
root is computed from canonical release content without its `root_digest` field
and binds the partition hashes. These three digests serve different purposes.

## Reviewer runtimes

CodeFusion's read-only check of its isolated service on port 18110 found that
`plugin-runner-backend` mounts an older SciRel body-wire source fixture and has
no installed `scirel` distribution. Its fixture manifest and remote bytes agree,
but two source files differ from the named SciRel source:

| File | Current SciRel `cc2fa21` SHA-256 | Existing runner fixture SHA-256 |
| --- | --- | --- |
| `src/scirel_plugin/plugin.py` | `7056f55da07174358287a67109a79b3db01bfdf47508df0d507c31e0633f51fb` | `9cc56e75a1bfd6770aa4b5ba6cd9c4a3e99558e8e6c9e5c19c6d1c284d95376c` |
| `src/scirel_workflow/workflow.py` | `d06b1e8a8131272da29e5925bcfcdbc073ee9ad77359a7dd1f32aaa358876f25` | `ad4a9f443de861b1248f0942c85fa57fb87adc6654ac4d62d1ddc9fcc5e4d01d` |

SciRel checked the two current local file hashes and the saved fixture manifest;
CodeFusion owns the remote mount, installed-package and remote-byte checks.
The existing registration contains only its old `plugin_release_ref`, with no
wheel, catalog or runtime dependency refs. The old review host snapshots are
valid for their own release identity, but cannot be reassigned to this wheel.

The corrected wheel contains seven `scirel_plugin` and five
`scirel_workflow` Python modules. A local comparison of its `plugin.py`,
`body_runner.py` and `workflow.py` with the current SciRel source found equal
text after CRLF/LF normalization. `workflow.py` also matches byte for byte;
the other two have different raw bytes because of line endings. This supports
the installed-wheel runner path used by the new isolated project below; it
does not rebind the old runner.

CodeFusion has since prepared a separate `m3-r43-b1ab-reviewer-backend` on
Spark. Its owner reports an offline installation of the exact `b1abff...`
wheel, NumPy 2.4.6 and SciPy 1.18.1, with SciRel import origins under
`/opt/install`; an HTTP body-wire `scirel.import_l1` smoke call passed. The old
backend and service remain running. SciRel has not independently queried this
remote container, and this runner check alone is not a reviewer host receipt.

## New host binding

CodeFusion reports that its new isolated project
`prj_0b4158c393a55f538dae18802c15770ef756` uploaded two ArtifactOwner
inputs and read them back under reviewer authentication:

| Input | ArtifactOwner ref | Media type | Readback SHA-256 |
| --- | --- | --- | --- |
| Corrected wheel | `cf://artifact/upload_3b6cf72adddd592f6edba784eaf7a0977ff69fd4bce4bdb3` | `application/octet-stream` | `b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684` |
| Catalog snapshot ZIP | `cf://artifact/upload_4b8246a7369ee9581e0e241830f0ea69c3a16cf934cdcc56` | `application/vnd.scirel.catalog-snapshot+zip` | `afee7fcf2d5bca4e04179aaaa1e1d98bdd689a8439c965f1b1c4580993c097e5` |

CodeFusion also independently checked the ZIP's 136 members, 135 partitions,
`release.json` SHA-256 and catalog root. SciRel's local ZIP checks are recorded
above; SciRel did not independently query ArtifactOwner. No SciRel release
manifest ArtifactOwner ref has yet been verified. The ordinary request's
`cf://user/.../resources/...` input is a ResourceOwner reference, not an
ArtifactOwner reference. Example refs in
`contracts/examples/scirel-plugin-registration.dev.json` are placeholders.
The new isolated product on Spark loopback port 18112 used the installed-wheel
backend and registered a development plugin release naming SciRel source
`cc2fa21`, wheel, and catalog. The wheel and catalog ArtifactOwner readbacks
are above. The release ref is:

```text
plugin-release://scirel/0.1.0.dev5/source-cc2fa21e03fa7e5152c29f0769165863429e1693/wheel-b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684/catalog-afee7fcf2d5bca4e04179aaaa1e1d98bdd689a8439c965f1b1c4580993c097e5
```

CodeFusion's 2026-09-30 read-only inspection of the isolated container and its
`product_plugin_releases` row confirmed the same release ref and two
`release.artifacts` entries: the wheel and catalog ArtifactOwner refs, digests,
and media types in the table above. `runtime_dependency_refs` is empty and
omitted from the serialized release JSON. The container registration's
canonical JSON has SHA-256
`40a83e4f18e0a4e621912ea61d2d2b8d96831d3701a8b8a4d44011774efbdcf2`;
the exact owner receipt is CodeFusion
`.runtime/m3-b1ab-registration-evidence.md`. SciRel did not independently
query the container or database. This confirms neutral wheel/catalog binding
for this development host, not expert approval, formal same-tuple release
acceptance, or stable release; the earlier reviewer registration remains a
separate historical instance.

At SciRel `ce758b3`, D2 appended registration evidence
`evidence:5f1c6c5b348a4ead3bbe72a450895f2f5ba389403798f83bf38adf4ad5f48f03`
for the current reviewer candidate in `provenance/release-index.dev.json`. Its
exact record is `provenance/r43-b1ab-review-registration-acceptance-20260930.json`.
D2 checked the saved owner report hash against the indexed candidate/workflow,
development wheel/catalog root, and earlier Artifact readbacks. D2's direct
container inspection was denied, so it did not recompute the registration
digest or query the database; those readbacks remain owner-verified.

For a later qualified candidate, the ordinary/reviewer handoff must identify
the same exact source Git, wheel, catalog release/root/ZIP, and review
workflow/successor. It must give the immutable plugin registration snapshot
locator and digest, enumerate the actual `PluginReleaseSnapshot.artifacts`
triples (`artifact_ref`, digest, media type) and `runtime_dependency_refs`, and
attach host installation and readback receipts. The frozen source Git SHA
belongs in the D2 index; this development run pins the workflow, review
successor, and host export separately as review evidence. A qualified release
needs its own immutable registration and approved dependency closure; the
development registration and reviewer decisions are not upgraded in place.

The first L1 run failed after a task-local proxy error; the retry under the
same release completed. CodeFusion reports these new project results and
authenticated Artifact readbacks:

| Step | Exact identity and result |
| --- | --- |
| L1 intake | `run_d9bc496e3714747d851e2f89c77a317351e5f5b97d59135c985598a9f9e80772d`; result Artifact `cf://artifact/upload_2a29b63525516715a362a175e804d67c805ae5cd54a98395`, SHA-256 `c1f632d433441be6bc84410ea28c558f64b11710be59cfcbd2b56585faf8e1a4`; 15 assets and five structural checks passed. |
| New review source | Uploaded workflow Artifact `cf://artifact/upload_8fe2f34e384bfea5f56bb605561c6e8af7677279544bd7bd`, SHA-256 `0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`; review-index run `run_e42f2d8a57ff503b4bbb3a924858833fa6346e405ecdb58c359ee92a5bf06020` admitted 13 items. |
| Weideman action | `request-evidence` run `run_96c8da8766b8eb0a7e78fbdb8649bffc9aa08c41ce7e23dc974b41c76a8bd9f2`; successor Artifact `cf://artifact/upload_615e3e16eff14ab1f750ef4628098ab7fd75202a5d1c0e67`, SHA-256 `d62ae8faf3b529605bb3795acbde9589d274a0bbca54cceb1dd5b7abddbcd461`. |
| Host export | Artifact `cf://artifact/upload_023f4dc2766a932f0ad6f4cf26347e9b8b751726272f8e03`, SHA-256 `b9e2c8c990f821232f2a912163a8ae03a970faa52c49ced1a701d22e1de9eabd`; 13 items, one applied transition, one `needs_evidence`, 12 `review_pending`, zero approved. |

The new review preparation bound development-index file SHA-256
`8768b807cd850538d13dbbc034d201cf48c8010bb9e8af5477a51c1de3aa9b88`.
Its submission ID is `fluidbw-r43-b1ab-review-prep-20260929` and its
candidate-pool digest is
`sha256:04748521cb88ab4acb495f5417973a3e60df6a4c1bb85f00cbdbd45bb6453036`.
The old review project's workflow revision
`sha256:a9099aa88aee7256e1d1e841b28779b458c2f39d192d672a1d6a40e10c82cb6a`
is a different frozen version. The new preparation retains the logical
candidate/draft IDs but incorporates the new L1 result, host Artifacts and
index snapshot; it neither modifies the old workflow bytes nor inherits an
old review conclusion. At `21cb40f`, D2 registered the new candidate and host
evidence
`evidence:dcb47181bdd4c05e67650d7fd2a66df00bb74ae6c74ec707c0bca0110fa396c7`;
an append-only `superseded` event points the old
`candidate:a90a56d6c69390d65c38b7ac8de7597ea5d6f5ef7cc7776377668daa8a7d3c14`
to the current candidate. The old review receipts remain bound to their own
workflow revision.

The development technical run cannot substitute for expert decisions, license
clearance, an approved-subset build and release checks, or `v1` convergence.
