"""FIDASIM mc_nbi source-plane ray construction and aperture acceptance.

Source: FIDASIM ``mc_nbi`` source-plane branch -- map caller-provided uniform
source samples and standard-normal divergence samples into the beam-coordinate
source point and unit ray, then test acceptance against every rectangular
(shape=1) or elliptical (shape=2) aperture.  The rectangle maps the uniform
pair affinely onto the source half-widths; the ellipse uses ``sqrt(u)`` and
``2*pi*v``.  The ray transverse components carry the focusing term
``-source/focus`` plus the ``tan(divergence * normal)`` divergence term, and
the accepted ray is normalized after the beam-basis transform.

Registered hardenings against the saved arm: focus lengths must be finite
(the saved arm checks only exact zero and lets NaN through), divergence
standard deviations must be finite (the saved arm propagates NaN ``tan``
values silently), half-widths must be finite, the scalar source shape rejects bools (Python and
NumPy), the transformed ray's norm must be finite and nonzero (an overflowing
squared norm would collapse ``beam_ray / Inf`` to a zero "unit" ray), and
every output must stay finite for finite inputs.
"""
from __future__ import annotations

import numpy as np

__all__ = ["construct_nbi_source_ray"]


def construct_nbi_source_ray(source_uniform, divergence_normal, source_shape, half_width_y_cm, half_width_z_cm, focus_y_cm, focus_z_cm, divergence_y_rad, divergence_z_rad, aperture_distance_cm, aperture_shape, aperture_offset_y_cm, aperture_offset_z_cm, aperture_half_width_y_cm, aperture_half_width_z_cm, beam_basis, beam_source_cm):
    """Map caller random variates to the beam-coordinate source point, unit ray and aperture acceptance."""
    uniform, normal = np.asarray(source_uniform, dtype=float), np.asarray(divergence_normal, dtype=float)
    basis, origin = np.asarray(beam_basis, dtype=float), np.asarray(beam_source_cm, dtype=float)
    apertures = [np.asarray(value) for value in (aperture_distance_cm, aperture_shape, aperture_offset_y_cm, aperture_offset_z_cm, aperture_half_width_y_cm, aperture_half_width_z_cm)]
    if (uniform.shape != (2,) or not np.all(np.isfinite(uniform)) or np.any((uniform < 0.0) | (uniform > 1.0))
            or normal.shape != (2,) or not np.all(np.isfinite(normal))
            or isinstance(source_shape, (bool, np.bool_)) or source_shape not in (1, 2)
            or not np.isscalar(half_width_y_cm) or not np.isfinite(half_width_y_cm) or half_width_y_cm <= 0.0
            or not np.isscalar(half_width_z_cm) or not np.isfinite(half_width_z_cm) or half_width_z_cm <= 0.0
            or not np.isfinite(focus_y_cm) or focus_y_cm == 0.0
            or not np.isfinite(focus_z_cm) or focus_z_cm == 0.0
            or not np.isfinite(divergence_y_rad) or not np.isfinite(divergence_z_rad)
            or basis.shape != (3, 3) or not np.all(np.isfinite(basis))
            or origin.shape != (3,) or not np.all(np.isfinite(origin))
            or any(value.ndim != 1 or value.shape != apertures[0].shape for value in apertures)
            or not all(np.all(np.isfinite(value)) for value in apertures)):
        raise ValueError("source, aperture, or beam-coordinate contract is invalid")
    if source_shape == 1:
        xyz_source = np.array([0.0, half_width_y_cm * 2.0 * (uniform[0] - 0.5), half_width_z_cm * 2.0 * (uniform[1] - 0.5)])
    else:
        rho, theta = np.sqrt(uniform[0]), 2.0 * np.pi * uniform[1]
        xyz_source = np.array([0.0, half_width_y_cm * rho * np.cos(theta), half_width_z_cm * rho * np.sin(theta)])
    xyz_ray = np.array([1.0, -xyz_source[1] / focus_y_cm + np.tan(divergence_y_rad * normal[0]), -xyz_source[2] / focus_z_cm + np.tan(divergence_z_rad * normal[1])])
    accepted = True
    for distance, shape, offset_y, offset_z, width_y, width_z in zip(*apertures):
        point = xyz_ray * distance + xyz_source
        if shape == 1:
            accepted &= abs(point[1] - offset_y) <= width_y and abs(point[2] - offset_z) <= width_z
        elif shape == 2:
            accepted &= ((point[1] - offset_y) * width_z) ** 2 + ((point[2] - offset_z) * width_y) ** 2 <= (width_y * width_z) ** 2
        else:
            raise ValueError("aperture_shape values must be 1 or 2")
    beam_ray = basis @ xyz_ray
    norm = np.linalg.norm(beam_ray)
    # Registered hardening: the saved arm normalizes Inf/NaN beam rays
    # silently.  An overflowing squared norm collapses beam_ray / Inf to the
    # zero vector, which still passes a finiteness check while violating the
    # unit-norm contract, so the norm itself must be finite and nonzero.
    if not np.isfinite(norm) or norm == 0:
        raise ValueError(
            "beam-basis ray norm overflowed or degenerated for finite but "
            "extreme input magnitudes (registered hardening)")
    source_beam = basis @ xyz_source + origin
    unit_ray = beam_ray / norm
    # Registered hardening: the saved arm normalizes inf/NaN beam rays
    # silently (e.g. an extreme half-width divided by a small focus overflows
    # the transverse ray components); every output must stay finite.
    if not (np.all(np.isfinite(source_beam)) and np.all(np.isfinite(unit_ray))):
        raise ValueError(
            "source-ray outputs are non-finite for finite but extreme input "
            "magnitudes (registered hardening)")
    return source_beam, unit_ray, bool(accepted)
