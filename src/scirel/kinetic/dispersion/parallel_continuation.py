"""Fail-closed seeded continuation for the parallel electromagnetic dispersion root."""

from __future__ import annotations

import numpy as np
from scipy.optimize import root

from scirel.kinetic.dispersion._fluid_parallel import (
    ContinuationFailure,
    _positive_finite_tolerance,
    em1d_parallel_residual,
)


def _continue_em1d(
    state, *, pm=1, k_grid=None, initial_guess=None, residual_tolerance=1e-10, solver_options=None
):
    """Corrected stopping protocol: finite solver-success AND scaled residual required.

    Source defaults/grid/initial seed retained; no failed root becomes next seed.
    Stops with attempted value/flags/residual and complete accepted prefix. No
    interpolation, alternate-root rescue or solver-convergence fiction in glue.
    """
    residual_tolerance = _positive_finite_tolerance(residual_tolerance, "residual_tolerance")
    if k_grid is not None:
        supplied = np.asarray(k_grid)
        if (
            supplied.dtype.kind not in "iuf"
            or not supplied.size
            or (not np.isfinite(supplied).all())
            or np.any(supplied == 0)
        ):
            raise ValueError("finite real nonzero continuation grid required; both signs supported")
    k = (
        np.arange(1, 51) * 0.01 / float(np.asarray(state["cwp"]).item())
        if k_grid is None
        else np.asarray(k_grid, dtype=float).reshape(-1)
    )
    seed = (
        complex((0.05 + 0.04j) * float(np.asarray(state["wcs1"]).item()))
        if initial_guess is None
        else complex(initial_guess)
    )
    solver = root
    accepted = []
    records = []
    for point in k:

        def fun(v):
            (f, scale) = em1d_parallel_residual(state, complex(*v), point, pm=pm)
            return np.array([f.real / scale, f.imag / scale])

        try:
            result = solver(
                fun, [seed.real, seed.imag], method="hybr", options=solver_options or {}
            )
        except Exception as cause:
            raise ContinuationFailure(
                dict(
                    k=float(point),
                    guess=seed,
                    accepted_prefix=tuple(accepted),
                    evaluation_error=repr(cause),
                )
            ) from cause
        attempted = complex(*result.x)
        (f, scale) = em1d_parallel_residual(state, attempted, point, pm=pm)
        record = dict(
            k=float(point),
            guess=seed,
            attempted=attempted,
            solver_success=bool(result.success),
            solver_status=int(result.status),
            scaled_residual=abs(f) / scale,
            accepted_prefix=tuple(accepted),
        )
        if (
            not result.success
            or not np.isfinite(attempted)
            or (not np.isfinite(f))
            or (abs(f) / scale > residual_tolerance)
        ):
            raise ContinuationFailure(record)
        accepted.append(attempted)
        records.append(record)
        seed = attempted
    return dict(k=k, omega=np.asarray(accepted), records=records)


def continue_em1d(inputs):
    """Continue a seeded parallel root across a k grid under the fail-closed policy."""

    return _continue_em1d(**inputs)
