"""Maxwellian relative-speed rate average on an explicit velocity mesh.

One leaf recovered from the saved the neutral-transport formulation ``make_sigmav`` slice, integrated as
:func:`average_cross_section_over_maxwellian`:

a monoenergetic particle directed along the axial velocity axis is averaged,
through a caller-supplied cross section, against a discretized Maxwellian
target on a cylindrical ``(vr, vx)`` velocity mesh with caller-supplied cell
volumes.  The result is the energy-resolved rate coefficient ``<sigma v>`` in
``m^3/s`` for each supplied particle energy.

**The model, exactly as the saved source defines it.**  With ``T_norm`` the
normalization temperature and ``m_t`` the target mass, the target thermal speed
is ``vth = sqrt(2 e T_norm / (m_t m_H))``.  Here ``m_H`` is the saved
hydrogen-mass constant, not the standard atomic mass unit.  The target Maxwellian is
``exp(-(vr^2 + vx^2) T_norm / T_target)``, normalized by the supplied cell
volumes; ``vr`` and ``vx`` are measured in units of ``vth``.  The particle
speed is ``sqrt(2 e E / (m_p m_H)) / vth`` along the ``vx`` axis, so the
relative speed is ``sqrt(vr^2 + (vx - v_px)^2)`` and the collision energy is
``0.5 m_p m_H vth^2 v_rel^2 / e`` in eV -- **formed with the particle mass, the
saved source's convention, not the reduced mass**.  The rate is
``vth * sum(volume * sigma(E_rel) * v_rel * f)`` over the mesh.

**The cell volumes need only be proportional to the measure.**  The target
distribution is normalized by the supplied weights before the quadrature, so a
constant rescaling of ``cylindrical_volume`` leaves the rate unchanged; only
the relative cell sizes (the ``vr``-weighted cylindrical measure) enter.

**The constants are the saved source's, frozen.**  ``AMU_KG`` and
``ELEMENTARY_CHARGE_C`` are kept bit-compatible with the saved bundle so the
bounded historical replay reproduces the source arithmetic.  They are
historical values, not the current best estimates; no conversion is
performed and no other constant is stated.

**Numerical repairs relative to the saved implementation, all documented.**  The
saved document declares non-finite inputs fail closed and the result finite,
but its implementation checked neither: a ``NaN`` mesh point, mass or
temperature propagated silently into the rate.  This module rejects non-finite
inputs by parameter name and rejects a computed rate that is not representable
in double precision, so the declared contract is true.  Additionally, extreme
but finite inputs can overflow the sampled collision-energy array; the saved
implementation handed that non-finite array to the caller's cross-section
callable before any check, so this module rejects it before the callable is
invoked.  Boolean, string and complex array inputs are additionally rejected
as non-real, and numeric-string scalar masses or temperatures now raise a
parameter-named ValueError.  The accepted real-valued shapes, signs and
positivity conditions are preserved, with messages that name the quantity.
The normalized mesh probabilities and the final positive sum are evaluated in
logarithms, so overflowing normalization sums or individually underflowing
probabilities do not silently erase representable rates.  An empty target mesh
or a positive rate that rounds to zero is rejected rather than returned as zero.

Evidence ceiling: this module establishes the discrete relation above, its
agreement with an independent loop-per-energy formulation, its rest-beam and
cold-target analytic limits, its volume-scale invariance, its input and failure
contracts, and -- in a separate intake replay -- bounded numerical
agreement with the saved the neutral-transport formulation implementation on the compared domain.  The
saved bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.  This module does
not evaluate any physical cross-section model, does not generate the velocity
mesh or its volumes, does not enforce the N1 convention that ``vr`` is a
nonnegative radial axis, and does not converge the quadrature for the caller.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
from scipy.special import logsumexp

from .._validation import required_finite_scalar

__all__ = [
    "AMU_KG",
    "ELEMENTARY_CHARGE_C",
    "average_cross_section_over_maxwellian",
]

# The saved the neutral-transport formulation make_sigmav constants, kept bit-compatible for the bounded
# historical replay; see the module docstring. AMU_KG is a historical name
# for the saved hydrogen mass, not the standard atomic mass unit.
AMU_KG = 1.6726231e-27
ELEMENTARY_CHARGE_C = 1.602177e-19


def _finite_1d(name, value):
    """Return ``value`` as a float64 one-dimensional array, finite."""
    array = _real_array(name, value)
    if array.ndim != 1 or not bool(np.all(np.isfinite(array))):
        raise ValueError(f"{name} must be a finite one-dimensional array")
    return array


def _real_array(name, value):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def _positive_scalar(name, value):
    raw = _real_array(name, value)
    if raw.ndim != 0:
        raise ValueError(f"{name} must be a finite scalar")
    return required_finite_scalar(raw, name, positive=True)


def _finite_1d_nonnegative(name, value):
    array = _finite_1d(name, value)
    if array.size == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional array")
    if bool(np.any(array < 0.0)):
        raise ValueError(f"{name} must be nonnegative")
    return array


def _shifted_square_exponent(axis, tnorm_ev, target_temperature_ev):
    """Evaluate (v**2 - v0**2)*T_norm/T_target before forming a common offset.

    v0 is the smallest absolute coordinate on this axis. Factor the square
    difference as (abs(v)-v0)*(abs(v)+v0); accumulate binary exponents separately
    so neither a square nor a temperature ratio has to be representable alone.
    """
    absolute = np.abs(axis)
    reference = np.min(absolute)
    difference = absolute - reference
    nonzero = difference > 0.0
    exponent = np.zeros_like(absolute)
    if np.any(nonzero):
        delta_mantissa, delta_power = np.frexp(difference[nonzero])
        axis_mantissa, axis_power = np.frexp(absolute[nonzero])
        reference_mantissa, reference_power = np.frexp(reference)
        # Scale the sum by each coordinate's binary exponent before adding.
        # reference <= abs(v), so a term too small for this sum is negligible;
        # the separate difference above still retains neighboring coordinates.
        sum_mantissa = axis_mantissa + np.ldexp(reference_mantissa, reference_power - axis_power)
        norm_mantissa, norm_power = np.frexp(tnorm_ev)
        temperature_mantissa, temperature_power = np.frexp(target_temperature_ev)
        mantissa = delta_mantissa * sum_mantissa * norm_mantissa / temperature_mantissa
        power = delta_power + axis_power + norm_power - temperature_power
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            exponent[nonzero] = np.ldexp(mantissa, power)
        if np.any(~np.isfinite(exponent[nonzero])) or np.any(exponent[nonzero] == 0.0):
            raise ValueError("target Maxwellian exponent differences are not representable")
    return exponent


def _mesh_log_probabilities(radial, axial, volume, tnorm_ev, target_temperature_ev):
    """Return log(volume * shape / sum(volume * shape)), without materializing it."""
    if volume.size == 0:
        raise ValueError("target Maxwellian is not representable on an empty mesh")
    radial_exponent = _shifted_square_exponent(radial, tnorm_ev, target_temperature_ev)
    axial_exponent = _shifted_square_exponent(axial, tnorm_ev, target_temperature_ev)
    with np.errstate(over="ignore", invalid="ignore"):
        exponent = radial_exponent[:, None] + axial_exponent[None, :]
    if not np.all(np.isfinite(exponent)):
        raise ValueError("target Maxwellian is not representable")
    # volume = mantissa * 2**power. Remove a common binary scale before taking
    # logarithms; volume / max(volume) could underflow a weight whose Gaussian
    # factor compensates for its size. Common Gaussian square terms have
    # already canceled independently on both axes, before they can hide a
    # probability difference belonging to the other axis.
    mantissa, power = np.frexp(volume)
    log_volume = np.log(mantissa) + (power - np.max(power)) * np.log(2.0)
    log_weight = log_volume - exponent
    log_weight -= np.max(log_weight)
    return log_weight - logsumexp(log_weight)


def _kinematic_scale(numerators, denominators=(), *, square_root=False, binary_power=0):
    """Keep a nonnegative product/ratio as a mantissa and a separate binary scale."""
    mantissa, power = 1.0, np.asarray(binary_power, dtype=np.int64)
    for factor in numerators:
        part, exponent = np.frexp(factor)
        mantissa = mantissa * part
        power = power + exponent
    for factor in denominators:
        part, exponent = np.frexp(factor)
        mantissa = mantissa / part
        power = power - exponent
    if square_root:
        mantissa = np.sqrt(np.ldexp(mantissa, power % 2))
        power = power // 2
    mantissa, adjustment = np.frexp(mantissa)
    return mantissa, power + adjustment


def _fraction_scale(value):
    """Round a rational's significand, without rounding its magnitude to zero."""
    if not value:
        return 0.0, 0
    power = abs(value.numerator).bit_length() - value.denominator.bit_length()
    scaled = value / (1 << power) if power >= 0 else value * (1 << -power)
    mantissa, adjustment = np.frexp(float(scaled))
    return mantissa, power + adjustment


