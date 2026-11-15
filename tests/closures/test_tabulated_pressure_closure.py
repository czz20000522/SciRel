import numpy as np
import pytest

from scirel.closures.tabulated_pressure_closure import (
    evaluate_tabulated_pressure,
    evaluate_tabulated_pressure as scientific_function,
)


def test_anisotropic_bilinear_table_matches_declared_values():
    result = scientific_function(
        np.array([1.5, 2.5]),
        np.array([0.25, 0.75]),
        np.array([0.0, 0.5, 1.0]),
        np.array([[1.0, 2.0, 3.0], [2.0, 3.0, 4.0], [3.0, 4.0, 5.0]]),
        np.array([[3.0, 3.5, 4.0], [6.0, 6.5, 7.0], [9.0, 9.5, 10.0]]),
        np.array([1.0, 2.0, 3.0]),
    )
    np.testing.assert_allclose(result["p_parallel"], [2.0, 4.0])
    np.testing.assert_allclose(result["p_perpendicular"], [4.75, 8.25])
    assert not result["is_isotropic"]


def test_isotropic_limit_ignores_field_and_default_domain_fails_closed():
    result = scientific_function(
        np.array([1.0, 8.0]),
        np.array([0.25, 0.75]),
        np.array([0.0, 0.5, 1.0]),
        np.array([10.0, 5.0, 0.0]),
    )
    np.testing.assert_allclose(result["p_parallel"], [7.5, 2.5])
    assert result["is_isotropic"]
    with pytest.raises(ValueError):
        scientific_function(1.0, 2.0, np.array([0.0, 1.0]), np.array([1.0, 0.0]))


def test_reviewed_relation_example():
    from scirel.closures.tabulated_pressure_closure import evaluate_tabulated_pressure
    import numpy as np

    b_axis = np.array([1.0, 2.0, 3.0])
    psi_axis = np.array([0.0, 0.5, 1.0])
    B, P = np.meshgrid(b_axis, psi_axis, indexing="ij")
    parallel = 1.0 + B + 2.0 * P + B * P
    perpendicular = 3.0 + 2.0 * B - P + 0.5 * B * P
    query_b = np.array([1.5, 2.5])
    query_psi = np.array([0.25, 0.75])
    result = evaluate_tabulated_pressure(
        query_b, query_psi, psi_axis, parallel, perpendicular, b_axis
    )
    np.testing.assert_allclose(
        result["p_parallel"], 1.0 + query_b + 2.0 * query_psi + query_b * query_psi
    )
    np.testing.assert_allclose(
        result["p_perpendicular"], 3.0 + 2.0 * query_b - query_psi + 0.5 * query_b * query_psi
    )
    assert not result["is_isotropic"]

    # 一维分支要求两个显式表逐节点同形且相等；magnetic_field 只参与广播。
    isotropic_table = np.array([2.0, 4.0, 8.0])
    isotropic = evaluate_tabulated_pressure(
        np.array([10.0, 20.0]),
        np.array([0.25, 0.75]),
        psi_axis,
        isotropic_table,
        isotropic_table.copy(),
    )
    np.testing.assert_allclose(isotropic["p_parallel"], [3.0, 6.0])
    np.testing.assert_allclose(isotropic["p_perpendicular"], [3.0, 6.0])
    assert isotropic["is_isotropic"]


