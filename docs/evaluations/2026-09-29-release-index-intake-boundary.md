# Release-index intake boundary (2026-09-29)

## Current coverage update (2026-09-30)

The index now carries a machine-readable `coverage` field. Its
`current_unpublished_entry_ids` names the three registered, still-current exact
entries: the r81 development snapshot `development:84d0882d...`, the r43
13-item reviewer candidate `candidate:af9f1e06...`, and the r43 development
snapshot `development:c34b22af...`. This is a census of registered entries,
not of all potential intake. External source checkouts, host artifacts outside
the index, and D1 inputs not handed to D2 have not been independently inventoried.
The 132-item development catalog does not close those gaps, and technical
acceptance does not confer scientific approval, license clearance, or release.
The entry identities and "current" descriptions below document earlier
checkpoints; use the index and its lifecycle entries for the present state.

`provenance/release-index.dev.json` records current unpublished SciRel development
snapshots and r43 review versions. D2 maintains it as the single
authoritative index for registered unpublished candidates. This dated check
records known D1 inputs that are not eligible for a releasable candidate entry.
D1 references below are relative to their named stage1 run. A frozen source
hash alone does not close
source/numerical comparison, and `pending_unapproved` does not imply D1 qualification.
The unpublished-candidate census is not independently complete; new qualified
intake and exact development deliveries must be appended as they arrive.
The later `cc2fa21` adapter wheel is a distinct r43 development successor:
its SHA-256 is `b1abff574c870e17dd4e24adc952ca4279561aa43adcc92250d019e42b2b3684`,
whereas the earlier indexed wheel is `927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda`.
The appended successor entry binds the exact wheel, Git source, local catalog,
and preserved ordinary-user install/result receipts through
`provenance/r43-adapter-corrected-development-acceptance-20260929.json`.
Its third destination reference is the independently saved
`docs/evaluations/outbound-progressive-projects/manifests/2026-09-29-fluidbw-r43-cc2fa21-outbound-check.json`:
the installed wheel passed 51 r43 scientific tests and a bounded local adapter
discover/read/invoke probe outside the source checkout.
The two entries share a catalog root but do not share wheel identity or transfer
the earlier D3 case results. The consumer request identity comes from the
CodeFusion owner's readback; D2 checked its downloaded receipt bytes locally,
without an independent product query or remote catalog byte download.
The append-only `superseded` lifecycle event now marks the earlier
`development:470d2b5b...` entry historical and the corrected
`development:c9a63b3f...` entry current, using that exact acceptance record.
The r43 13-item reviewer candidate remains a separate pending identity; this
development replacement does not transfer review state or approvals.
At that acceptance point, the ordinary-user dual-chain trace still lacked one
same-request binding to an owner-resolved immutable `scirel-solving` revision,
a frozen execution environment, and the shell Tool Plan. This development
snapshot does not close
that consumer-contract gap.

The later current-source ordinary-user request
`appreq_f9ab1cd4d20826bb_a76d533b66556885` closes that bounded trace gap.
Its exact development manifest at
`docs/evaluations/outbound-progressive-projects/manifests/2026-09-29-fluidbw-r43-b1ab-current-ordinary.json`
has SHA-256 `4e85873f9a8280a139158937f9bc9531c5f1b6ea67be2ed5762a16abf2aeea1f`.
The new append-only index evidence entry binds it to the existing `b1abff...`
development wheel. The owner verified the same request's frozen skill revision,
environment, shell Tool Plan and read-only wheel input; D2 checked saved local
script/result bytes and the two numerical outputs, without independently
querying the product. At that point the reviewer registration contained only the old
plugin release ref, with no wheel/catalog/runtime dependency binding. Its
runner uses a source-backed fixture with no installed SciRel wheel, according
to CodeFusion's read-only host check. That check also found the runner's
`scirel_plugin/plugin.py` and `scirel_workflow/workflow.py` bytes differ from
SciRel source `cc2fa21`; D2 did not independently read the container fixture.
Its 13-item workflow and non-approving successor remain separate evidence;
zero items are approved. That ordinary-user result alone was neither
same-tuple dual-chain acceptance nor stable release.

