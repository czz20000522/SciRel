"""Axisymmetric toroidal current from gyrotropic pressure balance."""
from .anisotropic_force_balance import compute_anisotropic_force_balance

def compute_anisotropic_toroidal_current(r_grid, z_grid, br, bz, p_parallel, p_perp):
    """Project ``div(P) = J x B`` and expose isotropic/anisotropic parts."""
    full = compute_anisotropic_force_balance(r_grid, z_grid, br, bz, p_parallel, p_perp, active_mask=None)
    isotropic = compute_anisotropic_force_balance(r_grid, z_grid, br, bz, p_perp, p_perp, active_mask=None)
    gradp_term = isotropic['J_phi']
    j_phi = full['J_phi']
    return {'j_phi': j_phi, 'gradp_term': gradp_term, 'anisotropy_curvature_term': j_phi - gradp_term, 'B': full['B'], 'force_diagnostics': full}
__all__ = ['compute_anisotropic_toroidal_current']