def _relative_kinematics(energies, radial, axial, tnorm_ev, particle_mass_amu, target_mass_amu):
    """Stable equivalent projectile-mass kinematics; no reduced-mass conversion."""
    beam_mantissa, beam_power = _kinematic_scale(
        (energies, target_mass_amu),
        (tnorm_ev, particle_mass_amu),
        square_root=True,
    )
    axial_mantissa, axial_power = np.frexp(axial)
    # A zero's frexp exponent is arbitrary: it must not force a tiny nonzero
    # component down to that exponent. All alignment arithmetic stays scaled.
    common_power = np.maximum(
        np.where(axial_mantissa != 0.0, axial_power, beam_power[:, None]),
        np.where(beam_mantissa[:, None] != 0.0, beam_power[:, None], axial_power),
    )
    scaled_axial = np.ldexp(axial_mantissa, axial_power - common_power)
    scaled_beam = np.ldexp(beam_mantissa[:, None], beam_power[:, None] - common_power)
    delta_mantissa, delta_adjustment = np.frexp(scaled_axial - scaled_beam)
    delta_power = common_power + delta_adjustment
    close = (scaled_axial > 0.0) & (
        np.abs(scaled_axial - scaled_beam) <= 0.0625 * np.maximum(scaled_axial, scaled_beam)
    )
    # x-sqrt(b) = (x*x-b)/(x+sqrt(b)). Only the potentially cancelling
    # energy/axial pairs need exact binary-input numerators; the radial axis
    # is not part of this loop. The branch limits cancellation in the direct
    # subtraction; it is an arithmetic choice, not a physical speed cutoff.
    axial_fractions = {}
    for energy_index in np.flatnonzero(np.any(close, axis=1)):
        beam_square = (
            Fraction(float(energies[energy_index]))
            * Fraction(target_mass_amu)
            / (Fraction(tnorm_ev) * Fraction(particle_mass_amu))
        )
        power = int(beam_power[energy_index])
        beam = Fraction(float(beam_mantissa[energy_index]))
        beam = beam * (1 << power) if power >= 0 else beam / (1 << -power)
        for axial_index in np.flatnonzero(close[energy_index]):
            coordinate = axial_fractions.setdefault(
                axial_index, Fraction(float(axial[axial_index]))
            )
            denominator = coordinate + beam
            difference = (coordinate**2 - beam_square) / denominator
            delta_mantissa[energy_index, axial_index], delta_power[energy_index, axial_index] = (
                _fraction_scale(difference)
            )
    # Compute energy from the component square sum, not hypot(...)**2:
    # rounding the norm and squaring again can cross a callback threshold.
    radial_mantissa, radial_power = np.frexp(radial[None, :, None])
    delta_mantissa = delta_mantissa[:, None, :]
    delta_power = delta_power[:, None, :]
    norm_power = np.maximum(
        np.where(radial_mantissa != 0.0, radial_power, delta_power),
        np.where(delta_mantissa != 0.0, delta_power, radial_power),
    )
    radial_fraction = np.ldexp(radial_mantissa, radial_power - norm_power)
    axial_fraction = np.ldexp(delta_mantissa, delta_power - norm_power)
    speed_mantissa, speed_adjustment = np.frexp(np.hypot(radial_fraction, axial_fraction))
    square_sum = radial_fraction**2 + axial_fraction**2
    energy_mantissa, energy_power = _kinematic_scale(
        (tnorm_ev, particle_mass_amu, square_sum),
        (target_mass_amu,),
        binary_power=2 * norm_power,
    )
    collision_energy = np.ldexp(energy_mantissa, energy_power)
    if np.any(~np.isfinite(collision_energy)) or np.any(
        (energy_mantissa > 0.0) & (collision_energy == 0.0)
    ):
        raise ValueError("the sampled collision energies are not representable")
    return (speed_mantissa, norm_power + speed_adjustment), collision_energy


