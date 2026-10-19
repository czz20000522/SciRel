"""D2 state/port regressions, frozen before successor implementation.

Current overrides follow I_k times the weighted per-source Green matrix.
TREX z0 follows its reference plane under translation/rotation; assignments
translate the existing cloud rather than reconstructing hidden source geometry.
"""
import numpy as np
import pytest

from scirel.configurations import TREXCoil
from scirel.electromagnetism import ArbitraryPoints, Device, compute_greens
from scirel.geometry import Mesh, PointsMesh, rotate


@pytest.mark.parametrize('name', ['psi', 'BR', 'BZ'])
@pytest.mark.parametrize('current', [np.nan, np.inf, [2., 3.]])
def test_source_common_current_override_requires_finite_scalar(name, current):
    source = ArbitraryPoints([[1., 0.]], mesh=[[.2, .3], [.4, -.2]])
    with pytest.raises(ValueError, match='current'):
        getattr(source, name)(current=current)


def test_device_ordered_current_matrix_override_and_mesh_lifecycle():
    mesh = PointsMesh([.2, .4], [.3, -.2])
    device = Device(mesh=mesh)
    device.first = ArbitraryPoints([[1., 0.]], current=2., weights=[-1.5])
    device.second = ArbitraryPoints([[.8, .1]], current=-3., weights=[.7])
    assert list(device) == [device.first, device.second]
    np.testing.assert_array_equal(device.current, [2., -3.])
    np.testing.assert_array_equal(device.R, mesh.R)
    np.testing.assert_array_equal(device.Z, mesh.Z)
    expected = compute_greens(device.rzw, Mesh.to_points(mesh))
    for field, green, rows in zip(('psi', 'BR', 'BZ'), ('gpsi', 'gBR', 'gBZ'), expected):
        np.testing.assert_allclose(getattr(device, green)(), rows, rtol=1e-15, atol=0.)
        np.testing.assert_allclose(getattr(device, field)(), np.array([2., -3.]) @ rows, rtol=1e-15, atol=0.)
        np.testing.assert_allclose(getattr(device, field)(current=[-4., 1.]), np.array([-4., 1.]) @ rows, rtol=1e-15, atol=0.)
        np.testing.assert_allclose(getattr(device, field)(current=0.), np.zeros(2), rtol=0., atol=0.)
        exposed = getattr(device, green)()
        exposed[:] = 42.
        np.testing.assert_array_equal(getattr(device, green)(), rows)
    alternate = PointsMesh([.1], [.7])
    device.mesh = alternate
    assert device.first.mesh is alternate and device.second.mesh is alternate
    device.mesh = None
    assert device.first.mesh is None and device.second.mesh is None
    with pytest.raises(ValueError, match='mesh'):
        device.psi()


@pytest.mark.parametrize('current', [[1.], [1., 2., 3.], [np.nan, 2.], np.inf])
def test_device_current_override_rejects_invalid_vectors(current):
    device = Device(mesh=[[.2, .3]])
    device.first = ArbitraryPoints([[1., 0.]])
    device.second = ArbitraryPoints([[.8, .1]])
    with pytest.raises(ValueError, match='current'):
        device.psi(current=current)


def test_trex_reference_plane_tracks_transforms_before_z0_assignment():
    coil = TREXCoil(z0=1.1)
    initial = coil.rz_pts.copy()
    coil.translate([.2, .4])
    assert coil.z0 == pytest.approx(1.5, abs=1e-15)
    np.testing.assert_allclose(coil.rz_pts, initial + [.2, .4], rtol=0., atol=1e-15)
    coil.z0 = -.3
    np.testing.assert_allclose(coil.rz_pts, initial + [.2, -1.4], rtol=0., atol=1e-15)
    before = coil.rz_pts.copy()
    center = before.mean(axis=0)
    coil.rotate(20., pivot=center)
    assert coil.z0 == pytest.approx(center[1], abs=1e-15)
    np.testing.assert_allclose(coil.rz_pts, rotate(before, 20., center), rtol=0., atol=1e-15)
    rotated = coil.rz_pts.copy()
    coil.z0 = .6
    np.testing.assert_allclose(coil.rz_pts, rotated + [0., .9], rtol=0., atol=1e-15)


def test_empty_device_matrix_shapes_and_missing_mesh():
    device = Device(mesh=[[.2, .3], [.4, -.2]])
    assert device.gpsi().shape == (0, 2)
    np.testing.assert_array_equal(device.psi(), [0., 0.])
    np.testing.assert_array_equal(device.psi(current=[]), [0., 0.])
    with pytest.raises(ValueError, match='mesh'):
        Device().psi()


def test_device_rejects_duplicate_physical_child_without_partial_registration():
    device = Device(mesh=[[.2, .3]])
    source = ArbitraryPoints([[1., 0.]])
    device.first = source
    before = device.psi().copy()
    with pytest.raises(AttributeError, match='already|registered'):
        device.alias = source
    assert device.current_sets == [source]
    assert not hasattr(device, 'alias')
    np.testing.assert_array_equal(device.psi(), before)
    device.first = source
    assert device.current_sets == [source]


def test_device_preserves_frozen_current_first_and_saved_mesh_first_calls():
    import inspect
    assert list(inspect.signature(Device.psi).parameters) == ['self', 'current', 'mesh']
    device = Device(mesh=[[.2, .3]])
    device.first = ArbitraryPoints([[1., 0.]], current=2.)
    alternate = PointsMesh([.4], [-.2])
    expected = device.first.psi(current=-3., mesh=alternate)
    np.testing.assert_array_equal(device.psi([-3.], alternate), expected)
    np.testing.assert_array_equal(device.psi(alternate), device.psi(mesh=alternate))
    array = np.array([[.4, -.2]])
    np.testing.assert_array_equal(device.psi(array), device.psi(mesh=array))
