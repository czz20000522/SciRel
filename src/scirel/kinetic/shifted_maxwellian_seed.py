"""Build a normalized shifted-Maxwellian seed on an explicit cylindrical velocity mesh."""

from __future__ import annotations

import numpy as np

from .._validation import required_finite_scalar, required_integer_scalar

__all__ = ["build_shifted_maxwellian_seed"]

AMU_KG = 1.6726231e-27
ELEMENTARY_CHARGE_C = 1.602177e-19


def _real_array(name, value):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def _positive_scalar(name, value):
    return required_finite_scalar(_real_array(name, value), name, positive=True)


def build_shifted_maxwellian_seed(
    *,
    vr,
    vx,
    tnorm_ev,
    shifted_vx_m_s,
    temperature_ev,
    mass_amu,
    molecule_count,
    cylindrical_volume,
):
    """Return the normalized exponential seed in ``create_shifted_maxwellian``.

    Parameters
    ----------
    vr : real array_like, shape [nvr]
        Finite nonempty one-dimensional normalized radial-speed mesh
        [v/vth (caller's normalized unit)].
    vx : real array_like, shape [nvx]
        Finite nonempty one-dimensional normalized axial-velocity mesh
        [v/vth (caller's normalized unit)].
    tnorm_ev : real scalar
        Positive finite normalization temperature [eV]; fixes the thermal
        speed converting shifts into mesh units.
    shifted_vx_m_s : real array_like, shape [n_shifts]
        Finite nonempty one-dimensional axial shifts [m/s].
    temperature_ev : real array_like, shape [n_shifts]
        Per-shift temperatures [eV], same shape as the shifts; every entry is
        finite and strictly positive.
    mass_amu : real scalar
        Positive finite mass multiplier [multiples of 1.6726231e-27 kg],
        relative to the saved hydrogen mass despite the historical name.
    molecule_count : integer scalar
        Integer scalar exactly ``1`` for atomic hydrogen or ``2`` for
        molecular hydrogen [dimensionless]; scales the exponent.
    cylindrical_volume : real array_like, shape [nvr,nvx]
        Finite strictly positive cell volumes [normalized velocity-space
        measure], shape ``(vr.size, vx.size)``.

    Returns
    -------
    distribution : ndarray of float64, shape [nvr,nvx,n_shifts]
        Normalized exponential seed [normalized distribution density], finite
        and strictly positive; ``sum(volume * distribution) == 1`` per shift.
    thermal_speed_m_s : float
        Thermal speed ``sqrt(2 e T_norm / (m m_H))`` [m/s].
    exponent : ndarray of float64, shape [nvr,nvx,n_shifts]
        Raw exponent per mesh node and shift [dimensionless]. It is finite and
        nonpositive for accepted inputs; a zero entry marks the peak that the
        seed floors to ``exp(-80)``.

    Raises
    ------
    ValueError
        If an input leaves the domain stated above, including empty shift
        arrays, or the shapes are inconsistent.

    See Also
    --------
    scirel.kinetic.make_cylindrical_velocity_quadrature : Build the required cell volumes.
    scirel.collisions.average_cross_section_over_maxwellian : Consume the seed in a rate average.

    Notes
    -----
    The mesh axes are normalized by the thermal speed
    ``sqrt(2 e T_norm / (m m_H))``. The seed is normalized by the supplied
    cylindrical cell volumes; the strict-interior clamp ``exp(-80)`` is applied
    before normalization. ``molecule_count`` is interpreted as the exponent
    multiplier, and no external distribution or collision model is inferred.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import build_shifted_maxwellian_seed, make_cylindrical_velocity_quadrature
    >>> from scirel.collisions import average_cross_section_over_maxwellian
    >>> vr = np.array([0.5, 1.5])
    >>> vx = np.array([-1.5, -0.5, 0.5, 1.5])
    >>> quadrature = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    >>> volume = quadrature['volume']
    >>> seed = build_shifted_maxwellian_seed(
    ...     vr=vr, vx=vx, tnorm_ev=20.0,
    ...     shifted_vx_m_s=np.array([0.0]),
    ...     temperature_ev=np.array([10.0]),
    ...     mass_amu=2.0, molecule_count=1,
    ...     cylindrical_volume=volume,
    ... )
    >>> assert seed['distribution'].shape == (2, 4, 1)
    >>> assert np.sum(volume * seed['distribution'][:, :, 0]) == 1.0
    >>> assert np.all(np.isfinite(seed['distribution']))
    >>> rate = average_cross_section_over_maxwellian(
    ...     particle_energy_ev=np.array([0.0, 10.0]),
    ...     particle_mass_amu=1.0,
    ...     target_temperature_ev=10.0,
    ...     target_mass_amu=2.0,
    ...     vx=vx, vr=vr, tnorm_ev=20.0,
    ...     cylindrical_volume=volume,
    ...     cross_section_m2=lambda energy: np.full_like(energy, 3.0e-20),
    ... )
    >>> assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)
    >>> try:
    ...     build_shifted_maxwellian_seed(
    ...         vr=vr, vx=vx, tnorm_ev=20.0,
    ...         shifted_vx_m_s=np.array([0.0]),
    ...         temperature_ev=np.array([10.0]),
    ...         mass_amu=2.0, molecule_count=3,
    ...         cylindrical_volume=volume,
    ...     )
    ... except ValueError as error:
    ...     assert 'physical' in str(error)
    ... else:
    ...     raise AssertionError('molecule_count 3 must be rejected')
    """
    radial = _real_array("vr", vr)
    axial = _real_array("vx", vx)
    shifts = _real_array("shifted_vx_m_s", shifted_vx_m_s)
    temperatures = _real_array("temperature_ev", temperature_ev)
    volume = _real_array("cylindrical_volume", cylindrical_volume)
    if (
        radial.ndim != 1
        or axial.ndim != 1
        or shifts.ndim != 1
        or temperatures.shape != shifts.shape
        or not radial.size
        or not axial.size
        or not shifts.size
        or volume.shape != (radial.size, axial.size)
    ):
        raise ValueError(
            "vr, vx, shifted_vx_m_s, temperature_ev and cylindrical_volume "
            "must have compatible nonempty shapes"
        )
    for name, array in (
        ("vr", radial),
        ("vx", axial),
        ("shifted_vx_m_s", shifts),
        ("temperature_ev", temperatures),
        ("cylindrical_volume", volume),
    ):
        if not bool(np.all(np.isfinite(array))):
            raise ValueError(f"{name} must be finite")
    if bool(np.any(temperatures <= 0.0)):
        raise ValueError("temperature_ev must be strictly positive")
    if bool(np.any(volume <= 0.0)):
        raise ValueError("cylindrical_volume must be strictly positive")
    tnorm_ev = _positive_scalar("tnorm_ev", tnorm_ev)
    mass_amu = _positive_scalar("mass_amu", mass_amu)
    molecule_count = required_integer_scalar(molecule_count, "molecule_count", minimum=1)
    if molecule_count > 2:
        raise ValueError("physical input molecule_count must be 1 or 2")
    # Extreme-but-finite inputs can overflow the thermal speed or the raw
    # exponent; the overflow warnings are the conditions the explicit
    # representability checks below report as ValueError.
    with np.errstate(over="ignore", invalid="ignore"):
        thermal_speed = np.sqrt(2.0 * ELEMENTARY_CHARGE_C * tnorm_ev / (mass_amu * AMU_KG))
    if not np.isfinite(thermal_speed) or thermal_speed <= 0.0:
        raise ValueError("the thermal speed is not representable for these finite inputs")
    with np.errstate(over="ignore", invalid="ignore"):
        argument = (
            -(
                radial[:, None, None] ** 2
                + (axial[None, :, None] - shifts[None, None, :] / thermal_speed) ** 2
            )
            * molecule_count
            * tnorm_ev
            / temperatures[None, None, :]
        )
    if not bool(np.all(np.isfinite(argument))):
        raise ValueError("the seed exponent is not representable for these finite inputs")
    with np.errstate(over="ignore", invalid="ignore"):
        seed = np.exp(np.where(np.logical_and(-80.0 < argument, argument < 0.0), argument, -80.0))
        seed /= np.sum(volume[:, :, None] * seed, axis=(0, 1), keepdims=True)
    # Extreme-but-finite volumes can make the normalization denominator
    # underflow (the divided distribution overflows to infinity) or overflow
    # (the divided distribution collapses to exact zeros); either way the
    # finite, strictly-positive contract is violated and the call fails closed.
    if not bool(np.all(np.isfinite(seed))) or not bool(np.all(seed > 0.0)):
        raise ValueError(
            "the normalized seed distribution is not representable for these finite inputs"
        )
    return {
        "distribution": seed,
        "thermal_speed_m_s": thermal_speed,
        "exponent": argument,
    }
