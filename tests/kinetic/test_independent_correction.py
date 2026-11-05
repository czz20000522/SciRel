"""Independent analytic and ODE oracles for the anisotropic D2 correction.

These contracts were frozen against the old code before receiver evaluation.
They do not use a source implementation as an answer generator.
"""

import math
import numpy as np
import pytest
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq
from scirel.equilibrium.anisotropic_force_balance import compute_anisotropic_force_balance
from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux
from scirel.closures.mirror_ambipolar_potential import solve_mirror_ambipolar_potential
from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state
from scirel.kinetic.mirror_constrained_moments import evaluate_mirror_constrained_moments
from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum


@pytest.mark.parametrize(
    "n,a,c,k,p0",
    [(13, 0.17, 2.8, 0.45, 11.0), (25, 0.11, 2.2, 0.65, 9.0), (49, 0.23, 3.1, 0.31, 7.0)],
)
def test_divergence_free_maxwell_stress_tensor_including_axis(n, a, c, k, p0):
    # curl B=div B=0 => div(BB - B²I/2)=0; the complete cylindrical axis limit is required.
    R, Z = np.meshgrid(np.linspace(0, 0.8, n), np.linspace(-0.35, 0.35, n))
    br = a * R
    bz = c - 2 * a * Z
    b2 = br**2 + bz**2
    v = compute_anisotropic_force_balance(R, Z, br, bz, p0 + k * b2 / 2, p0 - k * b2 / 2)
    for name in ["force_R", "force_Z"]:
        np.testing.assert_allclose(v[name], 0.0, rtol=0.0, atol=3e-10)


@pytest.mark.parametrize("n", [13, 25, 49])
def test_nonuniform_declared_nodal_domain_current_integral(n):
    r = 1 + np.linspace(0, 1, n) ** 2
    z = -0.4 + 0.8 * np.linspace(0, 1, n) ** 1.3
    R, Z = np.meshgrid(r, z)
    zero = np.zeros_like(R)
    v = update_axisymmetric_picard_flux(R, Z, R, zero, zero, np.zeros((R.size, R.size)), 0.0)
    np.testing.assert_allclose(v["plasma_cell_currents"].sum(), 1.2, rtol=0.0, atol=2e-13)


@pytest.mark.parametrize("n", [7, 14, 29])
def test_constant_pressure_and_flux_have_exact_zero_derivatives(n):
    R, Z = np.meshgrid(np.linspace(0, 0.8, n), np.linspace(-0.2, 0.2, n))
    zero = np.zeros_like(R)
    v = compute_anisotropic_force_balance(
        R, Z, zero, np.full_like(R, 1.7), np.full_like(R, 3.7), np.full_like(R, 3.7)
    )
    for name in ["force_R", "force_Z", "parallel_force_error"]:
        np.testing.assert_array_equal(v[name], np.zeros_like(v[name]))
    b = poloidal_field_from_flux(R, Z, np.full_like(R, 3.7))
    for name in ["B_R", "B_Z", "B"]:
        np.testing.assert_array_equal(b[name], np.zeros_like(R))


@pytest.mark.parametrize(
    "magnitude,turn", [(80.0, 10.0), (100.0, 10.0), (73.0, 9.0), (121.0, 7.5), (5.0, 0.2)]
)
def test_finite_end_loss_flux_against_bounded_direct_integral(magnitude, turn):
    q = 1.602176634e-19
    mass = 1.67262192369e-27
    b = magnitude * turn
    integral = quad(
        lambda x: math.exp(-x - max(0.0, b - magnitude * x)), 0, turn, epsabs=2e-15, epsrel=2e-13
    )[0] + math.exp(-turn)
    expected = math.sqrt(q / (2 * math.pi * mass)) * integral
    v = solve_mirror_ambipolar_potential(
        1.0,
        1 / (magnitude + 1),
        0.0,
        mass,
        q,
        1.0,
        q,
        (magnitude + 1) * q,
        q,
        mode="evaluate",
        phi_plug_v=b,
    )
    np.testing.assert_allclose(v["ion_particle_flux_m2_s"], expected, rtol=3e-12, atol=2e-14)


@pytest.mark.parametrize("ratio", [1.0001, 1.07, 1.8, 7.0, 33.0, 100.0, 137.0, 1000.0])
def test_isotropic_trapped_moments_against_pitch_integrals(ratio):
    xi = math.sqrt(1 - 1 / ratio)
    v = evaluate_mirror_constrained_moments(
        1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, b_plug_left_t=ratio, b_plug_right_t=ratio
    )
    for field, expected in [
        ("density_m3", xi),
        ("p_parallel_pa", xi**3),
        ("p_perpendicular_pa", (3 * xi - xi**3) / 2),
    ]:
        np.testing.assert_allclose(v[field], expected, rtol=2e-10, atol=3e-12)


@pytest.mark.parametrize("xend,count", [(1 / math.sqrt(3), 3), (0.43, 3), (0.67, 4), (0.88, 3)])
def test_ordered_spectrum_against_independent_regular_shooting(xend, count):
    # Direct y,y' evolution in xi; independent of phase integration and special-function degree formulas.
    def endpoint(w):
        sol = solve_ivp(
            lambda x, y: (y[1], (2 * x * y[1] - w * w * y[0]) / (1 - x * x)),
            (0, xend),
            (1.0, 0.0),
            method="DOP853",
            rtol=2e-12,
            atol=2e-14,
        )
        assert sol.success
        return float(sol.y[0, -1])

    roots = []
    left = 0.0001
    fleft = endpoint(left)
    step = 0.12 * math.pi / math.asin(xend)
    while len(roots) < count:
        right = left + step
        fright = endpoint(right)
        if fright * fleft < 0:
            roots.append(brentq(endpoint, left, right, xtol=1e-12, rtol=1e-13) ** 2)
        left = right
        fleft = fright
    v = solve_loss_cone_spectrum(xend, count, grid_points=400)
    np.testing.assert_allclose(v["eigenvalues"], roots, rtol=3e-9, atol=2e-10)
    np.testing.assert_allclose(v["eigenfunctions"][0], 1.0, rtol=0, atol=3e-12)
    assert np.all(np.diff(v["eigenvalues"]) > 0)


