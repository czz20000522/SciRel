"""D2 counterexamples: independent analytic oracles, not old-output parity."""

import math
import numpy as np
import pytest
from scipy.integrate import quad
from scirel.mirror.mirror_invariant_distribution import (
    evaluate_mirror_invariant_distribution as distribution,
)
from scirel.mirror.mirror_constrained_moments import evaluate_mirror_constrained_moments as moments
from scirel.mirror.mirror_ambipolar_potential import solve_mirror_ambipolar_potential as end_loss
from scirel.closures.hall_two_fluid_pressure import close_hall_two_fluid_pressure as hall
from scirel.mirror.mirror_total_pressure import assemble_mirror_total_pressure as total

E = 1.602176634e-19
M = 1.67262192369e-27


def test_extreme_finite_downhill_barrier_has_finite_flux():
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        result = end_loss(
            1.0, 1 / 101, 0.0, M, E, 1.0, E, 101 * E, E, mode="evaluate", phi_plug_v=1000.0
        )
    expected = math.exp(-10) * 100 / 99 * math.sqrt(E / (2 * math.pi * M))
    np.testing.assert_allclose(result["ion_particle_flux_m2_s"], expected, rtol=2e-13)
    assert np.isfinite(result["relative_current_residual"])
    assert result["current_balance_solved"] is False


@pytest.mark.parametrize("R", [1.000001, 1.1, 2.0, 10.0, 100.0, 1e4, 1e8])
@pytest.mark.parametrize("order", [8, 32, 64])
def test_trapped_isotropic_moments_match_pitch_angle_integrals(R, order):
    result = moments(
        1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        b_plug_left_t=R,
        b_plug_right_t=R,
        quadrature_order=order,
    )
    xi = math.sqrt((R - 1) / R)
    got = [result[k] for k in ("density_m3", "p_parallel_pa", "p_perpendicular_pa")]
    np.testing.assert_allclose(got, [xi, xi**3, 0.5 * xi * (3 - xi**2)], rtol=2e-11, atol=2e-14)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"v_parallel_m_s": np.nan},
        {"v_perpendicular_m_s": np.inf},
        {"b_t": np.inf},
        {"psi": np.nan},
        {"potential_v": np.inf},
    ],
)
def test_nonfinite_local_invariant_inputs_are_rejected(kwargs):
    args = dict(
        v_parallel_m_s=1.0,
        v_perpendicular_m_s=1.0,
        b_t=1.0,
        psi=0.0,
        potential_v=0.0,
        mass_kg=1.0,
        charge_c=1.0,
        density_ref_m3=1.0,
        temperature_parallel_j=1.0,
        temperature_perpendicular_ref_j=1.0,
        b_ref_t=1.0,
    )
    with pytest.raises((ValueError, FloatingPointError)):
        distribution(**{**args, **kwargs})


def test_hall_independent_fit_residual_is_explicit_and_species_sum_is_enforced():
    law = lambda b, p: {
        "p_parallel": np.full_like(b, 10.0),
        "p_perpendicular": np.full_like(b, 12.0),
    }
    result = hall(
        np.ones(2),
        np.zeros(2),
        law,
        1.0,
        2.0,
        0.0,
        ion_p_parallel_pa=3.0,
        ion_p_perpendicular_pa=4.0,
    )
    assert result["pressure_composition_mode"] == "independent_fit"
    np.testing.assert_array_equal(result["residual_stress_parallel_pa"], 5.0)
    np.testing.assert_array_equal(result["residual_stress_perpendicular_pa"], 6.0)
    assert not result["species_pressure_sum_consistent"]
    with pytest.raises(ValueError, match="species"):
        hall(
            np.ones(2),
            np.zeros(2),
            law,
            1.0,
            2.0,
            0.0,
            ion_p_parallel_pa=3.0,
            ion_p_perpendicular_pa=4.0,
            pressure_composition_mode="species_sum",
        )
    exact = hall(
        np.ones(2), np.zeros(2), law, 1.0, 2.0, 0.0, pressure_composition_mode="species_sum"
    )
    assert exact["species_pressure_sum_consistent"]
    np.testing.assert_array_equal(exact["residual_stress_parallel_pa"], 0.0)


@pytest.mark.parametrize("bad", [-1.0, np.nan, np.inf])
def test_total_pressure_rejects_invalid_density(bad):
    with pytest.raises(ValueError, match="density"):
        total(
            {"p_parallel_pa": 1.0, "p_perpendicular_pa": 1.0, "density_m3": bad},
            {
                "electron_density_m3": 1.0,
                "electron_pressure_pa": 1.0,
                "relative_charge_residual": 0.0,
            },
        )


