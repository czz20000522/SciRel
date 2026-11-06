"""The named result keeps mapping behaviour and adds attribute access."""

import numpy as np
import pytest

from scirel._result import Result
from scirel import closures, diagnostics, field, neoclassical
from scirel.field import compute_poloidal_field_magnitude
from scirel.kinetic import evaluate_plasma_dispersion

_FLUX_GRID_R, _FLUX_GRID_Z = np.meshgrid([0.0, 0.2, 0.4], [-0.5, 0.0, 0.5])
_COIL_MODULUS = field.compute_axisymmetric_coil_modulus(
    0.3,
    0.0,
    np.array([0.2, 0.2]),
    np.array([-0.1, 0.1]),
)
_COIL_K, _COIL_E = field.evaluate_complete_elliptic_integrals(_COIL_MODULUS[1])
_CONDUCTOR_INPUTS = {
    "uncorrected_field_flux": np.array([3.0, -1.0, 2.0]),
    "boundary_sample_matrix": np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]]),
    "green_boundary_to_boundary": np.array([[2.0, 0.0], [0.0, 4.0]]),
    "green_boundary_to_field": np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]]),
}


# Expected values were captured from baseline 968fb2a8 before the remaining
# plain-dict field returns were wrapped in Result. The existing domain tests
# retain the independent physical derivations and tighter numerical gates.
FIELD_CASES = [
    (
        "compute_poloidal_field_magnitude",
        ([[3.0, 0.0]], [[4.0, 0.0]]),
        {},
        {"B": np.array([[5.0, 1.0e-30]]), "B0_default": 2.5},
        "poloidal-magnitude",
    ),
    (
        "discretize_permanent_ring",
        (2.0, 3.0, 4.0, 2.0),
        {},
        {
            "rz_pts": np.array(
                [
                    [0.0, 2.0],
                    [0.0, 2.2857142857142856],
                    [0.0, 2.571428571428571],
                    [0.0, 2.857142857142857],
                    [0.0, 3.142857142857143],
                    [0.0, 3.4285714285714284],
                    [0.0, 3.7142857142857144],
                    [0.0, 4.0],
                    [4.0, 2.0],
                    [4.0, 2.2857142857142856],
                    [4.0, 2.571428571428571],
                    [4.0, 2.857142857142857],
                    [4.0, 3.142857142857143],
                    [4.0, 3.4285714285714284],
                    [4.0, 3.7142857142857144],
                    [4.0, 4.0],
                ],
                dtype=float,
            ),
            "default_weights": np.array([-1.0] * 8 + [1.0] * 8, dtype=float),
        },
        "permanent-ring",
    ),
    (
        "correct_ideal_conductor_boundary_flux",
        (),
        _CONDUCTOR_INPUTS,
        {
            "corrected_field_flux": np.array([0.0, 0.125, -0.125]),
            "boundary_currents": np.array([-1.5, -0.125]),
            "boundary_flux_correction": np.array([-3.0, -0.5]),
            "field_flux_correction": np.array([-3.0, 1.125, -2.125]),
            "singular_values": np.array([4.0, 2.0]),
            "effective_rank": 2,
            "residual": np.array([0.0, 0.0]),
            "residual_norm": 0.0,
        },
        "ideal-conductor",
    ),
    (
        "discretize_rectangular_coil",
        (1.0, 2.0, 2, 3, 0.5, 1.0),
        {},
        np.array(
            [
                [0.75, 1.0],
                [0.75, 2.0],
                [0.75, 3.0],
                [1.25, 1.0],
                [1.25, 2.0],
                [1.25, 3.0],
            ]
        ),
        "rectangular-coil",
    ),
    (
        "superpose_current_green_field",
        (
            [2.0, -1.0],
            [[1.0, 4.0], [3.0, 5.0]],
            [[2.0, 0.0], [1.0, 6.0]],
            [[-1.0, 3.0], [2.0, 4.0]],
        ),
        {},
        {
            "psi": np.array([-2.0, 1.0]),
            "BR": np.array([4.0, -4.0]),
            "BZ": np.array([-5.0, 0.0]),
        },
        "current-superposition",
    ),
    (
        "integrate_filament_vacuum_field",
        (
            np.array([[0.0, 0.1], [0.0, 0.1]]),
            np.array([[-0.1, -0.1], [0.1, 0.1]]),
            [[0.5, 0.0, 1000.0]],
        ),
        {},
        {
            "psi": np.array([[0.0, 6.0652851913171126e-06], [0.0, 6.0652851913171126e-06]]),
            "b_r": np.array([[0.0, -7.306763253636188e-05], [0.0, 7.306763253636188e-05]]),
            "b_z": np.array(
                [
                    [0.00118484040269335, 0.00121305703826342],
                    [0.00118484040269335, 0.00121305703826342],
                ]
            ),
        },
        "filament-vacuum",
    ),
    (
        "circular_filament_green_response",
        ([[0.35, 0.0, 1.0]], [[0.0, 0.0], [0.2, -0.1], [0.2, 0.1]]),
        {},
        {
            "gpsi": np.array([0.0, 3.408844653749818e-08, 3.408844653749818e-08]),
            "gBR": np.array([0.0, -5.94157114816084e-07, 5.94157114816084e-07]),
            "gBZ": np.array(
                [1.7951958020513105e-06, 1.8000939097309208e-06, 1.8000939097309208e-06]
            ),
        },
        "circular-filament",
    ),
    (
        "poloidal_field_from_flux",
        (_FLUX_GRID_R, _FLUX_GRID_Z, _FLUX_GRID_R**2),
        {},
        {
            "B_R": np.zeros_like(_FLUX_GRID_R),
            "B_Z": 2.0 * np.ones_like(_FLUX_GRID_R),
            "B": 2.0 * np.ones_like(_FLUX_GRID_R),
        },
        "poloidal-flux",
    ),
    (
        "dense_axisymmetric_green_response",
        ([[0.1, -0.1], [0.2, 0.1]], [[0.35, 0.0, 1.0], [0.45, 0.1, -0.5]]),
        {},
        {
            "gpsi": np.array(
                [
                    [8.1201982539211906e-09, -2.6700490205393802e-09],
                    [3.4088446537498181e-08, -1.5146403769655086e-08],
                ]
            ),
            "gBR": np.array(
                [[-2.0346323019342388e-07, 6.9095090739696396e-08], [5.9415711481608399e-07, 0.0]]
            ),
            "gBZ": np.array(
                [
                    [1.6522221976307801e-06, -5.3511766595145251e-07],
                    [1.8000939097309208e-06, -8.2527922099954808e-07],
                ]
            ),
        },
        "dense-green",
    ),
    (
        "build_mirror_plasma_flux_green",
        (
            np.array([[0.0, 0.1], [0.0, 0.1]]),
            np.array([[-0.1, -0.1], [0.1, 0.1]]),
        ),
        {},
        {
            "g_psi": np.array(
                [
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 2.2577708482093533e-09],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 2.2577708482093533e-09, 0.0, 0.0],
                ]
            )
        },
        "mirror-green",
    ),
    (
        "solve_multi_coil_vacuum_field",
        (),
        {
            "r_grid": np.meshgrid([0.0, 0.2], [-0.1, 0.1])[0],
            "z_grid": np.meshgrid([0.0, 0.2], [-0.1, 0.1])[1],
            "rectangular_coils": [
                {
                    "r0_m": 0.45,
                    "z0_m": 0.0,
                    "nr": 2,
                    "nz": 2,
                    "dr_m": 0.04,
                    "dz_m": 0.05,
                    "current_a": 1000.0,
                }
            ],
        },
        {
            "psi_vac": np.array(
                [
                    [0.0, 0.00010959011510665226],
                    [0.0, 0.00010959011510665225],
                ]
            ),
            "b_r_vac": np.array(
                [
                    [0.0, -0.0010127574873699627],
                    [0.0, 0.0010127574873699627],
                ]
            ),
            "b_z_vac": np.array(
                [
                    [0.005184721052146086, 0.0057889682202285605],
                    [0.005184721052146085, 0.0057889682202285605],
                ]
            ),
            "filaments": np.array(
                [
                    [0.43, -0.025, 1.0],
                    [0.43, 0.025, 1.0],
                    [0.47000000000000003, -0.025, 1.0],
                    [0.47000000000000003, 0.025, 1.0],
                ]
            ),
        },
        "multi-coil",
    ),
    (
        "compute_axisymmetric_coil_modulus",
        (0.3, 0.0, np.array([0.2, 0.2]), np.array([-0.1, 0.1])),
        {},
        (
            0.30000001,
            np.array([0.9230769183431952, 0.9230769183431952]),
            np.array([0.5099019611650852, 0.5099019611650852]),
        ),
        "coil-modulus-tuple",
    ),
    (
        "evaluate_complete_elliptic_integrals",
        (_COIL_MODULUS[1],),
        {},
        (
            np.array([2.70217831892606, 2.70217831892606]),
            np.array([1.0852560251068435, 1.0852560251068435]),
        ),
        "elliptic-tuple",
    ),
    (
        "evaluate_filament_coil_green_field",
        (
            _COIL_MODULUS[0],
            0.0,
            np.array([0.2, 0.2]),
            np.array([-0.1, 0.1]),
            np.array([10.0, 10.0]),
            np.array([2.0, 2.0]),
            _COIL_MODULUS[1],
            _COIL_K,
            _COIL_E,
        ),
        {},
        (1.5083433413389553e-06, 0.0, -8.685430511066101e-06),
        "filament-coil-tuple",
    ),
]


