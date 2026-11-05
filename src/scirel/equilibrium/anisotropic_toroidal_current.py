"""Toroidal current obtained from a gyrotropic pressure balance."""

from __future__ import annotations

from .anisotropic_force_balance import compute_anisotropic_force_balance

__all__ = ["compute_anisotropic_toroidal_current"]


def compute_anisotropic_toroidal_current(r_grid, z_grid, br, bz, p_parallel, p_perp):
    """Split the toroidal current into isotropic and curvature terms."""
    full = compute_anisotropic_force_balance(r_grid, z_grid, br, bz, p_parallel, p_perp)
    isotropic = compute_anisotropic_force_balance(r_grid, z_grid, br, bz, p_perp, p_perp)
    gradp = isotropic["J_phi"]
    return {
        "j_phi": full["J_phi"],
        "gradp_term": gradp,
        "anisotropy_curvature_term": full["J_phi"] - gradp,
        "B": full["B"],
        "force_diagnostics": full,
    }
