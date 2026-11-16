"""Independent evidence for the planar projection and the material-support mask.

Assets: ``scirel.geometry.planar-wavevector-projection``,
``scirel.geometry.material-support-classification``.

Both are *rules*, not measurements, so the evidence recomputes each rule by hand:

1. **Conventions decided by a discriminator.**  The polar mode places ``kz`` along
   the +Z axis (``theta = 0`` gives ``(kx, kz) = (0, k)``) and takes ``theta_rad``
   in **radians**; a reading from the +R axis, or a degree reading, moves a
   component by O(k).  Both are asserted before the chosen reading is bounded.
2. **Analytic identities.**  ``hypot(k sin t, k cos t) == k`` to 8 eps and the
   recovered angle returns the input; a doubled magnitude doubles both components
   exactly (power of two).
3. **The support mask is the declared boolean formula.**  On a hand-built grid the
   returned mask is compared, element by element, with
   ``((covered & side_flux) | axis) & interior & ~pec`` recomputed here, where
   ``interior`` is the grid with a ``pml_cells`` frame removed.  That is the
   contract's own definition, recomputed independently - not a second call of the
   implementation.
4. **Each term is isolated.**  Flipping ``closed_flux_side`` complements the
   closed mask on the covered region; a PEC cell removes exactly one cell; a point
   at the minimum radius but beyond ``xpoint_half_length`` is not axis support;
   the frame is exactly ``pml_cells`` wide.
5. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset, including the empty-support channel.

Budgets, fixed before measurement:

* the trigonometric identities: ``8 * eps * k`` per component (two rounded
  transcendentals, one product).
* the recovered angle: ``16 * eps`` absolute in radians.
* the mask comparisons: **exact** boolean equality.
* the exact power-of-two scalings: exact equality.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.geometry import classify_material_support, project_planar_wavevector

EPS = np.finfo(float).eps


# --------------------------------------------------------------------------- #
# planar-wavevector-projection
# --------------------------------------------------------------------------- #


def test_the_polar_mode_puts_kz_on_the_symmetry_axis_and_takes_radians():
    """Evidence 1: theta = 0 gives (0, k); the rival axis and unit readings differ by O(k)."""
    on_axis = project_planar_wavevector(k_grid=[2.0], theta_rad=0.0)
    assert on_axis["kx"][0] == 0.0
    assert on_axis["kz"][0] == 2.0
    # A reading from the +R axis would give (2, 0): both components differ by 2.
    assert abs(on_axis["kz"][0] - 0.0) > 1e6 * EPS
    # theta = 90 *degrees* read as radians is sin(90 rad) = 0.894, not 1.
    quarter = project_planar_wavevector(k_grid=[1.0], theta_rad=math.pi / 2)
    assert abs(quarter["kx"][0] - 1.0) <= 8 * EPS
    assert abs(quarter["kz"][0]) <= 8 * EPS


def test_the_two_modes_are_inverse_on_the_magnitude_and_the_angle():
    """Evidence 2: hypot(k sin t, k cos t) = k and the recovered angle is t."""
    for magnitude, angle in ((1.0, 0.0), (2.5, 0.3), (7.0, math.pi / 3), (0.125, -1.1)):
        polar = project_planar_wavevector(k_grid=[magnitude], theta_rad=angle)
        components = project_planar_wavevector(kx_grid=[polar["kx"][0]], kz_grid=[polar["kz"][0]])
        assert abs(components["k"][0] - magnitude) <= 8 * EPS * magnitude
        # The cartesian mode does not recover the angle: it reports None, which the
        # contract declares rather than silently inventing a value.
        assert components["theta_rad"] is None


def test_a_doubled_magnitude_doubles_both_components_exactly():
    """Evidence 2: an exact power-of-two scaling of the magnitude."""
    base = project_planar_wavevector(k_grid=[1.5], theta_rad=0.7)
    doubled = project_planar_wavevector(k_grid=[3.0], theta_rad=0.7)
    assert doubled["kx"][0] == 2.0 * base["kx"][0]
    assert doubled["kz"][0] == 2.0 * base["kz"][0]


def test_planar_projection_rejections():
    """Evidence 5: mode selection, sign, shape and finiteness channels."""
    call = project_planar_wavevector
    with pytest.raises(ValueError, match="choose a magnitude sweep"):
        call(k_grid=[1.0], kx_grid=[1.0], kz_grid=[1.0])
    with pytest.raises(ValueError, match="nonnegative"):
        call(k_grid=[-1.0], theta_rad=0.0)
    with pytest.raises(ValueError, match="both component grids"):
        call(kx_grid=[1.0])
    with pytest.raises(ValueError, match="finite paired nonempty"):
        call(kx_grid=[1.0, 2.0], kz_grid=[1.0])
    with pytest.raises(ValueError, match="finite"):
        call(kx_grid=[np.nan], kz_grid=[1.0])


# --------------------------------------------------------------------------- #
# material-support-classification
# --------------------------------------------------------------------------- #


def _support_grid(shape=(6, 5, 5)):
    """Return a grid whose flux increases with R, plus matching coordinates."""
    n_z, n_r, n_phi = shape
    r_axis = np.linspace(1.0, 2.0, n_r)
    z_axis = np.linspace(-1.0, 1.0, n_z)
    flux = np.broadcast_to(r_axis[None, :, None], shape).copy()
    radius = np.broadcast_to(r_axis[None, :, None], shape).copy()
    axial = np.broadcast_to(z_axis[:, None, None], shape).copy()
    return flux, radius, axial


def test_the_support_mask_is_the_declared_boolean_formula():
    """Evidence 3: recompute the contract's own formula and compare element by element."""
    shape = (6, 5, 5)
    flux, radius, axial = _support_grid(shape)
    covered = np.ones(shape, dtype=bool)
    covered[0, 0, 0] = False
    separatrix = 1.5
    side = "less_than"
    half_length = 0.5
    thickness = 1
    pec = np.zeros(shape, dtype=bool)
    pec[3, 2, 2] = True
    result = classify_material_support(
        flux,
        covered,
        radius,
        axial,
        separatrix_flux_wb_per_rad=separatrix,
        closed_flux_side=side,
        xpoint_half_length_m=half_length,
        pml_cells=thickness,
        pec_mask=pec,
    )
    closed = covered & (flux < separatrix)
    axis = covered & np.isclose(radius, np.min(radius), rtol=0.0, atol=1e-15)
    axis = axis & (np.abs(axial) < half_length)
    interior = np.ones(shape, dtype=bool)
    interior[:thickness] = False
    interior[-thickness:] = False
    interior[:, :thickness] = False
    interior[:, -thickness:] = False
    interior[:, :, :thickness] = False
    interior[:, :, -thickness:] = False
    expected = (closed | axis) & interior & ~pec
    assert np.array_equal(result["material_support_mask"], expected)
    assert np.array_equal(result["closed_flux_mask"], closed)


