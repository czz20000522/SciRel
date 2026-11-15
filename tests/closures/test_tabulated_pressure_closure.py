from bisect import bisect_right
from fractions import Fraction as F

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


def linear_reference(axis, table, query):
    k = min(max(bisect_right(axis, query) - 1, 0), len(axis) - 2)
    a, b, x = map(F, (float(axis[k]), float(axis[k + 1]), float(query)))
    return ((b - x) * F(float(table[k])) + (x - a) * F(float(table[k + 1]))) / (b - a)


def bilinear_reference(b_axis, psi_axis, table, b, psi):
    i = min(max(bisect_right(b_axis, b) - 1, 0), len(b_axis) - 2)
    j = min(max(bisect_right(psi_axis, psi) - 1, 0), len(psi_axis) - 2)
    B0, B1, P0, P1, B, P = map(
        F, map(float, (b_axis[i], b_axis[i + 1], psi_axis[j], psi_axis[j + 1], b, psi))
    )
    wb, wp = (
        ((B1 - B) / (B1 - B0), (B - B0) / (B1 - B0)),
        ((P1 - P) / (P1 - P0), (P - P0) / (P1 - P0)),
    )
    return sum(
        (wb[r] * wp[c] * F(float(table[i + r][j + c])) for r in (0, 1) for c in (0, 1)), F(0)
    )


M = float.fromhex("0x1p+60")
L = float.fromhex("0x1p+1023")
S = float.fromhex("0x1p-1022")
CASES = [
    ("endpoint-1d", 1.0, 1.0, [0.0, 1.0], [M, 1.0], None),
    ("endpoint-2d-psi", 1.5, 1.0, [0.0, 1.0], [[M, 1.0], [M, 1.0]], [1.0, 2.0]),
    ("endpoint-2d-b", 2.0, 0.5, [0.0, 1.0], [[M, M], [1.0, 1.0]], [1.0, 2.0]),
    ("wide-axis-1d", 1.0, 0.0, [-L, L], [2.0, 4.0], None),
    ("wide-axis-2d-psi", 1.5, 0.0, [-L, L], [[2.0, 4.0], [2.0, 4.0]], [1.0, 2.0]),
    ("wide-axis-2d-b", 0.0, 0.5, [0.0, 1.0], [[2.0, 2.0], [4.0, 4.0]], [-L, L]),
    ("compensated-weight-1d", 1.0, S, [0.0, L], [0.0, L], None),
    ("compensated-weight-2d", 1.5, S, [0.0, L], [[0.0, L], [0.0, L]], [1.0, 2.0]),
]


@pytest.mark.parametrize("label,b,psi,axis,table,b_axis", CASES, ids=[c[0] for c in CASES])
def test_supported_table_raw_input_witness(label, b, psi, axis, table, b_axis):
    exact = (
        linear_reference(axis, table, psi)
        if b_axis is None
        else bilinear_reference(b_axis, axis, table, b, psi)
    )
    expected = float(exact)
    assert expected > 0.0 and np.isfinite(expected)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        result = evaluate_tabulated_pressure(b, psi, axis, table, b_grid=b_axis)
    for key in ("p_parallel", "p_perpendicular"):
        actual = float(np.asarray(result[key]))
        assert actual == expected, (
            f"{label}: {key}; exact={exact!s}, expected={expected!r}, actual={actual!r}"
        )


