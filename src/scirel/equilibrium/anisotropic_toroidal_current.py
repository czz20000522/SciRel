"""Toroidal current obtained from a gyrotropic pressure balance."""

from __future__ import annotations

from scirel._result import Result

from .anisotropic_force_balance import compute_anisotropic_force_balance

__all__ = ["compute_anisotropic_toroidal_current"]


def compute_anisotropic_toroidal_current(r_grid, z_grid, br, bz, p_parallel, p_perp):
    """Split the toroidal current into isotropic and curvature terms.

    Parameters
    ----------
    r_grid : finite real array-like
        Cylindrical radius mesh [m] Shape [N_Z,N_R]. Rectilinear, nonnegative R, strictly increasing radial axis and at least three columns; same shape as other arrays.
    z_grid : finite real array-like
        Axial coordinate mesh [m] Shape [N_Z,N_R]. Rectilinear, strictly increasing axial axis and at least three rows; same shape as other arrays.
    br : finite real array-like
        Radial poloidal magnetic-field component [T] Shape [N_Z,N_R]. Exact grid shape; zero or tiny fields follow the dependency's numerical convention, not a physical validity gate.
    bz : finite real array-like
        Axial poloidal magnetic-field component [T] Shape [N_Z,N_R]. Exact grid shape and co-located with br.
    p_parallel : finite real array-like
        Pressure parallel to the poloidal field [Pa] Shape [N_Z,N_R]. Exact grid shape and nonnegative; scalar broadcasting is not performed.
    p_perp : finite real array-like
        Pressure perpendicular to the poloidal field [Pa] Shape [N_Z,N_R]. Exact grid shape and nonnegative; also supplies both pressures in the isotropic comparison.

    Returns
    -------
    j_phi : float64
        Full gyrotropic toroidal current-density projection [A/m^2] Shape [N_Z,N_R]. Equals gradp_term plus anisotropy_curvature_term by construction; zero at an R=0 axis column.
    gradp_term : float64
        Toroidal current from the isotropic p_perp comparison [A/m^2] Shape [N_Z,N_R]. Exactly the dependency's J_phi with both pressure inputs set to p_perp; not an independently evaluated gradient.
    anisotropy_curvature_term : float64
        Difference between full and isotropic-comparison current [A/m^2] Shape [N_Z,N_R]. Computed as j_phi - gradp_term; zero for equal pressures up to arithmetic error.
    B : float64
        Magnitude of the supplied poloidal field [T] Shape [N_Z,N_R]. Taken from the full force-balance evaluation.
    force_diagnostics : dict
        Plain-dict full corrected tensor-force result, including raw and resolved compatibility diagnostics [mixed SI] Shape mapping. This nested value is not a Result.

    The complete result is returned as one ``scirel._result.Result`` mapping. No nested
    mapping is wrapped, and every field also supports attribute access.

    Raises
    ------
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    compute_anisotropic_force_balance : Compute force and current diagnostics.

    Notes
    -----
    Evaluate the maintained gyrotropic force-balance projection twice: once with supplied p_parallel and p_perp and once with p_parallel=p_perp. The latter J_phi is gradp_term; anisotropy_curvature_term is the full J_phi minus gradp_term. The decomposition is defined by this discrete difference, not an independently discretized curvature formula.

    axisymmetric gyrotropic pressure tensor and perpendicular current projection

    Both magnetic components and pressures refer to the same R-Z nodes and use T and Pa, respectively.

    The parallel/perpendicular distinction is meaningful for the caller's gyrotropic model.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.equilibrium import compute_anisotropic_toroidal_current
    >>> r, z = np.meshgrid(np.linspace(0.2, 0.5, 5), np.linspace(-0.2, 0.2, 4))
    >>> p = 3.0 + r
    >>> result = compute_anisotropic_toroidal_current(r, z, np.zeros_like(r), np.full_like(r, 2.0), p, p)
    >>> assert isinstance(result, Result)
    >>> assert result.j_phi is result['j_phi']
    >>> assert type(result.force_diagnostics) is dict
    >>> np.testing.assert_allclose(result.j_phi, 0.5)
    >>> np.testing.assert_allclose(result.gradp_term, 0.5)
    >>> np.testing.assert_allclose(result.anisotropy_curvature_term, 0.0, atol=1e-12)
    """
    full = compute_anisotropic_force_balance(r_grid, z_grid, br, bz, p_parallel, p_perp)
    isotropic = compute_anisotropic_force_balance(r_grid, z_grid, br, bz, p_perp, p_perp)
    gradp = isotropic["J_phi"]
    return Result(
        {
            "j_phi": full["J_phi"],
            "gradp_term": gradp,
            "anisotropy_curvature_term": full["J_phi"] - gradp,
            "B": full["B"],
            "force_diagnostics": full,
        }
    )
