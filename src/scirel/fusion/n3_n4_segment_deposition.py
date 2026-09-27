"""FIDASIM N3/N4 segment-state validation and marker-normalized deposition.

Source: FIDASIM ``nbi`` per-track consumption of the ``colrad`` update
(the saved package ``N3逐段N4状态沉积``, src/fidasim.f90:13041-13057) --
verify the local snapshot position against the source track midpoint,
verify the caller's N4 result record (sample index, exact prior state,
matching ``dt_s``, finite state-shaped results, nonempty result
provenance), then apply the source's marker normalization:
``dens/nlaunch``, ``photons/nlaunch``, segment flux
``(sum(previous) - sum(next))/nlaunch`` and the accumulated deposition
``previous + segment_flux * cell_volume``.

Carried units and field naming (source-evidence reconciliation,
reviewer findings, pending expert adjudication): the level states in
this chain are source RATE DENSITIES in cm^-3 s^-1, seeded as
``states(1) = nneutrals*fraction/dv`` with ``nneutrals`` in particles/s
(matching the integrated ``nbi-component-initial-state`` asset's
``initial_state_rate_per_volume_cm_inv3_s_inv``).  The saved arm's
``*_cm_inv3`` field names mislabel that carried unit, so the public
field names here use the precise ``*_cm_inv3_s_inv`` form; the true
time-integrated density keeps its correct ``dens_cm_inv3`` name.  The
N4 record is an explicit external caller capability: the caller
separately composes the N4 colrad update, and no integrated SciRel
colrad asset is invoked here.  Under the frozen r77
``collisional-radiative-state-advance`` document contract (states
labeled cm^-3, photons s^-1) its outputs could not legally populate
this record as declared (rate-density states, cm^-3 integrated density,
cm^-3 s^-1 photons); that label correction is carried by the r78
successor documents, not the old freeze.

Registered hardenings against the saved arm: the sample index must be a
genuine nonnegative in-record integer (the saved arm compared
``int(record) != index`` and accepted bools), the normalization scalars
must be genuine finite scalars (Python bools and ``np.bool_`` rejected
-- the saved arm accepted ``np.bool_(True)`` as ``1.0``), non-numeric
record fields raise ValueError instead of the saved arm's raw TypeError,
and negative ``dens_cm_inv3`` or ``photons_per_cm3_s`` fail closed (the
saved arm's own operator contract declares them nonnegative but its
implementation only rejected negative next states).
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["assemble_n3_n4_segment_deposition"]


def _finite_scalar(value, name, *, positive=False):
    if (isinstance(value, (bool, np.bool_)) or not np.isscalar(value)
            or isinstance(value, (str, bytes))):
        raise ValueError(f"{name} must be a genuine finite scalar (registered hardening)")
    number = float(value)
    if not np.isfinite(number) or (positive and number <= 0.0):
        raise ValueError(f"{name} must be a genuine finite scalar (registered hardening)")
    return number


def assemble_n3_n4_segment_deposition(
    *,
    expected_position_cm,
    actual_position_cm,
    n4_cell_update_record,
    local_state_sample_index,
    previous_states_cm_inv3_s_inv,
    segment_duration_s,
    nlaunch,
    beam_grid_cell_volume_cm3,
    previous_deposited_particles_per_s,
):
    """Validate one N4 handoff and return its source-normalized N3 deposition."""
    expected = np.asarray(expected_position_cm, dtype=float)
    actual = np.asarray(actual_position_cm, dtype=float)
    previous = np.asarray(previous_states_cm_inv3_s_inv, dtype=float)
    if (expected.shape != actual.shape or expected.ndim != 1 or not np.all(np.isfinite(expected))
            or not np.all(np.isfinite(actual))):
        raise ValueError("track and local-state positions must be aligned finite vectors")
    tolerance = 1.0e-12 * max(1.0, float(np.max(np.abs(expected))))
    if not np.allclose(actual, expected, rtol=0.0, atol=tolerance):
        raise ValueError("local state sample position must equal the source track midpoint")
    # Registered hardening: strict nonnegative integer sample index; the
    # saved arm accepted bools and whole-number floats here.
    if (isinstance(local_state_sample_index, (bool, np.bool_))
            or not isinstance(local_state_sample_index, (int, np.integer))
            or local_state_sample_index < 0):
        raise ValueError("local_state_sample_index must be a zero-based nonnegative integer (registered hardening)")
    if previous.ndim != 1 or not np.all(np.isfinite(previous)) or np.any(previous < 0.0):
        raise ValueError("state, normalization, volume, and accumulated deposition must be finite")
    _finite_scalar(nlaunch, "nlaunch", positive=True)
    _finite_scalar(beam_grid_cell_volume_cm3, "beam_grid_cell_volume_cm3", positive=True)
    _finite_scalar(previous_deposited_particles_per_s, "previous_deposited_particles_per_s")
    _finite_scalar(segment_duration_s, "segment_duration_s")
    if not isinstance(n4_cell_update_record, Mapping):
        raise ValueError("each n4_cell_update_records item must be a mapping")
    required = {
        "local_state_sample_index", "input_neutral_states_cm_inv3_s_inv", "dt_s",
        "next_states_cm_inv3_s_inv", "dens_cm_inv3", "photons_per_cm3_s", "n4_result_provenance",
    }
    if required - set(n4_cell_update_record):
        raise ValueError("N4 update record misses a declared handoff field")
    record_index = n4_cell_update_record["local_state_sample_index"]
    if isinstance(record_index, (bool, np.bool_)) or not isinstance(record_index, (int, np.integer)):
        raise ValueError("N4 update record local_state_sample_index must be a plain integer (registered hardening)")
    if int(record_index) != int(local_state_sample_index):
        raise ValueError("N4 local_state_sample_index must be source-order zero-based")
    if (not isinstance(n4_cell_update_record["n4_result_provenance"], str)
            or not n4_cell_update_record["n4_result_provenance"].strip()):
        raise ValueError("N4 update record requires nonempty caller-owned result provenance")
    record_previous = np.asarray(n4_cell_update_record["input_neutral_states_cm_inv3_s_inv"], dtype=float)
    if record_previous.shape != previous.shape or not np.array_equal(record_previous, previous):
        raise ValueError("N4 update record must carry the exact prior N3 state")
    try:
        record_dt = float(n4_cell_update_record["dt_s"])
    except (TypeError, ValueError) as error:
        raise ValueError("N4 update record dt_s must be a finite number (registered hardening)") from error
    if not np.isfinite(record_dt) or not np.isclose(record_dt, float(segment_duration_s), rtol=1.0e-12, atol=0.0):
        raise ValueError("N4 update record dt_s must equal the track segment duration")
    next_states = np.asarray(n4_cell_update_record["next_states_cm_inv3_s_inv"], dtype=float)
    density = np.asarray(n4_cell_update_record["dens_cm_inv3"], dtype=float)
    try:
        photons = float(n4_cell_update_record["photons_per_cm3_s"])
    except (TypeError, ValueError) as error:
        raise ValueError("N4 update record photons_per_cm3_s must be a finite number (registered hardening)") from error
    # Registered hardening: the saved arm's operator contract declares the
    # density and photon outputs nonnegative, but its implementation only
    # rejected negative next states; negative density or photons fail closed.
    if (next_states.shape != previous.shape or density.shape != previous.shape
            or not np.all(np.isfinite(next_states)) or not np.all(np.isfinite(density))
            or not np.isfinite(photons) or np.any(next_states < 0.0)
            or np.any(density < 0.0) or photons < 0.0):
        raise ValueError("N4 handoff fields must be finite, nonnegative and state-shaped (registered hardening)")
    segment_flux = float((np.sum(previous) - np.sum(next_states)) / float(nlaunch))
    deposited = segment_flux * float(beam_grid_cell_volume_cm3)
    return {
        "next_states_cm_inv3_s_inv": next_states,
        "normalized_density_cm_inv3": density / float(nlaunch),
        "normalized_photons_per_cm3_s": photons / float(nlaunch),
        "segment_flux_per_cm3_s": segment_flux,
        "deposited_particles_per_s": float(previous_deposited_particles_per_s) + deposited,
    }
