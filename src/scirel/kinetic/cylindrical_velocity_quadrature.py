"""Cylindrical velocity-space quadrature on explicit normalized meshes.

One leaf recovered from the saved KN1DPy ``make_dvr_dvx`` slice (source anchor
``KN1DPy/make_dvr_dvx.py:20-123``), integrated as
:func:`make_cylindrical_velocity_quadrature`: from strictly increasing
normalized radial-speed and axial-velocity meshes it builds the ghost-extended
half-cell faces, the annular radial measure, the ``(nvr, nvx)`` cylindrical
cell volumes, the ghosted finite-volume difference coefficients, the speed
squared, and the positive/negative axial index ranges.

This is the N1 preparation relation whose ``volume`` output is the
``cylindrical_volume`` port consumed by the collisions-domain Maxwellian
relative-speed rate average and by the shifted-Maxwellian seed; the composition
is covered by direct tests on both consumer sides.

**The construction, exactly as the saved source defines it.**  The radial mesh
is extended by mirroring the last point (``2*vr[-1] - vr[-2]``) and the axial
mesh by mirroring both ends; cell faces are the midpoints of the extended
nodes, with the innermost radial face fixed at ``0``.  ``radial_measure`` is
``pi*(r_right^2 - r_left^2)`` per cell, ``volume`` is
``radial_measure[:, None] * dvx[None, :]``, and the four-pi measure is
``4/3*pi*(r_right^3 - r_left^3)``.  The ghosted coefficient arrays carry
``1/dvx``, ``vx/dvx`` and ``vr/dvr`` in their interior and exact zeros on the
boundary shell.  The sign index ranges locate the strictly positive and
strictly negative axial velocities.

**One repair relative to the saved implementation, documented.**  The saved
document declares non-finite inputs fail closed, but its implementation only
checked monotonicity and sizes: a ``NaN`` mesh point propagated silently into
every output.  This module rejects non-finite meshes by parameter name, so the
declared contract is true.  Everything else -- the construction, field set,
shapes and index semantics -- is preserved exactly.

Evidence ceiling: the maintained tests re-derive the annular measure, faces,
volumes, ghost shells, speed squared and sign indices by hand on a different
mesh than the saved package test, assert the box-partition closure, and cover
the input contract and the composition with the Maxwellian rate average; the
environment-gated replay pins the saved implementation by SHA-256 and compares
every field.  The saved bundle sits in the re-review archive (strict D1
qualification withdrawn), so the replay is bounded historical development
evidence only.  This module does not generate or adapt the meshes themselves
and does not decide whether the source's ghost-face convention fits any
downstream scheme beyond the relations documented here.
"""
from __future__ import annotations

import numpy as np

__all__ = ["make_cylindrical_velocity_quadrature"]


def _finite_increasing(name, value):
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or array.size < 2 or not bool(np.all(np.isfinite(array))):
        raise ValueError(f"{name} must be a finite one-dimensional array of length at least two")
    if bool(np.any(np.diff(array) <= 0.0)):
        raise ValueError(f"{name} must be strictly increasing")
    return array


def make_cylindrical_velocity_quadrature(*, vr, vx):
    """Return the source-order integration weights, ghosted differences and
    sign index ranges for the normalized cylindrical velocity mesh.

    Parameters
    ----------
    vr, vx
        Finite strictly increasing one-dimensional meshes (length >= 2) of the
        normalized radial speed and axial velocity.  ``vx`` must contain at
        least one strictly negative and one strictly positive entry.

    Returns
    -------
    dict
        The saved source's field set: ``radial_measure``,
        ``radial_four_pi_measure``, ``dvx``, ``vr_left``, ``vr_right``,
        ``vx_left``, ``vx_right``, ``volume``, ``inv_dvx_ghost``,
        ``vx_over_dvx_ghost``, ``vr_over_dvr_ghost``, ``speed_squared``,
        ``positive_vx_indices``, ``positive_vx_first_index``,
        ``positive_vx_last_index``, ``negative_vx_indices``,
        ``negative_vx_first_index``, ``negative_vx_last_index``.

    Raises
    ------
    ValueError
        If a mesh is not a finite strictly increasing one-dimensional array of
        length at least two, or if ``vx`` does not contain both negative and
        positive velocities.
    """
    radial = _finite_increasing("vr", vr)
    axial = _finite_increasing("vx", vx)
    radial_extended = np.append(radial, 2.0 * radial[-1] - radial[-2])
    radial_mid = np.concatenate(((0.0,), 0.5 * (radial_extended + np.roll(radial_extended, -1))))
    radial_left, radial_right = radial_mid[: radial.size], np.roll(radial_mid, -1)[: radial.size]
    axial_extended = np.concatenate(
        ((2.0 * axial[0] - axial[1],), axial, (2.0 * axial[-1] - axial[-2],))
    )
    axial_right = 0.5 * (np.roll(axial_extended, -1) + axial_extended)[1 : axial.size + 1]
    axial_left = 0.5 * (np.roll(axial_extended, 1) + axial_extended)[1 : axial.size + 1]
    dvr, dvx = radial_right - radial_left, axial_right - axial_left
    radial_measure = np.pi * (radial_right**2 - radial_left**2)
    volume = radial_measure[:, None] * dvx
    ghost_shape = (radial.size + 2, axial.size + 2)
    inv_dvx, vx_over_dvx, vr_over_dvr = (np.zeros(ghost_shape) for _ in range(3))
    inv_dvx[1:-1, 1:-1] = 1.0 / dvx
    vx_over_dvx[1:-1, 1:-1] = axial / dvx
    vr_over_dvr[1:-1, 1:-1] = (radial / dvr)[:, None]
    positive, negative = np.flatnonzero(axial > 0.0), np.flatnonzero(axial < 0.0)
    if positive.size == 0 or negative.size == 0:
        raise ValueError("vx must contain both negative and positive velocities")
    return {
        "radial_measure": radial_measure,
        "radial_four_pi_measure": 4.0 / 3.0 * np.pi * (radial_right**3 - radial_left**3),
        "dvx": dvx,
        "vr_left": radial_left,
        "vr_right": radial_right,
        "vx_left": axial_left,
        "vx_right": axial_right,
        "volume": volume,
        "inv_dvx_ghost": inv_dvx,
        "vx_over_dvx_ghost": vx_over_dvx,
        "vr_over_dvr_ghost": vr_over_dvr,
        "speed_squared": radial[:, None] ** 2 + axial**2,
        "positive_vx_indices": positive,
        "positive_vx_first_index": int(positive[0]),
        "positive_vx_last_index": int(positive[-1]),
        "negative_vx_indices": negative,
        "negative_vx_first_index": int(negative[0]),
        "negative_vx_last_index": int(negative[-1]),
    }
