"""FIDASIM neutral-beam full/half/third energy velocity scaling.

Source: FIDASIM ``mc_nbi``/``mc_nbi_cell`` — one birth particle's velocity
direction (a unit ray) is scaled by the injection speed divided by the square
root of its full/half/third energy-component index.  The source divides by
``sqrt(real(efrac))`` where ``efrac`` is default-REAL (Float32); that divisor
precision is preserved verbatim, so the result differs in the last ulps from
a Float64 divisor.  No clamping, no positivity repair: the caller supplies a
unit ray, a positive injection speed and one of the component indices 1/2/3.
"""
from __future__ import annotations

import numpy as np

__all__ = ["scale_nbi_velocity_for_energy_component"]


def scale_nbi_velocity_for_energy_component(unit_ray, injection_speed_cm_s, energy_component):
    """Return vnbi = unit_ray * vinj / sqrt(efrac) from mc_nbi/mc_nbi_cell.

    Registered hardening against the saved arm: the injection speed must be
    a finite positive scalar (the source's ``vinj <= 0`` check lets NaN
    through), the energy component must be exactly the integer 1, 2 or 3
    (bools and float 1.0 pass the source's tuple-membership test), and the
    result must stay finite.
    """
    ray = np.asarray(unit_ray, dtype=float)
    if (ray.shape != (3,) or not np.all(np.isfinite(ray))
            or not np.isclose(np.linalg.norm(ray), 1.0, rtol=1.0e-12, atol=1.0e-12)
            or isinstance(injection_speed_cm_s, bool) or not np.isscalar(injection_speed_cm_s)
            or not np.isfinite(injection_speed_cm_s) or injection_speed_cm_s <= 0.0
            or isinstance(energy_component, bool)
            or not isinstance(energy_component, (int, np.integer))
            or energy_component not in (1, 2, 3)):
        raise ValueError("unit ray, injection speed, or energy component is invalid")
    # Source uses sqrt(real(efrac)); preserve its default-REAL (Float32) divisor.
    result = ray * injection_speed_cm_s / np.sqrt(np.float32(energy_component))
    if not np.all(np.isfinite(result)):
        raise ValueError(
            "velocity scaling overflowed to a non-finite value for finite but "
            "extreme input magnitudes (registered hardening)")
    return result
