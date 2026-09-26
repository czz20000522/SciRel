"""Direct contract tests for the r65 terminal molecular diagnostics family.
Saved arms reproduced bit for bit on the declared domain; no repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    reduce_terminal_molecular_flux_velocity,
    reduce_terminal_molecular_pressure_temperature,
    reduce_terminal_molecular_heat_flux,
    reduce_terminal_molecular_energy_transfer,
    reduce_terminal_molecular_ion_state,
    reduce_qh2_total_conservation_diagnostic,
)


def _mesh(nvr=4, nvx=6, nx=5):
    vr = np.linspace(0.5, 2.0, nvr)
    vx = np.linspace(-1.5, 1.5, nvx)
    dvx = np.full(nvx, 0.5)
    weight = np.ones(nvr)
    return vr, vx, dvx, weight


def test_flux_velocity_reduction_returns_finite_profiles():
    vr, vx, dvx, weight = _mesh()
    dist = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))[:, :, None] * np.ones((4, 6, 3))
    result = reduce_terminal_molecular_flux_velocity(vx, 5000.0, dist, weight, dvx)
    assert set(result) == {"flux_profile_m2_s", "mean_velocity_profile_m_s"}
    assert result["flux_profile_m2_s"].shape == (3,)
    assert np.all(np.isfinite(result["flux_profile_m2_s"]))
    assert np.all(np.isfinite(result["mean_velocity_profile_m_s"]))


def test_flux_velocity_symmetric_input_gives_zero_flow():
    vr, vx, dvx, weight = _mesh()
    dist = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))[:, :, None] * np.ones((4, 6, 2))
    result = reduce_terminal_molecular_flux_velocity(vx, 5000.0, dist, weight, dvx)
    np.testing.assert_allclose(result["mean_velocity_profile_m_s"], np.zeros(2), atol=1e-12)


def test_flux_velocity_rejects_nonpositive_density():
    vr, vx, dvx, weight = _mesh()
    dist = np.zeros((4, 6, 2))
    with pytest.raises(ValueError, match="strictly positive density"):
        reduce_terminal_molecular_flux_velocity(vx, 5000.0, dist, weight, dvx)


def test_conservation_diagnostic_rejects_nonfinite():
    x = np.linspace(0, 1, 3)
    with pytest.raises(ValueError, match="finite"):
        reduce_qh2_total_conservation_diagnostic(
            x, np.full(3, np.nan), np.ones(3)
        )


def test_conservation_diagnostic_rejects_mismatched_shape():
    x = np.linspace(0, 1, 3)
    with pytest.raises(ValueError, match="finite one-dimensional"):
        reduce_qh2_total_conservation_diagnostic(
            x, np.ones(2), np.ones(3)
        )


def test_composition_heat_flux_energy_transfer_to_conservation_diagnostic():
    """Composition test: chain the heat flux and energy transfer outputs into
    the conservation diagnostic.  Uses compatible shared profiles (same nx=3,
    same velocity/spatial mesh) and checks that the diagnostic returns a
    finite [nx] error profile."""
    from scirel.kinetic import reduce_qh2_total_conservation_diagnostic
    vr = np.linspace(0.5, 2.0, 4)
    vx = np.linspace(-1.5, 1.5, 6)
    dvx = np.full(6, 0.5)
    weight = np.ones(4)
    nx = 3
    x = np.linspace(0.0, 1.0, nx)
    dist = np.exp(-(vr[:, None]**2 + vx[None, :]**2))[:, :, None] * np.ones((4, 6, nx))
    heat = reduce_terminal_molecular_heat_flux(vr, vx, 2.0, 5000.0, dist, weight, dvx)
    et = reduce_terminal_molecular_energy_transfer(
        vr, vx, 2.0, 5000.0, dist, np.ones((4, 6, nx)), weight, dvx, np.ones(nx)
    )
    result = reduce_qh2_total_conservation_diagnostic(
        x, heat['total_heat_flux_profile_w_m2'],
        et['total_energy_transfer_rate_profile_w_m3'],
    )
    err = result['total_energy_conservation_error_profile_dimensionless']
    assert err.shape == (nx,)
    assert np.all(np.isfinite(err))
    assert np.all(err >= 0.0)


def test_conservation_diagnostic_analytic_oracle_linear_flux():
    """Analytic conservation oracle: for a linear total heat flux
    qx(x) = a*x + b with constant energy transfer Q = a, the divergence of qx
    equals Q, so the conservation error should be exactly zero."""
    a, b = 3.0, 10.0
    x = np.linspace(0.0, 1.0, 11)
    qx = a * x + b
    q = np.full(11, a)
    result = reduce_qh2_total_conservation_diagnostic(x, qx, q)
    # The diagnostic computes q1 = diff(qx)/diff(x) = a at interior nodes,
    # and q2 = avg(Q[k], Q[k+1]) = a. So the error = |q1 - q2| / max(|q1|,|q2|) = 0.
    np.testing.assert_allclose(
        result['total_energy_conservation_error_profile_dimensionless'][:-1], 0.0, atol=1e-14
    )

