"""Contract tests for SciRel's ordered equilibrium grid composition."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
from pathlib import Path

import numpy as np
import pytest

UNIT_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_MODULE = (
    Path(
        importlib.import_module("scirel.geometry.axisymmetric_equilibrium_grid_support").__file__
    ).resolve()
    if os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1"
    else (UNIT_ROOT / "src/scirel/geometry/axisymmetric_equilibrium_grid_support.py")
)
COMPOSITION_DOCUMENT = (
    UNIT_ROOT
    / "catalog"
    / "examples"
    / "scirel.geometry.axisymmetric-equilibrium-grid-support.json"
)


def _inputs(equilibrium, axes):
    eq = equilibrium()
    x_axis, y_axis, z_axis, pec = axes()
    return {
        "equilibrium": eq,
        "x_m": x_axis,
        "y_m": y_axis,
        "z_m": z_axis,
        "xpoint_half_length_m": 0.2,
        "pml_cells": 1,
        "pec_mask": pec,
    }


# --- Test U1-C-T01: the composition returns both relations' outputs. --------
def test_u1_c_t01_composition_returns_the_documented_outputs(
    candidate, equilibrium, axes, cylindrical
):
    inputs = _inputs(equilibrium, axes)
    result = candidate["composition"](inputs)
    mapping = candidate["mapping"](
        inputs["equilibrium"], inputs["x_m"], inputs["y_m"], inputs["z_m"]
    )
    radii, axial = cylindrical(inputs["x_m"], inputs["y_m"], inputs["z_m"])
    classification = candidate["classification"](
        mapping["poloidal_flux_wb_per_rad"],
        mapping["covered_mask"],
        radii,
        axial,
        separatrix_flux_wb_per_rad=inputs["equilibrium"]["separatrix_flux_wb_per_rad"],
        closed_flux_side=inputs["equilibrium"]["closed_flux_side"],
        xpoint_half_length_m=inputs["xpoint_half_length_m"],
        pml_cells=inputs["pml_cells"],
        pec_mask=inputs["pec_mask"],
    )
    expected_outputs = {**mapping, **classification}
    assert set(result) == set(expected_outputs)
    for name, expected in expected_outputs.items():
        actual = result[name]
        if isinstance(expected, np.ndarray):
            np.testing.assert_array_equal(actual, expected, err_msg=name)
        else:
            assert actual == expected, name
    assert result["material_support_mask"].sum() == 176
    assert result["magnetic_flux_density_t"].shape == (9, 9, 7, 3)
    assert result["covered_mask"].dtype == bool
    assert result["material_support_mask"].dtype == bool
    assert isinstance(result["radially_clamped_point_count"], int)
    assert isinstance(result["axially_clamped_point_count"], int)


# --- Test U1-C-T02: the composition binds exactly the two dependencies. -----
def test_u1_c_t02_composition_binds_exactly_the_two_dependencies(candidate, equilibrium, axes):
    inputs = _inputs(equilibrium, axes)
    calls = []
    shape = (2, 2, 2)
    sentinel_magnetic = np.zeros(shape + (3,))
    sentinel_flux = np.arange(8.0).reshape(shape)
    sentinel_covered = np.ones(shape, dtype=bool)
    sentinel_support = np.zeros(shape, dtype=bool)

    def fake_mapping(equilibrium_argument, x_m, y_m, z_m):
        calls.append(("mapping", equilibrium_argument, x_m, y_m, z_m))
        return {
            "magnetic_flux_density_t": sentinel_magnetic,
            "poloidal_flux_wb_per_rad": sentinel_flux,
            "covered_mask": sentinel_covered,
            "radially_clamped_point_count": 3,
            "axially_clamped_point_count": 4,
        }

    def fake_classification(*arguments, **keywords):
        calls.append(("classification", arguments, keywords))
        return {
            "material_support_mask": sentinel_support,
            "closed_flux_mask": sentinel_support,
            "axis_segment_mask": sentinel_support,
        }

    result = candidate["composition"](
        inputs,
        equilibrium_grid_mapping=fake_mapping,
        material_support_classification=fake_classification,
    )
    assert [name for name, *_ in calls] == ["mapping", "classification"]
    # The mapping dependency received the caller's own objects, unmodified.
    assert calls[0][1] is inputs["equilibrium"]
    assert calls[0][2] is inputs["x_m"]
    # The classification dependency received the mapping's own outputs.
    assert calls[1][1][0] is sentinel_flux
    assert calls[1][1][1] is sentinel_covered
    assert calls[1][2]["pml_cells"] == 1
    assert calls[1][2]["pec_mask"] is inputs["pec_mask"]
    assert calls[1][2]["xpoint_half_length_m"] == 0.2
    assert (
        calls[1][2]["separatrix_flux_wb_per_rad"]
        == inputs["equilibrium"]["separatrix_flux_wb_per_rad"]
    )
    assert calls[1][2]["closed_flux_side"] == inputs["equilibrium"]["closed_flux_side"]
    assert result["radially_clamped_point_count"] == 3
    assert result["axially_clamped_point_count"] == 4
    assert result["material_support_mask"] is sentinel_support

    with pytest.raises(ValueError, match="unexpected composition keyword"):
        candidate["composition"](inputs, not_a_dependency=fake_mapping)
    with pytest.raises(ValueError, match="missing required composition inputs"):
        candidate["composition"](
            {key: value for key, value in inputs.items() if key != "pml_cells"}
        )
    with pytest.raises(ValueError, match="inputs must be a mapping"):
        candidate["composition"](None)


# --- Test U1-C-T03: the composition is a pure ordered DAG. -----------------
def test_u1_c_t03_composition_is_a_pure_ordered_dag(candidate):
    source = COMPOSITION_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add((node.level, node.module or "", tuple(alias.name for alias in node.names)))
        elif isinstance(node, ast.Import):
            imported.add((0, "", tuple(alias.name for alias in node.names)))
    assert imported == {
        (0, "__future__", ("annotations",)),
        (0, "collections.abc", ("Mapping",)),
        (0, "", ("numpy",)),
        (1, "axisymmetric_grid_mapping", ("map_axisymmetric_equilibrium_to_cartesian_grid",)),
        (1, "material_support", ("classify_material_support",)),
    }, imported

    # No run-time dependence on a source checkout, a YAML file, or any file.
    for forbidden in ("open(", "yaml", "Path", "environ", "importlib", "asset_loader"):
        assert forbidden not in source, forbidden
    assert isinstance(
        inspect.signature(candidate["composition"]).parameters,
        type(inspect.signature(candidate["composition"]).parameters),
    )
    # The injected-dependency form is the documented SciRel composition convention:
    # every dependency is a keyword parameter with a default, and there is no
    # feedback parameter because the composition has no loop.
    composition_signature = inspect.signature(
        candidate["composition"].__globals__["run_composition"]
    )
    parameters = composition_signature.parameters
    assert list(parameters) == [
        "inputs",
        "equilibrium_grid_mapping",
        "material_support_classification",
    ]
    assert parameters["equilibrium_grid_mapping"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["equilibrium_grid_mapping"].default is candidate["mapping"]
    assert parameters["material_support_classification"].default is candidate["classification"]


# --- Test U1-C-T04: the declared dependency closure is exactly two assets. --
def test_u1_c_t04_declared_dependency_closure_is_exactly_two_assets(candidate):
    document = json.loads(COMPOSITION_DOCUMENT.read_text(encoding="utf-8"))
    declared = {entry["asset_id"] for entry in document["version"]["dependencies"]}
    assert declared == {
        "scirel.geometry.axisymmetric-equilibrium-grid-mapping",
        "scirel.geometry.material-support-classification",
    }
    bound = {
        node["asset_id"]
        for node in document["composition"]["nodes"]
        if node.get("asset_id") is not None
    }
    assert bound == declared
    # Every declared composition input is consumed, and every declared output produced.
    consumed = {
        edge["to"]["port"]
        for edge in document["composition"]["edges"]
        if edge["from"]["node"] == "$input"
    }
    assert consumed == {port["name"] for port in document["inputs"]}
    produced = {
        edge["to"]["port"]
        for edge in document["composition"]["edges"]
        if edge["to"]["node"] == "$output"
    }
    assert produced == {port["name"] for port in document["outputs"]}
    # The composition has no feedback edge and declares no feedback contract.
    assert document["composition"]["execution"]["feedback"] == []
    assert all(edge["kind"] != "feedback" for edge in document["composition"]["edges"])
    # Every node input is connected by an edge.
    for node in document["composition"]["nodes"]:
        connected = {
            edge["to"]["port"]
            for edge in document["composition"]["edges"]
            if edge["to"]["node"] == node["id"]
        }
        assert connected == set(node["inputs"]), node["id"]


# --- Test U1-C-T05: the classification parameters are forwarded verbatim. --
def test_u1_c_t05_classification_parameters_are_forwarded_verbatim(candidate, equilibrium, axes):
    inputs = _inputs(equilibrium, axes)
    less = candidate["composition"](inputs)
    inputs["equilibrium"]["closed_flux_side"] = "greater_than"
    inputs["equilibrium"]["separatrix_flux_wb_per_rad"] = 0.2
    greater = candidate["composition"](inputs)
    # The mapping outputs are unaffected by the classification parameters ...
    np.testing.assert_array_equal(
        less["poloidal_flux_wb_per_rad"], greater["poloidal_flux_wb_per_rad"]
    )
    np.testing.assert_array_equal(
        less["magnetic_flux_density_t"], greater["magnetic_flux_density_t"]
    )
    # ... and the support mask moves with them, so the parameters really reach
    # the classification relation.
    assert not np.array_equal(less["material_support_mask"], greater["material_support_mask"])
    assert not np.array_equal(less["closed_flux_mask"], greater["closed_flux_mask"])


# --- Test U1-C-T06: the coordinates are the composition's own glue. --------
def test_u1_c_t06_coordinates_are_the_composition_glue(candidate, equilibrium, axes, cylindrical):
    inputs = _inputs(equilibrium, axes)
    result = candidate["composition"](inputs)
    radii, axial = cylindrical(inputs["x_m"], inputs["y_m"], inputs["z_m"])
    assert radii.shape == (9, 9, 7)
    # The glue's coordinates reproduce the mapping's own coverage mask exactly,
    # so the two nodes agree about the solver box without sharing a code path.
    r_axis = np.asarray(inputs["equilibrium"]["r_m"], dtype=float)
    z_axis = np.asarray(inputs["equilibrium"]["z_m"], dtype=float)
    expected = (
        (radii >= r_axis[0]) & (radii <= r_axis[-1]) & (axial >= z_axis[0]) & (axial <= z_axis[-1])
    )
    np.testing.assert_array_equal(result["covered_mask"], expected)
    # A grid whose axes are not one-dimensional is rejected by the glue.
    with pytest.raises(ValueError, match="must be a 1D array"):
        candidate["composition"]({**inputs, "x_m": np.zeros((2, 2))})


def test_u1_c_t06_coordinate_glue_preserves_full_grid_values_without_mesh_copy(
    candidate,
):
    """Separable coordinates must match the historical full mesh exactly."""
    x_axis = np.array([-0.7, -0.1, 0.4, 1.2])
    y_axis = np.array([-0.5, 0.2, 0.9])
    z_axis = np.array([-0.3, 0.0, 0.6, 1.1, 1.8])
    radii, axial = candidate["composition"].__globals__["_cylindrical_coordinates"](
        x_axis, y_axis, z_axis
    )
    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    np.testing.assert_array_equal(radii, np.hypot(xx, yy))
    np.testing.assert_array_equal(axial, zz)
    assert radii.shape == (4, 3, 5)
    assert axial.shape == (4, 3, 5)
    assert radii.strides[2] == 0
    assert axial.strides[0] == 0 and axial.strides[1] == 0


# --- Test U1-C-T07: the public signature is the documented one. ------------
def test_u1_c_t07_public_signature_is_the_documented_one(candidate):
    document = json.loads(COMPOSITION_DOCUMENT.read_text(encoding="utf-8"))
    python_api = document["public_api"]["python"]
    function = candidate["composition"]
    assert f"{python_api['symbol']}{inspect.signature(function)}" == python_api["signature"]
    assert python_api["signature"] == (
        "solve_axisymmetric_equilibrium_grid_mapping(inputs=None, **kwargs)"
    )
    assert python_api["module"] == "scirel.geometry.axisymmetric_equilibrium_grid_support"
    assert "composition" in document
    assert document["asset_id"] == "scirel.geometry.axisymmetric-equilibrium-grid-support"
