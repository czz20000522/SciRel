"""Scalar closed-form Green response for a collection of circular coils."""
from __future__ import annotations

import numpy as np

MU0_OVER_2PI = 2.0e-7


def evaluate_filament_coil_green_field(regularized_radius_m, observation_z_m, coil_radius_m, coil_z_m, current_a, turns, modulus_squared, complete_k, complete_e):
    """Return summed ``(psi, B_R, B_Z)`` for aligned coil arrays.

    ``regularized_radius_m`` is already offset by the geometry operator.  The
    response therefore applies no second axis shift.  Coincident rings are
    singular and rejected before any nonfinite response can escape.
    """
    radius = float(regularized_radius_m)
    observation_z_m = float(observation_z_m)
    arrays = tuple(np.asarray(value, dtype=float) for value in (
        coil_radius_m, coil_z_m, current_a, turns, modulus_squared, complete_k, complete_e
    ))
    coil_radius, coil_z, current, winding, modulus, k_value, e_value = arrays
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError("regularized observation coordinates must be finite and positive in radius")
    if any(value.ndim != 1 or value.shape != coil_radius.shape for value in arrays):
        raise ValueError("coil inputs and elliptic values must be same-shape vectors with valid geometry")
    finite_geometry = all(np.all(np.isfinite(value)) for value in (coil_radius, coil_z, current, winding, modulus))
    if (not finite_geometry or np.any(coil_radius <= 0.0) or np.any(modulus <= 0.0)
            or np.any(modulus > 1.0) or np.any(~np.isfinite(e_value))
            or np.any(~np.isfinite(k_value) & (modulus != 1.0))):
        raise ValueError("coil inputs and elliptic values must be same-shape vectors with valid geometry")
    dz = observation_z_m - coil_z
    with np.errstate(over="ignore", divide="raise", invalid="raise"):
        distance = np.hypot(radius + coil_radius, dz)
        separation2 = (radius - coil_radius) ** 2 + dz**2
        if np.any(separation2 <= 0.0) or np.any(modulus >= 1.0):
            raise ValueError("singular coil geometry: observation point on a filament ring")
        factor = MU0_OVER_2PI * winding * current
        flux_terms = factor / np.sqrt(modulus) * np.sqrt(radius * coil_radius) * ((2.0 - modulus) * k_value - 2.0 * e_value)
        radial_terms = factor * dz / radius / distance * ((radius**2 + coil_radius**2 + dz**2) / separation2 * e_value - k_value)
        axial_terms = factor / distance * ((coil_radius**2 - radius**2 - dz**2) / separation2 * e_value + k_value)
        result = tuple(float(np.sum(terms)) for terms in (flux_terms, radial_terms, axial_terms))
    if not all(np.isfinite(value) for value in result):
        raise ValueError("filament-coil response overflowed to a non-finite value")
    return result


__all__ = ["evaluate_filament_coil_green_field"]