@pytest.mark.parametrize(
    "barriers",
    [
        (2.0, 0.3, 4.0, -0.5),
        (-0.8, 2.0, 2.0, 1.0),
        (0.01, -0.002, 30.0, -1.0),
        (1000.0, 0.1, 20.0, 2.0),
    ],
)
def test_general_barriers_against_independent_parallel_velocity_integral(barriers):
    a, b, c, d = barriers
    result = moments(
        1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        b_plug_left_t=1 + a,
        b_plug_right_t=1 + c,
        phi_plug_left_v=b,
        phi_plug_right_v=d,
    )

    # Reverse the order of integration: z=v_parallel/sqrt(2T/m), then
    # analytically integrate perpendicular exp(-x) between barrier constraints.
    def x_bounds(z):
        low, high = 0.0, np.inf
        for slope, intercept in [(a, b), (c, d)]:
            if slope > 0:
                low = max(low, (z * z - intercept) / slope)
            elif slope < 0:
                high = min(high, (z * z - intercept) / slope)
            elif z * z >= intercept:
                return 0.0, 0.0
        return low, max(low, high)

    def integrand(z, kind):
        lo, hi = x_bounds(z)
        if hi <= lo:
            return 0.0
        upper = 0.0 if np.isinf(hi) else math.exp(-hi)
        density = math.exp(-lo) - upper
        if kind == 2:
            density = (lo + 1) * math.exp(-lo) - (0.0 if np.isinf(hi) else (hi + 1) * upper)
        return (
            2 / math.sqrt(math.pi) * math.exp(-z * z) * density * (2 * z * z if kind == 1 else 1.0)
        )

    values = [
        quad(lambda z: integrand(z, k), 0, np.inf, epsabs=2e-12, epsrel=2e-11, limit=300)[0]
        for k in range(3)
    ]
    np.testing.assert_allclose(
        [
            result[k]
            for k in (
                "density_pitch_integral",
                "parallel_pitch_integral",
                "perpendicular_pitch_integral",
            )
        ],
        values,
        rtol=2e-9,
        atol=2e-11,
    )


@pytest.mark.parametrize("n_ref,voltage", [(1e-300, 800.0), (1e300, -800.0)])
def test_boltzmann_normalization_does_not_clip_representable_density(n_ref, voltage):
    from scirel.closures.boltzmann_quasineutrality import (
        compute_boltzmann_electron_state as electron,
    )

    expected = math.exp(math.log(n_ref) + voltage)
    state = electron(voltage, E, n_ref, 0.0, expected, 1.0)
    np.testing.assert_allclose(state["electron_density_m3"], expected, rtol=3e-13)
    assert abs(state["logarithmic_charge_residual"]) < 3e-13
    assert abs(state["relative_charge_residual"]) < 3e-13


def test_boltzmann_relative_residual_avoids_sum_overflow_and_underflow_false_root():
    from scirel.closures.boltzmann_quasineutrality import (
        compute_boltzmann_electron_state as electron,
    )

    with np.errstate(all="raise"):
        large = electron(0.0, 1e-300, 1e308, 0.0, 5e307, 1.0)
        tiny = electron(-800.0, E, 1e-100, 0.0, 1e-300, 1.0)
        empty = electron(0.0, E, 0.0, 0.0, 0.0, 1.0)
    np.testing.assert_allclose(large["relative_charge_residual"], -1 / 3, atol=3e-14)
    assert tiny["logarithmic_charge_residual"] > 300.0
    assert tiny["relative_charge_residual"] == 1.0
    assert empty["logarithmic_charge_residual"] == 0.0
    assert empty["relative_charge_residual"] == 0.0


def test_barrier_integral_subnormal_crossing_has_finite_limit():
    from scirel.mirror._mirror_numerics import _barrier_log_integral

    value = _barrier_log_integral(-1e308, 1e-300)
    assert value == 0.0


def test_total_pressure_broadcasts_valid_observational_potential():
    potential = np.array([1.0, 2.0])
    state = total(
        {"p_parallel_pa": [2.0], "p_perpendicular_pa": [3.0], "density_m3": [1.0]},
        {
            "electron_density_m3": [1.0],
            "electron_pressure_pa": [1.0],
            "relative_charge_residual": [0.0],
            "electrostatic_potential": potential,
        },
    )
    np.testing.assert_array_equal(state["p_parallel"], [3.0, 3.0])
    assert state["electrostatic_potential"] is potential


