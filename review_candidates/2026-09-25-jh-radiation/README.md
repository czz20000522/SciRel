# Candidate: KN1DPy Johnson-Hinnov hydrogen radiation diagnostics family (three task graphs)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r59 successor of r58. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `2d3a89c` (r58, Johnson-Hinnov degree-convention correction,
  96 assets dev30, `pending_unapproved`).
- Unpublished candidate pool: the 52-asset Pleiades development sample and
  the two additional snapshots, unchanged; re-checked by relation (not by
  name) for hydrogen line-emission or population-inversion compositions —
  none exists in the pool. The baseline composes no hydrogen radiation
  relation either: the r57 coefficient assets are the closest neighbors and
  become the bound dependencies of this batch, not duplicates. All three
  incoming relations are therefore **new capabilities** as task graphs; no
  reuse, variant, duplicate or merge disposition applies to them.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  operator package `原子氢JH-r系数B样条评价`, implementation pinned by
  SHA-256 `253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344`.
  All imports of the saved tree ran `python -B` with
  `PYTHONDONTWRITEBYTECODE=1`; the round wrote nothing into the saved tree.
- Qualified L1 consumption: none. The qualified L1 delivery root
  (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) is empty
  (re-checked this round) and KN1DPy's strict D1 qualification has been
  withdrawn. Every comparison is bounded historical development evidence,
  not qualified-L1 provenance, and does not become expert approval.

## Inventory (all rows candidate-ready)

| Saved callable | Disposition | Proposed SciRel identity | Material differences | Evidence (collect-verified at freeze) |
| --- | --- | --- | --- | --- |
| `evaluate_lyman_alpha` (anchor `lyman_alpha.py:42-64`) | add new capability (task graph) | scirel.diagnostics.hydrogen-jh-lyman-alpha-emission | **composition, no repair** — photon rate `A_Lyman[0] * (r02 + r12 * n0 / saha1) * saha2` and emissivity with the frozen `13.6057 * (0.25 - 1/9)` eV factor, composed from the bound r57/r56 assets in the saved operation order; the saved Lyman energy factor is preserved and recorded as an open expert question | direct tests + 3 replay tests |
| `evaluate_balmer_alpha` (anchor `balmer_alpha.py:40-64`) | add new capability (task graph) | scirel.diagnostics.hydrogen-jh-balmer-alpha-emission | **composition, no repair** — level-3 channels and `A_Balmer[0]` in the saved operation order and frozen factors | direct tests + 3 replay tests |
| `invert_balmer_alpha_to_ground_state` (anchor `N0_from_balmer_alpha.py:12-70`) | add new capability (task graph) | scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion | **composition, no repair** — six-field inversion over r03/r13/s/alpha and Saha 1/3 with the saved operation order; the s/alpha density-semantics split carries into the returned source terms | direct tests + 3 replay tests |
| `produce_jh_coefficient_payload` (anchor `create_jh_bscoef.py:11-248`) | **deferred** (unchanged from r57) | none | materializes packaged coefficient data; admitting the data as a SciRel artifact is the still-open r57 expert decision | — |

Relations kept distinct and not merged: Lyman and Balmer are separate line
relations with different channels (levels 2 and 3) and Einstein vectors; the
inversion is the diagnostic inverse of the Balmer relation with four bound
dependencies and six returned fields. Merging the forward lines would hide
the per-line channel/Einstein binding; merging the inversion into the forward
emission would hide the observed-data input contract.

**Two pre-review corrections (read-only review, this round, before freeze).**
The first draft of this batch (1) validated only the payload fields each
branch consumes and (2) rejected nonpositive photon rates. Both diverged from
the saved contract and are fixed: the graphs now enforce the saved exact
eight-field payload contract (`scirel._validation.validate_jh_payload`,
messages identical to the saved `_validate_payload`, including fields the
branch does not numerically consume), and the forward output gate is
finiteness-only per source parity — `A[0] = 0` returns zero rates (no
emission), a negative `A[0]` returns negative values, both pinned bit-for-bit
on both replay arms. No pre-existing numerical assertion was weakened; the
corrected assertions are new in this batch.

## Declared domain narrowing and scientific differences

- The composed domain is the intersection of the bound assets' contracts:
  density and temperature in `(0, 1e32)` (the bound r56 Saha asset's
  documented limit; the saved radiation callable admits any positive finite
  values), `n0` in `(0, 1e32)` (the saved contract itself). Above `1e32` the
  graphs fail closed where the saved arm returns a value — declared, and
  witnessed by a dedicated replay test on each forward arm.
- The saved Lyman emissivity energy factor (n=3 -> 2 energy applied to the
  Lyman line) is preserved without repair and recorded as a new open expert
  question.
- The r57 open questions (r/alpha density sentinel overwrite, label-vs-degree,
  two payload forms, coefficient data artifact admission, Saha domain
  boundary) carry over unchanged; this batch resolves the Saha-boundary
  composition concern by declaring the intersection domain explicitly.

## Files

- `proposal/hydrogen_jh_lyman_alpha_emission.py`,
  `hydrogen_jh_balmer_alpha_emission.py`,
  `hydrogen_jh_balmer_alpha_ground_state_inversion.py`
- `proposal/test_graph_hydrogen_jh_lyman_alpha_emission.py` and `_l1.py`,
  likewise for the two sibling graphs
- `proposal/scirel.diagnostics.hydrogen-jh-lyman-alpha-emission.json`,
  `proposal/scirel.diagnostics.hydrogen-jh-balmer-alpha-emission.json`,
  `proposal/scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion.json`
  exact documents
- one supporting shared helper integrated under
  `src/scirel/_validation.py` (`validate_jh_payload`, contract-identical to
  the r57 s-asset copy, which is untouched)

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r59 freeze commit.
