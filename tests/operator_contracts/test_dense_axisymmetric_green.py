# 测试命令：python -m pytest test_scientific_operator.py -q -p no:cacheprovider
import numpy as np
import pytest

from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response, dense_axisymmetric_green_response as scientific_operator
from scirel.field.circular_filament_green import circular_filament_green_response


def test_shape_finiteness_and_axis_source_columns():
    result = scientific_operator(
        [[0.0, -0.2], [0.1, 0.0], [0.2, 0.2]],
        [[0.3, 0.0, 1.0], [0.4, 0.1, -0.5]],
    )
    for value in result.values():
        assert value.shape == (3, 2)
        assert np.all(np.isfinite(value))
    np.testing.assert_allclose(
        scientific_operator([[0.1, 0.0]], [[0.0, 0.0, 1.0]])["gpsi"], 0.0
    )


def test_source_weight_scales_each_column_and_zeroes_a_column():
    targets = [[0.05, -0.1], [0.2, 0.15]]
    unit = scientific_operator(targets, [[0.3, 0.0, 1.0]])
    weighted = scientific_operator(targets, [[0.3, 0.0, -2.5]])
    for name in ("gpsi", "gBR", "gBZ"):
        np.testing.assert_allclose(weighted[name], -2.5 * unit[name])
    zero = scientific_operator(targets, [[0.3, 0.0, 0.0]])
    for value in zero.values():
        np.testing.assert_allclose(value, 0.0)


def test_columns_match_individual_filament_flux_and_field_responses():
    targets = np.array([[0.08, -0.17], [0.22, 0.04], [0.31, 0.18]])
    sources = np.array([[0.39, -0.06, 1.0], [0.48, 0.27, -0.4]])
    dense = scientific_operator(targets, sources)
    for column, source in enumerate(sources):
        single = circular_filament_green_response([source], targets)
        for name in ("gpsi", "gBR", "gBZ"):
            np.testing.assert_allclose(dense[name][:, column], single[name], rtol=2e-14, atol=1e-18)


def test_axis_bz_matches_circular_filament_limit():
    r0 = 0.35
    z0 = -0.1
    target_z = 0.25
    result = scientific_operator([[0.0, target_z]], [[r0, z0, 1.0]])
    distance = abs(target_z - z0)
    expected = 2.0 * np.pi * 1.0e-7 * r0**2 / (r0**2 + distance**2) ** 1.5
    np.testing.assert_allclose(result["gBZ"][0, 0], expected, rtol=1.0e-13, atol=1.0e-30)
    np.testing.assert_allclose(result["gBR"][0, 0], 0.0, atol=0.0)


def test_rejects_negative_target_radius():
    with pytest.raises(ValueError, match="cylindrical radii"):
        scientific_operator([[-0.1, 0.0]], [[0.3, 0.0, 1.0]])


def test_rejects_invalid_source_shape():
    with pytest.raises(ValueError, match="source_rzw"):
        scientific_operator([[0.1, 0.0]], [[0.3, 0.0]])


@pytest.mark.parametrize("shape", [(2, 0), (0, 2), (0, 3, 1)])
def test_empty_source_shorthand_does_not_hide_invalid_shapes(shape):
    with pytest.raises(ValueError, match="source_rzw"):
        scientific_operator([[0.1, 0.0]], np.empty(shape))


def test_empty_source_shorthand_matches_explicit_zero_source_matrix():
    shorthand = scientific_operator([[0.1, 0.0]], [])
    explicit = scientific_operator([[0.1, 0.0]], np.empty((0, 3)))
    for name in shorthand:
        np.testing.assert_array_equal(shorthand[name], explicit[name])


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response

    targets = np.array([[0.0, -0.1], [0.2, 0.15]])
    source_r = 0.35
    unit = dense_axisymmetric_green_response(targets, [[source_r, -0.1, 1.0]])
    weighted = dense_axisymmetric_green_response(targets, [[source_r, -0.1, -2.5]])
    empty = dense_axisymmetric_green_response(targets, [])
    for name in ("gpsi", "gBR", "gBZ"):
        np.testing.assert_allclose(weighted[name], -2.5 * unit[name])
        assert empty[name].shape == (targets.shape[0], 0)
    expected_axis_bz = 2.0 * np.pi * 1.0e-7 / source_r
    np.testing.assert_allclose(unit["gBZ"][0, 0], expected_axis_bz, rtol=1.0e-13)
    np.testing.assert_allclose(unit["gpsi"][0, 0], 0.0)
    np.testing.assert_allclose(unit["gBR"][0, 0], 0.0)