FIELD_FAILURE_CASES = [
    (
        "discretize_permanent_ring",
        (2.0, 3.0, 0.0, 2.0),
        {},
        ValueError,
        "ring geometry must have nonnegative radius and positive dimensions",
        "permanent-invalid-size",
    ),
    (
        "correct_ideal_conductor_boundary_flux",
        (),
        {**_CONDUCTOR_INPUTS, "rcond": -1.0},
        ValueError,
        "rcond must be a non-negative finite value",
        "conductor-invalid-rcond",
    ),
    (
        "superpose_current_green_field",
        (
            [1.0, 2.0],
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        ),
        {},
        ValueError,
        "Green source axis (columns) must equal the number of currents",
        "current-source-axis",
    ),
    (
        "integrate_filament_vacuum_field",
        (
            np.array([[0.0, 0.1, 0.2], [0.0, 0.11, 0.2]]),
            np.array([[-0.1, -0.1, -0.1], [0.1, 0.1, 0.1]]),
            [[0.5, 0.0, 1000.0]],
        ),
        {},
        ValueError,
        "r_grid must be a rectilinear radial coordinate varying along exactly one axis",
        "filament-nonrectilinear",
    ),
    (
        "circular_filament_green_response",
        ([[0.3, 0.0]], [[0.1, 0.0]]),
        {},
        ValueError,
        "rzw must have shape (n_filaments, 3)",
        "circular-source-shape",
    ),
    (
        "dense_axisymmetric_green_response",
        ([[0.1, 0.0]], [[0.3, 0.0]]),
        {},
        ValueError,
        "source_rzw must have shape (n_sources, 3)",
        "dense-source-shape",
    ),
    (
        "build_mirror_plasma_flux_green",
        (
            np.array([[0.0, 0.1, 0.2], [0.0, 0.1, 0.2], [0.0, 0.1, 0.2]]),
            np.array([[-0.2, -0.2, -0.2], [0.0, 0.0, 0.0], [0.3, 0.3, 0.3]]),
        ),
        {},
        ValueError,
        "the reflection construction requires an axis-reflection-symmetric Z grid",
        "mirror-asymmetry",
    ),
    (
        "solve_multi_coil_vacuum_field",
        (),
        {
            "r_grid": np.empty((0, 2)),
            "z_grid": np.empty((0, 2)),
            "rectangular_coils": [
                {
                    "r0_m": 0.45,
                    "z0_m": 0.0,
                    "nr": 1,
                    "nz": 1,
                    "dr_m": 0.04,
                    "dz_m": 0.05,
                    "current_a": 1000.0,
                }
            ],
        },
        ValueError,
        "r_grid and z_grid must be nonempty 2-D arrays",
        "multi-coil-empty-grid",
    ),
]

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