@pytest.mark.parametrize("poison", ["nonconverged", "wrong_final_state"])
def test_quasineutral_composition_checks_actual_terminal_state(poison):
    from scirel.mirror.mirror_quasineutral_closure import _run_composition
    from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state
    from scirel.closures.quasineutral_reference_density import compute_reference_electron_density

    deps = {
        "scirel.mirror.mirror_constrained_moments": moments,
        "scirel.closures.boltzmann_quasineutrality": compute_boltzmann_electron_state,
        "scirel.closures.quasineutral_reference_density": compute_reference_electron_density,
        "scirel.mirror.mirror_total_pressure": total,
    }

    def fake(*args, **kwargs):
        if poison == "nonconverged":
            return {"potential_v": np.asarray(0.0), "iterations": 1, "converged": False}
        return {"potential_v": np.asarray(10.0), "iterations": 1, "converged": True}

    deps["scirel.closures.quasineutral_potential"] = fake
    inputs = dict(
        b_t=1.0,
        psi=0.0,
        mass_kg=M,
        charge_c=E,
        density_ref_m3=1.0,
        temperature_parallel_j=E,
        temperature_perpendicular_ref_j=E,
        b_ref_t=1.0,
        electron_temperature_j=E,
    )
    with pytest.raises(RuntimeError, match="terminal"):
        _run_composition(inputs, asset_loader=deps.__getitem__)


def test_boltzmann_pressure_is_retained_when_density_underflows():
    from scirel.closures.boltzmann_quasineutrality import (
        compute_boltzmann_electron_state as electron,
    )

    state = electron(-800.0 * 1e100 / E, 1e100, 1.0, 0.0, 0.0, 1.0)
    assert state["electron_density_m3"] == 0.0
    np.testing.assert_allclose(
        state["electron_pressure_pa"], math.exp(-800 + math.log(1e100)), rtol=3e-13
    )
    assert state["relative_charge_residual"] == -1.0
    assert state["logarithmic_charge_residual"] < 0


@pytest.mark.parametrize("refill", [0.0, 0.2, 1.0])
def test_general_moment_refinement_and_refill(refill):
    common = dict(
        b_t=1.0,
        psi=0.0,
        potential_v=0.0,
        mass_kg=1.0,
        charge_c=1.0,
        density_ref_m3=1.0,
        temperature_parallel_j=1.0,
        temperature_perpendicular_ref_j=1.0,
        b_ref_t=1.0,
        b_plug_left_t=0.2,
        b_plug_right_t=3.0,
        phi_plug_left_v=2.0,
        phi_plug_right_v=1.0,
        loss_cone_refill=refill,
    )
    results = [moments(**common, quadrature_order=order) for order in (8, 32, 64)]
    for key in ("density_m3", "p_parallel_pa", "p_perpendicular_pa"):
        np.testing.assert_allclose(
            [r[key] for r in results], results[-1][key], rtol=2e-11, atol=2e-13
        )
        if refill == 1.0:
            np.testing.assert_allclose(results[0][key], 1.0, rtol=2e-14)


def test_grid_rejects_endpoint_evaluation_in_place_of_requested_balance():
    from scirel.mirror.grid_mirror_kinetic_closure import _run_composition
    from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile

    R, Z = np.meshgrid([0.0, 1.0], [-1.0, 0.0, 1.0])

    def endpoint(*args, **kwargs):
        return {"potential_v": np.zeros(2), "converged": True, "current_balance_solved": False}

    deps = {
        "scirel.geometry.flux_surface_profile": evaluate_flux_surface_profile,
        "scirel.mirror.mirror_ambipolar_potential": endpoint,
    }

    def nested(_):
        raise AssertionError("nested closure ran after unsolved endpoint")

    inputs = dict(
        r_grid=R,
        z_grid=Z,
        b_t=1 + Z * Z,
        psi=R * R,
        mass_kg=M,
        charge_c=E,
        density_ref_m3=1.0,
        temperature_parallel_j=E,
        temperature_perpendicular_ref_j=E,
        electron_temperature_j=E,
        reference_z=0.0,
        plug_left_z=-1.0,
        plug_right_z=1.0,
        plug_potential_mode="ambipolar_end_loss",
        loss_cone_refill=0.1,
    )
    with pytest.raises(RuntimeError, match="endpoint"):
        _run_composition(inputs, asset_loader=deps.__getitem__, composition_loader=nested)


def test_trapped_pressure_scales_before_rounding_intermediate_product():
    # All requested final fields are representable, although n_full*T_parallel
    # alone is not. The constant electrostatic barrier has an analytic gamma
    # fraction, and T_perp differs from T_parallel without changing B.
    tiny = 1e-134
    state = moments(
        1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1e300,
        1e100,
        1e-100,
        1.0,
        b_plug_left_t=1.0,
        b_plug_right_t=1.0,
        phi_plug_left_v=1e-34,
        phi_plug_right_v=1e-34,
    )
    parallel = math.exp(
        math.log(1e300)
        + math.log(1e100)
        + math.log(4 / (3 * math.sqrt(math.pi)))
        + 1.5 * math.log(tiny)
    )
    density = math.exp(math.log(1e300) + math.log(2 / math.sqrt(math.pi)) + 0.5 * math.log(tiny))
    np.testing.assert_allclose(state["p_parallel_pa"], parallel, rtol=4e-12)
    np.testing.assert_allclose(state["density_m3"], density, rtol=4e-12)
