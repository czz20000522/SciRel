"""Atomic-hydrogen Saha equilibrium population on the saved scientific branch.

The saved KN1DPy ``nh_saha`` slice uses constants 3.310e-28 and 13.6057 eV.
Its non-scientific branches use a 1e32 sentinel; this callable rejects those
inputs. The comparison is historical development evidence, not a qualified D1
freeze or external validation of the Saha model.
"""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_h_saha_equilibrium_population"]


def _real_vector(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(isinstance(item, (bool, np.bool_))
                    for item in np.asarray(value, dtype=object).flat)
        ):
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def evaluate_h_saha_equilibrium_population(
    electron_density_m3, electron_temperature_ev, principal_level,
):
    """Return the level population density in m^-3 for paired 1-D samples."""
    density = _real_vector(electron_density_m3, "electron_density_m3")
    temperature = _real_vector(electron_temperature_ev, "electron_temperature_ev")
    if density.ndim != 1 or temperature.ndim != 1 or density.size == 0:
        raise ValueError("electron density and temperature must be non-empty one-dimensional arrays")
    if density.shape != temperature.shape:
        raise ValueError("electron density and temperature must have the same shape")
    if not np.all(np.isfinite(density)) or not np.all(np.isfinite(temperature)):
        raise ValueError("electron density and temperature must be finite")

    try:
        raw_level = np.asarray(principal_level)
        if raw_level.ndim != 0 or raw_level.dtype.kind not in "iuf":
            raise ValueError
        if raw_level.dtype.kind in "iu":
            level = int(raw_level)
            level_value = None
        else:
            level_value = float(raw_level)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("principal_level must be a scalar integer") from exc
    if level_value is not None:
        if not np.isfinite(level_value) or not level_value.is_integer() or level_value < 1:
            raise ValueError("principal_level must be an integer >= 1")
        level = int(level_value)
    if level < 1:
        raise ValueError("principal_level must be an integer >= 1")

    if np.any(density <= 0.0) or np.any(density >= 1.0e32):
        raise ValueError("electron density is outside the scientific domain")
    if np.any(temperature <= 0.0) or np.any(temperature >= 1.0e32):
        raise ValueError("electron temperature is outside the scientific domain")

    try:
        level_squared = float(level * level)
    except OverflowError as exc:
        raise ValueError("principal_level is outside the representable domain") from exc
    population = (
        density * (3.310e-28 * density) * level_squared
        * np.exp(13.6057 / (level_squared * temperature))
        / temperature**1.5
    )
    if not np.all(np.isfinite(population)) or np.any(population <= 0.0):
        raise ValueError("Saha population is not finite and positive for the supplied inputs")
    return population
