"""Independent evidence for the cylindrical velocity quadrature.

Asset: ``scirel.neutrals.cylindrical-velocity-quadrature``.

The mesh measures are a discrete partition of the velocity-space region, so the
strongest available evidence is **telescoping conservation**, which holds for any
correct face/measure construction and fails for a wrong index convention, a wrong
power, or a dropped factor:

1. **The radial rings partition the disc.**  ``sum(radial_measure) = pi * R**2``
   with ``R`` the outermost face, and ``sum(radial_four_pi_measure) = 4/3 pi R**3``
   (the ball volume), exactly to rounding.  A wrong radial power or an unequal
   number of faces breaks one of the two.
2. **The axial widths partition the span.**  ``sum(dvx) = vx_right[-1] -
   vx_left[0]``, so the ghost-face extrapolation is consistent at both ends.
3. **The volume is the product measure.**  ``sum(volume) = sum(radial_measure) *
   sum(dvx)`` and ``sum(volume) = 2 pi integral(r dr) * span`` to rounding, which
   ties the two axes together and catches an axial/radial transposition.
4. **Exact rational faces and measures.**  Faces are midpoints and the annulus
   measures are ``pi * (r_right**2 - r_left**2)``; both are recomputed with
   :class:`fractions.Fraction` and compared after one rounding.
5. **Declared structural fields.**  ``speed_squared`` is the node speed squared,
   the ghost ring is exactly zero while the interior is exactly ``1/dvx``,
   ``vx/dvx`` and ``vr/dvr``, and the sign blocks are the strictly negative and
   strictly positive index runs.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel.

Budgets, fixed before measurement:

* telescoping sums over ``n`` cells: ``(n + 4) * eps * scale`` where ``scale`` is
  the summed magnitude; the partitions are exact in exact arithmetic, so only
  rounding from the ``n-1`` additions and the power/py products remains.
* exact rational comparisons: ``8 * eps`` relative after one division by pi.
* structural equality (ghost zeros, interior ratios, sign blocks): exact
  ``array_equal``.
"""

from __future__ import annotations

from fractions import Fraction
import math

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps

VR = np.array([0.5, 1.5, 4.0])
VX = np.array([-2.0, -0.5, 0.75, 3.0])


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _quadrature(vr=VR, vx=VX):
    """Return the quadrature mapping for the shared mesh."""
    return N.make_cylindrical_velocity_quadrature(vr=vr, vx=vx)


def _exact_faces(axis):
    """Exact finite-volume faces of the ghost-extrapolated increasing axis."""
    values = [2.0 * axis[0] - axis[1], *axis, 2.0 * axis[-1] - axis[-2]]
    left = [(_frac(values[i - 1]) + _frac(values[i])) / 2 for i in range(1, len(values) - 1)]
    right = [(_frac(values[i]) + _frac(values[i + 1])) / 2 for i in range(1, len(values) - 1)]
    return left, right


def test_radial_rings_partition_the_disc():
    """Evidence 1: telescoping radial measures recover pi R^2 and 4/3 pi R^3."""
    result = _quadrature()
    outer = float(result["vr_right"][-1])
    measure = np.asarray(result["radial_measure"])
    four_pi = np.asarray(result["radial_four_pi_measure"])
    scale = max(float(np.sum(np.abs(measure))), 1.0)
    assert abs(float(np.sum(measure)) - math.pi * outer**2) <= (measure.size + 4) * EPS * scale
    scale = max(float(np.sum(np.abs(four_pi))), 1.0)
    assert (
        abs(float(np.sum(four_pi)) - (4.0 / 3.0) * math.pi * outer**3)
        <= (four_pi.size + 4) * EPS * scale
    )


def test_axial_widths_partition_the_span():
    """Evidence 2: the ghosted axial widths sum to the total span."""
    result = _quadrature()
    widths = np.asarray(result["dvx"])
    span = float(result["vx_right"][-1]) - float(result["vx_left"][0])
    assert abs(float(np.sum(widths)) - span) <= (widths.size + 4) * EPS * max(abs(span), 1.0)


def test_volume_is_the_product_measure():
    """Evidence 3: the cell volumes telescope to the disc times the span."""
    result = _quadrature()
    volume = np.asarray(result["volume"])
    radial = float(np.sum(np.asarray(result["radial_measure"])))
    axial = float(np.sum(np.asarray(result["dvx"])))
    outer = float(result["vr_right"][-1])
    scale = max(float(np.sum(np.abs(volume))), 1.0)
    assert abs(float(np.sum(volume)) - radial * axial) <= (volume.size + 4) * EPS * scale
    assert (
        abs(float(np.sum(volume)) - math.pi * outer**2 * axial) <= (volume.size + 8) * EPS * scale
    )


