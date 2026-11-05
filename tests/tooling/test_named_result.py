"""The named result keeps mapping behaviour and adds attribute access."""

import numpy as np
import pytest

from scirel._result import Result
from scirel import diagnostics
from scirel.field import compute_poloidal_field_magnitude
from scirel.kinetic import evaluate_plasma_dispersion


_SYNTHESIS_R, _SYNTHESIS_Z = np.meshgrid([0.0, 1.0, 2.0], [-1.0, 0.0, 1.0])


def _synthesis_flux_kwargs(points):
    return {
        "R": _SYNTHESIS_R,
        "Z": _SYNTHESIS_Z,
        "equilibrium": {"psi": _SYNTHESIS_R**2, "psi_unit": "Wb/rad"},
        "observations": {
            "flux_loops": {
                "points": points,
                "quantity": "magnetic_flux",
                "unit": "Wb",
            }
        },
    }


def _synthesis_thomson_kwargs():
    return {
        "R": _SYNTHESIS_R,
        "Z": _SYNTHESIS_Z,
        "equilibrium": {
            "profiles": {
                "p_parallel": 10.0 + _SYNTHESIS_R + _SYNTHESIS_Z,
                "p_perp": 20.0 + 2.0 * _SYNTHESIS_R + _SYNTHESIS_Z,
                "density": 3.0 + _SYNTHESIS_R,
                "electron_temperature": 4.0 + _SYNTHESIS_Z,
            },
            "profile_units": {
                "density": "m^-3",
                "electron_temperature": "eV",
                "p_parallel": "Pa",
                "p_perp": "Pa",
            },
        },
        "observations": {
            "thomson": {
                "points": [[0.5, 0.5]],
                "density": {"unit": "m^-3"},
                "electron_temperature": {"unit": "eV"},
                "p_parallel": {"unit": "Pa"},
                "p_perp": {"unit": "Pa"},
            }
        },
    }


