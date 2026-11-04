# Scientific Validation Catalog

## Evidence order

Use all applicable gates. A later row does not replace an earlier one.

| Gate | Proves | Typical metric |
| --- | --- | --- |
| Contract | units, axes, signs, domains, state ownership | explicit assertion / rejection |
| Analytic or manufactured | relation evaluation on known input | `max_abs`, `max_rel` |
| Residual | output satisfies an independently assembled equation | norm / normalized residual |
| Limit or invariant | physical/numerical property | conservation, symmetry, bounds |
| Refinement | discrete consistency | observed order / error ratio |
| Differential | agreement with independent code, source, or asset | deltas and norm |
| External reference | real-system or standard-case fidelity | declared observable delta |
| Functional reassembly | identical explicit source/bundle inputs reach complete terminal outputs | schema equality plus exact/discrete and scale-aware field deltas |

Source parity is a differential gate for source behavior fidelity, not scientific truth.

## Test selection by mapping

| Mapping type | Minimum applicable gates |
| --- | --- |
| Algebraic physical transform | units/signs, analytic values, symmetry or limit |
| Derivative, interpolation, quadrature | manufactured function, endpoint/knot rule, refinement |
| Linear matrix/RHS or implicit solve | independently assembled residual, boundary rows, singular/failure case |
| Explicit or implicit time advance | conservation/balance ledger, positivity/bounds, time-step refinement |
| Nonlinear/iterative solver | fixed-point or governing residual, convergence and non-convergence semantics, initial-state sensitivity |
| Random/stochastic operator | declared RNG/seed reproducibility, independent moment/statistical bound |
| Diagnostic/moment reduction | independent quadrature or moment calculation, symmetry and zero/constant cases |
| Lookup/table/coefficient mapping | provenance, index/unit/boundary checks, continuity/monotonicity when claimed |
| Task graph | node-port contract, state/branch/order tests, whole-graph balance or residual; validate leaf science through its operators |
| Whole source-program reassembly | canonical plus sealed holdout, semantic completion, complete output/state schema, lifecycle/branch coverage, source-free execution |

## Required category accounting

For every implemented or changed scientific relation, account for all of these categories:

1. contract, units, axes, signs, input domain, and state ownership/lifecycle;
2. analytic or manufactured values when constructible;
3. independently assembled governing residual or balance when the relation is solved rather than directly evaluated;
4. physical/numerical limits, invariants, conservation, symmetry, positivity, monotonicity, or bounds as applicable;
5. material endpoint, zero, singular/near-singular, invalid-input, and failure behavior;
6. grid/time-step/quadrature/iteration refinement and observed convergence when a discrete approximation is claimed;
7. independent differential comparison with source, another released asset, independent implementation, or external reference when available;
8. functional reassembly when the relation participates in a declared runnable source path.

Run every applicable category. Record `inapplicable` with a scientific reason rather than silently
omitting it; record `blocked` when required evidence is missing. A blocked required category
prevents the corresponding correctness claim.

## Independence rules

- A production finite-difference routine cannot be the residual oracle for its own derivative.
- A task graph cannot be the independent oracle for an operator it calls.
- A second implementation may share constants and declared input data, but not the same hidden
  numerical transformation being tested.
- A source fixture proves only that the asset agrees with the captured source case.
- A paper curve without its input state is evidence of trend only, not a numerical oracle.

## Scale-aware differential acceptance

Pre-register a differential gate in the units and magnitude regime of its declared output. A single
global `max_abs` threshold is valid only when the contract bounds the compared field scale in those
same units. For floating fields whose source magnitude can vary by configuration, lifecycle, or
component, gate the declared active extent with finite-mask/shape equality and a scale-aware metric
(for example relative L2, relative infinity norm, or a documented componentwise reference scale).
Report raw `max_abs` for diagnosis; do not turn it into an acceptance gate unless its scale or ULP
budget is explicitly stated.

Freeze the metric, reference scale, and threshold before revealing holdout output. If a holdout
reveals that the pre-registered metric is dimensionally or scale-wise invalid, record that case as
rejected calibration evidence rather than retroactively loosening the gate. Generate a new unseen
holdout after registering the corrected scale-aware criterion. Exact integer/discrete contracts
remain exact; this rule does not license tolerance relaxation for selectors, indices, masks, or
branch outcomes.

## Boundary and defect rules

- Include endpoint, zero, symmetry, singular/near-singular, invalid-shape, and failure tests only
  when they are material to the declared mapping.
- Require a separate corrected-path test when a source crash, undefined branch, or known defect
  is repaired.
- Keep legacy compatibility and corrected-science results in separate test names and evidence rows.
