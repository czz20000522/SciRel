# Candidate: KN1DPy convergence/accumulation family (four operators)

Status: development candidate prepared for expert review, to be frozen as
the pending_unapproved r64 successor of r63. Nothing here is expert
approval, a trusted version, or a public release.

## Base and comparison scope

- SciRel base: `f79bc4d` (r63, transport-step family, 116 assets dev37,
  `pending_unapproved`).
- Unpublished candidate pool: re-checked by relation for convergence
  stopping criteria, generation accumulation state updates, or outer-loop
  convergence evaluations — none exists. All four incoming leaves are
  **new capabilities**.
- Incoming source (read only): the saved KN1DPy bundle
  `D1待重审历史产物/KN1DPy-631d0bf1` (provisional; strict D1 withdrawn),
  four operator packages, each implementation pinned by SHA-256.
- Qualified L1 consumption: none (delivery root empty; strict D1
  withdrawn). Bounded historical development evidence only.

## Inventory (all rows candidate-ready)

| Saved callable | Disposition | Proposed SciRel identity | Material differences | Evidence (shared) |
| --- | --- | --- | --- | --- |
| `evaluate_neutral_generation_stopping` (anchor `kinetic_h.py:1278-1305`) | add new capability | scirel.kinetic.neutral-generation-stopping | **no repair** — Delta_n = max(gen)/max(acc), truncate and seed_relative paths reproduced bit for bit; returns a 3-tuple (delta, done, reason) | shared: 9 direct + 5 replay |
| `update_neutral_generation_accumulation` (anchor `kinetic_h.py:1240-1276`) | add new capability | scirel.kinetic.generation-accumulation-update | **no repair** — first call creates state from None, second call accumulates; signed distribution cells preserved per source contract; density stays nonnegative | shared |
| `evaluate_neutral_outer_seed_convergence` (anchor `kinetic_h.py:1090-1115`) | add new capability | scirel.kinetic.outer-seed-convergence | **no repair** — seed_error = max(abs(diff))/max(curr), reentry threshold = 10*truncate; returns a mapping with seed_error, reentry_threshold, should_reiterate, reason | shared |
| `evaluate_kn1d_outer_convergence` (anchor `kn1d.py:493-511`) | add new capability | scirel.kinetic.kn1d-outer-convergence | **no repair** — top-level kn1d outer-pass convergence; reentry threshold = truncate (not 10*); returns a mapping with the same four fields | shared |

Relations kept distinct and not merged: stopping evaluates per-generation
density ratio; accumulation maintains the running state; outer-seed and
top-level convergence differ in their reentry thresholds (10*truncate vs
truncate). Merging them would hide the source's two-level convergence
structure.

## Test delta (collect-verified, pwsh 7)

- `test_convergence_accumulation.py`: 9 direct tests
- `test_convergence_accumulation_l1.py`: 5 environment-gated replay tests
  (including discriminating regression for ratio-of-max vs per-node
  formula and first-call/second-call accumulation accumulation)
- Total 14 new tests.

## Files

- `proposal/neutral_generation_stopping.py`,
  `proposal/generation_accumulation_update.py`,
  `proposal/outer_seed_convergence.py`,
  `proposal/kn1d_outer_convergence.py`
- `proposal/test_convergence_accumulation.py`,
  `proposal/test_convergence_accumulation_l1.py`
- 4 `proposal/scirel.kinetic.*.json` exact documents

## Version and impact

Version `0.1.0.dev37` -> `0.1.0.dev38`; catalog 116 -> 120 exact
documents. The other 116 documents change only in their mechanical
`implementation_version` bump.
