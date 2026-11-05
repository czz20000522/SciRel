"""Composition boundary for the pressure-only equilibrium feedback solve."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from scirel._validation import finite_scalar, integer_scalar
from .equilibrium_state import compute_equilibrium
from .pressure_flux_state import build_pressure_flux_state

__all__ = ["solve_isotropic_pressure_flux"]


def _required_inputs(inputs):
    names = (
        "r_grid",
        "z_grid",
        "psi_vac",
        "g_psi",
        "pressure_of_radius",
        "tol",
        "maxiter",
        "relax",
    )
    missing = [name for name in names if name not in inputs]
    if missing:
        raise ValueError(f"{missing[0]} is required")


def run_composition(inputs):
    """Validate composition ports and package the shared solver's terminal state."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    _required_inputs(inputs)
    R, Z, psi_vac, green = [
        np.asarray(inputs[name], dtype=float) for name in ("r_grid", "z_grid", "psi_vac", "g_psi")
    ]
    if R.ndim != 2 or Z.shape != R.shape or psi_vac.shape != R.shape:
        raise ValueError("r_grid, z_grid and psi_vac must be same-shape [Z,R] grids")
    if green.shape != (R.size, R.size):
        raise ValueError(f"g_psi must have shape ({R.size}, {R.size})")
    tol = finite_scalar(inputs["tol"], "tol", None)
    maxiter = integer_scalar(inputs["maxiter"], "maxiter", None, minimum=0)
    relax = finite_scalar(inputs["relax"], "relax", None)
    pressure_of_radius = inputs["pressure_of_radius"]
    if not callable(pressure_of_radius):
        raise ValueError("pressure_of_radius must be callable")

    def pressure(radius):
        value = np.asarray(pressure_of_radius(radius), dtype=float)
        if value.ndim != 0 or not np.isfinite(value) or value < 0.0:
            raise ValueError("pressure_of_radius must return finite nonnegative scalar values")
        return float(value)

    try:
        result = compute_equilibrium(
            R,
            Z,
            pressure,
            psi_vac,
            green,
            tol=tol,
            maxiter=maxiter,
            relax=relax,
            plas_clip=inputs.get("plasma_mask"),
        )
    except ValueError as exc:
        if "uniformly spaced" in str(exc):
            raise ValueError(
                "r_grid and z_grid must be uniformly spaced tensor-product grids and resolvable"
            ) from exc
        raise

    representation = None
    if result.p_psifit is not None and np.all(np.isfinite(result.psi)):
        try:
            representation = build_pressure_flux_state(
                R, Z, result.psi, pressure, inputs.get("plasma_mask")
            )["pressure_of_psi"]
        except (ValueError, FloatingPointError):
            if result.status != "nonfinite":
                raise
    return {
        "psi": result.psi,
        "plasma_currents": result.plas_currents,
        "pressure_of_psi": representation,
        "iterations": result.iterations,
        "residual": result.residual,
        "closure_residual": result.closure_residual,
        "residual_history": np.asarray(result.residual_history, dtype=float),
        "closure_residual_history": np.asarray(result.closure_residual_history, dtype=float),
        "converged": result.status == "converged",
        "status": result.status,
        "failure_reason": (
            None
            if result.status == "converged"
            else "maxiter_reached"
            if result.status == "maxiter"
            else result.reason
        ),
    }


def solve_isotropic_pressure_flux(inputs=None, **kwargs):
    """Solve pressure-only Picard feedback with flux and closure gates.

    Inputs may be supplied as a mapping, keywords, or both.  The public
    boundary accepts increasing or decreasing uniform axes; ``relax=1`` is
    rejected by the shared solver because it freezes the initial current state.
    """
    if inputs is not None and not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    values = {} if inputs is None else dict(inputs)
    values.update(kwargs)
    return run_composition(values)
