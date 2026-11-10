"""Bisection solver for the quasineutral potential relation."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from scirel._result import Result
from scirel._numerics import _potential_midpoint


ELEMENTARY_CHARGE_C = 1.602176634e-19


def _field(value, shape, name):
    values = np.asarray(value, dtype=float)
    try:
        values = np.broadcast_to(values, shape)
    except ValueError as exc:
        raise ValueError(f"{name} cannot be broadcast to the declared surface shape") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def solve_quasineutral_potential(
    potential_reference_v,
    temperature_parallel_j,
    electron_temperature_j,
    charge_c,
    active,
    residual,
    potential_tolerance_v=1.0e-8,
    quasineutral_tolerance=1.0e-10,
    max_iterations=100,
    initial_bracket_thermal=8.0,
):
    """Solve a vectorized logarithmic quasineutral potential relation.

    Parameters
    ----------
    potential_reference_v : real array-like
        Reference potential, also returned on inactive surfaces. [V] Shape:
        scalar or array broadcast with both temperatures and ``active``.
        Every converted value must be finite.
    temperature_parallel_j : real array-like
        Ion parallel thermal-energy scale used in the initial bracket. [J]
        Shape: scalar or array in the common broadcast shape. Values must be
        finite and strictly positive.
    electron_temperature_j : real array-like
        Electron thermal-energy scale used in the initial bracket. [J] Shape:
        scalar or array in the common broadcast shape. Values must be finite
        and strictly positive.
    charge_c : real scalar
        Positive ion charge used to convert ion thermal energy to volts. [C]
        Shape: scalar. Must convert to a finite positive float.
    active : array-like
        Mask selecting surfaces requiring a root. [dimensionless] Shape:
        scalar or array in the common broadcast shape. Values are converted to
        booleans; inactive positions are fixed at their reference potentials.
    residual : callable
        Caller-owned evaluator accepting a potential field and returning a
        mapping with ``logarithmic_charge_residual``. [input V; output dimensionless]
        Shape: callable result scalar or array broadcastable to the common
        surface shape. Positive residuals must lie on the lower-potential side
        of the desired root.
    potential_tolerance_v : real scalar, optional
        Maximum active bracket width at convergence. [V] Shape: scalar.
        Default: 1e-8. Must be finite and strictly positive.
    quasineutral_tolerance : real scalar, optional
        Maximum absolute active logarithmic residual at convergence.
        [dimensionless] Shape: scalar. Default: 1e-10. Must be finite and
        strictly positive.
    max_iterations : int, optional
        Maximum vectorized midpoint evaluations after bracket expansion.
        [iterations] Shape: scalar. Default: 100. Must be an integer of at
        least two; booleans and floats are rejected.
    initial_bracket_thermal : real scalar, optional
        Initial half-width as a multiple of the combined ion and electron
        thermal voltages. [dimensionless] Shape: scalar. Default: 8.0. Must be
        finite and strictly positive.

    Returns
    -------
    potential_v : numpy.ndarray
        Converged active potentials and unchanged reference potentials on
        inactive surfaces. [V] Shape: common broadcast shape, including scalar
        shape ``()``.
    logarithmic_charge_residual : numpy.ndarray
        Callback residual evaluated at the complete returned potential field.
        [dimensionless] Shape: common broadcast shape.
    iterations : int
        Shared number of vectorized midpoint evaluations. [iterations] Shape:
        scalar.
    converged : bool
        Whether all active positions met both stopping conditions or no
        positions were active. [dimensionless] Shape: scalar.

    Raises
    ------
    ValueError
        If potentials or temperatures are nonfinite, temperatures or charge
        are nonpositive, solver controls are invalid, ``max_iterations`` is
        not an integer of at least two, or the callback result lacks a finite
        broadcastable ``logarithmic_charge_residual``.
    FloatingPointError
        If a thermal bracket or midpoint evaluation produces a nonfinite
        potential or residual.
    TypeError
        If the callback is not callable or numeric conversion receives an
        unsupported kind.
    RuntimeError
        If endpoint expansion cannot bracket every active surface or the
        bisection does not meet both width and residual tolerances within
        ``max_iterations``.

    See Also
    --------
    scirel.mirror.solve_mirror_quasineutral_closure : Mirror closure that supplies the residual callback.

    Notes
    -----
    The target equation is ``log(Z*n_i(phi)) - log(n_e(phi)) = 0``, but the
    solver sees only the caller's logarithmic residual. It initializes the
    bracket with ``temperature_parallel_j/charge_c +
    electron_temperature_j/e``, expands each active side for at most eight
    rounds, and then uses vectorized midpoint bisection. Success requires both
    the original potential-width and residual tolerances on every active
    surface. Midpoints avoid adding large absolute potentials; inactive
    surfaces are held at their reference values during active evaluations.
    No kinetic or electron closure is inferred by this operator.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.closures import solve_quasineutral_potential
    >>> e=1.602176634e-19
    >>> def residual(phi):
    ...     return {'logarithmic_charge_residual': 0.5-np.asarray(phi)}
    >>> r=solve_quasineutral_potential([0.0,17.0],0.1*e,0.1*e,e,[True,False],residual)
    >>> np.testing.assert_allclose(r['potential_v'],[0.5,17.0],atol=1e-8)
    >>> assert abs(r['logarithmic_charge_residual'][0])<=1e-10
    >>> np.testing.assert_allclose(r['logarithmic_charge_residual'][1],-16.5)
    >>> assert r['converged'] and 1<=r['iterations']<=100
    """
    phi_ref, t_parallel, t_e, active = np.broadcast_arrays(
        np.asarray(potential_reference_v, dtype=float),
        np.asarray(temperature_parallel_j, dtype=float),
        np.asarray(electron_temperature_j, dtype=float),
        np.asarray(active, dtype=bool),
    )
    phi_ref = phi_ref.copy()
    t_parallel = t_parallel.copy()
    t_e = t_e.copy()
    active = active.copy()
    if not all(np.all(np.isfinite(value)) for value in (phi_ref, t_parallel, t_e)):
        raise ValueError("potential and temperatures must be finite")
    if np.any(t_parallel <= 0.0) or np.any(t_e <= 0.0):
        raise ValueError("temperatures must be positive")
    charge = float(charge_c)
    if not np.isfinite(charge) or charge <= 0.0:
        raise ValueError("charge_c must be finite and positive")
    tolerance = float(potential_tolerance_v)
    residual_tolerance = float(quasineutral_tolerance)
    if isinstance(max_iterations, (bool, np.bool_)) or not isinstance(
        max_iterations, (int, np.integer)
    ):
        raise ValueError("max_iterations must be an integer")
    iterations_limit = int(max_iterations)
    bracket_thermal = float(initial_bracket_thermal)
    if (
        not np.isfinite(tolerance)
        or not np.isfinite(residual_tolerance)
        or not np.isfinite(bracket_thermal)
        or tolerance <= 0.0
        or residual_tolerance <= 0.0
        or bracket_thermal <= 0.0
    ):
        raise ValueError("invalid quasineutral solver controls")
    if iterations_limit < 2:
        raise ValueError("max_iterations must be at least 2 for bisection")

    def evaluate(value):
        result = residual(value)
        if not isinstance(result, Mapping) or "logarithmic_charge_residual" not in result:
            raise ValueError("residual must return logarithmic_charge_residual")
        return _field(
            result["logarithmic_charge_residual"],
            phi_ref.shape,
            "logarithmic_charge_residual",
        )

    thermal_voltage = t_parallel / charge + t_e / ELEMENTARY_CHARGE_C
    lower = phi_ref - bracket_thermal * thermal_voltage
    upper = phi_ref + bracket_thermal * thermal_voltage
    if not np.any(active):
        return Result(
            {
                "potential_v": phi_ref,
                "logarithmic_charge_residual": evaluate(phi_ref),
                "iterations": 0,
                "converged": True,
            }
        )

    active_indices = np.flatnonzero(active.reshape(-1))
    active_lower = lower.reshape(-1)[active_indices].copy()
    active_upper = upper.reshape(-1)[active_indices].copy()

    def evaluate_active(value):
        full = phi_ref.reshape(-1).copy()
        full[active_indices] = value
        return evaluate(full.reshape(phi_ref.shape)).reshape(-1)[active_indices]

    active_lower_residual = evaluate_active(active_lower)
    active_upper_residual = evaluate_active(active_upper)
    for _ in range(8):
        missing_lower = active_lower_residual < 0.0
        missing_upper = active_upper_residual > 0.0
        if not np.any(missing_lower | missing_upper):
            break
        span = active_upper - active_lower
        active_lower = np.where(missing_lower, active_lower - span, active_lower)
        active_upper = np.where(missing_upper, active_upper + span, active_upper)
        active_lower_residual = evaluate_active(active_lower)
        active_upper_residual = evaluate_active(active_upper)
    if np.any((active_lower_residual < 0.0) | (active_upper_residual > 0.0)):
        raise RuntimeError("failed to bracket ambipolar potential")

    final_potential = None
    final_iterations = 0
    for iterations in range(1, iterations_limit + 1):
        potential = _potential_midpoint(active_lower, active_upper)
        potential_residual = evaluate_active(potential)
        # A strict zero of the supplied residual is an exact root hit, not
        # a tolerance-based convergence shortcut or a stalled interval.
        exact = potential_residual == 0.0
        active_lower = np.where(exact, potential, active_lower)
        active_upper = np.where(exact, potential, active_upper)
        width = active_upper - active_lower
        if np.max(width) <= tolerance and np.max(np.abs(potential_residual)) <= residual_tolerance:
            final_potential = potential
            final_iterations = iterations
            break
        positive = potential_residual > 0.0
        active_lower = np.where(positive, potential, active_lower)
        active_upper = np.where(~positive, potential, active_upper)

    if final_potential is None:
        raise RuntimeError("ambipolar potential solve did not converge")

    returned_potential = phi_ref.reshape(-1).copy()
    returned_potential[active_indices] = final_potential
    returned_potential = returned_potential.reshape(phi_ref.shape)
    return Result(
        {
            "potential_v": returned_potential,
            "logarithmic_charge_residual": evaluate(returned_potential),
            "iterations": final_iterations,
            "converged": True,
        }
    )


__all__ = ["solve_quasineutral_potential"]
