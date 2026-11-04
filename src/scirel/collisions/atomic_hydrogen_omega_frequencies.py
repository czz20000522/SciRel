"""Cell-local atomic hydrogen elastic moments and explicitly qualified rates.

The mixed-channel SIG matrices include target quadrature and signed axial
relative speed; the self kernel includes the signed stress projector / 8.
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
    """Reduce physical nonnegative velocity distributions on a common grid.

    Parameters
    ----------
    fH : ndarray, shape (nvr, nvx, nx)
        Density per dimensionless cylindrical velocity volume, m^-3.
    nH : ndarray, shape (nx,)
        Positive number density, m^-3; equals the weighted integral of f to
        64 binary64 eps relative summation roundoff (not a physical floor).
    Alpha_H_P, Alpha_H_H2 : ndarray, shape (nvr, nvx, nx)
        Signed mixed momentum Alpha fields, m^-1, from physical backgrounds
        on the same velocity normalization; partner flows must match them.
    SIG_H_H : ndarray, shape (N, N)
        Self stress matrix, m^2, column-weighted, Fortran velocity ordering.
    Vr2pidVr, dVx : ndarray
        Positive dimensionless cylindrical radial and axial quadrature weights.
    vr, vx : ndarray
        Increasing dimensionless nodes; vr positive, vx need not cross zero.
    Vth : float
        Shared positive velocity normalization, m/s.
    vxi, vxH2 : ndarray, shape (nx,)
        Background bulk velocities in m/s, consistent with supplied Alpha.
    moment_state : str or ndarray, shape (nx,)
        'central' (default) or 'target', chosen explicitly per cell.
    target_distribution : ndarray or None
        Required for target cells. Nonnegative aligned distribution conserving
        density, bulk flow and kinetic energy; its stress is subtracted from f's central stress.
    H_P_EL, H_H2_EL, H_H_EL : bool
        Enabled channels. Disabled channels have exactly zero rate/moment and
        status 'disabled'; enabled undefined channels remain distinguishable.

    Returns
    -------
    dict
        VxH in m/s; Wperp_paraH and central_stress dimensionless second moments.
        For each channel: Omega (m^-1), nu (s^-1), moment (m^-1 with normalized
        velocity powers), moment_rate (mixed m/s^2, self m^2/s^3), defined mask
        and status. Omega_EL/nu_EL propagate any enabled undefined NaN; their
        defined_EL mask is the conjunction. Ratios do not identify a unique
        linear response at 0/0 without a specified perturbation family.

    Raises
    ------
    ValueError
        Invalid shapes, nonphysical density/distribution/weights, inconsistent
        target invariants, nonboolean flags or unrepresentable finite results.
    """
    return reduce_elastic_moments(
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