The later isolated reviewer project used a new development release ref naming
SciRel Git `cc2fa21`, wheel `b1abff...` and catalog ZIP `afee7fcf...`.
CodeFusion read back both uploaded Artifacts and reported an installed-wheel
backend; D2 checked the saved local readback bytes and receipts, without an
independent product or database query. At that point the saved D2 evidence did
not include a neutral registration readback, so matching material digests
supported a bounded technical comparison across the two projects. Its new
`review_pending` workflow SHA-256
`0d252fbef7a0d55f70d4943c369440c7e3e0bc8e523f25b1248e4d26b052c03b`
retains the same 13 review units and item refs as the old `a9099a...` version,
but binds the corrected L1 result, wheel/catalog Artifacts and exact index
snapshot `8768b807...`. The index now registers this as current candidate
`candidate:1d02ae5282f0947a40f5e15bb30df1ca9613fdd491d5012ab7b204f88d6c2218`
and marks the old candidate superseded without changing its entries or host
receipts. The new host export SHA-256 `b9e2c8c990f821232f2a912163a8ae03a970faa52c49ced1a701d22e1de9eabd`
contains 13 matching item refs, one Weideman `request-evidence` successor
`d62ae8...`, 12 other pending items and zero approvals. Exact run and Artifact
bindings are in `provenance/r43-b1ab-review-workflow-acceptance-20260929.json`
and `provenance/r43-b1ab-review-host-acceptance-20260929.json`. This is a
development reviewer acceptance, not expert approval, license clearance or
stable release.

CodeFusion's subsequent read-only inspection of the isolated product's running
container registration and `product_plugin_releases` row reported the same
development release ref and exact neutral `release.artifacts`: wheel Artifact
`cf://artifact/upload_3b6cf72adddd592f6edba784eaf7a0977ff69fd4bce4bdb3`
at SHA-256 `b1abff...` and catalog ZIP Artifact
`cf://artifact/upload_4b8246a7369ee9581e0e241830f0ea69c3a16cf934cdcc56`
at SHA-256 `afee7fcf...`. The reported canonical registration JSON SHA-256 is
`40a83e4f18e0a4e621912ea61d2d2b8d96831d3701a8b8a4d44011774efbdcf2`;
`runtime_dependency_refs` is empty. D2 hashed the saved owner report and
checked its materials against the indexed wheel, catalog root, workflow and
prior Artifact readback receipts. Direct D2 container inspection was denied
by host permissions, so D2 did not recompute the registration digest or query
the database. The append-only registration evidence is bound to the current
candidate in `provenance/r43-b1ab-review-registration-acceptance-20260930.json`.
This establishes an owner-verified neutral material binding for the isolated
development host, not expert approval, license clearance or formal release.
The old reviewer project's registration remains a separate historical identity.

The verified local scope is the r81/dev58 and r43/dev5 development deliveries,
the corrected adapter successor, and both exact r43 13-item review versions.
The r43 workflow itself records an unpublished-candidate census gap, so these
entries are not an authoritative inventory of every external checkout or host
artifact.

Earlier outbound case manifests also bind development wheels labelled dev12,
dev15, dev24, dev39, and dev5. The local dev24 wheel SHA-256
`a0c665a7d2920650fce832c448c49d4c866260daec0cba0102dd60e3e56c95a0`
and dev39 wheel SHA-256
`be5a2a2b40461ded5c486d9c9689ceaaed987923b9ba428da73ab59ca1eef9b8`
match their outbound manifests. These case-bound inputs do not establish a new
D2-frozen candidate identity or D1 qualification. Version labels alone are
insufficient: a 2026-09-25 dev5 outbound wheel has SHA-256
`1ab011ff5f3c34d833122e6834185122fbff6e2081efaba7b1f765c117306690`,
while the indexed r43/dev5 wheel has SHA-256
`927b33e4a1051d71698714b30d80dfe9da46c7647ebe25fd9c2fedfc6025deda`.
The earlier case records remain at their exact manifests; this check does not
close the unpublished-candidate census gap.

