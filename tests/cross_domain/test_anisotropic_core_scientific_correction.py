"""Scientific regressions; initial failures and each added defect retain pre-fix evidence."""

import numpy as np
import pytest
from scirel.equilibrium.anisotropic_force_balance import compute_anisotropic_force_balance as force
from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux as update
from scirel.equilibrium.axisymmetric_anisotropic_picard import (
    solve_axisymmetric_anisotropic_picard as solve,
)
from scirel.equilibrium.anisotropic_picard_feedback import (
    update_anisotropic_picard_flux as feedback,
)
from scirel.equilibrium.free_boundary_anisotropic_picard import (
    solve_free_boundary_anisotropic_picard as free,
)
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as field
from scirel.closures.reduced_hall_drift import close_reduced_hall_drift as hall


@pytest.mark.parametrize("n", [9, 17, 33])
def test_exact_vacuum_tensor_equilibrium_axis(n):
    R, Z = np.meshgrid(np.linspace(0, 1, n), np.linspace(-0.5, 0.5, n))
    a, c = 0.2, 2.0
    br = a * R
    bz = c - 2 * a * Z
    b2 = br**2 + bz**2
    pp, pt = 10 + b2 / 2, 10 - b2 / 2
    f = force(R, Z, br, bz, pp, pt)
    assert np.max(np.abs(f["force_Z"])) < 1e-10
    assert np.max(np.abs(f["force_R"])) < 1e-10
    assert f["parallel_force_error"] < 0.05
    h = hall(
        R,
        Z,
        br,
        bz,
        pp,
        pt,
        {
            "ion_density": np.ones_like(R),
            "electron_pressure": np.zeros_like(R),
            "electrostatic_potential": np.zeros_like(R),
        },
        np.ones_like(R, dtype=bool),
        1.0,
        1.0,
        include_toroidal_inertia=False,
    )
    assert np.max(np.abs(h["force_Z"])) < 1e-10
    assert h["parallel_force_error"] < 0.05


@pytest.mark.parametrize("p", [0.1, 1.0, 3.0, 10.0])
@pytest.mark.parametrize("n", [5, 7, 9, 17])
def test_zero_force_not_rejected(p, n):
    R, Z = np.meshgrid(np.linspace(0.2, 0.6, n), np.linspace(-0.2, 0.2, n))
    f = force(R, Z, R * 0, R * 0 + 1, R * 0 + p, R * 0 + p)
    assert f["parallel_force_error"] == 0.0
    out = solve(
        r_grid=R,
        z_grid=Z,
        psi_vac=R**2 / 2,
        g_psi=np.zeros((R.size, R.size)),
        pressure_closure=lambda b, psi: {"p_parallel": p, "p_perpendicular": p},
        maxiter=2,
    )
    assert out["converged"]


def test_true_parallel_imbalance_still_rejected():
    R, Z = np.meshgrid(np.linspace(0.2, 0.6, 9), np.linspace(-0.2, 0.2, 9))
    with pytest.raises(ValueError, match="parallel"):
        solve(
            r_grid=R,
            z_grid=Z,
            psi_vac=R**2 / 2,
            g_psi=np.zeros((R.size, R.size)),
            pressure_closure=lambda b, psi: {"p_parallel": 3 + Z, "p_perpendicular": 3 + Z},
            maxiter=2,
        )


def test_nonuniform_compact_current_integral_converges():
    errors = []
    for n in [9, 17, 33]:
        R, Z = np.meshgrid(1 + np.linspace(0, 1, n) ** 2, np.linspace(-1, 1, n))
        j = (R - 1) ** 2 * (2 - R) ** 2 * (1 - Z**2) ** 2
        out = update(R, Z, j, R * 0, R * 0, np.zeros((R.size, R.size)), 0.0)
        errors.append(abs(np.sum(out["plasma_cell_currents"]) - 8 / 225))
    assert errors[-1] < 5e-5
    assert errors[1] < errors[0] / 3 and errors[2] < errors[1] / 3


def test_uniform_positive_radius_explicit_cells_preserved():
    R, Z = np.meshgrid(np.linspace(1, 2, 9), np.linspace(-1, 1, 9))
    out = update(
        R,
        Z,
        R,
        R * 0,
        R * 0,
        np.zeros((R.size, R.size)),
        0.0,
        cell_edges=(
            np.linspace(1 - 0.0625, 2 + 0.0625, 10),
            np.linspace(-1 - 0.125, 1 + 0.125, 10),
        ),
    )
    np.testing.assert_allclose(out["plasma_cell_currents"], R * 0.125 * 0.25, rtol=0, atol=0)