def _assert_value_equal(actual, expected):
    if isinstance(expected, tuple):
        assert type(actual) is tuple
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected):
            _assert_value_equal(actual_item, expected_item)
    elif isinstance(expected, np.ndarray):
        assert type(actual) is np.ndarray
        assert actual.shape == expected.shape
        assert actual.dtype == expected.dtype
        np.testing.assert_allclose(actual, expected, rtol=2.0e-14, atol=1.0e-300)
    elif isinstance(expected, float):
        assert type(actual) is float
        assert actual == pytest.approx(expected, rel=2.0e-14, abs=1.0e-300)
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


def test_field_cases_cover_every_public_callable():
    assert {case[0] for case in FIELD_CASES} == set(field.__all__)


def test_field_failure_cases_cover_every_newly_migrated_callable():
    assert {case[0] for case in FIELD_FAILURE_CASES} == {
        "discretize_permanent_ring",
        "correct_ideal_conductor_boundary_flux",
        "superpose_current_green_field",
        "integrate_filament_vacuum_field",
        "circular_filament_green_response",
        "dense_axisymmetric_green_response",
        "build_mirror_plasma_flux_green",
        "solve_multi_coil_vacuum_field",
    }


@pytest.mark.parametrize(
    "name,args,kwargs,expected",
    [pytest.param(*case[:4], id=case[4]) for case in FIELD_CASES],
)
def test_field_results_preserve_baseline_values_keys_and_mapping_types(
    name, args, kwargs, expected
):
    result = getattr(field, name)(*args, **kwargs)

    if isinstance(expected, dict):
        assert type(result) is Result
        assert isinstance(result, dict)
        assert list(result) == list(expected)
        assert not any(isinstance(value, dict) for value in result.values())
        for key, expected_value in expected.items():
            _assert_value_equal(result[key], expected_value)
            assert getattr(result, key) is result[key]
    else:
        assert type(result) is type(expected)
        _assert_value_equal(result, expected)