An isolated CodeFusion development host at source Git
`2d3de66e04d81fcbb94fd069bb7f4d93630cd844` indexed the same r43
initial workflow revision in one reviewer project and exported a host snapshot
of that project's 13 pending items. The host Artifact digest is
`sha256:6e46b5fc63b0ab4287aaead559b656a3f97e5c97b6eeee3e7b0d60da0ae52bd5`;
the CodeFusion owner checked the 9,110 downloaded bytes, same-key replay, and
ordinary-user denial. D2 checked the local host receipt against the candidate's
workflow revision and item count, but did not independently download the host
Artifact or compare all exported item refs. The exact D2 acceptance record is
`provenance/review-host-export-acceptance-20260929.json`, bound as an append-only
evidence entry in the development index. Zero review transitions were applied.
This project-scoped export is neither a complete candidate census, scientific
approval, nor a stable outbound release.
It belongs to a new isolated project, not the older workbench project read below.

The same isolated project later applied one non-approving `request-evidence`
action to the indexed Weideman item. Its successor Artifact digest is
`sha256:cad374f922e0b7ea4bed6d2141244bc3b86450ee162163a46b1523c27d24c475`.
The next host snapshot has SHA-256
`9ed3e5d329bee9d01dc0f7f128bb55abd69bcbfdd59903da08e5a78aca37fe99`;
the CodeFusion owner checked 9,750 downloaded bytes, one applied transition
bound to the action run and successor, and 12 unchanged item Artifacts. The
project now has one `needs_evidence`, 12 `review_pending`, and zero approved
items. D2 checked the local action receipt and indexed item identity, but did
not independently download the snapshot or successor Artifact. The exact
record `provenance/review-host-request-evidence-acceptance-20260929.json` is a
second append-only evidence entry for the same candidate. The first snapshot
remains the immutable zero-transition baseline for this project.

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
| Pleiades `stage1-Pleiades-opt-20260921T093633Z` | Frozen source SHA-256 `7c809a0d6d1fb18568e3b70e1a0fcbee7fff42469881b859df2028a373488c5a`; earlier D2-checked comparison candidate SHA-256 `b09804ced2f8cd8c499638d6b68bc39444e72a0351e9be908f8c7519d317baa2`; `coordination/source-first-public-terminal-census-20260927.json` SHA-256 `3b3b8ae9166a03fc1b79c78e4eb2a4dcf4efa93b484d098b04a7fdaa50fb2252`; rev5 successor `coordination/source-first-public-terminal-census-20260929-rev5.json` SHA-256 `fb7754eb21a766e5e7e31802366d20e1dc7c14bfc7cf989c0ea9d7fb5290458b`; `lanes/wi-wham-source-api-domain-wham-control-20260929/attempts/a01/evidence/source-solver-entry-check.json` SHA-256 `773a196789082151d91526b5c81e2f925bc5f787d64bad9762720f273bbc294f` | Source-first census has 5 drivers and 292 terminal-field occurrences; 7 target paths remain open. The WHAM API-domain source check and one equal-temperature canonical terminal comparison passed on the earlier candidate; that variant still lacks its own sealed holdout, and full-source freeze remains open. Historical 52-item SciRel sample stays historical. |
| FIDASIM `stage1-FIDASIM-20260917T053940Z` | Frozen source SHA-256 `c8bd91ecaeac96de7aa08a8eb7eeec435ee63b2a613d37254a607f1b8bc81f70`; current bundle SHA-256 `9677d76a88bf884eec33c66eecd2d03c0c86d63ea5f722acbee286116c02394a`; `coordination/capacity-checkpoint-20260928T012947Z.json` SHA-256 `b7472b11ae95ef8a6517c2504be48ea53a3d550391f08ca9eb482c1259d1b7d5` | Of 146 scoped items, 105 proved, 18 residual and 23 terminal; 0/10 target paths passed, and holdout independence remains unproved. D1 work continues. |
| aorsa3d `stage1-aorsa3d-20260915T170735Z` | r20 `coordination/capability_progress_reopened_20260921_r20/capability_progress.json` SHA-256 `0444d35e4610f0c49784ecf39e2bc4bb0a5c37c0b9dc311993f6d4cd2b7f9705`; reported candidate SHA-256 `d3399929bdf92837aa350accd468dd0fa34cda0090053ea21c438ac5a3fe3da8` | The schema 1.0 r20 record self-reports 5/5 source partitions, 16/16 paths and `full_freeze`. The upstream owner's read-only run of the current `validate_capability_progress.py` against r20, its original scope/matrix/ledger and the live bundle returned exit 1, `valid=false`: `closure_signal` lacks `asset_entry_validation`, and the closure comparison receipts are v1 where the current gate requires v2. D2 independently checked the r20 file hash, schema and missing field, but did not rerun the validator. This is not a current qualified D1 handoff or D2 intake; any recovery needs a new successor with attributable execution evidence, preserving r20. |
| ASCOT5 `stage1-ASCOT5-20260919T173158Z` | `coordination/capability_progress.json` SHA-256 `62272c7e9d43b206f3a56be70729bd818936ba2c036be0ff1e4093d76645e0ba` | The schema 1.0 record self-reports 6/6 source partitions, 11/11 paths and `full_freeze`. The upstream owner's read-only run of the current validator against this record, its original scope/matrix/ledger and the live bundle returned `valid=false` with 23 errors: missing `closure_signal.asset_entry_validation` and 22 v1 closure comparison receipts where v2 is required. D2 checked the record hash, schema and missing field, but did not rerun the validator. This old self-report is not current qualified full-source D1 or D2 intake; preserve it and require a new evidenced successor for any recovery. |
| TokaGrad `stage1-TokaGrad-20260920T025327Z` | `evidence_out/capability_progress.json` SHA-256 `70ebf8708a6581fc4935c77520f5340814f62c564c9b9edc6493468a91798dd1` | The schema 1.0 record self-reports 24/24 source partitions, 22/22 paths and `full_freeze`. The upstream owner's read-only run of the current validator against this record, its original scope/matrix and the live ledger/bundle returned `valid=false` with 45 errors: missing `closure_signal.asset_entry_validation` and 44 v1 closure comparison receipts where v2 is required. D2 checked the record hash, schema and missing field, but did not rerun the validator. This old self-report is not current qualified full-source D1 or D2 intake; preserve it and require a new evidenced successor for any recovery. |
| cql3d `stage1-cql3d-20260916T092101Z` | r1 `evidence_out/project_decomposition_d1_freeze_20260920_r1/capability_progress.json` SHA-256 `8bda8a438f5fd0df06f2539733f033a58c5d637a86fcf805b1beb78cef9f8643` | The record self-reports `full_freeze`, but its own claim ceiling excludes a sealed-holdout campaign. The upstream owner's read-only run of the current validator against the original r1 scope/matrix/ledger and live bundle returned `valid=false`: schema version 1.1 is not the required 1.0, and `closure_signal.asset_entry_validation` is missing. D2 checked the record hash, schema, claim ceiling and missing field, but did not rerun the validator. This is not a current strict full-source D1 freeze or D2 intake; preserve r1 unchanged. |

