# r43 corrected-wheel reviewer rebind handoff (2026-09-29)

This is a development handoff for a new technical reviewer run. It does not
authorize a release or change the existing 13-item review project's identity.

## Exact SciRel inputs

| Input | Identity | Local evidence |
| --- | --- | --- |
| Source | Git `cc2fa21e03fa7e5152c29f0769165863429e1693` | Corrected development index entry |
| Distribution | `scirel` `0.1.0.dev5`, wheel SHA-256 `b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684` | `build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/wheels/scirel-0.1.0.dev5-py3-none-any.whl` |
| Catalog | `release.json` SHA-256 `fece59b88ad39480a58b3c35f7678b2007a578f5918a74533f5b0cae6dfe2d02`; root `sha256:1bd47cc5cce3155cb8ec17676eb4f0296374d85939c7396c8be9a9ee06e7cdfb` | `build/verification/fluidbw-r43-development-delivery-20260929/bundle/catalog/release.json` |
| Catalog snapshot ZIP | SHA-256 `afee7fcf2d5bca4e04179aaaa1e1d98bdd689a8439c965f1b1c4580993c097e5`; 703,217 bytes; media type `application/vnd.scirel.catalog-snapshot+zip` | `build/verification/fluidbw-r43-cc2fa21-outbound-acceptance-20260929/catalog-snapshot.zip` |
| Development index | `development:c9a63b3f8068626417895ecfdc45787045a46a2a78ff6972642f6e8164de0463` | `provenance/release-index.dev.json` at `b0ef52a` |
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

## Current reviewer runtime

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
an installed-wheel runner path, but does not show that the current host runs
the wheel. The new runner must actually install the exact wheel and record its
import origins and dependencies.

## New host binding required

CodeFusion reports that its new isolated project
`prj_0b4158c393a55f538dae18802c15770ef756` uploaded the corrected wheel
as `cf://artifact/upload_3b6cf72adddd592f6edba784eaf7a0977ff69fd4bce4bdb3`
with media type `application/octet-stream`; its authenticated readback matched
the `b1abff...` SHA-256. No host-issued ArtifactOwner reference for this
catalog ZIP or a SciRel release manifest has yet been verified in the saved
handoff. The ordinary
request's `cf://user/.../resources/...` input is a ResourceOwner reference, not
an ArtifactOwner reference. Example refs in
`contracts/examples/scirel-plugin-registration.dev.json` are placeholders.
Do not place a digest alone or an invented `cf://artifact/...` value in the
new registration.

For a new isolated technical reviewer run, the host must register exact
ArtifactOwner refs with owner readback of bytes, digest, media type and scope;
assemble and check the reviewer runner from the exact `cc2fa21` body-wire
source and its dependencies (or execute those modules from the verified
`b1abff...` installed wheel); and issue a new immutable plugin registration
with a resolved runtime dependency binding. Record the runner's import origins,
distribution/source identity and dependency versions alongside the registration.
Then create a new reviewer project under that release and obtain new
authenticated item, action and host export receipts. The previous 13-item
project and its non-approving successor remain historical evidence.

The development technical run cannot substitute for expert decisions, license
clearance, an approved-subset build and release checks, or `v1` convergence.
