"""Contract tests for the U1 material-support classification relation.

The discriminating questions for this asset are: does the classification produce
the declared support mask; is the zero-thickness PML frame rejected explicitly
instead of silently excluding the whole solver box; and is the innermost-radius
segment a live branch only when the equilibrium map reaches the grid's minimum
radius.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
from pathlib import Path

import numpy as np
import pytest

CLASSIFICATION_MODULE = (
    Path(importlib.import_module("scirel.geometry.material_support").__file__).resolve()
    if os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1"
    else (Path(__file__).resolve().parents[2] / "src/scirel/geometry/material_support.py")
)

_HALF_LENGTH = 0.2


def _interior(shape, thickness):
    """Independent reconstruction of the non-PML interior of the solver box."""
    interior = np.ones(shape, dtype=bool)
    for axis_index in range(3):
        for edge in (slice(0, thickness), slice(shape[axis_index] - thickness, shape[axis_index])):
            selector = [slice(None)] * 3
            selector[axis_index] = edge
            interior[tuple(selector)] = False
    return interior


def _classify(
    candidate,
    equilibrium,
    axes,
    cylindrical,
    *,
    side=None,
    separatrix=None,
    pml_cells=1,
    pec=None,
    r_start=0.05,
):
    eq = equilibrium(
        r_start=r_start,
        side="less_than" if side is None else side,
        separatrix=0.4 if separatrix is None else separatrix,
    )
    x_axis, y_axis, z_axis, default_pec = axes()
    radii, axial = cylindrical(x_axis, y_axis, z_axis)
    # Flux and coverage come from the maintained mapping relation; coordinates
    # are built independently here.
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    mask = candidate["classification"](
        result["poloidal_flux_wb_per_rad"],
        result["covered_mask"],
        radii,
        axial,
        separatrix_flux_wb_per_rad=eq["separatrix_flux_wb_per_rad"],
        closed_flux_side=eq["closed_flux_side"],
        xpoint_half_length_m=_HALF_LENGTH,
        pml_cells=pml_cells,
        pec_mask=default_pec if pec is None else pec,
    )
    return eq, result, radii, axial, mask, (x_axis, y_axis, z_axis)


# --- Test U1-B-T01: the closed-flux side selects the flux-surface side. -----
def test_u1_b_t01_closed_flux_side_selects_the_flux_surface_side(
    candidate, equilibrium, axes, cylindrical
):
    _, _, _, _, less, _ = _classify(candidate, equilibrium, axes, cylindrical, side="less_than")
    _, _, _, _, greater, _ = _classify(
        candidate, equilibrium, axes, cylindrical, side="greater_than", separatrix=0.4
    )
    # The two sides are disjoint and neither is empty on this map.
    assert less["closed_flux_mask"].sum() > 0
    assert greater["closed_flux_mask"].sum() > 0
    assert not np.any(less["closed_flux_mask"] & greater["closed_flux_mask"])
    # The side is a strict choice, not a relaxation: raising the separatrix flux
    # can only grow the less_than side.
    _, _, _, _, higher, _ = _classify(
        candidate, equilibrium, axes, cylindrical, side="less_than", separatrix=0.6
    )
    assert higher["closed_flux_mask"].sum() > less["closed_flux_mask"].sum()
    assert np.all(higher["closed_flux_mask"][less["closed_flux_mask"]])


# --- Test U1-B-T02: the PML frame is excluded on all six faces. -------------
@pytest.mark.parametrize("thickness", [1, 2])
def test_u1_b_t02_pml_frame_is_excluded_on_all_six_faces(
    candidate, equilibrium, axes, cylindrical, thickness
):
    _, result, radii, axial, mask, (x_axis, y_axis, z_axis) = _classify(
        candidate, equilibrium, axes, cylindrical, pml_cells=thickness
    )
    support = mask["material_support_mask"]
    for axis_index, size in enumerate(support.shape):
        for edge in (slice(0, thickness), slice(size - thickness, size)):
            selector = [slice(None)] * 3
            selector[axis_index] = edge
            assert not np.any(support[tuple(selector)]), (axis_index, edge)

    expected_interior = _interior(support.shape, thickness)
    np.testing.assert_array_equal(support, mask["closed_flux_mask"] & expected_interior)
    # The support is a strict subset of the interior, so the frame really bites.
    assert support.sum() < expected_interior.sum()
    assert radii.shape == support.shape and axial.shape == support.shape


# --- Test U1-B-T03: the PEC mask removes support. --------------------------
def test_u1_b_t03_pec_mask_removes_support(candidate, equilibrium, axes, cylindrical):
    x_axis, y_axis, z_axis, pec = axes()
    _, _, _, _, clean, _ = _classify(candidate, equilibrium, axes, cylindrical)
    assert clean["material_support_mask"][5, 5, 3]
    pec[5, 5, 3] = True
    _, _, _, _, masked, _ = _classify(candidate, equilibrium, axes, cylindrical, pec=pec)
    assert not masked["material_support_mask"][5, 5, 3]
    assert masked["material_support_mask"].sum() == clean["material_support_mask"].sum() - 1
    # The PEC mask is applied after the flux-surface classification, so the
    # closed-flux mask itself is unchanged.
    np.testing.assert_array_equal(masked["closed_flux_mask"], clean["closed_flux_mask"])


# --- Test U1-B-T04: a zero-thickness PML frame is rejected, not silent. ----
def test_u1_b_t04_zero_thickness_pml_frame_is_rejected_not_silent(
    candidate, equilibrium, axes, cylindrical
):
    with pytest.raises(ValueError, match="positive integer") as candidate_error:
        _classify(candidate, equilibrium, axes, cylindrical, pml_cells=0)
    assert "silently excluded the whole solver box" in str(candidate_error.value)
    assert "pml_cells" in str(candidate_error.value)


# --- Test U1-B-T05: the innermost-radius segment is a live branch. ----------
def test_u1_b_t05_innermost_radius_segment_is_a_live_branch(
    candidate, equilibrium, axes, cylindrical
):
    # When the equilibrium map starts above the grid's minimum radius, the
    # segment is intersected away by the coverage mask and can add nothing.
    _, _, _, _, inert, _ = _classify(candidate, equilibrium, axes, cylindrical, r_start=0.05)
    assert inert["axis_segment_mask"].sum() == 0

    # When the map reaches the grid's minimum radius and the closed-flux side
    # excludes the axis, the segment adds exactly the innermost-radius points
    # that lie within the poloidal half length.
    _, _, _, axial, live, (x_axis, y_axis, z_axis) = _classify(
        candidate, equilibrium, axes, cylindrical, r_start=0.0, side="greater_than", separatrix=0.5
    )
    segment = live["axis_segment_mask"]
    assert segment.sum() == 3
    axis_column = np.zeros_like(segment)
    axis_column[4, 4, :] = True
    expected = axis_column & (np.abs(axial) < _HALF_LENGTH)
    np.testing.assert_array_equal(segment, expected)
    # None of those points would be closed on this side, so the segment is what
    # puts them into the support mask.
    assert not np.any(live["closed_flux_mask"][segment])
    assert np.all(live["material_support_mask"][segment])
    # The segment lies inside the non-PML interior and is disjoint from the
    # closed-flux mask on this side, so the two contributions add exactly.
    interior = _interior(segment.shape, 1)
    assert np.all(interior[segment])
    np.testing.assert_array_equal(
        live["material_support_mask"], (live["closed_flux_mask"] | segment) & interior
    )
    assert live["material_support_mask"].sum() == (
        int(np.count_nonzero(live["closed_flux_mask"] & interior)) + int(segment.sum())
    )
    assert live["material_support_mask"].sum() > int(segment.sum())


# --- Test U1-B-T06: an empty support mask is an error that names the cause. -
def test_u1_b_t06_empty_support_mask_names_the_actual_cause(
    candidate, equilibrium, axes, cylindrical
):
    # A frame thicker than half the smallest grid extent leaves no interior.
    with pytest.raises(ValueError) as error:
        _classify(candidate, equilibrium, axes, cylindrical, pml_cells=5)
    message = str(error.value)
    assert "material support classification is empty" in message
    for cause in ("closed-flux side", "innermost-radius segment", "PML frame", "PEC mask"):
        assert cause in message, cause
    assert "machine equilibrium" not in message


# --- Test U1-B-T07: validation is fail-closed. -----------------------------
def test_u1_b_t07_validation_is_fail_closed(candidate, equilibrium, axes, cylindrical):
    eq, result, radii, axial, _, (x_axis, y_axis, z_axis) = _classify(
        candidate, equilibrium, axes, cylindrical
    )
    *_, pec = axes()
    flux = result["poloidal_flux_wb_per_rad"]
    covered = result["covered_mask"]
    base = dict(
        separatrix_flux_wb_per_rad=eq["separatrix_flux_wb_per_rad"],
        closed_flux_side=eq["closed_flux_side"],
        xpoint_half_length_m=_HALF_LENGTH,
        pml_cells=1,
        pec_mask=pec,
    )
    cases = [
        (
            (flux, covered, radii, axial),
            {**base, "closed_flux_side": "sideways"},
            "less_than or greater_than",
        ),
        ((flux[..., None], covered, radii, axial), base, "must be a 3D array"),
        ((flux, covered[:-1], radii, axial), base, "covered_mask must match"),
        ((flux, covered, radii[:-1], axial), base, "radii_m must match"),
        ((flux, covered, radii, axial[:-1]), base, "axial_coordinate_m must match"),
        ((flux, covered, radii * np.nan, axial), base, "radii_m must be finite"),
        ((flux, covered, -radii, axial), base, "non-negative"),
        (
            (flux, covered, radii, axial),
            {**base, "separatrix_flux_wb_per_rad": np.nan},
            "must be finite",
        ),
        ((flux, covered, radii, axial), {**base, "xpoint_half_length_m": 0.0}, "strictly positive"),
        ((flux, covered, radii, axial), {**base, "xpoint_half_length_m": np.inf}, "must be finite"),
        ((flux, covered, radii, axial), {**base, "pml_cells": -1}, "positive integer"),
        ((flux, covered, radii, axial), {**base, "pml_cells": 1.5}, "positive integer"),
        ((flux, covered, radii, axial), {**base, "pml_cells": "2"}, "positive integer"),
        ((flux, covered, radii, axial), {**base, "pml_cells": True}, "positive integer"),
        ((flux, covered, radii, axial), {**base, "pec_mask": pec[:-1]}, "pec_mask must match"),
        ((np.full_like(flux, np.nan), covered, radii, axial), base, "must be finite"),
    ]
    for arguments, keywords, message in cases:
        with pytest.raises(ValueError, match=message):
            candidate["classification"](*arguments, **keywords)


# --- Test U1-B-T09: the classification relation is free of map arrays. ------
def test_u1_b_t09_classification_relation_is_free_of_map_arrays(candidate):
    source = CLASSIFICATION_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported == {"__future__"}, imported
    # The docstring may name the mapping relation; the executable body may not
    # depend on it, so the search runs over the body only.
    body = source.replace(candidate["classification_module"].__doc__, "")
    assert body != source
    assert "axisymmetric_grid_mapping" not in body
    assert "equilibrium" not in body
    assert "interp" not in body
    signature = inspect.signature(candidate["classification"])
    assert (
        f"classify_material_support{signature}"
        == "classify_material_support(poloidal_flux_wb_per_rad, covered_mask, radii_m, "
        "axial_coordinate_m, *, separatrix_flux_wb_per_rad, closed_flux_side, "
        "xpoint_half_length_m, pml_cells, pec_mask)"
    )
    assert candidate["classification_module"].__all__ == [
        "ALLOWED_CLOSED_FLUX_SIDES",
        "classify_material_support",
    ]