The indexed `r81-dev58-169` wheel/catalog
(`development:84d0882deca15fdba4dbb9dafeea773b34203f6200628b528ab3fd4636953d7c`)
is a separate `mixed_unverified` development snapshot, not a qualified FIDASIM
D1 handoff. The review record `docs/evaluations/review-version-2026-09-27-r81.md`
on intake branch `647d5dbd36404bc5e76d934a875984787e789644` (SHA-256
`57d74f05db134ff0f6ed2dc1d7996113cd88038c511ce6a761f3be79b919bbaa`)
states that the qualified L1 delivery root was empty and its external NPA
`store_npa` source microprobe could not be independently checked. That NPA
energy-bin leaf exists on the isolated branch but not in the current main
checkout. The indexed development artifact does not by itself qualify a new
mainline scientific intake or transfer the branch's provisional source claim.

The latter seven inputs remain visible here for comparison and follow-up. They do
not create `candidate` entries or imply a new census of the historical 52-item
snapshot. A bounded D1 batch may enter D2 before whole-project freeze once its
own source implementation and numerical comparison have passed.

## PDRK spectrum path screen

The PDRK r9 progress record (SHA-256
`9ddd03747c8d0b6c7f9b8ef99416447750cc6bd435036469fd48ca744b39bcef`)
marks `T-PDRK-SPECTRUM` passed on candidate bundle
`a35bd08ad1afb3912b996d8528317641ea9960b9875bbf0ccabfe8429c3c6310`.
Its canonical and source-origin sealed-holdout comparison receipts have SHA-256
`64dd09b918266de2850f966e153fe7b24f05ffd0863a2f2e8d9e4f948576fb52`
and `38d6fcaafe5c508c46d3c157a4e792e9d1e25d31de8aeb4411806d94f5405e86`.
This numerical path does not use the still-open JPOLE generator.

