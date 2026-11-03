"""Pressure-only equilibrium feedback with explicit terminal diagnostics.

The solver is deliberately a discrete Green-map iteration.  It owns the
pressure spline, cell-current assembly, relaxation, and finite-state checks;
it does not claim a continuum force-balance solution.
"""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Callable

import numpy as np

from ._pressure_current import (
    current_target,
    fit_pressure_spline,
    pressure_derivative,
    relaxed_green_update,
)

__all__ = ["EquilibriumResult", "compute_equilibrium"]


@dataclass(frozen=True)
class EquilibriumResult:
    """Terminal state and both fixed-point residual histories."""

    psi: np.ndarray
    plas_currents: np.ndarray
    p_psifit: object
    status: str
    iterations: int
    residual: float
    closure_residual: float
    reason: str
    residual_history: tuple = ()
    closure_residual_history: tuple = ()

    def as_tuple(self):
        """Return the historical ``(psi, currents, pressure_fit)`` view."""
        return self.psi, self.plas_currents, self.p_psifit


def _normalized_closure_residual(actual, target):
    """Compute ``||actual-target|| / ||target||`` with common scaling."""
    actual = np.asarray(actual, dtype=float)
    target = np.asarray(target, dtype=float)
    target_peak = float(np.max(np.abs(target)))
    if target_peak == 0.0:
        return 0.0 if np.all(actual == 0.0) else np.inf
    scale = max(target_peak, float(np.max(np.abs(actual))))
    actual_scaled, target_scaled = actual / scale, target / scale
    target_norm = float(np.linalg.norm(target_scaled))
    if target_norm == 0.0:
        return np.inf
    return float(np.linalg.norm(actual_scaled - target_scaled) / target_norm)


def _validate_uniform_grid(R, Z, psi_vac, green):
    """Validate the real, rectangular, uniformly spaced grid contract."""
    if any(np.iscomplexobj(value) for value in (R, Z, psi_vac, green)):
        raise ValueError("R, Z, psi_vac, and g_psi must be real arrays")
    R, Z, psi_vac, green = [np.asarray(value, dtype=float) for value in (R, Z, psi_vac, green)]
    if R.ndim != 2 or Z.shape != R.shape or psi_vac.shape != R.shape:
        raise ValueError("R, Z, and psi_vac must have equal 2-D shapes")
    size = R.size
    if green.shape != (size, size) or not all(
        np.all(np.isfinite(value)) for value in (R, Z, psi_vac, green)
    ):
        raise ValueError("finite Green matrix and grids matching flattened shape required")
    if min(R.shape) < 2:
        raise ValueError("at least a 2x2 rectangular grid is required")
    if not np.array_equal(R, np.broadcast_to(R[0:1, :], R.shape)) or not np.array_equal(
        Z, np.broadcast_to(Z[:, 0:1], Z.shape)
    ):
        raise ValueError("R must be column-consistent and Z row-consistent")
    for axis in (R[0], Z[:, 0]):
        spacing = np.diff(axis)
        if spacing.size == 0 or spacing[0] == 0.0:
            raise ValueError("R and Z spacing must be nonzero")
        scale = max(float(np.max(np.abs(axis))), abs(float(axis[-1] - axis[0])))
        bound = 8.0 * np.finfo(float).eps * scale
        if (
            not np.isfinite(bound)
            or bound >= abs(float(spacing[0])) / 4.0
            or not np.all(spacing * spacing[0] > 0.0)
            or np.any(np.abs(spacing - spacing[0]) > bound)
        ):
            raise ValueError("R and Z axes must be uniformly spaced and resolvable")
    return R, Z, psi_vac, green


