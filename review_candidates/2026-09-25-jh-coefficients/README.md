# Candidate: KN1DPy Johnson-Hinnov coefficient B-spline family (three assets)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r57 successor of r56. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `93bb7cc` (r56, atomic-hydrogen population family, 93 assets
  dev28, `pending_unapproved`).
- Unpublished candidate pool: the 52-asset Pleiades development sample and
  the two additional snapshots, unchanged; re-checked by relation (not by
  name) for B-spline coefficient evaluations, Johnson-Hinnov rate
  coefficients, or hydrogen line-radiation diagnostics — none exists in the
  pool. The baseline holds no B-spline coefficient-table evaluation either:
  the closest neighbors are the Maxwellian relative-speed average (a mesh
  average, different relation), the Bosch-Hale analytic reactivity
  (temperature-only analytic parameterization, different model), and the
  r56 population leaves (closed forms, not splines). All three incoming
  leaves are therefore **new capabilities**; no reuse, variant, duplicate or
  merge disposition applies to them.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  operator package `原子氢JH-r系数B样条评价`, implementation pinned by
  SHA-256 `253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344`.

**Qualification status.** The qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) is empty
(re-checked this round), and KN1DPy's strict D1 qualification has been
withdrawn. Every comparison in this proposal is therefore bounded historical
development evidence, not qualified-L1 provenance, and does not become
expert approval of the SciRel relation.

## Inventory (all rows candidate-ready)

| Saved callable | Disposition | Proposed SciRel identity | Material differences | Evidence (collect-verified) |
| --- | --- | --- | --- | --- |
| `evaluate_h_jh_r_coefficient` (anchor `jhr_coef.py:12-66`) | add new capability | scirel.collisions.hydrogen-jh-r-coefficient | **no repair** — saved formal contract (1-D paired profiles, ion {0,1}, level [2,6], knot/tensor consistency, `no_null=1` only) reproduced bit for bit; the no_null=1 null-sentinel density overwrite is preserved and recorded as an open expert question | 7 direct + 4 replay |
| `evaluate_h_jh_s_coefficient` (anchor `jhs_coef.py:24-60`) | add new capability | scirel.collisions.hydrogen-jh-s-coefficient | **no repair** — payload validation (exact field set, order 4, 77-coefficient knot geometry) and the density-consuming evaluation reproduced bit for bit | 5 direct + 4 replay |
| `evaluate_h_jh_alpha_coefficient` (anchor `jhalpha_coef.py:10-64`) | add new capability | scirel.collisions.hydrogen-jh-alpha-coefficient | **no repair** — the null-sentinel density overwrite and input-immutability guarantee reproduced bit for bit, recorded as an open expert question | 6 direct + 4 replay |

Relations kept distinct and not merged: the three leaves are sibling
evaluations of one saved operator package, but each evaluates a different
coefficient vector under a different density semantics — r selects an
(ion, level) slice from an explicit `(n, 2, 5)` tensor and overwrites
density with the source's `1e32` sentinel; s consumes the caller's density;
alpha reads its own vector, overwrites density, and guarantees the caller's
input is never mutated. Merging them would hide the density-semantics split
that the saved source itself exhibits. The in-package Saha relation
(`evaluate_h_saha_population`) is **already integrated** as
`scirel.kinetic.hydrogen-saha-equilibrium-population` (r56) and is not
re-added; a domain-boundary difference between the saved package's internal
copy (positive finite only) and the integrated asset (positive finite below
1e32) is recorded for the radiation successor batch. The package's
radiation diagnostics (`evaluate_lyman_alpha`, `evaluate_balmer_alpha`,
`invert_balmer_alpha_to_ground_state`) and the payload producer
(`produce_jh_coefficient_payload`) are **deferred**: the diagnostics compose
the already-integrated Saha asset with these coefficients and are best
reviewed as a successor composition batch; the payload producer
materializes packaged coefficient data, and admitting coefficient data as a
SciRel artifact is a separate expert decision. Still deferred from r46/r49/
r56: wall/source sequences, adaptive mesh, cross-grid interpolation,
BoltzmannRHS assembly, SIG matrix assembly.

## Files

- `proposal/hydrogen_jh_r_coefficient.py`, `hydrogen_jh_s_coefficient.py`,
  `hydrogen_jh_alpha_coefficient.py` and their two test files each
- three `proposal/scirel.collisions.hydrogen-jh-*.json` exact documents

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r57 freeze commit.
