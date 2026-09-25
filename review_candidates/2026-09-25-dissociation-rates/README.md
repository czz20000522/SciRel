# Candidate: KN1DPy dissociation-rate family (nine assets)

Status: development candidate prepared for expert review, frozen as the
pending_unapproved r54 successor of r53. Nothing here is expert approval, a
trusted version, or a public release.

## Base and comparison scope

- SciRel base: `e3f2ebe559e57e35eff2e23170211377db24b0a8` (r53,
  `review-2026-09-25-r53-elastic-cross-sections`, 81 assets dev26,
  `pending_unapproved`).
- Unpublished candidate pool: the 52-asset Pleiades development sample and the
  two additional snapshots, unchanged; none contains a dissociation-rate
  asset (re-checked by relation, not by name).
- Incoming source: the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn).

## Inventory (all rows candidate-ready)

All nine leaves share one relation shape — a temperature-only nine-coefficient
logarithmic polynomial in log(T), evaluated in the saved source's Horner
order, clipped to [0.1, 2.01e4] eV, scaled by 1e-6 to m^3/s — and differ only
in species/channel and frozen coefficients. Test counts below are
`pytest --collect-only` verified: 6 direct + 3 replay per asset, 81 total.

| Saved package | Channel | Proposed SciRel identity | Saved impl SHA-256 |
| --- | --- | --- | --- |
| 分子氢电子碰撞解离H1sH1s速率 | H2 + e -> H(1s) + H(1s) + e | scirel.collisions.h2-dissociation-h1s-h1s-rate-coefficient | 87965fad…d0ec |
| 分子氢电子碰撞解离H1sH2s速率 | H2 + e -> H(1s) + H(2s) + e | scirel.collisions.h2-dissociation-h1s-h2s-rate-coefficient | 432a3141…85ca |
| 分子氢电子碰撞解离H1sHn3速率 | H2 + e -> H(1s) + H(n=3) + e | scirel.collisions.h2-dissociation-h1s-hn3-rate-coefficient | 6f2b0000…b115 |
| 分子氢电子碰撞解离H2pH2s速率 | H2 + e -> H2+ + H(2s) channel | scirel.collisions.h2-dissociation-h2p-h2s-rate-coefficient | b7e8903c…e0c0 |
| 分子氢电子碰撞解离pH1s速率 | H2 + e -> H+ + H(1s) + 2e channel | scirel.collisions.h2-dissociation-p-h1s-rate-coefficient | 78cd4d21…bdca |
| 分子氢离子双质子解离速率 | H2+ + e -> p + p channel | scirel.collisions.h2-plus-two-proton-dissociation-rate-coefficient | c559efd7…af61 |
| 分子氢离子pH1s解离速率 | H2+ + e -> H+ + H(1s) + e | scirel.collisions.h2-plus-p-h1s-dissociation-rate-coefficient | 384e60d9…2124 |
| 分子氢离子pHn2解离速率 | H2+ + e -> H+ + H(n=2) + e | scirel.collisions.h2-plus-p-hn2-dissociation-rate-coefficient | bbea8bbd…37c |
| 分子氢离子H1sHn解离复合速率 | H2+ + e -> H(1s) + H(n) dissociative recombination | scirel.collisions.h2-plus-h1s-hn-dissociative-recombination-rate-coefficient | e7304b94…44ef |

Dispositions: nine **new capabilities** as sibling identities — none derives
from another, and each channel is a physically distinct rate. The one
documented repair (shared by all nine, declared by each saved document and
unchecked by every saved implementation): a nonpositive temperature is
rejected instead of being silently clipped into the fit domain. The Horner
arithmetic, clipping and 1e-6 scaling are preserved bit for bit. No reuse,
variant, duplicate or merge applies.

## Generation provenance

The nine successor modules, test files and exact documents were generated
from shared templates (included in `proposal/`) with the coefficient tables
extracted from the pinned saved implementations via `repr(float(v))`
round-trip, eliminating the transcription-error class caught in r49's COLLRAD
table. The four generator scripts are part of the proposal for auditability;
their templates embed the per-channel anchors and the single inserted check.

## Files

- `proposal/<module>.py`, `proposal/test_<module>.py`,
  `proposal/test_<module>_l1.py` for the nine modules
- nine `proposal/scirel.collisions.*.json` exact documents
- four generator scripts

The proposal copies are byte-identical to the integrated files under `src/`,
`tests/` and `catalog/examples/` in the r54 freeze commit.