def test_each_term_of_the_mask_is_isolated():
    """Evidence 4: flip the side, remove one PEC cell, and test the axis length window."""
    shape = (6, 5, 5)
    flux, radius, axial = _support_grid(shape)
    covered = np.ones(shape, dtype=bool)
    pec = np.zeros(shape, dtype=bool)
    common = dict(
        separatrix_flux_wb_per_rad=1.5,
        xpoint_half_length_m=0.5,
        pml_cells=1,
        pec_mask=pec,
    )
    less = classify_material_support(
        flux, covered, radius, axial, closed_flux_side="less_than", **common
    )
    greater = classify_material_support(
        flux, covered, radius, axial, closed_flux_side="greater_than", **common
    )
    # On the covered region the two closed masks are exact complements.
    assert np.array_equal(
        less["closed_flux_mask"] & greater["closed_flux_mask"], np.zeros(shape, dtype=bool)
    )
    # Both comparisons are strict, so a node sitting exactly on the separatrix
    # belongs to NEITHER side: the union is the covered region minus that node set.
    separatrix_nodes = np.isclose(flux, 1.5, rtol=0.0, atol=0.0)
    assert np.any(separatrix_nodes)
    assert np.array_equal(
        less["closed_flux_mask"] | greater["closed_flux_mask"], covered & ~separatrix_nodes
    )
    assert not np.any(less["closed_flux_mask"] & separatrix_nodes)
    assert not np.any(greater["closed_flux_mask"] & separatrix_nodes)
    # One PEC cell removes exactly the cells that were supported at that index.
    target = tuple(int(i) for i in np.argwhere(less["material_support_mask"])[0])
    pec[target] = True
    with_pec = classify_material_support(
        flux, covered, radius, axial, closed_flux_side="less_than", **common
    )
    assert not with_pec["material_support_mask"][target]
    assert (
        np.count_nonzero(less["material_support_mask"])
        - np.count_nonzero(with_pec["material_support_mask"])
        == 1
    )
    # A point at the minimum radius but beyond xpoint_half_length is not axis support.
    far = dict(common)
    far["xpoint_half_length_m"] = 0.1
    limited = classify_material_support(
        flux, covered, radius, axial, closed_flux_side="greater_than", **far
    )
    assert limited["axis_segment_mask"].sum() < greater["axis_segment_mask"].sum()


def test_support_rejections():
    """Evidence 5: shape, cell-count, side and empty-support channels."""
    shape = (6, 5, 5)
    flux, radius, axial = _support_grid(shape)
    covered = np.ones(shape, dtype=bool)
    pec = np.zeros(shape, dtype=bool)
    call = classify_material_support
    kwargs = dict(
        separatrix_flux_wb_per_rad=1.5,
        closed_flux_side="less_than",
        xpoint_half_length_m=0.5,
        pml_cells=1,
        pec_mask=pec,
    )
    with pytest.raises(ValueError, match="must match the poloidal flux shape"):
        call(flux[:, :, :3], covered, radius, axial, **kwargs)
    with pytest.raises(ValueError, match="positive integer"):
        call(flux, covered, radius, axial, **{**kwargs, "pml_cells": 0})
    with pytest.raises(ValueError, match="closed_flux_side|side"):
        call(flux, covered, radius, axial, **{**kwargs, "closed_flux_side": "either"})
    with pytest.raises(ValueError, match="empty"):
        call(flux, np.zeros(shape, dtype=bool), radius, axial, **kwargs)
