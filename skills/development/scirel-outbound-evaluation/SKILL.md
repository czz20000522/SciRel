---
name: scirel-outbound-evaluation
description: Evaluate how well the delivered SciRel package serves agents, and turn the findings into changes. For SciRel maintainers running blind tests or benchmarks. Not delivered to users.
---

# Evaluate the delivered package

The delivered skills speak to any user's agent and carry no evaluation content. This skill holds what maintainers need to test them.

## Run a clean evaluation

1. Build the package from a clean commit with `scripts/build_pure_delivery.py`.
2. Scan the package for answers before use, including wheel metadata such as the README and project URLs. `tests/tooling/test_solved_examples.py` guards the known cases.
3. Give the agent only the package, the request and its own working directory. Keep reference answers and hidden oracles out of its context, and compare only after the run.
4. Read the report, open the figures, and check the transcript for access outside the allowed paths.

Record each requested case as `ATTEMPTED`, `UNATTEMPTED`, `RUNTIME_GAP`, `CONTRACT_MISMATCH` or `COMPLETED`. An unattempted case is not a capability gap. A parseable output only proves the run reached its output path.

## Internal and external runs

The delivered skills treat every run as a user's task: when no capability applies, the agent writes ordinary tested code and continues.

When the owner is evaluating or extending SciRel, also treat a missing capability, weak discovery or a misleading result as a finding:

- Record it with a [gap card](references/capability-gap-intake.md).
- Keep the affected claim at the capability boundary and route reusable relations to `scirel-integration`.
- Keep task-specific glue out of the library. A glue success does not show that SciRel owns the relation.

## Turning findings into changes

Fix findings in generic form. Delivered skills must not mention the case, its numbers, this process, repository files or catalog sizes, so they need no edit as the catalog grows. `tests/tooling/test_solved_examples.py` checks this.

Rebuild the package after changing a delivered skill.

## References

- [Gap card format](references/capability-gap-intake.md)
- [Handover record for a run](references/outbound-evidence.md)
- [Behavioural scenarios for the solving method](references/acceptance-scenarios.md)