@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
@pytest.mark.parametrize("case", ["opposite-rows", "tiny-row"])
def test_complete_bilinear_contributions_before_rounding(case, policy):
    # Closed-form anchors from raw binary powers, independent of the evaluator:
    # averaging opposite slopes gives M/2; L*(minsub/4) gives 2**-53.
    minsub = float.fromhex("0x1p-1074")
    if case == "opposite-rows":
        field, flux, b_axis = 1.5, L, [1.0, 2.0]
        table, expected = [[0.0, M], [M, 0.0]], M / 2.0
    else:
        field, flux, b_axis = L, 0.25, [0.0, 1.0]
        table, expected = [[0.0, 0.0], [0.0, minsub]], 2.0**-53
    assert float(bilinear_reference(b_axis, [0.0, 1.0], table, field, flux)) == expected
    with np.errstate(all=policy):
        result = evaluate_tabulated_pressure(
            field,
            flux,
            [0.0, 1.0],
            table,
            b_grid=b_axis,
            bounds_error=False,
            fill_value=None,
        )
    for key in ("p_parallel", "p_perpendicular"):
        assert result[key] == expected


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize("case", ["positive-underflow", "negative-underflow", "overflow"])
@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
def test_genuine_final_range_failure_rejects_instead_of_returning_zero(dimension, case, policy):
    minsub = float.fromhex("0x1p-1074")
    if case == "overflow":
        row, flux = [np.finfo(float).max / 2.0, np.finfo(float).max], 2.0
    else:
        row = [0.0, minsub]
        flux = 0.25 if case == "positive-underflow" else -0.25
    exact = linear_reference([0.0, 1.0], row, flux)
    if case == "overflow":
        assert exact > F(float(np.finfo(float).max))
    elif case == "positive-underflow":
        assert 0 < exact < F(minsub) / 2
    else:
        assert -F(minsub) / 2 < exact < 0
    with np.errstate(all=policy), pytest.raises(ValueError, match="finite and nonnegative"):
        evaluate_tabulated_pressure(
            1.5,
            flux,
            [0.0, 1.0],
            row if dimension == 1 else [row, row],
            b_grid=None if dimension == 1 else [1.0, 2.0],
            bounds_error=False,
            fill_value=None,
        )


@pytest.mark.parametrize("dimension", [1, 2])
def test_true_zero_subnormal_node_and_maximum_constant_are_preserved(dimension):
    minsub, maximum = float.fromhex("0x1p-1074"), np.finfo(float).max
    for row, flux, expected in [
        ([0.0, minsub], 0.0, 0.0),
        ([0.0, minsub], 1.0, minsub),
        ([maximum, maximum], 0.375, maximum),
    ]:
        with np.errstate(all="raise"):
            result = evaluate_tabulated_pressure(
                1.5,
                flux,
                [0.0, 1.0],
                row if dimension == 1 else [row, row],
                b_grid=None if dimension == 1 else [1.0, 2.0],
            )
        assert result.p_parallel == expected
        assert result.p_perpendicular == expected


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
def test_wide_axes_fill_and_input_validation(dimension, policy):
    row = [0.0, L]
    table = np.array(row if dimension == 1 else [row, row])
    axes = np.array([-L, L])
    with np.errstate(all=policy):
        result = evaluate_tabulated_pressure(
            [0.0, 0.0],
            [0.0, L],
            axes,
            table,
            b_grid=None if dimension == 1 else axes,
        )
        np.testing.assert_array_equal(result.p_parallel, [L / 2.0, L])
        # An irrelevant out-of-domain extrapolation would overflow.
        fill = evaluate_tabulated_pressure(
            1.5,
            [-L, 0.5, L],
            [0.0, 1.0],
            table,
            b_grid=None if dimension == 1 else [1.0, 2.0],
            bounds_error=False,
            fill_value=7.0,
        )
        np.testing.assert_array_equal(fill.p_parallel, [7.0, L / 2.0, 7.0])
        for bad in (np.nan, np.inf, -1.0):
            invalid_table = table.copy()
            invalid_table.flat[0] = bad
            with pytest.raises(ValueError):
                evaluate_tabulated_pressure(
                    1.5,
                    L,
                    [0.0, 1.0],
                    invalid_table,
                    b_grid=None if dimension == 1 else [1.0, 2.0],
                    bounds_error=False,
                    fill_value=7.0,
                )
        with pytest.raises(ValueError, match="must be finite"):
            evaluate_tabulated_pressure(
                1.5,
                np.inf,
                [0.0, 1.0],
                table,
                b_grid=None if dimension == 1 else [1.0, 2.0],
                bounds_error=False,
                fill_value=7.0,
            )


