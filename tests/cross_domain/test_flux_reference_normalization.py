"""Direct bounded checks of radial references and pressure-current normalization."""

import numpy as np
import pytest

from cross_domain._flux_reference import (
    FULL_R,
    FULL_TARGETS,
    FULL_Z,
    RADIAL_R,
    RADIAL_SOURCE,
    RADIAL_Z,
    STEP_R,
    STEP_SOURCE,
    STEP_TARGET,
    STEP_Z,
    checked_full_flux,
    checked_loop_integral,
    full_currents,
)


@pytest.mark.parametrize("transpose", [False, True])
def test_nonzero_radial_reference_is_not_a_global_flux(transpose):
    expected_br = [
        float(checked_loop_integral(RADIAL_SOURCE, (RADIAL_R[0], z), "br")) for z in RADIAL_Z
    ]
    expected_bz = [
        float(checked_loop_integral(RADIAL_SOURCE, (RADIAL_R[0], z), "bz")) for z in RADIAL_Z
    ]

    from scirel.field import integrate_filament_vacuum_field, poloidal_field_from_flux

    r, z = np.meshgrid(RADIAL_R, RADIAL_Z)
    result = integrate_filament_vacuum_field(
        r.T if transpose else r, z.T if transpose else z, [RADIAL_SOURCE]
    )
    psi = result.psi.T if transpose else result.psi
    br = result.b_r.T if transpose else result.b_r
    bz = result.b_z.T if transpose else result.b_z
    recovered = poloidal_field_from_flux(r, z, psi)

    np.testing.assert_array_equal(psi[:, 0], 0.0)
    np.testing.assert_array_equal(recovered.B_R[:, 0], 0.0)
    assert all(value > 0 for value in expected_br)
    np.testing.assert_allclose(br[:, 0], expected_br, rtol=2e-12, atol=1e-20)
    np.testing.assert_allclose(bz[:, 0], expected_bz, rtol=2e-12, atol=1e-20)
    assert np.all(br[:, 0] > recovered.B_R[:, 0])


def test_real_pressure_step_has_independent_off_source_flux_amplitude():
    expected_psi = float(checked_loop_integral(STEP_SOURCE, STEP_TARGET, "psi"))

    from scirel.electromagnetism import get_gpsi
    from scirel.equilibrium import pressure_flux_picard_step

    r, z = np.meshgrid(STEP_R, STEP_Z)
    result = pressure_flux_picard_step(
        r,
        z,
        np.zeros_like(r),
        np.zeros_like(r),
        get_gpsi(r, z),
        [2.0, 0.0, 0.0, 0.0],
        1.0,
        None,
        0.0,
    )

    np.testing.assert_array_equal(result.plasma_currents, [1.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(result.psi_next[1, 1], expected_psi, rtol=2e-12, atol=1e-20)


@pytest.mark.parametrize("clipped", [False, True])
def test_real_pressure_graph_first_update_matches_independent_loop_sum(clipped):
    expected_current = np.array([float(value) for value in full_currents(clipped)]).reshape(3, 5)
    expected_flux = [float(checked_full_flux(target, clipped)) for target in FULL_TARGETS]

    from scirel.electromagnetism import get_gpsi
    from scirel.equilibrium import solve_isotropic_pressure_flux

    r, z = np.meshgrid(FULL_R, FULL_Z)
    vacuum = r**2 / 2
    mask = np.zeros_like(r, dtype=bool)
    mask[1, 1] = True
    result = solve_isotropic_pressure_flux(
        r,
        z,
        vacuum,
        get_gpsi(r, z),
        lambda radius: max(25 / 32 - radius**2 / 2, 0.0),
        tol=1e-14,
        maxiter=1,
        relax=0.0,
        plasma_mask=mask if clipped else None,
    )

    np.testing.assert_allclose(result["plasma_currents"], expected_current, rtol=2e-12, atol=1e-15)
    np.testing.assert_array_equal(result["plasma_currents"][:, -1], 0.0)
    assert np.all(result["plasma_currents"][:, -2] < 0.0)
    if clipped:
        assert result["plasma_currents"][1, 1] == 0.0
    increment = result["psi"] - vacuum
    np.testing.assert_allclose(
        [increment[2, 2], increment[2, 4]], expected_flux, rtol=2e-12, atol=5e-16
    )
    assert result["iterations"] == 1
    assert result["status"] == "maxiter"
    assert result["failure_reason"] == "maxiter_reached"
    assert not result["converged"]
    assert result["residual_history"].shape == (1,)
    assert result["closure_residual_history"].shape == (1,)
    assert np.isfinite(result["residual"]) and result["residual"] > 1e-14
    assert np.isfinite(result["closure_residual"])