def test_feedback_without_field_greens_recovers_plasma_field():
    R, Z = np.meshgrid(np.linspace(1, 2, 5), np.linspace(-1, 1, 5))
    G = np.eye(R.size)
    out = feedback(R**2, R, Z, None, None, 0.0, G, None, None, R**2 / 2, R * 0, R * 0 + 1)
    delta = field(R, Z, out["psi"] - R**2 / 2)
    np.testing.assert_allclose(out["BZ"], 1 + delta["B_Z"], rtol=1e-12, atol=1e-12)


def test_free_boundary_flux_and_magnetic_correction_same_terminal_state():
    R, Z = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(0.1, 0.5, 5))
    sample = np.zeros((1, R.size))
    sample[0, 0] = 1
    response = (R**2 * (Z + 1)).ravel()[:, None]
    config = {
        "boundary_sample_matrix": sample,
        "green_boundary_to_boundary": sample @ response,
        "green_boundary_to_field": response,
    }
    out = free(
        r_grid=R,
        z_grid=Z,
        psi_vac=R**2 / 2,
        br_vac=R * 0,
        bz_vac=R * 0 + 1,
        g_psi=np.zeros((R.size, R.size)),
        params={},
        tol=1e-9,
        maxiter=3,
        relax=0.0,
        pressure_closure=lambda s: {
            "p_parallel": R * 0 + 3,
            "p_perp": R * 0 + 3,
            "density": None,
            "electron_temperature": None,
        },
        boundary_correction=config,
    )
    expected = field(R, Z, out["psi"])
    np.testing.assert_allclose(out["BR"], expected["B_R"], atol=1e-12, rtol=1e-12)
    np.testing.assert_allclose(out["BZ"], expected["B_Z"], atol=1e-12, rtol=1e-12)
    assert out["converged"]


def test_free_boundary_true_parallel_force_cannot_be_converged():
    R, Z = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(-0.2, 0.2, 5))
    with pytest.raises(ValueError, match="parallel"):
        free(
            r_grid=R,
            z_grid=Z,
            psi_vac=R**2 / 2,
            br_vac=R * 0,
            bz_vac=R * 0 + 1,
            g_psi=np.zeros((R.size, R.size)),
            params={},
            tol=1e-9,
            maxiter=3,
            relax=0.0,
            pressure_closure=lambda s: {
                "p_parallel": 3 + Z,
                "p_perp": 3 + Z,
                "density": None,
                "electron_temperature": None,
            },
        )


@pytest.mark.parametrize("n", [5, 9, 17, 33])
def test_linear_nodal_domain_integral_exact(n):
    R, Z = np.meshgrid(1 + np.linspace(0, 1, n) ** 2, 0.8 * np.linspace(0, 1, n) ** 1.5 - 0.4)
    out = update(R, Z, R, R * 0, R * 0, np.zeros((R.size, R.size)), 0.0)
    assert abs(np.sum(out["plasma_cell_currents"]) - 1.2) < 1e-14


@pytest.mark.parametrize("consistent", [True, False])
def test_hall_component_accounting_explicit(consistent):
    R, Z = np.meshgrid(np.linspace(1, 2, 5), np.linspace(-1, 1, 5))
    p = R * 0 + 3
    state = {
        "ion_density": R * 0 + 1,
        "electron_pressure": R * 0 + 1,
        "electrostatic_potential": R * 0,
        "ion_p_parallel": R * 0 + (2 if consistent else 1),
        "ion_p_perpendicular": R * 0 + (2 if consistent else 1),
    }
    out = hall(R, Z, R * 0, R * 0 + 1, p, p, state, R > 0, 1.0, 1.0, include_toroidal_inertia=False)
    assert out["species_pressure_sum_consistent"] is consistent
    np.testing.assert_array_equal(
        out["residual_stress_parallel_pa"], R * 0 + (0 if consistent else 1)
    )
    state["pressure_composition_mode"] = "species_sum"
    if not consistent:
        with pytest.raises(ValueError, match="species pressure sum"):
            hall(
                R, Z, R * 0, R * 0 + 1, p, p, state, R > 0, 1.0, 1.0, include_toroidal_inertia=False
            )


