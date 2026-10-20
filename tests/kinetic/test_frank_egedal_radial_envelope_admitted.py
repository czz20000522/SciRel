import numpy as np
import pytest
from scirel.kinetic.frank_egedal_radial_envelope import evaluate_frank_egedal_radial_envelope as envelope


def test_closed_form_and_input_ownership():
    x = np.array([[-2., 0., .25, .5, .75, 1., 3.]])
    saved = x.copy()
    out = envelope(x, {'psi_axis': 0., 'psi_edge': 1., 'alpha': 2.})
    np.testing.assert_array_equal(out, [[1., 1., .5625, .25, .0625, 0., 0.]])
    np.testing.assert_array_equal(x, saved)
    assert not np.shares_memory(x, out)


@pytest.mark.parametrize('scale,offset', [(4., 8.), (-4., 8.), (1e-12, 0.)])
def test_affine_flux_relabelling_preserves_envelope(scale, offset):
    x = np.array([[-1., 0., .25, .5, 1., 2.]])
    actual = envelope(scale*x+offset, {'psi_axis': offset, 'psi_edge': scale+offset, 'alpha': 1.})
    np.testing.assert_allclose(actual, [[1., 1., .75, .5, 0., 0.]])


def test_zero_exponent_and_default_references():
    np.testing.assert_array_equal(envelope([[-1., 0., 1., 2.]], {'alpha': 0.}), [[1., 1., 1., 1.]])
    np.testing.assert_array_equal(envelope([[2., 3., 4.]], {}), [[1., .5, 0.]])


@pytest.mark.parametrize('grid,params', [([], {}), ([[0., np.nan]], {}), ([[2., 2.]], {}),
    ([[0., 1.]], {'alpha': -1.}), ([[0., 1.]], {'alpha': np.inf}),
    ([[0., 1.]], {'psi_axis': -1e308, 'psi_edge': 1e308}),
    ([[0., 1.]], {'psi_axis': 0., 'psi_edge': 1e-31})])
def test_explicit_invalid_domain_is_rejected(grid, params):
    with pytest.raises(ValueError):
        envelope(grid, params)