# Expected values were captured from baseline 0f74255b before the five remaining
# plain-dict diagnostics returns were wrapped in Result.
DIAGNOSTICS_CASES = [
    (
        "compute_picard_flux_residual",
        (np.array([[3.0, 4.0]]), np.array([[6.0, 8.0]])),
        {},
        {"residual": 1.0},
        "picard-nonzero",
    ),
    (
        "compute_picard_flux_residual",
        (np.zeros((1, 2)), np.zeros((1, 2))),
        {},
        {"residual": 0.0},
        "picard-zero",
    ),
    (
        "compute_firehose_mirror_margins",
        (1.0, 2.0, 1.0),
        {
            "mu0": 1.0,
            "dp_perp_dB": -4.0,
            "parallel_equilibrium": {"error": 0.25, "max_relative_error": 0.125},
        },
        {
            "firehose_margin": np.asarray(2.0, dtype=np.float64),
            "mirror_margin": np.asarray(-3.0, dtype=np.float64),
            "firehose_stable": True,
            "mirror_stable": False,
            "min_firehose_margin": 2.0,
            "min_mirror_margin": -3.0,
            "parallel_equilibrium_error": 0.25,
            "max_parallel_equilibrium_error": 0.125,
            "dp_perp_dB": np.asarray(-4.0, dtype=np.float64),
            "derivative_method": "explicit_fixed_flux_derivative",
            "criterion": "local_gyrotropic_tension_and_fixed_flux_total_pressure_slope",
        },
        "firehose-mirror",
    ),
    (
        "compute_firehose_mirror_margins",
        (np.asarray([3.0, 6.0, 11.0]), np.asarray([1.0, 4.0, 9.0]), [1.0, 2.0, 3.0]),
        {"mu0": 1.0, "field_axis": 0, "psi": 0.0},
        {
            "firehose_margin": np.asarray([-1.0, 2.0, 7.0], dtype=np.float64),
            "mirror_margin": np.asarray([3.0, 12.0, 27.0], dtype=np.float64),
            "firehose_stable": False,
            "mirror_stable": True,
            "min_firehose_margin": -1.0,
            "min_mirror_margin": 3.0,
            "parallel_equilibrium_error": None,
            "max_parallel_equilibrium_error": None,
            "dp_perp_dB": np.asarray([2.0, 4.0, 6.0], dtype=np.float64),
            "derivative_method": "declared_fixed_flux_axis_finite_difference",
            "criterion": "local_gyrotropic_tension_and_fixed_flux_total_pressure_slope",
        },
        "firehose-mirror-sampled-derivative",
    ),
    (
        "compute_parallel_pressure_residual",
        (np.asarray([1.0, 4.0, 9.0]), np.asarray([-1.0, -4.0, -9.0]), [1.0, 2.0, 3.0]),
        {"dp_parallel_dB": np.asarray([2.0, 4.0, 6.0])},
        {
            "rhs": np.asarray([-1.0, -4.0, -9.0], dtype=np.float64),
            "error": np.asarray([0.0, 0.0, 0.0], dtype=np.float64),
            "relative_error": np.asarray([0.0, 0.0, 0.0], dtype=np.float64),
            "max_relative_error": 0.0,
            "mean_relative_error": 0.0,
            "passed": True,
            "dp_parallel_dB": np.asarray([2.0, 4.0, 6.0], dtype=np.float64),
            "derivative_method": "explicit_fixed_flux_derivative",
        },
        "parallel-pressure-explicit-derivative",
    ),
    (
        "compute_parallel_pressure_residual",
        (np.asarray([1.0, 4.0, 9.0]), np.asarray([-1.0, -4.0, -9.0]), [1.0, 2.0, 3.0]),
        {"field_axis": 0, "psi": 0.0},
        {
            "rhs": np.asarray([-1.0, -4.0, -9.0], dtype=np.float64),
            "error": np.asarray([0.0, 0.0, 0.0], dtype=np.float64),
            "relative_error": np.asarray([0.0, 0.0, 0.0], dtype=np.float64),
            "max_relative_error": 0.0,
            "mean_relative_error": 0.0,
            "passed": True,
            "dp_parallel_dB": np.asarray([2.0, 4.0, 6.0], dtype=np.float64),
            "derivative_method": "declared_fixed_flux_axis_finite_difference",
        },
        "parallel-pressure-sampled-derivative",
    ),
    (
        "reduce_observation_residuals",
        (),
        {
            "predicted": {"flux_loops": [3.0], "thomson": {"p_perp": [5.0]}},
            "observations": {
                "flux_loops": {"values": [1.0], "sigma": [2.0]},
                "thomson": {"p_perp": {"values": [3.0], "sigma": [1.0]}},
            },
        },
        {
            "residual_vector": np.asarray([1.0, 2.0], dtype=np.float64),
            "chi2": 5.0,
        },
        "observation-residuals",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _synthesis_flux_kwargs([[1.0, 0.0]]),
        {
            "flux_loops": np.asarray([2.0 * np.pi], dtype=np.float64),
            "units": {"flux_loops": "Wb"},
        },
        "equilibrium-synthesis",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _synthesis_thomson_kwargs(),
        {
            "thomson": {
                "density": np.asarray([3.5], dtype=np.float64),
                "electron_temperature": np.asarray([4.5], dtype=np.float64),
                "p_parallel": np.asarray([11.0], dtype=np.float64),
                "p_perp": np.asarray([21.5], dtype=np.float64),
            },
            "units": {
                "thomson": {
                    "density": "m^-3",
                    "electron_temperature": "eV",
                    "p_parallel": "Pa",
                    "p_perp": "Pa",
                }
            },
        },
        "equilibrium-synthesis-thomson",
    ),
    (
        "compute_pointwise_firehose_margin",
        (1.0e100, 1.0e100, 1.0),
        {"mu0": 1.0},
        {"firehose_margin": np.asarray(1.0, dtype=np.float64)},
        "pointwise-firehose",
    ),
    (
        "compute_species_absorption_fraction",
        ([1.0, 2.0, 3.0, 4.0],),
        {},
        {
            "total_power": 10.0,
            "species_fraction_percent": np.asarray([10.0, 20.0, 30.0, 40.0], dtype=np.float64),
            "total_fraction_percent": 100.0,
            "fraction_sum_residual_percent": 0.0,
            "branch": "nonzero_total",
        },
        "species-absorption",
    ),
]


_SYNTHESIS_MISSING_R = _synthesis_flux_kwargs([[1.0, 0.0]])
_SYNTHESIS_MISSING_R.pop("R")
_SYNTHESIS_SHAPE_MISMATCH = _synthesis_flux_kwargs([[1.0, 0.0]])
_SYNTHESIS_SHAPE_MISMATCH["Z"] = _SYNTHESIS_Z[:, :2]


