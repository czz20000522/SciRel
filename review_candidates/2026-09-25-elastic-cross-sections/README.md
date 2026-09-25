# Candidate: KN1DPy elastic momentum-transfer cross-section family (five assets)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r53 successor of r52. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `380cdb1a7f86f4b2690c9d05a380e16a4f06f758` (r52,
  `review-2026-09-25-r52-evidence-correction`, 76 assets dev25,
  `pending_unapproved`; wheel/catalog bytes reused from r51 with stated
  provenance).
- Unpublished candidate pool: the 52-asset Pleiades development sample and the
  two additional snapshots, unchanged; none contains an elastic
  momentum-transfer cross-section asset (re-checked by relation, not by name).
- Incoming source: the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn).

## Inventory (all rows candidate-ready)

| Saved package | Disposition | Proposed SciRel identity | Material differences | Evidence (collect-verified) |
| --- | --- | --- | --- | --- |
| 原子氢弹性动量转移截面 (sigma_el_h_h.py:19-38) | add new capability | scirel.collisions.atomic-hydrogen-elastic-cross-section | negative-energy rejection; 0-d-scalar selector requirement (saved relied on bool() coercion: silent 0-d/size-1 acceptance, generic ambiguity failure for larger arrays); both branch arithmetics bit-preserved | 8 direct + 4 replay |
| 原子氢质子弹性动量转移截面 (sigma_el_p_h.py:1-42) | add new capability | scirel.collisions.proton-atomic-hydrogen-elastic-cross-section | negative-energy rejection; the 10 eV strict-branch breakpoint zero and the np.array([E]) leading-axis wrapper kept as declared source behavior | 6 direct + 3 replay |
| 原子氢分子氢弹性动量转移截面 (sigma_el_h_hh.py:1-31) | add new capability | scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section | negative-energy rejection; the np.array([E]) leading-axis wrapper kept as declared source behavior | 5 direct + 3 replay |
| 分子氢分子氢弹性动量转移截面 (sigma_el_hh_hh.py:1-31) | add new capability | scirel.collisions.molecular-hydrogen-elastic-cross-section | negative-energy rejection; the saved implementation's own scalar-boolean/integer selector validation and same-fit viscosity fallback kept as declared behavior | 6 direct + 3 replay |
| 分子氢质子弹性动量转移截面 (sigma_el_p_hh.py:1-31) | add new capability | scirel.collisions.proton-molecular-hydrogen-elastic-cross-section | negative-energy rejection; fit arithmetic bit-preserved | 6 direct + 3 replay |

Relations kept distinct and not merged: the five assets are sibling fits for
five different species pairs (H–H, H+–H, H–H2, H2–H2, H2–H+), each a separate
identity; none derives from another. The H–H asset additionally carries the
source's distinct viscosity fit as a second branch — a different quantity, not
a parameterization of the momentum-transfer fit. No reuse, variant, duplicate
or composition disposition applies; the composition test covers the H–H
momentum-transfer fit serving the retained Maxwellian rate-average port.
Deferral honored: this is the next batch of the KN1DPy leaves r46/r49 deferred
(molecular/atomic elastic momentum-transfer cross sections). Still deferred:
dissociation-rate family, wall/source sequences, adaptive mesh, cross-grid
interpolation, BoltzmannRHS assembly.

## Files

- `proposal/atomic_hydrogen_elastic_cross_section.py` and tests
- `proposal/hydrogen_proton_elastic_cross_section.py` and tests
- `proposal/hydrogen_h2_elastic_cross_section.py` and tests
- `proposal/hydrogen2_hydrogen2_elastic_cross_section.py` and tests
- `proposal/hydrogen2_proton_elastic_cross_section.py` and tests
- five `proposal/scirel.collisions.*.json` exact documents

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r53 freeze commit.
