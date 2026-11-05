"""Assemble finite gas, electron, and hot-ion pressure fields."""

import numpy as np


def assemble_frank_egedal_pressure(
    psi,
    radial_shape,
    hot_parallel_shape,
    hot_perpendicular_shape,
    hot_density_shape,
    *,
    hot_pressure_scale=1.0,
    gas_dynamic_pressure=0.0,
    gas_dynamic_density=None,
    hot_density_scale=None,
    electron_temperature=None,
):
    """Assemble the source-order Frank--Egedal pressure state.

    Parameters
    ----------
    psi : array_like, shape (N_Z, N_R)
        Finite, nonempty flux-coordinate field in [Wb] by historical source
        convention, used to define the output shape. Its values do not enter
        the pressure formulas, and the unit is not runtime-enforced.
    radial_shape : array_like, shape (N_Z, N_R)
        Finite nonnegative radial envelope with the same shape as ``psi``.
    hot_parallel_shape : array_like, shape (N_Z, N_R)
        Finite nonnegative hot-ion parallel pressure shape.
    hot_perpendicular_shape : array_like, shape (N_Z, N_R)
        Finite nonnegative hot-ion perpendicular pressure shape.
    hot_density_shape : array_like, shape (N_Z, N_R)
        Finite nonnegative hot-ion density shape. It is required even when
        ``hot_density_scale`` is ``None``.
    hot_pressure_scale : float, default=1.0
        Hot-ion pressure scale in [Pa]. Must be finite and nonnegative.
    gas_dynamic_pressure : float, default=0.0
        Gas dynamic pressure scale in [Pa]. Must be finite and nonnegative.
    gas_dynamic_density : float or None, default=None
        Optional gas density scale in [m^-3]. ``None`` omits the gas-density
        term; an explicit zero still returns a zero density field.
    hot_density_scale : float or None, default=None
        Optional hot-ion density scale in [m^-3]. ``None`` omits the hot-ion
        density term.
    electron_temperature : float or None, default=None
        Optional constant electron energy per particle in [J]. ``None``
        leaves electron temperature and electron pressure unset. The value is
        not converted from Kelvin.

    Returns
    -------
    p_parallel : numpy.ndarray
        Total parallel pressure in [Pa], with the shape of ``psi``.
    p_perp : numpy.ndarray
        Total perpendicular pressure in [Pa], with the shape of ``psi``.
    density : numpy.ndarray or None
        Configured gas-plus-hot-ion density in [m^-3], or ``None`` when both
        density scales are omitted.
    electron_temperature : numpy.ndarray or None
        Constant electron-energy field in [J], or ``None`` when unconfigured.

    Raises
    ------
    ValueError
        If a field is not a finite nonempty two-dimensional grid, a shape is
        not exactly aligned with ``psi``, a shape is negative, a scale is
        negative or nonfinite, or assembled output is nonfinite.
    TypeError
        If a supplied scale cannot be converted to a scalar float.

    See Also
    --------
    scirel.kinetic.evaluate_frank_egedal_radial_envelope
        Build the radial envelope used by this assembly.
    scirel.kinetic.solve_frank_egedal_pressure_closure
        Compose the full Frank--Egedal pressure closure.

    Notes
    -----
    Let ``r`` be ``radial_shape``, ``h_parallel`` and ``h_perp`` be the two
    hot-ion pressure shapes, and ``h_n`` be ``hot_density_shape``. The
    optional density is ``r * gas_dynamic_density + r * h_n *
    hot_density_scale``. The electron pressure is ``density *
    electron_temperature`` when both are configured, and the hot-ion terms are
    ``hot_pressure_scale * r * h_parallel`` and ``hot_pressure_scale * r *
    h_perp``. Thus both pressure components share the gas and electron
    contributions and retain the hot-ion anisotropy.

    References
    ----------
    Frank and Egedal, arXiv:2509.17288 (2025).

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_frank_egedal_pressure
    >>> psi = np.zeros((1, 2))
    >>> radial = np.array([[1.0, 0.5]])
    >>> r = assemble_frank_egedal_pressure(
    ...     psi,
    ...     radial,
    ...     np.full((1, 2), 2.0),
    ...     np.full((1, 2), 3.0),
    ...     np.full((1, 2), 4.0),
    ...     hot_pressure_scale=5.0,
    ...     gas_dynamic_pressure=7.0,
    ...     gas_dynamic_density=11.0,
    ...     hot_density_scale=13.0,
    ...     electron_temperature=17.0,
    ... )
    >>> np.testing.assert_allclose(r["density"], 63.0 * radial)
    >>> np.testing.assert_allclose(r["p_parallel"], 1088.0 * radial)
    >>> np.testing.assert_allclose(r["p_perp"], 1093.0 * radial)
    >>> np.testing.assert_allclose(r["electron_temperature"], 17.0)
    """
    psi = np.asarray(psi, dtype=float)
    fields = [
        np.asarray(value, dtype=float)
        for value in (radial_shape, hot_parallel_shape, hot_perpendicular_shape, hot_density_shape)
    ]
    if (
        psi.ndim != 2
        or psi.size == 0
        or not np.all(np.isfinite(psi))
        or any(
            value.shape != psi.shape or not np.all(np.isfinite(value)) or np.any(value < 0.0)
            for value in fields
        )
    ):
        raise ValueError("pressure assembly requires same-shape finite two-dimensional fields")
    radial, hot_parallel, hot_perpendicular, hot_density = fields
    hot_pressure_scale = float(hot_pressure_scale)
    gas_dynamic_pressure = float(gas_dynamic_pressure)
    electron_temperature_value = electron_temperature
    scales = [
        hot_pressure_scale,
        gas_dynamic_pressure,
        gas_dynamic_density,
        hot_density_scale,
        electron_temperature_value,
    ]
    if any(
        not np.isfinite(float(value)) or float(value) < 0.0 for value in scales if value is not None
    ):
        raise ValueError("pressure, density and temperature scales must be finite and nonnegative")
    p_gd = gas_dynamic_pressure * radial
    density = np.zeros_like(psi, dtype=float)
    if gas_dynamic_density is not None:
        density += float(gas_dynamic_density) * radial
    if hot_density_scale is not None:
        density += float(hot_density_scale) * radial * hot_density
    electron_temperature = (
        None
        if electron_temperature_value is None
        else np.full_like(psi, float(electron_temperature_value), dtype=float)
    )
    electron_pressure = 0.0 if electron_temperature is None else density * electron_temperature
    result = {
        "p_parallel": p_gd + electron_pressure + hot_pressure_scale * radial * hot_parallel,
        "p_perp": p_gd + electron_pressure + hot_pressure_scale * radial * hot_perpendicular,
        "density": None if gas_dynamic_density is None and hot_density_scale is None else density,
        "electron_temperature": electron_temperature,
    }
    if any(not np.all(np.isfinite(value)) for value in result.values() if value is not None):
        raise ValueError("pressure assembly produced non-finite fields")
    return result


__all__ = ["assemble_frank_egedal_pressure"]
