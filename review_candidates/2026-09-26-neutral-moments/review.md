# Candidate: KN1DPy neutral-moment diagnostics family (eleven operators)

Status: development candidate prepared for expert review, to be frozen as the
pending_unapproved r60 successor of r59. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `39416f5` (r59, JH hydrogen radiation diagnostics family,
  99 assets dev31, `pending_unapproved`).
- Unpublished candidate pool: the 52-asset Pleiades development sample and
  the two additional snapshots, unchanged; re-checked by relation (not by
  name) for neutral moment reductions, thermal-speed scales, boundary-flux
  normalizations, collision-frequency assemblies, or scattered-source
  aggregations — none exists in the pool. All eleven incoming leaves are
  therefore **new capabilities**; no reuse, variant, duplicate or merge
  disposition applies.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  eleven operator packages, each implementation pinned by SHA-256 (listed
  per exact document). Every import of the saved tree was read-only
  (`python -B`, `PYTHONDONTWRITEBYTECODE=1`); zero writes.
- Qualified L1 consumption: none. The qualified L1 delivery root
  (`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) is empty
  (re-checked this round) and KN1DPy's strict D1 qualification has been
  withdrawn. All comparison is bounded historical development evidence.

## Inventory (all rows candidate-ready)

| Saved callable | Disposition | Proposed SciRel identity | Material differences | Evidence (collect-verified) |
| --- | --- | --- | --- | --- |
| `compute_thermal_speed_m_s` (`kinetic_h2.py:1360-1371`) | add new capability | scirel.kinetic.thermal-speed-scale | **no repair** — frozen constants, scalar fail-closed contract reproduced bit for bit | direct + replay |
| `reduce_generation_density` (`kinetic_h.py:1410-1424`, `kinetic_h2.py:1548-1573`) | add new capability | scirel.kinetic.generation-density-reduction | **no repair** — both saved weight paths (full 2-D and 1-D radial projection) and the uniform-column routing identity reproduced | direct + replay |
| `reduce_axisymmetric_neutral_distribution` (`kinetic_h.py:1443-1605`, `kinetic_h2.py:1612-1801`) | add new capability | scirel.kinetic.axisymmetric-neutral-moments | **two declared tightenings** (see below) plus preserved sigma_zz=sigma_yy identification and both empty-slice policies | direct + replay |
| `sum_elastic_frequency_channels` (`kinetic_h.py:1297-1317`, `kinetic_h2.py:1258-1297`) | add new capability | scirel.kinetic.elastic-frequency-channels | **one declared narrowing**: overflow of the channel sum fail-closes instead of returning inf | direct + replay |
| `normalize_incoming_neutral_boundary` (`kinetic_h.py:600-616`, `kinetic_h2.py:715-731`) | add new capability | scirel.kinetic.incoming-boundary-flux-normalization | **no repair** — positive-half scaling, abs(target) scale, zero negative half reproduced | direct + replay |
| `normalize_spatial_source_shape` (`kn1d.py:520-577`) | add new capability | scirel.kinetic.spatial-source-shape-normalization | **no repair** — trapezoidal measure, unit-integral re-check (rtol 1e-12) reproduced | direct + replay |
| `assemble_neutral_total_collision_frequency` (`kinetic_h.py:1089-1095`, `kinetic_h2.py:1151-1157`) | add new capability | scirel.kinetic.neutral-total-collision-frequency | **no repair** — wall-loss broadcast, zero-diameter semantics, enabled-CX fail-closed rule reproduced | direct + replay |
| `reduce_atomic_scattered_sources` (`kinetic_h.py:1297-1317`) | add new capability | scirel.kinetic.atomic-scattered-sources-reduction | **no repair** — signed-value preservation witnessed | direct + replay |
| `reduce_molecular_scattered_sources` (`kinetic_h2.py:1422-1546`) | add new capability | scirel.kinetic.molecular-scattered-sources-reduction | **no repair** — separate asset from the atomic sibling because the wall channel exists only on the molecular side | direct + replay |
| `aggregate_elastic_regeneration_source` (`kinetic_h.py:1340-1398`, `kinetic_h2.py:1468-1538`) | add new capability | scirel.kinetic.elastic-regeneration-aggregation | **no repair** — exact key-set matching and dict-iteration summation order preserved | direct + replay |
| `assemble_simple_charge_exchange_source` (`kinetic_h.py:1297-1317`, `kinetic_h2.py:1444-1461`) | add new capability | scirel.kinetic.simple-charge-exchange-source | **no repair** — cell-local rate contraction with the saved operation order | direct + replay |

Relations kept distinct and not merged: the atomic two-channel and molecular
three-channel source reductions differ in the saved wall channel; the
frequency assembly consumes aggregated channels rather than producing them;
the moment reduction and the density reduction answer different questions
(full moment set vs per-generation density).

## Declared tightenings (pre-review, two rounds; source arm preserved as evidence)

1. **Non-finite velocity axes** — the saved arm accepts a NaN axis and
   propagates NaN into the flow-speed/temperature moments; this integration
   fail-closes (pre-review round 1).
2. **Overflowing channel sum** — the saved arm returns inf for three 1e308
   finite channels; this integration fail-closes (round 1).
3. **Non-finite normalization temperature, mass, or volume** — the saved
   arm accepts each and propagates NaN (also under `source_default`); this
   integration fail-closes (round 2).
4. **Non-finite outputs** — a final finiteness gate on all nine returned
   moment fields (round 2).

Each case: the saved behavior is recorded in the module docstring and the
exact document's assumptions, and a regression test pins the fail-closed
result. No saved numerical assertion was weakened; nothing was silently
repaired.

## Preserved saved behaviors raised for expert review

- `sigma_zz = sigma_yy`: the saved cylindrical identification is returned
  as an independent copy. Whether an independent zz stress is intended is
  an open question.
- `empty_slice_policy="source_default"`: zero-density slices report flow
  0 m/s and temperature 1 eV (saved initial-iteration semantics), retained
  for callers that need it; the default policy is `reject`.
- Wall loss at zero pipe diameter contributes zero (the saved arithmetic),
  not an infinite-pipe limit.

## Files

- Eleven `proposal/<module>.py` integration modules
- Five `proposal/test_*.py` contract/replay test files
- Eleven `proposal/scirel.kinetic.*.json` exact documents
- One shared pattern: environment-gated replay pins each saved
  implementation by SHA-256 via `SCIREL_KN1DPY_REVIEW_ROOT`

## Public API and dependency impact

Eleven new public callables in `scirel.kinetic` and the root namespace;
eleven new exact documents (kind `operator`); version
`0.1.0.dev31` -> `0.1.0.dev32`; catalog 99 -> 110 assets. The other 99
exact documents change only in the mechanical `implementation_version`
bump. No existing test assertions weakened.
