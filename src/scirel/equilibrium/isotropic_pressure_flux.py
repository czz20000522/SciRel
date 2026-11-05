"""Composition boundary for the pressure-only equilibrium feedback solve."""

from __future__ import annotations

import numpy as np

from scirel._validation import finite_scalar, integer_scalar
from .equilibrium_state import compute_equilibrium
from .pressure_flux_state import build_pressure_flux_state

__all__ = ["solve_isotropic_pressure_flux"]


def _run_composition(
    r_grid,
    z_grid,
    psi_vac,
    g_psi,
    pressure_of_radius,
    *,
    tol,
    maxiter,
    relax,
    plasma_mask=None,
):
    """Validate composition ports and package the shared solver's terminal state."""
    R, Z, psi_vac, green = [
        np.asarray(value, dtype=float) for value in (r_grid, z_grid, psi_vac, g_psi)
    ]
    if R.ndim != 2 or Z.shape != R.shape or psi_vac.shape != R.shape:
        raise ValueError("r_grid, z_grid and psi_vac must be same-shape [Z,R] grids")
    if green.shape != (R.size, R.size):
        raise ValueError(f"g_psi must have shape ({R.size}, {R.size})")
    tol = finite_scalar(tol, "tol", None)
    maxiter = integer_scalar(maxiter, "maxiter", None, minimum=0)
    relax = finite_scalar(relax, "relax", None)
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
            plas_clip=plasma_mask,
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
            representation = build_pressure_flux_state(R, Z, result.psi, pressure, plasma_mask)[
                "pressure_of_psi"
            ]
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


def solve_isotropic_pressure_flux(
    r_grid,
    z_grid,
    psi_vac,
    g_psi,
    pressure_of_radius,
    *,
    tol,
    maxiter,
    relax,
    plasma_mask=None,
):
    """Solve bounded pressure-only Picard feedback with two residual gates.

    The shared solver owns the only feedback loop. It builds the midplane
    pressure spline, assembles cell currents, relaxes them, applies the supplied
    Green response and checks both the flux update and terminal current closure.
    Increasing or decreasing uniform axes are accepted; ``relax=1`` is rejected
    because it freezes the initial current state.

    Parameters
    ----------
    r_grid : real array-like, shape [N_Z,N_R]
        Cylindrical radius at each field cell [m]. Finite, rectilinear and
        uniformly spaced along a strictly monotone R axis; same shape as
        ``z_grid`` and ``psi_vac``, with at least two points per axis.
    z_grid : real array-like, shape [N_Z,N_R]
        Axial coordinate at each field cell [m]. Finite, rectilinear and
        uniformly spaced along a strictly monotone Z axis; contains exactly one
        complete row at ``Z=0``.
    psi_vac : real array-like, shape [N_Z,N_R]
        Caller-supplied vacuum or external flux ``psi=R A_phi`` [Wb/rad].
        Finite, copied into the initial state, and aligned with Green-matrix
        field-point rows in C order.
    g_psi : real array-like, shape [N_Z*N_R,N_Z*N_R]
        Dense response from cell currents to field-point flux [Wb/rad/A]. Rows
        and columns follow the input grid in C order; this is not a
        coil-to-probe Green cache.
    pressure_of_radius : callable
        Midplane radial pressure function ``pressure_of_radius(R_m) -> P_Pa``
        [Pa]. It must return finite nonnegative scalar values, include an exact
        zero-pressure boundary and yield enough increasing flux samples for a
        cubic spline.
    tol : real scalar
        Shared threshold for the normalized flux-update and pressure-current
        closure residuals [dimensionless]. Finite and strictly positive; no
        update leaves both residuals at positive infinity.
    maxiter : integer scalar
        Maximum number of Picard updates [iteration]. Nonnegative and not bool;
        zero validates the initial state without updating it.
    relax : real scalar
        Weight of the previous cell current in each update [dimensionless].
        Finite with ``0 <= relax < 1``.
    plasma_mask : boolean array-like, optional
        Cell selector with shape [N_Z,N_R] [boolean]. ``True`` suppresses the
        local pressure derivative; numeric masks are rejected. Default is
        ``None``, which applies no mask.

    Returns
    -------
    psi : ndarray of float64, shape [N_Z,N_R]
        Last evaluated flux state [Wb/rad]; with ``maxiter=0`` this is an
        independent copy of ``psi_vac``.
    plasma_currents : ndarray of float64, shape [N_Z,N_R]
        Last cell-current state [A] in [Z,R] order.
    pressure_of_psi : mapping or None
        Terminal pressure-flux samples and cubic-spline representation
        [Pa and Wb/rad], with zero extrapolation metadata; ``None`` when no
        valid terminal spline is available.
    iterations : int
        Number of attempted Picard updates [iteration], from zero through
        ``maxiter``.
    residual : float
        Last normalized L2 flux-change residual [dimensionless]; positive
        infinity before any update.
    residual_history : ndarray of float64, shape [N_completed]
        Flux residuals after completed paired residual evaluations
        [dimensionless].
    converged : bool
        Whether both finite residuals were at most ``tol`` after an update
        [boolean].
    failure_reason : str or None
        ``None`` on convergence, ``maxiter_reached`` at the iteration bound, or
        the shared solver's specific terminal failure reason.
    closure_residual : float
        Terminal normalized pressure-current residual [dimensionless];
        positive infinity before any update.
    closure_residual_history : ndarray of float64, shape [N_completed]
        Closure residuals at the same states as ``residual_history``
        [dimensionless].
    status : str
        Terminal status: ``converged``, ``maxiter`` or ``nonfinite``.

    Raises
    ------
    TypeError
        If a required argument is missing, the removed mapping or ``**kwargs``
        form is used, or an unknown keyword is supplied.
    ValueError
        If arrays, grids, callback results, controls or a boolean mask violate
        the documented contract. Exceptions raised by ``pressure_of_radius``
        propagate unchanged.

    See Also
    --------
    scirel.equilibrium.compute_equilibrium : Shared pressure-current feedback.
    scirel.equilibrium.build_pressure_flux_state : Terminal pressure spline.

    Notes
    -----
    ``residual`` measures the Green-map flux update, while
    ``closure_residual`` measures the pressure-current equation in the terminal
    spline state. Both must be finite and no greater than ``tol`` after an
    actual update before ``converged`` is true. This is a bounded discrete
    Green-map closure, not a continuum force-balance or stability claim.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import solve_isotropic_pressure_flux
    >>> r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.8, 4), [-0.1, 0.0, 0.1])
    >>> result = solve_isotropic_pressure_flux(
    ...     r_grid=r_grid,
    ...     z_grid=z_grid,
    ...     psi_vac=r_grid.copy(),
    ...     g_psi=np.zeros((r_grid.size, r_grid.size)),
    ...     pressure_of_radius=lambda r: max(1.0-r/0.8, 0.0),
    ...     tol=1e-12,
    ...     maxiter=1,
    ...     relax=0.0,
    ... )
    >>> np.testing.assert_allclose(result['psi'], r_grid)
    >>> assert result['iterations'] == 1 and result['converged']
    >>> assert result['pressure_of_psi']['extrapolation'] == 'zeros'
    >>> assert result['closure_residual']<=1e-12 and result['status']=='converged'
    """
    return _run_composition(
        r_grid,
        z_grid,
        psi_vac,
        g_psi,
        pressure_of_radius,
        tol=tol,
        maxiter=maxiter,
        relax=relax,
        plasma_mask=plasma_mask,
    )
