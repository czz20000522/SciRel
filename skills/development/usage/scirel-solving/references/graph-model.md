# Explain coupled dependencies

Use a diagram when several physical steps or feedback would otherwise be hard to follow. A single call with one output usually needs no diagram.

Keep two views of one computation:

| view | useful content |
| --- | --- |
| user plan | supplied quantities, physical subproblems, outputs, unresolved decisions and checks, with units |
| execution evidence | selected capabilities, supplementary calculations, actual calls, data and diagnostics |

The user plan explains the result in physical language. Keep it small enough to read; expand a subproblem when needed. Internal IDs, code paths and package bookkeeping belong in execution evidence unless requested.

For each composed connection, establish compatible units, normalization, axes, shape, sign/index convention, state, model and boundary. A conversion or missing transformation becomes an explicit [supplementary calculation](glue-gap.md). An unresolved edge stays unknown or `NOT_RUN`.

For feedback, identify the iterated state, update rule, stopping criterion and convergence diagnostic. A converged iteration still needs an appropriate scientific check.

A plan is a working explanation, not an additional schema or deliverable. Keep only steps that support the requested result and its checks. The [FRC example](example-frc-flame.md) shows a physical outline.
