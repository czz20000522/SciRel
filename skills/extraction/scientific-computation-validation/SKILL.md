---
name: scientific-computation-validation
description: Use when designing, executing, or assessing claim-specific scientific and numerical tests for an exact scientific relation, operator, TaskGraph, solver, diagnostic, or functional composition. Returns bounded evidence, not stage completion, repair, approval, or release authority.
---

# Scientific Computation Validation

## Purpose and authority

Establish what an exact scientific computation is proved to do. Given a frozen target and explicit claim scope,
design independent tests, execute them in the authorized runtime when possible, and report actual observations,
evidence strength, and claim limits.

This skill does not choose extraction boundaries, repair implementations, normalize candidates, approve assets,
or decide whether any production stage is complete. Its `pass`, `fail`, and `blocked` results apply only to named
claim gates for the exact tested version.

Use `scientific-runtime-dataset-construction` when required source/runtime observations do not exist. That
helper owns capture placement, coverage, split integrity, and custody; validation owns oracle independence,
metrics, tolerances, execution interpretation, and the strongest earned claim.

Validation proves a named claim for an exact revision. It does not choose an extraction boundary,
normalize a package, approve an asset, or write plugin lifecycle state. When its result crosses an
owner boundary, return the exact evidence and limitation to the caller; the receiving SciRel workflow performs
its own candidate or release transition. If a validator and skill disagree, record a `tooling_defect` observation and
preserve the scientific result.

## Required invocation

Require:

- exact target and dependency digests;
- the public scientific/port contract and applicability;
- named claims to assess and explicit exclusions;
- available evidence and source/reference identities;
- authorized runtime/profile and output locations; and
- whether the request is test design, execution, or evidence assessment.

A contract need not be a Markdown page: read exact code/YAML/docstring anchors and supplement only necessary
physical facts that cannot be recovered reliably. Preserve prior-stage deliveries read-only; new results belong
to the current derived candidate/evidence. For an attributable result with a defective assertion, path or packaging
binding, preserve the original observation and repair the affected checker/binding. Rerun its cheap comparison,
not unchanged science; never relax tolerances or fabricate old identity/independence.

Never substitute a mutable `latest` target, infer an omitted scientific equation from candidate output, or expand
the claim beyond the caller's scope.

## Keep five questions separate

1. **Source behavior fidelity:** does the target reproduce a declared source behavior or fixture?
2. **Scientific relation correctness:** is the stated equation, convention, closure, or physical limit correct?
3. **Numerical correctness:** does the discrete method solve or approximate that relation with its declared
   boundaries, stability, convergence, and failure semantics?
4. **Composition correctness:** do ports preserve units, axes, state ownership, order, failure, and reproducibility?
5. **Functional reassembly:** for declared inputs and branches, does a source-free composition reproduce the
   complete terminal scientific output/state contract?

Source parity answers only question 1. Functional reassembly answers question 5 only for its declared domain.
Import, compile, smoke, code similarity, test count, or two implementations sharing the same hidden formula are
not independent scientific evidence.

## Workflow

1. **Freeze the testable claim.** List the governing relation, inputs/outputs, units, coordinate/index
   conventions, assumptions, closures, boundaries, numerical method, lifecycle/update order, failure semantics,
   and observable. Classify each required fact as `given`, `derived`, `assumed`, or `missing`.
2. **Select evidence by claim.** Read
   [the validation catalog](references/validation-catalog.md). Account for each applicable category and record a
   scientific reason for `inapplicable`. Use `blocked` when a required oracle fact is missing.
3. **Pre-register the gate.** Before reading held-out candidate output, freeze the claim, oracle derivation,
   fixture identity, observable, units, normalization/scale, metric, tolerance or expected order, applicability,
   runtime, and exact target version. Derive thresholds from precision, conditioning, discretization, analytic
   limits, or an independent calibration case; never loosen them after seeing the result.
4. **Check oracle independence.** The production derivative, interpolation, quadrature, residual assembly, update
   path, or TaskGraph cannot be its own oracle. Shared declared constants and raw input data are allowed; shared
   hidden numerical transformations are not. A source fixture supports source fidelity only.
5. **Execute in the authorized environment.** Verify runtime/profile identity before candidate import. Run
   source-free targets without undeclared source mounts or network. Record the actual command, runtime,
   environment-relevant versions, complete observed schema, and numerical metrics. A proposed test is not an
   executed result.
6. **Fail closed on observations.** Missing fields are not numeric zero. Reject malformed shape, dtype, units,
   selectors, masks, lifecycle fields, or contradictory nullable/status contracts before numerical comparison.
   Preserve an execution failure as evidence instead of aborting without a receipt.
7. **Interpret the named gate.** Report `pass`, `fail`, `inapplicable`, or `blocked`, the actual metric against its
   pre-registered criterion, oracle independence, and the strongest supported claim. Keep rejected calibrations
   and disagreements in the evidence record.

For stochastic relations, pre-register the seed/reproducibility or statistical claim, sample design, statistic,
confidence/error bound, and scheduling assumptions. A single sequence cannot establish a distributional claim.

## Relation-specific rules

- Direct/analytic relations: check dimensions, hand-computable cases, limits, symmetry, signs, and material
  boundaries.
- Discrete operators: use manufactured functions or independently assembled residuals and applicable refinement,
  conservation, stability, monotonicity, conditioning, endpoint, and failure checks.
- Iterative or implicit mappings: distinguish update magnitude from governing residual and final-state error.
  Independently witness at least one material state transition or terminal residual.
- TaskGraphs: verify exact node versions, port handoffs, units/axes, order, branch, state ownership, feedback,
  convergence/non-convergence, failure propagation, and complete terminal fields. Validate leaf science at its
  operator boundary.
- Functional reassembly: use identical explicit inputs, one canonical case and an unseen sealed holdout, semantic
  completion markers, complete terminal schema, exact discrete comparisons, pre-registered scale-aware floating
  metrics, and material branch/lifecycle coverage.

For a target that intentionally corrects a source defect, compare the corrected domain with the independently
specified corrected relation and keep source divergence explicit. Validate unaffected source-fidelity domains
separately. This skill reports the evidence; it does not authorize or implement the correction.

## High-consequence compositions

For a coupled closure, nonlinear/implicit solver, material TaskGraph, or whole-program composition, keep gate
design, output-blind gate review, and fresh execution independent when resources allow:

1. the designer freezes claims, formulas, fixtures, metrics, and thresholds without candidate results;
2. the reviewer checks completeness, independence, dimensional scales, lifecycle, failures, and artifact
   producibility for the exact register digest; and
3. the executor runs only an approved immutable register and cannot change gates after seeing output.

If independent workers are unavailable, perform the same sequence serially with sealed artifacts and do not expose
candidate results to later gate design. Missing specification remains `validation_oracle_gap`; worker count never
changes the evidence standard.

## Output

Read [the evidence record](references/evidence-record.md) before writing results. For each gate record the exact
target, claim, oracle, fixtures, applicability, runtime, metric/criterion, observation, result, and limitation.
Summarize only the strongest claims supported by all required gates. Do not infer repair success, stage completion,
workflow state, approval, normalization, packaging, release, or production readiness.
