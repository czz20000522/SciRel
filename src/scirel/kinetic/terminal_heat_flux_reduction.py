"""Terminal H2 random and total heat flux on an explicit thermal-speed carrier.

The random-flux field overlaps ``axisymmetric_neutral_moments`` on positive
quadrature weights. This terminal relation also returns total heat flux and
allows zero quadrature cells when each spatial slice has positive density.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_heat_flux"]

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


def reduce_terminal_molecular_heat_flux(
    radial_velocity_normalized,
    axial_velocity_normalized,
    mass_ratio,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Reduce a terminal H2 distribution to random and total heat-flux profiles.

    Parameters
    ----------
    radial_velocity_normalized : array_like, shape (nvr,)
        Finite nonnegative normalized radial velocity nodes; zero nodes are
        allowed and monotonicity is not required. [v/Vth]
    axial_velocity_normalized : array_like, shape (nvx,)
        Finite signed normalized axial velocity nodes; zero nodes are allowed.
        [v/Vth]
    mass_ratio : float
        Positive finite factor multiplying the declared hydrogen mass; H2 uses
        twice this factor. [factor of 1.6726231e-27 kg]
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
    random_heat_flux_profile_w_m2 : ndarray, shape (nx,)
        Centered axial random-energy flux. [W/m^2 on the source distribution normalization]
    total_heat_flux_profile_w_m2 : ndarray, shape (nx,)
        Total axial kinetic-energy flux including convective and random terms.
        [W/m^2 on the source distribution normalization]

    Raises
    ------
    ValueError
        If inputs are non-real, non-finite or misaligned, radial nodes/distribution/
        weights/widths are negative, mass ratio or thermal speed is nonpositive,
        integrated density is nonpositive, or either output is non-finite.

    See Also
    --------
    reduce_axisymmetric_neutral_moments : Full neutral moments and heat flux.
    reduce_terminal_molecular_energy_transfer : Signed transfer-rate reduction.

    Notes
    -----
    The centered axial velocity is formed from density and particle flux, then
    the random heat flux is the centered third moment of the distribution. The
    total flux adds the pressure, longitudinal-stress and convective terms using
    the contract's fixed hydrogen mass and elementary-charge constants. The
    caller owns the terminal distribution and thermal speed; this is a diagnostic
    reduction, not a complete terminal closure or a validation of the incoming
    distribution.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_terminal_molecular_heat_flux
    >>> vr = np.array([0.5, 1.0])
    >>> vx = np.array([-1.0, 0.0, 2.0])
    >>> f = np.ones((2, 3, 1))
    >>> r = reduce_terminal_molecular_heat_flux(vr, vx, 1.0, 5000.0, f, np.array([1.0, 2.0]), np.array([0.5, 0.0, 0.25]))
    >>> assert set(r) == {'random_heat_flux_profile_w_m2', 'total_heat_flux_profile_w_m2'}
    >>> assert r['random_heat_flux_profile_w_m2'].shape == (1,)
    >>> assert all(np.isfinite(value).all() for value in r.values())

    """
    radial_velocity = _real_numeric("radial_velocity_normalized", radial_velocity_normalized)
    axial_velocity = _real_numeric("axial_velocity_normalized", axial_velocity_normalized)
    mass = _real_numeric("mass_ratio", mass_ratio)
    thermal_speed = _real_numeric("thermal_speed_m_s", thermal_speed_m_s)
    distribution = _real_numeric("terminal_distribution", terminal_distribution)
    weight = _real_numeric("cylindrical_weight", cylindrical_weight)
    widths = _real_numeric("dvx", dvx)
    valid = (
        radial_velocity.ndim == 1
        and radial_velocity.size > 0
        and axial_velocity.ndim == 1
        and axial_velocity.size > 0
        and mass.ndim == 0
        and np.isfinite(mass)
        and float(mass) > 0.0
        and thermal_speed.ndim == 0
        and np.isfinite(thermal_speed)
        and float(thermal_speed) > 0.0
        and distribution.ndim == 3
        and distribution.shape
        == (
            radial_velocity.size,
            axial_velocity.size,
            distribution.shape[2],
        )
        and distribution.shape[2] > 0
        and weight.shape == (radial_velocity.size,)
        and widths.shape == (axial_velocity.size,)
        and all(
            np.all(np.isfinite(value))
            for value in (radial_velocity, axial_velocity, distribution, weight, widths)
        )
        and np.all(radial_velocity >= 0.0)
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal heat-flux inputs must be finite, shape-compatible, and physically nonnegative"
        )

    nx = distribution.shape[2]
    thermal = float(thermal_speed)
    molecule_mass = 2.0 * float(mass) * H_MASS_KG
    # Put the spatial axis first.  ``matmul`` still performs the source
    # matrix-vector contraction for every slice, while the outer reduction is
    # expressed once for the whole profile.
    slices = distribution.transpose(2, 0, 1)
    density = np.sum(np.matmul(slices, widths) * weight[None, :], axis=1)
    particle_flux = thermal * np.sum(
        np.matmul(slices, axial_velocity * widths) * weight[None, :], axis=1
    )
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal heat-flux reduction requires strictly positive density")

    mean_velocity = particle_flux / density
    normalized_mean_velocity = mean_velocity / thermal
    # This is an outer broadcast; keep the per-slice reduction order below
    # unchanged while avoiding Python loops over radial and spatial cells.
    random_velocity_squared = (
        radial_velocity[:, None, None] ** 2
        + (axial_velocity[None, :, None] - normalized_mean_velocity[None, None, :]) ** 2
    )

    thermal_squared = thermal * thermal
    thermal_cubed = thermal_squared * thermal
    pressure = np.zeros(nx, dtype=float)
    longitudinal_stress = np.zeros(nx, dtype=float)
    random_heat_flux = np.zeros(nx, dtype=float)
    # The three terminal moments are assembled slice by slice deliberately:
    # this retains the source's reduction order and therefore bitwise
    # invariance when a caller partitions the spatial axis.
    for k in range(nx):
        distribution_slice = slices[k]
        random_slice = random_velocity_squared[:, :, k] * distribution_slice
        centered_axial = axial_velocity - normalized_mean_velocity[k]
        weighted_random_second = np.sum(weight * (random_slice @ widths))
        pressure[k] = molecule_mass * thermal_squared * weighted_random_second / (3.0 * Q_COULOMB)
        weighted_axial_second = np.sum(weight * (distribution_slice @ (widths * centered_axial**2)))
        longitudinal_stress[k] = (
            molecule_mass * thermal_squared * weighted_axial_second / Q_COULOMB - pressure[k]
        )
        random_heat_flux[k] = (
            0.5
            * molecule_mass
            * thermal_cubed
            * np.sum(weight * (random_slice @ (widths * centered_axial)))
        )

    total_heat_flux = (
        (0.5 * density * molecule_mass * mean_velocity * mean_velocity + 2.5 * pressure * Q_COULOMB)
        * mean_velocity
        + Q_COULOMB * longitudinal_stress * mean_velocity
        + random_heat_flux
    )
    outputs = (random_heat_flux, total_heat_flux)
    if not all(np.all(np.isfinite(value)) for value in outputs):
        raise ValueError("terminal heat-flux reduction produced a non-finite profile")
    return {
        "random_heat_flux_profile_w_m2": random_heat_flux,
        "total_heat_flux_profile_w_m2": total_heat_flux,
    }
