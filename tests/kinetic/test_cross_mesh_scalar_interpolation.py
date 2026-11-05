"""Direct contract tests for the neutral-transport formulation spatial scalar mesh handoff."""

from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import interpolate_scalar_across_mesh


def test_linear_profile_and_exact_knots():
    xa = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    fa = 1.0 + 2.0 * xa
    xb = np.array([0.0, 0.25, 0.8, 1.1, 1.6, 2.0])
    np.testing.assert_allclose(
        interpolate_scalar_across_mesh(fa, xa, xb),
        1.0 + 2.0 * xb,
        rtol=0.0,
        atol=4.0 * np.finfo(float).eps,
    )


def test_out_of_range_zero_fill_and_affine_invariance():
    xa = np.array([0.1, 0.7, 1.3, 2.9])
    fa = np.array([-2.5, 4.0, 0.0, 7.25])
    xb = np.array([-1.0, 0.1, 1.0, 2.9, 5.0])
    fb = interpolate_scalar_across_mesh(fa, xa, xb)
    assert fb[0] == fb[-1] == 0.0
    transformed = interpolate_scalar_across_mesh(3.0 * fa + 1.0, xa, xb)
    np.testing.assert_allclose(transformed[1:-1], 3.0 * fb[1:-1] + 1.0, rtol=0, atol=1e-12)


def test_unsorted_but_contiguous_in_range_nodes_keep_positional_mapping():
    np.testing.assert_array_equal(
        interpolate_scalar_across_mesh([0.0, 1.0], [0.0, 1.0], [2.0, 0.8, 0.2, -1.0]),
        [0.0, 0.8, 0.2, 0.0],
    )


def test_noncontiguous_in_range_nodes_fail_closed():
    with pytest.raises(ValueError, match="contiguous block"):
        interpolate_scalar_across_mesh([0.0, 1.0], [0.0, 1.0], [0.5, 2.0, 0.6])


def test_warnings_do_not_change_values():
    fa, xa, xb = [1.0, 2.0, 3.0], [0.0, 1.0, 2.0], [-1.0, 0.5, 1.5, 3.0]
    expected = interpolate_scalar_across_mesh(fa, xa, xb)
    with pytest.warns(UserWarning) as caught:
        actual = interpolate_scalar_across_mesh(fa, xa, xb, do_warn=-1)
    assert len(caught) == 2
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize(
    ("fa", "xa", "xb", "message"),
    [
        ([1.0], [0.0, 1.0], [0.5], "fa"),
        ([1.0, 2.0], [0.0, 0.0], [0.0], "strictly increasing"),
        ([1.0, 2.0], [0.0, 1.0], [2.0], "within range"),
        ([1.0], [0.0], [0.0], "xa"),
        ([1.0, np.nan], [0.0, 1.0], [0.5], "fa"),
        ([1.0, 2.0], [0.0, 1.0], [np.inf], "xb"),
        ([1.0, 2.0], [0.0, 1.0], [[0.5]], "xb"),
        ([1.0, True], [0.0, 1.0], [0.5], "fa"),
        ([1.0, 2.0], ["0", "1"], [0.5], "xa"),
        ([1.0, 2.0], [0.0, 1.0], [0.5 + 0j], "xb"),
    ],
)
def test_invalid_arrays_fail_closed(fa, xa, xb, message):
    with pytest.raises(ValueError, match=message):
        interpolate_scalar_across_mesh(fa, xa, xb)


@pytest.mark.parametrize("do_warn", [True, 1.0, "1", 1 + 0j, np.inf, [1]])
def test_warning_selector_must_be_an_integer_scalar(do_warn):
    with pytest.raises(ValueError, match="do_warn"):
        interpolate_scalar_across_mesh([1.0, 2.0], [0.0, 1.0], [0.5], do_warn)
