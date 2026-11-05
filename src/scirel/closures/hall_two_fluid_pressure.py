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
    """Assemble a prescribed reduced Hall state in SI units.

    ``independent_fit`` permits total and ion tensors to be fitted independently.
    Their difference after subtracting the electron
    tensor is returned as residual stress, not a validated extra species.
    Total force uses the supplied total tensor; ion thermal inertia uses only
    ion moments. This prescribed state is not proof of self-consistent two-fluid
    equilibrium. ``species_sum`` rejects inconsistent components (roundoff
    allowance only). Omitted ion moments are total minus electron moments.
    Electron density equals ion density under the source singly charged model.

    Returns
    -------
    The top-level value is a ``scirel._result.Result`` mapping; field values
    are available by key and preserve the baseline key order.
    p_parallel : NumPy float64 array [Pa]
        Total parallel pressure returned by pressure_law.
    p_perpendicular : NumPy float64 array [Pa]
        Total perpendicular pressure returned by pressure_law.
    ion_density : NumPy float64 array [m^-3]
        Prescribed ion number density.
    electron_density : NumPy float64 array [m^-3]
        Copy of the ion number density under the implemented single-charge neutrality assumption.
    electron_pressure : NumPy float64 array [Pa]
        Prescribed electron pressure baseline.
    electron_p_parallel : NumPy float64 array [Pa]
        Electron parallel pressure component.
    electron_p_perpendicular : NumPy float64 array [Pa]
        Electron perpendicular pressure component.
    electrostatic_potential : NumPy float64 array [V]
        Prescribed electrostatic potential.
    ion_p_parallel : NumPy float64 array [Pa]
        Ion parallel pressure, explicit or total minus electron parallel component.
    ion_p_perpendicular : NumPy float64 array [Pa]
        Ion perpendicular pressure, explicit or total minus electron perpendicular component.
    pressure_composition_mode : string [enum]
        Selected composition contract.
    species_pressure_sum_consistent : Python bool [boolean]
        Both residual stresses vanish within roundoff-scaled comparison.
    residual_stress_parallel_pa : NumPy float64 scalar or array [Pa]
        Total parallel stress minus specified ion/electron pressure components.
    residual_stress_perpendicular_pa : NumPy float64 scalar or array [Pa]
        Total perpendicular stress minus specified ion/electron pressure components."""
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
