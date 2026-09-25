"""Maxwellian relative-speed rate average on an explicit velocity mesh.

One leaf recovered from the saved KN1DPy ``make_sigmav`` slice (source anchor
``KN1DPy/make_sigmav.py:13-57``), integrated as
:func:`average_cross_section_over_maxwellian`:

a monoenergetic particle directed along the axial velocity axis is averaged,
through a caller-supplied cross section, against a discretized Maxwellian
target on a cylindrical ``(vr, vx)`` velocity mesh with caller-supplied cell
volumes.  The result is the energy-resolved rate coefficient ``<sigma v>`` in
``m^3/s`` for each supplied particle energy.

**The model, exactly as the saved source defines it.**  With ``T_norm`` the
normalization temperature and ``m_t`` the target mass, the target thermal speed
is ``vth = sqrt(2 e T_norm / (m_t amu))``.  The target Maxwellian on the mesh is
``exp(-(vr^2 + vx^2) T_norm / T_target)``, normalized by the supplied cell
volumes; ``vr`` and ``vx`` are measured in units of ``vth``.  The particle
speed is ``sqrt(2 e E / (m_p amu)) / vth`` along the ``vx`` axis, so the
relative speed is ``sqrt(vr^2 + (vx - v_px)^2)`` and the collision energy is
``0.5 m_p vth^2 v_rel^2 / e`` in eV -- **formed with the particle mass, the
saved source's convention, not the reduced mass**.  The rate is
``vth * sum(volume * sigma(E_rel) * v_rel * f)`` over the mesh.

**The cell volumes need only be proportional to the measure.**  The target
distribution is normalized by the supplied weights before the quadrature, so a
constant rescaling of ``cylindrical_volume`` leaves the rate unchanged; only
the relative cell sizes (the ``vr``-weighted cylindrical measure) enter.

**The constants are the saved source's, frozen.**  ``AMU_KG`` and
``ELEMENTARY_CHARGE_C`` are kept bit-compatible with the saved bundle so the
bounded historical replay reproduces the source arithmetic.  They are
1998-CODATA-era values, not the current best estimates; no conversion is
performed and no other constant is stated.

**Two repairs relative to the saved implementation, both documented.**  The
saved document declares non-finite inputs fail closed and the result finite,
but its implementation checked neither: a ``NaN`` mesh point, mass or
temperature propagated silently into the rate.  This module rejects non-finite
inputs by parameter name and rejects a computed rate that is not representable
in double precision, so the declared contract is true.  The rejection *domain*
is otherwise unchanged: the same shapes, signs and positivity conditions as the
saved implementation, with messages that name the parameter instead of two
generic strings.

Evidence ceiling: this module establishes the discrete relation above, its
agreement with an independent loop-per-energy formulation, its rest-beam and
cold-target analytic limits, its volume-scale invariance, its input and failure
contracts, and -- in the environment-gated replay test -- bounded numerical
agreement with the saved KN1DPy implementation on the compared domain.  The
saved bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.  This module does
not evaluate any physical cross-section model, does not generate the velocity
mesh or its volumes, does not enforce the N1 convention that ``vr`` is a
nonnegative radial axis, and does not converge the quadrature for the caller.
"""
from __future__ import annotations

import numpy as np

from .._validation import required_finite_scalar

__all__ = [
    "AMU_KG",
    "ELEMENTARY_CHARGE_C",
    "average_cross_section_over_maxwellian",
]

# The saved KN1DPy make_sigmav constants, kept bit-compatible for the bounded
# historical replay; see the module docstring.
AMU_KG = 1.6726231e-27
ELEMENTARY_CHARGE_C = 1.602177e-19


def _finite_1d(name, value):
    """Return ``value`` as a float64 one-dimensional array, finite."""
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or not bool(np.all(np.isfinite(array))):
        raise ValueError(f"{name} must be a finite one-dimensional array")
    return array