def test_contract_rejects_nonfinite_fill_and_nonphysical_extrapolation():
    import numpy as np
    import pytest

    psi_grid = np.array([0.0, 1.0])
    b_grid = np.array([1.0, 2.0])
    table = np.ones((2, 2))
    with pytest.raises(ValueError, match="fill_value"):
        evaluate_tabulated_pressure(
            5.0,
            0.5,
            psi_grid,
            table,
            b_grid=b_grid,
            bounds_error=False,
            fill_value=np.nan,
        )
    with pytest.raises(ValueError, match="finite and nonnegative"):
        evaluate_tabulated_pressure(
            5.0,
            0.5,
            psi_grid,
            np.array([[2.0, 2.0], [1.0, 1.0]]),
            b_grid=b_grid,
            bounds_error=False,
            fill_value=None,
        )


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize("options", [(False,), (False, 9.0)])
def test_behavior_options_reject_positional_arguments(dimension, options):
    args = (
        1.5,
        0.5,
        [0.0, 1.0],
        [2.0, 6.0] if dimension == 1 else [[2.0, 6.0], [4.0, 8.0]],
        None if dimension == 1 else [[3.0, 7.0], [5.0, 9.0]],
        None if dimension == 1 else [1.0, 2.0],
    )
    with pytest.raises(TypeError):
        evaluate_tabulated_pressure(*args, *options)


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize("mode", ["default", "bounds", "extrapolate", "fill-zero", "fill"])
def test_named_behavior_options_preserve_result_broadcast_and_domain_values(dimension, mode):
    from scirel._result import Result

    field = np.array([[1.25], [1.75]])
    flux = np.array([[0.0, 0.5, 1.0] if mode in ("default", "bounds") else [-0.25, 0.5, 1.25]])
    options = {
        "default": {},
        "bounds": {"bounds_error": True, "fill_value": None},
        "extrapolate": {"bounds_error": False, "fill_value": None},
        "fill-zero": {"bounds_error": False, "fill_value": 0.0},
        "fill": {"bounds_error": False, "fill_value": 9.0},
    }[mode]
    result = evaluate_tabulated_pressure(
        field,
        flux,
        [0.0, 1.0],
        [2.0, 6.0] if dimension == 1 else [[2.0, 6.0], [4.0, 8.0]],
        None if dimension == 1 else [[3.0, 7.0], [5.0, 9.0]],
        None if dimension == 1 else [1.0, 2.0],
        **options,
    )
    expected_parallel = np.broadcast_to(
        2.0 + 4.0 * flux if dimension == 1 else 2.0 * field + 4.0 * flux, (2, 3)
    ).copy()
    expected_perpendicular = expected_parallel.copy() + (dimension == 2)
    if mode.startswith("fill"):
        expected_parallel[:, [0, 2]] = options["fill_value"]
        expected_perpendicular[:, [0, 2]] = options["fill_value"]
    assert type(result) is Result
    assert list(result) == ["p_parallel", "p_perpendicular", "is_isotropic", "table_dimension"]
    for name, expected in (
        ("p_parallel", expected_parallel),
        ("p_perpendicular", expected_perpendicular),
    ):
        assert type(result[name]) is np.ndarray and result[name].shape == (2, 3)
        np.testing.assert_array_equal(result[name], expected)
        assert getattr(result, name) is result[name]
    assert result["is_isotropic"] is (dimension == 1)
    assert result["table_dimension"] == dimension


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize("options", [{}, {"bounds_error": True, "fill_value": 9.0}])
def test_named_bounds_reject_outside_queries_before_returning_a_result(dimension, options):
    with pytest.raises(ValueError, match="outside the interpolation domain"):
        evaluate_tabulated_pressure(
            1.5,
            1.25,
            [0.0, 1.0],
            [2.0, 6.0] if dimension == 1 else [[2.0, 6.0], [4.0, 8.0]],
            None,
            None if dimension == 1 else [1.0, 2.0],
            **options,
        )


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize(
    "options,message",
    [
        ({"bounds_error": 0}, "bounds_error must be boolean"),
        ({"bounds_error": None}, "bounds_error must be boolean"),
        ({"bounds_error": False, "fill_value": -1.0}, "fill_value"),
        ({"bounds_error": False, "fill_value": np.nan}, "fill_value"),
        ({"bounds_error": False, "fill_value": np.inf}, "fill_value"),
        ({"bounds_error": False, "fill_value": [1.0]}, "fill_value"),
    ],
)
def test_named_invalid_options_retain_their_value_errors(dimension, options, message):
    with pytest.raises(ValueError, match=message):
        evaluate_tabulated_pressure(
            1.5,
            0.5,
            [0.0, 1.0],
            [2.0, 6.0] if dimension == 1 else [[2.0, 6.0], [4.0, 8.0]],
            None,
            None if dimension == 1 else [1.0, 2.0],
            **options,
        )
