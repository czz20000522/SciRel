"""FIDASIM fast-ion energy relative to local plasma rotation.

Source: FIDASIM ``erel`` -- one fast ion's kinetic energy in the local
plasma-rotation frame: ``E_rel = v2_to_E_per_amu * A * |v_i - v_rot|^2`` in
keV, with the relative velocity vector returned alongside.

Registered hardening against the saved arm: the relative-beam-energy output
must stay finite; the saved arm would return Inf silently for finite but
extreme velocities.
"""
from __future__ import annotations

import numpy as np

__all__ = ["calculate_fast_ion_relative_energy"]


def calculate_fast_ion_relative_energy(*, ion_velocity_cm_s, plasma_rotation_cm_s, ion_mass_amu, velocity_squared_to_kev_per_amu):
    """Return source `erel = v2_to_E_per_amu * A * |v_i-v_rot|^2` in keV."""
    ion_velocity = np.asarray(ion_velocity_cm_s, dtype=float)
    rotation = np.asarray(plasma_rotation_cm_s, dtype=float)
    if ion_velocity.shape != (3,) or rotation.shape != (3,) or not np.all(np.isfinite(ion_velocity)) or not np.all(np.isfinite(rotation)):
        raise ValueError("ion_velocity_cm_s and plasma_rotation_cm_s must be finite shape-(3,) vectors")
    if not np.isfinite(ion_mass_amu) or ion_mass_amu <= 0.0 or not np.isfinite(velocity_squared_to_kev_per_amu) or velocity_squared_to_kev_per_amu <= 0.0:
        raise ValueError("ion_mass_amu and velocity_squared_to_kev_per_amu must be finite and positive")
    relative_velocity = ion_velocity - rotation
    relative_beam_energy_kev = float(velocity_squared_to_kev_per_amu * ion_mass_amu * np.dot(relative_velocity, relative_velocity))
    if not np.isfinite(relative_beam_energy_kev):
        raise ValueError(
            "relative beam energy overflowed for finite but extreme input "
            "magnitudes (registered hardening)")
    return {"relative_velocity_cm_s": relative_velocity, "relative_beam_energy_kev": relative_beam_energy_kev}
