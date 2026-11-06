"""Build the explicit two-fluid state consumed by reduced Hall drift closure."""

import numpy as np

from scirel._result import Result


def _profile(value, magnetic_field, psi, name):
    raw = value(magnetic_field, psi) if callable(value) else value
    try:
        result = np.broadcast_to(np.asarray(raw, dtype=float), magnetic_field.shape)
    except ValueError as exc:
        raise ValueError(f"Hall profile '{name}' does not match the R-Z grid") from exc
    if not np.all(np.isfinite(result)):
        raise FloatingPointError(f"Hall profile '{name}' contains NaN or infinity")
    return np.asarray(result)


def close_hall_two_fluid_pressure(
    magnetic_field,
    psi,
    pressure_law,
    ion_density_m3,
    electron_pressure_pa,
    electrostatic_potential_v,
    ion_p_parallel_pa=None,
    ion_p_perpendicular_pa=None,
    electron_p_parallel_pa=None,
    electron_p_perpendicular_pa=None,
    pressure_composition_mode="independent_fit",
):
    """Assemble a prescribed reduced Hall two-fluid pressure state in SI units.

    Parameters
    ----------
    magnetic_field : real array-like
        Magnetic-field magnitude. [T] Shape: scalar or array jointly
        broadcast with ``psi``. Values must be finite.
    psi : real array-like
        Caller-defined flux coordinate. [caller-defined flux coordinate]
        Shape: scalar or array jointly broadcast with ``magnetic_field``.
        Values must be finite.
    pressure_law : callable
        Callable accepting the broadcast magnetic field and flux coordinate
        and returning a dictionary with finite ``p_parallel`` and
        ``p_perpendicular`` pressure profiles. [inputs T and caller-defined flux coordinate; outputs Pa]
        Shape: callable returning scalar or broadcastable arrays.
    ion_density_m3 : real array-like or callable
        Ion number density or a callable of ``(magnetic_field, psi)``.
        [m^-3] Shape: scalar, array or callable output broadcastable to the
        common shape. Values must be finite and nonnegative.
    electron_pressure_pa : real array-like or callable
        Baseline electron pressure profile. [Pa] Shape: scalar, array or
        callable output broadcastable to the common shape. Values must be
        finite and nonnegative.
    electrostatic_potential_v : real array-like or callable
        Electrostatic potential profile. [V] Shape: scalar, array or callable
        output broadcastable to the common shape. Values must be finite.
    ion_p_parallel_pa : real array-like or callable, optional
        Explicit ion parallel pressure. [Pa] Shape: scalar, array or callable
        output broadcastable to the common shape. Default: None, which uses
        ``p_parallel - electron_p_parallel_pa``.
    ion_p_perpendicular_pa : real array-like or callable, optional
        Explicit ion perpendicular pressure. [Pa] Shape: scalar, array or
        callable output broadcastable to the common shape. Default: None,
        which uses ``p_perpendicular - electron_p_perpendicular_pa``.
    electron_p_parallel_pa : real array-like or callable, optional
        Explicit electron parallel pressure. [Pa] Shape: scalar, array or
        callable output broadcastable to the common shape. Default: None,
        which reuses ``electron_pressure_pa``.
    electron_p_perpendicular_pa : real array-like or callable, optional
        Explicit electron perpendicular pressure. [Pa] Shape: scalar, array or
        callable output broadcastable to the common shape. Default: None,
        which reuses ``electron_pressure_pa``.
    pressure_composition_mode : {'independent_fit', 'species_sum'}, optional
        Composition contract for the total pressure. [enum] Shape: scalar.
        Default: ``'independent_fit'``. ``'species_sum'`` requires the supplied
        ion and electron components to sum to the total pressure within the
        implementation's roundoff allowance.

    Returns
    -------
    p_parallel : numpy.ndarray
        Total parallel pressure returned by ``pressure_law``. [Pa] Shape:
        common broadcast shape.
    p_perpendicular : numpy.ndarray
        Total perpendicular pressure returned by ``pressure_law``. [Pa] Shape:
        common broadcast shape.
    ion_density : numpy.ndarray
        Prescribed ion number density. [m^-3] Shape: common broadcast shape.
    electron_density : numpy.ndarray
        Electron number density, equal to the ion density in the implemented
        singly charged model. [m^-3] Shape: common broadcast shape.
    electron_pressure : numpy.ndarray
        Prescribed baseline electron pressure. [Pa] Shape: common broadcast
        shape.
    electron_p_parallel : numpy.ndarray
        Electron parallel pressure component. [Pa] Shape: common broadcast
        shape.
    electron_p_perpendicular : numpy.ndarray
        Electron perpendicular pressure component. [Pa] Shape: common
        broadcast shape.
    electrostatic_potential : numpy.ndarray
        Prescribed electrostatic potential. [V] Shape: common broadcast shape.
    ion_p_parallel : numpy.ndarray
        Ion parallel pressure, explicit or derived from total minus electron
        parallel pressure. [Pa] Shape: common broadcast shape.
    ion_p_perpendicular : numpy.ndarray
        Ion perpendicular pressure, explicit or derived from total minus
        electron perpendicular pressure. [Pa] Shape: common broadcast shape.
    pressure_composition_mode : str
        Selected composition contract. [enum] Shape: scalar.
    species_pressure_sum_consistent : bool
        Whether both residual stresses vanish within the roundoff-scaled
        comparison. [boolean] Shape: scalar.
    residual_stress_parallel_pa : numpy.ndarray
        Total parallel pressure minus the specified ion and electron
        components. [Pa] Shape: common broadcast shape.
    residual_stress_perpendicular_pa : numpy.ndarray
        Total perpendicular pressure minus the specified ion and electron
        components. [Pa] Shape: common broadcast shape.

    Raises
    ------
    ValueError
        If the composition mode is unsupported, the magnetic field or flux is
        nonfinite, a profile cannot broadcast, a checked moment is negative,
        or a requested species-sum identity is inconsistent.
    FloatingPointError
        If a profile or composed pressure sum contains a nonfinite value.
    TypeError
        If ``pressure_law`` is not callable or does not return a dictionary,
        or if numeric conversion receives an unsupported kind.
    KeyError
        If ``pressure_law`` omits ``p_parallel`` or ``p_perpendicular``.

    See Also
    --------
    scirel.closures.close_reduced_hall_drift : Reduced Hall state that consumes pressure and closure fields.

    Notes
    -----
    ``pressure_law(b, psi)`` supplies the total parallel and perpendicular
    pressures. Electron components default to ``electron_pressure_pa`` and
    omitted ion components default to total minus electron pressure. The
    residual stresses are diagnostics, not an implied additional species.
    ``species_sum`` accepts only residuals within the declared roundoff
    allowance; ``independent_fit`` reports the residual explicitly. The
    returned electron density is a single-charge equilibrium assumption, not a
    proof of a self-consistent two-fluid closure.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.closures import close_hall_two_fluid_pressure
    >>> def law(b, psi):
    ...     return {'p_parallel': 5.0 + b + psi, 'p_perpendicular': 4.0 + b + 2.0*psi}
    >>> r = close_hall_two_fluid_pressure([[1.0, 2.0]], [[0.2, 0.4]], law, 1.0e18, 1.0, 3.0)
    >>> np.testing.assert_allclose(r['p_parallel'], [[6.2, 7.4]])
    >>> np.testing.assert_allclose(r['ion_p_parallel'] + r['electron_p_parallel'], r['p_parallel'])
    >>> np.testing.assert_allclose(r['electron_density'], r['ion_density'])
    >>> assert r['species_pressure_sum_consistent']
    >>> np.testing.assert_allclose(r['residual_stress_parallel_pa'], 0., atol=1e-14)
    """
    if pressure_composition_mode not in {"independent_fit", "species_sum"}:
        raise ValueError("pressure_composition_mode must be independent_fit or species_sum")
    b_t, flux = np.broadcast_arrays(
        np.asarray(magnetic_field, dtype=float), np.asarray(psi, dtype=float)
    )
    if not np.all(np.isfinite(b_t)) or not np.all(np.isfinite(flux)):
        raise ValueError("magnetic_field and psi must be finite")
    if not callable(pressure_law):
        raise TypeError("pressure_law must be callable")
    pressure = pressure_law(b_t, flux)
    if not isinstance(pressure, dict):
        raise TypeError("pressure_law must return a dictionary")
    try:
        parallel = _profile(pressure["p_parallel"], b_t, flux, "p_parallel")
        perpendicular = _profile(pressure["p_perpendicular"], b_t, flux, "p_perpendicular")
    except KeyError as exc:
        raise KeyError("pressure_law must return p_parallel and p_perpendicular") from exc
    density = _profile(ion_density_m3, b_t, flux, "ion_density")
    electron_pressure = _profile(electron_pressure_pa, b_t, flux, "electron_pressure")
    electron_parallel = _profile(
        electron_pressure if electron_p_parallel_pa is None else electron_p_parallel_pa,
        b_t,
        flux,
        "electron_p_parallel",
    )
    electron_perpendicular = _profile(
        electron_pressure if electron_p_perpendicular_pa is None else electron_p_perpendicular_pa,
        b_t,
        flux,
        "electron_p_perpendicular",
    )
    potential = _profile(electrostatic_potential_v, b_t, flux, "electrostatic_potential")
    ion_parallel = (
        parallel - electron_parallel
        if ion_p_parallel_pa is None
        else _profile(ion_p_parallel_pa, b_t, flux, "ion_p_parallel")
    )
    ion_perpendicular = (
        perpendicular - electron_perpendicular
        if ion_p_perpendicular_pa is None
        else _profile(ion_p_perpendicular_pa, b_t, flux, "ion_p_perpendicular")
    )
    if any(
        (
            np.any(value < 0.0)
            for value in (
                density,
                electron_pressure,
                electron_parallel,
                electron_perpendicular,
                ion_parallel,
                ion_perpendicular,
            )
        )
    ):
        raise ValueError("Hall fluid closure returned a negative moment")
    with np.errstate(over="ignore", invalid="ignore"):
        sum_parallel = ion_parallel + electron_parallel
        sum_perpendicular = ion_perpendicular + electron_perpendicular
        residual_parallel = parallel - sum_parallel
        residual_perpendicular = perpendicular - sum_perpendicular
    if not all(
        np.all(np.isfinite(x))
        for x in (sum_parallel, sum_perpendicular, residual_parallel, residual_perpendicular)
    ):
        raise FloatingPointError("Hall pressure composition must be finite")
    scale_parallel = np.maximum(np.maximum(abs(parallel), abs(sum_parallel)), np.finfo(float).tiny)
    scale_perpendicular = np.maximum(
        np.maximum(abs(perpendicular), abs(sum_perpendicular)), np.finfo(float).tiny
    )
    consistent = bool(
        np.all(abs(residual_parallel) <= 64 * np.finfo(float).eps * scale_parallel)
        and np.all(abs(residual_perpendicular) <= 64 * np.finfo(float).eps * scale_perpendicular)
    )
    if pressure_composition_mode == "species_sum" and not consistent:
        raise ValueError("total pressure is inconsistent with the species pressure sum")
    return Result(
        {
            "pressure_composition_mode": pressure_composition_mode,
            "species_pressure_sum_consistent": consistent,
            "residual_stress_parallel_pa": residual_parallel,
            "residual_stress_perpendicular_pa": residual_perpendicular,
            "p_parallel": parallel,
            "p_perpendicular": perpendicular,
            "ion_density": density,
            "electron_density": density,
            "electron_pressure": electron_pressure,
            "electron_p_parallel": electron_parallel,
            "electron_p_perpendicular": electron_perpendicular,
            "electrostatic_potential": potential,
            "ion_p_parallel": ion_parallel,
            "ion_p_perpendicular": ion_perpendicular,
        }
    )


__all__ = ["close_hall_two_fluid_pressure"]
