"""One source-order flux-relaxed axisymmetric Picard Green update."""
import numpy as np

def update_axisymmetric_picard_flux(r_grid, z_grid, j_phi, psi_state, psi_vac, g_psi, relax, previous_cell_currents=None):
    """Discretize current, project Green flux, relax flux, and measure source-order changes."""
    arrays = [np.asarray(value, dtype=float) for value in (r_grid, z_grid, j_phi, psi_state, psi_vac)]
    shape = arrays[0].shape
    if any((value.ndim != 2 or value.shape != shape or (not np.all(np.isfinite(value))) for value in arrays)):
        raise ValueError('R, Z, j_phi, psi_state, and psi_vac must be finite same-shape [Z,R] arrays')
    r_grid, z_grid, j_phi, psi_state, psi_vac = arrays
    r, z = (r_grid[0, :], z_grid[:, 0])
    if r.size < 3 or z.size < 3 or (not np.allclose(r_grid, r[np.newaxis, :])) or (not np.allclose(z_grid, z[:, np.newaxis])) or (r[0] < 0.0) or np.any(np.diff(r) <= 0.0) or np.any(np.diff(z) <= 0.0):
        raise ValueError('a finite nonnegative strictly increasing rectilinear R-Z grid with at least 3 points per axis is required')
    matrix = np.asarray(g_psi, dtype=float)
    if matrix.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(matrix)):
        raise ValueError('g_psi must be finite with shape (grid_size, grid_size)')
    relax = float(relax)
    if not np.isfinite(relax) or not 0.0 <= relax < 1.0:
        raise ValueError('relax must lie in [0, 1)')
    raw_currents = j_phi * float(r[1] - r[0]) * float(z[1] - z[0])
    old = np.zeros_like(raw_currents) if previous_cell_currents is None else np.asarray(previous_cell_currents, dtype=float)
    if old.shape != shape or not np.all(np.isfinite(old)):
        raise ValueError('previous_cell_currents must be finite with shape [N_Z,N_R]')
    candidate = psi_vac + (matrix @ raw_currents.ravel()).reshape(shape)
    psi_next = relax * psi_state + (1.0 - relax) * candidate
    relative_psi_change = float(np.linalg.norm(psi_next - psi_state) / max(float(np.linalg.norm(psi_next)), float(np.linalg.norm(psi_vac)), np.finfo(float).tiny))
    relative_current_change = float(np.linalg.norm(raw_currents - old) / max(float(np.linalg.norm(raw_currents)), 1.0))
    return {'psi_next': psi_next, 'plasma_cell_currents': raw_currents, 'relative_psi_change': relative_psi_change, 'relative_current_change': relative_current_change}
__all__ = ['update_axisymmetric_picard_flux']
