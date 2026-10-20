"""Failing successor regressions captured before D2 repairs (F1/F2)."""
import numpy as np
import pytest
from scipy.special import erfcx, wofz
from scirel.kinetic import (
    evaluate_cauchy_transform,
    evaluate_maxwellian_electrostatic,
    solve_maxwellian_electrostatic_mode,
)


def test_small_k_maxwellian_limit_is_three_quarters_and_false_seed_rejected():
    # Independent large-z Maxwellian expansion: epsilon(2,k)->1-1/4=0.75.
    for k in (1e-5, 1e-7, 1e-9, 1e-10):
        got = evaluate_maxwellian_electrostatic(2.0, k)
        assert complex(got["epsilon"]).real == pytest.approx(0.75, abs=1e-7)
        assert abs(complex(got["epsilon"]).imag) < 1e-12
        try:
            mode = solve_maxwellian_electrostatic_mode(k, 2.0)
        except RuntimeError:
            continue
        omega = complex(mode['omega'])
        assert abs(omega - 2.0) > 0.1
        assert abs(1 - 1 / omega**2 - 3 * k**2 / omega**4) < 1e-6


def test_maxwellian_matrix_application_matches_scalar_application():
    # Regression for the public vector/matrix contract and elementwise scalar semantics.
    omega = np.array([[1.2 + 0.3j, 1.4 - 0.1j, 0.8 + 0.2j], [2.0j, 0.6, -1.1 + 0.4j]])
    got = evaluate_maxwellian_electrostatic(omega, 0.4)["epsilon"]
    expected = np.vectorize(lambda x: evaluate_maxwellian_electrostatic(x, 0.4)["epsilon"])(omega)
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-13)


def test_cauchy_shifted_narrow_gaussian_requires_declared_support_and_matches_faddeeva():
    center, width, z = 10.0, 0.1, 1j
    density = lambda v: np.exp(-((v - center) / width) ** 2) / (np.sqrt(np.pi) * width)
    expected = 1j * np.sqrt(np.pi) * wofz((z - center) / width) / width
    # A declared support/scale is required for a generic callback; it must resolve the feature.
    mesh = center + width * np.linspace(-10, 10, 41)
    got = evaluate_cauchy_transform(z, density, integration_mesh=mesh)
    np.testing.assert_allclose(got["G"], expected, rtol=0, atol=1e-9)
    assert np.all(np.asarray(got["quadrature_error"]) >= 0)


def test_cauchy_invalid_epsabs_is_value_error_and_unresolved_default_fails_closed():
    density = lambda v: np.exp(-v * v) / np.sqrt(np.pi)
    for bad in (None, [1e-3], True, 0.0, np.inf):
        with pytest.raises(ValueError):
            evaluate_cauchy_transform(1j, density, epsabs=bad)
    with pytest.raises((ValueError, RuntimeError)):
        evaluate_cauchy_transform(1j, lambda v: np.exp(-((v - 10) / 0.1) ** 2) / (np.sqrt(np.pi) * 0.1))


def test_cauchy_finite_support_continuation_only_crosses_interior_cut():
    density = lambda v: 1.0
    analytic = lambda z: 1.0
    inside = evaluate_cauchy_transform(0.2 - 0.5j, density, bounds=(-1.0, 1.0), analytic_density=analytic)
    outside = evaluate_cauchy_transform(2.0 - 0.5j, density, bounds=(-1.0, 1.0), analytic_density=analytic)
    inside_contour = evaluate_cauchy_transform(0.2 - 0.5j, density, bounds=(-1.0, 1.0))
    outside_contour = evaluate_cauchy_transform(2.0 - 0.5j, density, bounds=(-1.0, 1.0))
    assert abs(complex(inside["G"]) - complex(inside_contour["G"]) - 2j * np.pi) < 1e-10
    assert abs(complex(outside["G"]) - complex(outside_contour["G"])) < 1e-10


@pytest.mark.parametrize('bad', ['1e-4', np.array(True)])
def test_cauchy_tolerances_require_real_numeric_scalars(bad):
    with pytest.raises(ValueError):
        evaluate_cauchy_transform(1j, lambda v: 1.0, bounds=(-1, 1), epsabs=bad)


def test_cauchy_mesh_rejects_mixed_boolean_coordinates():
    with pytest.raises(ValueError):
        evaluate_cauchy_transform(1j, lambda v: 1.0, integration_mesh=[False, 1.0])