@pytest.mark.parametrize(
    "name,args,kwargs,exception_type,message",
    [pytest.param(*case[:5], id=case[5]) for case in FIELD_FAILURE_CASES],
)
def test_field_failures_match_baseline_type_and_message(
    name, args, kwargs, exception_type, message
):
    function = getattr(field, name)
    with pytest.raises(exception_type) as error:
        function(*args, **kwargs)
    assert str(error.value) == message


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


# Baseline checks for the seven plain-dict closure returns migrated in #2, plus
# the two closure exports that already returned Result. Detailed numerics stay in
# tests/closures; this protects return type, key order and representative baseline
# values without duplicating the #1 numpydoc matrix.
_E = 1.602176634e-19


def _closure_hall_call():
    def law(b, psi):
        return {"p_parallel": 5.0 + b + psi, "p_perpendicular": 4.0 + b + 2.0 * psi}

    return closures.close_hall_two_fluid_pressure([[1.0, 2.0]], [[0.2, 0.4]], law, 1.0e18, 1.0, 3.0)


def _closure_quasi_call():
    return closures.solve_quasineutral_potential(
        [0.0, 17.0],
        0.1 * _E,
        0.1 * _E,
        _E,
        [True, False],
        lambda phi: {"logarithmic_charge_residual": 0.5 - np.asarray(phi)},
    )


def _closure_ambipolar_call():
    return closures.solve_mirror_ambipolar_potential(
        1.0,
        1.0,
        0.0,
        1.67262192595e-27,
        _E,
        2.0e18,
        2.0 * _E,
        3.0 * _E,
        _E,
        electron_density_ref_m3=3.0e18,
        ion_loss_refill=0.25,
        electron_loss_refill=0.5,
        mode="evaluate",
        phi_plug_v=1.0,
    )


def _closure_reduced_hall_call():
    r, z = np.meshgrid(np.linspace(0.0, 0.4, 3), np.linspace(-0.2, 0.2, 3))
    pressure = np.full((3, 3), 20.0)
    return closures.close_reduced_hall_drift(
        r,
        z,
        np.zeros((3, 3)),
        np.full((3, 3), 2.0),
        pressure,
        pressure,
        {
            "ion_density": np.full((3, 3), 1.0e18),
            "electron_pressure": np.zeros((3, 3)),
            "electrostatic_potential": np.zeros((3, 3)),
            "ion_p_parallel": pressure,
            "ion_p_perpendicular": pressure,
        },
        np.ones((3, 3), dtype=bool),
        1.67262192595e-27,
        _E,
    )


def _closure_mirror_quasi_call():
    return closures.solve_mirror_quasineutral_closure(
        b_t=np.array([1.0, 1.4, 2.0]),
        psi=np.zeros(3),
        mass_kg=1.67262192595e-27,
        charge_c=_E,
        density_ref_m3=2.0e18,
        temperature_parallel_j=1200.0 * _E,
        temperature_perpendicular_ref_j=2400.0 * _E,
        b_ref_t=1.0,
        electron_temperature_j=600.0 * _E,
    )


