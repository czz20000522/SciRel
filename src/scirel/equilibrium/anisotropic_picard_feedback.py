"""One SciRel anisotropic Picard current relaxation and Green feedback step."""
import numpy as np
from ._anisotropic_numerics import cell_areas, flux_field_increment

def _field(name, value, shape):
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f'{name} must be a finite [Z,R] array with shape {shape}')
    return array

def _matrix(name, value, size, required):
    if value is None:
        if required:
            raise ValueError(f'{name} is required')
        return None
    matrix = np.asarray(value, dtype=float)
    if matrix.shape != (size, size) or not np.all(np.isfinite(matrix)):
        raise ValueError(f'{name} must have shape ({size}, {size}) and finite entries')
    return matrix

def update_anisotropic_picard_flux(j_phi, r_grid, z_grid, plasma_mask, currents_old, relax, g_psi, g_br, g_bz, psi_vac, br_vac, bz_vac, *, cell_edges=None):
    """Relax local control-cell currents and project through Green matrices.

    Axes may ascend or descend and may be nonuniform. Default trapezoid
    weights span the nodes; explicit cell_edges bind cell-center domains. A supplied
    mask is boolean with exact [Z,R] shape. Without field Green matrices, the
    field increment is differentiated from the same plasma flux increment.
    """
    shape = np.asarray(r_grid, dtype=float).shape
    if len(shape) != 2:
        raise ValueError('r_grid must be a two-dimensional [Z,R] grid')
    r = _field('r_grid', r_grid, shape)
    z = _field('z_grid', z_grid, shape)
    current_density = _field('j_phi', j_phi, shape)
    psi0 = _field('psi_vac', psi_vac, shape)
    br0 = _field('br_vac', br_vac, shape)
    bz0 = _field('bz_vac', bz_vac, shape)
    if not np.allclose(r, r[0:1, :], rtol=1e-12, atol=1e-14) or not np.allclose(z, z[:, 0:1], rtol=1e-12, atol=1e-14):
        raise ValueError('r_grid and z_grid must be tensor-product [Z,R] grids')
    if r.shape[0] < 2 or r.shape[1] < 2:
        raise ValueError('r_grid and z_grid need at least two points per axis to define cell area')
    areas = cell_areas(r,z,cell_edges)
    size = r.size
    old = np.zeros(size, dtype=float) if currents_old is None else np.asarray(currents_old, dtype=float)
    if old.shape != (size,) or not np.all(np.isfinite(old)):
        raise ValueError(f'currents_old must have finite shape ({size},)')
    relaxation = float(relax)
    if not np.isfinite(relaxation) or not 0.0 <= relaxation <= 1.0:
        raise ValueError('relax must be a finite scalar in [0,1]')
    if (g_br is None) != (g_bz is None):
        raise ValueError('g_br and g_bz must be provided together')
    green_psi = _matrix('g_psi', g_psi, size, True)
    green_br = _matrix('g_br', g_br, size, False)
    green_bz = _matrix('g_bz', g_bz, size, False)
    density = current_density
    if plasma_mask is not None:
        mask = np.asarray(plasma_mask)
        if mask.dtype != np.dtype(bool) or mask.shape != shape:
            raise ValueError(f'plasma_mask must be boolean with shape {shape}')
        density = np.where(mask, current_density, 0.0)
    raw_currents = density.ravel() * areas.ravel()
    currents = (1.0 - relaxation) * raw_currents + relaxation * old
    psi = (psi0.ravel() + green_psi @ currents).reshape(shape)
    if green_br is None:
        # Differentiate the flux increment, preserving the supplied vacuum field.
        # The field operator uses ascending axes, so orient only for this call.
        reverse_z, reverse_r = z[1,0]<z[0,0], r[0,1]<r[0,0]
        order = (slice(None,None,-1) if reverse_z else slice(None), slice(None,None,-1) if reverse_r else slice(None))
        delta = flux_field_increment(r[order],z[order],(psi-psi0)[order])
        br, bz = br0+delta['B_R'][order], bz0+delta['B_Z'][order]
    else:
        br = (br0.ravel() + green_br @ currents).reshape(shape)
        bz = (bz0.ravel() + green_bz @ currents).reshape(shape)
    return {'psi': psi, 'BR': br, 'BZ': bz, 'j_phi': density, 'initial_picard_current_state': np.zeros(size, dtype=float), 'picard_current_state': currents, 'plasma_currents': raw_currents.reshape(shape)}
__all__ = ['update_anisotropic_picard_flux']
