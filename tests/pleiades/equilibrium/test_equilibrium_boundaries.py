"""D2 falsification of the bounded pressure-current feedback contract."""
import importlib
import importlib.util
import os
from pathlib import Path
import sys

import numpy as np
import pytest


def module():
    target = os.environ.get('SCIREL_EQUILIBRIUM_TARGET')
    if target is None:
        return importlib.import_module('scirel.equilibrium')
    path = Path(target)
    spec = importlib.util.spec_from_file_location('bounded_equilibrium_target', path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def data():
    R = np.tile(np.arange(1.0, 6.0), (2, 1))
    Z = np.tile(np.array([-1.0, 0.0])[:, None], (1, 5))
    return R, Z, lambda r: 5.0-r, R.copy(), np.zeros((10, 10))


def test_full_old_current_relaxation_is_rejected():
    # I_new=(1-relax)*R*Pprime*dR*dZ + relax*I_old. At relax=1 and
    # I_old=0 this erases a known nonzero pressure-current closure forever.
    # A zero flux update therefore cannot qualify this parameter as a solve.
    with pytest.raises(ValueError, match='relax'):
        module().compute_equilibrium(*data(), relax=1.0)


@pytest.mark.parametrize('index', [0, 1, 3, 4])
def test_complex_scientific_arrays_are_rejected_before_cast(index):
    arguments = list(data())
    arguments[index] = arguments[index].astype(complex) + 1j
    with pytest.raises(ValueError, match='real'):
        module().compute_equilibrium(*arguments)


@pytest.mark.parametrize('bound', [True, np.bool_(False), 2.0, np.inf, np.nan])
def test_iteration_bound_requires_nonboolean_integer(bound):
    with pytest.raises(ValueError, match='maxiter'):
        module().compute_equilibrium(*data(), maxiter=bound)


def test_clip_mask_requires_grid_shape_even_when_size_matches():
    with pytest.raises(ValueError, match='plas_clip'):
        module().compute_equilibrium(*data(), plas_clip=np.zeros(10, dtype=bool))


def test_clip_mask_validated_even_without_iterations():
    with pytest.raises(ValueError, match='plas_clip'):
        module().compute_equilibrium(*data(), plas_clip=np.zeros((2, 4), dtype=bool), maxiter=0)


@pytest.mark.parametrize('kind', ['nonrectangular', 'nonuniform', 'folded_z'])
def test_grid_rejects_approximate_allclose_false_positive(kind):
    arguments = list(data())
    if kind == 'nonrectangular':
        arguments[0] = arguments[0].copy()
        arguments[0][0, 2] += 1e-6
    elif kind == 'nonuniform':
        arguments[0] = arguments[0].copy()
        arguments[0][:, 2] += 1e-6
    else:
        arguments[0] = np.tile(np.arange(1., 6.), (3, 1))
        arguments[1] = np.tile(np.array([-1., 0., -1.])[:, None], (1, 5))
        arguments[3] = arguments[0].copy()
        arguments[4] = np.zeros((15, 15))
    with pytest.raises(ValueError, match='R|Z|spacing|axes'):
        module().compute_equilibrium(*arguments)


def test_decimal_uniform_grid_and_descending_z_remain_supported():
    R, Z = np.meshgrid(np.linspace(.35, 1.25, 5), np.linspace(.6, -.6, 7))
    Redge = float(R[0, -1])
    result = module().compute_equilibrium(R, Z, lambda r: Redge-r, R, np.zeros((35, 35)))
    assert result.status == "converged"
    assert result.iterations == 1
    np.testing.assert_allclose(result.plas_currents, -R*.225*.2, rtol=1e-12, atol=1e-12)


def test_feedback_cap_has_analytic_geometric_decay_and_final_fit():
    # Constant Green shift leaves P'=-1; relaxation with alpha=.5 yields
    # I_n=-R*(1-2**(-n)), psi_n=R-.1*(1-2**(-n)). This independently gives
    # both the state and update-norm residual after each cap.
    R, Z, P, psi, _ = data()
    G = np.full((10, 10), 1./300.)
    for n in [1, 2, 3, 6, 10]:
        result = module().compute_equilibrium(R, Z, P, psi, G, relax=.5, maxiter=n, tol=1e-14)
        factor = 1.-2.**(-n)
        assert result.status == 'maxiter'
        assert result.iterations == n
        np.testing.assert_allclose(result.plas_currents, -R*factor, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(result.psi, R-.1*factor, rtol=1e-12, atol=1e-12)
        expected_residual = np.sqrt(10.)*.1*2.**(-n)/(5.-.1*factor)
        np.testing.assert_allclose(result.residual, expected_residual, rtol=1e-10, atol=1e-13)
        np.testing.assert_allclose(result.p_psifit(result.psi[-1]), 5.-R[-1], rtol=1e-12, atol=1e-12)


def test_zero_edge_is_failed_snapshot_without_convergence_claim():
    R, Z, P, _, G = data()
    result = module().compute_equilibrium(R, Z, P, R-5., G)
    assert result.status == 'nonfinite'
    assert result.iterations == 0
    assert np.isnan(result.residual)
    assert result.reason == 'zero or nonfinite edge flux'
    np.testing.assert_array_equal(result.plas_currents, np.zeros(R.shape))
