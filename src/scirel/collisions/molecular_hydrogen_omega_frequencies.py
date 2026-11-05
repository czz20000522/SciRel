"""Cell-local molecular hydrogen elastic moments and explicitly qualified rates.

The mixed-channel SIG matrices include target quadrature and signed axial
relative speed; the self kernel includes the signed stress projector * 3/8.
Alpha and Omega use normalized velocities and have units m^-1. nu = Vth*Omega
is s^-1. Negative ratios are retained with negative_no_bgk_closure status:
the moment is defined but a nonnegative BGK relaxation cannot represent it.

A central state uses the central perpendicular-minus-parallel second moment.
A target state uses the difference to a supplied number/flow/energy-conserving target,
independently in each spatial cell. There is no global accumulator sentinel.
At a zero denominator the rate is NaN with defined=False, while finite
collision moments are returned. No floor, positivity clipping or equilibrium
linearization is inferred. The original the neutral-transport formulation model is a moment-matched BGK
approximation; finite-grid quadrature does not guarantee exact Maxwell balance.
"""

from ._elastic_moments import reduce_elastic_moments

__all__ = ["assemble_molecular_hydrogen_omega_frequencies"]


def assemble_molecular_hydrogen_omega_frequencies(
    fH2,
    nH2,
    Alpha_H2_P,
    Alpha_H2_H,
    SIG_H2_H2,
    Vr2pidVr,
    dVx,
    vr,
    vx,
    Vth,
    vxi,
    VxH,
    *,
    moment_state="central",
    target_distribution=None,
    H2_P_EL=True,
    H2_H_EL=True,
    H2_H2_EL=True,
):
    """Reduce molecular-hydrogen elastic moments to local Omega and frequency data.

    Parameters
    ----------
    fH2 : real array-like
        Nonnegative density on the normalized cylindrical velocity carrier. [m^-3]
        Shape: ``[nvr, nvx, nx]``. Every value must be finite.
    nH2 : real array-like
        Positive cell number density. [m^-3] Shape: ``[nx]``. It must equal the
        weighted integral of ``fH2`` to within 64 binary64 eps relative roundoff.
    Alpha_H2_P : real array-like
        Signed H2-P mixed momentum field on the same normalization. [m^-1] Shape:
        ``[nvr, nvx, nx]``. Every value must be finite; negative values are kept.
    Alpha_H2_H : real array-like
        Signed H2-H mixed momentum field on the same normalization. [m^-1] Shape:
        ``[nvr, nvx, nx]``. Every value must be finite; negative values are kept.
    SIG_H2_H2 : real array-like
        Self-collision stress matrix in Fortran velocity ordering. [m^2] Shape:
        ``[N, N]`` with ``N=nvr*nvx``. The matrix must be finite and square; signed
        entries are kept.
    Vr2pidVr : real array-like
        Radial quadrature measure. [dimensionless] Shape: ``[nvr]``. The value must
        be finite and strictly positive.
    dVx : real array-like
        Axial quadrature widths. [dimensionless] Shape: ``[nvx]``. The value must
        be finite and strictly positive.
    vr : real array-like
        Radial normalized velocity nodes. [v/Vth] Shape: ``[nvr]``. The value must
        be finite, strictly positive and strictly increasing.
    vx : real array-like
        Axial normalized velocity nodes. [v/Vth] Shape: ``[nvx]``. The value must
        be finite and strictly increasing; it need not cross zero.
    Vth : real scalar
        Shared physical velocity normalization. [m/s] Shape: ``scalar``. The value
        must be finite and strictly positive.
    vxi : real array-like
        H2-P background bulk velocity per cell. [m/s] Shape: ``[nx]``. The value
        must be finite and consistent with the supplied ``Alpha_H2_P``.
    VxH : real array-like
        H2-H background bulk velocity per cell. [m/s] Shape: ``[nx]``. The value
        must be finite and consistent with the supplied ``Alpha_H2_H``.
    moment_state : str or array-like, optional
        Cell state selector, keyword-only. [dimensionless] Shape: ``scalar or
        [nx]``. The default is ``'central'``; accepted values are ``'central'`` and
        ``'target'``.
    target_distribution : real array-like or None, optional
        Number-conserving target distribution, keyword-only. [m^-3] Shape:
        ``[nvr, nvx, nx]`` or ``None``. The default is ``None``. It is required for
        every target-state cell and must conserve density, mean velocity and total
        kinetic energy there.
    H2_P_EL, H2_H_EL, H2_H2_EL : bool, optional
        Channel-enable flags, keyword-only. [dimensionless] Shape: ``scalar``. The
        defaults are ``True``. A disabled channel returns exactly zero moment and
        frequency with status ``'disabled'``.

    Returns
    -------
    VxH2 : numpy.ndarray
        Physical H2 bulk velocity recovered from ``fH2``. [m/s] Shape: ``[nx]``.
    Wperp_paraH2, central_stress : numpy.ndarray
        Perpendicular-minus-parallel stress and central stress. [(v/Vth)^2] Shape:
        ``[nx]``. Both are finite and may be negative or zero.
    Omega_H2_P, Omega_H2_H, Omega_H2_H2 : numpy.ndarray
        Signed normalized moment ratios per channel. [m^-1] Shape: ``[nx]``. An
        enabled zero denominator is represented by NaN and ``defined_* = False``.
    nu_H2_P, nu_H2_H, nu_H2_H2 : numpy.ndarray
        Physical channel frequencies, ``Vth * Omega``. [s^-1] Shape: ``[nx]``.
        They share their channel's definedness; a negative value is retained but
        is not a valid nonnegative BGK relaxation.
    moment_H2_P, moment_H2_H, moment_H2_H2 : numpy.ndarray
        Retained collision-moment numerators. [m^-1] Shape: ``[nx]``. These remain
        finite even where a frequency is undefined.
    moment_rate_H2_P, moment_rate_H2_H : numpy.ndarray
        Signed physical mixed-channel acceleration. [m/s^2] Shape: ``[nx]``.
    moment_rate_H2_H2 : numpy.ndarray
        Signed self-collision stress rate. [m^2/s^3] Shape: ``[nx]``.
    defined_H2_P, defined_H2_H, defined_H2_H2 : numpy.ndarray
        Per-channel definedness masks. [dimensionless] Shape: ``[nx]``. A disabled
        channel is defined; an enabled zero-denominator channel is not.
    status_H2_P, status_H2_H, status_H2_H2 : numpy.ndarray
        Per-channel status strings. [dimensionless] Shape: ``[nx]``. Values are
        ``'disabled'``, ``'finite_nonnegative'``,
        ``'negative_no_bgk_closure'`` or ``'undefined_zero_denominator'``.
    Omega_EL : numpy.ndarray
        Sum of the three channel Omegas. [m^-1] Shape: ``[nx]``. Undefined enabled
        terms propagate as NaN.
    nu_EL : numpy.ndarray
        Physical total frequency, ``Vth * Omega_EL``. [s^-1] Shape: ``[nx]``.
    defined_EL : numpy.ndarray
        Conjunction of the three channel masks. [dimensionless] Shape: ``[nx]``.

    Raises
    ------
    ValueError
        If carrier shapes are inconsistent, data are non-real or non-finite,
        distributions are negative, density or weights are nonpositive, axes are
        not increasing, channel flags are not booleans, target invariants fail, or
        a required moment or frequency is not representable as a finite float64.

    See Also
    --------
    assemble_molecular_hydrogen_collision_matrices : Builds the self-collision
        matrix accepted here.
    assemble_atomic_hydrogen_omega_frequencies : The atomic-H counterpart.
    reduce_elastic_moments : Shared private reduction kernel.

    Notes
    -----
    This is a cell-local, moment-matched BGK reduction, not the full Boltzmann
    collision operator. For a central state the stress denominator is the central
    ``vr**2 - 2*(vx-u)**2`` moment. For a target state it is the difference between
    ``fH2`` and a target distribution that conserves particle number, mean
    velocity and total kinetic energy in the same cell. Mixed-channel denominators
    are normalized background-flow differences. No floor or positivity clipping
    is applied: a zero denominator yields NaN with ``defined = False`` while the
    finite moment is retained. Negative ratios are kept with
    ``negative_no_bgk_closure``. Grid convergence remains the caller's
    responsibility.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import assemble_molecular_hydrogen_collision_matrices, assemble_molecular_hydrogen_omega_frequencies
    >>> vr = np.array([0.5, 1.0])
    >>> vx = np.array([-1.0, 0.0, 1.0])
    >>> wr = np.array([1.0, 2.0])
    >>> dx = np.ones(3)
    >>> w = wr[:, None] * dx
    >>> f = np.exp(-vr[:, None]**2 - (vx[None, :] - 0.2)**2)
    >>> f *= 2e17 / np.sum(w * f)
    >>> bg = np.exp(-vr[:, None]**2 - vx[None, :]**2)
    >>> bg *= 3e17 / np.sum(w * bg)
    >>> s = assemble_molecular_hydrogen_collision_matrices(vr, vx, wr, dx, 1.0, mu=2.0, n_theta=32)
    >>> vth = float(np.sqrt(s['Vth2'][0]))
    >>> ub = np.array([vth * np.sum(w * bg * vx) / np.sum(w * bg)])
    >>> alphas = [(s[k] @ bg.ravel(order='F')).reshape(f.shape, order='F')[:, :, None] for k in ['SIG_H2_P', 'SIG_H2_H']]
    >>> r = assemble_molecular_hydrogen_omega_frequencies(f[:, :, None], np.array([2e17]), *alphas, s['SIG_H2_H2'], wr, dx, vr, vx, vth, ub, ub)
    >>> assert np.isfinite(r['moment_H2_P']).all()
    >>> assert r['defined_H2_P'].all()
    >>> np.testing.assert_allclose(r['nu_H2_P'], vth * r['Omega_H2_P'], rtol=1e-14)
    """
    return reduce_elastic_moments(
        fH2,
        nH2,
        Alpha_H2_P,
        Alpha_H2_H,
        SIG_H2_H2,
        Vr2pidVr,
        dVx,
        vr,
        vx,
        Vth,
        vxi,
        VxH,
        moment_state=moment_state,
        target_distribution=target_distribution,
        enabled=(H2_P_EL, H2_H_EL, H2_H2_EL),
        names=("H2_P", "H2_H", "H2_H2"),
        flow_name="VxH2",
        stress_name="Wperp_paraH2",
        mass_fractions=(1 / 3, 1 / 3),
    )
