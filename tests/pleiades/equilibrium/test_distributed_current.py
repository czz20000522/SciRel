"""Independent loop-integral and port gates for the regular-grid consumer.

NASA 20010038494 equation (1): psi=R*A_phi, SI vacuum prefactor 1e-7.
The zero self-cell is an explicit compatibility discretization, not a finite
wire self-field. Triangulation topology is shared; barycentric evaluation and
current contraction are assembled here independently of production code.
"""
import importlib.util
import os
from pathlib import Path

import netCDF4
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.spatial import Delaunay


@pytest.fixture
def consumer():
    if os.environ.get('SCIREL_FROZEN_CONSUMER') == '1':
        path = Path('/prior-partial/get_deltapsi_consumer_witness.py')
        spec = importlib.util.spec_from_file_location('frozen_consumer_witness', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.load_frozen_helper()[0].get_deltapsi
    from scirel.electromagnetism.distributed import get_deltapsi
    return get_deltapsi


LAYERS = np.array([
    [[1., -2., 3., .5], [-.3, 4., -1., 2.], [2.5, -.7, 1.2, -3.]],
    [[-.2, .7, -1., 2.], [3., -2., .4, -.9], [-1., 1.5, -.6, 4.]],
])


def dataset(path, values):
    data = netCDF4.Dataset(path, 'w', format='NETCDF4_CLASSIC')
    data.createDimension('nzeqadim', values.shape[-2])
    data.createDimension('nreqadim', values.shape[-1])
    dims = ('nzeqadim', 'nreqadim')
    if values.ndim == 3:
        data.createDimension('layer', values.shape[0])
        dims = ('layer',) + dims
    var = data.createVariable('curr_diamcurv_phi', 'f8', dims)
    var.units = 'A/cm^2'
    var[:] = values
    return data


def reference(Req, Zeq, layers):
    nr, nz = layers.shape[-1], layers.shape[-2]
    r = np.linspace(Req.min(), Req.max(), nr)
    z = np.linspace(Zeq.min(), Zeq.max(), nz)
    source = np.array([(a, h) for h in z for a in r])
    currents = layers.sum(axis=0) if layers.ndim == 3 else layers
    values = []
    for R, Z in source:
        total = 0.
        for j, (a, z0) in enumerate(source):
            if (R == a and Z == z0) or R == 0 or a == 0:
                continue
            integral = quad(
                lambda phi: np.cos(phi) / np.sqrt(
                    (R-a)**2 + 4*R*a*np.sin(phi/2)**2 + (Z-z0)**2),
                0, 2*np.pi, epsabs=1e-12, epsrel=1e-12,
            )[0]
            total += 1e-7*a*R*integral*currents.ravel()[j]*1e4*(r[1]-r[0])*(z[1]-z[0])
        values.append(total)
    triangulation = Delaunay(source)
    targets = np.column_stack((Req.ravel(), Zeq.ravel()))
    result = []
    for target, simplex in zip(targets, triangulation.find_simplex(targets)):
        assert simplex >= 0
        vertices = triangulation.simplices[simplex]
        coordinates = source[vertices]
        barycentric = np.linalg.solve(
            np.vstack((coordinates.T, np.ones(3))), np.append(target, 1.))
        result.append(barycentric @ np.array(values)[vertices])
    return np.array(result).reshape(Req.shape)


def test_rectangular_signed_current_oracle_and_layer_sum(consumer, tmp_path):
    R, Z = np.meshgrid(np.linspace(.35, 1.25, 7), np.linspace(-.6, .8, 5))
    with dataset(tmp_path/'layers.nc', LAYERS) as data:
        before = data.variables['curr_diamcurv_phi'][:].copy()
        got = consumer(data, R, Z)
        np.testing.assert_array_equal(data.variables['curr_diamcurv_phi'][:], before)
    assert got.shape == (5, 7)
    np.testing.assert_allclose(got, reference(R, Z, LAYERS), rtol=1e-12, atol=1e-18)
    separately = []
    for i, layer in enumerate(LAYERS):
        with dataset(tmp_path/f'layer-{i}.nc', layer) as data:
            separately.append(consumer(data, R, Z))
    np.testing.assert_allclose(got, sum(separately), rtol=1e-12, atol=1e-18)
    with dataset(tmp_path/'negative.nc', -2*LAYERS) as data:
        np.testing.assert_allclose(consumer(data, R, Z), -2*got, rtol=1e-12, atol=1e-18)
    with dataset(tmp_path/'transposed-target.nc', LAYERS) as data:
        np.testing.assert_allclose(consumer(data, R.T, Z.T), got.T, rtol=1e-12, atol=1e-18)


def test_self_cell_zero_policy_not_finite_self_field(consumer, tmp_path):
    R, Z = np.meshgrid([.35, .65, .95, 1.25], [-.6, .1, .8])
    single = np.zeros((3, 4))
    single[1, 2] = 1.
    with dataset(tmp_path/'single.nc', single) as data:
        got = consumer(data, R, Z)
    assert got[1, 2] == 0
    np.testing.assert_allclose(got, reference(R, Z, single), rtol=1e-12, atol=1e-18)


def test_axis_sources_and_zero_weights_keep_discrete_omission_policy(consumer, tmp_path):
    R, Z = np.meshgrid([0.0, 0.5, 1.0, 1.5], [-0.6, 0.1, 0.8])
    values = np.zeros((3, 4))
    values[:, 0] = [4.0, -2.0, 1.0]
    values[1, 2] = 3.0
    with dataset(tmp_path/'axis-source.nc', values) as data:
        got = consumer(data, R, Z)
    np.testing.assert_allclose(got, reference(R, Z, values), rtol=1e-12, atol=1e-18)


@pytest.mark.parametrize('kind', ['one-cell', 'collapsed-r', 'collapsed-z', 'nonfinite-target', 'negative-radius'])
def test_invalid_geometry_has_explicit_value_error(consumer, tmp_path, kind):
    values = np.ones((3, 4))
    R, Z = np.meshgrid([.35, .65, .95, 1.25], [-.6, .1, .8])
    if kind == 'one-cell':
        values = np.ones((1, 4))
    elif kind == 'collapsed-r':
        R[:] = .5
    elif kind == 'collapsed-z':
        Z[:] = .2
    elif kind == 'nonfinite-target':
        R[0, 0] = np.nan
    elif kind == 'negative-radius':
        R[0, 0] = -.1
    with dataset(tmp_path/f'{kind}.nc', values) as data:
        with pytest.raises(ValueError):
            consumer(data, R, Z)


def test_masked_current_rejected(consumer, tmp_path):
    R, Z = np.meshgrid([.35, .65, .95, 1.25], [-.6, .1, .8])
    with dataset(tmp_path/'masked.nc', LAYERS) as data:
        data.variables['curr_diamcurv_phi'][0, 0, 0] = np.ma.masked
        with pytest.raises(ValueError):
            consumer(data, R, Z)
