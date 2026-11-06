"""Terminal H2 pressure and temperature on an explicit thermal-speed carrier.

This two-moment diagnostic retains the saved terminal interface and accepts
zero quadrature cells when each spatial slice has positive density. The
positive-weight relation overlaps the pressure and temperature fields of
``axisymmetric_neutral_moments`` without requiring its higher moments.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_pressure_temperature"]

H_MASS_KG = 1.6726231e-27
Q_COULOMB = 1.602177e-19


def _real_numeric(name, value):
    try:
        if not isinstance(value, np.ndarray) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def reduce_terminal_molecular_pressure_temperature(
    vr,
    vx,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Reduce a terminal H2 distribution to centered pressure and temperature.

    Parameters
    ----------
    vr : array_like, shape (nvr,)
        Finite nonnegative normalized radial velocity nodes; zero nodes are
        allowed and monotonicity is not required. [v/Vth]
    vx : array_like, shape (nvx,)
        Finite signed normalized axial velocity nodes; zero nodes are allowed.
        [v/Vth]
    mass_ratio : float
        Positive finite factor multiplying the frozen hydrogen mass; H2 uses twice
        this factor. [factor of 1.6726231e-27 kg]
    thermal_speed_m_s : float
        Positive finite caller-supplied H2 thermal speed. [m/s]
    terminal_distribution : array_like, shape (nvr, nvx, nx)
        Finite nonnegative nonempty terminal distribution. [source-normalized distribution; no implicit conversion]
    cylindrical_weight : array_like, shape (nvr,)
        Finite nonnegative radial integration measure; zero cells are allowed when
        integrated density remains positive. [source-normalized radial-area measure]
    dvx : array_like, shape (nvx,)
        Finite nonnegative normalized axial widths; zero cells are allowed when
        integrated density remains positive. [normalized axial-speed increment]

    Returns
    -------
    pressure_profile_ev_m3 : ndarray, shape (nx,)
        Centered one-third-trace H2 pressure profile. [eV/m^3 on the source distribution normalization]
    temperature_profile_ev : ndarray, shape (nx,)
        Pressure divided by positive integrated density. [eV]

    Raises
    ------
    ValueError
        If inputs are non-real, non-finite or malformed, radial nodes/distribution/
        weights/widths are negative, mass ratio or thermal speed is nonpositive,
        integrated density is nonpositive, or pressure/temperature is non-finite or
        negative.

    See Also
    --------
    reduce_axisymmetric_neutral_moments : Full neutral moment reduction.
    reduce_terminal_molecular_heat_flux : Random and total terminal heat flux.

    Notes
    -----
    The reduction first forms density and axial particle flux, derives the mean
    flow, and evaluates the centered squared normalized speed
    ``vr**2 + (vx - flux/(density*Vth))**2``. Pressure is the weighted one-third
    trace of the centered second moment with the specified H2 mass and eV
    conversion; temperature is pressure divided by density. Zero quadrature
    weights are allowed but every integrated density must remain strictly
    positive. The caller owns the terminal distribution and thermal speed; this
    does not establish a complete terminal closure.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_terminal_molecular_pressure_temperature
    >>> vr = np.array([0.5, 1.0])
    >>> vx = np.array([-1.0, 0.0, 2.0])
    >>> f = np.ones((2, 3, 1))
    >>> r = reduce_terminal_molecular_pressure_temperature(vr, vx, 1.0, 5000.0, f, np.array([1.0, 2.0]), np.array([0.5, 0.0, 0.25]))
    >>> assert set(r) == {'pressure_profile_ev_m3', 'temperature_profile_ev'}
    >>> assert r['pressure_profile_ev_m3'].shape == (1,)
    >>> assert all(np.isfinite(value).all() for value in r.values())

    """
    radial_velocity = _real_numeric("vr", vr)
    velocity = _real_numeric("vx", vx)
    mass = _real_numeric("mass_ratio", mass_ratio)
    thermal_speed = _real_numeric("thermal_speed_m_s", thermal_speed_m_s)
    distribution = _real_numeric("terminal_distribution", terminal_distribution)
    weight = _real_numeric("cylindrical_weight", cylindrical_weight)
    widths = _real_numeric("dvx", dvx)
    valid = (
        radial_velocity.ndim == 1
        and radial_velocity.size > 0
        and velocity.ndim == 1
        and velocity.size > 0
        and mass.ndim == 0
        and np.isfinite(mass)
        and float(mass) > 0.0
        and thermal_speed.ndim == 0
        and np.isfinite(thermal_speed)
        and float(thermal_speed) > 0.0
        and distribution.ndim == 3
        and distribution.shape[0] > 0
        and distribution.shape[1] > 0
        and distribution.shape[2] > 0
        and distribution.shape == (radial_velocity.size, velocity.size, distribution.shape[2])
        and weight.shape == (radial_velocity.size,)
        and widths.shape == (velocity.size,)
        and all(
            np.all(np.isfinite(value))
            for value in (radial_velocity, velocity, distribution, weight, widths)
        )
        and np.all(radial_velocity >= 0.0)
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal pressure inputs must be finite, shape-compatible, and physically nonnegative"
        )

    slices = distribution.transpose(2, 0, 1)
    density = np.sum(np.matmul(slices, widths) * weight[None, :], axis=1)
    flux = float(thermal_speed) * np.sum(
        np.matmul(slices, velocity * widths) * weight[None, :], axis=1
    )
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal pressure reduction requires strictly positive density")

    mean_velocity = flux / density
    normalized_mean_velocity = mean_velocity / float(thermal_speed)
    # This is an outer broadcast; keep the per-slice reduction order below
    # unchanged while avoiding Python loops over radial and spatial cells.
    random_velocity_squared = (
        radial_velocity[:, None, None] ** 2
        + (velocity[None, :, None] - normalized_mean_velocity[None, None, :]) ** 2
    )

    thermal_speed_squared = float(thermal_speed) * float(thermal_speed)
    random_slices = random_velocity_squared.transpose(2, 0, 1) * slices
    weighted_random_second = np.sum(np.matmul(random_slices, widths) * weight[None, :], axis=1)
    pressure = (
        (2.0 * float(mass) * H_MASS_KG)
        * thermal_speed_squared
        * weighted_random_second
        / (3.0 * Q_COULOMB)
    )
    if not np.all(np.isfinite(pressure)) or np.any(pressure < 0.0):
        raise ValueError("terminal pressure reduction produced an invalid pressure profile")
    temperature = pressure / density
    if not np.all(np.isfinite(temperature)) or np.any(temperature < 0.0):
        raise ValueError("terminal pressure reduction produced an invalid temperature profile")
    return {
        "pressure_profile_ev_m3": pressure,
        "temperature_profile_ev": temperature,
    }