# Failure types and messages are copied from baseline 0f74255b. They are not
# obtained by calling the migrated implementation to describe its own errors.
DIAGNOSTICS_FAILURE_CASES = [
    (
        "compute_picard_flux_residual",
        ([[1.0, 2.0]], [[1.0], [2.0]]),
        {},
        ValueError,
        "psi_previous and psi_next must be same-shape two-dimensional [Z,R] arrays",
        "picard-shape",
    ),
    (
        "compute_picard_flux_residual",
        ([[1.0]], [[np.nan]]),
        {},
        ValueError,
        "psi_previous and psi_next must contain only finite values",
        "picard-nonfinite",
    ),
    (
        "compute_picard_flux_residual",
        ([[0.0]], [[1.0e308]]),
        {},
        ValueError,
        "relative residual exceeds the finite floating-point range",
        "picard-unrepresentable",
    ),
    (
        "compute_parallel_pressure_residual",
        ([1.0, 2.0], [1.0], [1.0, 2.0]),
        {"dp_parallel_dB": 0.0},
        ValueError,
        "p_parallel, p_perp, and magnetic_field must have the same shape",
        "parallel-shape",
    ),
    (
        "compute_parallel_pressure_residual",
        ([1.0], [np.nan], [1.0]),
        {"dp_parallel_dB": 0.0},
        ValueError,
        "pressures must be finite",
        "parallel-nonfinite",
    ),
    (
        "compute_parallel_pressure_residual",
        ([1.0], [2.0], [1.0]),
        {"dp_parallel_dB": 0.0, "strict": True},
        ValueError,
        "parallel equilibrium check failed",
        "parallel-strict",
    ),
    (
        "compute_parallel_pressure_residual",
        ([1.0], [0.0], [1.0]),
        {},
        ValueError,
        "a fixed-flux derivative or field_axis plus fixed psi samples is required",
        "parallel-missing-derivative",
    ),
    (
        "compute_firehose_mirror_margins",
        ([1.0, 2.0], [1.0], [1.0, 2.0]),
        {"dp_perp_dB": 0.0},
        ValueError,
        "p_parallel, p_perp, and magnetic_field must have the same shape",
        "firehose-shape",
    ),
    (
        "compute_firehose_mirror_margins",
        ([np.nan], [1.0], [1.0]),
        {"dp_perp_dB": 0.0},
        ValueError,
        "parallel pressure must be finite",
        "firehose-nonfinite",
    ),
    (
        "compute_firehose_mirror_margins",
        ([1.0], [2.0], [1.0]),
        {},
        ValueError,
        "a fixed-flux derivative or field_axis plus fixed psi samples is required",
        "firehose-missing-derivative",
    ),
    (
        "compute_firehose_mirror_margins",
        ([1.0, 1.0, 1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]),
        {"mu0": 1.0, "field_axis": 0, "psi": 0.0},
        ValueError,
        "fixed-flux magnetic-field samples must be unique and strictly monotonic",
        "firehose-nonmonotone-samples",
    ),
    (
        "compute_firehose_mirror_margins",
        ([1.0], [2.0], [1.0]),
        {"mu0": 1.0, "dp_perp_dB": -4.0, "parallel_equilibrium": []},
        ValueError,
        "parallel_equilibrium must be a mapping when provided",
        "firehose-invalid-port",
    ),
    (
        "reduce_observation_residuals",
        (),
        {
            "predicted": {},
            "observations": {"flux_loops": {"values": [1.0]}},
        },
        ValueError,
        "predicted must contain flux_loops for every requested usable signal",
        "observation-missing-prediction",
    ),
    (
        "reduce_observation_residuals",
        (),
        {
            "predicted": {"flux_loops": [1.0]},
            "observations": {"flux_loops": {"values": [1.0, 2.0]}},
        },
        ValueError,
        "flux_loops prediction and observation values must have exact same shape",
        "observation-shape",
    ),
    (
        "reduce_observation_residuals",
        (),
        {
            "predicted": {"flux_loops": [np.nan]},
            "observations": {"flux_loops": {"values": [1.0]}},
        },
        ValueError,
        "flux_loops prediction must be finite",
        "observation-nonfinite",
    ),
    (
        "reduce_observation_residuals",
        (),
        {
            "predicted": {"flux_loops": [1.0]},
            "observations": {"flux_loops": {"values": [1.0], "sigma": [0.0]}},
        },
        ValueError,
        "flux_loops values and sigma must be finite and sigma must be positive",
        "observation-sigma",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _SYNTHESIS_MISSING_R,
        ValueError,
        "inputs requires non-null field R",
        "synthesis-missing-port",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _synthesis_flux_kwargs([[1.0]]),
        ValueError,
        "diagnostic points must have nonempty shape (N, 2)",
        "synthesis-point-shape",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _synthesis_flux_kwargs([[10.0, 0.0]]),
        ValueError,
        "diagnostic point lies outside the R-Z grid",
        "synthesis-out-of-domain",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _synthesis_flux_kwargs([[np.nan, 0.0]]),
        ValueError,
        "points must be a finite array with shape (n_points, 2)",
        "synthesis-nonfinite-point",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        _SYNTHESIS_SHAPE_MISMATCH,
        ValueError,
        "R and Z must be same-shape 2-D arrays",
        "synthesis-grid-shape",
    ),
    (
        "synthesize_equilibrium_diagnostics",
        (),
        {
            "R": _SYNTHESIS_R,
            "Z": _SYNTHESIS_Z,
            "equilibrium": {"profiles": {}, "profile_units": {"p_perp": "Pa"}},
            "observations": {"thomson": {"points": [[0.5, 0.5]], "p_perp": {"unit": "Pa"}}},
        },
        ValueError,
        "equilibrium.profiles requires non-null field p_perp",
        "synthesis-missing-thomson-port",
    ),
]