@pytest.mark.parametrize(
    "exponent,nref", [(800.0, 1e-300), (-800.0, 1e300), (710.0, 1e-100), (-720.0, 1e100)]
)
def test_boltzmann_density_and_residual_use_unclipped_combined_log(exponent, nref):
    q = 1.602176634e-19
    expected_log = math.log(nref) + exponent
    v = compute_boltzmann_electron_state(exponent, q, nref, 0.0, 1.0, 1.0)
    np.testing.assert_allclose(
        v["electron_density_m3"], math.exp(expected_log), rtol=3e-13, atol=0.0
    )
    np.testing.assert_allclose(
        v["logarithmic_charge_residual"], -expected_log, rtol=3e-14, atol=2e-13
    )
    np.testing.assert_allclose(
        v["relative_charge_residual"], math.tanh(-expected_log / 2), rtol=3e-14, atol=2e-15
    )


@pytest.mark.parametrize("lower", [0.0, 0.25, 0.7])
def test_common_population_angular_moments_and_reachable_orbits(lower):
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    b = np.array([[0.35, 0.7, 1.0, 1.4, 2.2, 3.0]])
    mirror = 3.0
    c = np.sqrt(1 - 1 / mirror)
    hi = np.sqrt(np.maximum(0.0, 1 - b / mirror))
    lo = np.sqrt(np.maximum(0.0, 1 - b))
    x = evaluate_frank_egedal_hot_ion_moments(
        b,
        {
            "B0": 1.0,
            "mirror_ratio": mirror,
            "vc_over_v0": 0.25,
            "velocity_lower": lower,
            "quadrature_rtol": 1e-9,
        },
        [0.0],
        [1.0],
        15,
        lambda degree, xi, terms: np.ones_like(xi),
    )
    np.testing.assert_allclose(x["hot_density_shape"], (hi - lo) / c, rtol=2e-10, atol=3e-12)
    np.testing.assert_allclose(
        x["hot_parallel_shape"], (hi**3 - lo**3) / c**3, rtol=2e-10, atol=3e-12
    )
    np.testing.assert_allclose(
        x["hot_perpendicular_shape"],
        (3 * (hi - lo) - (hi**3 - lo**3)) / (2 * c**3),
        rtol=2e-10,
        atol=3e-12,
    )


def test_relaxed_hall_iteration_must_not_hide_fixed_point_error():
    from scirel.closures.reduced_hall_drift import close_reduced_hall_drift

    r, z = np.meshgrid(np.linspace(0.2, 1.0, 9), np.linspace(-1.0, 1.0, 9))
    p = 10 + r * r
    o = np.ones_like(r)
    zero = np.zeros_like(r)
    with pytest.raises(RuntimeError, match="converge"):
        close_reduced_hall_drift(
            r,
            z,
            zero,
            o,
            p,
            p,
            {"ion_density": o, "electron_pressure": zero, "electrostatic_potential": zero},
            o.astype(bool),
            1.0,
            1.0,
            maximum_inertial_mach=10.0,
            inertia_relax=1 - 1e-12,
            inertia_tolerance=1e-10,
        )


def test_boltzmann_resolves_difference_before_multiplication():
    q = 1.602176634e-19
    ref = 1e20
    phi = np.nextafter(ref, np.inf)
    t = q * (phi - ref)
    x = compute_boltzmann_electron_state(phi, t, 1.0, ref, 1.0, 1.0)
    np.testing.assert_allclose(x["electron_density_m3"], np.exp(1.0), rtol=3e-13, atol=0.0)


def test_invariant_distribution_is_electrostatic_gauge_invariant():
    from scirel.kinetic.mirror_invariant_distribution import evaluate_mirror_invariant_distribution

    states = [
        evaluate_mirror_invariant_distribution(
            0.3, 0.4, 1.0, 0.0, shift, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, phi_ref_v=shift
        )
        for shift in [0.0, 1e20]
    ]
    np.testing.assert_allclose(states[1]["f0_s3_m6"], states[0]["f0_s3_m6"], rtol=3e-13, atol=0.0)


def test_trapped_occupation_is_electrostatic_gauge_invariant():
    from scirel.kinetic.mirror_invariant_distribution import evaluate_mirror_invariant_distribution

    states = [
        evaluate_mirror_invariant_distribution(
            0.2,
            1.0,
            1.0,
            0.0,
            shift,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            phi_ref_v=shift,
            b_plug_left_t=2.0,
            b_plug_right_t=2.0,
            phi_plug_left_v=shift,
            phi_plug_right_v=shift,
        )
        for shift in [0.0, 1e20]
    ]
    assert states[0]["occupation"] == 1.0 and states[1]["occupation"] == 1.0
    np.testing.assert_allclose(states[1]["f0_s3_m6"], states[0]["f0_s3_m6"], rtol=3e-13, atol=0.0)
