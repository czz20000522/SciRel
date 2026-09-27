"""FIDASIM ``ndmc`` beam-neutral deposition main-loop producer orchestration.

Source: the producer side of ``ndmc`` (the saved package
``NDMC束中性沉积生产者``; src/fidasim.f90:12990-13119, with
``store_neutrals`` at src/fidasim.f90:10428-10482 and the source
elementary charge at src/fidasim.f90:69) for one marker slice: compute
``nneutrals = 1e6*pinj / (1e3*einj*e0*(f1 + f2/2 + f3/3))`` with the
source-faithful ``e0 = 1.60217733e-19``, materialize the per-fraction
initial level state ``states(1) = nneutrals*fraction/dv``, and accumulate
the ``store_neutrals`` full/half/third population updates plus
``flux_tot`` from per-segment collisional-radiative deposition handoff
records (cell index, ``dens/nlaunch``, segment flux) produced by the N3
beam-neutral deposition loop.  Single-rank, bounded to one marker slice:
no random numbers, no plasma/field projections, no MPI/OpenMP runtime.

Carried units (source-evidence reconciliation, reviewer finding): the
seeded level states and the caller's per-segment ``dens/nlaunch``
records follow the source's rate-density semantics -- the deposition
loop's level states are cm^-3 s^-1 (the source's implicit 1 s convention
is not proven; see the integrated ``nbi-component-initial-state`` asset),
``dens/nlaunch`` accumulates into the cm^-3 population arrays, and
``flux*dv`` accumulates into particles/s.  The saved arm's
``*_cm_inv3`` field names for the initial states mislabel that carried
unit; the names are kept verbatim and the unit question is retained for
expert adjudication.  The e0 fork is an existing inter-asset divergence:
``nbi-injected-neutrals-normalization`` uses the CODATA 2018 value
1.602176634e-19 while ``nbi-component-initial-state`` uses the source
value like this producer; this gate rejects a CODATA-e0 normalization
(source-faithful choice, pending expert adjudication of the fork).

Registered hardenings against the saved arm: ``grid_shape`` must be a
genuine integer triple (the saved arm's ``astype(int)`` silently
truncated whole-number floats such as 2.0); accumulated populations
must stay finite.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

__all__ = ["ELEMENTARY_CHARGE_C", "run_ndmc_deposition_producer"]

# Source-faithful elementary charge (src/fidasim.f90:69 ``e0 = 1.60217733d-19``).
# The frozen trace initial state ``states(1) = nneutrals*full/dv`` reproduces the
# source bit-for-bit with this constant (rel 0.0).  The integrated
# ``nbi-injected-neutrals-normalization`` asset uses the CODATA 2018 value
# 1.602176634e-19, which yields rel ~4.34e-7 deviation from the traced state.
ELEMENTARY_CHARGE_C = 1.60217733e-19

_ENERGY_FRACTION_DENOMINATOR = (1.0, 2.0, 3.0)
_POPULATION_NAMES = {1: "full", 2: "half", 3: "third"}


def _positive_scalar(value, *, name: str) -> float:
    if isinstance(value, bool) or not np.isscalar(value):
        raise ValueError(f"{name} must be a scalar")
    number = float(value)
    if not np.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return number


def _nonnegative_scalar(value, *, name: str) -> float:
    if isinstance(value, bool) or not np.isscalar(value):
        raise ValueError(f"{name} must be a scalar")
    number = float(value)
    if not np.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


def _fractions(value) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("current_fractions must be numeric") from exc
    if array.shape != (3,) or not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise ValueError("current_fractions must be a finite nonnegative triple")
    if float(np.sum(array)) <= 0.0:
        raise ValueError("at least one current_fraction must be positive")
    return array


def _initial_states(value, *, nlevels: int) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("initial_states_cm_inv3_s_inv must be numeric") from exc
    if array.shape != (3, nlevels) or not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise ValueError(f"initial_states_cm_inv3_s_inv must be a finite nonnegative (3, {nlevels}) array")
    return array


def _population(value, *, name: str, shape) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.shape != shape or not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise ValueError(f"{name} must be a finite nonnegative {shape} array")
    return array


def _grid_shape(value) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("grid_shape must be an integer triple") from exc
    # Registered hardening: the saved arm's astype(int) silently truncated
    # whole-number floats; a genuine integer triple is required here.
    if array.shape != (3,) or array.dtype.kind not in "iu":
        raise ValueError("grid_shape must be a positive integer triple (nx, ny, nz) (registered hardening)")
    if np.any(array <= 0):
        raise ValueError("grid_shape must be a positive integer triple (nx, ny, nz)")
    return array.astype(np.int64, copy=False)


def _vector(value, *, name: str, size: int | None = None, nonnegative: bool = False) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite one-dimensional vector")
    if size is not None and array.shape != (size,):
        raise ValueError(f"{name} must have shape ({size},)")
    if nonnegative and np.any(array < 0.0):
        raise ValueError(f"{name} must be nonnegative")
    return array


def _segment_record(record: object, *, nlevels: int, grid_shape) -> dict[str, object]:
    if not isinstance(record, Mapping):
        raise ValueError("each segment record must be a mapping")
    required = {"grid_index_one_based", "normalized_density_cm_inv3", "segment_flux_per_cm3_s"}
    if required - set(record):
        raise ValueError("segment record misses a declared deposition field")
    index = np.asarray(record["grid_index_one_based"])
    if index.shape != (3,) or index.dtype.kind not in "iu":
        raise ValueError("grid_index_one_based must be an integer triple")
    if np.any(index < 1) or np.any(index > grid_shape):
        raise ValueError("grid_index_one_based must lie inside the declared beam grid")
    density = _vector(record["normalized_density_cm_inv3"], name="normalized_density_cm_inv3",
                      size=nlevels, nonnegative=True)
    # Source-faithful signed flux: (iflux - sum(states))/nlaunch is signed and
    # the colrad advance drives a net level-population gain whenever the rate
    # matrix's inflow (population) terms outweigh its losses (a loss-only
    # matrix with all column sums <= 0 cannot produce a gain), so a valid N3
    # handoff may carry a negative segment flux.  Only finiteness is required;
    # the saved arm's documented nonnegativity is a bounded incompatibility
    # recorded for expert adjudication.
    if isinstance(record["segment_flux_per_cm3_s"], (bool, np.bool_)) or not np.isscalar(record["segment_flux_per_cm3_s"]):
        raise ValueError("segment_flux_per_cm3_s must be a scalar")
    flux = float(record["segment_flux_per_cm3_s"])
    if not np.isfinite(flux):
        raise ValueError("segment_flux_per_cm3_s must be finite")
    return {
        "grid_index_one_based": index.astype(np.int64, copy=False),
        "normalized_density_cm_inv3": density,
        "segment_flux_per_cm3_s": flux,
    }


def run_ndmc_deposition_producer(
    *,
    injected_power_mw,
    injection_energy_kev,
    current_fractions,
    beam_grid_cell_volume_cm3,
    nlaunch,
    nlevels,
    grid_shape,
    initial_states_cm_inv3_s_inv,
    initial_population_density_full,
    initial_population_density_half,
    initial_population_density_third,
    per_fraction_segment_depositions,
    expected_deposited_particles_per_s_per_fraction=None,
):
    """Orchestrate the ndmc main-loop population accumulation for one marker slice.

    Parameters mirror the source ``ndmc`` producer (fidasim.f90:12990-13119):
    beam power/energy/current fractions define ``nneutrals``; ``nlaunch`` is the
    marker count denominator; per-fraction ordered segment deposition records
    carry each collisional-radiative cell handoff (cell index, ``dens/nlaunch``,
    segment flux) produced by the N3 beam-neutral deposition loop.  The operator
    validates the source-faithful initial level state per fraction and
    accumulates the ``store_neutrals`` full/half/third population arrays and
    ``flux_tot``.
    """
    power = _nonnegative_scalar(injected_power_mw, name="injected_power_mw")
    energy = _positive_scalar(injection_energy_kev, name="injection_energy_kev")
    fractions = _fractions(current_fractions)
    dv = _positive_scalar(beam_grid_cell_volume_cm3, name="beam_grid_cell_volume_cm3")
    nlaunch_value = _positive_scalar(nlaunch, name="nlaunch")
    if isinstance(nlevels, bool) or not isinstance(nlevels, (int, np.integer)) or nlevels < 1:
        raise ValueError("nlevels must be a positive integer")
    nlevels = int(nlevels)
    grid_shape = _grid_shape(grid_shape)
    initial_states = _initial_states(initial_states_cm_inv3_s_inv, nlevels=nlevels)
    population_shape = (nlevels, int(grid_shape[0]), int(grid_shape[1]), int(grid_shape[2]))
    populations = {
        "full": _population(initial_population_density_full, name="initial_population_density_full", shape=population_shape),
        "half": _population(initial_population_density_half, name="initial_population_density_half", shape=population_shape),
        "third": _population(initial_population_density_third, name="initial_population_density_third", shape=population_shape),
    }
    if isinstance(per_fraction_segment_depositions, (str, bytes)) or not isinstance(per_fraction_segment_depositions, Mapping):
        raise ValueError("per_fraction_segment_depositions must be a mapping keyed by neutral type 1..3")

    energy_factor = float(sum(f / divisor for f, divisor in zip(fractions, _ENERGY_FRACTION_DENOMINATOR)))
    nneutrals = 1.0e6 * power / (1.0e3 * energy * ELEMENTARY_CHARGE_C * energy_factor)

    populations = {name: array.copy() for name, array in populations.items()}
    flux_tot = np.zeros(3, dtype=np.float64)
    segment_counts = {1: 0, 2: 0, 3: 0}
    store_event_counts = {1: 0, 2: 0, 3: 0}
    for fraction, records in per_fraction_segment_depositions.items():
        if isinstance(fraction, bool) or not isinstance(fraction, (int, np.integer)) or int(fraction) not in _POPULATION_NAMES:
            raise ValueError("per_fraction_segment_depositions keys must be neutral type IDs 1..3")
        fraction = int(fraction)
        if fractions[fraction - 1] == 0.0:
            raise ValueError(f"fraction {fraction} has zero current_fraction but supplied segment records")
        if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
            raise ValueError(f"fraction {fraction} segment records must be an ordered sequence")

    reference_initial = np.zeros((3, nlevels), dtype=np.float64)
    for fraction in (1, 2, 3):
        reference_initial[fraction - 1, 0] = nneutrals * fractions[fraction - 1] / dv
    if not np.allclose(initial_states, reference_initial, rtol=1.0e-9, atol=0.0):
        raise ValueError(
            "initial_states_cm_inv3_s_inv must equal nneutrals*current_fraction/dv "
            "(source-faithful e0); a CODATA-e0 NBI normalization will not reproduce the traced state"
        )

    for fraction, records in per_fraction_segment_depositions.items():
        parsed_records = [_segment_record(record, nlevels=nlevels, grid_shape=grid_shape) for record in records]
        for parsed in parsed_records:
            ix, iy, iz = (int(value) - 1 for value in parsed["grid_index_one_based"])
            populations[_POPULATION_NAMES[fraction]][:, ix, iy, iz] += parsed["normalized_density_cm_inv3"]
            flux_tot[fraction - 1] += parsed["segment_flux_per_cm3_s"] * dv
            segment_counts[fraction] += 1
            store_event_counts[fraction] += 1

    if not all(np.all(np.isfinite(array)) and np.all(array >= 0.0) for array in populations.values()):
        raise ValueError("accumulated NDMC populations must be finite and nonnegative")

    if expected_deposited_particles_per_s_per_fraction is not None:
        # Signed like the accumulation: a net level-population gain over
        # segments yields a negative flux_tot component, so the caller's
        # expected totals may be negative too.
        expected = _vector(
            expected_deposited_particles_per_s_per_fraction,
            name="expected_deposited_particles_per_s_per_fraction",
            size=3,
        )
        if not np.allclose(flux_tot, expected, rtol=1.0e-9, atol=0.0):
            raise ValueError("flux_tot must equal the summed per-segment segment_flux*cell_volume")

    return {
        "elementary_charge_c": ELEMENTARY_CHARGE_C,
        "nneutrals_s_inv": float(nneutrals),
        "energy_weight_factor": energy_factor,
        "initial_state_rate_per_volume_cm_inv3_s_inv": reference_initial,
        "initial_state_validated": True,
        "population_density_full": populations["full"],
        "population_density_half": populations["half"],
        "population_density_third": populations["third"],
        "flux_tot_per_fraction": flux_tot,
        "deposited_particles_per_s": float(np.sum(flux_tot)),
        "segment_count_per_fraction": segment_counts,
        "store_neutral_event_count_per_fraction": store_event_counts,
        "population_shape": population_shape,
        "grid_shape": tuple(int(value) for value in grid_shape),
        "single_rank_unpartitioned": True,
        "source_anchor": "src/fidasim.f90:12990-13119",
    }
