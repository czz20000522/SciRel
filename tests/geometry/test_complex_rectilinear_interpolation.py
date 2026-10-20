"""Direct, discriminating contract tests for the U2 complex interpolation candidate.

These tests load the *isolated* candidate module by file path, so the frozen
``src/scirel`` tree is never on ``sys.path`` and never imported.  Every claim in
``documents/scirel.geometry.complex-rectilinear-interpolation.json`` is bound to
a test ID below.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import math
import os
from pathlib import Path

import numpy as np
import pytest

_CANDIDATE = Path(
    importlib.import_module(
        "scirel.geometry.complex_rectilinear_interpolation"
    ).__file__
).resolve() if os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1" else (
    Path(__file__).resolve().parents[2]
    / "src/scirel/geometry/complex_rectilinear_interpolation.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "scirel_candidate_u2_complex_rectilinear_interpolation", _CANDIDATE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load()
INTERPOLATE = MODULE.interpolate_complex_rectilinear_field

# Deliberately non-uniform axes: a swapped or reordered axis is detected.
AXES = {"x_m": np.array([0.0, 1.0, 2.0]), "y_m": np.array([-1.0, 0.5, 3.0]), "z_m": np.array([0.0, 0.25, 2.0])}


def _field(seed: int = 0) -> np.ndarray:
    generator = np.random.default_rng(seed)
    return generator.normal(size=(3, 3, 3)) + 1j * generator.normal(size=(3, 3, 3))


_AXIS_KEYS = ("x_m", "y_m", "z_m")


def _cell(axis_key: str, coordinate: float) -> int:
    """Index of the grid interval containing ``coordinate``."""
    grid = AXES[axis_key]
    index = int(np.searchsorted(grid, coordinate) - 1)
    return int(np.clip(index, 0, grid.size - 2))


def _oracle(values, point) -> complex:
    """Independent trilinear reference written as an explicit 8-corner sum.

    The enclosing cell on each axis is the single interval that contains the
    query coordinate, and the corner weights are the in-cell barycentric
    weights.  This is a different formulation from the shipped implementation,
    which delegates to a separable interpolator, so agreement is real evidence
    rather than a tautology.
    """
    cells = [_cell(key, coordinate) for key, coordinate in zip(_AXIS_KEYS, point)]
    total = 0.0 + 0.0j
    for i in range(2):
        for j in range(2):
            for k in range(2):
                weight = 1.0
                for axis_index, offset in enumerate((i, j, k)):
                    grid = AXES[_AXIS_KEYS[axis_index]]
                    cell = cells[axis_index]
                    lower, upper = grid[cell], grid[cell + 1]
                    fraction = (point[axis_index] - lower) / (upper - lower)
                    weight *= fraction if offset else (1.0 - fraction)
                total += weight * values[cells[0] + i, cells[1] + j, cells[2] + k]
    return total


def _tolerance() -> float:
    lower = np.array([AXES[key][0] for key in ("x_m", "y_m", "z_m")])
    upper = np.array([AXES[key][-1] for key in ("x_m", "y_m", "z_m")])
    return 32.0 * np.finfo(float).eps * float(np.max(np.maximum(1.0, np.abs(upper - lower))))


# --- Test U2-T01: in-box values reproduce an independent trilinear reference. --
def test_u2_t01_interior_points_match_independent_trilinear_reference():
    values = _field(0)
    points = np.array(
        [
            [0.25, -0.5, 0.125],
            [1.0, 0.5, 0.25],
            [1.75, 2.0, 1.5],
            [0.0, -1.0, 0.0],
            [2.0, 3.0, 2.0],
        ]
    )
    result = INTERPOLATE(AXES, values, points)
    assert result["valid_mask"].all()
    for index, point in enumerate(points):
        assert result["interpolated_values"][index] == pytest.approx(_oracle(values, point), rel=1e-13, abs=1e-13)


# --- Test U2-T02: dtype, key set, and array shape are part of the contract. ----
def test_u2_t02_result_dtype_keys_and_shapes():
    values = _field(1)
    result = INTERPOLATE(AXES, values, np.array([[1.0, 0.0, 1.0], [0.5, 0.0, 0.5]]))
    assert set(result) == {"interpolated_values", "valid_mask"}
    assert result["interpolated_values"].dtype == np.complex128
    assert result["interpolated_values"].shape == (2,)
    assert result["valid_mask"].dtype == np.bool_
    assert result["valid_mask"].shape == (2,)


# --- Test U2-T03: valid_mask is geometric containment in the tol-expanded box. -
def test_u2_t03_valid_mask_is_tolerance_expanded_geometric_containment():
    tolerance = _tolerance()
    values = _field(2)
    points = np.array(
        [
            [1.0, 0.0, 1.0],                       # strictly inside
            [2.0, 0.0, 1.0],                       # on the upper x face
            [0.0, 0.0, 1.0],                       # on the lower x face
            [1.0, 3.0 + tolerance, 1.0],           # exactly tol outside
            [1.0, 3.0 + 4.0 * tolerance, 1.0],     # outside tol
            [1.0, -1.0 - tolerance / 2.0, 1.0],    # inside tol, outside the box
            [1.0, 0.0, -tolerance / 2.0],          # inside tol on the lower z face
        ]
    )
    result = INTERPOLATE(AXES, values, points)
    lower = np.array([0.0, -1.0, 0.0])
    upper = np.array([2.0, 3.0, 2.0])
    expected = np.all((points >= lower - tolerance) & (points <= upper + tolerance), axis=1)
    np.testing.assert_array_equal(result["valid_mask"], expected)
    assert result["valid_mask"].tolist() == [True, True, True, True, False, True, True]


# --- Test U2-T04: finite source + valid_mask => finite value (the honest half). -
def test_u2_t04_finite_source_gives_finite_values_wherever_valid_mask_is_true():
    tolerance = _tolerance()
    values = _field(3)
    generator = np.random.default_rng(11)
    interior = generator.uniform(
        low=[0.0, -1.0, 0.0], high=[2.0, 3.0, 2.0], size=(64, 3)
    )
    straddling = np.array(
        [
            [1.0, 3.0 + tolerance / 2.0, 1.0],
            [1.0, -1.0 - tolerance / 2.0, 1.0],
            [2.0 + tolerance / 2.0, 0.0, 1.0],
            [1.0, 0.0, 2.0 + tolerance / 2.0],
            [1.0, 0.0, -tolerance / 2.0],
        ]
    )
    points = np.vstack([interior, straddling])
    result = INTERPOLATE(AXES, values, points)
    assert result["valid_mask"].all()
    assert np.all(np.isfinite(result["interpolated_values"]))


# --- Test U2-T05: tolerance-zone points are clamped onto the closed box. -------
def test_u2_t05_tolerance_zone_points_are_clamped_to_the_closed_box():
    tolerance = _tolerance()
    values = _field(4)
    outside_inside_tol = np.array(
        [
            [1.0, 3.0 + tolerance / 2.0, 1.0],
            [1.0, -1.0 - tolerance / 2.0, 1.0],
            [1.0, 0.0, -tolerance / 2.0],
        ]
    )
    on_face = np.array([[1.0, 3.0, 1.0], [1.0, -1.0, 1.0], [1.0, 0.0, 0.0]])
    clamped_result = INTERPOLATE(AXES, values, outside_inside_tol)
    face_result = INTERPOLATE(AXES, values, on_face)
    assert clamped_result["valid_mask"].all() and face_result["valid_mask"].all()
    np.testing.assert_allclose(
        clamped_result["interpolated_values"], face_result["interpolated_values"], rtol=0.0, atol=0.0
    )


# --- Test U2-T06: outside the expanded box => nan+nanj and valid_mask False. ---
def test_u2_t06_outside_expanded_box_returns_nan_pair_and_false_mask():
    tolerance = _tolerance()
    # Offsets are far enough beyond `tol` that the sum is representable; a bare
    # multiple of `tol` near 1.0 rounds away to the face and would not probe the
    # out-of-box path at all.
    outside = 1.0e6 * tolerance
    values = _field(5)
    points = np.array(
        [
            [1.0, 3.0 + outside, 1.0],
            [1.0, 0.0, -outside],
            [1.0, 0.0, 2.0 + outside],
            [1.0, 0.0, 1.0],
        ]
    )
    result = INTERPOLATE(AXES, values, points)
    assert result["valid_mask"].tolist() == [False, False, False, True]
    for index in (0, 1, 2):
        assert math.isnan(result["interpolated_values"][index].real)
        assert math.isnan(result["interpolated_values"][index].imag)
    assert np.isfinite(result["interpolated_values"][3])


# --- Test U2-T07: valid_mask does NOT imply a finite value (R3 counterexample). -
def test_u2_t07_nonfinite_source_propagates_while_valid_mask_stays_true():
    values = _field(6)
    # Both points are strictly interior to their cells: the poisoned node (0,0,0)
    # is a stencil corner for the first and outside the stencil of the second.
    # Interior points are used deliberately -- exactly-on-the-node coordinates
    # are decided by the interpolator's own tie-breaking and would test scipy
    # rather than this contract.
    depends = np.array([[0.25, -0.5, 0.125]])
    independent = np.array([[1.5, 2.0, 1.5]])
    assert values.shape == (3, 3, 3)

    poisoned_nan = values.copy()
    poisoned_nan[0, 0, 0] = np.nan + 0.0j
    nan_depends = INTERPOLATE(AXES, poisoned_nan, depends)
    nan_independent = INTERPOLATE(AXES, poisoned_nan, independent)
    assert nan_depends["valid_mask"].all() and nan_independent["valid_mask"].all()
    assert np.isnan(nan_depends["interpolated_values"][0].real)
    assert np.isfinite(nan_independent["interpolated_values"][0])

    poisoned_inf = values.copy()
    poisoned_inf[0, 0, 0] = np.inf + 0.0j
    # scipy emits this warning while multiplying the infinite node by a zero
    # weight.  The warning is the inf-to-nan propagation being demonstrated here,
    # so it is asserted rather than filtered: it is the only warning this unit
    # raises, and it must not be mistaken for an unexplained diagnostic.
    with pytest.warns(RuntimeWarning, match="invalid value encountered in multiply"):
        inf_depends = INTERPOLATE(AXES, poisoned_inf, depends)
    assert inf_depends["valid_mask"].all()
    assert not np.isfinite(inf_depends["interpolated_values"][0])

    # The mask still separates the in-box point from a genuinely out-of-box one.
    mixed = INTERPOLATE(AXES, poisoned_nan, np.array([[0.25, -0.5, 0.125], [1.0, 0.0, -1.0]]))
    assert mixed["valid_mask"].tolist() == [True, False]


# --- Test U2-T08: shape, dtype, and axis-order conformance. --------------------
def test_u2_t08_source_shape_dtype_and_axis_order_conformance():
    values = _field(7)
    points = np.array([[1.0, 0.0, 1.0]])
    # Leading shape must match (N_x, N_y, N_z) in that order.
    with pytest.raises(ValueError, match="leading shape"):
        INTERPOLATE(AXES, values[:2], points)
    # Axis identity: each axis key maps to its own positional axis.  Reversing
    # one axis array without permuting the values must change the answer.
    swapped_axes = {"x_m": AXES["x_m"], "y_m": AXES["y_m"], "z_m": AXES["z_m"][::-1]}
    with pytest.raises(ValueError, match="strictly increasing"):
        INTERPOLATE(swapped_axes, values, points)
    # The (x, y, z) index order is checked against a non-symmetric probe array
    # whose three axes have different lengths.
    probe_axes = {"x_m": AXES["x_m"], "y_m": AXES["y_m"], "z_m": np.array([0.0, 0.25, 2.0])}
    probe = np.zeros((3, 3, 3), dtype=complex)
    probe[1, 1, 1] = 7.0 + 3.0j
    probe[1, 1, 2] = -1.0 + 0.0j
    node = INTERPOLATE(probe_axes, probe, np.array([[1.0, 0.5, 0.25]]))
    assert node["interpolated_values"][0] == pytest.approx(7.0 + 3.0j)
    # Reading the same array through a permuted axis mapping must not reproduce it.
    permuted = INTERPOLATE(
        {"x_m": AXES["x_m"], "y_m": AXES["z_m"], "z_m": AXES["y_m"]}, probe, np.array([[1.0, 0.5, 0.25]])
    )
    assert permuted["interpolated_values"][0] != pytest.approx(7.0 + 3.0j)
    # Real input is accepted and promoted; higher-rank trailing axes are kept.
    real_values = values.real
    real_result = INTERPOLATE(AXES, real_values, points)
    assert real_result["interpolated_values"].dtype == np.complex128
    batched = np.stack([values, 2.0 * values], axis=-1)
    batched_result = INTERPOLATE(AXES, batched, points)
    assert batched_result["interpolated_values"].shape == (1, 2)
    np.testing.assert_allclose(
        batched_result["interpolated_values"][0, 1],
        2.0 * batched_result["interpolated_values"][0, 0],
        rtol=1e-13,
        atol=1e-13,
    )


# --- Test U2-T09: source axis validation is fail-closed. -----------------------
@pytest.mark.parametrize(
    "axes, message",
    [
        ({"x_m": [0.0, 1.0, 2.0], "y_m": [-1.0, 0.5, 3.0]}, "requires the z_m axis"),
        ({"x_m": [0.0, 1.0, 2.0], "y_m": [[-1.0, 0.5, 3.0]], "z_m": [0.0, 1.0, 2.0]}, "must be a 1-D array"),
        ({"x_m": [0.0], "y_m": [-1.0, 0.5, 3.0], "z_m": [0.0, 1.0, 2.0]}, "at least two points"),
        ({"x_m": [0.0, 1.0, 2.0], "y_m": [-1.0, 0.5, np.nan], "z_m": [0.0, 1.0, 2.0]}, "finite values"),
        ({"x_m": [0.0, 1.0, 2.0], "y_m": [-1.0, 0.5, 0.5], "z_m": [0.0, 1.0, 2.0]}, "strictly increasing"),
        ({"x_m": [0.0, 2.0, 1.0], "y_m": [-1.0, 0.5, 3.0], "z_m": [0.0, 1.0, 2.0]}, "strictly increasing"),
        (["x_m", "y_m", "z_m"], "must be a mapping"),
    ],
)
def test_u2_t09_source_axis_validation_is_fail_closed(axes, message):
    with pytest.raises(ValueError, match=message):
        INTERPOLATE(axes, _field(8), np.array([[1.0, 0.0, 1.0]]))


# --- Test U2-T10: target point validation is fail-closed. ---------------------
@pytest.mark.parametrize(
    "points",
    [
        np.array([1.0, 0.0, 1.0]),
        np.array([[1.0, 0.0]]),
        np.array([[1.0, 0.0, 1.0, 0.0]]),
        np.array([[1.0, 0.0, np.nan]]),
        np.array([[1.0, 0.0, np.inf]]),
    ],
)
def test_u2_t10_target_point_validation_is_fail_closed(points):
    with pytest.raises(ValueError, match=r"shape \(n_points, 3\)"):
        INTERPOLATE(AXES, _field(9), points)


# --- Test U2-T11: empty target sets are legal and shape-consistent. -----------
def test_u2_t11_empty_target_set_returns_empty_results():
    result = INTERPOLATE(AXES, _field(10), np.zeros((0, 3)))
    assert result["interpolated_values"].shape == (0,)
    assert result["valid_mask"].shape == (0,)


# --- Test U2-T12: the sibling real R-Z sampler is not reimplemented here. -----
def test_u2_t12_declared_sibling_relation_is_structural_not_a_duplicate():
    """The candidate must not import, shadow, or re-export the frozen real sampler."""
    source = _CANDIDATE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name == "scirel" or name.startswith("scirel.") for name in imported)
    assert not hasattr(MODULE, "sample_rectilinear_field")
    assert not hasattr(MODULE, "_axes")
    assert MODULE.__all__ == ["interpolate_complex_rectilinear_field"]