def _closure_feedback_call():
    inputs = {
        "input_time_s": [0.0],
        "observation_time_s": [0.0],
        "signals": {
            "reference_T": [[0.0] * 10],
            "measured_T": [[0.0] * 10],
            "feedforward_current_A": [[0.0] * 11],
            "enable": [0],
        },
    }
    controller = {
        "sample_period_s": 1.0,
        "P": [0.0] * 10,
        "I": [0.0] * 10,
        "D": [0.0] * 10,
        "N_per_s": [0.0] * 10,
        "coefficient_matrix_unscaled": [[0.0] * 10 for _ in range(11)],
        "coefficient_scale": 1.0,
        "integrator_initial_state": [0.0] * 10,
        "filter_initial_state": [0.0] * 10,
        "internal_integration_enable": [1] * 10,
        "internal_reset": 0,
    }
    return closures.simulate_discrete_vector_feedback(inputs, controller)


_CLOSURE_CASES = {
    "compute_reference_electron_density": (
        lambda: closures.compute_reference_electron_density([1.0e18, 2.0e18], [1.0, 3.0]),
        ("electron_density_ref_m3",),
        {"electron_density_ref_m3": np.array([1.0e18, 6.0e18])},
        Result,
    ),
    "compute_boltzmann_electron_state": (
        lambda: closures.compute_boltzmann_electron_state(np.log(2.0), _E, 3.0, 0.0, 3.0, 2.0),
        (
            "electron_density_m3",
            "electron_pressure_pa",
            "logarithmic_charge_residual",
            "charge_residual_m3",
            "relative_charge_residual",
        ),
        {
            "electron_density_m3": np.float64(6.000000000000001),
            "electron_pressure_pa": np.float64(9.613059803999962e-19),
            "logarithmic_charge_residual": np.array(-2.220446049250313e-16),
        },
        Result,
    ),
    "close_hall_two_fluid_pressure": (
        _closure_hall_call,
        (
            "pressure_composition_mode",
            "species_pressure_sum_consistent",
            "residual_stress_parallel_pa",
            "residual_stress_perpendicular_pa",
            "p_parallel",
            "p_perpendicular",
            "ion_density",
            "electron_density",
            "electron_pressure",
            "electron_p_parallel",
            "electron_p_perpendicular",
            "electrostatic_potential",
            "ion_p_parallel",
            "ion_p_perpendicular",
        ),
        {
            "pressure_composition_mode": "independent_fit",
            "species_pressure_sum_consistent": True,
            "p_parallel": np.array([[6.2, 7.4]]),
            "p_perpendicular": np.array([[5.4, 6.8]]),
        },
        Result,
    ),
    "solve_quasineutral_potential": (
        _closure_quasi_call,
        ("potential_v", "logarithmic_charge_residual", "iterations", "converged"),
        {
            "potential_v": np.array([0.5, 17.0]),
            "logarithmic_charge_residual": np.array([0.0, -16.5]),
            "iterations": 5,
            "converged": True,
        },
        Result,
    ),
    "evaluate_tabulated_pressure": (
        lambda: closures.evaluate_tabulated_pressure(
            1.5,
            0.25,
            np.array([0.0, 1.0]),
            np.array([[2.0, 4.0], [4.0, 6.0]]),
            np.array([[3.0, 5.0], [5.0, 7.0]]),
            np.array([1.0, 2.0]),
        ),
        ("p_parallel", "p_perpendicular", "is_isotropic", "table_dimension"),
        {
            "p_parallel": np.float64(3.5),
            "p_perpendicular": np.float64(4.5),
            "is_isotropic": False,
            "table_dimension": 2,
        },
        Result,
    ),
    "solve_mirror_ambipolar_potential": (
        _closure_ambipolar_call,
        (
            "potential_v",
            "ion_particle_flux_m2_s",
            "electron_particle_flux_m2_s",
            "log_current_ratio",
            "relative_current_residual",
            "iterations",
            "converged",
            "evaluation_complete",
            "current_balance_solved",
        ),
        {
            "potential_v": np.array(1.0),
            "ion_particle_flux_m2_s": np.float64(1.674573179533026e21),
            "electron_particle_flux_m2_s": np.float64(2.5096434433404035e23),
            "iterations": 0,
            "current_balance_solved": False,
        },
        Result,
    ),
    "close_reduced_hall_drift": (
        _closure_reduced_hall_call,
        tuple(
            """pressure_composition_mode species_pressure_sum_consistent residual_stress_parallel_pa
            residual_stress_perpendicular_pa J_phi force_R force_Z pressure_force_R pressure_force_Z
            electron_pressure_force_R electron_pressure_force_Z parallel_force parallel_force_error
            parallel_force_diagnostics ohm_diagnostics momentum_diagnostics momentum_residual_R
            momentum_residual_Z momentum_error ion_toroidal_velocity electron_toroidal_velocity
            raw_ion_toroidal_velocity ion_toroidal_mach raw_ion_toroidal_mach centrifugal_force_R
            electric_field_R electric_field_Z hall_electric_field_R hall_electric_field_Z ohm_residual_R
            ohm_residual_Z ohm_parallel generalized_ohm_error firehose_margin ion_skin_depth
            electron_skin_depth ion_gyroradius magnetic_scale_length hall_scale_ratio
            electron_inertia_scale_ratio ion_gyroradius_scale_ratio hall_active_mask density_floor_m3
            velocity_cap_fraction inertia_iterations inertia_relative_change
            inertia_fixed_point_residual inertia_converged""".split()
        ),
        {
            "pressure_composition_mode": "independent_fit",
            "species_pressure_sum_consistent": True,
            "J_phi": np.zeros((3, 3)),
            "ion_toroidal_velocity": np.zeros((3, 3)),
            "inertia_iterations": 1,
            "inertia_converged": True,
        },
        Result,
    ),
    "solve_mirror_quasineutral_closure": (
        _closure_mirror_quasi_call,
        tuple(
            """density_m3 p_parallel_pa p_perpendicular_pa temperature_parallel_j
            temperature_perpendicular_local_j untruncated_density_m3 density_pitch_integral
            parallel_pitch_integral perpendicular_pitch_integral p_parallel p_perpendicular
            ion_density ion_p_parallel ion_p_perpendicular electron_density electron_pressure
            electrostatic_potential relative_charge_residual kinetic_moments iterations
            converged""".split()
        ),
        {"converged": True},
        Result,
    ),
    "simulate_discrete_vector_feedback": (
        _closure_feedback_call,
        ("schema", "time_s", "values", "state_trace"),
        {
            "schema": "magnetic-error-current-feedback-discrete",
            "time_s": [0.0],
            "values": {
                "total_current_A": [[0.0] * 11],
                "feedback_current_A": [[0.0] * 11],
                "pid_components": [[0.0] * 30],
                "error_T": [[0.0] * 10],
            },
            "state_trace": {
                "reset_at_sample": [True],
                "pre_integrator_state": [[0.0] * 10],
                "pre_filter_state": [[0.0] * 10],
                "post_integrator_state": [[0.0] * 10],
                "post_filter_state": [[0.0] * 10],
            },
        },
        Result,
    ),
}

