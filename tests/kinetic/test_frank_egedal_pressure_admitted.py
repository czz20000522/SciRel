import numpy as np
import pytest
from scirel.kinetic.frank_egedal_pressure_state import assemble_frank_egedal_pressure as assemble

def run(params, a=None):
    return assemble([[2., 3.]], [[1., .5]] if a is None else a, [[2., 3.]], [[4., 5.]], [[7., 11.]], params)

def test_independent_cellwise_formula_and_anisotropy():
    result = run({'hot_pressure_scale': 3., 'gas_dynamic_pressure': 5., 'gas_dynamic_density': 2., 'hot_density_scale': 4., 'electron_temperature': .25})
    for i, (a, hp, ht, hn) in enumerate([(1., 2., 4., 7.), (.5, 3., 5., 11.)]):
        density = a * (2 + 4 * hn)
        isotropic = a * 5 + density * .25
        assert result['density'][0, i] == density
        assert result['p_parallel'][0, i] == isotropic + 3 * a * hp
        assert result['p_perp'][0, i] == isotropic + 3 * a * ht
        assert result['p_perp'][0, i] - result['p_parallel'][0, i] == 3 * a * (ht - hp)

def test_missing_density_differs_from_explicit_zero():
    missing = run({'electron_temperature': 9.})
    explicit = run({'gas_dynamic_density': 0., 'electron_temperature': 9.})
    assert missing['density'] is None
    np.testing.assert_array_equal(explicit['density'], [[0., 0.]])
    for name in ('p_parallel', 'p_perp', 'electron_temperature'):
        np.testing.assert_array_equal(missing[name], explicit[name])

def test_scale_fallback_and_zero_radial_envelope():
    np.testing.assert_array_equal(run({'p0': 2.})['p_parallel'], [[4., 3.]])
    np.testing.assert_array_equal(run({'p0': 99., 'hot_pressure_scale': 0.})['p_parallel'], [[0., 0.]])
    zero = run({'background_density': 8., 'hot_density_scale': 3., 'electron_temperature': 4.}, [[0., 0.]])
    for name in ('p_parallel', 'p_perp', 'density'):
        np.testing.assert_array_equal(zero[name], [[0., 0.]])

@pytest.mark.parametrize('key', ['hot_pressure_scale','gas_dynamic_pressure','gas_dynamic_density','hot_density_scale','electron_temperature'])
def test_negative_scale_is_rejected(key):
    with pytest.raises(ValueError):
        run({key: -1.})

def test_overflow_is_rejected():
    with np.errstate(over='ignore'), pytest.raises(ValueError, match='non-finite'):
        run({'hot_pressure_scale': 1e308})

def test_finite_grid_shape_validation_and_input_preservation():
    shape = np.array([[1., .5]])
    before = shape.copy()
    run({}, shape)
    np.testing.assert_array_equal(shape, before)
    for invalid in ([[np.nan, .5]], [[-1., .5]], [[1.]]):
        with pytest.raises(ValueError):
            run({}, invalid)
