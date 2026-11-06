"""Cylindrical velocity-space quadrature on explicit normalized meshes.

One leaf recovered from the saved the neutral-transport formulation ``make_dvr_dvx`` slice, integrated as
:func:`make_cylindrical_velocity_quadrature`: from strictly increasing
normalized radial-speed and axial-velocity meshes it builds the ghost-extended
half-cell faces, the annular radial measure, the ``(nvr, nvx)`` cylindrical
cell volumes, the ghosted finite-volume difference coefficients, the speed
squared, and the positive/negative axial index ranges.

This is the N1 preparation relation whose ``volume`` output is the
``cylindrical_volume`` port consumed by the collisions-domain Maxwellian
relative-speed rate average; that composition is covered by direct tests.

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

**Input repairs relative to the saved implementation.**  The saved
document declares non-finite inputs fail closed, but its implementation only
checked monotonicity and sizes: a ``NaN`` mesh point propagated silently into
every output.  This module rejects non-finite meshes by parameter name, so the
declared contract is true.  Boolean, string and complex meshes are also
rejected as non-real inputs instead of being coerced or raising an unrelated
exception.  The construction, field set, shapes and index semantics on valid
real meshes are preserved exactly.

Evidence ceiling: the maintained tests re-derive the annular measure, faces,
volumes, ghost shells, speed squared and sign indices by hand on a different
mesh than the saved package test, assert the box-partition closure, and cover
the input contract and the composition with the Maxwellian rate average; a
separate intake replay pinned the saved implementation by SHA-256 and compared
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
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        array = np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc
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
    vr : real array_like, shape [nvr]
        Finite strictly increasing one-dimensional normalized radial-speed
        mesh [v/vth (caller's normalized unit)], length at least two, with
        nonnegative entries.
    vx : real array_like, shape [nvx]
        Finite strictly increasing one-dimensional normalized axial-velocity
        mesh [v/vth (caller's normalized unit)], length at least two, with at
        least one strictly negative and one strictly positive entry.

    Returns
    -------
    radial_measure : ndarray of float64, shape [nvr]
        Annular radial measure [normalized velocity-space measure].
    radial_four_pi_measure : ndarray of float64, shape [nvr]
        Four-pi radial measure [normalized velocity-space measure].
    dvx : ndarray of float64, shape [nvx]
        Axial cell widths [v/vth].
    vr_left : ndarray of float64, shape [nvr]
        Left radial faces [v/vth].
    vr_right : ndarray of float64, shape [nvr]
        Right radial faces [v/vth].
    vx_left : ndarray of float64, shape [nvx]
        Left axial faces [v/vth].
    vx_right : ndarray of float64, shape [nvx]
        Right axial faces [v/vth].
    volume : ndarray of float64, shape [nvr,nvx]
        Cell volumes [normalized velocity-space measure].
    inv_dvx_ghost : ndarray of float64, shape [nvr+2,nvx+2]
        Ghosted inverse axial widths [v/vth inverse].
    vx_over_dvx_ghost : ndarray of float64, shape [nvr+2,nvx+2]
        Ghosted axial velocity over width [dimensionless].
    vr_over_dvr_ghost : ndarray of float64, shape [nvr+2,nvx+2]
        Ghosted radial velocity over width [dimensionless].
    speed_squared : ndarray of float64, shape [nvr,nvx]
        Node speed squared [dimensionless (normalized speed squared)].
    positive_vx_indices : ndarray of int64, shape [n_positive]
        Indices of strictly positive axial velocities [dimensionless].
    positive_vx_first_index : int
        First strictly positive axial index [dimensionless].
    positive_vx_last_index : int
        Last strictly positive axial index [dimensionless].
    negative_vx_indices : ndarray of int64, shape [n_negative]
        Indices of strictly negative axial velocities [dimensionless].
    negative_vx_first_index : int
        First strictly negative axial index [dimensionless].
    negative_vx_last_index : int
        Last strictly negative axial index [dimensionless].

    Raises
    ------
    ValueError
        If a mesh is not a finite strictly increasing nonnegative
        one-dimensional array of length at least two (``vr`` is a radial-speed
        axis, so negative nodes are outside the domain), if ``vx`` does not
        contain both negative and positive velocities, or if the outputs are
        not representable in double precision for the supplied finite inputs.

    See Also
    --------
    scirel.kinetic.build_shifted_maxwellian_seed : Consume these volumes in a normalized seed.
    scirel.collisions.average_cross_section_over_maxwellian : Consume the volume measure in a rate average.

    Notes
    -----
    The radial mesh is extended by mirroring its last spacing and the axial
    mesh by mirroring both ends. Cell faces are midpoints of the extended
    nodes, with the innermost radial face fixed at zero. ``radial_measure`` is
    ``pi*(r_right**2-r_left**2)``; ``volume`` is its outer product with
    ``dvx``; and the four-pi measure is
    ``4/3*pi*(r_right**3-r_left**3)``. The ghosted coefficient arrays are zero
    on their boundary shell and contain the indicated interior ratios. Invalid
    or unrepresentable outputs are rejected rather than returned as NaN.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import make_cylindrical_velocity_quadrature
    >>> from scirel.collisions import average_cross_section_over_maxwellian
    >>> vr = np.array([0.5, 1.5])
    >>> vx = np.array([-1.5, -0.5, 0.5, 1.5])
    >>> result = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    >>> np.testing.assert_allclose(result['radial_measure'], [np.pi, 3.0 * np.pi], rtol=0, atol=0)
    >>> np.testing.assert_allclose(result['vx_left'], [-2.0, -1.0, 0.0, 1.0], rtol=0, atol=0)
    >>> assert np.all(result['inv_dvx_ghost'][0, :] == 0.0)
    >>> assert np.all(result['inv_dvx_ghost'][1:-1, 1:-1] == 1.0)
    >>> assert result['positive_vx_first_index'] == 2
    >>> rate = average_cross_section_over_maxwellian(
    ...     particle_energy_ev=np.array([0.0, 10.0]),
    ...     particle_mass_amu=1.0,
    ...     target_temperature_ev=10.0,
    ...     target_mass_amu=2.0,
    ...     vx=vx,
    ...     vr=vr,
    ...     tnorm_ev=20.0,
    ...     cylindrical_volume=result['volume'],
    ...     cross_section_m2=lambda energy: np.full_like(energy, 3.0e-20),
    ... )
    >>> assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)
    >>> try:
    ...     make_cylindrical_velocity_quadrature(vr=vr, vx=np.array([1.0, np.nan, 2.0]))
    ... except ValueError as error:
    ...     assert 'vx' in str(error)
    ... else:
    ...     raise AssertionError('a non-finite mesh must be rejected')
    """
    radial = _finite_increasing("vr", vr)
    axial = _finite_increasing("vx", vx)
    if bool(np.any(radial < 0.0)):
        raise ValueError("vr must be nonnegative")
    # The ghost-face extrapolation and the squared faces overflow for meshes
    # near the float64 ceiling; the overflow warnings are the conditions the
    # explicit representability check below reports as ValueError.
    with np.errstate(over="ignore", invalid="ignore"):
        radial_extended = np.append(radial, 2.0 * radial[-1] - radial[-2])
        radial_mid = np.concatenate(
            ((0.0,), 0.5 * (radial_extended + np.roll(radial_extended, -1)))
        )
        radial_left, radial_right = (
            radial_mid[: radial.size],
            np.roll(radial_mid, -1)[: radial.size],
        )
        axial_extended = np.concatenate(
            ((2.0 * axial[0] - axial[1],), axial, (2.0 * axial[-1] - axial[-2],))
        )
        axial_right = 0.5 * (np.roll(axial_extended, -1) + axial_extended)[1 : axial.size + 1]
        axial_left = 0.5 * (np.roll(axial_extended, 1) + axial_extended)[1 : axial.size + 1]
        dvr, dvx = radial_right - radial_left, axial_right - axial_left
        radial_measure = np.pi * (radial_right**2 - radial_left**2)
        radial_four_pi_measure = 4.0 / 3.0 * np.pi * (radial_right**3 - radial_left**3)
        volume = radial_measure[:, None] * dvx
        ghost_shape = (radial.size + 2, axial.size + 2)
        inv_dvx, vx_over_dvx, vr_over_dvr = (np.zeros(ghost_shape) for _ in range(3))
        inv_dvx[1:-1, 1:-1] = 1.0 / dvx
        vx_over_dvx[1:-1, 1:-1] = axial / dvx
        vr_over_dvr[1:-1, 1:-1] = (radial / dvr)[:, None]
        speed_squared = radial[:, None] ** 2 + axial**2
    float_outputs = (
        radial_measure,
        radial_four_pi_measure,
        dvx,
        radial_left,
        radial_right,
        axial_left,
        axial_right,
        volume,
        inv_dvx,
        vx_over_dvx,
        vr_over_dvr,
        speed_squared,
    )
    if not all(np.all(np.isfinite(array)) for array in float_outputs):
        raise ValueError("the quadrature outputs are not representable for these finite inputs")
    for name, array in (
        ("radial_measure", radial_measure),
        ("radial_four_pi_measure", radial_four_pi_measure),
        ("dvx", dvx),
        ("volume", volume),
    ):
        if bool(np.any(array <= 0.0)):
            raise ValueError(f"the quadrature {name} underflows to zero for these finite inputs")
    positive, negative = np.flatnonzero(axial > 0.0), np.flatnonzero(axial < 0.0)
    if positive.size == 0 or negative.size == 0:
        raise ValueError("vx must contain both negative and positive velocities")
    return {
        "radial_measure": radial_measure,
        "radial_four_pi_measure": radial_four_pi_measure,
        "dvx": dvx,
        "vr_left": radial_left,
        "vr_right": radial_right,
        "vx_left": axial_left,
        "vx_right": axial_right,
        "volume": volume,
        "inv_dvx_ghost": inv_dvx,
        "vx_over_dvx_ghost": vx_over_dvx,
        "vr_over_dvr_ghost": vr_over_dvr,
        "speed_squared": speed_squared,
        "positive_vx_indices": positive,
        "positive_vx_first_index": int(positive[0]),
        "positive_vx_last_index": int(positive[-1]),
        "negative_vx_indices": negative,
        "negative_vx_first_index": int(negative[0]),
        "negative_vx_last_index": int(negative[-1]),
    }
