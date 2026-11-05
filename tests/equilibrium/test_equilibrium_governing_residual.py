"""Analytic criteria for the pressure-only closure, fixed before repair runs.

For psi=R and P=R_edge-R, dP/dpsi=-1. Therefore I*=-R*dR*dZ
and, with zero Green matrix, relaxed current error after n updates is relax**n.
This independently measures the governing current relation, not flux updates.
"""

import numpy as np
import pytest

from scirel.equilibrium import compute_equilibrium


@pytest.mark.parametrize("amplitude", [1.0, 1e160])
@pytest.mark.parametrize("gain", [0.2, 0.8, 4.0])
def test_target_norm_residual_with_oversized_terminal_current(amplitude, gain):
    # Analytic nonphysical supplied-G witness: psi0=R, P=a*(5-R),
    # G=-gain/a Identity, relax=0 -> I=-a R, psi=(1+gain)R,
    # terminal target=-a R/(1+gain), relative target error=gain.
    R, Z = np.meshgrid(np.arange(1.0, 6.0), [-1.0, 0.0])
    result = compute_equilibrium(
        R, Z, lambda r: amplitude * (5.0 - r), R, -gain / amplitude * np.eye(R.size), maxiter=1
    )
    assert result.status == "maxiter"
    np.testing.assert_allclose(result.closure_residual, gain, rtol=1e-12, atol=1e-12)


def test_oversized_current_cannot_pass_target_relative_stopping_gate():
    R, Z = np.meshgrid(np.arange(1.0, 6.0), [-1.0, 0.0])
    result = compute_equilibrium(
        R, Z, lambda r: 5.0 - r, R, -4.0 * np.eye(R.size), maxiter=1, tol=2.0
    )
    assert result.residual < 2.0
    assert result.closure_residual > 2.0
    assert result.status == "maxiter"


@pytest.mark.parametrize("relax", [0.5, 0.999])
def test_stationary_flux_does_not_hide_current_closure_failure(relax):
    R, Z = np.meshgrid(np.arange(1.0, 6.0), [-1.0, 0.0])
    result = compute_equilibrium(
        R, Z, lambda r: 5.0 - r, R, np.zeros((R.size, R.size)), relax=relax, tol=1e-10, maxiter=1
    )
    assert result.residual == 0.0
    assert result.status == "maxiter"
    np.testing.assert_allclose(result.plas_currents, -(1 - relax) * R, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result.closure_residual, relax, rtol=1e-12, atol=1e-12)


def test_relaxed_analytic_closure_converges_at_original_tolerance():
    R, Z = np.meshgrid(np.arange(1.0, 6.0), [-1.0, 0.0])
    result = compute_equilibrium(R, Z, lambda r: 5.0 - r, R, np.zeros((R.size, R.size)), relax=0.5)
    assert result.status == "converged"
    assert result.iterations == 34
    np.testing.assert_allclose(result.closure_residual, 2.0**-34, rtol=1e-5, atol=1e-15)
    np.testing.assert_allclose(result.plas_currents, -R, rtol=1e-10, atol=1e-10)


def test_heldout_masked_decimal_grid_current_residual():
    R, Z = np.meshgrid(np.linspace(0.4, 1.6, 7), [-0.3, 0.0, 0.3])
    mask = np.zeros(R.shape, dtype=bool)
    mask[0, 2] = True
    result = compute_equilibrium(
        R,
        Z,
        lambda r: 1.6 - r,
        R,
        np.zeros((R.size, R.size)),
        relax=0.7,
        maxiter=4,
        plas_clip=mask,
        tol=1e-12,
    )
    expected = -R * 0.2 * 0.3 * (1 - 0.7**4)
    expected[mask] = 0.0
    assert result.status == "maxiter"
    assert result.iterations == 4
    np.testing.assert_allclose(result.plas_currents, expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result.closure_residual, 0.7**4, rtol=1e-12, atol=1e-12)


def test_nonfinite_pressure_derivative_is_not_silently_zeroed():
    R, Z = np.meshgrid(np.arange(1.0, 6.0), [-1.0, 0.0])
    with np.errstate(all="ignore"):
        result = compute_equilibrium(
            R, Z, lambda r: 5.0 - r, R * 1e-310, np.zeros((R.size, R.size))
        )
    assert result.status == "nonfinite"
    assert "pressure-current" in result.reason