_CLOSURES_MIGRATED = {
    "close_hall_two_fluid_pressure",
    "solve_quasineutral_potential",
    "evaluate_tabulated_pressure",
    "close_reduced_hall_drift",
    "simulate_discrete_vector_feedback",
    "solve_mirror_ambipolar_potential",
    "solve_mirror_quasineutral_closure",
}
# No public closure callable returns a bare tuple or ndarray in this baseline.
_CLOSURES_BARE_RETURN_CASES = set()

_CLOSURES_FAILURE_CASES = [
    (
        "close_hall_two_fluid_pressure",
        lambda: closures.close_hall_two_fluid_pressure(
            np.ones((1, 1)), np.zeros((1, 1)), 1, 1.0, 1.0, 0.0
        ),
        TypeError,
        "pressure_law must be callable",
    ),
    (
        "solve_quasineutral_potential",
        lambda: closures.solve_quasineutral_potential(0.0, 1.0, 1.0, 1.0, True, lambda _: {}),
        ValueError,
        "residual must return logarithmic_charge_residual",
    ),
    (
        "evaluate_tabulated_pressure",
        lambda: closures.evaluate_tabulated_pressure(1.0, 0.0, [1.0], [1.0, 2.0]),
        ValueError,
        "psi_grid must be one-dimensional, finite, and strictly increasing",
    ),
    (
        "solve_mirror_ambipolar_potential",
        lambda: closures.solve_mirror_ambipolar_potential(
            1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, mode="bad"
        ),
        ValueError,
        "mode must be solve or evaluate",
    ),
    (
        "close_reduced_hall_drift",
        lambda: closures.close_reduced_hall_drift(
            np.ones((2, 2)),
            np.ones((2, 2)),
            1.0,
            1.0,
            1.0,
            1.0,
            {"ion_density": 1.0, "electron_pressure": 1.0, "electrostatic_potential": 0.0},
            np.ones((2, 2), dtype=bool),
            1.0,
            1.0,
        ),
        ValueError,
        "a rectilinear R-Z grid with at least 3 points per axis is required",
    ),
    (
        "solve_mirror_quasineutral_closure",
        lambda: closures.solve_mirror_quasineutral_closure(inputs={}),
        ValueError,
        "missing required inputs: b_ref_t, b_t, charge_c, density_ref_m3, electron_temperature_j, mass_kg, psi, temperature_parallel_j, temperature_perpendicular_ref_j",
    ),
    (
        "simulate_discrete_vector_feedback",
        lambda: closures.simulate_discrete_vector_feedback([], {}),
        TypeError,
        "inputs and controller must be mappings",
    ),
]