def _finite_1d_nonnegative(name, value):
    array = _finite_1d(name, value)
    if array.size == 0:
        raise ValueError(f"{name} must be a nonempty one-dimensional array")
    if bool(np.any(array < 0.0)):
        raise ValueError(f"{name} must be nonnegative")
    return array


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
    """Return the Maxwellian relative-speed average ``<sigma v>`` per energy.

    Parameters
    ----------
    particle_energy_ev
        Nonempty one-dimensional nonnegative particle energies in eV; a zero
        entry is a particle at rest and is accepted.
    particle_mass_amu, target_mass_amu
        Positive scalar masses in amu.  The collision energy is formed with
        ``particle_mass_amu``, the saved source's convention, not the reduced
        mass.
    target_temperature_ev, tnorm_ev
        Positive scalar temperatures in eV: the target Maxwellian temperature
        and the mesh normalization temperature.
    vx, vr
        Finite one-dimensional axial and radial velocity axes in units of the
        target thermal speed at ``tnorm_ev``.  No monotonicity or sign
        convention is enforced.
    cylindrical_volume
        Finite strictly positive cell volumes with shape ``(vr.size,
        vx.size)``.  Only their relative sizes enter: the target distribution
        is normalized by these weights, so a constant rescaling leaves the rate
        unchanged.
    cross_section_m2
        Callable mapping the sampled collision-energy array (eV, shape
        ``(energies.size, vr.size, vx.size)``) to finite nonnegative cross
        sections in ``m^2`` with the same shape.

    Returns
    -------
    numpy.ndarray
        Float64 rate coefficients in ``m^3/s`` with shape ``(energies.size,)``.

    Raises
    ------
    ValueError
        If an input leaves the domain stated above, if the callable returns a
        wrong-shape, non-finite or negative array, or if the computed rate is
        not representable in double precision.  Exceptions raised by the
        callable itself propagate unchanged.
    """
    if not callable(cross_section_m2):
        raise ValueError("cross_section_m2 must be callable")
    energies = _finite_1d_nonnegative("particle_energy_ev", particle_energy_ev)
    particle_mass_amu = required_finite_scalar(particle_mass_amu, "particle_mass_amu", positive=True)
    target_temperature_ev = required_finite_scalar(
        target_temperature_ev, "target_temperature_ev", positive=True
    )
    target_mass_amu = required_finite_scalar(target_mass_amu, "target_mass_amu", positive=True)
    tnorm_ev = required_finite_scalar(tnorm_ev, "tnorm_ev", positive=True)
    axial = _finite_1d("vx", vx)
    radial = _finite_1d("vr", vr)
    volume = np.asarray(cylindrical_volume, dtype=float)
    if volume.shape != (radial.size, axial.size):
        raise ValueError("cylindrical_volume must have shape (vr.size, vx.size)")
    if not bool(np.all(np.isfinite(volume))) or bool(np.any(volume <= 0.0)):
        raise ValueError("cylindrical_volume must be finite and strictly positive")

    # The overflow/invalid warnings NumPy would raise here are the conditions
    # the explicit non-finite checks below detect and report as ValueError, so
    # they are suppressed rather than reported twice.
    with np.errstate(over="ignore", invalid="ignore"):
        thermal_speed = np.sqrt(
            2.0 * ELEMENTARY_CHARGE_C * tnorm_ev / (target_mass_amu * AMU_KG)
        )
        target_distribution = np.exp(
            -(radial[:, None] ** 2 + axial[None, :] ** 2) * tnorm_ev / target_temperature_ev
        )
        target_distribution /= np.sum(volume * target_distribution)
        particle_vx = (
            np.sqrt(2.0 * ELEMENTARY_CHARGE_C * energies / (particle_mass_amu * AMU_KG))
            / thermal_speed
        )
        relative_speed = np.sqrt(
            radial[None, :, None] ** 2
            + (axial[None, None, :] - particle_vx[:, None, None]) ** 2
        )
        collision_energy = (
            0.5
            * thermal_speed**2
            * relative_speed**2
            * particle_mass_amu
            * AMU_KG
            / ELEMENTARY_CHARGE_C
        )
        cross_section = np.asarray(cross_section_m2(collision_energy), dtype=float)
        if cross_section.shape != collision_energy.shape:
            raise ValueError(
                "cross_section_m2 must return an array with the collision-energy shape"
            )
        if not bool(np.all(np.isfinite(cross_section))) or bool(np.any(cross_section < 0.0)):
            raise ValueError("cross_section_m2 must return finite nonnegative values")
        rate = thermal_speed * np.sum(
            volume[None, :, :] * cross_section * relative_speed * target_distribution[None, :, :],
            axis=(1, 2),
        )
    if not bool(np.all(np.isfinite(rate))):
        raise ValueError(
            "the Maxwellian relative-speed average is not representable for these finite inputs"
        )
    return rate
