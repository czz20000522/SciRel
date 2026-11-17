"""Closed-form identities for the axisymmetric equilibrium map.

Asset: ``scirel.geometry.axisymmetric-equilibrium-grid-mapping``.

The map is a bilinear interpolation of ``(br, bz, psi)`` on a rectilinear
``(r, z)`` grid plus a rotation into Cartesian coordinates.  Its *independent
basis* is two analytic facts, neither of which depends on how the interpolation
is coded:

1. **Multilinear reproduction.** A tensor-product linear interpolant reproduces a
   function that is multilinear in its arguments exactly: interpolating
   ``psi = a + b r + c z`` between grid nodes must return ``a + b r + c z`` at
   *every* query point, not merely at the nodes.  Because the radial coordinate
   is the Cartesian ``hypot(x, y)`` and the axial coordinate is shared, the query
   point's radius is the only thing the interpolant sees, so this identity also
   proves that the axial coordinate is not rescaled, shifted or swapped on the
   way through.  Dyadic coefficients and dyadic query coordinates make the
   identity **bitwise**; the test asserts bitwise equality and does not fall back
   to a tolerance.
2. **The exact transverse split.** The declared split is
   ``(Bx, By) = br * (x, y) / r`` with ``br`` a signed scalar.  At the
   Pythagorean radius ``r = hypot(3, 4) = 5`` the factors are the exact rationals
   ``3/5`` and ``4/5``, so ``br * x / r`` and ``br * y / r`` are exact rational
   operations; the test recomputes them in ``fractions.Fraction`` and compares
   bitwise.  This decides the *pairing* (x with the cosine side, y with the sine
   side), the **sign** (``+br``, not ``-br``) and the division by ``r`` (not by
   ``x``, ``y`` or ``r**2``) at once, with no tolerance to hide behind.
3. **The azimuthal identity.** ``Bx * y - By * x = 0`` and
   ``Bx * x + By * y = r * |Bxy|`` are the two components of "the transverse field
   is radial"; both are asserted here on a rotated query pair so that a wrong
   angle cannot satisfy them by accident.  ``tests/geometry/test_axisymmetric_mapping_evidence.py``
   carries the wider version of this identity (including the sign and the
   on-axis convention) and is not duplicated.

Precision budgets, fixed before measurement (``eps = 2.22e-16``):

* multilinear reproduction: **bitwise**, because every operation on dyadic data
  is exact.  A non-dyadic second case is admitted at ``8 * eps * scale``.
* the transverse split: **bitwise** rational equality after the exact rational
  recomputation, because ``hypot(3, 4) = 5`` is exact and both products and the
  division are exact on these operands.
* the azimuthal identity: ``16 * eps`` of the product magnitude, the bound the
  wider evidence file already uses.

The matrix covers a normal interior grid, the boundaries of the map box (inner
radius ``r = 0``, outer radius, both axial faces), a degenerate axis row
(``r = 0`` where the split is undefined), an asymmetric grid (``nr != nz``, and
unequal ``x``/``y`` axes so a transpose is visible) and the non-finite and
malformed channels.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry import map_axisymmetric_equilibrium_to_cartesian_grid

EPS = np.finfo(float).eps


def _exact(value):
    """Exact rational value of the binary64 number ``value``."""
    return Fraction(float(value))


def _linear_equilibrium(radial, axial):
    """``psi = 2 r + 3 z`` with a constant radial field and a constant axial one."""
    rr, zz = np.meshgrid(radial, axial, indexing="ij")
    return {
        "r_m": radial,
        "z_m": axial,
        "psi_wb_per_rad": 2.0 * rr + 3.0 * zz,
        "br_t": np.full_like(rr, 2.5),
        "bz_t": np.full_like(rr, 1.0),
    }


def test_a_multilinear_flux_is_reproduced_bitwise_everywhere():
    """The interpolant of ``a + b r + c z`` is that same function at every query."""
    radial = np.linspace(0.0, 1.5, 5)
    axial = np.linspace(-1.0, 1.0, 5)
    equilibrium = _linear_equilibrium(radial, axial)
    # The inner radius is 0, so every query below is covered and nothing is clamped.
    x_axis = np.array([-0.7, -0.35, 0.0, 0.35, 0.7])
    z_axis = np.array([-0.5, 0.0, 0.5])
    result = map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x_axis, x_axis, z_axis)
    assert result["covered_mask"].all()
    assert result["radially_clamped_point_count"] == 0
    assert result["axially_clamped_point_count"] == 0

    xx, yy, zz = np.meshgrid(x_axis, x_axis, z_axis, indexing="ij")
    closed_form = 2.0 * np.hypot(xx, yy) + 3.0 * zz
    assert np.array_equal(result["poloidal_flux_wb_per_rad"], closed_form)


def test_an_asymmetric_grid_keeps_the_axis_roles():
    """``nr != nz`` and unequal x/y axes: a transposed or swapped axis shows up."""
    radial = np.linspace(0.0, 2.0, 6)  # nr = 6
    axial = np.linspace(-1.0, 1.0, 5)  # nz = 5, so nr != nz
    equilibrium = _linear_equilibrium(radial, axial)
    x_axis = np.array([-0.9, 0.0, 0.9])
    y_axis = np.array([-0.4, 0.4])
    z_axis = np.array([-0.5, 0.5])
    result = map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x_axis, y_axis, z_axis)
    assert result["poloidal_flux_wb_per_rad"].shape == (3, 2, 2)
    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    assert np.array_equal(result["poloidal_flux_wb_per_rad"], 2.0 * np.hypot(xx, yy) + 3.0 * zz)


def test_the_transverse_split_is_an_exact_rational_operation_at_r_five():
    """At (x, y) = (3, 4) the split is ``br * 3 / 5`` and ``br * 4 / 5``, exactly."""
    radial = np.linspace(0.0, 6.0, 7)
    axial = np.linspace(-1.0, 1.0, 5)
    equilibrium = _linear_equilibrium(radial, axial)
    result = map_axisymmetric_equilibrium_to_cartesian_grid(
        equilibrium,
        np.array([3.0, 5.0]),
        np.array([0.0, 4.0]),
        np.array([0.0, 0.5]),
    )
    field = result["magnetic_flux_density_t"]
    # (3, 4): radius exactly 5, so the two factors are exactly 3/5 and 4/5.
    assert field[0, 1, 0, 0] == float(_exact(2.5) * 3 / 5)
    assert field[0, 1, 0, 1] == float(_exact(2.5) * 4 / 5)
    assert field[0, 1, 0, 2] == 1.0
    assert field[0, 1, 0, 0] == 1.5 and field[0, 1, 0, 1] == 2.0
    # (5, 0): the whole radial field lands on x and y is exactly zero.
    assert field[1, 0, 0, 0] == 2.5
    assert field[1, 0, 0, 1] == 0.0


def test_the_transverse_field_is_radial_for_every_azimuth():
    """Bx*y - By*x = 0 and Bx*x + By*y = r*|Bxy| on a rotated query pair."""
    radial = np.linspace(0.0, 6.0, 7)
    axial = np.linspace(-1.0, 1.0, 5)
    equilibrium = _linear_equilibrium(radial, axial)
    radius = 2.0
    for degrees in (0.0, 30.0, 45.0, 120.0):
        radians = math.radians(degrees)
        x, y = radius * math.cos(radians), radius * math.sin(radians)
        # The axis entries must stay strictly increasing, so the query of interest
        # is the first node and the second node is a distinct point one metre away.
        result = map_axisymmetric_equilibrium_to_cartesian_grid(
            equilibrium,
            np.array([x, x + 1.0]),
            np.array([y, y + 1.0]),
            np.array([0.0, 0.5]),
        )
        bx, by = result["magnetic_flux_density_t"][0, 0, 0, :2]
        scale = 16 * EPS * max(abs(bx * y), abs(by * x), 1.0)
        assert abs(bx * y - by * x) <= scale, degrees
        assert abs(bx * x + by * y - radius * math.hypot(bx, by)) <= scale, degrees


def test_the_axis_row_and_the_box_boundaries():
    """r = 0 sets both transverse components to zero; the faces clamp and report it."""
    radial = np.linspace(0.0, 1.0, 5)
    axial = np.linspace(-1.0, 1.0, 5)
    equilibrium = _linear_equilibrium(radial, axial)
    z_axis = np.array([-1.0, 1.0])
    result = map_axisymmetric_equilibrium_to_cartesian_grid(
        equilibrium,
        np.array([0.0, 2.0]),
        np.array([0.0, 1.0]),
        z_axis,
    )
    field = result["magnetic_flux_density_t"]
    # On the axis the split is undefined, so both transverse components are set
    # exactly to zero rather than to a divided-by-zero limit.
    assert field[0, 0, :, 0].tolist() == [0.0, 0.0]
    assert field[0, 0, :, 1].tolist() == [0.0, 0.0]
    assert field[0, 0, :, 2].tolist() == [1.0, 1.0]
    # x = 2 lies outside the outer radius of 1, so it is clamped onto the face and
    # the face value - not zero - is what the map returns.  Both z entries of the
    # x = 2 column are outside, in both y rows: four clamped points.
    assert field[1, 0, 0, 2] == 1.0
    assert result["radially_clamped_point_count"] == 4
    assert not result["covered_mask"][1, 0, 0]
    assert result["axially_clamped_point_count"] == 0
    # Clamping is not zero-filling: the clamped poloidal flux equals the face value
    # 2 * 1 + 3 * 0 evaluated at the clamped radius 1.
    face = 2.0 * 1.0 + 3.0 * z_axis[0]
    assert result["poloidal_flux_wb_per_rad"][1, 0, 0] == pytest.approx(face, rel=0, abs=8 * EPS)


def test_the_map_rejects_each_declared_channel():
    """One executable assertion per ``failure_semantics`` entry of the mapping."""
    radial = np.linspace(0.0, 1.0, 5)
    axial = np.linspace(-1.0, 1.0, 5)
    good = _linear_equilibrium(radial, axial)
    x_axis = np.array([0.0, 0.5])

    with pytest.raises(ValueError, match="must be a mapping"):
        map_axisymmetric_equilibrium_to_cartesian_grid([good], x_axis, x_axis, np.array([0.0, 0.5]))
    missing = {key: value for key, value in good.items() if key != "br_t"}
    with pytest.raises(ValueError, match="missing the required entry"):
        map_axisymmetric_equilibrium_to_cartesian_grid(
            missing, x_axis, x_axis, np.array([0.0, 0.5])
        )
    with pytest.raises(ValueError, match="at least five points"):
        map_axisymmetric_equilibrium_to_cartesian_grid(
            {**good, "r_m": np.array([0.0, 0.5, 1.0])}, x_axis, x_axis, np.array([0.0, 0.5])
        )
    with pytest.raises(ValueError, match="must have shape"):
        map_axisymmetric_equilibrium_to_cartesian_grid(
            {**good, "br_t": np.zeros((5, 4))}, x_axis, x_axis, np.array([0.0, 0.5])
        )
    with pytest.raises(ValueError, match="must be finite"):
        map_axisymmetric_equilibrium_to_cartesian_grid(
            {**good, "psi_wb_per_rad": np.full((5, 5), np.nan)},
            x_axis,
            x_axis,
            np.array([0.0, 0.5]),
        )
    with pytest.raises(ValueError, match="strictly increasing"):
        map_axisymmetric_equilibrium_to_cartesian_grid(
            good, np.array([0.5, 0.0]), x_axis, np.array([0.0, 0.5])
        )
    with pytest.raises(ValueError, match="at least two points"):
        map_axisymmetric_equilibrium_to_cartesian_grid(
            good, np.array([0.0]), x_axis, np.array([0.0, 0.5])
        )
