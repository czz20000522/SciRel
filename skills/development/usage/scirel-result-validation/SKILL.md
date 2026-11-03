---
name: scirel-result-validation
description: Validate a SciRel-backed task result with boundary tests, readback, failure semantics and explicit glue evidence before delivery.
---

# SciRel result validation

Use this skill after an agent has written a task solution and before claiming
that the request is complete. Validate the whole user result, not only a SciRel
call.

1. Run normal, lower-bound and upper-bound cases.
2. Add degenerate, branch, failure and composition cases when the task permits.
3. Test both public SciRel calls and agent-written glue, including units,
   shapes, ordering, conversions and formatting.
4. Read output files and stderr back after execution. Preserve typed failures
   and declared non-convergence; do not replace them with fabricated success.
5. Record the generated entrypoint, selected asset IDs, API trace, test matrix,
   outputs, failures and uncovered relations.
6. Compare against supplied benchmark material only after the clean run; the
   benchmark is not a user input or a discovery oracle.

A parseable output proves only that an output path was reached. Completion
requires the stated boundary matrix, readback and failure behavior. A missing
public capability is a task-level gap for external use and a maintenance
intake finding for internal use; it is not silently converted into a SciRel
claim.
