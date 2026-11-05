import numpy as np
import pytest
from scirel.configurations import BRB, TREXCoil, WHAM
from scirel.electromagnetism import MagnetRing, RectangularCoil


def test_configurations_construct_and_preserve_source_counts():
    brb = BRB()
    assert len(brb.current_sets) == 40
    assert brb.hh_n.npts == brb.hh_s.npts == 88
    assert len([x for x in brb.current_sets if isinstance(x, MagnetRing)]) == 36
    wham = WHAM()
    assert len(wham.current_sets) == 4
    assert [x.npts for x in wham.current_sets] == [32, 32, 10, 10]
    trex = TREXCoil()
    assert trex.npts == 88
    assert trex.area == pytest.approx(0.0134166**2 * 88)


def test_configuration_geometry_can_evaluate_on_mesh():
    brb = BRB()
    mesh = np.array([[0.3, 0.0], [1.0, 0.2]])
    psi = brb.psi(mesh=mesh)
    assert psi.shape == (2,)
    assert np.all(np.isfinite(psi))


def test_rectangular_coil_rotate_then_translate_preserves_parameter_state():
    coil = RectangularCoil(1.0, 0.2, nr=2, nz=3, dr=0.1, dz=0.2)
    coil.rotate(90, pivot=(1.0, 0.2))
    rotated = coil.rz_pts.copy()
    coil.translate([0.2, 0.1])
    np.testing.assert_allclose(coil.rz_pts, rotated + [0.2, 0.1])
    np.testing.assert_allclose(coil.centroid, [1.2, 0.3])
    assert coil.angle == pytest.approx(90.0)


def test_magnet_ring_rotate_then_translate_preserves_parameter_state():
    ring = MagnetRing(1.0, 0.2, width=0.1, height=0.2, mu_hat=30.0)
    ring.rotate(20.0, pivot=(1.0, 0.2))
    rotated = ring.rz_pts.copy()
    ring.translate([0.2, 0.1])
    np.testing.assert_allclose(ring.rz_pts, rotated + [0.2, 0.1])
    np.testing.assert_allclose(ring.centroid, [1.2, 0.3])
    assert ring.mu_hat == pytest.approx(50.0)
