# VEQpy C++ LM branch boundary (2026-09-30)

Status: `T-EQ-SOLVE` remains open. This is a read-only source-first branch
audit, not a comparison receipt, a new tolerance, or a D1 freeze. The frozen
source, r13 candidate, probes, and coordination records were not changed.

The frozen C++ runtime's `run_levenberg_marquardt_once` at
`sources/VEQpy/veqpy/kernels/cxx_kernel/core/kernel_runtime.h:641-667`
always encodes `x0` by `x_scale` into `z`, runs
`nonlinear::LevenbergMarquardt` on `ScaledResidualProblem`, and decodes `z`
when filling `SolveResult`. The source C++ LM context in
`core/nonlinear.h:931-1131` selects standard CMINPACK or in-tree LM, with
Jacobian or finite-difference callbacks according to the functor. The
`SolveResult` definition at `core/kernel_topology.h:212-254` includes the
physical `x`, raw and scaled residual vectors, alpha, norms, solver status,
evaluation counters, acceptance metadata, and other diagnostic fields.
Source hashes: `kernel_runtime.h`
`cece19bc1cd83170938c80e0c80a19d713a3e17dc276564939160dd00845dfd7`,
`nonlinear.h`
`3ae08852bd54314b1beed096866954c9c83449a0cc7fe48c94c00bbe009603f6`.

The r13 candidate's packed solver at
`candidate_bundle/operators/VEQpy打包非线性求解/scientific_operator.py:549-599`
applies its explicit `x_scale` transform only for SciPy `root(method="hybr")`.
Its LM branch sends `x_initial` directly to SciPy
`least_squares(method="lm")`; it does not reproduce the C++ `z` solve or its
MINPACK-specific status/counter contract. This mirrors the frozen Numba
source's `_optimizer_problem` at `numba_kernel/solver.py:217-228`, which also
transforms only `hybr`, so Numba LM agreement cannot stand in for C++ LM
agreement. Candidate file SHA-256:
`8828986ef82bca933f642e476b5d96ff5abaeab6d76b06af28ed225f752f03b5`.

Earlier bounded source/bundle probes in
`coordination/veqpy-lm-terminal-denominator-20260925.txt`,
`veqpy-lm-full-terminals-bounded-20260925.txt`, and
`veqpy-cxx-public-lm-bounded-20260925.txt` establish executability and some
measured values, but the C++ public holdout-h1 was inadmissible, exploratory
h3 was not independently predeclared, and the graph does not return the full
method-specific `SolveResult`. A successor must separately predeclare an
admissible C++ LM canonical/independent sealed holdout pair, compare every
retained public terminal and failure/status behavior under identical inputs,
and bind the exact bundle digest in strict receipts. Keep the r13 historical
materials and candidate bundle unchanged until the original coordinator's
single-writer successor work.