def average_cross_section_over_maxwellian(
    *,
    particle_energy_ev,
    particle_mass_amu,
    target_temperature_ev,
    target_mass_amu,
    vx,
    vr,
    tnorm_ev,
    cylindrical_volume,
    cross_section_m2,
):
    """Average a caller-supplied cross section over a Maxwellian target mesh.

    Parameters
    ----------
    particle_energy_ev : real array-like
        Energies of the axial monoenergetic particle. [eV] Shape: ``[ne]``. The
        value must be nonempty, finite, one-dimensional and nonnegative; zero is a
        particle at rest.
    particle_mass_amu : real scalar
        Projectile mass factor used in the collision energy. [multiples of
        1.6726231e-27 kg] Shape: ``scalar``. The value must be finite and strictly
        positive. The historical name does not imply standard atomic-mass units and
        the collision energy uses this mass rather than a reduced mass.
    target_temperature_ev : real scalar
        Maxwellian target temperature. [eV] Shape: ``scalar``. The value must be
        finite and strictly positive.
    target_mass_amu : real scalar
        Target mass factor used to set the thermal speed. [multiples of
        1.6726231e-27 kg] Shape: ``scalar``. The value must be finite and strictly
        positive.
    vx : real array-like
        Axial velocity mesh. [v/vth (dimensionless, target thermal speed at
        tnorm_ev)] Shape: ``[nvx]``. The value must be finite and one-dimensional;
        monotonicity and sign are not enforced.
    vr : real array-like
        Radial velocity mesh. [v/vth (dimensionless, target thermal speed at
        tnorm_ev)] Shape: ``[nvr]``. The value must be finite and one-dimensional;
        monotonicity and nonnegative-radial convention are not enforced.
    tnorm_ev : real scalar
        Mesh normalization temperature. [eV] Shape: ``scalar``. The value must be
        finite and strictly positive.
    cylindrical_volume : real array-like
        Relative velocity-space cell measure. [normalized velocity-space measure]
        Shape: ``[nvr, nvx]``. The value must be finite and strictly positive. Only
        relative sizes matter because the target distribution is normalized by
        these weights.
    cross_section_m2 : callable
        Cross-section law evaluated at each sampled collision energy. [m^2] The
        callable maps an array of shape ``[ne, nvr, nvx]`` in eV to a finite,
        nonnegative real array of the same shape.

    Returns
    -------
    rate_m3_s : numpy.ndarray
        Energy-resolved Maxwellian rate coefficient on the supplied mesh. [m^3/s]
        Shape: ``[ne]``. Every returned value is finite and nonnegative.

    Raises
    ------
    ValueError
        If an input is not real numeric, finite, correctly shaped or within its
        stated sign or positivity domain; if the target mesh cannot be normalized,
        sampled collision energies or the computed rate are not representable
        (including a positive rate rounded to zero); if ``cross_section_m2`` is not
        callable; or if the callable returns a wrong-shape, non-finite or negative
        array. Exceptions raised by the callable itself propagate unchanged.

    See Also
    --------
    evaluate_atomic_hydrogen_charge_exchange_cross_section : A compatible
        cross-section source for this averaging port.
    evaluate_atomic_hydrogen_elastic_cross_section : A compatible elastic
        cross-section source.
    evaluate_molecular_hydrogen_charge_exchange_cross_section : A compatible
        molecular-H2 cross-section source.

    Notes
    -----
    With ``vth = sqrt(2 * e * tnorm_ev / (target_mass_amu * m_H))``, the target
    density is ``exp(-(vr**2 + vx**2) * tnorm_ev / target_temperature_ev)``
    normalized by ``cylindrical_volume``. The particle speed is
    ``sqrt(2 * e * particle_energy_ev / (particle_mass_amu * m_H)) / vth`` along
    ``vx``. The rate is the volume sum of ``vth * sigma * v_rel * f``. The
    historical constants are ``m_H=1.6726231e-27`` kg and
    ``e=1.602177e-19`` C. They are frozen source values, not current CODATA
    constants. The function does not generate the mesh, validate its quadrature
    convergence, or supply a physical cross-section model; those remain caller
    responsibilities.

    Numerically, use log probabilities ``log(p) = log(volume) - q - log(Z)``,
    where ``q = (vr**2 + vx**2) * tnorm_ev / target_temperature_ev`` and
    ``Z = sum(volume * exp(-q))``. Before combining axes, cancel the common
    squared coordinate on each axis using ``(abs(v)-v0)*(abs(v)+v0)``, where
    ``v0=min(abs(v))`` on that axis. Binary mantissas and exponents keep the
    temperature-scaled differences from overflowing or underflowing silently.
    Common volume and Gaussian scales cancel without first forming the large
    total ``q``. Unrepresentable differences or their sum raise ValueError.
    Evaluate ``vth * sum(p * sigma * v_rel)`` in logarithms through the final
    sum with separate binary powers for the cross section and speeds, retaining
    contributions whose small probabilities are compensated by large cross
    sections. Reconstruct the result with a binary scale rather than taking
    the exponential of a large rate logarithm. An empty mesh or a positive
    result rounded to zero
    raises ValueError; exact zero cross sections or relative speeds still give
    an exact zero rate.

    Cancel the common constants before evaluating the normalized beam speed:
    ``u = sqrt(E * m_target / (T_norm * m_particle))``. When positive ``vx``
    and ``u`` differ by at most one sixteenth of their maximum, evaluate
    ``vx-u = (vx**2-u**2)/(vx+u)`` with an exact binary-input rational numerator
    and a rounded positive denominator. This branch avoids subtracting rounded
    square roots; it runs only over close energy/axial-coordinate pairs. Other
    pairs use scaled subtraction. Keep the thermal speed, normalized beam and
    relative norm as binary mantissas and powers through the weighted sum.
    Form ``E_rel = T_norm * (m_particle/m_target) * (vr**2 + (vx-u)**2)``
    from scaled components, before rounding the norm. Only collision energies
    passed to the callback and the final rate must be materialized as float64;
    an unrepresentable intermediate speed alone does not require rejection.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import average_cross_section_over_maxwellian
    >>> dvr = 3.5 / 24
    >>> dvx = 7.0 / 36
    >>> vr = (np.arange(24) + 0.5) * dvr
    >>> vx = (np.arange(36) + 0.5) * dvx - 3.5
    >>> vth = np.sqrt(2.0 * 1.602177e-19 * 20.0 / (2.0 * 1.6726231e-27))
    >>> volume = np.outer(vr * dvr, np.full(36, dvx)) * vth ** 3
    >>> sigma_const = lambda energy: np.full_like(energy, 3.0e-20)
    >>> rate = average_cross_section_over_maxwellian(
    ...     particle_energy_ev=np.array([0.0, 10.0, 100.0]),
    ...     particle_mass_amu=1.0,
    ...     target_temperature_ev=10.0,
    ...     target_mass_amu=2.0,
    ...     vx=vx,
    ...     vr=vr,
    ...     tnorm_ev=20.0,
    ...     cylindrical_volume=volume,
    ...     cross_section_m2=sigma_const,
    ... )
    >>> assert rate.shape == (3,) and rate.dtype == np.float64
    >>> assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)
    >>> scaled = average_cross_section_over_maxwellian(
    ...     particle_energy_ev=np.array([0.0, 10.0, 100.0]),
    ...     particle_mass_amu=1.0,
    ...     target_temperature_ev=10.0,
    ...     target_mass_amu=2.0,
    ...     vx=vx,
    ...     vr=vr,
    ...     tnorm_ev=20.0,
    ...     cylindrical_volume=volume * 7.5,
    ...     cross_section_m2=sigma_const,
    ... )
    >>> assert np.allclose(scaled, rate, rtol=1e-14)
    >>> bad_vx = vx.copy()
    >>> bad_vx[3] = np.nan
    >>> try:
    ...     average_cross_section_over_maxwellian(
    ...         particle_energy_ev=np.array([10.0]),
    ...         particle_mass_amu=1.0,
    ...         target_temperature_ev=10.0,
    ...         target_mass_amu=2.0,
    ...         vx=bad_vx,
    ...         vr=vr,
    ...         tnorm_ev=20.0,
    ...         cylindrical_volume=volume,
    ...         cross_section_m2=sigma_const,
    ...     )
    ... except ValueError as error:
    ...     assert 'vx' in str(error)
    ... else:
    ...     raise AssertionError('a non-finite mesh point must be rejected')
    >>> try:
    ...     average_cross_section_over_maxwellian(
    ...         particle_energy_ev=np.array([10.0]),
    ...         particle_mass_amu=1.0,
    ...         target_temperature_ev=10.0,
    ...         target_mass_amu=2.0,
    ...         vx=vx,
    ...         vr=vr,
    ...         tnorm_ev=20.0,
    ...         cylindrical_volume=volume,
    ...         cross_section_m2=lambda energy: np.full_like(energy, 1.0e305),
    ...     )
    ... except ValueError as error:
    ...     assert 'not representable' in str(error)
    ... else:
    ...     raise AssertionError('a non-representable rate must be rejected')
    """
    if not callable(cross_section_m2):
        raise ValueError("cross_section_m2 must be callable")
    energies = _finite_1d_nonnegative("particle_energy_ev", particle_energy_ev)
    particle_mass_amu = _positive_scalar("particle_mass_amu", particle_mass_amu)
    target_temperature_ev = _positive_scalar("target_temperature_ev", target_temperature_ev)
    target_mass_amu = _positive_scalar("target_mass_amu", target_mass_amu)
    tnorm_ev = _positive_scalar("tnorm_ev", tnorm_ev)
    axial = _finite_1d("vx", vx)
    radial = _finite_1d("vr", vr)
    volume = _real_array("cylindrical_volume", cylindrical_volume)
    if volume.shape != (radial.size, axial.size):
        raise ValueError("cylindrical_volume must have shape (vr.size, vx.size)")
    if not bool(np.all(np.isfinite(volume))) or bool(np.any(volume <= 0.0)):
        raise ValueError("cylindrical_volume must be finite and strictly positive")

    # The overflow/invalid warnings NumPy would raise here are the conditions
    # the explicit non-finite checks below detect and report as ValueError, so
    # they are suppressed rather than reported twice.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        thermal_mantissa, thermal_power = _kinematic_scale(
            (2.0, ELEMENTARY_CHARGE_C, tnorm_ev),
            (target_mass_amu, AMU_KG),
            square_root=True,
        )
        log_probability = _mesh_log_probabilities(
            radial, axial, volume, tnorm_ev, target_temperature_ev
        )
        (speed_mantissa, speed_power), collision_energy = _relative_kinematics(
            energies, radial, axial, tnorm_ev, particle_mass_amu, target_mass_amu
        )
        # Extreme-but-finite inputs can overflow this intermediate array.  The
        # failure contract requires rejecting it here, before the caller's
        # cross-section callable observes a value the asset never declared.
        if not bool(np.all(np.isfinite(collision_energy))) or bool(
            np.any((speed_mantissa > 0.0) & (collision_energy == 0.0))
        ):
            raise ValueError(
                "the sampled collision energies are not representable for these finite inputs"
            )
    # A caller's arithmetic policy belongs to its callback. Restrict suppression
    # to the internal calculations, so callback exceptions propagate unchanged.
    cross_section = _real_array("cross_section_m2", cross_section_m2(collision_energy))
    if cross_section.shape != collision_energy.shape:
        raise ValueError("cross_section_m2 must return an array with the collision-energy shape")
    if not bool(np.all(np.isfinite(cross_section))) or bool(np.any(cross_section < 0.0)):
        raise ValueError("cross_section_m2 must return finite nonnegative values")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        # Do not materialize p, sigma*v_rel or volume*sigma: any one may
        # underflow/overflow even when the complete positive average is finite.
        positive_cell = (cross_section > 0.0) & (speed_mantissa > 0.0)
        positive_rate = np.any(positive_cell, axis=(1, 2))
        sigma_mantissa, sigma_power = np.frexp(cross_section)
        cell_power = sigma_power + speed_power + thermal_power
        common_power = np.max(
            np.where(positive_cell, cell_power, np.iinfo(np.int32).min), axis=(1, 2)
        )
        common_power = np.where(positive_rate, common_power, 0)
        log_integrand = (
            log_probability[None, :, :]
            + np.log(sigma_mantissa)
            + np.log(speed_mantissa)
            + np.log(thermal_mantissa)
            + (cell_power - common_power[:, None, None]) * np.log(2.0)
        )
        log_sum = logsumexp(log_integrand, axis=(1, 2))
        # Reconstruct with an exact binary scale. exp(log(rate)) would lose
        # relative accuracy for a very large rate, while exp(log_sum) alone
        # could underflow before a positive common_power restores its range.
        shift = np.floor(log_sum[positive_rate] / np.log(2.0))
        final_power = common_power[positive_rate] + shift
        if np.any(~np.isfinite(final_power)) or np.any(
            (final_power < -1075) | (final_power > 1024)
        ):
            raise ValueError(
                "the Maxwellian relative-speed average is not representable for these finite inputs"
            )
        rate = np.zeros(energies.shape, dtype=float)
        rate[positive_rate] = np.ldexp(
            np.exp(log_sum[positive_rate] - shift * np.log(2.0)), final_power.astype(int)
        )
    if not bool(np.all(np.isfinite(rate))) or bool(np.any(positive_rate & (rate == 0.0))):
        raise ValueError(
            "the Maxwellian relative-speed average is not representable for these finite inputs"
        )
    return rate
