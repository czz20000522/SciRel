"""Ambipolar end-loss potential closure for one magnetized ion species."""

from scirel._validation import (
    required_finite_scalar as _require_finite_scalar,
    required_integer_scalar as _require_integer_scalar,
)
import numpy as np
from scirel._mirror_numerics import _mirror_flux
from scirel._numerics import _potential_midpoint

ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837139e-31


def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    values = np.asarray(value, dtype=float)
    try:
        values = np.broadcast_to(values, np.shape(psi))
    except ValueError as exc:
        raise ValueError(f"{name} cannot be broadcast over psi") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def _one_way_flux(
    density,
    mass_kg,
    charge_c,
    temperature_parallel_j,
    temperature_perpendicular_j,
    b_reference_t,
    b_plug_t,
    phi_reference_v,
    phi_plug_v,
    refill,
):
    """Evaluate the one-way half-space flux above a mirror/electrostatic barrier."""
    return _mirror_flux(
        density,
        mass_kg,
        charge_c,
        temperature_parallel_j,
        temperature_perpendicular_j,
        b_reference_t,
        b_plug_t,
        phi_reference_v,
        phi_plug_v,
        refill,
    )


def solve_mirror_ambipolar_potential(
    b_reference_t,
    b_plug_t,
    psi,
    ion_mass_kg,
    ion_charge_c,
    ion_density_ref_m3,
    ion_temperature_parallel_j,
    ion_temperature_perpendicular_j,
    electron_temperature_j,
    phi_reference_v=0.0,
    electron_density_ref_m3=None,
    ion_loss_refill=1.0,
    electron_loss_refill=1.0,
    potential_tolerance_v=1e-06,
    current_tolerance=1e-10,
    max_iterations=100,
    initial_bracket_thermal=8.0,
    mode="solve",
    phi_plug_v=None,
):
    """Solve ``Z_i Gamma_i = Gamma_e`` independently on each flux surface.

    Barrier fluxes use bounded exponent differences. In evaluate mode
    converged retains its historical meaning of successful evaluation; the
    explicit current_balance_solved flag is False and the current residual
    must not be interpreted as a solved equilibrium. Fluxes use relative
    potentials before species scaling, and finite stable midpoints retain a
    large common gauge without changing the residual/width gates. Nonfinite states fail."""
    if mode not in {"solve", "evaluate"}:
        raise ValueError("mode must be solve or evaluate")
    ion_mass_kg = _require_finite_scalar(ion_mass_kg, "ion_mass_kg", positive=True)
    ion_charge_c = _require_finite_scalar(ion_charge_c, "ion_charge_c", positive=True)
    ion_loss_refill = _require_finite_scalar(ion_loss_refill, "ion_loss_refill", nonnegative=True)
    electron_loss_refill = _require_finite_scalar(
        electron_loss_refill, "electron_loss_refill", positive=True
    )
    potential_tolerance_v = _require_finite_scalar(
        potential_tolerance_v, "potential_tolerance_v", positive=True
    )
    current_tolerance = _require_finite_scalar(
        current_tolerance, "current_tolerance", positive=True
    )
    max_iterations = _require_integer_scalar(max_iterations, "max_iterations", minimum=1)
    initial_bracket_thermal = _require_finite_scalar(
        initial_bracket_thermal, "initial_bracket_thermal", positive=True
    )
    if not 0.0 <= ion_loss_refill <= 1.0:
        raise ValueError("ion_loss_refill must lie in [0, 1]")
    if mode == "solve" and ion_loss_refill <= 0.0:
        raise ValueError(
            "a positive ion_loss_refill is required to determine an ambipolar end potential"
        )
    if electron_loss_refill > 1.0:
        raise ValueError("electron_loss_refill must lie in (0, 1]")
    b_reference_t, b_plug_t, psi, phi_reference_v = np.broadcast_arrays(
        np.asarray(b_reference_t, dtype=float),
        np.asarray(b_plug_t, dtype=float),
        np.asarray(psi, dtype=float),
        np.asarray(phi_reference_v, dtype=float),
    )
    if not all(
        (np.all(np.isfinite(value)) for value in (b_reference_t, b_plug_t, psi, phi_reference_v))
    ):
        raise ValueError("field, psi, and reference potential inputs must be finite")
    if np.any(b_reference_t <= 0.0) or np.any(b_plug_t <= 0.0):
        raise ValueError("reference and plug magnetic fields must be positive")
    ion_density = _field(ion_density_ref_m3, psi, "ion_density_ref_m3")
    ion_parallel = _field(ion_temperature_parallel_j, psi, "ion_temperature_parallel_j")
    ion_perpendicular = _field(
        ion_temperature_perpendicular_j, psi, "ion_temperature_perpendicular_j"
    )
    electron_temperature = _field(electron_temperature_j, psi, "electron_temperature_j")
    charge_state = ion_charge_c / ELEMENTARY_CHARGE_C
    electron_density = (
        charge_state * ion_density
        if electron_density_ref_m3 is None
        else _field(electron_density_ref_m3, psi, "electron_density_ref_m3")
    )
    if np.any(ion_density < 0.0) or np.any(electron_density < 0.0):
        raise ValueError("reference densities cannot be negative")
    if (
        np.any(ion_parallel <= 0.0)
        or np.any(ion_perpendicular <= 0.0)
        or np.any(electron_temperature <= 0.0)
    ):
        raise ValueError("temperatures must be positive")

    def fluxes(phi_plug_v):
        ion_flux = _one_way_flux(
            ion_density,
            ion_mass_kg,
            ion_charge_c,
            ion_parallel,
            ion_perpendicular,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            ion_loss_refill,
        )
        electron_flux = _one_way_flux(
            electron_density,
            ELECTRON_MASS_KG,
            -ELEMENTARY_CHARGE_C,
            electron_temperature,
            electron_temperature,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            electron_loss_refill,
        )
        log_ion = _mirror_flux(
            ion_density,
            ion_mass_kg,
            ion_charge_c,
            ion_parallel,
            ion_perpendicular,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            ion_loss_refill,
            return_log=True,
        ) + np.log(charge_state)
        log_electron = _mirror_flux(
            electron_density,
            ELECTRON_MASS_KG,
            -ELEMENTARY_CHARGE_C,
            electron_temperature,
            electron_temperature,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            electron_loss_refill,
            return_log=True,
        )
        # The inactive/vacuum evaluator keeps finite log diagnostics. Active
        # positive populations retain their analytic logs even when flux rounds
        # to zero, so underflow cannot manufacture a balanced root.
        both = (ion_density > 0) & (electron_density > 0) & (ion_loss_refill > 0)
        tiny_log = np.log(np.finfo(float).tiny)
        residual = np.empty(log_ion.shape)
        residual[both] = log_ion[both] - log_electron[both]
        residual[~both] = np.maximum(log_ion[~both], tiny_log) - np.maximum(
            log_electron[~both], tiny_log
        )
        if not np.all(np.isfinite(residual)):
            raise FloatingPointError("end-loss current residual must be finite")
        return (residual, ion_flux, electron_flux)

    if mode == "evaluate":
        if phi_plug_v is None:
            raise ValueError("phi_plug_v is required when mode=evaluate")
        potential = _field(phi_plug_v, psi, "phi_plug_v")
        log_ratio, ion_flux, electron_flux = fluxes(potential)
        return {
            "potential_v": potential,
            "ion_particle_flux_m2_s": ion_flux,
            "electron_particle_flux_m2_s": electron_flux,
            "log_current_ratio": log_ratio,
            "relative_current_residual": np.tanh(0.5 * log_ratio),
            "iterations": 0,
            "converged": True,
            "evaluation_complete": True,
            "current_balance_solved": False,
        }
    if np.any((ion_density > 0.0) != (electron_density > 0.0)):
        raise ValueError(
            "ion and electron reference densities must be both positive or both zero on each surface for solve mode"
        )
    active = (ion_density > 0.0) & (electron_density > 0.0)
    thermal_voltage = ion_parallel / ion_charge_c + electron_temperature / ELEMENTARY_CHARGE_C
    span = initial_bracket_thermal * thermal_voltage
    lower = phi_reference_v - span
    upper = phi_reference_v + span
    lower_residual = fluxes(lower)[0]
    upper_residual = fluxes(upper)[0]
    for _ in range(8):
        missing_lower = active & (lower_residual < 0.0)
        missing_upper = active & (upper_residual > 0.0)
        if not np.any(missing_lower | missing_upper):
            break
        span = upper - lower
        lower = np.where(missing_lower, lower - span, lower)
        upper = np.where(missing_upper, upper + span, upper)
        lower_residual = fluxes(lower)[0]
        upper_residual = fluxes(upper)[0]
    if np.any(active & ((lower_residual < 0.0) | (upper_residual > 0.0))):
        raise RuntimeError("failed to bracket the ambipolar end potential")
    potential = np.where(active, _potential_midpoint(lower, upper), phi_reference_v)
    converged = not np.any(active)
    iterations = 0
    for iterations in range(1, int(max_iterations) + 1):
        residual, _, _ = fluxes(potential)
        exact = active & (residual == 0.0)
        lower = np.where(exact, potential, lower)
        upper = np.where(exact, potential, upper)
        # Test the residual at the very potential we will return. The
        # predecessor tested this midpoint but returned the next midpoint.
        if not np.any(active) or (
            np.max(np.abs(upper[active] - lower[active])) <= 2 * potential_tolerance_v
            and np.max(np.abs(residual[active])) <= current_tolerance
        ):
            converged = True
            break
        lower = np.where(active & (residual > 0.0), potential, lower)
        upper = np.where(active & (residual <= 0.0), potential, upper)
        potential = np.where(active, _potential_midpoint(lower, upper), phi_reference_v)
    if not converged:
        raise RuntimeError("ambipolar end-potential solve did not converge")
    log_ratio, ion_flux, electron_flux = fluxes(potential)
    if np.any(active) and np.max(np.abs(log_ratio[active])) > current_tolerance:
        raise RuntimeError("returned ambipolar end potential does not satisfy current tolerance")
    return {
        "potential_v": potential,
        "ion_particle_flux_m2_s": ion_flux,
        "electron_particle_flux_m2_s": electron_flux,
        "log_current_ratio": log_ratio,
        "relative_current_residual": np.tanh(0.5 * log_ratio),
        "iterations": iterations,
        "converged": bool(converged),
        "evaluation_complete": True,
        "current_balance_solved": True,
    }


__all__ = ["solve_mirror_ambipolar_potential"]
