# KN1DPy Maxwellian relative-speed rate average: candidate comparison view

This directory is the isolated review proposal for one incoming operator.
Nothing here is imported by `src/scirel`; the proposed development integration
lives on the branch `codex/kn1dpy-maxwellian-rate-intake` and is described
below. Nothing in this proposal is expert approval, a trusted version, or a
public release.

## Exact comparison inputs

- SciRel Git base: `465cd8a208579e89cc4ebbd583abad2c218673c1` (the r40 frozen
  pending-review state, development version `0.1.0.dev18`, 68 public assets).
- Unpublished candidate-pool snapshot: the locally discovered
  `review_pending` records captured in
  `../../review_candidates/2026-09-24-pdr-wavevector/pool-snapshot.json`
  (snapshot digest `sha256:c383bccc25f297a963cb35ad697ef2f71d0c7ff023f13c7412b76a48da44ca6f`;
  52 exact Pleiades review units plus two additional older snapshots). No new
  local `review_pending` snapshot appeared during this work. The host queue
  has not been queried.
- Incoming source (read only): the saved KN1DPy extraction bundle
  `D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1`
  — 84 operator packages, 21 task-graph packages, frozen Python source
  revision `6926123c671da5e0a6cd7b809c86ec428fc28eef` per the bundle's own
  extraction report. The compared operator package is
  `operators/Maxwellian相对速度速率平均` with source anchor
  `KN1DPy/make_sigmav.py:13-57`; the saved implementation file is pinned by
  SHA-256 `e006a4ddb49f00d732ba03816fec591bca41d518d6d8df71a2b4985edb1aecb6`.

**Qualification status.** The currently qualified L1 delivery root
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`) is empty, and
KN1DPy's strict D1 qualification has been withdrawn — the bundle above sits in
the re-review archive. Every comparison in this proposal is therefore bounded
historical development evidence, not qualified-L1 provenance, and does not
become expert approval of the SciRel relation.

## Inventory and closure

The incoming unit is one operator plus one consumer graph:

| Incoming asset | Kind | Disposition | SciRel identity |
| --- | --- | --- | --- |
| `Maxwellian相对速度速率平均` (`average_cross_section_over_maxwellian`) | operator | add (new capability) | `scirel.collisions.maxwellian-relative-speed-rate-average` |
| `粒子靶Maxwellian速率系数图` | task_graph | subsumed: identity single-node composition of the operator | documented in the exact document's identity/composition contract plus a maintained composition test |

The graph adds no scientific relation beyond the operator: every edge is an
identity pass-through, its `order_policy` is one N1 mesh snapshot consumed
immutably, and its failure policy is the operator's own validation. Publishing
a single-node TaskGraph asset would restate the operator's contract; the
state/order/failure content is instead documented in the exact document and
protected by `test_the_saved_graph_contract_consumes_one_immutable_mesh_snapshot`.

The minimal useful consumer closure is closed at this depth: inside the saved
bundle, the only consumer of the operator is that single-node graph. The
molecular `sigv` rate-table graph composes electron-impact rate leaves, not
this Maxwellian average, so no further reverse dependency is bound.

## Deduplication view

No semantic duplicate, variant, or composition target for this relation exists
in the SciRel baseline or in the unpublished candidate pool:

- `scirel.fusion.bosch-hale-reactivity` is a temperature-only analytic
  reactivity parameterization for fusion reactions — a different model with
  different inputs, not a variant of a mesh-based explicit cross-section
  average.
- `scirel.collisions.relativistic_maxwellian_bessel` and
  `scirel.collisions.momentum_scales` are Bessel-closure evaluations and
  momentum definitions; neither averages a cross section over relative speed.
- The 52 Pleiades units and the two additional snapshots in the pool snapshot
  contain no collision-rate, cross-section, or Maxwellian-averaging asset.

Names were used only to find comparison targets; the dispositions above rest
on the relations' inputs, models, and outputs.

## Proposal contents

- `review.md` — the candidate document and the requested expert decision.
- `proposal/asset-document.json` — the proposed canonical exact document
  (identical to the integrated
  `catalog/examples/scirel.collisions.maxwellian-relative-speed-rate-average.json`).
- `proposal/maxwellian_relative_speed_rate_average.py` and
  `proposal/test_maxwellian_relative_speed_rate_average.py` — copies of the
  integrated implementation and direct tests.
- `proposal/test_maxwellian_relative_speed_rate_average_l1.py` — the
  environment-gated bounded historical replay test.

The development verification evidence (gates, installed-state checks, wheel
and catalog digests) is recorded in
`docs/evaluations/intake-2026-09-25-kn1dpy-maxwellian-rate.md` on the
development branch.
