---
name: scirel-solving
description: Answer a scientific or physics question for a user — clarify it, design the physical method, confirm it, compute and check the result, and deliver a short paper-style report with figures — using SciRel capabilities where they help and ordinary code (NumPy, SciPy) elsewhere.
---

# Solve a scientific question with SciRel

The goal is a correct answer to the user's question that a physicist who does not read code can follow and check. SciRel is a set of tested scientific operators that can save work; it is not the subject of the report. NumPy, SciPy and your own code are normal for any step SciRel does not cover.

## The five stages

Every task goes through the same stages, whatever plan or task template the host platform uses. Details, outputs and branches are in [workflow](references/workflow.md).

1. **Clarify.** Restate the question, reuse facts already given, and ask only about choices that change the numbers. See [clarification](references/clarification.md).
2. **Design the physical method.** Before any code, write the physics: what decides the answer, the model and assumptions, the laws and formulas, the route to the requested quantities, and how you will know the result is right. See [physical method](references/method-design.md).
3. **Confirm.** Show the user the assumptions and method and wait, unless they already confirmed it or asked you to skip this step. In a one-shot task (no questions possible, or the task says clarification and confirmation are done) skip the asking but still write `request.md` and `method.md`, with a confirmation-status paragraph in `method.md` that separates task-given facts from unconfirmed assumptions; no separate plan file is needed. See [workflow](references/workflow.md).
4. **Compute and check.** Look up a SciRel capability only where it saves work (see the `scirel-capability-discovery` skill), read its full contract, write the rest as ordinary code, and run checks that could catch a plausible wrong answer. See [result checks](references/result-checks.md) and [supplementary calculations](references/glue-gap.md).
5. **Report.** Write a short technical report in seven sections — answer, problem and understanding, physical model and method, results with figures, discussion, conclusion, appendix. See [report format](references/report-format.md) and the [worked example](references/example-report.md).

## Rules that hold on every platform

- **A physical-method section exists before computing.** If the host's plan template has no place for it, add one. Data definitions, constraints and deliverable lists are not a method.
- **Report confirmation truthfully.** Write "the user confirmed X" only if the user said so in this conversation. Facts fixed in advance by the task statement are written as "given in the task". Assumptions you could not confirm are labelled unconfirmed.
- **Deliver what was asked.** The seven-section report is the main deliverable. A host platform's own summary, brief or interactive visualisation is optional and never replaces it. Do not add deliverables the user did not request.
- **Checks must be independent and discriminate.** The expected value must come from a separate route: an analytic limit, an independent method or a conservation law. A relation that holds by definition, such as a magnitude computed from its own components, is not a check. Symmetry and finiteness alone are not enough, and the number of checks is not a goal. Fix tolerances before looking at results. If a check fails and the tolerance's basis turns out to be wrong, that is a wrong check: re-derive the tolerance from the error estimate alone, rerun and record why; never widen it just to pass.
- **Do not judge acceptability without the user's criterion.** Describe the effect in physical terms and say how the user can compare it with their own requirement.
- **Resolve failures first.** When a check fails, find out why. If the physics result is wrong, fix the calculation and rerun. If the check is wrong (its reference formula, tolerance basis or comparison direction), fix the check, rerun, and say in the appendix in a sentence or two what changed. Only a failure that stays unresolved after that is reported as a failure. A check known to be wrong is never kept as a failure, and never reaches the answer or conclusion. Do not widen a tolerance just to pass. The latest run is the result.
- **Explain the dominant mechanism.** The discussion names the physics that decides the result and tests the attribution with comparison runs that change one factor at a time, giving each factor's rough contribution. Watch for reversed cause and effect.
- **Keep the answer clean.** The answer section states the result and only the limits that would change the conclusion. Process and check records belong in the appendix.
- **Figures show physics, and you look at them.** Plot physical quantities only, never code flow or tool use. Choose axis ranges that make the key difference visible. Open each figure after generating it (pixel statistics do not count) and check for overlaps, legends covering data, and ranges.

## Using SciRel

- Discover capabilities with the `scirel-capability-discovery` skill. Take the identity values from `describe` and use them consistently for the whole task. If an integrity or identity check fails, stop relying on that package and say so.
- Install the wheel named by `describe` from the package's `wheel/` directory, in an environment that meets `runtime.requires_python`, and call the public Python API.
- In the report, mention an operator in one short clause where a step uses it. Do not add operator lists or mapping tables.
- Multi-step couplings: see [coupled dependencies](references/graph-model.md).

## Tools in this skill

- `scripts/validate_report.py REPORT.md` checks report structure (section order, figures and captions, no implementation detail in the method, significant digits). It does not check physics.
- `scripts/delivery.py` is an optional helper that turns saved CSV tables into bounded numerical statements and plots and replays them; see [delivery helper](references/delivery-tool.md).

Use only the inputs the user supplied and the public package. The host platform controls permissions; this skill grants none.