def _assert_closure_value(actual, expected):
    if isinstance(expected, dict):
        _assert_mapping_values_equal(actual, expected)
    elif isinstance(expected, np.generic):
        assert type(actual) is type(expected)
        np.testing.assert_allclose(actual, expected, rtol=2.0e-14, atol=1.0e-300)
    else:
        _assert_value_equal(actual, expected)


def test_closures_cases_cover_every_public_callable():
    assert set(_CLOSURE_CASES) == set(closures.__all__)
    assert _CLOSURES_BARE_RETURN_CASES == set()


@pytest.mark.parametrize("name", sorted(_CLOSURE_CASES))
def test_closure_results_preserve_baseline_values_and_return_types(name):
    call, expected_keys, expected, expected_type = _CLOSURE_CASES[name]
    result = call()
    assert type(result) is expected_type
    assert isinstance(result, dict)
    assert list(result) == list(expected_keys)
    if expected_type is Result:
        for key in expected_keys:
            if key != "values":
                assert getattr(result, key) is result[key]
    for key, expected_value in expected.items():
        _assert_closure_value(result[key], expected_value)
    if name == "solve_mirror_quasineutral_closure":
        assert result["p_parallel"].shape == (3,)
        assert np.max(np.abs(result["relative_charge_residual"])) < 1e-10
    if name == "simulate_discrete_vector_feedback":
        assert callable(result.values)
        assert list(result["values"]) == list(expected["values"])
        assert list(dict.values(result))[2] is result["values"]


def test_closures_failure_cases_cover_every_migrated_callable():
    assert {case[0] for case in _CLOSURES_FAILURE_CASES} == _CLOSURES_MIGRATED


@pytest.mark.parametrize("name,call,exception_type,message", _CLOSURES_FAILURE_CASES)
def test_closures_failures_match_baseline_type_and_message(name, call, exception_type, message):
    with pytest.raises(exception_type) as error:
        call()
    assert str(error.value) == message


# Baseline checks for the one plain-dict neoclassical return migrated in #2.
# The coefficient fits intentionally remain tuples under the unchanged public
# contract, so these cases distinguish the migrated mapping from bare returns.
_NEOCLASSICAL_F = np.array([0.2, 0.5])
_NEOCLASSICAL_NU_E = np.array([0.01, 10.0])
_NEOCLASSICAL_Z = np.array([1.5, 2.0])
_NEOCLASSICAL_NU_I = np.array([0.03, 2.0])


def _neoclassical_current_inputs():
    one = np.ones(3)
    zero = np.zeros(3)
    return {
        "rho_face": [0.0, 0.5, 1.0],
        "F_face": one,
        "B0": 2.0,
        "dpsi_drho_face": one,
        "p_e_face": one,
        "p_i_face": one,
        "dlnne_drho_face": one,
        "dlnni_drho_face": zero,
        "dlnte_drho_face": zero,
        "dlnti_drho_face": zero,
        "L31": one,
        "L32": zero,
        "L34": one,
        "alpha": one,
    }


