"""One axisymmetric Picard flux update over a declared R--Z grid."""

from __future__ import annotations

import numpy as np

from ._anisotropic_numerics import cell_areas

__all__ = ["update_axisymmetric_picard_flux"]


def update_axisymmetric_picard_flux(
    r_grid,
    z_grid,
    j_phi,
    psi_state,
    psi_vac,
    g_psi,
    relax,
    previous_cell_currents=None,
    *,
    cell_edges=None,
):
    """Integrate current, apply the Green response, and report residuals.

    Parameters
    ----------
    r_grid : finite real array-like
        Cylindrical radius mesh [m] Shape [N_Z,N_R]. Nonnegative, rectilinear and strictly increasing radial axis; at least three columns.
    z_grid : finite real array-like
        Axial coordinate mesh [m] Shape [N_Z,N_R]. Rectilinear and strictly increasing axial axis; at least three rows and same shape as r_grid.
    j_phi : finite real array-like
        Caller-selected toroidal current density at each grid cell [A/m^2] Shape [N_Z,N_R]. Same shape as the grid; this Operator does not apply a plasma mask.
    psi_state : finite real array-like
        Previous total psi=R A_phi state [Wb/rad] Shape [N_Z,N_R]. Same shape as the grid; used for flux relaxation and relative change.
    psi_vac : finite real array-like
        Vacuum or external psi=R A_phi contribution [Wb/rad] Shape [N_Z,N_R]. Same shape as the grid and aligned with Green response rows.
    g_psi : finite real array-like
        Dense cell-current-to-psi response matrix [Wb/rad/A] Shape [N_Z*N_R,N_Z*N_R]. Finite square matrix with field-point rows and source-current columns in [Z,R] C order.
    relax : real scalar convertible to float
        Weight retained from psi_state Shape scalar. Finite and 0 <= relax < 1; one is rejected.
    previous_cell_currents : finite real array-like or None
        Previous raw cell-current array used only for the current-change diagnostic [A] Shape [N_Z,N_R] or null. If omitted or null, compare against zeros; otherwise exactly match the grid shape.
    cell_edges : pair of finite arrays or None
        Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current [m] Shape (N_R+1, N_Z+1) arrays or None. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Returns
    -------
    psi_next : float64
        Flux-relaxed next total psi=R A_phi state [Wb/rad] Shape [N_Z,N_R]. relax*psi_state+(1-relax)*(psi_vac+G_psi @ raw_currents).
    plasma_cell_currents : float64
        Terminal or step current density integrated with the explicitly declared node/cell-domain weights [A] Shape [N_Z,N_R]. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.
    relative_psi_change : float
        L2 norm of psi_next-psi_state divided by max(||psi_next||,||psi_vac||,tiny) Shape scalar. Uses the returned psi_next and the previous psi_state.
    relative_current_change : float
        L2 norm of raw currents minus prior currents divided by max(||raw currents||,1) Shape scalar. Previous currents affect this diagnostic only, not the flux update.
    fixed_point_residual : float
        Norm(candidate-psi_state)/max(norm(candidate),norm(psi_vac),tiny); independent of relax Shape scalar. Norm(candidate-psi_state)/max(norm(candidate),norm(psi_vac),tiny); independent of relax.

    Raises
    ------
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    compute_anisotropic_force_balance : Compute the force state that supplies the current.

    Notes
    -----
    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current. Form candidate=psi_vac+G_psi@I and psi_next=relax*psi_state+(1-relax)*candidate. Return relaxed step change, raw-current change, and unrelaxed fixed-point residual.

    one axisymmetric dense-Green Picard step with flux relaxation, not current relaxation

    relax is the weight of the previous flux, not a mixer for current values.

    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Both psi and the Green flux response use the R A_phi convention in Wb/rad; the actual toroidal equation does not include 2*pi, the legacy Wb labels in the vacuum-field/superposition chain are corrected, and no numerical value is changed.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import update_axisymmetric_picard_flux
    >>> r,z=np.meshgrid([1.,1.2,2.],[-.4,-.1,.4])
    >>> out=update_axisymmetric_picard_flux(r,z,r,r*0,r*0,np.zeros((9,9)),0.)
    >>> np.testing.assert_allclose(out['plasma_cell_currents'].sum(),1.2,rtol=1e-14,atol=1e-14)
    """
    arrays = [
        np.asarray(value, dtype=float) for value in (r_grid, z_grid, j_phi, psi_state, psi_vac)
    ]
    shape = arrays[0].shape
    if any(
        value.ndim != 2 or value.shape != shape or not np.all(np.isfinite(value))
        for value in arrays
    ):
        raise ValueError(
            "R, Z, j_phi, psi_state, and psi_vac must be finite same-shape [Z,R] arrays"
        )
    r_grid, z_grid, j_phi, psi_state, psi_vac = arrays
    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (
        r_axis.size < 3
        or z_axis.size < 3
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
        or r_axis[0] < 0.0
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
    ):
        raise ValueError(
            "a finite nonnegative strictly increasing rectilinear R-Z grid with at least 3 points per axis is required"
        )
    green = np.asarray(g_psi, dtype=float)
    if green.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(green)):
        raise ValueError(f"g_psi must have shape ({r_grid.size}, {r_grid.size}) and finite entries")
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation < 1.0:
        raise ValueError("relax must lie in [0, 1)")

    raw_currents = j_phi * cell_areas(r_grid, z_grid, cell_edges)
    old = (
        np.zeros_like(raw_currents)
        if previous_cell_currents is None
        else np.asarray(previous_cell_currents, dtype=float)
    )
    if old.shape != shape or not np.all(np.isfinite(old)):
        raise ValueError("previous_cell_currents must be finite with shape [N_Z,N_R]")

    candidate = psi_vac + (green @ raw_currents.ravel()).reshape(shape)
    psi_next = relaxation * psi_state + (1.0 - relaxation) * candidate
    tiny = np.finfo(float).tiny
    relative_psi_change = float(
        np.linalg.norm(psi_next - psi_state)
        / max(np.linalg.norm(psi_next), np.linalg.norm(psi_vac), tiny)
    )
    fixed_point_residual = float(
        np.linalg.norm(candidate - psi_state)
        / max(np.linalg.norm(candidate), np.linalg.norm(psi_vac), tiny)
    )
    relative_current_change = float(
        np.linalg.norm(raw_currents - old) / max(np.linalg.norm(raw_currents), 1.0)
    )
    return {
        "psi_next": psi_next,
        "plasma_cell_currents": raw_currents,
        "relative_psi_change": relative_psi_change,
        "relative_current_change": relative_current_change,
        "fixed_point_residual": fixed_point_residual,
    }
