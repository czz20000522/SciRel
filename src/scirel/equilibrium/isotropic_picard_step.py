"""One finite isotropic pressure-current/Green update."""

from __future__ import annotations

import numpy as np

from scirel._result import Result

from ._pressure_current import current_target, relaxed_green_update

__all__ = ["pressure_flux_picard_step"]


def pressure_flux_picard_step(
    r_grid, z_grid, psi_state, psi_vac, g_psi, pressure_derivative, psi_edge, currents_old, relax
):
    """Advance one current, Green-flux, and normalized residual step.

    Parameters
    ----------
    r_grid : real array-like, converted to float64
        Cylindrical radius at each grid cell [m] Shape [N_Z,N_R]. Finite two-dimensional tensor-product grid with at least two strictly increasing, uniformly spaced R points; same shape as z_grid, psi_state and psi_vac. Physical use requires nonnegative radii, which are not checked.
    z_grid : real array-like, converted to float64
        Axial coordinate at each grid cell [m] Shape [N_Z,N_R]. Finite tensor-product grid with at least two strictly increasing, uniformly spaced Z points; same shape as r_grid. A Z=0 plane is not required by this callable.
    psi_state : real array-like, converted to float64
        Psi=R A_phi before this Picard update [Wb/rad] Shape [N_Z,N_R]. Finite and same shape as r_grid.
    psi_vac : real array-like, converted to float64
        Fixed vacuum psi=R A_phi contribution added after Green-matrix contraction [Wb/rad] Shape [N_Z,N_R]. Finite and same shape as r_grid.
    g_psi : real array-like, converted to float64
        Psi=R A_phi response to cell current; target cells index rows and source cells index columns [Wb/rad/A] Shape [N,N], N=N_Z*N_R. Finite square matrix using the same C-order cell indexing on both axes.
    pressure_derivative : real array-like, converted to float64
        Pressure derivative with respect to psi=R A_phi at each source cell [Pa/(Wb/rad)] Shape N elements after flattening. Finite; one value per grid cell in C order.
    psi_edge : real scalar, converted to float
        Boundary-flux scale for the residual denominator [Wb/rad] Shape scalar. Finite and nonzero; the absolute value is used.
    currents_old : real array-like, converted to float64, or None
        Cell currents from the preceding update; explicit None selects a zero vector [A] Shape N elements after flattening, or None. Finite with one value per grid cell when not None. This argument has no signature default; explicit None is accepted.
    relax : real scalar, converted to float
        Weight of old currents in the new current vector Shape scalar. Finite and in [0,1].

    Returns
    -------
    plasma_currents : float64
        Relaxed, area-integrated cell-current vector [A] Shape [N]. C-order cell indexing; relax=1 retains old currents.
    psi_next : float64
        Updated psi=R A_phi from Green plasma response plus fixed vacuum flux [Wb/rad] Shape [N_Z,N_R]. Finite and same grid shape on successful return; no silent nonfinite masking.
    residual : Python float
        L2 norm of updated-minus-previous flux, divided by the absolute boundary flux Shape scalar. Finite normalized L2 update norm; no grid-size normalization; overflow raises FloatingPointError.

    The complete result is returned as one ``scirel._result.Result`` mapping. No nested
    mapping is introduced, and every field also supports attribute access.

    Raises
    ------
    FloatingPointError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    TypeError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    build_pressure_flux_state : Build the pressure derivative state.

    Notes
    -----
    For each C-order flattened [Z,R] cell form I_target=R*(dp/dpsi)*dR*dZ and I_new=(1-relax)*I_target+relax*I_old. At relax=1 explicitly retain old currents without forming an unused target. Compute psi_plasma=g_psi@I_new, psi_next=psi_plasma+psi_vac and residual=||psi_next-psi_state||_2/abs(psi_edge). Reject any nonfinite current, Green contraction, total flux or residual; no value is silently replaced by zero. This single update does not establish iterative convergence.

    historical axisymmetric isotropic pressure-flux Picard cell-current update using a caller-supplied Green response

    The caller's g_psi maps the same C-order cell-current vector to psi=R A_phi in Wb/rad on the supplied grid; R*dP/dpsi uses that same per-radian coordinate.

    The intended cylindrical radius is nonnegative, but this implementation does not enforce that physical precondition.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step
    >>> r_grid, z_grid = np.meshgrid([1.0, 2.0], [-1.0, 1.0])
    >>> result = pressure_flux_picard_step(r_grid, z_grid, np.zeros((2, 2)), np.ones((2, 2)), np.eye(4), [1.0, 2.0, 3.0, 4.0], 2.0, [10.0, 20.0, 30.0, 40.0], 0.25)
    >>> assert isinstance(result, Result)
    >>> assert result.residual == result['residual']
    >>> np.testing.assert_allclose(result.plasma_currents, [4.0, 11.0, 12.0, 22.0])
    >>> np.testing.assert_allclose(result.psi_next, [[5.0, 12.0], [13.0, 23.0]])
    >>> assert np.isclose(result.residual, np.sqrt(867.0)/2.0)
    """
    r_grid, z_grid, psi_state, psi_vac = [
        np.asarray(value, dtype=float) for value in (r_grid, z_grid, psi_state, psi_vac)
    ]
    if r_grid.ndim != 2 or any(
        value.shape != r_grid.shape for value in (z_grid, psi_state, psi_vac)
    ):
        raise ValueError("r_grid, z_grid, psi_state and psi_vac must be same-shape [Z,R] grids")
    if any(not np.all(np.isfinite(value)) for value in (r_grid, z_grid, psi_state, psi_vac)):
        raise ValueError("r_grid, z_grid, psi_state and psi_vac must be finite")

    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    uniform_r = np.allclose(np.diff(r_axis), np.diff(r_axis)[0], rtol=1e-12, atol=1e-14)
    uniform_z = np.allclose(np.diff(z_axis), np.diff(z_axis)[0], rtol=1e-12, atol=1e-14)
    if (
        r_axis.size < 2
        or z_axis.size < 2
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or not uniform_r
        or not uniform_z
    ):
        raise ValueError("r_grid and z_grid must be uniformly spaced tensor-product grids")

    size = r_grid.size
    green = np.asarray(g_psi, dtype=float)
    if green.shape != (size, size) or not np.all(np.isfinite(green)):
        raise ValueError(f"g_psi must have shape ({size}, {size}) and finite values")
    derivative = np.asarray(pressure_derivative, dtype=float).reshape(-1)
    old = (
        np.zeros(size, dtype=float)
        if currents_old is None
        else np.asarray(currents_old, dtype=float).reshape(-1)
    )
    if derivative.shape != (size,) or old.shape != (size,):
        raise ValueError("pressure_derivative and currents_old must have one value per grid cell")
    if not np.all(np.isfinite(derivative)) or not np.all(np.isfinite(old)):
        raise ValueError("pressure_derivative and currents_old must be finite")
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation <= 1.0:
        raise ValueError("relax must be between 0 and 1")
    edge = float(psi_edge)
    if not np.isfinite(edge) or edge == 0.0:
        raise ValueError("psi_edge must be finite and non-zero")
    dr = abs(float(r_grid[0, 1] - r_grid[0, 0]))
    dz = abs(float(z_grid[1, 0] - z_grid[0, 0]))
    if not np.isfinite(dr) or not np.isfinite(dz) or dr == 0.0 or dz == 0.0:
        raise ValueError("r_grid and z_grid must have nonzero finite spacing")

    target = old if relaxation == 1.0 else current_target(r_grid.ravel(), derivative, dr, dz)
    currents, flux = relaxed_green_update(target, old, relaxation, green, psi_vac.ravel())
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        residual = float(np.linalg.norm(flux - psi_state.ravel()) / abs(edge))
    if not np.isfinite(residual):
        raise FloatingPointError("nonfinite normalized flux-update residual")
    return Result(
        {
            "plasma_currents": currents,
            "psi_next": flux.reshape(r_grid.shape),
            "residual": residual,
        }
    )
