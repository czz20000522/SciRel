"""New geometric invariants and whole-configuration composition gates.

Coordinate oracles use elementary trigonometry and independent Cartesian
products. These establish geometry/state conventions, not experimental
validity of BRB, WHAM, or a permanent-magnet constitutive model.
"""

import numpy as np
import inspect
import pytest

from scirel.configurations import BRB, WHAM
from scirel.electromagnetism import ArbitraryPoints, MagnetRing, RectangularCoil
from scirel.geometry import (
    Mesh,
    PointsMesh,
    RChord,
    ZChord,
    SphericalRChord,
    ThetaChord,
    RectMesh,
    rotate,
)


def test_magnet_ring_public_docstring_declares_contract():
    doc = inspect.getdoc(MagnetRing)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "signed-filament geometry approximation" in doc


def test_arbitrary_points_public_docstring_declares_contract():
    doc = inspect.getdoc(ArbitraryPoints)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "(R, Z)" in doc
    assert "coincidence is singular" in doc


def test_rectangular_coil_public_docstring_declares_contract():
    doc = inspect.getdoc(RectangularCoil)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "nr*nz" in doc
    assert "rebuild atomically" in doc


@pytest.mark.parametrize("angle", [-130.0, -7.0, 0.0, 37.0, 91.0, 360.0])
def test_rotation_inverse_distance_and_nonmutation(angle):
    points = np.array([[1.4, -0.3], [2.1, 0.7], [0.2, 1.5]])
    pivot = np.array([0.8, -0.4])
    before = points.copy()
    transformed = rotate(points, angle, pivot)
    np.testing.assert_allclose(
        np.linalg.norm(transformed - pivot, axis=1),
        np.linalg.norm(points - pivot, axis=1),
        rtol=5e-15,
        atol=1e-15,
    )
    np.testing.assert_allclose(rotate(transformed, -angle, pivot), points, rtol=0.0, atol=2e-15)
    np.testing.assert_array_equal(points, before)


def test_all_chord_conventions_and_structured_point_order():
    values = np.array([0.2, 0.5, 0.8])
    np.testing.assert_array_equal(
        Mesh.to_points(RChord(values, 0.7)), np.column_stack((values, np.full(3, 0.7)))
    )
    np.testing.assert_array_equal(
        Mesh.to_points(ZChord(values, 0.7)), np.column_stack((np.full(3, 0.7), values))
    )
    angles = np.array([12.0, 37.0, 109.0, 164.0])
    chord = ThetaChord(angles, r0=1.3)
    np.testing.assert_allclose(chord.r, 1.3, rtol=5e-15, atol=0.0)
    np.testing.assert_allclose(chord.theta, np.deg2rad(angles), rtol=5e-15, atol=1e-15)
    radius = SphericalRChord(values, theta0=37.0)
    np.testing.assert_allclose(radius.r, values, rtol=5e-15, atol=0.0)
    np.testing.assert_allclose(radius.theta, np.deg2rad(37.0), rtol=5e-15, atol=0.0)
    mesh = RectMesh(rmin=0.2, rmax=0.8, nr=3, zmin=-0.7, zmax=0.4, nz=2)
    np.testing.assert_array_equal(
        Mesh.to_points(mesh),
        np.array([[0.2, -0.7], [0.5, -0.7], [0.8, -0.7], [0.2, 0.4], [0.5, 0.4], [0.8, 0.4]]),
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RectangularCoil(1.2, 0.3, nr=3, nz=4, dr=0.07, dz=0.09, angle=37.0),
        lambda: MagnetRing(
            1.2, 0.3, width=0.07, height=0.09, mu_hat=37.0, weights=[-2.0, -0.5, 0.5, 2.0]
        ),
    ],
)
def test_parameterized_source_chained_rigid_geometry_and_signed_current(factory):
    source = factory()
    points = source.rz_pts.copy()
    distance = np.linalg.norm(points - source.centroid, axis=1)
    source.rotate(13.0, pivot=(0.9, 0.1))
    source.translate([0.3, -0.2])
    np.testing.assert_allclose(
        source.rz_pts, rotate(points, 13.0, (0.9, 0.1)) + [0.3, -0.2], rtol=0.0, atol=1e-15
    )
    np.testing.assert_allclose(
        np.linalg.norm(source.rz_pts - source.centroid, axis=1), distance, rtol=1e-14, atol=1e-15
    )
    source.current = -3.0
    assert source.total_current == pytest.approx(-3.0 * source.weights.sum(), abs=1e-15)


@pytest.mark.parametrize("factory", [BRB, WHAM])
def test_complete_configuration_current_reversal_and_direct_child_state(factory):
    device = factory()
    mesh = PointsMesh([0.31, 0.77, 1.1], [0.12, -0.43, 0.68])
    device.mesh = mesh
    first = next(iter(device))
    original = first.rz_pts.copy()
    expected = {
        name: sum(getattr(child, name)() for child in device) for name in ["psi", "BR", "BZ"]
    }
    for name in expected:
        np.testing.assert_allclose(getattr(device, name)(), expected[name], rtol=2e-14, atol=2e-18)
        np.testing.assert_allclose(
            getattr(device, name)(current=-device.current), -expected[name], rtol=2e-14, atol=2e-18
        )
    first.translate([0.0, 0.07])
    first.psi()  # reproduce formerly dangerous child-before-parent cache order
    for name in expected:
        updated = sum(getattr(child, name)() for child in device)
        np.testing.assert_allclose(getattr(device, name)(), updated, rtol=2e-14, atol=2e-18)
    assert not np.array_equal(first.rz_pts, original)


def test_brb_geometry_parity_and_wham_reflection_at_every_source():
    brb = BRB()
    centers = np.array([getattr(brb, f"mr{i}").centroid for i in range(1, 37)])
    np.testing.assert_allclose(centers[:, 0], centers[::-1, 0], rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(centers[:, 1], -centers[::-1, 1], rtol=0.0, atol=1e-15)
    for i in range(2, 36):
        ring = getattr(brb, f"mr{i}")
        theta = np.linspace(7.5, 172.5, 34)[i - 2]
        assert ring.mu_hat == pytest.approx(theta + (i - 1) % 2 * 180.0, abs=1e-14)
        assert ring.current == pytest.approx(2710.68, abs=1e-12)
    wham = WHAM()
    for north, south in [(wham.hts1, wham.hts2), (wham.cc1, wham.cc2)]:
        expected = north.rz_pts.copy()
        expected[:, 1] *= -1
        np.testing.assert_allclose(
            np.sort(south.rz_pts, axis=0), np.sort(expected, axis=0), rtol=0.0, atol=1e-15
        )


def test_mutable_source_domain_errors_and_atomic_setters():
    source = ArbitraryPoints([[1.0, 0.0]], weights=[1.0], mesh=[[0.2, 0.3]])
    source.psi()
    source.rz_pts[0, 0] = -1.0
    with pytest.raises(ValueError):
        source.psi()
    source.rz_pts[0, 0] = 1.0
    source.weights[0] = np.nan
    with pytest.raises(ValueError):
        source.psi()
    mesh = RectMesh(nr=3, nz=2)
    original = Mesh.to_points(mesh).copy()
    with pytest.raises(ValueError):
        mesh.rmin = 2.0
    np.testing.assert_array_equal(Mesh.to_points(mesh), original)
