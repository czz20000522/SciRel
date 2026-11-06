"""Terminal H2 axial flux and velocity on an explicit thermal-speed carrier.

This narrow diagnostic shares its positive-weight flux relation with
``axisymmetric_neutral_moments``. It keeps the saved terminal interface, which
accepts the thermal speed directly and allows zero quadrature cells without
requiring radial nodes or computing higher moments.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_flux_velocity"]


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


def _contract_profile(slices, radial_weight, axial_weight):
    """Return one radial contraction for every spatial slice."""
    return np.sum(np.matmul(slices, axial_weight) * radial_weight[None, :], axis=1)


def reduce_terminal_molecular_flux_velocity(
    vx,
    thermal_speed_m_s,
    terminal_distribution,
    cylindrical_weight,
    dvx,
):
    """Reduce a terminal H2 distribution to axial flux and mean velocity.

    Parameters
    ----------
    vx : array_like, shape (nvx,)
        Finite one-dimensional normalized axial velocity nodes; zero values are
        allowed and no monotonicity gate is imposed. [v/Vth]
    thermal_speed_m_s : float
        Positive finite H2 thermal speed used by the axial-flux integral. [m/s]
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
    flux_profile_m2_s : ndarray, shape (nx,)
        Signed terminal H2 axial particle flux. [source-discrete distribution measure times m/s]
    mean_velocity_profile_m_s : ndarray, shape (nx,)
        Terminal H2 mean axial velocity, flux divided by positive integrated
        density. [m/s]

    Raises
    ------
    ValueError
        If inputs are non-real, non-finite or malformed, distribution/weights/widths
        are negative, thermal speed is nonpositive, integrated density is
        nonpositive, or density, flux or mean velocity is non-finite.

    See Also
    --------
    reduce_axisymmetric_neutral_moments : Full neutral moments including stresses.
    reduce_terminal_molecular_pressure_temperature : Terminal pressure and temperature.

    Notes
    -----
    The density and axial flux use the declared per-slice matrix-vector and
    radial reduction order. Individual quadrature cells may have zero weight or
    width, but every spatial cell must have strictly positive integrated density.
    The caller supplies the thermal-speed carrier directly; this narrow diagnostic
    does not compute pressures, stresses or a complete terminal closure.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_terminal_molecular_flux_velocity
    >>> vx = np.array([-1., 0., 2.])
    >>> f = np.ones((2, 3, 1))
    >>> r = reduce_terminal_molecular_flux_velocity(vx, 5000., f, np.array([1., 2.]), np.array([0.5, 0., 0.25]))
    >>> assert set(r) == {'flux_profile_m2_s', 'mean_velocity_profile_m_s'}
    >>> assert r['flux_profile_m2_s'].shape == (1,)
    >>> assert all(np.isfinite(value).all() for value in r.values())

    """
    velocity = _real_numeric("vx", vx)
    thermal_speed = _real_numeric("thermal_speed_m_s", thermal_speed_m_s)
    distribution = _real_numeric("terminal_distribution", terminal_distribution)
    weight = _real_numeric("cylindrical_weight", cylindrical_weight)
    widths = _real_numeric("dvx", dvx)
    valid = (
        velocity.ndim == 1
        and velocity.size > 0
        and thermal_speed.ndim == 0
        and np.isfinite(thermal_speed)
        and float(thermal_speed) > 0.0
        and distribution.ndim == 3
        and all(size > 0 for size in distribution.shape)
        and velocity.shape == (distribution.shape[1],)
        and weight.shape == (distribution.shape[0],)
        and widths.shape == (distribution.shape[1],)
        and all(np.all(np.isfinite(value)) for value in (velocity, distribution, weight, widths))
        and np.all(distribution >= 0.0)
        and np.all(weight >= 0.0)
        and np.all(widths >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal flux inputs must be finite, shape-compatible, and physically nonnegative"
        )

    # Move the spatial axis to the leading position so each k-slice keeps the
    # original matrix-vector reduction order while NumPy handles the batch.
    # The explicit per-slice order is part of the saved terminal contract:
    # reductions remain ``weight * (slice @ widths)`` followed by the radial
    # sum, rather than a three-axis reduction with a different accumulation
    # order.
    slices = distribution.transpose(2, 0, 1)
    density = _contract_profile(slices, weight, widths)
    flux = float(thermal_speed) * _contract_profile(slices, weight, velocity * widths)
    if not np.all(np.isfinite(density)) or np.any(density <= 0.0):
        raise ValueError("terminal flux reduction requires strictly positive density")
    if not np.all(np.isfinite(flux)):
        raise ValueError("terminal flux reduction produced a nonfinite flux profile")
    mean_velocity = flux / density
    if not np.all(np.isfinite(mean_velocity)):
        raise ValueError("terminal flux reduction produced a nonfinite mean velocity profile")
    return {
        "flux_profile_m2_s": flux,
        "mean_velocity_profile_m_s": mean_velocity,
    }