The same frozen r9 record has `state=reopened` and
`closure_signal.kind=active`. The upstream owner read all 24 canonical and
holdout comparison receipts referenced by its 12 passed paths; each declares
`scirel.extraction-reassembly-comparison.v1`. The current validator requires
v2 receipts for `full_freeze` or `bounded_delivery`, so this receipt version
alone does not trigger that gate for r9's `reopened/active` state. D2 checked
the r9 hash and state fields, but did not rerun r9 against the later live
`7b69c725...` bundle. Its passed-path claims and v1 receipts remain bound to
the old `a35bd08a...` candidate and cannot establish a current full freeze.
A future full-freeze successor would also require freeze-level
`asset_entry_validation`. This version and candidate-binding limit is separate
from the open J-pole path; r9 is not a D2 intake.

The saved PDRK `task_graphs/kinetic_dispersion_relation` is not the existing
SciRel graph of the same name. SciRel evaluates two kinetic determinants at one
wavepoint; PDRK combines loss-cone partitioning, an EM3D matrix and an
eigensolve to return a complex-frequency spectrum. The five PDRK node
relations therefore need individual scientific comparison before reuse.

The exact PDRK graph YAML (SHA-256
`69f911ef51b0d76de51f509fa49931ba4706537e8a6a5c1c32040a911edeb488`)
omits `c2` and `vds` from the scale node outputs, EM3D node inputs and edges,
although the executable graph (SHA-256
`529302e91ee886d6f6acd89382e35b394dc5ec46234d819491d9bde64311bf5d`)
passes both values and the EM3D operator requires them. It also declares
`graph_order` shape `(6,)` while the executable graph and direct test return
five node labels. The runtime source comparison does not verify this YAML
port contract. At screening time, no bounded handoff was found for this path;
a D1 successor needed to bind the corrected graph contract and exact candidate
bytes before D2 could credit this as an importable TaskGraph. The frozen r9
evidence stays unchanged.

The PDRK owner subsequently recorded a structural D1 successor at
`evidence_out/d1_successor_spectrum_graph_contract_20260929/successor_record.json`
(SHA-256 `bb99bbe5f3cfd53bcadd2b7aff02f69f80d8df33914afff07fbd2549c57f28b5`).
It binds candidate bundle `5516b7998753283db982d3df26598aed0bd0f0295b22d2536609b5dfc4f921ab`:
the YAML declares the internal `c2` and `vds` ports and edges and the five-label
`graph_order`, while the executable graph pins the corrected YAML hash. Eight
focused graph tests, import-intake, and source-free checks passed on that bundle.
The predecessor canonical and sealed-holdout receipts bind only `a35bd08a...`;
no new numerical receipts were established at `5516b799...`. Both
`T-PDRK-SPECTRUM` and `T-PDRK-JPOLE-GENERATOR` remain OPEN, with the latter
still subject to the canonical plus independent same-path sealed-holdout gate.
This successor is not a qualified D1 handoff, full freeze, or D2 intake.

Read-only D2 comparison of the five node contracts on `5516b799...` found no
direct callable reuse in the current SciRel kinetic domain:

| PDRK node | Nearest current SciRel relation | Contract difference preventing direct reuse |
| --- | --- | --- |
| `species_equilibrium_scales` | `derive_species_equilibrium_scales` | PDRK converts charge/proton-mass inputs, separate parallel/perpendicular eV temperatures and light-speed-normalized drift; fluidBW takes SI charge/mass and one reference-scaled temperature. Their constants and first-species versus minimum cyclotron normalization also differ. |
| `loss_cone_partition` | `solve_loss_cone_spectrum` | PDRK forms algebraic core/loss-cone weights and `(2, species)` thermal branches. SciRel's existing relation solves an angular Legendre eigenproblem; it does not produce those branches. |
| `z_pole_coefficients` | `get_z_pole_coefficients` | Both return `bzj`/`czj`, but PDRK supports J=4/8/12 and its J=8/12 tables differ from the fluidBW J=8/12 tables. Matching port names do not license replacing either source-specific pole set. |
| `em3d_dispersion_matrix` | `assemble_fluid_dispersion_matrix` and the kinetic determinant operators | PDRK assembles a sparse, two-branch kinetic matrix at fixed `kx,kz` whose eigenvalues are complex frequencies. The fluidBW matrix solves for perpendicular wavenumber at fixed frequency; its kinetic operators evaluate determinants, not this eigenmatrix. |
| `dispersion_eigensolve` | `solve_fluid_wavevector_eigenproblem` | PDRK offers dense full-spectrum or sparse near-guess frequency roots ordered by descending growth. SciRel filters and orders perpendicular-wavenumber roots by propagation and damping. |

This is a relation and dependency screen, not numerical equivalence evidence.
The PDRK five-node graph remains a separate candidate composition pending its
same-bundle D1 source comparisons and D2 import checks.

The same `5516b799...` graph has one further unresolved declared-port origin:
`em3d_dispersion_matrix` lists `S` as an input, while its YAML gives `S` no
caller input, producer output, or edge/transform. The executable graph passes
`S=len(scales["qs"])`. Its new structural test checks `c2`, `vds`, and order,
but not this derived species count. D1 owns the exact graph-contract successor;
the passing tests and intake probe do not close this D2 dependency finding.

The subsequent D1 `S` successor at
`evidence_out/d1_successor_spectrum_species_count_20260929/successor_record.json`
(SHA-256 `7f1b94346c28fcef83888f232358bf864060f18418562ce19477b98807645743`)
binds a new 67-file candidate digest
`7b69c725cf218159f8e24f04095f57216cb4ab12c4d0a3bce95bf44378ff1d5b`.
D2 read the frozen record and checked the candidate YAML, executable graph,
test-file hashes, and fresh receipt hashes. YAML now has one required
`species_equilibrium_scales.qs -> em3d_dispersion_matrix.S` edge with
`transform: length(qs)`; the graph passes `len(scales["qs"])`, and its regression
asserts the runtime value. The new `splus-r11-1` probe exited 0; eight graph
tests, import-intake and source-free checks passed. Spectrum and PDF each have
new canonical and sealed-holdout receipts bound to that same candidate digest.
The PDF comparison uses positional `z` alignment at its original tolerance;
the saved cross-position negative control fails while a flattened multiset
would pass. The prior `modular-r10-1` exit-1 PDF failure remains historical.
The D1 record explicitly leaves `T-PDRK-JPOLE-GENERATOR` OPEN and sets
`full_freeze=false`, `d2_intake=false`, and `exported=false`. This closes the
reported `S` contract discrepancy for this successor but does not register a
PDRK D2 candidate or change the SciRel index.

The Pleiades equal-temperature WHAM API-domain canonical attempt `a02` has an
exact comparison at `lanes/wi-wham-source-api-domain-terminal-comparison-20260929/attempts/a02/evidence/wham-api-domain-terminal-comparison.json`
(SHA-256 `2a552662e1a873ef7eea8b2b11946f8735be504c9247b8fd022dedeb80b56135`)
and result arrays `wham-api-domain-terminal-states.npz` in the same directory
(SHA-256 `d9a6c4228bb6ba69fafc39b9590734d6081f74d90d7d4d75b96fa41c3b392457`).
The comparison reports 105/105 terminal fields passed at `atol=rtol=1e-12`,
equal source/candidate input digests, and convergence in 10 iterations on each
side. The wrapper receipt reports exit code 0, no network, and read-only source
and candidate mounts. Its own classification is a source-supported API-domain
variant, not the literal public-driver default or a sealed holdout. This receipt
alone does not qualify a new D1 handoff or change the index.