def _neoclassical_current_call():
    return neoclassical.calculate_bootstrap_current(**_neoclassical_current_inputs())


_NEOCLASSICAL_CASES = {
    "calculate_sauter_coefficients": (
        lambda: neoclassical.calculate_sauter_coefficients(
            _NEOCLASSICAL_F,
            _NEOCLASSICAL_NU_E,
            _NEOCLASSICAL_Z,
            _NEOCLASSICAL_NU_I,
        ),
        tuple,
        (
            np.array([0.25917819213065246, 0.13392807216870214]),
            np.array([-0.11574116188410322, 0.0702213976355152]),
            np.array([0.2591068046093363, 0.1202184934201009]),
            np.array([-0.870010942879218, -0.22957797344199568]),
        ),
    ),
    "calculate_redl_coefficients": (
        lambda: neoclassical.calculate_redl_coefficients(
            _NEOCLASSICAL_F,
            _NEOCLASSICAL_NU_E,
            _NEOCLASSICAL_Z,
            _NEOCLASSICAL_NU_I,
        ),
        tuple,
        (
            np.array([0.21296571828116218, 0.07440042135914428]),
            np.array([-0.10833728380262302, 0.09740318582888735]),
            np.array([0.21296571828116218, 0.07440042135914428]),
            np.array([-0.7951882184432387, 0.6440950155435712]),
        ),
    ),
    "calculate_bootstrap_current": (
        _neoclassical_current_call,
        Result,
        {
            "j_parallel_bootstrap_face": np.array([0.0, -np.pi, -np.pi]),
            "j_parallel_bootstrap": np.array([-np.pi / 2.0, -np.pi]),
        },
    ),
}

_NEOCLASSICAL_MIGRATED = {"calculate_bootstrap_current"}
_NEOCLASSICAL_BARE_RETURN_CASES = {
    "calculate_sauter_coefficients",
    "calculate_redl_coefficients",
}

_NEOCLASSICAL_FAILURE_CASES = [
    (
        "calculate_sauter_coefficients",
        lambda: neoclassical.calculate_sauter_coefficients(
            [True, 0.5], [1.0, 1.0], [2.0, 2.0], [1.0, 1.0]
        ),
        ValueError,
        "f_trap must be a real numeric face array",
    ),
    (
        "calculate_redl_coefficients",
        lambda: neoclassical.calculate_redl_coefficients(
            [True, 0.5], [1.0, 1.0], [2.0, 2.0], [1.0, 1.0]
        ),
        ValueError,
        "f_trap must be a real numeric face array",
    ),
    (
        "calculate_bootstrap_current",
        lambda: neoclassical.calculate_bootstrap_current(
            **{**_neoclassical_current_inputs(), "B0": 0.0}
        ),
        ValueError,
        "B0 must be finite and nonzero; multiplier must be finite",
    ),
]


def test_neoclassical_cases_cover_every_public_callable():
    assert set(_NEOCLASSICAL_CASES) == set(neoclassical.__all__)
    assert _NEOCLASSICAL_MIGRATED == {
        name for name, case in _NEOCLASSICAL_CASES.items() if case[1] is Result
    }
    assert _NEOCLASSICAL_BARE_RETURN_CASES == {
        name for name, case in _NEOCLASSICAL_CASES.items() if case[1] is tuple
    }


@pytest.mark.parametrize("name", sorted(_NEOCLASSICAL_CASES))
def test_neoclassical_results_preserve_baseline_values_and_return_types(name):
    call, expected_type, expected = _NEOCLASSICAL_CASES[name]
    result = call()
    assert type(result) is expected_type
    if expected_type is Result:
        assert isinstance(result, dict)
        assert list(result) == list(expected)
        _assert_mapping_values_equal(result, expected, root=True)
        for key in expected:
            assert getattr(result, key) is result[key]
    else:
        _assert_value_equal(result, expected)


def test_neoclassical_failure_cases_cover_every_public_callable():
    assert {case[0] for case in _NEOCLASSICAL_FAILURE_CASES} == set(neoclassical.__all__)


@pytest.mark.parametrize("name,call,exception_type,message", _NEOCLASSICAL_FAILURE_CASES)
def test_neoclassical_failures_match_baseline_type_and_message(name, call, exception_type, message):
    with pytest.raises(exception_type) as error:
        call()
    assert str(error.value) == message
