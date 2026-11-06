"""Cell-local atomic hydrogen elastic moments and explicitly qualified rates.

The mixed-channel SIG matrices include target quadrature and signed axial
relative speed; the self kernel includes the signed stress projector * 3/8.
Alpha and Omega use normalized velocities and have units m^-1. nu = Vth*Omega
is s^-1. Negative ratios remain negative_no_bgk_closure, and a finite
denominator at or below the declared binary64 conditioning boundary is
near_equilibrium_ill_conditioned_denominator; neither is a usable nonnegative
BGK rate. A finite enabled result that is not representable raises
FloatingPointError.

A central state uses the central perpendicular-minus-parallel second moment.
A target state uses the difference to a supplied number/flow/energy-conserving target,
independently in each spatial cell. There is no global accumulator sentinel.
At or below that boundary, including exact zero, the rate is NaN with
defined=False, while finite collision moments are returned. No floor,
positivity clipping, absolute value or equilibrium linearization is inferred.
The original the neutral-transport formulation model is a moment-matched BGK
approximation; finite-grid quadrature does not guarantee exact Maxwell balance.
"""

from scirel._result import Result

from ._elastic_moments import reduce_elastic_moments

__all__ = ["assemble_atomic_hydrogen_omega_frequencies"]


def assemble_atomic_hydrogen_omega_frequencies(
    fH,
    nH,
    Alpha_H_P,
    Alpha_H_H2,
    SIG_H_H,
    Vr2pidVr,
    dVx,
    vr,
    vx,
    Vth,
    vxi,
    vxH2,
    *,
    moment_state="central",
    target_distribution=None,
    H_P_EL=True,
    H_H2_EL=True,
    H_H_EL=True,
):
    """Reduce atomic-hydrogen elastic moments to local Omega and frequency data.

    Parameters
    ----------
    fH : real array-like
        Nonnegative density on the normalized cylindrical velocity carrier. [m^-3]
        Shape: ``[nvr, nvx, nx]``. Every value must be finite.
    nH : real array-like
        Positive cell number density. [m^-3] Shape: ``[nx]``. It must equal the
        weighted integral of ``fH`` to within 64 binary64 eps relative roundoff.
    Alpha_H_P : real array-like
        Signed H-P mixed momentum field on the same normalization. [m^-1] Shape:
        ``[nvr, nvx, nx]``. Every value must be finite; negative values are kept.
    Alpha_H_H2 : real array-like
        Signed H-H2 mixed momentum field on the same normalization. [m^-1] Shape:
        ``[nvr, nvx, nx]``. Every value must be finite; negative values are kept.
    SIG_H_H : real array-like
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
        H-P background bulk velocity per cell. [m/s] Shape: ``[nx]``. The value
        must be finite and consistent with the supplied ``Alpha_H_P``.
    vxH2 : real array-like
        H-H2 background bulk velocity per cell. [m/s] Shape: ``[nx]``. The value
        must be finite and consistent with the supplied ``Alpha_H_H2``.
    moment_state : str or array-like, optional
        Cell state selector, keyword-only. [dimensionless] Shape: ``scalar or
        [nx]``. The default is ``'central'``; accepted values are ``'central'`` and
        ``'target'``.
    target_distribution : real array-like or None, optional
        Number-conserving target distribution, keyword-only. [m^-3] Shape:
        ``[nvr, nvx, nx]`` or ``None``. The default is ``None``. It is required for
        every target-state cell and must conserve density, mean velocity and total
        kinetic energy there.
    H_P_EL, H_H2_EL, H_H_EL : bool, optional
        Channel-enable flags, keyword-only. [dimensionless] Shape: ``scalar``. The
        defaults are ``True``. A disabled channel returns exactly zero moment and
        frequency with status ``'disabled'``.

    Returns
    -------
    VxH : numpy.ndarray
        Physical H bulk velocity recovered from ``fH``. [m/s] Shape: ``[nx]``.
    Wperp_paraH, central_stress : numpy.ndarray
        Perpendicular-minus-parallel stress and central stress. [(v/Vth)^2] Shape:
        ``[nx]``. Both are finite and may be negative or zero.
    Omega_H_P, Omega_H_H2, Omega_H_H : numpy.ndarray
        Signed normalized moment ratios per channel. [m^-1] Shape: ``[nx]``. An
        enabled zero denominator is represented by NaN and ``defined_* = False``.
    nu_H_P, nu_H_H2, nu_H_H : numpy.ndarray
        Physical channel frequencies, ``Vth * Omega``. [s^-1] Shape: ``[nx]``.
        They share their channel's definedness; a negative value is retained but
        is not a valid nonnegative BGK relaxation.
    moment_H_P, moment_H_H2, moment_H_H : numpy.ndarray
        Retained collision-moment numerators. [m^-1] Shape: ``[nx]``. These remain
        finite even where a frequency is undefined.
    moment_rate_H_P, moment_rate_H_H2 : numpy.ndarray
        Signed physical mixed-channel acceleration. [m/s^2] Shape: ``[nx]``.
    moment_rate_H_H : numpy.ndarray
        Signed self-collision stress rate. [m^2/s^3] Shape: ``[nx]``.
    defined_H_P, defined_H_H2, defined_H_H : numpy.ndarray
        Per-channel definedness masks. [dimensionless] Shape: ``[nx]``. A disabled
        channel is defined; an enabled zero-denominator channel is not.
    status_H_P, status_H_H2, status_H_H : numpy.ndarray
        Per-channel status strings. [dimensionless] Shape: ``[nx]``. Values are
        ``'disabled'``, ``'finite_nonnegative'``,
        ``'negative_no_bgk_closure'``,
        ``'near_equilibrium_ill_conditioned_denominator'`` or
        ``'nonfinite_failure'``. Only ``'finite_nonnegative'`` is a usable
        nonnegative BGK classification.
    Omega_EL : numpy.ndarray
        Heterogeneous diagnostic sum of the three channel rates. [m^-1] Shape:
        ``[nx]``. This is not a single physical total collision frequency;
        undefined enabled terms propagate as NaN.
    nu_EL : numpy.ndarray
        Heterogeneous diagnostic sum, ``Vth * Omega_EL``. [s^-1] Shape: ``[nx]``.
        This is not a single physical total collision frequency.
    defined_EL : numpy.ndarray
        Conjunction of the three channel masks. [dimensionless] Shape: ``[nx]``.

    The complete result is returned as one ``scirel._result.Result`` mapping. No nested
    mapping or recursive wrapping is introduced, and non-colliding fields also support
    attribute access.

    Raises
    ------
    ValueError
        If carrier shapes are inconsistent, data are non-real or non-finite,
        distributions are negative, density or weights are nonpositive, axes are
        not increasing, channel flags are not booleans, or target invariants fail.
    FloatingPointError
        If a collision moment, moment rate, finite enabled frequency or finite
        diagnostic aggregate derived from finite inputs is not representable as
        float64. Non-representable values are neither returned as inf/nan nor
        silently treated as truncated.

    See Also
    --------
    assemble_atomic_hydrogen_collision_matrices : Builds the self-collision
        matrix accepted here.
    assemble_molecular_hydrogen_omega_frequencies : The molecular-H2 counterpart.
    reduce_elastic_moments : Shared private reduction kernel.

    Notes
    -----
    This is a cell-local, moment-matched BGK reduction, not the full Boltzmann
    collision operator. For a central state the stress denominator is the central
    ``vr**2 - 2*(vx-u)**2`` moment. For a target state it is the difference between
    ``fH`` and a target distribution that conserves particle number, mean velocity
    and total kinetic energy in the same cell. Mixed-channel denominators are
    normalized background-flow differences. No floor or positivity clipping is
    applied. A finite denominator with
    ``abs(d) <= 8 * eps * max(vx.max() - vx.min(), 1)`` and an exact zero
    denominator yield NaN with ``defined = False`` and the
    ``near_equilibrium_ill_conditioned_denominator`` status while the finite
    moment is retained. Negative ratios are kept with
    ``negative_no_bgk_closure``. ``Omega_EL`` is a heterogeneous diagnostic sum,
    not a single physical total collision frequency. Grid convergence remains the
    caller's responsibility.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.collisions import assemble_atomic_hydrogen_collision_matrices, assemble_atomic_hydrogen_omega_frequencies
    >>> vr = np.array([0.5, 1.0])
    >>> vx = np.array([-1.0, 0.0, 1.0])
    >>> wr = np.array([1.0, 2.0])
    >>> dx = np.ones(3)
    >>> w = wr[:, None] * dx
    >>> f = np.exp(-vr[:, None]**2 - (vx[None, :] - 0.2)**2)
    >>> f *= 2e17 / np.sum(w * f)
    >>> bg = np.exp(-vr[:, None]**2 - vx[None, :]**2)
    >>> bg *= 3e17 / np.sum(w * bg)
    >>> s = assemble_atomic_hydrogen_collision_matrices(vr, vx, wr, dx, 1.0, mu=2.0, n_theta=32)
    >>> vth = float(np.sqrt(s['Vth2'][0]))
    >>> ub = np.array([vth * np.sum(w * bg * vx) / np.sum(w * bg)])
    >>> alphas = [(s[k] @ bg.ravel(order='F')).reshape(f.shape, order='F')[:, :, None] for k in ['SIG_H_P', 'SIG_H_H2']]
    >>> r = assemble_atomic_hydrogen_omega_frequencies(f[:, :, None], np.array([2e17]), *alphas, s['SIG_H_H'], wr, dx, vr, vx, vth, ub, ub)
    >>> assert isinstance(r, Result)
    >>> assert r.Omega_H_P is r['Omega_H_P']
    >>> assert np.isfinite(r['moment_H_P']).all()
    >>> assert r['defined_H_P'].all()
    >>> np.testing.assert_allclose(r['nu_H_P'], vth * r['Omega_H_P'], rtol=1e-14)
    """
    result = reduce_elastic_moments(
        fH,
        nH,
        Alpha_H_P,
        Alpha_H_H2,
        SIG_H_H,
        Vr2pidVr,
        dVx,
        vr,
        vx,
        Vth,
        vxi,
        vxH2,
        moment_state=moment_state,
        target_distribution=target_distribution,
        enabled=(H_P_EL, H_H2_EL, H_H_EL),
        names=("H_P", "H_H2", "H_H"),
        flow_name="VxH",
        stress_name="Wperp_paraH",
        mass_fractions=(0.5, 2 / 3),
    )
    return Result(result)
