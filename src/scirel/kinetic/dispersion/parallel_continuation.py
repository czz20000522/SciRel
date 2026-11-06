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
    r"""Continue a single causal kinetic root through an explicit grid with accepted-seed feedback and diagnostic failure records. Failed or false-success roots never propagate.

    Parameters
    ----------
    state : mapping[str,numeric array or scalar]
        Explicit initialized isotropic drifting-Maxwellian kinetic state. [wps2 s^-2; vds,vtzs m/s; wcs
        rad/s; c2 m^2/s^2] Shape: mapping with matching nonempty (S,) vectors. wps2 nonnegative; vtzs
        positive; finite c2. Optional Tzs,Tps must be equal and alphas must be one. Continuation defaults
        additionally require cwp[m], wcs1[rad/s].
    pm : int
        Circular-polarization sign about the fixed positive z basis. [dimensionless] Shape: scalar. Default:
        1. Exactly +1 or -1. This is not helicity defined along k and is not swapped when k changes sign.
    k_grid : float64 array or None
        Ordered signed real wavevector grid. [m^-1] Shape: (K,) or null. Default: None. Finite nonzero
        points; explicit arrays are flattened. None uses 0.01*arange(1,51)/state[cwp]. The default source
        grid is best-effort; explicit arrays are flattened and both signs are supported.
    initial_guess : complex128 or None
        First complex temporal frequency seed. [rad/s] Shape: scalar or null. Default: None. Finite; None
        uses the source best-effort seed (0.05+0.04j)*state[wcs1]. Callers claiming a branch should supply
        an explicit seed.
    residual_tolerance : float64
        Required scaled dispersion residual for every accepted point. [dimensionless] Shape: scalar.
        Default: 1e-10. Finite positive; default 1e-10.
    solver_options : dict or None
        Options passed to the fixed SciPy hybr solver. [option-specific] Shape: mapping or null. Default:
        None. No fallback solver or silent rescue. maxfev may set the finite evaluation budget.

    Returns
    -------
    result : dict[str,array or list[dict]]
        Accepted continuation mapping with k, omega and per-point solver records. [k m^-1; omega rad/s;
        residual dimensionless] Shape: k,omega:(K,); records:length K. Only successful finite roots passing
        abs(f)/scale <= residual_tolerance are returned; order follows the supplied grid.

    Raises
    ------
    ValueError
        For invalid inputs or a missing required mapping key.
    ContinuationFailure
        When a point is not accepted as a converged root. The exception carries attempted k, seed,
        solver success/status, scaled residual and the accepted prefix; no partial result is returned
        as a successful complete continuation.

    See Also
    --------
    scirel.kinetic.dispersion.parallel.em1d_parallel_residual : Related contract dependency.

    Notes
    -----
    At each k, solve the two real components of f/scale with scipy.optimize.root(method=hybr). Accept
    only solver.success, finite output and the declared residual bound. Only an accepted root becomes
    the next initial guess. Arbitrary-species drifting isotropic Maxwellian parallel electromagnetic
    response. Assumptions: The Gaussian velocity integral gives |k|*vt in both causal denominators,
    retaining signed k*vd. No anisotropic or loss-cone substitution is made. Kinetic constants are
    caller-owned initialized state: c2, wps2, wcs and vtzs are consumed without conversion; vtzs uses
    sqrt(2*kB*T/m). No fluid epsilon0/gamma/deck profile is substituted. The source current
    initialization uses c2=(2.9979e8)^2, epsilon0=8.8542e-12, kB=1.3807e-23, charge-unit=1.6022e-19 C,
    mass-unit=1.6726e-27 kg, eV-to-J=1.6022e-19; these define a possible predecessor, not new fixed
    constants in this residual.

    References
    ----------
    Xie and Xiao, PDRK: A General Kinetic Dispersion Relation Solver for Magnetized Plasma, Plasma Science and Technology 18 (2016).

    Examples
    --------
    >>> from scirel.kinetic.dispersion.parallel import continue_em1d
    >>> s = dict(wps2=[0.0], vds=[0.0], vtzs=[1.0], wcs=[0.0], c2=1.0)
    >>> r = continue_em1d(dict(state=s, k_grid=[0.2, 0.21], initial_guess=0.2+0j))
    >>> assert len(r["omega"]) == 2
    """

    return _continue_em1d(**inputs)
