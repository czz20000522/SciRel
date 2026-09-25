# Candidate: KN1DPy molecular-hydrogen charge-exchange pair (two assets)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r51 successor of r50. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `8b8dd150fe5778da8bd88fdf9c66b05c37f2c954` (r50,
  `review-2026-09-25-r50-installed-runtime`, 74 assets dev24,
  `pending_unapproved`; wheel/catalog bytes reused from r49 with stated
  provenance).
- Unpublished candidate pool: the 52-asset Pleiades development sample and the
  two additional snapshots, unchanged; none contains a molecular-hydrogen
  collision-data asset (re-checked by relation, not by name).
- Incoming source: the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn).

## Inventory (both rows candidate-ready)

| Saved package | Disposition | Proposed SciRel identity | Material differences | Evidence |
| --- | --- | --- | --- | --- |
| 分子氢电荷交换截面 (sigma_cx_hh.py:5-23) | add new capability | scirel.collisions.molecular-hydrogen-charge-exchange-cross-section | one documented repair: negative-energy rejection; fit arithmetic bit-preserved | 8 direct + 3 replay tests |
| 分子氢电荷交换Maxwellian速率系数 (sigmav_cx_hh.py:5-95, N15) | add new capability | scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient | two documented repairs: nonpositive-temperature and negative-energy rejection; summation order bit-preserved | 9 direct + 4 replay tests |

Relations kept distinct and not merged: the two H2 assets are sibling fits of
one process, not one relation, mirroring the r49 atomic pair; the molecular
fits are different physical systems from the atomic ones (distinctness is
asserted numerically in both directions); the rate-coefficient fit is not the
Maxwellian average of the cross section — the averaging relation remains
`maxwellian-relative-speed-rate-average`, whose `cross_section_m2` port the
molecular cross section can serve (composition test included). No reuse,
variant, duplicate or composition disposition applies.

Deferral honored: this is the second batch of the leaves r46/r49 deferred
(molecular H2 family). Still deferred: elastic momentum-transfer cross
sections, dissociation rates, wall/source sequences, adaptive meshes,
cross-grid interpolation, BoltzmannRHS assembly.

## Files

- `proposal/molecular_hydrogen_charge_exchange_cross_section.py` and tests
  (`test_molecular_hydrogen_charge_exchange_cross_section.py`, `_l1.py`)
- `proposal/hydrogen2_charge_exchange_rate.py` and tests
- `proposal/scirel.collisions.molecular-hydrogen-charge-exchange-cross-section.json`
- `proposal/scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient.json`

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r51 freeze commit.
