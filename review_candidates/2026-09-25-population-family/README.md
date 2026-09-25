# Candidate: KN1DPy atomic-hydrogen population family (three assets)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r56 successor of r55. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `7222f2b584e368c7399182f6227117930005f9d8` (r55,
  `review-2026-09-25-r55-index-paths`, 90 assets dev27, `pending_unapproved`;
  wheel/catalog bytes reused from r54 with stated provenance).
- Unpublished candidate pool: the 52-asset Pleiades development sample and the
  two additional snapshots, unchanged; none contains an ionization,
  recombination or equilibrium-population asset (re-checked by relation, not
  by name — the r49 COLLRAD asset is a density-dependent H0 ionization table,
  a different relation from these temperature-only or equilibrium forms).
- Incoming source: the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn).

## Inventory (all rows candidate-ready)

| Saved package | Disposition | Proposed SciRel identity | Material differences | Evidence (collect-verified) |
| --- | --- | --- | --- | --- |
| Janev电子碰撞电离率 (sigmav_ion_h0.py:1-22 + sigmav_ion_hh.py:1-27) | add new capability | scirel.collisions.janev-electron-impact-ionization-rate-coefficient | nonpositive-temperature rejection with a named error (saved folded temperature+species checks into one generic error and clipped silently); closed species enum H/H2 kept; both fits bit-preserved | 8 direct + 4 replay |
| 原子氢1s辐射复合速率 (sigmav_rec_h1s.py:3-25) | add new capability | scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient | nonpositive-temperature rejection; frozen Storey-type constants and closed form bit-preserved | 6 direct + 3 replay |
| 原子氢Saha平衡人口密度 (jh_related/nh_saha.py:25-46) | add new capability | scirel.kinetic.hydrogen-saha-equilibrium-population | **no repair** — the saved formal implementation already enforced its declared contract (scientific-branch-only exposure, 1-D paired inputs, positive finite domain, integer level, finite positive result); reproduced bit for bit | 7 direct + 4 replay |

Relations kept distinct and not merged: the three leaves are sibling
population-data relations, not one relation — the Janev leaf is a
two-species dispatch between different physical systems (its two branches
disagree numerically and the enum is closed); the recombination leaf fixes
the ground state n=1 with its own frozen constants; the Saha leaf is an
equilibrium population (m^-3), not a rate coefficient, and is placed in the
`kinetic` domain accordingly. No reuse, variant, duplicate or composition
disposition applies. Deferral honored: this is the next batch of the KN1DPy
leaves r46/r49 deferred. Still deferred: wall/source sequences, adaptive
mesh, cross-grid interpolation, BoltzmannRHS assembly, SIG matrix assembly.

## Files

- `proposal/janev_electron_impact_ionization_rate.py` and tests
- `proposal/atomic_hydrogen_1s_radiative_recombination_rate.py` and tests
- `proposal/hydrogen_saha_equilibrium_population.py` and tests
- three `proposal/scirel.*.json` exact documents

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r56 freeze commit.
