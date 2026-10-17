"""Bounded equilibrium feedback proposal preserving legacy numerical ingredients.

Derived from frozen Pleiades D0 eq_solve.py compute_equilibrium.
D2 adds a result object and validates terminal states.  It does not
claim physical equilibrium correctness beyond the supplied Green matrix and
pressure law.  The legacy tuple can be recovered with ``result.as_tuple()``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from numbers import Integral

import numpy as np
from ._pressure_current import fit_pressure_spline, pressure_derivative, current_target, relaxed_green_update

__all__ = ["EquilibriumResult", "compute_equilibrium"]


@dataclass(frozen=True)
class EquilibriumResult:
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
        return self.psi, self.plas_currents, self.p_psifit


def _normalized_closure_residual(actual, target):
    """Return ``||actual-target||_2 / ||target||_2`` with safe scaling."""
    actual = np.asarray(actual, dtype=float)
    target = np.asarray(target, dtype=float)
    target_scale = float(np.max(np.abs(target)))
    if target_scale == 0.0:
        return 0.0 if np.all(actual == 0.0) else np.inf
    component_scale = max(target_scale, float(np.max(np.abs(actual))))
    target_scaled = target / component_scale
    actual_scaled = actual / component_scale
    target_norm = float(np.linalg.norm(target_scaled))
    if target_norm == 0.0:
        return np.inf
    return float(np.linalg.norm(actual_scaled - target_scaled) / target_norm)


def compute_equilibrium(
    R, Z, Pfunc: Callable[[float], float], psi_vac, g_psi,
    tol=1e-10, maxiter=100, relax=0.0, plas_clip=None, plotit=False,
):
    """Run bounded feedback and report an explicit terminal state.

    ``residual`` retains the normalized flux-update diagnostic;
    ``closure_residual`` measures the current-pressure equation in the terminal
    spline state. ``converged`` requires both to be at most ``tol``. This is a
    discrete pressure-only feedback solve, not a continuum force-balance test.

    Supported contract: finite, rectangular, uniformly spaced R/Z arrays with a
    nonempty exact midplane row; finite Green matrix matching the flattened grid;
    pressure values containing an exact zero edge; finite positive ``tol`` and
    nonnegative integer ``maxiter``. ``relax`` lies in [0,1), and a supplied
    clip mask is boolean and matches the grid shape. Uniformity permits only
    eight float64 epsilon times axis scale of construction/subtraction error,
    below one quarter of spacing; descending axes remain supported. Plotting is intentionally unsupported in
    this proposal so terminal state is not coupled to a GUI side effect.
    """
    if plotit:
        raise ValueError("plotting is outside this finite-contract proposal")
    raw_arrays = (R, Z, psi_vac, g_psi)
    if any(np.iscomplexobj(a) for a in raw_arrays):
        raise ValueError("R, Z, psi_vac, and g_psi must be real arrays")
    R, Z, psi_vac, g_psi = [np.asarray(a, dtype=float) for a in raw_arrays]
    if R.ndim != 2 or Z.shape != R.shape or psi_vac.shape != R.shape:
        raise ValueError("R, Z, and psi_vac must have equal 2-D shapes")
    n = R.size
    if g_psi.shape != (n, n) or not (np.all(np.isfinite(R)) and np.all(np.isfinite(Z)) and np.all(np.isfinite(psi_vac)) and np.all(np.isfinite(g_psi))):
        raise ValueError("finite Green matrix and grids matching flattened shape required")
    if R.shape[0] < 2 or R.shape[1] < 2:
        raise ValueError("at least a 2x2 rectangular grid is required")
    if not (np.array_equal(R, np.broadcast_to(R[0:1, :], R.shape)) and
            np.array_equal(Z, np.broadcast_to(Z[:, 0:1], Z.shape))):
        raise ValueError("R must be column-consistent and Z row-consistent")
    dr_axis = np.diff(R[0, :])
    dz_axis = np.diff(Z[:, 0])
    if dr_axis.size == 0 or dz_axis.size == 0 or dr_axis[0] == 0 or dz_axis[0] == 0:
        raise ValueError("R and Z spacing must be nonzero")
    # Validate the affine grid up to float64 construction/subtraction error,
    # not NumPy's default allclose tolerance. This accepts decimal linspace
    # grids while rejecting geometry deviations that alter cell-area weights.
    for axis, spacing in ((R[0, :], dr_axis), (Z[:, 0], dz_axis)):
        scale = max(float(np.max(np.abs(axis))), abs(float(axis[-1] - axis[0])))
        bound = 8.0 * np.finfo(float).eps * scale
        if (not np.isfinite(bound) or bound >= abs(float(spacing[0])) / 4.0 or
                not np.all(spacing * spacing[0] > 0.0) or
                np.any(np.abs(spacing - spacing[0]) > bound)):
            raise ValueError("R and Z axes must be uniformly spaced and resolvable")
    if not np.isfinite(tol) or tol <= 0 or isinstance(maxiter, (bool, np.bool_)) or not isinstance(maxiter, Integral) or maxiter < 0:
        raise ValueError("tol must be positive finite and maxiter a nonnegative integer")
    if not np.isfinite(relax) or not 0 <= relax < 1:
        raise ValueError("relax must lie in [0, 1)")
    if plas_clip is not None:
        clip = np.asarray(plas_clip)
        if clip.shape != R.shape or clip.dtype.kind != "b":
            raise ValueError("plas_clip must match grid shape and be boolean")
        clip = clip.ravel()
    z0_idx = np.where(Z.ravel() == 0.0)[0]
    if z0_idx.size < 3:
        raise ValueError("at least three exact midplane points are required")
    r = R.ravel().astype(float)
    z = Z.ravel().astype(float)
    # The pressure edge is the first zero encountered outward in R, not the
    # first zero in storage order. Preserve the declared descending-axis
    # capability without reordering the Green matrix, currents or outputs.
    # Only the physical midplane spline/edge traversal is put in radial order.
    z0_idx = z0_idx[np.argsort(r[z0_idx])]
    r_z0 = r[z0_idx]
    p_z0 = np.asarray([Pfunc(x) for x in r_z0], dtype=float)
    if not np.all(np.isfinite(p_z0)):
        raise ValueError("pressure law must be finite on the midplane")
    zero = np.flatnonzero(p_z0 == 0.0)
    if zero.size == 0:
        raise ValueError("pressure law must contain an exact zero edge")
    lim_idx = int(zero[0])
    psi0 = psi_vac.ravel().astype(float)
    psi = psi0.copy()
    currents = np.zeros(n, dtype=float)
    dr = abs(float(R[0, 1] - R[0, 0]))
    dz = abs(float(Z[1, 0] - Z[0, 0]))
    if dr == 0 or dz == 0:
        raise ValueError("R and Z spacing must be nonzero")

    update_history, closure_history = [], []
    def result(*args):
        return EquilibriumResult(*args, tuple(update_history), tuple(closure_history))

    def fit(psi_mid):
        return fit_pressure_spline(psi_mid[:lim_idx + 1], p_z0[:lim_idx + 1])

    try:
        pfit = fit(psi[z0_idx])
    except Exception as exc:
        return result(psi.reshape(R.shape), currents.reshape(R.shape), None, "nonfinite", 0, np.nan, np.nan, str(exc))
    edge = float(psi[z0_idx][lim_idx])
    if not np.isfinite(edge) or edge == 0:
        return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "nonfinite", 0, np.nan, np.nan, "zero or nonfinite edge flux")

    residual = np.inf
    closure_residual = np.inf
    def closure(fitted_pressure, flux, edge_flux):
        derivative = pressure_derivative(fitted_pressure, flux, edge_flux,
            clip if plas_clip is not None else None)
        return current_target(r, derivative, dr, dz)

    # State owner: this call. Order is spline derivative -> clip -> relaxed
    # current -> Green contraction -> flux -> edge/fit -> normalized update.
    # Stop when both residuals<=tol, nonfinite state, or maxiter updates. The update
    # residual is not a governing-equation/force-balance residual. relax=1 is
    # excluded because it freezes zero initial currents and can falsely stop.
    for iteration in range(1, int(maxiter) + 1):
        try:
            target_currents = closure(pfit, psi, edge)
        except FloatingPointError as exc:
            return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "nonfinite", iteration - 1, np.nan, np.nan, str(exc))
        old = psi.copy()
        old_currents = currents.copy()
        try:
            currents, psi = relaxed_green_update(target_currents, old_currents, relax, g_psi, psi0)
        except FloatingPointError as exc:
            return result(old.reshape(R.shape), old_currents.reshape(R.shape), pfit, "nonfinite", iteration, np.nan, np.nan, str(exc))
        psi_mid = psi[z0_idx]
        try:
            edge = float(psi_mid[lim_idx])
            pfit = fit(psi_mid)
        except Exception as exc:
            return result(psi.reshape(R.shape), currents.reshape(R.shape), None, "nonfinite", iteration, np.nan, np.nan, str(exc))
        if not np.isfinite(edge) or edge == 0:
            return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "nonfinite", iteration, np.nan, np.nan, "zero or nonfinite edge flux")
        residual = float(np.linalg.norm(psi - old) / abs(edge))
        if not np.isfinite(residual):
            return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "nonfinite", iteration, residual, np.nan, "nonfinite update residual")

        # The update residual only measures a fixed point of the Green map.  A
        # zero (or otherwise insensitive) Green map can therefore report a
        # stationary flux while relaxed currents still violate the governing
        # pressure-current relation.  Re-evaluate the relation against the
        # *new* spline state before declaring convergence.  This is a closure
        # residual for I_cell = R (dP/dpsi) dR dZ; it is not a force-balance
        # residual and makes no broader physical-equilibrium claim.
        try:
            target_new = closure(pfit, psi, edge)
        except FloatingPointError as exc:
            return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "nonfinite", iteration, residual, np.nan, str(exc))
        # Use common component scaling before norms.  The denominator is only
        # the target norm, giving the declared
        # ||I_new-I_target||_2 / ||I_target||_2 relation; using the actual
        # current as a competing denominator would under-report an oversized
        # current and make the public closure contract state-dependent.
        closure_residual = _normalized_closure_residual(currents, target_new)
        update_history.append(residual)
        closure_history.append(closure_residual)
        if not np.isfinite(closure_residual):
            return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "nonfinite", iteration, residual, closure_residual, "nonfinite pressure-current closure residual")
        if residual <= tol and closure_residual <= tol:
            return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "converged", iteration, residual, closure_residual, "update and pressure-current closure residuals <= tol")
    return result(psi.reshape(R.shape), currents.reshape(R.shape), pfit, "maxiter", int(maxiter), residual, closure_residual, "iteration bound reached")