The read-only independent follow-up at
`coordination/reviews/wham-api-domain-canonical-followup-20260929.json`
(SHA-256 `b32930c5e5aa1c91110d9ae4be970273be2a296af28bf6991e9dac94cff7b582`)
accepts this 1000/1000 eV canonical case with a candidate-continuity condition:
the coordinator was the sole candidate writer, no file mtime postdates a02,
and a supplemental read-only mounted-tree probe recomputed the recorded digest
and 134-file count. The original a02 probe did not itself recompute that digest.
The literal 1000/2000 eV public-driver default still fails the source
integrability guard. The follow-up grants no independent holdout, whole-source
closure, full freeze, export, or D2 intake status.

The unchanged source-first census also counts 146 embedded-data field
occurrences alongside the 292 public-driver terminal-field occurrences, for
438 source output/artifact occurrences in total. A disposition label for each
occurrence is not a numerical validation. The current WHAM contract map at
`coordination/wham-kinetic-closure-contract-map-20260929-v2.json`
(SHA-256 `95033ec0775544cd362252ae89b065b12c7ceda19b56428a87562aa752f66de6`)
binds bounded graph-contract/source-branch tests and the accepted a02 canonical
case. It also preserves a fixed-a05 105/105 numerical comparison whose
independent holdout admission remains pending, and identifies a public-driver
serialization-key defect. Neither the bounded graph test nor these finite
comparisons closes the remaining source paths or qualifies a D1 handoff.

The additive Pleiades rev5 source census (SHA-256
`fb7754eb21a766e5e7e31802366d20e1dc7c14bfc7cf989c0ea9d7fb5290458b`)
retains that source denominator and all seven target paths. It explicitly
disposes the broken `mirror_equilibrium` wrapper as a non-candidate entry while
retaining its six executable physical subrelations, including the free-boundary
coil-current constraint. Its current candidate map assigns all 438 occurrences,
but 378 remain unvalidated and no target has a complete canonical plus
independent holdout receipt. This source-scope disposition neither removes the
retained physics nor qualifies a D1 handoff or D2 intake.

The WHAM terminal-denominator reconciliation at
`coordination/wham-terminal-denominator-reconciliation-20260929.json`
(SHA-256 `f52a6a1fbddccbd45c9c3e80daad48bbc1cea7cd21a07a8fd8a3074a7873b326`)
binds the same frozen source and `b09804ced2f8cd8c499638d6b68bc39444e72a0351e9be908f8c7519d317baa2`
candidate to the a02 API-domain comparison. Its 56 unique source-declared
WHAM archive/summary rows map to 57 distinct comparison outputs marked passed;
the predecessor map, a02 comparison, and source projector hashes match its
references. The frozen public driver uses three unsuffixed flux keys where the
source state has `_m2_s` keys, so its archive and subsequent summary are not
materialized. The comparison projects source-computed state with the actual
producer keys. This bounded reconciliation does not validate the literal
1000/2000 eV default, admit an independent holdout, close the full-source
denominator, or qualify D1 intake. A changed candidate digest needs fresh
comparison evidence.

The FLAME kinetic public canonical source-only attempt `a02` at
`lanes/wi-flame-kinetic-source-canonical-20260929/attempts/a02/evidence/`
has a probe receipt SHA-256
`ca4caf3400f8bc34f87bb0a82e1f6741c08bb8e6324d59599094d5fd81d6fc35`
and source-intermediates record SHA-256
`7b9b65da178fae537bc7ebd42d618758796467cf0cde13e77d3420bcc081215f`.
The frozen source converged in four iterations on its 151 by 51 mesh and
materialized 35 NPZ fields and 25 summary fields; both output hashes and the
intermediate-array hash match the record. The source mount was read-only,
candidate mounting was unavailable, and the probe reports no candidate read.
The record preserves the source summary's omitted `dR` volume weight as a
known behavior, not an endorsed correction. This is a source-side baseline
only: no candidate comparison, independent holdout, whole-source closure, or
D1 intake follows from it. The failed `a01` receipt remains separate.

