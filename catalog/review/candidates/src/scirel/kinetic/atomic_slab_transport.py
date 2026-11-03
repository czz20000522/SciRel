"""Finite velocity atomic slab transport composition.

This composition owns the reusable mesh, boundary, collision, generation and
moment orchestration for the fixed atomic slab contract. Plotting and report
formatting remain caller glue.
"""
from __future__ import annotations

import numpy as np

__all__ = ["solve_atomic_slab_transport"]


def _volume(vr: np.ndarray, vx: np.ndarray) -> np.ndarray:
    if vr.size < 2 or vx.size < 2:
        raise ValueError("atomic slab transport needs at least two velocity centres per axis")
    re = np.r_[0.0, (vr[:-1] + vr[1:]) / 2.0, vr[-1] + (vr[-1] - vr[-2]) / 2.0]
    xe = np.r_[vx[0] - (vx[1] - vx[0]) / 2.0, (vx[:-1] + vx[1:]) / 2.0,
               vx[-1] + (vx[-1] - vx[-2]) / 2.0]
    return np.pi * (re[1:] ** 2 - re[:-1] ** 2)[:, None] * np.diff(xe)[None, :]


def solve_atomic_slab_transport(inputs: dict) -> dict:
    """Run the declared finite atomic slab composition.

    ``inputs`` follows the demo ``profiles``, ``incident`` and ``configuration``
    mapping. The returned arrays are task-ready scientific fields; serialization
    and visualization are caller-owned.
    """
    from .adaptive_neutral_velocity_mesh import create_adaptive_neutral_velocity_mesh
    from .axisymmetric_neutral_moments import reduce_axisymmetric_neutral_moments
    from .incoming_boundary_flux_normalization import normalize_incoming_neutral_boundary
    from .neutral_generation_propagation import propagate_neutral_generation
    from .neutral_generation_stopping import evaluate_neutral_generation_stopping
    from .neutral_total_collision_frequency import assemble_neutral_total_collision_frequency
    from .simple_charge_exchange_source import assemble_simple_charge_exchange_source
    from .shifted_maxwellian_seed import build_shifted_maxwellian_seed
    from .upwind_transport_coefficients import assemble_neutral_upwind_transport_coefficients
    from ..collisions.janev_electron_impact_ionization_rate import evaluate_janev_electron_impact_ionization_rate
    from ..collisions.atomic_hydrogen_charge_exchange_rate import evaluate_atomic_hydrogen_charge_exchange_rate
    from ..collisions.atomic_hydrogen_1s_radiative_recombination_rate import evaluate_atomic_hydrogen_1s_radiative_recombination_rate

    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    profiles = inputs.get("profiles", {})
    config = inputs.get("configuration", {}).get("kinetic_h", {})
    incident = inputs.get("incident", {})
    x = np.asarray(profiles.get("x"), dtype=float)
    ti = np.asarray(profiles.get("Ti"), dtype=float)
    te = np.asarray(profiles.get("Te", ti), dtype=float)
    ne = np.asarray(profiles.get("n", np.ones_like(x)), dtype=float)
    if x.ndim != 1 or ti.shape != x.shape or te.shape != x.shape or ne.shape != x.shape:
        raise ValueError("profiles x/Ti/Te/n must be aligned one-dimensional arrays")
    if not np.all(np.isfinite(np.c_[x, ti, te, ne])) or np.any(ti <= 0) or np.any(te <= 0) or np.any(ne < 0):
        raise ValueError("profiles must be finite with positive temperatures and nonnegative density")
    vx, vr, tnorm, _, _ = create_adaptive_neutral_velocity_mesh(
        int(config.get("mesh_size", 6)), ti, incident.get("energies_eV", [3.0])
    )
    volume = _volume(vr, vx)
    mass_amu = float(profiles.get("mu", 2.0))
    seed = build_shifted_maxwellian_seed(
        vr=vr, vx=vx, tnorm_ev=tnorm, shifted_vx_m_s=[0.0],
        temperature_ev=[float(ti[0])], mass_amu=mass_amu, molecule_count=1,
        cylindrical_volume=volume,
    )
    target_flux = float(incident.get("density_m3", 1.0e15))
    boundary, _, _ = normalize_incoming_neutral_boundary(
        seed["distribution"][:, :, 0], vx, volume, seed["thermal_speed_m_s"], target_flux
    )
    ion_rate = evaluate_janev_electron_impact_ionization_rate(te, "H")
    cx_rate = evaluate_atomic_hydrogen_charge_exchange_rate(
        ti, np.full_like(ti, float(np.asarray(incident.get("energies_eV", [3.0]))[0]))
    )
    base = ne * ion_rate / seed["thermal_speed_m_s"]
    cx = np.broadcast_to((ne * cx_rate / seed["thermal_speed_m_s"])[None, None, :], (vr.size, vx.size, x.size))
    raw_diameter = inputs.get("pipe_diameter_m", np.zeros_like(x))
    if isinstance(raw_diameter, str):
        if raw_diameter not in ("zero", "zero at all original and derived points"):
            raise ValueError("pipe_diameter_m string must declare the zero-pipe contract")
        diameter = np.zeros_like(x)
    else:
        diameter = np.asarray(raw_diameter, dtype=float)
    if diameter.shape != x.shape:
        raise ValueError("pipe_diameter_m must be scalar text zero or an x-aligned array")
    alpha = assemble_neutral_total_collision_frequency(
        vr, vx, base, np.zeros_like(base), diameter, cx, True
    )
    source = np.zeros_like(alpha)
    coeff = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    first_generation = propagate_neutral_generation(
        vx, coeff["Ak"], coeff["Bk"], coeff["Fk"], coeff["Ck"], coeff["Dk"], coeff["Gk"],
        "first_flight", incoming_boundary=boundary
    )
    generations = [first_generation]
    accumulated = np.array(first_generation, copy=True)
    moments = reduce_axisymmetric_neutral_moments(
        accumulated, vx, vr, volume, tnorm, mass_amu, 1, empty_slice_policy="source_default"
    )
    density = moments["density_m3"]
    delta, stopped, reason = evaluate_neutral_generation_stopping(
        moments["density_m3"], moments["density_m3"], float(inputs.get("solver", {}).get("truncate", 1e-3))
    )
    max_generations = int(inputs.get("solver", {}).get("max_generations", 50))
    if max_generations < 1:
        raise ValueError("solver.max_generations must be a positive integer")
    recombination_rate = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(te)
    # The fixed candidate has no molecular or elastic source.  Each later
    # generation receives the public simple-CX contraction from its predecessor
    # plus the declared radiative recombination source shape.
    recombination_source = np.broadcast_to(
        (ne * ne * recombination_rate / seed["thermal_speed_m_s"])[None, None, :],
        accumulated.shape,
    ) * np.broadcast_to(seed["distribution"][:, :, 0, None], accumulated.shape)
    while not stopped and len(generations) < max_generations:
        previous = generations[-1]
        cx_source = assemble_simple_charge_exchange_source(
            np.broadcast_to(seed["distribution"][:, :, 0, None], previous.shape),
            cx,
            previous,
            volume,
            np.ones(vx.size, dtype=float),
        )
        scattered_source = cx_source + recombination_source
        next_generation = propagate_neutral_generation(
            vx, coeff["Ak"], coeff["Bk"], coeff["Fk"], coeff["Ck"], coeff["Dk"], coeff["Gk"],
            "scattered", scattered_source_distribution=scattered_source
        )
        generations.append(next_generation)
        accumulated = accumulated + next_generation
        updated_moments = reduce_axisymmetric_neutral_moments(
            accumulated, vx, vr, volume, tnorm, mass_amu, 1, empty_slice_policy="source_default"
        )
        delta, stopped, reason = evaluate_neutral_generation_stopping(
            reduce_axisymmetric_neutral_moments(
                next_generation, vx, vr, volume, tnorm, mass_amu, 1, empty_slice_policy="source_default"
            )["density_m3"],
            updated_moments["density_m3"],
            float(inputs.get("solver", {}).get("truncate", 1e-3)),
        )
        moments = updated_moments
        density = moments["density_m3"]
    if not stopped and len(generations) >= max_generations:
        reason = "max_generations"
    generation = accumulated
    return {
        "schema": "scirel.atomic-slab-transport.v1",
        "distribution": generation,
        "generation_distributions": np.asarray(generations),
        "generation_count": len(generations),
        "x_m": x,
        "vx": vx,
        "vr": vr,
        "normalization_temperature_ev": float(tnorm),
        "density_m3": density,
        "particle_flux_m2_s": moments["axial_flux_m2_s"],
        "flow_velocity_m_s": moments["axial_velocity_m_s"],
        "pressure_ev_m3": moments["pressure_ev_m3"],
        "temperature_ev": moments["temperature_ev"],
        "random_heat_flux_w_m2": moments["random_heat_flux_w_m2"],
        "ionization_source_m3_s": ne * ion_rate * density,
        "recombination_source_m3_s": ne * ne * recombination_rate,
        "charge_exchange_frequency_m_inv": cx,
        "generation_delta": float(delta),
        "generation_stopped": bool(stopped),
        "generation_stop_reason": reason,
    }
