"""Standalone bisection of the kinetic quasineutral-potential relation."""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
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
    """Solve ``log(Z*n_i(phi))-log(n_e(phi)) == 0`` by vectorized bisection.

    ``residual`` is a caller-owned source-free evaluator returning a mapping with
    ``logarithmic_charge_residual``. Positive residuals must be on the lower
    potential side of the root. The operator owns bracket expansion and the
    monotone bisection state, not the kinetic or electron relation. Midpoints
    avoid adding large absolute potentials; convergence still requires the
    actual returned potential to meet both original width and residual limits.
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
        return {
            "potential_v": phi_ref,
            "logarithmic_charge_residual": evaluate(phi_ref),
            "iterations": 0,
            "converged": True,
        }

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
        potential = _potential_midpoint(active_lower,active_upper)
        potential_residual = evaluate_active(potential)
        # A strict zero of the supplied residual is an exact root hit, not
        # a tolerance-based convergence shortcut or a stalled interval.
        exact = potential_residual == 0.0
        active_lower = np.where(exact, potential, active_lower)
        active_upper = np.where(exact, potential, active_upper)
        width = active_upper - active_lower
        if (
            np.max(width) <= tolerance
            and np.max(np.abs(potential_residual)) <= residual_tolerance
        ):
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
    return {
        "potential_v": returned_potential,
        "logarithmic_charge_residual": evaluate(returned_potential),
        "iterations": final_iterations,
        "converged": True,
    }


__all__ = ["solve_quasineutral_potential"]
