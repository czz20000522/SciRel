---
name: scientific-computation-validation
description: Design, execute, or assess claim-specific scientific and numerical tests for an exact relation, operator, TaskGraph, solver, diagnostic, or composition; return bounded evidence only.
---

# Scientific computation validation

Use the shared operating contract already loaded for this task mode. If it is
not loaded, read [the shared operating contract](../references/scirel-development-core.md)
once before proceeding; do not reload it for each routed sub-skill.
This skill proves named claims for one exact target. It does not choose extraction boundaries, implement repairs,
normalize candidates, approve assets, write stage state or release a package.

## Trigger and required input

Use this skill when a caller names a claim and asks for test design, execution or evidence assessment. Require
exact target/dependency digests, public scientific/port contract and applicability, claims plus exclusions, source
or independent reference identity, authorized runtime/profile and output path. If source/runtime observations are
missing, route to [runtime dataset construction](../scientific-runtime-dataset-construction/SKILL.md); do not infer
an oracle from candidate output.

Choose one claim mode:

- `source_fidelity`: compare source output/state/failure for D1; source defects remain source issues.
- `scientific_correctness`: test an independently stated equation, convention, limit or physical closure.
- `numerical_correctness`: test discretization, conditioning, stability, convergence and declared failures.
- `composition`: test units, axes, state ownership, order, branches, exceptions and reproducibility.
- `functional_reassembly`: test complete terminal output/state for declared source-free cases.

Source parity answers only `source_fidelity`; imports, compile, similarity and test count are not independent
scientific evidence.

## Bounded workflow

1. Freeze target, inputs, denominator, applicability and tolerances. Keep original grids, threshold neighbors,
   boundaries, failure rows and `atol=0`/other explicit criteria.
2. Build an independent oracle or reference and name its provenance. Separate source-runtime, wheel-runtime,
   development and reference dependencies; a missing tool is a runtime gap, not a numerical pass.
3. Cover the target and affected capability closure named by the claim, then spend deeper cases on algorithmic
   risk, coupled state/iteration, conditioning and boundary sensitivity. Cover every retained core capability only
   when the claim explicitly concerns a complete project or full source reassembly. Use a separate holdout only when
   the selected claim requires it.
4. Execute in the authorized environment, verify runtime identity before import, and keep source-free runs free of
   undeclared source mounts/network. Record command, case counts, observations and exact failures.
5. Interpret only the selected claim. Rerun changed behavior and affected reverse dependencies; do not relax a
   tolerance or silently switch model/asset. Preserve `failed`, `blocked`, `NOT_RUN` and inapplicable rows.

Return exact observations, metric/criterion, evidence hashes, claim ceiling, untested scope and reopen condition.
`pass` applies only to the named gate; it never advances D0-D3, approval or release. If a validator disagrees with
this method, record `tooling_defect` while preserving the scientific result.

Load [the validation catalog](references/validation-catalog.md) for category-specific cases and
[the evidence record](references/evidence-record.md) for receipt fields; do not read both unless required.
