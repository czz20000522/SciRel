---
name: scientific-relation-implementation
description: Use when implementing or changing one scientific or physical relation, numerical model, closure, diagnostic, solver feature, or supplied evidence-bounded scientific asset gap from equations, assumptions, code, or scientific assets.
---

# Scientific Relation Implementation

## Purpose

Turn one declared scientific relation into the smallest executable implementation and make an
honest claim about its correctness. This covers both a new user scientific feature and a concrete
asset gap supplied by extraction or review. It is not a discovery, acceptance-review, or UI/backend
design skill.

Treat an asset bundle, NumPy/SciPy, and the standard library as optional implementation
dependencies. The scientific relation is authoritative; companion validation defines how to produce and bound its
test evidence, while the receiving owner records any durable disposition.

This skill may implement one evidence-bounded relation or controlled repair inside the caller's
authorized project or supplied candidate boundary. It cannot create review, expert-approval, catalog, or
release facts, and it cannot hide an unresolved scientific choice behind generated code. Return any
cross-owner result to the caller as evidence; the receiving owner decides whether and how to admit it.

## Workflow

### 1. Classify the implementation request

Choose one evidence origin before coding:

- `new_relation`: a user or project requests a bounded new scientific capability;
- `asset_completion`: extraction, review, or runtime evidence identifies a concrete missing
  operator, graph edge, state schema, or numerical relation;
- `scientific_correction`: an inspected implementation contradicts a sufficiently determined scientific
  or numerical contract; repair is part of extraction, not deferred automatically to expert review;
- `not_ready`: the requested relation is not yet uniquely specified. For a user project, return the exact
  missing scientific decisions and required evidence to `scientific-project-implementation` so it can
  continue requirement discovery with the user. Return to extraction only when the actual task is
  source-asset candidate discovery; do not turn an underspecified new feature into an extraction task.
  Do not use `not_ready` for a value that can be a callable input, a state derivable from the governing
  relation, or a numerical setting the AI can select and validate.

For `asset_completion`, record the supplied gap basis and preserve its asset boundary. Do not
invent a gap or treat a source-visible implementation as post-extraction glue. A source-observation
dataset may bound the missing relation, but samples alone do not define a unique algorithm. Require
source or equation semantics, and leave unseen replay and claim evaluation to
`scientific-computation-validation`. If the supplied gap is a reproducible source defect, use the
shared controlled-repair protocol and preserve original behavior as evidence, not as an extra usable
asset by default. For scientific defects read [scientific correction](references/scientific-correction.md),
which defines the whole skill group's handoffs, critical diagnosis, verification and page disclosure.
Use the same bounded candidate edit boundary for `scientific_correction` as for `asset_completion`.

### 2. Freeze the scientific claim before coding

State the requested mapping in the project’s own language. Record the inputs, outputs, governing
equations, coordinates, units, sign conventions, domain of validity, closures, initial/boundary
conditions, state initialization/frozen/recomputed lifecycle, update order, numerical tolerances,
and expected observable behavior.

For every mask, selector, piecewise branch, or threshold, define both the active branch and its
complement, including equality at the threshold. Phrases such as "apply inside the mask" do not define
whether outside values are zero, preserved, extrapolated, or invalid. Treat an unspecified complement as
`missing`, not as reversible implementation detail.

Separate facts into `given`, `derived`, `assumed`, and `missing`. Do not silently choose a material
closure, boundary, empirical coefficient, normalization, or physical regime. If a missing fact
prevents a unique scientific relation, stop and request it or narrow the claim.

Do not confuse an unspecified runtime value with an unspecified relation. Geometry arrays, profiles,
boundary values, coefficients, and case controls may remain typed callable inputs. Use dimensionally valid
manufactured values to implement and test the mapping; request the user's concrete values only when running
their concrete case. Once a governing relation is frozen, derive its internal states, algebraic
consequences, diagnostics, residuals, and required input dependencies without sending them back as user
questions.

For `new_relation`, the governing relation must come from explicit user equations, supplied source or
documents, or a traceable authoritative scientific reference. A model name, desired fields, numerical
controls, or permission to choose a minimal model is not equation authority. When proposing a relation
from literature, record the exact equations, signs, reductions, and deviations from the reference and
return only a materially different model choice to `scientific-project-implementation`; derived equations,
interfaces, and numerical consequences do not require separate user confirmation. If the user delegates
model selection, choose the narrowest traceable candidate and keep the claim bounded to it.
`assumed` may hold reversible implementation details; it cannot authorize governing physics, closures,
boundary physics, residual definitions, or nonlinear update equations.

Load `scientific-computation-validation` before preparing or evaluating tests.

### 3. Choose the smallest reliable implementation path

Prefer these implementation sources, adapting the search to the supplied evidence and available environment. Skip unavailable or irrelevant sources; preserve the frozen scientific contract and explain the chosen route:

1. compatible code already in the user project;
2. verified scientific assets that match the required contract;
3. already-installed third-party numerical/scientific libraries;
4. a minimal project-local implementation using the standard library.

