"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/原子氢JH-r系数B样条评价``
sits in the re-review archive: KN1DPy's strict D1 qualification has been
withdrawn, so this replay is bounded historical development evidence about
the arithmetic, not qualified-L1 provenance and not expert approval.  The
tests are skipped unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle
root, and the saved implementation file is pinned by SHA-256 so a different
byte stream can never masquerade as the compared arm.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import evaluate_h_jh_r_coefficient

SOURCE_OPERATOR_SHA256 = "253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "原子氢JH-r系数B样条评价" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location("kn1dpy_jh_bscoef", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_r_branch_is_reproduced_exactly_on_the_packaged_payload():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    density = np.array([1.0e19, 5.0e19, 1.0e20, 2.0e21])
    temperature = np.array([1.0, 5.0, 20.0, 100.0])
    for ion in (0, 1):
        for level in (2, 3, 4, 5, 6):
            np.testing.assert_array_equal(
                evaluate_h_jh_r_coefficient(
                    density,
                    temperature,
                    ion,
                    level,
                    payload["DKnot"],
                    payload["TKnot"],
                    int(payload["order"]),
                    payload["LogR_BSCoef"],
                ),
                source.evaluate_h_jh_r_coefficient(
                    density,
                    temperature,
                    ion,
                    level,
                    payload["DKnot"],
                    payload["TKnot"],
                    int(payload["order"]),
                    payload["LogR_BSCoef"],
                ),
            )


def test_the_saved_r_branch_is_reproduced_exactly_on_a_synthetic_payload():
    source = _source_operator()
    from scipy.interpolate import RectBivariateSpline

    temperature_axis = np.linspace(-1.0, 1.0, 5)
    density_axis = np.linspace(30.0, 32.0, 5)
    surface = np.add.outer(temperature_axis, density_axis)
    spline = RectBivariateSpline(temperature_axis, density_axis, surface, kx=4, ky=4)
    temperature_knots, density_knots = spline.get_knots()
    coefficients = np.zeros((spline.get_coeffs().size, 2, 5), dtype=float)
    coefficients[:, 0, 1] = spline.get_coeffs()
    coefficients[:, 1, 4] = spline.get_coeffs() + 0.25
    density = np.array([1.0e10, np.exp(31.0), 1.0e20])
    temperature = np.array([np.exp(-2.0), np.exp(0.5), np.exp(2.0)])
    np.testing.assert_array_equal(
        evaluate_h_jh_r_coefficient(
            density, temperature, 0, 3, density_knots, temperature_knots, 4, coefficients
        ),
        source.evaluate_h_jh_r_coefficient(
            density, temperature, 0, 3, density_knots, temperature_knots, 4, coefficients
        ),
    )


def test_the_saved_density_overwrite_witness_is_reproduced_exactly():
    """The saved package's own witness: different densities, one output."""
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    arguments = (
        0,
        3,
        payload["DKnot"],
        payload["TKnot"],
        int(payload["order"]),
        payload["LogR_BSCoef"],
    )
    np.testing.assert_array_equal(
        evaluate_h_jh_r_coefficient(
            np.array([np.exp(30.0), 1.0e10]), np.array([np.exp(0.5), np.exp(0.5)]), *arguments
        ),
        evaluate_h_jh_r_coefficient(
            np.array([np.exp(32.0), 1.0e20]), np.array([np.exp(0.5), np.exp(0.5)]), *arguments
        ),
    )
    np.testing.assert_array_equal(
        source.evaluate_h_jh_r_coefficient(
            np.array([np.exp(30.0), 1.0e10]), np.array([np.exp(0.5), np.exp(0.5)]), *arguments
        ),
        source.evaluate_h_jh_r_coefficient(
            np.array([np.exp(32.0), 1.0e20]), np.array([np.exp(0.5), np.exp(0.5)]), *arguments
        ),
    )


def test_the_saved_rejection_behavior_agrees_exactly():
    source = _source_operator()
    payload = source.produce_jh_coefficient_payload()
    arguments = (
        np.array([np.exp(31.0)]),
        np.array([np.exp(0.5)]),
        0,
        3,
        payload["DKnot"],
        payload["TKnot"],
        int(payload["order"]),
        payload["LogR_BSCoef"],
    )
    for keyword_arguments in ({"no_null": 0}, {"principal_level": 1}, {"ion": 2}):
        passed = dict(zip(
            ("density_m3", "temperature_ev", "ion", "principal_level", "density_knots", "temperature_knots", "spline_order", "log_r_bscoef"),
            arguments,
        ))
        passed.update(keyword_arguments)
        with pytest.raises(ValueError):
            evaluate_h_jh_r_coefficient(**passed)
        with pytest.raises(ValueError):
            source.evaluate_h_jh_r_coefficient(**passed)