def test_faces_and_annulus_measures_match_exact_rationals():
    """Evidence 4: midpoint faces and pi (r_right^2 - r_left^2) exactly."""
    result = _quadrature()
    for axis, left_key, right_key in (
        (VR, "vr_left", "vr_right"),
        (VX, "vx_left", "vx_right"),
    ):
        left, right = _exact_faces(axis)
        expected_left = np.array([float(value) for value in left])
        expected_right = np.array([float(value) for value in right])
        assert np.all(
            np.abs(np.asarray(result[left_key]) - expected_left)
            <= 8 * EPS * max(float(np.max(np.abs(expected_left))), 1.0)
        )
        assert np.all(
            np.abs(np.asarray(result[right_key]) - expected_right)
            <= 8 * EPS * max(float(np.max(np.abs(expected_right))), 1.0)
        )
    left, right = _exact_faces(VR)
    exact_measure = [math.pi * float(r**2 - l**2) for l, r in zip(left, right)]
    assert np.all(
        np.abs(np.asarray(result["radial_measure"]) - np.array(exact_measure))
        <= 16 * EPS * max(float(np.max(np.abs(exact_measure))), 1.0)
    )


def test_declared_structural_fields_are_exact():
    """Evidence 5: node speed squared, the ghost ring, the interior ratios and the sign blocks."""
    result = _quadrature()
    speed_squared = np.asarray(result["speed_squared"])
    exact = np.array([[float(_frac(r) ** 2 + _frac(x) ** 2) for x in VX] for r in VR])
    assert np.allclose(speed_squared, exact, rtol=0.0, atol=8 * EPS * float(np.max(exact)))
    inv = np.asarray(result["inv_dvx_ghost"])
    widths = np.asarray(result["dvx"])
    assert np.all(inv[0, :] == 0.0) and np.all(inv[-1, :] == 0.0)
    assert np.all(inv[:, 0] == 0.0) and np.all(inv[:, -1] == 0.0)
    interior = (VR.size, VX.size)
    assert np.array_equal(inv[1:-1, 1:-1], np.broadcast_to(1.0 / widths, interior))
    assert np.array_equal(
        np.asarray(result["vx_over_dvx_ghost"])[1:-1, 1:-1],
        np.broadcast_to(VX / widths, interior),
    )
    dr = np.asarray(result["vr_right"]) - np.asarray(result["vr_left"])
    assert np.array_equal(
        np.asarray(result["vr_over_dvr_ghost"])[1:-1, 1:-1],
        np.broadcast_to((VR / dr)[:, None], interior),
    )
    assert np.array_equal(result["positive_vx_indices"], np.array([2, 3]))
    assert result["positive_vx_first_index"] == 2 and result["positive_vx_last_index"] == 3
    assert np.array_equal(result["negative_vx_indices"], np.array([0, 1]))
    assert result["negative_vx_first_index"] == 0 and result["negative_vx_last_index"] == 1
    # An exactly zero node belongs to neither sign block; VX has no zero, so the
    # discriminator needs a mesh that does.
    zero_axis = np.array([-2.0, -0.5, 0.0, 0.75, 3.0])
    zeroed = N.make_cylindrical_velocity_quadrature(vr=VR, vx=zero_axis)
    assert np.array_equal(zeroed["positive_vx_indices"], np.array([3, 4]))
    assert np.array_equal(zeroed["negative_vx_indices"], np.array([0, 1]))
    assert zeroed["positive_vx_first_index"] == 3 and zeroed["negative_vx_last_index"] == 1


def test_quadrature_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.make_cylindrical_velocity_quadrature
    with pytest.raises(ValueError, match="length at least two"):
        call(vr=np.array([0.5]), vx=VX)
    with pytest.raises(ValueError, match="strictly increasing"):
        call(vr=np.array([1.5, 0.5, 4.0]), vx=VX)
    with pytest.raises(ValueError, match="strictly increasing"):
        call(vr=VR, vx=np.array([-2.0, -0.5, -0.5, 3.0]))
    with pytest.raises(ValueError, match="finite one-dimensional"):
        call(vr=VR, vx=np.array([-2.0, np.nan, 3.0]))
    with pytest.raises(ValueError, match="real numeric"):
        call(vr=VR, vx=np.array([-2.0, "a", 3.0]))
    with pytest.raises(ValueError, match="vr must be nonnegative"):
        call(vr=np.array([-0.5, 1.5, 4.0]), vx=VX)
    with pytest.raises(ValueError, match="both negative and positive"):
        call(vr=VR, vx=np.array([0.5, 1.0, 3.0]))
    with pytest.raises(ValueError, match="both negative and positive"):
        call(vr=VR, vx=np.array([-3.0, -1.0, -0.5]))