def compute_equilibrium(
    R,
    Z,
    Pfunc: Callable[[float], float],
    psi_vac,
    g_psi,
    tol=1e-10,
    maxiter=100,
    relax=0.0,
    plas_clip=None,
    plotit=False,
):
    """Run bounded pressure/current feedback and return its terminal state.

    ``residual`` measures the Green-map flux update.  ``closure_residual``
    measures the pressure-current equation in the terminal spline state.  Both
    must satisfy ``tol`` for a ``converged`` result; ``maxiter=0`` performs no
    update and returns a nonconverged state.
    """
    if plotit:
        raise ValueError("plotting is outside this finite-contract proposal")
    R, Z, psi_vac, g_psi = _validate_uniform_grid(R, Z, psi_vac, g_psi)
    n_points = R.size
    if not callable(Pfunc):
        raise ValueError("Pfunc must be callable")
    if (
        not np.isfinite(tol)
        or tol <= 0.0
        or isinstance(maxiter, (bool, np.bool_))
        or not isinstance(maxiter, Integral)
        or maxiter < 0
    ):
        raise ValueError("tol must be positive finite and maxiter a nonnegative integer")
    if not np.isfinite(relax) or not 0.0 <= relax < 1.0:
        raise ValueError("relax must lie in [0, 1)")
    if plas_clip is not None:
        clip = np.asarray(plas_clip)
        if clip.shape != R.shape or clip.dtype.kind != "b":
            raise ValueError("plas_clip must match grid shape and be boolean")
        clip = clip.ravel()
    else:
        clip = None

    flat_R, flat_Z = R.ravel(), Z.ravel()
    midplane = np.flatnonzero(flat_Z == 0.0)
    if midplane.size < 3:
        raise ValueError("at least three exact midplane points are required")
    midplane = midplane[np.argsort(flat_R[midplane])]
    radii = flat_R[midplane]
    pressure = np.asarray([Pfunc(radius) for radius in radii], dtype=float)
    if not np.all(np.isfinite(pressure)):
        raise ValueError("pressure law must be finite on the midplane")
    zero_edges = np.flatnonzero(pressure == 0.0)
    if zero_edges.size == 0:
        raise ValueError("pressure law must contain an exact zero edge")
    limiter = int(zero_edges[0])

    psi_zero = psi_vac.ravel().copy()
    psi = psi_zero.copy()
    currents = np.zeros(n_points, dtype=float)
    dr = abs(float(R[0, 1] - R[0, 0]))
    dz = abs(float(Z[1, 0] - Z[0, 0]))
    if dr == 0.0 or dz == 0.0:
        raise ValueError("R and Z spacing must be nonzero")

    update_history, closure_history = [], []

    def make_result(pfit, status, iterations, residual, closure, reason):
        return EquilibriumResult(
            psi.reshape(R.shape),
            currents.reshape(R.shape),
            pfit,
            status,
            iterations,
            residual,
            closure,
            reason,
            tuple(update_history),
            tuple(closure_history),
        )

    def fit_state(current_psi):
        samples = current_psi[midplane][: limiter + 1]
        return fit_pressure_spline(samples, pressure[: limiter + 1])

    try:
        fitted = fit_state(psi_zero)
    except (ValueError, ArithmeticError, np.linalg.LinAlgError) as exc:
        return make_result(None, "nonfinite", 0, np.nan, np.nan, str(exc))
    edge = float(psi_zero[midplane][limiter])
    if not np.isfinite(edge) or edge == 0.0:
        return make_result(fitted, "nonfinite", 0, np.nan, np.nan, "zero or nonfinite edge flux")

    def target_current(current_psi, current_fit, edge_flux):
        derivative = pressure_derivative(current_fit, current_psi, edge_flux, clip)
        return current_target(flat_R, derivative, dr, dz)

    residual = closure_residual = np.inf
    for iteration in range(1, int(maxiter) + 1):
        try:
            target = target_current(psi, fitted, edge)
        except FloatingPointError as exc:
            return make_result(fitted, "nonfinite", iteration - 1, np.nan, np.nan, str(exc))
        old_psi, old_currents = psi.copy(), currents.copy()
        try:
            currents, psi = relaxed_green_update(target, currents, relax, g_psi, psi_zero)
        except FloatingPointError as exc:
            psi, currents = old_psi, old_currents
            return make_result(fitted, "nonfinite", iteration, np.nan, np.nan, str(exc))

        try:
            edge = float(psi[midplane][limiter])
            fitted = fit_state(psi)
        except (ValueError, ArithmeticError, np.linalg.LinAlgError) as exc:
            return make_result(None, "nonfinite", iteration, np.nan, np.nan, str(exc))
        if not np.isfinite(edge) or edge == 0.0:
            return make_result(
                fitted, "nonfinite", iteration, np.nan, np.nan, "zero or nonfinite edge flux"
            )
        residual = float(np.linalg.norm(psi - old_psi) / abs(edge))
        if not np.isfinite(residual):
            return make_result(
                fitted, "nonfinite", iteration, residual, np.nan, "nonfinite update residual"
            )
        try:
            target_new = target_current(psi, fitted, edge)
        except FloatingPointError as exc:
            return make_result(fitted, "nonfinite", iteration, residual, np.nan, str(exc))
        closure_residual = _normalized_closure_residual(currents, target_new)
        update_history.append(residual)
        closure_history.append(closure_residual)
        if not np.isfinite(closure_residual):
            return make_result(
                fitted,
                "nonfinite",
                iteration,
                residual,
                closure_residual,
                "nonfinite pressure-current closure residual",
            )
        if residual <= tol and closure_residual <= tol:
            return make_result(
                fitted,
                "converged",
                iteration,
                residual,
                closure_residual,
                "update and pressure-current closure residuals <= tol",
            )
    return make_result(
        fitted, "maxiter", int(maxiter), residual, closure_residual, "iteration bound reached"
    )
