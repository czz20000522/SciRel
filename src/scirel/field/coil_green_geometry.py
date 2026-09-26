"""GSEQ filament-coil observation geometry and elliptic modulus.

Source: GSEQ filament-coil Green geometry (``fun_Bfield`` observation
prologue): the observation radius is first regularized by the source's axis
offset ``r0 <- r0 + 1e-8`` -- an explicit contract of the original
implementation that must not be silently replaced by downstream
special-function handling -- and then each coil's squared elliptic modulus
``m = 4*r0*rl/((r0+rl)^2+(z0-zl)^2)`` and Green distance denominator
``sqrt((r0+rl)^2+(z0-zl)^2)`` are produced.  This operator only generates the
geometric quantities; it neither evaluates ``K, E`` nor the field responses.

The regularized radius is the value downstream GSEQ Green operators must
receive; pairing with the integrated ``evaluate_filament_coil_green_field``
uses the same offset once (the response operator consumes the already
regularized radius and does not add the offset again).
"""
from __future__ import annotations

import numpy as np

__all__ = ["compute_axisymmetric_coil_modulus"]

SOURCE_AXIS_OFFSET_M = 1.0e-8


def compute_axisymmetric_coil_modulus(observation_radius_m, observation_z_m, coil_radius_m, coil_z_m):
    """Return source-regularized radius, squared modulus, and Green denominator.

    A raw observation radius in ``(-1e-8, 0)`` would turn positive only
    through the axis offset and silently re-labels a point behind the axis;
    this port rejects such radii explicitly (registered hardening: the saved
    implementation accepts them because only the offset result is checked).
    """
    radius = float(observation_radius_m) + SOURCE_AXIS_OFFSET_M
    coil_radius = np.asarray(coil_radius_m, dtype=float)
    coil_z = np.asarray(coil_z_m, dtype=float)
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError("observation coordinates must be finite after source axis offset")
    if float(observation_radius_m) < 0.0:
        raise ValueError(
            "observation_radius_m must be nonnegative: a negative raw radius "
            "within the offset width would be silently regularized to a "
            "positive one (registered hardening)")
    if coil_radius.shape != coil_z.shape or coil_radius.ndim != 1 or np.any(coil_radius <= 0.0) or not np.all(np.isfinite(coil_radius)) or not np.all(np.isfinite(coil_z)):
        raise ValueError("coil radii/z coordinates must be finite same-shape vectors with positive radii")
    denominator_m = (radius + coil_radius) ** 2 + (observation_z_m - coil_z) ** 2
    modulus_squared = 4.0 * radius * coil_radius / denominator_m
    distance = np.sqrt(denominator_m)
    # Registered hardening: finite inputs with extreme magnitudes (e.g.
    # r0 = rl = 1e308) overflow the squared sums and produce non-finite
    # geometry; the saved implementation would hand such NaN/Inf downstream
    # silently, this port fails closed.
    if not np.all(np.isfinite(modulus_squared)) or not np.all(np.isfinite(distance)):
        raise ValueError(
            "coil geometry overflowed to non-finite modulus/distance; "
            "finite but extreme input magnitudes are rejected (registered "
            "hardening)")
    return radius, modulus_squared, distance
