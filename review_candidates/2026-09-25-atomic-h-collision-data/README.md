# Candidate: KN1DPy atomic-hydrogen collision data family (three assets)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r49 successor of r48. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `dbb4385b2ec428c04c8706a484694d598ad14412` (r48,
  `review-2026-09-25-r48-representability`, 71 assets, `pending_unapproved`).
- Unpublished candidate pool: the 52-asset Pleiades development sample and the
  two additional snapshots, unchanged since the r41 comparison; none contains a
  hydrogen collision-data asset (re-checked by relation, not by name).
- Incoming source: the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn).

## Inventory (all rows candidate-ready)

| Saved package | Disposition | Proposed SciRel identity | Material differences | Evidence |
| --- | --- | --- | --- | --- |
| 原子氢电荷交换截面 (sigma_cx_h0.py:7-32) | add new capability | scirel.collisions.atomic-hydrogen-charge-exchange-cross-section | two documented repairs: negative-energy rejection, scalar-only branch selector; branch arithmetic bit-preserved | 8 direct + 4 replay tests |
| 原子氢电荷交换Maxwellian速率系数 (sigmav_cx_h0.py:8-95, N25) | add new capability | scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient | two documented repairs: nonpositive-temperature and negative-energy rejection; summation order bit-preserved | 7 direct + 4 replay tests |
| COLLRAD_H0电子碰撞电离率 (collrad_sigmav_ion_h0.py:16-217) | add new capability | scirel.collisions.collrad-h0-ionization-rate | one documented repair: equal-shape inputs and shape-preserving output; table and interpolation bit-preserved | 10 direct + 4 replay tests |

Relations kept distinct and not merged: the two charge-exchange assets are
sibling fits of one process (a cross section and a bivariate rate-coefficient
fit), not one relation; the rate-coefficient fit is not the Maxwellian average
of the cross section, and
`scirel.collisions.maxwellian-relative-speed-rate-average` remains the only
averaging relation. No reuse, variant, duplicate or composition disposition
applies: no baseline or pool asset evaluates a hydrogen collision coefficient.

Deferral honored: r46 explicitly deferred "电荷交换速率系数等叶节点" to a later
evidence-bounded batch; this is that batch. The remaining KN1DPy leaves
(adaptive meshes, cross-grid interpolation, molecular-H2 family, wall/source
sequences, BoltzmannRHS assembly) stay deferred.

## Files

- `proposal/atomic_hydrogen_charge_exchange_cross_section.py` and tests
  (`test_atomic_hydrogen_charge_exchange_cross_section.py`, `_l1.py`)
- `proposal/atomic_hydrogen_charge_exchange_rate.py` and tests
- `proposal/collrad_h0_ionization_rate.py` and tests
- `proposal/scirel.collisions.atomic-hydrogen-charge-exchange-cross-section.json`
- `proposal/scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient.json`
- `proposal/scirel.collisions.collrad-h0-ionization-rate.json`

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r49 freeze commit.