def test_retained_current_is_not_false_fixed_point():
    R, Z = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(-0.2, 0.2, 5))
    out = free(
        r_grid=R,
        z_grid=Z,
        psi_vac=R**2 / 2,
        br_vac=R * 0,
        bz_vac=R * 0 + 1,
        g_psi=np.eye(R.size) * 0.1,
        params={},
        tol=1e-9,
        maxiter=3,
        relax=1.0,
        pressure_closure=lambda s: {
            "p_parallel": 3 + R,
            "p_perp": 3 + R,
            "density": None,
            "electron_temperature": None,
        },
    )
    assert out["residual"] == 0.0
    assert out["fixed_point_residual"] > 1e-9
    assert not out["converged"]


def test_two_node_feedback_remains_supported_with_explicit_cells():
    R, Z = np.meshgrid([0.2, 0.4], [-0.1, 0.1])
    out = feedback(
        R * 0 + 1,
        R,
        Z,
        None,
        None,
        0.0,
        np.zeros((4, 4)),
        None,
        None,
        R**2 / 2,
        R * 0,
        R * 0 + 1,
        cell_edges=([0.1, 0.3, 0.5], [-0.2, 0.0, 0.2]),
    )
    np.testing.assert_allclose(out["plasma_currents"], 0.04, rtol=1e-15, atol=1e-15)
    np.testing.assert_array_equal(out["BZ"], R * 0 + 1)


def test_hall_primary_negative_pressure_rejected():
    R, Z = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(-0.2, 0.2, 5))
    with pytest.raises(ValueError, match="pressure"):
        hall(
            R,
            Z,
            R * 0,
            R * 0 + 1,
            R * 0 - 1,
            R * 0 - 1,
            {
                "ion_density": R * 0 + 1,
                "electron_pressure": R * 0,
                "electrostatic_potential": R * 0,
                "ion_p_parallel": R * 0 + 1,
                "ion_p_perpendicular": R * 0 + 1,
            },
            R > 0,
            1.0,
            1.0,
        )


@pytest.mark.parametrize("n", [7, 13, 29])
def test_constant_flux_gauge_has_exactly_zero_field(n):
    R, Z = np.meshgrid(np.linspace(0, 0.8, n), np.linspace(-0.2, 0.2, n))
    b = field(R, Z, R * 0 + 3.7)
    np.testing.assert_array_equal(b["B_R"], R * 0)
    np.testing.assert_array_equal(b["B_Z"], R * 0)


@pytest.mark.parametrize("n", [9, 17])
def test_resolvable_strong_flux_gauge_invariance(n):
    R, Z = np.meshgrid(np.linspace(0, 1, n) ** 2, np.linspace(-0.5, 0.5, n))
    psi = 0.5 * R**2 * (2 - 0.25 * Z)
    b = field(R, Z, psi)
    shifted = field(R, Z, psi + 2**16)
    np.testing.assert_allclose(shifted["B_R"], b["B_R"], atol=1e-12, rtol=1e-12)
    np.testing.assert_allclose(shifted["B_Z"], b["B_Z"], atol=1e-12, rtol=1e-12)


def test_hall_near_unit_relaxation_cannot_fake_local_convergence():
    R, Z = np.meshgrid(np.linspace(0.2, 1, 9), np.linspace(-1, 1, 9))
    p = 10 + R**2
    state = {"ion_density": R * 0 + 1, "electron_pressure": R * 0, "electrostatic_potential": R * 0}
    with pytest.raises(RuntimeError, match="inertia iteration did not converge"):
        hall(
            R,
            Z,
            R * 0,
            R * 0 + 1,
            p,
            p,
            state,
            R > 0,
            1.0,
            1.0,
            maximum_inertial_mach=10.0,
            inertia_relax=1 - 1e-12,
            inertia_tolerance=1e-10,
        )


def test_hall_analytic_local_fixed_point_uses_returned_current():
    R, Z = np.meshgrid(np.linspace(0.2, 1, 9), np.linspace(-1, 1, 9))
    p = 10 + R**2
    state = {"ion_density": R * 0 + 1, "electron_pressure": R * 0, "electrostatic_potential": R * 0}
    out = hall(
        R,
        Z,
        R * 0,
        R * 0 + 1,
        p,
        p,
        state,
        R > 0,
        1.0,
        1.0,
        maximum_inertial_mach=10.0,
        inertia_relax=0.5,
        inertia_tolerance=1e-10,
    )
    np.testing.assert_allclose(out["J_phi"], R, atol=1e-10, rtol=1e-10)
    assert out["inertia_converged"] and out["inertia_fixed_point_residual"] <= 1e-10
    assert np.max(abs(out["momentum_residual_R"])) < 1e-9
