"""One finite isotropic pressure-current/Green update; no convergence claim."""
import numpy as np
from ._pressure_current import current_target, relaxed_green_update

def pressure_flux_picard_step(r_grid, z_grid, psi_state, psi_vac, g_psi, pressure_derivative, psi_edge, currents_old, relax):
    """Advance one source-order cell-current, Green-flux and residual step."""
    r_grid = np.asarray(r_grid, dtype=float)
    z_grid = np.asarray(z_grid, dtype=float)
    psi_state = np.asarray(psi_state, dtype=float)
    psi_vac = np.asarray(psi_vac, dtype=float)
    if r_grid.ndim != 2 or any((value.shape != r_grid.shape for value in (z_grid, psi_state, psi_vac))):
        raise ValueError('r_grid, z_grid, psi_state and psi_vac must be same-shape [Z,R] grids')
    if any((not np.all(np.isfinite(value)) for value in (r_grid, z_grid, psi_state, psi_vac))):
        raise ValueError('r_grid, z_grid, psi_state and psi_vac must be finite')
    r_axis, z_axis = (r_grid[0, :], z_grid[:, 0])
    if r_axis.size < 2 or z_axis.size < 2 or (not np.allclose(r_grid, r_axis[np.newaxis, :])) or (not np.allclose(z_grid, z_axis[:, np.newaxis])) or np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0) or (not np.allclose(np.diff(r_axis), np.diff(r_axis)[0], rtol=1e-12, atol=1e-14)) or (not np.allclose(np.diff(z_axis), np.diff(z_axis)[0], rtol=1e-12, atol=1e-14)):
        raise ValueError('r_grid and z_grid must be uniformly spaced tensor-product grids')
    n_points = r_grid.size
    g_psi = np.asarray(g_psi, dtype=float)
    if g_psi.shape != (n_points, n_points) or not np.all(np.isfinite(g_psi)):
        raise ValueError(f'g_psi must have shape ({n_points}, {n_points}) and finite values')
    pressure_derivative = np.asarray(pressure_derivative, dtype=float).reshape(-1)
    currents_old = np.zeros(n_points, dtype=float) if currents_old is None else np.asarray(currents_old, dtype=float).reshape(-1)
    if pressure_derivative.shape != (n_points,) or currents_old.shape != (n_points,):
        raise ValueError('pressure_derivative and currents_old must have one value per grid cell')
    if not np.all(np.isfinite(pressure_derivative)) or not np.all(np.isfinite(currents_old)):
        raise ValueError('pressure_derivative and currents_old must be finite')
    relax = float(relax)
    if not np.isfinite(relax) or not 0.0 <= relax <= 1.0:
        raise ValueError('relax must be between 0 and 1')
    psi_edge = float(psi_edge)
    if not np.isfinite(psi_edge) or psi_edge == 0.0:
        raise ValueError('psi_edge must be finite and non-zero')
    dr = abs(float(r_grid[0, 1] - r_grid[0, 0]))
    dz = abs(float(z_grid[1, 0] - z_grid[0, 0]))
    if not np.isfinite(dr) or not np.isfinite(dz) or dr == 0.0 or (dz == 0.0):
        raise ValueError('r_grid and z_grid must have nonzero finite spacing')
    # relax=1 is a legitimate explicit one-step no-op in current space;
    # the full closure-aware solver separately excludes it.
    target = currents_old if relax == 1.0 else current_target(r_grid.ravel(), pressure_derivative, dr, dz)
    currents, psi_next = relaxed_green_update(target, currents_old, relax, g_psi, psi_vac.ravel())
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        residual = float(np.linalg.norm(psi_next - psi_state.ravel()) / abs(psi_edge))
    if not np.isfinite(residual):
        raise FloatingPointError('nonfinite normalized flux-update residual')
    return {'plasma_currents': currents, 'psi_next': psi_next.reshape(r_grid.shape), 'residual': residual}
__all__ = ['pressure_flux_picard_step']
