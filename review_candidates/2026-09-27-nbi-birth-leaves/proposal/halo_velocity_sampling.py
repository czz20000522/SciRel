"""FIDASIM ``mc_halo`` thermal-Maxwellian velocity mapping.

Source: FIDASIM ``mc_halo`` — one thermal-halo neutral birth velocity is the
plasma rotation velocity plus a thermal-speed-scaled standard-normal draw.
The randomness stays caller-owned: the standard-normal triplet is an explicit
input, so the mapping is a deterministic, replayable function of its inputs.
The thermal speed uses the source's ``sqrt(Ti/2 / (scale * mass))`` form in
the velocity-squared-to-keV-per-amu convention.
"""
from __future__ import annotations

import numpy as np

__all__ = ["sample_halo_velocity"]


def sample_halo_velocity(*, plasma_rotation_cm_s, ion_temperature_kev, ion_mass_amu,
                         velocity_squared_to_kev_per_amu, standard_normal_draw):
    """Return one source-shaped halo velocity from caller-owned normal variates."""
    rotation = np.asarray(plasma_rotation_cm_s, dtype=float)
    draw = np.asarray(standard_normal_draw, dtype=float)
    if (rotation.shape != (3,) or draw.shape != (3,) or not np.all(np.isfinite(rotation))
            or not np.all(np.isfinite(draw)) or ion_temperature_kev < 0.0
            or ion_mass_amu <= 0.0 or velocity_squared_to_kev_per_amu <= 0.0
            or not np.isfinite(ion_temperature_kev) or not np.isfinite(ion_mass_amu)
            or not np.isfinite(velocity_squared_to_kev_per_amu)):
        raise ValueError("finite 3-vectors, nonnegative temperature, and positive mass/conversion are required")
    denominator = velocity_squared_to_kev_per_amu * ion_mass_amu
    # Registered contract normalization: a finite-but-underflowed denominator
    # (product rounding to exactly 0.0) makes the source arm raise a bare
    # ZeroDivisionError from the scalar division.  The SciRel failure
    # contract is ValueError for every rejected input, so the underflow is
    # detected and converted here; this is a declared divergence in exception
    # type only, not in accepted domain.
    if denominator == 0.0 or not np.isfinite(denominator):
        raise ValueError(
            "velocity_squared_to_kev_per_amu * ion_mass_amu underflowed or "
            "overflowed to a non-representable denominator (registered "
            "hardening; the saved arm raises a bare ZeroDivisionError here)")
    thermal_speed_cm_s = np.sqrt(
        ion_temperature_kev * 0.5 / denominator
    )
    halo_velocity = rotation + thermal_speed_cm_s * draw
    # Registered hardening: finite extreme draws/magnitudes can overflow the
    # product or sum; the saved arm would return Inf silently.
    if not np.all(np.isfinite(halo_velocity)) or not np.isfinite(thermal_speed_cm_s):
        raise ValueError(
            "halo velocity sampling overflowed to non-finite values for "
            "finite but extreme input magnitudes (registered hardening)")
    return {
        "halo_velocity_cm_s": halo_velocity,
        "thermal_speed_cm_s": thermal_speed_cm_s,
    }
