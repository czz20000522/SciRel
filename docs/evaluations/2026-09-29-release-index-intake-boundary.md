# Release-index intake boundary (2026-09-29)

`provenance/release-index.dev.json` records current unpublished SciRel development
snapshots and the r43 initial review candidate. This dated check records known D1
inputs that are not eligible for a releasable candidate entry. D1 references below
are relative to their named stage1 run. A frozen source hash alone does not close
source/numerical comparison, and `pending_unapproved` does not imply D1 qualification.
The unpublished-candidate census is not independently complete; new qualified
intake and exact development deliveries must be appended as they arrive.
The verified local scope is the r81/dev58 and r43/dev5 development deliveries
plus the r43 initial 13-item review version. The r43 workflow itself records an
unpublished-candidate census gap, so these entries are not an authoritative
inventory of every external checkout or host artifact.

The 2026-09-29 reviewer workbench readback showed 12 `review_pending` items and
one Weideman `needs_evidence` successor, SHA-256
`376899b3d2801fe7452f66086667852f08da98a21a4515d3d07e4fc88d9810ac`.
The index retains the initial workflow revision
`sha256:a9099aa88aee7256e1d1e841b28779b458c2f39d192d672a1d6a40e10c82cb6a`;
the workbench is the source for later item revisions and current decisions.

| D1 input | Exact evidence locator | Current boundary and destination |
| --- | --- | --- |
| fluidBW `stage1-fluidBW-20260920T025316Z` | r43 bundle SHA-256 `02b9b01d5224ecd2be0781aaae3540fdbe1526c05203f3748bdad6f9a6bd02fd`; `evidence_out/fluidbw-d1-extraction-freeze-20260920-r43/D1-HANDOFF-v2.json` SHA-256 `3c514298bd46be501a097e53766868285928c9e3cdb5f66c06a291289ec26f9a` | 16/16 source partitions and 4/4 target paths; issued for read-only D2 intake. The index binds its 13 retained review items separately from the mixed 132-item development wheel. |
| PDRK `stage1-PDRK-20260919T214903Z` | Frozen source SHA-256 `7ceab1c6383a474ec55095c7ff19316db5c1b739855e495a6b325f0f110b39e4`; candidate bundle SHA-256 `a35bd08ad1afb3912b996d8528317641ea9960b9875bbf0ccabfe8429c3c6310`; `coordination/capability_progress_reopened_20260921_r9/capability_progress.json` SHA-256 `9ddd03747c8d0b6c7f9b8ef99416447750cc6bd435036469fd48ca744b39bcef`; `coordination/pdrk-fixed-jpole-user-ruling-20260928.txt` SHA-256 `32d09ec338f1b75107a59abf1ff9e70458c33204914f389db4966a3a4f1e6120` | 12/13 paths closed; `T-PDRK-JPOLE-GENERATOR` lacks independent same-path sealed holdout. Remains OPEN in D1. PDRF proposal is also not uploaded; the isolated comparison in `docs/evaluations/2026-09-25-planar-wavevector-integration.md` is development evidence only. |
| Pleiades `stage1-Pleiades-opt-20260921T093633Z` | Frozen source SHA-256 `7c809a0d6d1fb18568e3b70e1a0fcbee7fff42469881b859df2028a373488c5a`; current comparison candidate SHA-256 `b09804ced2f8cd8c499638d6b68bc39444e72a0351e9be908f8c7519d317baa2`; `coordination/source-first-public-terminal-census-20260927.json` SHA-256 `3b3b8ae9166a03fc1b79c78e4eb2a4dcf4efa93b484d098b04a7fdaa50fb2252`; `lanes/wi-wham-source-api-domain-wham-control-20260929/attempts/a01/evidence/source-solver-entry-check.json` SHA-256 `773a196789082151d91526b5c81e2f925bc5f787d64bad9762720f273bbc294f` | Source-first census has 5 drivers and 292 terminal-field occurrences; 7 target paths remain open. One WHAM API-domain source check passed, while complete same-input terminal comparison remains unfinished. Historical 52-item SciRel sample stays historical. |
| FIDASIM `stage1-FIDASIM-20260917T053940Z` | Frozen source SHA-256 `c8bd91ecaeac96de7aa08a8eb7eeec435ee63b2a613d37254a607f1b8bc81f70`; current bundle SHA-256 `9677d76a88bf884eec33c66eecd2d03c0c86d63ea5f722acbee286116c02394a`; `coordination/capacity-checkpoint-20260928T012947Z.json` SHA-256 `b7472b11ae95ef8a6517c2504be48ea53a3d550391f08ca9eb482c1259d1b7d5` | Of 146 scoped items, 105 proved, 18 residual and 23 terminal; 0/10 target paths passed, and holdout independence remains unproved. D1 work continues. |

The latter three inputs remain visible here for comparison and follow-up. They do
not create `candidate` entries or imply a new census of the historical 52-item
snapshot. A bounded D1 batch may enter D2 before whole-project freeze once its
own source implementation and numerical comparison have passed.

## Review-slice dependency closure

The r43 index binds 13 retained review items, but this slice alone is not a
closed first-release set. `kinetic-dispersion-relation`,
`kinetic-wavevector-scan`, and `fluid-wavevector-scan` each depend on
`scirel.kinetic.species-equilibrium-scales`. D2 reused that existing relation
and absorbed its r43 lineage; it is not one of the 13 review items, and the
index has no prior trusted released baseline. The other 10 items have their
declared dependencies within the review slice. Even if all 13 current items
were later approved, the three compositions could not enter a first release
without an exact approved review of the reused dependency; a release may
instead exclude those compositions. Existing development code, documents,
catalog coverage, and D1 qualification do not supply that approval.

The declared document dependencies are not the whole runtime import closure.
`kinetic-dispersion-ronnmark` calls the separately indexed
`ronnmark-r-function`, and `kinetic-wavevector-roots` calls
`kinetic-dispersion-ronnmark`; both current exact documents list no version
dependencies. Those imported modules are among the 13 review items, but a
smaller approved subset selecting either caller alone cannot form an importable
wheel. The first-release source preparer rejects such a selection. Any change
to the submitted document dependency lists needs an exact reviewer successor;
the initial index entry and frozen review artifacts remain unchanged.

## Local draft outside the index

A read-only worktree check also found two untracked files on
`codex/d2-pointwise-margin` at Git `53271f0faa28aaac574481c9fe042f15b0be254a`:
`src/scirel/collisions/collrad_h0_ionization_rate.py` (SHA-256
`fb86d8f188f5cc2502b05c1867e5e8ed8d0ec9eb0d195764be5c5e655302fc21`) and
`tests/operator_contracts/test_collrad_h0_ionization_rate.py` (SHA-256
`5bda82bc9b20b4b3b7ddf91caf737937736d02e470438e3c2df3ed41da334013`).
The draft itself identifies the saved KN1DPy strict D1 qualification as
withdrawn and its source replay as historical development evidence. These files
are not part of that worktree's Git commit or the current SciRel index. Their
presence does not establish a qualified D1 handoff, a completed D2 asset, or a
review candidate; the owning worktree remains untouched.
