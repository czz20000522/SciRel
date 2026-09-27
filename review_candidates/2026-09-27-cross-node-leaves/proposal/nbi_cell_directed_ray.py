"""Deterministic FIDASIM mc_nbi_cell source-to-cell ray relation.

Source: FIDASIM ``mc_nbi_cell`` -- for one beam-grid cell, transform the
cell center (plus offset) into beam coordinates with the inverse beam basis,
form the unit ray from the source point, test aperture acceptance per
aperture (rectangle shape=1 / ellipse shape=2), and compute the Gaussian
divergence trajectory weight.  The velocity uses the Float32 energy-component
divisor shared with the other N2 leaves; the source's theta_z uses ``focy``
(not ``focz``) -- a recorded quirk that the saved package's own test pins.

Registered hardening: the returned velocity, unit ray and weight must stay
finite; the saved arm would return Inf/NaN silently for finite extreme
inputs.
"""
from __future__ import annotations

import numpy as np

__all__ = ["nbi_cell_directed_ray"]


def nbi_cell_directed_ray(cell_center_uvw_cm, cell_offset_cm, source_xyz_cm, beam_origin_uvw_cm, inverse_beam_basis, beam_basis, injection_speed_cm_s, neutral_type, aperture_distance_cm, aperture_shape, aperture_offset_y_cm, aperture_offset_z_cm, aperture_half_width_y_cm, aperture_half_width_z_cm, focus_y_cm, focus_z_cm, divergence_y_rad, divergence_z_rad):
    c, o, s, b = (np.asarray(x, float) for x in (cell_center_uvw_cm, cell_offset_cm, source_xyz_cm, beam_origin_uvw_cm))
    inv, bas = np.asarray(inverse_beam_basis, float), np.asarray(beam_basis, float)
    ap = [np.asarray(x) for x in (aperture_distance_cm, aperture_shape, aperture_offset_y_cm, aperture_offset_z_cm, aperture_half_width_y_cm, aperture_half_width_z_cm)]
    dy, dz = np.asarray(divergence_y_rad, float), np.asarray(divergence_z_rad, float)
    if (any(x.shape != (3,) or not np.all(np.isfinite(x)) for x in (c, o, s, b))
            or inv.shape != (3, 3) or bas.shape != (3, 3)
            or neutral_type not in (1, 2, 3) or injection_speed_cm_s <= 0
            or not np.isfinite(focus_y_cm) or not np.isfinite(focus_z_cm)
            or focus_y_cm == 0 or focus_z_cm == 0 or dy.shape != (3,) or dz.shape != (3,)
            or np.any(dy <= 0) or np.any(dz <= 0)
            or any(x.ndim != 1 or x.shape != ap[0].shape for x in ap)
            or not all(np.all(np.isfinite(x)) for x in ap)):
        raise ValueError("invalid NBI cell-ray contract")
    receiver = inv @ (c + o - b)
    ray = receiver - s
    norm = np.linalg.norm(ray)
    if norm == 0:
        raise ValueError("source and receiver must differ")
    ray /= norm
    accepted = True
    for d, shape, oy, oz, wy, wz in zip(*ap):
        point = ray * d + s
        if shape == 1:
            accepted &= abs(point[1] - oy) <= wy and abs(point[2] - oz) <= wz
        elif shape == 2:
            accepted &= ((point[1] - oy) * wz) ** 2 + ((point[2] - oz) * wy) ** 2 <= (wy * wz) ** 2
        else:
            raise ValueError("aperture_shape values must be 1 or 2")
    direction = bas @ ray
    direction /= np.linalg.norm(direction)
    velocity = injection_speed_cm_s * direction / np.sqrt(np.float32(neutral_type))
    vy, vz = ray[1] / ray[0], ray[2] / ray[0]
    ty, tz = np.arctan(vy + s[1] / focus_y_cm), np.arctan(vz + s[2] / focus_y_cm)
    index = neutral_type - 1
    py = np.exp(-ty ** 2 / (2 * dy[index] ** 2)) / ((1 + (vy + s[1] / focus_y_cm) ** 2) * np.sqrt(2 * dy[index] ** 2))
    pz = np.exp(-tz ** 2 / (2 * dz[index] ** 2)) / ((1 + (vz + s[2] / focus_y_cm) ** 2) * np.sqrt(2 * dz[index] ** 2))
    if not (np.all(np.isfinite(velocity)) and np.all(np.isfinite(ray))
            and np.isfinite(py) and np.isfinite(pz)):
        raise ValueError(
            "NBI cell-ray outputs are non-finite for finite but extreme "
            "input magnitudes (registered hardening)")
    weight = py * pz
    # Registered hardening: py and pz can each be finite while their product
    # overflows (e.g. divergences near the float underflow make the
    # normalization denominators tiny); the saved arm returns Inf silently.
    # Non-finite focus lengths are also rejected (the saved arm checks only
    # for exact zero).
    if not np.isfinite(weight):
        raise ValueError(
            "trajectory weight overflowed to a non-finite value for finite "
            "but extreme input magnitudes (registered hardening)")
    # Registered hardening: accepted rays must carry a strictly positive
    # weight; extreme divergences underflow the Gaussian exponentials to 0.0
    # (the saved arm returns accepted=True with weight 0.0 silently).
    if accepted and weight <= 0.0:
        raise ValueError(
            "accepted ray has a non-positive trajectory weight for finite "
            "but extreme divergences (registered hardening)")
    return {"receiver_xyz_cm": receiver, "unit_ray_xyz": ray, "velocity_uvw_cm_s": velocity, "accepted": bool(accepted), "trajectory_weight": weight}
