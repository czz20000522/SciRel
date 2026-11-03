# Scientific correctness review criteria

Apply only the checks relevant to the exact operator or TaskGraph and its stated claims.

## Scientific identity and contract

- The unit is a closed scientific or numerical relation, not an arithmetic primitive, source helper, cache, parser,
  or call-order fragment.
- The relation direction, variables, assumptions, model, geometry, coordinates, normalization, sign, closure,
  boundary, and applicability are explicit.
- Every port states scientific meaning, units/convention, dtype, shape, axes/indexing, ownership, lifecycle,
  mutation/persistence, and failure behavior where applicable.
- The contract is understandable without source filenames, project-specific node names, hidden globals, or
  undocumented caller state.

## Implementation correspondence

- Formulas, coefficients, weights, indices, masks, branches, endpoint rules, state transitions, update order,
  convergence checks, and terminal projection agree with the contract.
- A TaskGraph binds exact scientific nodes and keeps glue limited to declared information-preserving adaptation.
- Returned fields represent the actual terminal state, not stale or pre-update intermediates.
- A claimed correction has an independent basis, predecessor/successor diff, expected source divergence, and
  affected-domain boundary.

## Evidence adequacy

- Contract, analytic/manufactured, residual, invariant/limit, boundary/failure, refinement, differential,
  composition, and reassembly gates are present when their claims require them.
- Oracles do not reuse the same hidden production formula or numerical path.
- Metrics have units or declared normalization, scale-aware tolerances, applicability, and actual observed values.
- Held-out criteria were fixed before output was observed; rejected calibration is retained.
- Source parity is labelled source fidelity. Import, smoke, code similarity, test counts, and one matching output
  are not scientific-correctness evidence.
- Missing or malformed observations fail closed and are not replaced with zeros or inferred values.

## Useful counterexamples

Choose only material probes: dimensional/scaling consistency, sign reversal, axis permutation, duplicate or
non-finite coordinates, endpoint and mask policy, conservation/balance, residual versus update magnitude,
initial-state sensitivity, branch thresholds, non-convergence, and failure propagation. A fixture is useful only
when the plausible wrong implementation changes a directly observed quantity or control witness.

## Finding discipline

Use `Blocker` when the stated claim is false or cannot be reproduced because a material relation, port, state,
boundary, or oracle is absent. Use `Major` for a bounded but consequential defect or unsupported claim. Use `Minor`
for a precise non-material ambiguity that does not change the current result. Do not invent a defect outside the
supplied scope or turn an executable correction into a vague request for later judgment.