@pytest.mark.parametrize("scale", [2.0**-129, 2.0**-128, 1.0, 2.0**128, 2.0**129])
@pytest.mark.parametrize("dimension", [1, 2])
def test_nonuniform_broadcast_fraction_reference_and_inputs_unchanged(scale, dimension):
    axis = scale * np.array([-2.0, 0.0, 0.25, 3.0])
    b_axis = scale * np.array([-3.0, -1.0, 2.0])
    field = scale * np.array([[-3.0], [-0.375], [2.0]])
    flux = scale * np.array([[-2.0, -0.375, 0.125, 3.0]])
    row = scale * np.array([0.0, 2.0, 0.25, 8.0])
    parallel = row if dimension == 1 else np.stack([row, row + scale, 2 * row])
    perpendicular = None if dimension == 1 else parallel + scale / 4
    saved = [a.copy() for a in (axis, b_axis, field, flux, parallel)]
    if perpendicular is not None:
        saved.append(perpendicular.copy())
    with np.errstate(all="raise"):
        result = evaluate_tabulated_pressure(
            field,
            flux,
            axis,
            parallel,
            perpendicular,
            None if dimension == 1 else b_axis,
        )
    for key, table in [
        ("p_parallel", parallel),
        ("p_perpendicular", parallel if dimension == 1 else perpendicular),
    ]:
        expected = np.array(
            [
                [
                    float(
                        linear_reference(axis, table, y)
                        if dimension == 1
                        else bilinear_reference(b_axis, axis, table, x, y)
                    )
                    for y in flux[0]
                ]
                for x in field[:, 0]
            ]
        )
        np.testing.assert_allclose(result[key], expected, rtol=64 * np.finfo(float).eps, atol=0)
    for original, before in zip(
        (axis, b_axis, field, flux, parallel) + (() if dimension == 1 else (perpendicular,)),
        saved,
        strict=True,
    ):
        np.testing.assert_array_equal(original, before)
    assert result.is_isotropic is (dimension == 1)
    # The original empty-query behavior and metadata are preserved.
    empty = evaluate_tabulated_pressure(
        np.empty((0, 1)),
        np.empty((1, 2)),
        axis,
        parallel,
        perpendicular,
        None if dimension == 1 else b_axis,
    )
    assert empty.p_parallel.shape == empty.p_perpendicular.shape == (0, 2)


@pytest.mark.parametrize("dimension", [1, 2])
@pytest.mark.parametrize(
    "value",
    [
        2.0**128,
        np.nextafter(2.0**128, np.inf),
        2.0**-128,
        np.nextafter(2.0**-128, 0.0),
    ],
)
def test_arithmetic_optimization_boundary_is_not_an_input_limit(dimension, value):
    # Constant interpolation is exactly the raw table value on both sides.
    row = [value, value]
    with np.errstate(all="raise"):
        result = evaluate_tabulated_pressure(
            0.375,
            0.625,
            [0.0, 1.0],
            row if dimension == 1 else [row, row],
            b_grid=None if dimension == 1 else [0.0, 1.0],
        )
    assert result.p_parallel == result.p_perpendicular == value


@pytest.mark.parametrize("dimension", [1, 2])
def test_subnormal_nonuniform_axis_and_adjacent_large_nodes(dimension):
    # Adjacent binary64 coordinates remain distinct despite their scale.
    minsub = float.fromhex("0x1p-1074")
    for axis, flux in [
        ([0.0, minsub, 4 * minsub], 2 * minsub),
        (
            [L, np.nextafter(L, np.inf), np.nextafter(L, np.inf) * (1 + 2**-52)],
            np.nextafter(L, np.inf),
        ),
    ]:
        row = [0.0, 3.0, 6.0]
        expected = float(linear_reference(axis, row, flux))
        with np.errstate(all="raise"):
            result = evaluate_tabulated_pressure(
                1.5,
                flux,
                axis,
                row if dimension == 1 else [row, row],
                b_grid=None if dimension == 1 else [1.0, 2.0],
            )
        assert result.p_parallel == result.p_perpendicular == expected
