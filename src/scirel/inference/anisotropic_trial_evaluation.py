"""Dimension-preserving evaluation through caller-owned scientific ports."""

from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import numpy as np
from scirel.diagnostics.observation_residuals import _observation_layout


def _size(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError("residual_size must be a positive integer")
    return int(value)


def _residual_record(reduced, size):
    if not isinstance(reduced, Mapping):
        raise ValueError("residual_reducer must return a mapping")
    vector = np.asarray(reduced.get("residual_vector"), dtype=float)
    if vector.shape != (size,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"residual vector must be finite with fixed shape ({size},)")
    with np.errstate(over="ignore", invalid="ignore"):
        norm = float(vector @ vector)
    chi2 = float(reduced.get("chi2", np.nan))
    if (
        not np.isfinite(norm)
        or not np.isfinite(chi2)
        or chi2 < 0
        or not np.isclose(chi2, norm, rtol=1e-12, atol=0.0)
    ):
        raise ValueError("chi2 must be finite and equal the squared residual norm")
    return vector.copy(), norm


def evaluate_anisotropic_trial(
    *,
    params,
    observations,
    solver_config,
    equilibrium_solver,
    diagnostic_evaluator,
    residual_reducer,
    residual_size=None,
    failure_penalty=1.0e12,
):
    """Evaluate one anisotropic inversion trial at a fixed residual size.

    Parameters
    ----------
    params : mapping
        Complete parameter mapping for one trial [per parameter contract]. A
        deep copy is placed in the payload passed to ``equilibrium_solver``.
    observations : mapping
        Requested observations and uncertainty metadata [per channel
        contract]. When ``residual_size`` is None, this must use the standard
        ``flux_loops``/``thomson`` layout; the total requested element count is
        the fixed residual size N.
    solver_config : mapping
        Forward configuration [mixed physical units]. It must contain
        ``r_grid`` and ``z_grid``. The mapping is deep-copied and its
        ``params`` member is replaced in the copy before the forward call.
    equilibrium_solver : callable
        Forward port ``equilibrium_solver(payload) -> mapping`` [per forward
        contract]. The returned mapping must contain a Boolean ``converged``;
        ``False`` short-circuits diagnostics. A valid converged mapping must
        not carry a truthy ``failure_reason``.
    diagnostic_evaluator : callable
        Diagnostic port ``diagnostic_evaluator(payload) -> mapping`` [same as
        observations]. It is called only after forward convergence and
        receives deep copies of ``equilibrium``, ``R``, ``Z`` and
        ``observations``.
    residual_reducer : callable
        Reduction port ``residual_reducer(*, predicted, observations) ->
        mapping`` [dimensionless]. It must return ``residual_vector`` with
        shape ``(N,)`` and a matching finite ``chi2``.
    residual_size : int or None, optional
        Predetermined residual count [count]. The default is None, which
        derives N from the standard observation layout before any scientific
        call. A custom layout must supply a positive integer explicitly.
    failure_penalty : float, optional
        Positive per-component value used for a nonconverged forward state or
        a captured numerical failure [dimensionless]. The default is 1e12;
        N times its square must remain finite.

    Returns
    -------
    params : dict
        Deep copy of the submitted parameter mapping [per parameter contract].
    chi2 : float
        Recomputed squared norm of a successful residual vector, or
        ``N * failure_penalty**2`` for a failed trial [dimensionless].
    residuals : ndarray of float64, shape (N,)
        Successful normalized residuals or the same-size penalty vector
        [dimensionless].
    equilibrium : mapping or None
        Forward state obtained so far [mixed]. A failed forward state may be
        retained for diagnosis but is not a valid physical solution.
    failure_reason : str or None
        Forward-nonconvergence or numerical-failure explanation [identifier].
        It is None only when all trial contracts pass.
    valid : bool
        Whether the forward state and residual contract both pass [boolean].
    status : str
        One of ``valid``, ``forward_nonconvergence`` or
        ``numerical_failure`` [identifier].
    failed_port : str or None
        Name of the port where a recorded failure occurred [identifier].
    exception_type : str or None
        Class name of a recorded numerical exception, or None for
        nonconvergence without an exception [identifier].

    Raises
    ------
    ValueError
        If a structural input, port, dimension, penalty or returned residual
        record is invalid, or a numeric conversion raises ``ValueError``. A
        converged forward state carrying a ``failure_reason`` is also rejected.
    TypeError
        If a numeric conversion or nested port raises ``TypeError``.
    KeyError
        If a nested port contract raises or propagates a missing-key error.
    ArithmeticError, FloatingPointError
        Nested arithmetic errors from a scientific port are recorded as
        ``numerical_failure``. An arithmetic error raised outside the protected
        port calls propagates.
    RuntimeError
        A nested RuntimeError from a scientific port is recorded as
        ``numerical_failure``. One raised outside the protected calls
        propagates.

    See Also
    --------
    optimize_anisotropic_parameters : Consume fixed-size trial records in a
        bounded local optimizer.
    scirel.diagnostics.reduce_observation_residuals : Standard reducer for the
        supported observation layout.

    Notes
    -----
    The residual size is fixed before the scientific calls. The function
    deep-copies the caller mappings and arrays, so mutation by a port does not
    alter its inputs. A false ``converged`` flag returns a penalty vector
    without calling diagnostics. Only ``ArithmeticError`` and ``RuntimeError``
    from the protected port calls become failure records; validation,
    programming and contract errors are not converted to physical
    infeasibility. The penalty is an optimizer-interface value, not an
    observation or a feasible solution.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.inference import evaluate_anisotropic_trial
    >>> from scirel.diagnostics import reduce_observation_residuals
    >>> calls=[]
    >>> r=evaluate_anisotropic_trial(params={'p':1.}, observations={'flux_loops':{'values':[1.,2.]}}, solver_config={'r_grid':[0.],'z_grid':[0.]}, equilibrium_solver=lambda _: {'converged':False,'failure_reason':'iteration limit'}, diagnostic_evaluator=lambda _:calls.append('unexpected'), residual_reducer=reduce_observation_residuals)
    >>> assert not calls and not r['valid']
    >>> np.testing.assert_array_equal(r['residuals'],[1e12,1e12])
    >>> assert r['chi2']==2e24 and r['status']=='forward_nonconvergence'
    """
    if not all(isinstance(x, Mapping) for x in (params, observations, solver_config)):
        raise ValueError("params, observations and solver_config must be mappings")
    if not all(callable(x) for x in (equilibrium_solver, diagnostic_evaluator, residual_reducer)):
        raise ValueError("scientific ports must be callable")
    if not {"r_grid", "z_grid"} <= set(solver_config):
        raise ValueError("solver_config must supply r_grid and z_grid")
    n = (
        sum(values.size for _, _, values, _, _ in _observation_layout(observations))
        if residual_size is None
        else _size(residual_size)
    )
    penalty = float(failure_penalty)
    if not np.isfinite(penalty) or penalty <= 0 or not np.isfinite(penalty * penalty * n):
        raise ValueError("failure_penalty must be positive with a finite squared N-vector norm")
    equilibrium = None
    port = "equilibrium_solver"

    def failed(kind, reason, error_type=None):
        residuals = np.full(n, penalty, dtype=float)
        return {
            "params": deepcopy(dict(params)),
            "residuals": residuals,
            "chi2": float(residuals @ residuals),
            "equilibrium": equilibrium,
            "failure_reason": str(reason),
            "valid": False,
            "status": kind,
            "failed_port": port,
            "exception_type": error_type,
        }

    try:
        payload = deepcopy(dict(solver_config))
        payload["params"] = deepcopy(dict(params))
        equilibrium = equilibrium_solver(payload)
        if not isinstance(equilibrium, Mapping) or not isinstance(
            equilibrium.get("converged"), (bool, np.bool_)
        ):
            raise ValueError("equilibrium_solver must return a mapping with boolean converged")
        if not equilibrium["converged"]:
            return failed(
                "forward_nonconvergence",
                equilibrium.get("failure_reason") or "equilibrium solver did not converge",
            )
        if equilibrium.get("failure_reason"):
            raise ValueError("converged equilibrium must not carry a failure_reason")
        port = "diagnostic_evaluator"
        predicted = diagnostic_evaluator(
            {
                "equilibrium": deepcopy(equilibrium),
                "R": deepcopy(solver_config["r_grid"]),
                "Z": deepcopy(solver_config["z_grid"]),
                "observations": deepcopy(observations),
            }
        )
        port = "residual_reducer"
        reduced = residual_reducer(predicted=predicted, observations=deepcopy(observations))
        residuals, chi2 = _residual_record(reduced, n)
    except (ArithmeticError, RuntimeError) as exc:
        return failed("numerical_failure", exc, type(exc).__name__)
    return {
        "params": deepcopy(dict(params)),
        "chi2": chi2,
        "residuals": residuals,
        "equilibrium": equilibrium,
        "failure_reason": None,
        "valid": True,
        "status": "valid",
        "failed_port": None,
        "exception_type": None,
    }


__all__ = ["evaluate_anisotropic_trial"]
