# PDRK EM1D exact-d34 derived receipt audit (2026-09-30)

Status: bounded canonical and independently sealed-holdout comparison evidence
and independent source-to-candidate scientific review exist for
`T-PDRK-BEAMMODE-EM1D`. The current-digest r11 strict progress snapshot grants
credit to this path only.
This is not a PDRK `full_freeze` or D2 intake decision. J-pole remains OPEN under
the unchanged two-axis gate.

The frozen source tree digest is
`7ceab1c6383a474ec55095c7ff19316db5c1b739855e495a6b325f0f110b39e4`.
The exact candidate bundle digest is
`d34b0a3694315e0d3f037a23eac4367609a128464b6957f96de26716bffceadf`.
The candidate-blind `strict-src-6` source oracle probe exited 0 with the
candidate unavailable. The candidate-only r1 probe exited 0 with the source
and candidate mounts read-only and network `none`; its terminal receipt SHA-256
is `479f771764c70a667eae1502a05ab2da79cc4c18245d150b1d0236be418f16cb`.
The r1 raw output and oracle bytes were retained. Its first v2 comparison
receipts lacked required schema fields and are not admissible closure receipts.

A fresh saved-output adapter used precommitted, hash-checked copies of those
bytes and did not rerun either science implementation. Its exit-0 wrapper
receipt is SHA-256
`cea3ae30341d1ea58a1493e422391f8f4113536df2518ccf673ff9d0958b23e7`.
The derived receipt index is SHA-256
`63f798987506191ed567710e41e5544fb4dee7c3f43b45edefdc40aa03aebf54`.
Canonical receipt `EX-EM1D-CAN` is SHA-256
`e718f260e375339ee3d92a674602fb762f684c4082fd80bb3d178be9817ae4c6`;
sealed holdout receipt `EX-EM1D-HOLD` is SHA-256
`c98c7f79ed7d88cd61d74e0e3daf6e534f7dd43a72192dac4d79f97745454d75`.
Both bind the same candidate digest, their distinct source/bundle input digests,
the original exit-0 candidate probe receipt, the saved source oracles, and
unchanged tolerance-contract SHA-256
`08d8977c9b454e4134c7ae0b97cce0aa90c5cfec3c75442dd17d9e520e86e68e`.

| Case | `k` max absolute error (bound `1e-12`) | Positional `w` max absolute error (bound `1e-5`) |
| --- | ---: | ---: |
| Canonical | `2.117582368135751e-22` | `2.2361388016374403e-11` |
| Sealed holdout | `2.117582368135751e-22` | `1.0592650197121205e-7` |

Both cases passed a cross-index swap negative control: the multiset remained
unchanged, while positional comparison rejected the swap. The source oracles
did not emit a composite `source_input_digest`; the coordinator derived each
digest from the exact deck/control input manifest, so independent review must
check that manifest against the frozen source execution. That review is recorded
below. The adapter's schema shape and file hashes have been read-only checked.
Preserve r1 and all earlier attempts unchanged.

## Independent scientific review

Read-only review of the frozen `em1d_dr.m`, `faddeeva.m`, `pdrk_setup.m` and
`pdrk_initialize.m` against the exact d34 candidate found the same four-species
dispersion sum, signed cyclotron term with `pm=1`, SI species scales, default
Weideman `N=16`, initial `(0.05+0.04i)*wcs1` seed, and ordered continuation
over `k=(0.01:0.01:0.5)/cwp`. The candidate uses SciPy `hybr` in place of the
source's Octave `fsolve` call; the saved output comparison, rather than solver
identity, supports this bounded equivalence claim.

The canonical deck SHA-256 is
`cc679af7916ec967cd1566310c8e49a1b0a72996d0b68a9e9ac0f78f5ae3f0ee`;
the holdout deck SHA-256 is
`b6afc0e278ff3d934b75b286e0dce8d6b5328bc5afeddd8d3a3fae1731fa71f6`.
Both match the earlier run-level sealed deck manifest and the deck copies used
by the candidate probe. The source probe script copied each deck to
`code/input/pdrk.in` before running the frozen setup, initialization and EM1D
script. It used the source's fixed `B0=60e-9 T`, grid, branch and Faddeeva
default. Its wrapper reports an unavailable candidate mount, network `none`,
Octave exit 0 for both cases, and `nk=nw=50` with finite outputs. The source
oracles retain distinct SHA-256 values
`d1bf716309f69c73999d7d3814a67038d677b8a477c03270b0c9e159038fb9b2`
and `b8fa8bd50398809d18462d17ba27993ff3b8696cbe0a1a65987c439daa0a60ea`.

The receipt adapter checked the saved raw candidate arrays and source oracle
hashes, equal 50-point shapes, finite values, and positional `k,w` errors
under the original bounds. A first/last-root swap preserves the candidate
multiset but exceeds the `w` bound in both cases. The reviewed source input
manifest covers the exact deck SHA-256 and source control values; its composite
digest was derived later by the coordinator because the source oracle did not
emit one. This is an acceptable, explicitly attributed saved-output binding
for the bounded comparison, not a new source execution or a claim about other
EM1D inputs. Independent scientific review accepts the two exact-d34 cases.

## Current-digest strict snapshot

The coordinator's r11 `capability_progress.json` is SHA-256
`382b4b040e95651ddb9a0d5f825e3100d942f6f9fcdaa03b587b15be040bb9d6`.
Its bound review record is SHA-256
`d8e46df3334ff1875833ce19a62b00a658001dfab9799a31216824595468b06f`.
An independent read-only run of the deployed schema-1.0 progress validator
against the frozen scope manifest, evidence matrix, current ledger and exact
d34 bundle returned `valid=true` and `errors=[]` with
`--require-closure-signal`. The snapshot credits only
`T-PDRK-BEAMMODE-EM1D`: 11 other paths require current-digest reassembly, and
`T-PDRK-JPOLE-GENERATOR` remains OPEN under the unchanged two-axis gate. PDRK
remains active and has no `full_freeze` or D2 intake claim.