Reuse only a component whose units, axes, indexing, boundary semantics, assumptions, and numerical
meaning match the claim. An asset is a library dependency, not a substitute for understanding the
relation. For `new_relation`, do not modify the library bundle. For `asset_completion`, modify
only the supplied candidate package boundary. Do not read source code at runtime to supply omitted
scientific logic.

### 4. Derive the executable algorithm

Translate the continuous relation into an explicit computational contract before implementation:

- analytic versus discrete evaluation;
- grid, quadrature, derivative, interpolation, and coordinate conventions;
- boundary/initial rows and singular or zero-value handling;
- iteration/update order, stopping criterion, and failure behavior;
- expected consistency, stability, and convergence behavior.

This translation is implementation work the AI may perform within the accepted claim. Choose a stable, accurate method and validate it;
do not ask the user to specify quadrature order, derivative stencil, iteration controls, or every boundary
row unless exact compatibility with a named implementation makes that discrete choice part of the claim.

Freeze one numerical producer for every state that feeds later relations. Analytic evaluation, discrete
integration, interpolation, differentiation, and algebraically equivalent update orders are not
interchangeable merely because they represent the same continuous quantity. If the project or source
declares one path, preserve it; qualify a replacement only with a predeclared numerical equivalence claim
and downstream-state validation. An unresolved choice between such paths means `not_ready`.

This preservation rule protects a valid declared numerical contract. It must not force retention of a
demonstrated defect: an explicitly justified `scientific_correction` changes that contract transparently,
documents its effect and uses independent corrected-domain plus downstream-state validation rather
than an equivalence claim to known wrong behavior.

When a legacy path leaves a temporary variable undefined on a singular or zero branch, do not
publish that temporary as an asset result and do not invent a default. Expose an effective output
only when the declared consumer-visible result is uniquely determined by explicit state (for
example, a verified all-zero field remains zero under the unused scale); otherwise fail closed.
Mark this as controlled completion, capture the genuine branch, and require one ordinary source
replay plus the material zero/failure boundary before claiming the narrowed mapping.
For a reproducible shape, index, allocation, or producer/consumer mismatch, recover intent from both
sides, make the smallest axis/index/extent-preserving change, and add
unaffected-domain plus repaired-boundary and sealed-holdout evidence. A `source_repaired` result
does not by itself establish `scientifically_corrected` behavior.

Keep project code organized by its scientific/product role (for example `equilibrium.py`,
`pressure.py`, or `diagnostics.py`). Do not impose `operator`, `task_graph`, or `main.py` names on
the user project. For a first-stage extraction package, do not require a demo, usage entrypoint, invocation
section, or application example. Existing source examples may be used as bound evidence or test vectors.
Record only the current candidate's interface evidence, claim ceiling, and known gaps. Do not make maintained-baseline,
release, asset-site, or harness-task claims from first-stage implementation evidence.

### 5. Bind mandatory independent scientific and numerical validation

Load `scientific-computation-validation` to select independent equation, residual, limit,
invariant, refinement, parity, and external-reference gates. This skill supplies the implemented
relation and its declared numerical contract; the validation skill defines comprehensive test design,
oracle independence, execution evidence, and how to bound the earned scientific claim. The receiving owner decides
whether that evidence supports a durable disposition.

Do not treat implementation as complete until validation has evaluated every catalog evidence
category and run every applicable gate. Require contract/dimensional checks,
analytic/manufactured cases when constructible, independently assembled governing residuals,
material limits/invariants/symmetries, boundary and failure behavior, refinement/convergence for
discrete methods, and an independent differential or external reference when available. Mark a
gate inapplicable only with a scientific reason; source replay or a second call to the production
formula cannot replace independent scientific and numerical evidence.

For every source-like mask, equality, threshold, index rule, or typed scientific handoff, require a
mutation-discriminating witness: identify a plausible wrong predicate, recomputed field, side swap, or
index schedule and choose inputs for which that mutation changes an observed value or direct control-path
witness. A case that executes the line but produces the same post-clipping, integrated, symmetric, or
same-branch result does not validate the claimed rule.

When the changed relation participates in a declared source-program path, rerun the affected canonical
and sealed holdout functional reassembly cases. For a fidelity claim, unexplained terminal-output
divergence is a failure. For an intentional scientific correction, record that divergence and verify
the complete corrected terminal contract independently; matching known wrong output is not acceptance.

### 6. Deliver at the correct boundary

Treat the prior stage's delivery as read-only. Implement changes and annotations in this stage's derived candidate,
linked to that original. Necessary science may be anchored in code, YAML, docstrings or function/module comments;
formal human-facing documents wait until D2 retained code is stable and final review is prepared. Do not generate
a second draft page for facts already recoverable from code.


For `new_relation`, integrate into normal project conventions. For `asset_completion` or
`scientific_correction`, update the
affected operator/task-graph package, its declared ports, tests, and project sidecars without
self-accepting it. In both cases, document assumptions concisely, make caller state explicit, and
hand evidence to `scientific-computation-validation`. Do not claim experimental fidelity,
paper-result parity, expert approval, functional reassembly, or a more complete model than evidence
supports.