def _assert_mapping_values_equal(actual, expected, *, root=False):
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        assert type(actual) is (Result if root else dict)
        assert list(actual) == list(expected)
        for key, expected_value in expected.items():
            _assert_mapping_values_equal(actual[key], expected_value)
    elif isinstance(expected, np.ndarray):
        assert isinstance(actual, np.ndarray)
        assert actual.shape == expected.shape
        assert actual.dtype == expected.dtype
        np.testing.assert_array_equal(actual, expected)
    else:
        assert type(actual) is type(expected)
        assert actual == expected


def test_result_is_a_mapping_with_attributes():
    result = Result(a=1)
    assert isinstance(result, dict)
    assert result.a == result["a"] == 1
    assert "a" in dir(result)
    with pytest.raises(AttributeError):
        result.missing


@pytest.mark.parametrize(
    "call, field",
    [
        (lambda: compute_poloidal_field_magnitude([[3.0]], [[4.0]]), "B"),
        (lambda: evaluate_plasma_dispersion(0.5 + 0.1j), "Z"),
    ],
)
def test_converted_functions_return_the_same_values_by_key_and_attribute(call, field):
    result = call()
    assert isinstance(result, Result)
    np.testing.assert_array_equal(getattr(result, field), result[field])


def test_diagnostics_cases_cover_every_public_callable():
    covered = {case[0] for case in DIAGNOSTICS_CASES}
    assert covered == set(diagnostics.__all__)


def test_diagnostics_failure_cases_cover_every_newly_migrated_callable():
    assert {case[0] for case in DIAGNOSTICS_FAILURE_CASES} == {
        "compute_picard_flux_residual",
        "compute_firehose_mirror_margins",
        "compute_parallel_pressure_residual",
        "reduce_observation_residuals",
        "synthesize_equilibrium_diagnostics",
    }


@pytest.mark.parametrize(
    "name,args,kwargs,expected",
    [pytest.param(*case[:4], id=case[4]) for case in DIAGNOSTICS_CASES],
)
def test_diagnostics_results_preserve_baseline_values_keys_and_attribute_access(
    name, args, kwargs, expected
):
    function = getattr(diagnostics, name)
    result = function(*args, **kwargs)

    assert type(result) is Result
    assert isinstance(result, dict)
    assert list(result) == list(expected)
    _assert_mapping_values_equal(result, expected, root=True)
    for key in expected:
        assert getattr(result, key) is result[key]


@pytest.mark.parametrize(
    "name,args,kwargs,exception_type,message",
    [pytest.param(*case[:5], id=case[5]) for case in DIAGNOSTICS_FAILURE_CASES],
)
def test_diagnostics_failures_match_baseline_type_and_message(
    name, args, kwargs, exception_type, message
):
    function = getattr(diagnostics, name)
    with pytest.raises(exception_type) as error:
        function(*args, **kwargs)
    assert str(error.value) == message