For the earlier `b09804ced2f8cd8c499638d6b68bc39444e72a0351e9be908f8c7519d317baa2`
candidate, `task_graphs/device_vacuum_field/graph.py` (SHA-256
`e7c8ad607534670a43fde57754fa2d8969b38202532b609fbaeaca7d6be1c62f`)
calls `device_coil_configuration(preset)`. That operator (SHA-256
`66b3491cdc035018689b8713956d3a08150a51462d2d32fad56277b508fcd77b`)
registers only `wham` and `brb`. A focused source-fidelity pass for the
separate `flame_coil_filaments` operator has probe receipt SHA-256
`f39f5b0764ea3bfc8b4c4be347478640e826e0432095105d3b67a82eb0bc98a1`
and log SHA-256 `b26b48fa378229daa452dcd365d7fbfb3783f19dd1a17a38da089f511f4dabd7`;
its 4108-filament source comparison reports zero absolute and relative error.
That local result alone did not establish a composed FLAME field/Green TaskGraph
path or 60-field terminal parity. The later a03 comparison below covers one
canonical path, without granting intake credit.

The later Pleiades candidate SHA-256
`9eb0bad7b4021689a6a9d64d1b9d0a22b627dcb0a5a97cfcbe8791c85f767e93`
has a FLAME terminal reassembly comparison at
`lanes/wi-flame-terminal-reassembly-20260929/attempts/a03/evidence/flame-terminal-reassembly-comparison.json`
(SHA-256 `766a808aa155f3144c0cceeebe654998edc8be1a9987eb6f47fefae4c8b56577`).
D2 checked that report's bytes and its source/candidate digests: 35 archive
fields and 25 summary fields passed at `atol=rtol=1e-12`, with zero failed
fields. The D1 coordination record gives this canonical case no independent
holdout credit. WHAM a06 admission and whole-source closure also remain open,
so this is neither a qualified D1 handoff nor an index entry.

## Review-slice dependency closure

The current r43 candidate binds 13 retained review items, but this slice alone is not a
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

The declared dependencies in the submitted r43 documents are not the whole
runtime import closure. `kinetic-dispersion-ronnmark` calls the separately
indexed `ronnmark-r-function`, and `kinetic-wavevector-roots` calls
`kinetic-dispersion-ronnmark`; the submitted documents list no version
dependencies for those callers. The current development exact documents now
record both edges. Those imported modules are among the 13 review items, but a
smaller approved subset selecting either caller alone cannot form an importable
wheel. The first-release source preparer rejects such a selection. The current
document corrections require exact reviewer successors before they can govern
approval or release; both submitted workflow versions retain their original
document digests and frozen review artifacts.

The current corrected documents are bound by Git `d794fdc` and have these
canonical-JSON digests. The submitted digests remain the ones in the index;
this table is a D2 successor input, not a host-issued review successor or an
approval event.

| Review item | Submitted document | Corrected development document |
| --- | --- | --- |
| `scirel-review-item:0d72a89726790d2dda217f52b8ee89b7e433b8de80074ba8545945989b2a7cd6` (`kinetic-dispersion-ronnmark`) | `sha256:1e46df1ba8b7cd17edb6eaf4687be11ce527a03b5f63d8ffd22cec59c1369396` | `sha256:2c79d1dc3ace5516f57b212eab2794e4118e42139daa69234d5d9a888b166033` |
| `scirel-review-item:765b51697dfde7549eb64be905d7bfe069c067359b28dc1b8f7e8574a1176338` (`kinetic-wavevector-roots`) | `sha256:8771407744edb8adb71fa64276e9cdfd6ce824b076c32c263dc5ad08d6e7885e` | `sha256:6d9e7459db7f6f768bcdae3a0a690eb91c315252851cf0d0ac3d2a7d1d2d5aa7` |

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
