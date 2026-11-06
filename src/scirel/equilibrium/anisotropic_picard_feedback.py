"""Single anisotropic Picard current relaxation and Green feedback step."""

from __future__ import annotations

import numpy as np

from scirel._result import Result

from ._anisotropic_numerics import cell_areas, flux_field_increment

__all__ = ["update_anisotropic_picard_flux"]


def _finite_field(name, value, shape):
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite [Z,R] array with shape {shape}")
    return array


def _green_matrix(name, value, size, required):
    if value is None:
        if required:
            raise ValueError(f"{name} is required")
        return None
    matrix = np.asarray(value, dtype=float)
    if matrix.shape != (size, size) or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must have shape ({size}, {size}) and finite entries")
    return matrix


def update_anisotropic_picard_flux(
    j_phi,
    r_grid,
    z_grid,
    plasma_mask,
    currents_old,
    relax,
    g_psi,
    g_br,
    g_bz,
    psi_vac,
    br_vac,
    bz_vac,
    *,
    cell_edges=None,
):
    """Relax toroidal currents and map them to flux and poloidal fields.

    Parameters
    ----------
    j_phi : finite real array-like
        Toroidal current density before optional plasma clipping [A/m^2] Shape [N_Z,N_R]. Same shape as the grid; when a mask is supplied, True cells preserve the supplied value and False cells become zero before weighting.
    r_grid : finite real array-like
        Radius tensor grid [m] Shape [N_Z,N_R]. At least two points per axis, rows repeat one strictly monotone radial axis within the implementation tolerances; descending axes are allowed.
    z_grid : finite real array-like
        Axial tensor grid [m] Shape [N_Z,N_R]. Same grid shape; columns repeat one strictly monotone axial axis within the implementation tolerances; descending axes are allowed.
    plasma_mask : bool array or None
        Optional active-cell selector, passed explicitly as None when absent [boolean] Shape [N_Z,N_R] or null. None means all cells active; otherwise exact grid shape and boolean dtype, without broadcast or 0/1 coercion. True cells preserve j_phi and False cells zero it.
    currents_old : finite real array-like or None
        Previous relaxed cell-current state, passed explicitly as None for zero initialization [A] Shape [N_Z*N_R] or null. None initializes all zeros; otherwise exact flattened length and finite values.
    relax : finite real scalar
        Retention weight of the old cell-current state Shape scalar. 0 <= relax <= 1; 0 uses raw current, 1 retains the old state.
    g_psi : finite real array-like
        Dense current-to-flux Green response for psi=R A_phi [Wb/rad/A] Shape [N_Z*N_R,N_Z*N_R]. Required, exact square shape; rows are field points and columns are C-order source cells.
    g_br : finite real array-like or None
        Optional current-to-radial-field Green response, passed explicitly as None when absent [T/A] Shape [N_Z*N_R,N_Z*N_R] or null. Must be supplied as a finite exact square matrix together with g_bz, or both must be None.
    g_bz : finite real array-like or None
        Optional current-to-axial-field Green response, passed explicitly as None when absent [T/A] Shape [N_Z*N_R,N_Z*N_R] or null. Must be supplied as a finite exact square matrix together with g_br, or both must be None.
    psi_vac : finite real array-like
        Vacuum or external psi=R A_phi offset [Wb/rad] Shape [N_Z,N_R]. Exact grid shape; added to the g_psi response.
    br_vac : finite real array-like
        Vacuum radial-field offset [T] Shape [N_Z,N_R]. Exact grid shape; when field Green matrices are absent, add the discrete field increment derived from the same plasma flux increment.
    bz_vac : finite real array-like
        Vacuum axial-field offset [T] Shape [N_Z,N_R]. Exact grid shape; when field Green matrices are absent, add the discrete field increment derived from the same plasma flux increment.
    cell_edges : pair of finite arrays or None
        Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current [m] Shape (N_R+1, N_Z+1) arrays or None. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Returns
    -------
    psi : float64
        Vacuum psi=R A_phi plus relaxed-current Green response [Wb/rad] Shape [N_Z,N_R]. The matrix response uses C-order flattened cell currents.
    BR : float64
        Vacuum radial field plus the same added plasma-flux field response [T] Shape [N_Z,N_R]. With paired field Green matrices, add g_br times the relaxed source currents; when both are None, add -dZ(psi-psi_vac)/R using the maintained discrete flux derivative and regular-axis rule.
    BZ : float64
        Vacuum axial field plus the same added plasma-flux field response [T] Shape [N_Z,N_R]. With paired field Green matrices, add g_bz times the relaxed source currents; when both are None, add dR(psi-psi_vac)/R using the maintained discrete flux derivative and regular-axis rule.
    j_phi : float64
        Current density after plasma-mask clipping [A/m^2] Shape [N_Z,N_R]. True cells retain the supplied value; False cells are zero when a mask is supplied.
    initial_picard_current_state : float64
        Zero current vector for graph zero-step initialization [A] Shape [N_Z*N_R]. Always zeros, independent of supplied currents_old.
    picard_current_state : float64
        Relaxed C-order flattened cell-current vector used by the Green projections [A] Shape [N_Z*N_R]. (1-relax)*raw currents + relax*old currents.
    plasma_currents : float64
        Terminal or step current density integrated with the explicitly declared node/cell-domain weights [A] Shape [N_Z,N_R]. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    The complete result is returned as one ``scirel._result.Result`` mapping. No nested
    mapping is introduced, and every field also supports attribute access.

    Raises
    ------

    See Also
    --------
    update_axisymmetric_picard_flux : Apply the isotropic counterpart of this Picard update.

    Notes
    -----
    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current. Set inactive density to zero; I=(1-relax)*I_raw+relax*I_old. Project psi through G_psi. A paired G_BR/G_BZ supplies field responses; when absent, differentiate the same added flux and add that magnetic increment to the vacuum field.

    one explicit cell-current Picard feedback step using caller-provided dense linear Green responses

    The caller's Green matrices match the declared cell-current ordering and SI response units.

    relax weights the previous cell-current state, not the previous flux.

    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Both psi and the Green flux response use the R A_phi convention in Wb/rad; the actual toroidal equation does not include 2*pi, the legacy Wb labels in the vacuum-field/superposition chain are corrected, and no numerical value is changed.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.equilibrium import update_anisotropic_picard_flux
    >>> r, z = np.meshgrid([0.2, 0.4], [-0.1, 0.1])
    >>> j = np.array([[1.0, 2.0], [3.0, 4.0]])
    >>> mask = np.array([[True, False], [False, True]])
    >>> old = np.array([0.2, 0.3, 0.4, 0.5])
    >>> result = update_anisotropic_picard_flux(j, r, z, mask, old, 0.25, np.eye(4), 2*np.eye(4), -np.eye(4), np.zeros((2,2)), np.ones((2,2)), 2*np.ones((2,2)), cell_edges=([.1,.3,.5],[-.2,0.,.2]))
    >>> raw = np.array([0.04, 0.0, 0.0, 0.16])
    >>> relaxed = 0.75*raw + 0.25*old
    >>> assert isinstance(result, Result)
    >>> assert result.psi is result['psi']
    >>> np.testing.assert_allclose(result.plasma_currents.ravel(), raw)
    >>> np.testing.assert_allclose(result.picard_current_state, relaxed)
    >>> np.testing.assert_allclose(result.psi.ravel(), relaxed)
    >>> np.testing.assert_allclose(result.BR.ravel(), 1.0 + 2*relaxed)
    >>> np.testing.assert_allclose(result.BZ.ravel(), 2.0 - relaxed)
    """
    r_grid = np.asarray(r_grid, dtype=float)
    if r_grid.ndim != 2:
        raise ValueError("r_grid must be a two-dimensional [Z,R] grid")
    shape = r_grid.shape
    r_grid = _finite_field("r_grid", r_grid, shape)
    z_grid = _finite_field("z_grid", z_grid, shape)
    j_phi = _finite_field("j_phi", j_phi, shape)
    psi_vac = _finite_field("psi_vac", psi_vac, shape)
    br_vac = _finite_field("br_vac", br_vac, shape)
    bz_vac = _finite_field("bz_vac", bz_vac, shape)
    if not np.allclose(r_grid, r_grid[0:1, :]) or not np.allclose(z_grid, z_grid[:, 0:1]):
        raise ValueError("r_grid and z_grid must be tensor-product [Z,R] grids")
    if shape[0] < 2 or shape[1] < 2:
        raise ValueError("r_grid and z_grid need at least two points per axis to define cell area")

    areas = cell_areas(r_grid, z_grid, cell_edges)
    size = r_grid.size
    old = (
        np.zeros(size, dtype=float)
        if currents_old is None
        else np.asarray(currents_old, dtype=float)
    )
    if old.shape != (size,) or not np.all(np.isfinite(old)):
        raise ValueError(f"currents_old must have finite shape ({size},)")
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation <= 1.0:
        raise ValueError("relax must be a finite scalar in [0,1]")
    if (g_br is None) != (g_bz is None):
        raise ValueError("g_br and g_bz must be provided together")
    green_psi = _green_matrix("g_psi", g_psi, size, True)
    green_br = _green_matrix("g_br", g_br, size, False)
    green_bz = _green_matrix("g_bz", g_bz, size, False)

    density = j_phi
    if plasma_mask is not None:
        mask = np.asarray(plasma_mask)
        if mask.dtype != np.dtype(bool) or mask.shape != shape:
            raise ValueError(f"plasma_mask must be boolean with shape {shape}")
        density = np.where(mask, j_phi, 0.0)
    raw_currents = density * areas
    currents = (1.0 - relaxation) * raw_currents.ravel() + relaxation * old
    psi = (psi_vac.ravel() + green_psi @ currents).reshape(shape)

    if green_br is None:
        reverse_z = z_grid[1, 0] < z_grid[0, 0]
        reverse_r = r_grid[0, 1] < r_grid[0, 0]
        order = (
            slice(None, None, -1) if reverse_z else slice(None),
            slice(None, None, -1) if reverse_r else slice(None),
        )
        increment = flux_field_increment(r_grid[order], z_grid[order], (psi - psi_vac)[order])
        br = br_vac + increment["B_R"][order]
        bz = bz_vac + increment["B_Z"][order]
    else:
        br = (br_vac.ravel() + green_br @ currents).reshape(shape)
        bz = (bz_vac.ravel() + green_bz @ currents).reshape(shape)
    return Result(
        {
            "psi": psi,
            "BR": br,
            "BZ": bz,
            "j_phi": density,
            "initial_picard_current_state": np.zeros(size, dtype=float),
            "picard_current_state": currents,
            "plasma_currents": raw_currents,
        }
    )
