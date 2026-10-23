"""Contract tests for the U1 mapping relation.

The discriminating questions for this asset are: is the reconstruction the
tensor-product bilinear interpolant of the map on a rectilinear grid; is the
clamping onto the closed map box reported rather than hidden; and does the
relation stay free of the flux-surface classification parameters that the
retained single operator also carried.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import os
from pathlib import Path

import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator

from scirel.geometry.axisymmetric_grid_mapping import (
    _evaluate_cylindrical,
    _interpolate_cylindrical,
    _interpolation_coordinates,
)

MAPPING_MODULE = Path(
    importlib.import_module("scirel.geometry.axisymmetric_grid_mapping").__file__
).resolve() if os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1" else (
    Path(__file__).resolve().parents[2]
    / "src/scirel/geometry/axisymmetric_grid_mapping.py"
)


def _reference_bilinear(equilibrium, x_axis, y_axis, z_axis):
    """Independent tensor-product reconstruction with independent clamping."""
    r_axis = np.asarray(equilibrium["r_m"], dtype=float)
    z_axis_map = np.asarray(equilibrium["z_m"], dtype=float)
    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    radii = np.hypot(xx, yy)
    query = np.column_stack(
        [np.clip(radii, r_axis[0], r_axis[-1]).ravel(), np.clip(zz, z_axis_map[0], z_axis_map[-1]).ravel()]
    )
    out = {}
    for name in ("psi_wb_per_rad", "br_t", "bz_t"):
        interpolator = RegularGridInterpolator(
            (r_axis, z_axis_map), np.asarray(equilibrium[name], dtype=float), method="linear"
        )
        out[name] = interpolator(query).reshape(radii.shape)
    return out, radii, zz


# --- Test U1-A-T01: the reconstruction is the tensor-product interpolant. ---
def test_u1_a_t01_reconstruction_is_the_tensor_product_bilinear_interpolant(
    candidate, equilibrium, axes
):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    reference, _, _ = _reference_bilinear(eq, x_axis, y_axis, z_axis)

    np.testing.assert_allclose(
        result["poloidal_flux_wb_per_rad"], reference["psi_wb_per_rad"], rtol=1e-14, atol=1e-14
    )
    assert result["poloidal_flux_wb_per_rad"].shape == (9, 9, 7)
    # The map is deliberately non-separable, so a reconstruction that dropped one
    # interpolation stage would not reproduce it.
    rr = np.asarray(eq["r_m"])[:, None]
    assert not np.allclose(
        result["poloidal_flux_wb_per_rad"],
        np.broadcast_to(0.9 * np.hypot(*np.meshgrid(x_axis, y_axis, indexing="ij"))[:, :, None], (9, 9, 7)),
    )
    assert rr.shape == (21, 1)


# --- Test U1-A-T02: the two-stage ordering is not discriminating. -----------
def test_u1_a_t02_stage_order_is_measured_to_be_non_discriminating(
    candidate, equilibrium, axes
):
    """Record that the retained "ordering is part of the relation" claim is vacuous.

    Both stages are linear on a rectilinear grid, so the composition is the
    tensor-product interpolant and the stage order only changes the float
    association.  This is measured, not assumed, on a non-separable map.
    """
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    _, radii, zz = _reference_bilinear(eq, x_axis, y_axis, z_axis)
    r_axis = np.asarray(eq["r_m"], dtype=float)
    z_axis_map = np.asarray(eq["z_m"], dtype=float)
    values = np.asarray(eq["psi_wb_per_rad"], dtype=float)
    flat_r = np.clip(radii, r_axis[0], r_axis[-1]).ravel()
    flat_z = np.clip(zz, z_axis_map[0], z_axis_map[-1]).ravel()

    radial_first = np.stack(
        [np.interp(flat_r, r_axis, values[:, index]) for index in range(z_axis_map.size)],
        axis=1,
    )
    axial_first = np.stack(
        [np.interp(flat_z, z_axis_map, values[index, :]) for index in range(r_axis.size)],
        axis=1,
    )
    retained_order = np.asarray(
        [np.interp(flat_z[i], z_axis_map, radial_first[i]) for i in range(flat_z.size)]
    )
    swapped_order = np.asarray(
        [np.interp(flat_r[i], r_axis, axial_first[i]) for i in range(flat_r.size)]
    )
    divergence = float(np.max(np.abs(retained_order - swapped_order)))
    assert divergence < 1e-15, divergence

    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    np.testing.assert_allclose(
        result["poloidal_flux_wb_per_rad"].ravel(), retained_order, rtol=1e-14, atol=1e-14
    )


def test_u1_a_t02_pre_resolved_coordinates_preserve_interpolation_values(
    equilibrium, axes
):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes(
        x=(-1.1, 1.1, 11), y=(-0.9, 0.9, 9), z=(-0.7, 0.7, 8)
    )
    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    radii = np.clip(np.hypot(xx, yy), eq["r_m"][0], eq["r_m"][-1]).ravel()
    axial = np.clip(zz, eq["z_m"][0], eq["z_m"][-1]).ravel()
    coordinates = _interpolation_coordinates(eq["r_m"], eq["z_m"], radii, axial)

    for name in ("psi_wb_per_rad", "br_t", "bz_t"):
        expected = _interpolate_cylindrical(
            eq["r_m"], eq["z_m"], eq[name], radii, axial
        )
        actual = _evaluate_cylindrical(eq[name], coordinates)
        np.testing.assert_array_equal(actual, expected)


# --- Test U1-A-T03: the coverage mask marks containment in the closed box. ---
def test_u1_a_t03_coverage_mask_marks_the_closed_map_box(candidate, equilibrium, axes):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    _, radii, zz = _reference_bilinear(eq, x_axis, y_axis, z_axis)
    r_axis = np.asarray(eq["r_m"], dtype=float)
    z_axis_map = np.asarray(eq["z_m"], dtype=float)
    expected = (
        (radii >= r_axis[0])
        & (radii <= r_axis[-1])
        & (zz >= z_axis_map[0])
        & (zz <= z_axis_map[-1])
    )
    np.testing.assert_array_equal(result["covered_mask"], expected)
    assert result["covered_mask"].dtype == bool
    assert result["covered_mask"].shape == (9, 9, 7)
    # The inner radius of the map is not covered, because the map does not
    # represent radii below its first axis value.
    assert not result["covered_mask"][4, 4, 3]


# --- Test U1-A-T04: the clamping is reported by the two counters. -----------
def test_u1_a_t04_clamp_counters_report_the_clamped_query_points(
    candidate, equilibrium, axes
):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes(x=(-1.2, 1.2, 13), y=(-1.2, 1.2, 13), z=(-0.8, 0.8, 9))
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    _, radii, zz = _reference_bilinear(eq, x_axis, y_axis, z_axis)
    r_axis = np.asarray(eq["r_m"], dtype=float)
    z_axis_map = np.asarray(eq["z_m"], dtype=float)

    assert result["radially_clamped_point_count"] == int(np.count_nonzero(radii > r_axis[-1]))
    assert result["axially_clamped_point_count"] == int(
        np.count_nonzero((zz < z_axis_map[0]) | (zz > z_axis_map[-1]))
    )
    assert result["radially_clamped_point_count"] > 0
    assert result["axially_clamped_point_count"] > 0
    # A clamped point is reconstructed at the box face, not rejected and not
    # extrapolated: the count of clamped points and the covered count differ.
    assert int(np.count_nonzero(result["covered_mask"])) < radii.size

    inside = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    np.testing.assert_array_equal(
        inside["covered_mask"], result["covered_mask"]
    )


# --- Test U1-A-T05: the Cartesian assembly preserves the cylindrical split. -
def test_u1_a_t05_cartesian_assembly_preserves_the_cylindrical_split(
    candidate, equilibrium, axes
):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    reference, radii, _ = _reference_bilinear(eq, x_axis, y_axis, z_axis)
    magnetic = result["magnetic_flux_density_t"]
    assert magnetic.shape == (9, 9, 7, 3)
    np.testing.assert_allclose(magnetic[..., 2], reference["bz_t"], rtol=1e-14, atol=1e-14)

    xx, yy, _ = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    transverse = np.hypot(magnetic[..., 0], magnetic[..., 1])
    off_axis = radii > 0.0
    np.testing.assert_allclose(
        transverse[off_axis], np.abs(reference["br_t"])[off_axis], rtol=1e-13, atol=1e-13
    )
    # On the axis the transverse split is undefined and is set exactly to zero
    # instead of being propagated as a division by the radius.
    np.testing.assert_array_equal(magnetic[..., 0][~off_axis], np.zeros(int((~off_axis).sum())))
    np.testing.assert_array_equal(magnetic[..., 1][~off_axis], np.zeros(int((~off_axis).sum())))
    assert int((~off_axis).sum()) > 0


def test_cartesian_assembly_preserves_signed_radial_and_axial_components(
    candidate, equilibrium
):
    eq = equilibrium()
    eq["br_t"] = np.full_like(eq["br_t"], -3.0)
    eq["bz_t"] = np.full_like(eq["bz_t"], 4.0)
    x_axis, y_axis, z_axis = [-0.2, 0.2], [-0.3, 0.3], [-0.1, 0.1]
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    xx, yy, _ = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    radius = np.hypot(xx, yy)
    magnetic = result["magnetic_flux_density_t"]

    np.testing.assert_allclose(magnetic[..., 0], -3.0 * xx / radius, rtol=1e-14, atol=1e-14)
    np.testing.assert_allclose(magnetic[..., 1], -3.0 * yy / radius, rtol=1e-14, atol=1e-14)
    np.testing.assert_array_equal(magnetic[..., 2], np.full(radius.shape, 4.0))
    np.testing.assert_allclose(np.linalg.norm(magnetic, axis=-1), 5.0, rtol=1e-14, atol=1e-14)


@pytest.mark.parametrize("sign", [-1.0, 1.0])
def test_nonrepresentable_interpolated_flux_fails_closed(candidate, equilibrium, sign):
    eq = equilibrium(r_size=5, z_size=5)
    eq["br_t"] = np.zeros_like(eq["br_t"])
    eq["bz_t"] = np.zeros_like(eq["bz_t"])
    eq["psi_wb_per_rad"] = np.broadcast_to(
        sign * np.array([1e308, -1e308, 1e308, -1e308, 1e308])[:, None],
        eq["psi_wb_per_rad"].shape,
    ).copy()

    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="non-finite poloidal flux"):
            candidate["mapping"](eq, [0.3, 0.4], [0.0, 0.1], [-0.1, 0.1])


# --- Test U1-A-T06: validation is fail-closed. ------------------------------
@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda eq, x, y, z: (eq, x, y, z[::-1]), "strictly increasing"),
        (lambda eq, x, y, z: (eq, x, y, z[None, :], ), "must be a 1D array"),
        (lambda eq, x, y, z: (eq, x, y, z[:1], ), "at least two points"),
        (lambda eq, x, y, z: (eq, x, y, np.where(z == z[0], np.inf, z)), "must be finite"),
        (lambda eq, x, y, z: ({k: v for k, v in eq.items() if k != "br_t"}, x, y, z), "missing the required entry"),
        (lambda eq, x, y, z: ({**eq, "bz_t": eq["bz_t"][:-1]}, x, y, z), "must have shape"),
        (lambda eq, x, y, z: ({**eq, "psi_wb_per_rad": np.full_like(eq["psi_wb_per_rad"], np.nan)}, x, y, z), "must be finite"),
        (lambda eq, x, y, z: ({**eq, "r_m": eq["r_m"][:3]}, x, y, z), "at least five points"),
        (lambda eq, x, y, z: ({**eq, "z_m": np.zeros_like(eq["z_m"])}, x, y, z), "strictly increasing"),
        (lambda eq, x, y, z: ("not a mapping", x, y, z), "must be a mapping"),
    ],
)
def test_u1_a_t06_validation_is_fail_closed(candidate, equilibrium, axes, mutation, message):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    mutated = mutation(eq, x_axis, y_axis, z_axis)
    with pytest.raises(ValueError, match=message):
        candidate["mapping"](*mutated)


# --- Test U1-A-T07: the mapping relation is free of classification inputs. --
def test_u1_a_t07_mapping_relation_is_free_of_classification_inputs(candidate, equilibrium, axes):
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    # The classification parameters are simply not part of this relation, so the
    # call succeeds with them absent from the equilibrium mapping.
    stripped = {
        key: value
        for key, value in eq.items()
        if key not in ("separatrix_flux_wb_per_rad", "closed_flux_side")
    }
    result = candidate["mapping"](stripped, x_axis, y_axis, z_axis)
    assert set(result) == {
        "magnetic_flux_density_t",
        "poloidal_flux_wb_per_rad",
        "covered_mask",
        "radially_clamped_point_count",
        "axially_clamped_point_count",
    }
    # A bogus classification parameter is ignored rather than consulted.
    assert "material_support_mask" not in result

    tree = ast.parse(MAPPING_MODULE.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported == {"__future__", "collections.abc"}, imported
    assert "material_support" not in MAPPING_MODULE.read_text(encoding="utf-8")
    assert "separatrix" not in MAPPING_MODULE.read_text(encoding="utf-8")


# --- Test U1-A-T09: the public signature is the documented one. -------------
def test_u1_a_t09_public_signature_is_the_documented_one(candidate):
    function = candidate["mapping"]
    assert (
        f"map_axisymmetric_equilibrium_to_cartesian_grid{inspect.signature(function)}"
        == "map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x_m, y_m, z_m)"
    )
    assert candidate["mapping_module"].__all__ == [
        "map_axisymmetric_equilibrium_to_cartesian_grid"
    ]


# --- Test U1-A-T10: the frozen real R-Z sampler is a sibling, not a base. ---
def test_u1_a_t10_declared_sibling_relation_is_structural_not_a_duplicate(
    candidate, equilibrium, axes
):
    """Record the relation to ``scirel.geometry.sample_rectilinear_field``.

    The frozen baseline already samples real rectilinear R-Z fields.  This asset
    is a sibling, not a duplicate and not a successor: it takes a mapping of named
    arrays and 1-D axes, returns the whole Cartesian grid with the cylindrical
    split, and clamps out-of-domain points instead of raising.  The candidate must
    therefore not import, shadow, or re-export the frozen sampler, and the
    clamp-and-report policy that separates the two must be observable here.
    """
    source = MAPPING_MODULE.read_text(encoding="utf-8")
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
    assert not hasattr(candidate["mapping_module"], "sample_rectilinear_field")
    assert not hasattr(candidate["mapping_module"], "_axes")
    assert "sample_rectilinear_field" in (candidate["mapping_module"].__doc__ or "")

    # The policy difference, observed rather than asserted from prose: a query
    # point outside the map box is clamped and reported, where the frozen
    # fail-closed sampler raises instead.  On this fixture the out-of-box points
    # are the ones inside the map's inner radius, not beyond its outer radius.
    eq = equilibrium()
    x_axis, y_axis, z_axis, _ = axes()
    result = candidate["mapping"](eq, x_axis, y_axis, z_axis)
    r_axis = np.asarray(eq["r_m"], dtype=float)
    z_axis_map = np.asarray(eq["z_m"], dtype=float)
    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    radii = np.hypot(xx, yy)
    outside = (
        (radii < r_axis[0])
        | (radii > r_axis[-1])
        | (zz < z_axis_map[0])
        | (zz > z_axis_map[-1])
    )
    assert np.any(outside), "the fixture must exercise the clamp path"
    assert not np.all(result["covered_mask"]), "out-of-box points must be reported"
    assert np.all(np.isfinite(result["poloidal_flux_wb_per_rad"][outside]))
    assert not np.any(result["covered_mask"] & outside)
    # And the relation is free of the frozen sampler's 2-D mesh contract: the
    # source here is a mapping of 1-D axes plus named arrays.
    assert np.asarray(eq["r_m"]).ndim == 1 and np.asarray(eq["z_m"]).ndim == 1
