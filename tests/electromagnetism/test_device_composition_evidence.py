"""Independent evidence for the ordered device compositions.

Assets: ``scirel.electromagnetism.device``,
``scirel.configurations.trex-coil``, ``scirel.configurations.brb`` and
``scirel.configurations.wham``.

These assets are compositions: a device is an ordered container of source
sets, and the two fixed configurations are hard-coded arrangements of the
sources evidenced in ``test_source_geometry_evidence.py``.  The evidence here
is therefore of three kinds, and the contracts say which statement rests on
which:

* **Exact composition laws.**  ``Device`` stacks the child responses; the
  device field must be the contraction ``current @ gpsi`` of the *same*
  matrices its children return, decided with ``Fraction`` arithmetic over the
  returned binary64 values.  A device that reordered its children, applied the
  currents per target instead of per child, or summed the wrong axis cannot
  pass it.
* **Exact symmetry of the fixed geometry.**  Both fixed configurations place
  their filaments in a multiset that is exactly mirror-symmetric about a
  plane: the sorted heights of the whole BRB device sum to zero against their
  own mirror image *bitwise*, and each WHAM coil pair is a bitwise mirror pair.
  A dropped, duplicated or misplaced filament breaks this, and so does a wrong
  ordering of the two TREX coils.
* **The elementary on-axis loop field.**  For the 88-filament TREX cloud the
  axial field on the axis is the sum of ``1e-7 w 2 pi a^2/(a^2+dz^2)^{3/2}``
  over its own filaments - a closed form with no elliptic integral, evaluated
  on the geometry the coil actually built.

What this evidence does **not** establish, and what the contracts record as
``cannot establish``: that the hard-coded device constants (the TREX conductor
radii and axial stations, the BRB ring currents, the WHAM coil parameters) are
the right numbers for those experiments.  The repository holds no independent
source for those constants; only their internal consistency and symmetry are
checked here.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.configurations import BRB, TREXCoil, WHAM
from scirel.electromagnetism import ArbitraryPoints, Device, RectangularCoil

FIELD_BUDGET = 128.0 * 2**-52
EPS = Fraction(2, 2**52)


def _contraction_bound(value, expected, count):
    """Assert a sum of ``count`` products is within ``count + 2`` roundings."""
    got, want = Fraction(float(value)), Fraction(float(expected))
    scale = abs(want) if want != 0 else Fraction(1)
    return abs(got - want) <= (count + 2) * EPS * scale


# ------------------------------------------------------------------- device
def test_device_order_currents_and_stacked_matrices():
    """Composition assets: order, per-child currents, and the stacked matrices."""
    device = Device()
    first = ArbitraryPoints([[0.5, 0.0]], current=2.0)
    second = RectangularCoil(0.9, 0.25, nr=2, nz=1, dr=0.1, current=-1.5)
    device.child_a = first
    device.child_b = second
    assert [id(source) for source in device.current_sets] == [id(first), id(second)]
    np.testing.assert_array_equal(device.current, [2.0, -1.5])
    assert len(device.rzw) == 2
    np.testing.assert_array_equal(device.rzw[0], first.rzw)
    np.testing.assert_array_equal(device.rzw[1], second.rzw)
    targets = np.array([[0.2, 0.1], [0.7, -0.3], [1.4, 0.5]])
    stacked = device.gpsi(mesh=targets)
    assert stacked.shape == (2, len(targets))
    np.testing.assert_array_equal(stacked[0], first.gpsi(mesh=targets))
    np.testing.assert_array_equal(stacked[1], second.gpsi(mesh=targets))
    # The device field is exactly the contraction of those matrices with the
    # per-child currents; a target-axis contraction would change the shape and
    # a wrong sign on the second child changes the value.
    psi = device.psi(mesh=targets)
    for column in range(len(targets)):
        expected = Fraction(float(device.current[0])) * Fraction(float(stacked[0, column])) + (
            Fraction(float(device.current[1])) * Fraction(float(stacked[1, column]))
        )
        assert _contraction_bound(psi[column], expected, 2)
    # An explicit current vector is applied per child, not per target.
    override = device.psi(current=[1.0, 1.0], mesh=targets)
    manual = stacked[0] + stacked[1]
    for column in range(len(targets)):
        assert _contraction_bound(override[column], manual[column], 2)
    with pytest.raises(ValueError, match="current must be finite scalar or vector"):
        device.psi(current=[1.0], mesh=targets)
    with pytest.raises(ValueError, match="a mesh is required for field evaluation"):
        device.psi()


def test_device_mesh_lifecycle_and_removal():
    """The mesh is stored, re-read by the children, and removable."""
    device = Device()
    device.coil = ArbitraryPoints([[0.6, 0.0]], current=3.0)
    device.mesh = np.array([[0.3, 0.2]])
    first = float(device.BZ()[0])
    child_alone = float(device.coil.BZ()[0])
    assert first > 0.0
    # The device contracts one child, so the value is reproduced up to the two
    # roundings of the contraction itself.
    deviation = abs(child_alone - first) / abs(first)
    assert deviation <= 2 * 2**-52, (child_alone, first, deviation)
    device.mesh = np.array([[0.9, -0.1], [0.3, 0.2]])
    assert device.BZ().shape == (2,)
    # The stored mesh is re-read by the child, so the moved target gives a
    # different value while the original target keeps its own.
    assert float(device.BZ()[1]) == first
    assert abs(float(device.BZ()[0]) - first) > 0.0
    del device.coil
    assert device.current_sets == []
    assert device.gpsi(mesh=np.array([[0.3, 0.2]])).shape == (0, 1)


# ---------------------------------------------------------------- TREX coil
def test_trex_coil_geometry_and_on_axis_field():
    """The fixed 88-point cloud, its exact spacing, and the elementary on-axis sum."""
    coil = TREXCoil(z0=0.4)
    assert coil.npts == 88
    points = coil.rz_pts
    radii = np.unique(points[:, 0])
    # Five columns of sixteen axial points plus one column of eight midpoints.
    counts = [int(np.count_nonzero(points[:, 0] == radius)) for radius in radii]
    assert counts == [16, 16, 16, 16, 16, 8]
    # Each station is ``_RMIN + t`` rounded, so its absolute error is at most
    # half an ulp of the station radius and an adjacent difference carries at
    # most two of those.  The bound is therefore an absolute one derived from
    # ``np.spacing`` of the station magnitudes, not a relative tolerance.
    np.testing.assert_allclose(
        np.diff(radii),
        np.full(radii.size - 1, coil.dr),
        rtol=0.0,
        atol=2 * np.spacing(np.max(radii)),
    )
    axial = np.unique(points[points[:, 0] == radii[0], 1])
    # The stations are equal to each other (a single spacing, up to the
    # rounding of each station), while ``dz`` is the declared conductor
    # thickness rounded to six decimals: it agrees with the station spacing to
    # within half of that last declared digit and is not the spacing itself.
    axial_steps = np.diff(axial)
    np.testing.assert_allclose(
        axial_steps,
        np.full(axial_steps.size, axial_steps[0]),
        rtol=0.0,
        atol=2 * np.spacing(np.max(np.abs(axial))),
    )
    assert abs(axial_steps[0] - coil.dz) <= 5e-7, (axial_steps[0], coil.dz)
    # The sixth column sits exactly midway between adjacent stations.
    midpoint = np.sort(points[points[:, 0] == radii[-1], 1])
    np.testing.assert_array_equal(midpoint, (axial[::2] + axial[1::2]) / 2)
    # The cloud is centred on z0 and the area is the declared conductor proxy.
    assert _contraction_bound(np.mean(points[:, 1]), coil.z0 * 1.0, 88)
    assert _contraction_bound(coil.area, Fraction(coil.dr) ** 2 * 88, 4)
    # On the axis the field is a sum of elementary loop fields over the cloud.
    targets = np.array([[0.0, 0.6], [0.0, -0.35]])
    coil.mesh = targets
    axial_field = coil.BZ()
    for index, height in enumerate(targets[:, 1]):
        expected = 0.0
        for radius, point_height in points:
            expected += (
                1e-7 * 2.0 * np.pi * radius**2 / (radius**2 + (height - point_height) ** 2) ** 1.5
            )
        deviation = abs(float(axial_field[index]) - expected) / abs(expected)
        assert deviation <= FIELD_BUDGET, (index, float(axial_field[index]), expected, deviation)


def test_trex_coil_transform_and_immutability():
    """Only the reference plane and rigid transforms change the cloud."""
    coil = TREXCoil(z0=0.4)
    original = coil.rz_pts.copy()
    coil.z0 = 0.75
    np.testing.assert_allclose(
        coil.rz_pts - original,
        np.broadcast_to([0.0, 0.35], original.shape),
        rtol=0,
        atol=8 * 2**-52,
    )
    np.testing.assert_array_equal(coil.rz_pts[:, 0], original[:, 0])
    with pytest.raises(NotImplementedError, match="changed through z0"):
        coil.rz_pts = original
    with pytest.raises(ValueError, match="weights must be a finite vector matching npts"):
        coil.weights = [1.0]


# --------------------------------------------------------------------- BRB
def test_brb_composition_order_counts_and_balance():
    """The ordered BRB composition, its counts, and the balanced ring weights."""
    device = BRB()
    names = [type(source).__name__ for source in device.current_sets]
    assert names[:4] == ["TREXCoil", "TREXCoil", "RectangularCoil", "RectangularCoil"]
    assert names[4:] == ["MagnetRing"] * 36
    counts = [source.npts for source in device.current_sets]
    assert counts[:4] == [88, 88, 130, 130]
    assert counts[4:] == [16] * 36
    # Every ring is an exactly balanced signed-filament pair set, so its total
    # current is zero while its field is not; the coils carry unit weights.
    for source in device.current_sets[4:]:
        assert float(np.sum(source.weights)) == 0.0
        assert source.total_current == 1.0 * 0.0
        assert np.any(source.weights > 0.0) and np.any(source.weights < 0.0)
    for source in device.current_sets[:4]:
        np.testing.assert_array_equal(source.weights, np.ones(source.npts))


def test_brb_and_wham_geometry_is_exactly_mirror_symmetric():
    """Exact multiset symmetry of the fixed configurations."""
    brb = BRB()
    heights = np.sort(np.concatenate([source.rz_pts[:, 1] for source in brb.current_sets]))
    # The ascending multiset added to its own descending order gives zero to
    # within the rounding of each mirrored node, which is the statement that the
    # multiset is symmetric about the ring plane and not merely that its mean is
    # zero.  Each pair is formed as ``z0 + t`` and ``-(z0 + t)`` by different
    # expressions inside the constructors, so the sum carries up to one ulp of
    # the node magnitude per side.
    np.testing.assert_allclose(
        heights + heights[::-1], 0.0, rtol=0.0, atol=2 * np.spacing(np.max(np.abs(heights)))
    )
    both_trex = [source for source in brb.current_sets if type(source).__name__ == "TREXCoil"]
    upper = np.sort(both_trex[0].rz_pts[:, 1])
    lower = np.sort(both_trex[1].rz_pts[:, 1])
    np.testing.assert_allclose(
        upper + lower[::-1], 0.0, rtol=0.0, atol=2 * np.spacing(np.max(np.abs(upper)))
    )
    wham = WHAM()
    assert [source.npts for source in wham.current_sets] == [32, 32, 10, 10]
    for upper, lower in ((wham.hts1, wham.hts2), (wham.cc1, wham.cc2)):
        np.testing.assert_array_equal(upper.rz_pts[:, 0], lower.rz_pts[:, 0])
        upper_heights = np.sort(upper.rz_pts[:, 1])
        lower_heights = np.sort(lower.rz_pts[:, 1])
        np.testing.assert_allclose(
            upper_heights + lower_heights[::-1],
            0.0,
            rtol=0.0,
            atol=2 * np.spacing(np.max(np.abs(upper_heights))),
        )


def test_device_field_of_a_fixed_configuration_is_the_child_contraction():
    """The fixed device's field over its children, decided with fractions."""
    device = WHAM()
    targets = np.array([[0.0, 0.0], [0.3, 0.55]])
    stacked = device.gpsi(mesh=targets)
    field = device.psi(mesh=targets)
    assert stacked.shape == (4, 2)
    for column in range(len(targets)):
        expected = sum(
            (
                Fraction(float(device.current[index])) * Fraction(float(stacked[index, column]))
                for index in range(4)
            ),
            Fraction(0),
        )
        assert _contraction_bound(field[column], expected, 4)
    # Changing one child current changes the device field by exactly that
    # child's response, so no other child is silently reused.
    before = device.psi(mesh=targets).copy()
    device.cc1.current = 2.0 * device.cc1.current
    after = device.psi(mesh=targets)
    delta = after - before
    np.testing.assert_allclose(delta, device.cc1.current * stacked[2] / 2.0, rtol=1e-14, atol=0.0)
