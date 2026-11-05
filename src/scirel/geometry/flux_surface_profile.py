"""One-dimensional linear profiles indexed by poloidal flux."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_flux_surface_profile"]


def evaluate_flux_surface_profile(
    *, psi_samples, values, target, left=None, right=None
) -> dict[str, np.ndarray]:
    """Sort a profile, remove duplicate coordinates, and evaluate it linearly."""
    coordinates = np.asarray(psi_samples, dtype=float).ravel()
    samples = np.asarray(values, dtype=float).ravel()
    query = np.asarray(target, dtype=float)
    if coordinates.size != samples.size or coordinates.size < 2:
        raise ValueError("psi_samples and values require at least two paired samples")
    if not (
        np.isfinite(coordinates).all() and np.isfinite(samples).all() and np.isfinite(query).all()
    ):
        raise ValueError("profile coordinates, values, and target must be finite")
    order = np.argsort(coordinates)
    coordinates, samples = coordinates[order], samples[order]
    coordinates, first = np.unique(coordinates, return_index=True)
    samples = samples[first]
    if coordinates.size < 2:
        raise ValueError("psi samples do not span a usable interval")
    left_value = float(samples[0] if left is None else left)
    right_value = float(samples[-1] if right is None else right)
    if not np.isfinite(left_value) or not np.isfinite(right_value):
        raise ValueError("profile endpoint values must be finite")
    result = np.interp(query.ravel(), coordinates, samples, left=left_value, right=right_value)
    return {
        "values": result.reshape(query.shape),
        "psi": coordinates,
        "profile_values": samples,
    }


scientific_function = evaluate_flux_surface_profile
