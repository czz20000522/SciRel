# r43 independent outbound selection (2026-09-30)

This is the current frozen **development** outbound selection, not a stable
release or an approval decision. D2's single unpublished-candidate index is
[`release-index.dev.json`](../../provenance/release-index.dev.json). At this
readback it has 21 entries, no `released` entry, and these current r43 entries:

- Reviewer candidate `candidate:af9f1e067df3a354a8059787315e199ccb73816ed709ecf2dc8722b8f9f06562`:
  13 exact items at SciRel Git `b986952474cc63971e0f518a18fa33c78ca9ac17`,
  `bounded_d1`, `pending_unapproved`. The initial review workflow is
  `sha256:e1169e806437fe8d3ad9acf3e0d3e4e726fcfd635fdb01cf5ca40ed8024e2c11`.
- Development delivery `development:c34b22afc988ce05c58808f2aa8955ecf2f3d721ccb2b19fbc4df0d30dd07722`:
  the same source revision, a 132-asset wheel/catalog, `mixed_unverified`,
  `pending_unapproved`. Only the 13 indexed items have the r43 bounded D1
  qualification; the other packaged assets do not inherit it.

The selected development tuple is exact at the SciRel artifact level:

| Part | Bound identity |
| --- | --- |
| Source | SciRel Git `b986952474cc63971e0f518a18fa33c78ca9ac17` |
| Wheel | `build/verification/r43-corrected-development-b986952-20260930/wheels/scirel-0.1.0.dev5-py3-none-any.whl`, SHA-256 `50f411c4d5a763b9a58aef25af5658d1d4a35984eca8f5934d936e6a214ed256` |
| Catalog release | `build/verification/r43-corrected-development-b986952-20260930/catalog/release.json`, SHA-256 `a0ff2790af0b7841de44f659e57a5ad73e866570092d6472efc0b85324666da5`, root `478509e591b36b3aadae3c71daabce83375691b47ffca7c7d545b2f3d21c0f39` |
| Catalog snapshot | `build/verification/r43-corrected-development-b986952-20260930/catalog-snapshot.zip`, SHA-256 `ec47a718a478c4033de7d528421255672757be41ddec77edde2777e1dd821cb5` |
| Python requirements | Wheel metadata: Python `>=3.10`, NumPy `>=1.24`, SciPy `>=1.10`; `pytest>=7` is a test extra. The saved consumer venv currently resolves Python 3.14.3, NumPy 2.5.1 and SciPy 1.18.0 through host site packages. These readback versions are not a locked, hash-identified dependency wheelhouse. |

The 13 indexed item documents and dependency lists match the maintained exact
documents by canonical JSON digest. Their transitive asset closure has 14
members: the 13 indexed items plus the reused
`scirel.kinetic.species-equilibrium-scales` document (canonical digest
`sha256:6091e23034ca8a066a04710811b2e08edbb5502e3a59d3ea5e8cb170a0d84834`).
That support asset has its own historical and r43 source lineage and remains
outside the 13 review items; its scientific and license disposition must be
bound separately before selecting any of the three graphs that depend on it.
The exact membership is in the
[`verification.json`](../../build/verification/r43-corrected-development-b986952-20260930/verification.json).
The other absorbed r43 input, `bessel-gamma`, is not a declared member of this
closure. A public release may select a smaller approved closed subset, but
this 132-asset development package cannot serve as that approved-only package.

The index already records the reviewer predecessor
`candidate:1d02ae5282f0947a40f5e15bb30df1ca9613fdd491d5012ab7b204f88d6c2218`
as superseded by `af9f` in `lifecycle:aa242bb9a68d257a174fe554a5f9e6dc37b031f143e324527b66fd4282e20ff2`.
It separately records development predecessor
`development:c9a63b3f8068626417895ecfdc45787045a46a2a78ff6972642f6e8164de0463`
as superseded by `c34b22` in
`lifecycle:293fd3658e7c6330ccda3ad8d50d8437be71ae3bc435cbd15e6f9e22198a6c62`.
These are two distinct replacement relationships; neither transfers an old
review decision or test receipt to the successor.

## Evidence boundary

- The saved r43 v2 L1 handoff digest is
  `3c514298bd46be501a097e53766868285928c9e3cdb5f66c06a291289ec26f9a`;
  candidate bundle digest is
  `02b9b01d5224ecd2be0781aaae3540fdbe1526c05203f3748bdad6f9a6bd02fd`.
  The [D2 comparison](2026-09-29-fluidbw-r43-d2-comparison.md) records
  the bounded D1 source scope and independent macro review digest
  `7b67725beb8622e70711aee00677a9d737a5aa5eccb0bbe83d09dc622ce79fa5`:
  54/54 named files and 14 comparison records checked. It reused earlier
  package evidence and did not rerun scientific execution. The original D1
  handoff file is unavailable in this checkout, so this readback relies on
  the saved D2 verification rather than a fresh D1 artifact hash check.
- The [independent D2 final review](../../build/verification/fluidbw-r43-independent-review-20260929/d2-final-acceptance-c69a9473.json),
  SHA-256 `fce91e5760c93a24423a643bfd50875f49036a5e240b81b47295e99d8509f110`,
  accepted a bounded development predecessor at `c69a9473`; it did not
  independently review the later `b986952` wheel. For the selected tuple,
  [D2 installed-wheel acceptance](../../provenance/r43-corrected-development-acceptance-20260930.json)
  binds 161 Python wheel members to the frozen source and reports 13 candidate
  examples, 132 runtime document checks and 51 scientific tests passed. Its
  source-free SciRel import used host site packages for NumPy/SciPy/Pytest.
- [Corrected reviewer intake](../../provenance/r43-corrected-review-intake-acceptance-20260930.json)
  binds the 13 new item identities and corrected dependency lists. The later
  [same-tuple CodeFusion host record](../../provenance/r43-corrected-development-host-acceptance-20260930.json)
  binds source, wheel, catalog, backend and immutable registration on CodeFusion
  `936e339f9a3fb835466482400fa9702fcc27650c`. After a separately recorded
  initial L1 credential failure, the reviewer run completed with 13 items,
  zero transitions and zero approvals. The
  [ordinary-user manifest](outbound-progressive-projects/manifests/2026-09-30-r43-corrected-ordinary-same-request.json)
  records a completed same-request discovery/read/two-invocation chain and two
  finite SciPy comparisons. This is development technical acceptance, not an
  approved-only reviewer and consumer release chain.

## Remaining decisions

An authorized reviewer must refresh each selected current item and give an
exact-revision scientific disposition and scope. The new 13-item cohort has no
approval; the older cohort's Weideman `needs_evidence` successor does not
approve the corrected item. The [expert handoff](2026-09-30-r43-expert-license-handoff.md) identifies unreported producer
build identifiers and any item-specific evidence still needed. A license owner
must decide rights for every selected code/document and runtime dependency,
including `species-equilibrium-scales` if selected; current documents say
`pending-human-decision`.

Before public release, D2 needs a host-authenticated selected-subset decision
chain with a current-revision recheck, an approved-only source/document/wheel/
catalog build and isolated scientific verification, fixed dependency artifacts
and rights, one matching CodeFusion registration and consumer readback, and
explicit release authorization. The `.dev` contracts converge to `v1` at that
point. D2 alone appends any resulting evidence, lifecycle or released entry to
the unified index. This selection neither opens a new candidate pool nor
revisits the historical 52-item snapshot.
