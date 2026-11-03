"""Independent mathematics for the GPDF half-spectral initial-value problem."""

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.linalg import expm
from scirel.kinetic.vlasov_poisson import (
    vp_init,
    vp_distribution,
    vp_field,
    vp_rhs,
    vp_rk4_step,
    vp_evolve,
    vp_envelope,
    vp_diagnostic,
    solve_vlasov_poisson,
)


def test_poisson_and_rank_one_feedback_not_diagonal():
    v = np.array([-2.0, -0.5, 1.0, 3.0])
    g = np.array([0.2, 0.7, -0.5, -0.4])
    f = np.array([1.0 + 2j, 2.0, -1j, 3.0])
    k, dv = 0.4, 0.2
    field = vp_field(f, k, dv)
    assert_allclose(1j * k * field, -dv * np.sum(f))
    matrix = -1j * k * np.diag(v) + (1j * dv / k) * np.outer(g, np.ones(v.size))
    assert_allclose(vp_rhs(f, field, v, g, k), matrix @ f)
    # A perturbation at one node changes the force at every nonzero g node.
    shifted = f.copy()
    shifted[0] += 1
    difference = vp_rhs(shifted, vp_field(shifted, k, dv), v, g, k) - vp_rhs(f, field, v, g, k)
    assert_allclose(difference[1:], 1j * dv / k * g[1:])


def test_initial_constraint_and_source_defaults():
    s = vp_init()
    assert s["nv"] == 2048 and s["nt"] == 2000 and s["dt"] == 0.01
    assert s["vv"].shape == (2049,)
    assert_allclose(s["dv"], 40 / 2048)
    assert_allclose(s["dE"], vp_field(s["df"], s["k"], s["dv"]))
    assert not np.isclose(s["dE"], 0.01)
    assert_allclose(s["wr"], 1)
    assert_allclose(s["wi"], -0.15 * np.sqrt(2))


@pytest.mark.parametrize("selector", [1, 2, 3, 4])
def test_distribution_symmetry_and_finite(selector):
    v = np.linspace(-20, 20, 2049)
    g, _, _ = vp_distribution(v, selector)
    assert np.isfinite(g).all()
    assert_allclose(g, -g[::-1], atol=1e-15)


def test_kappa_derivative_independent_central_difference():
    from scipy.special import gamma

    v = np.array([-0.9, 0.3, 1.8])
    kap = 2.5
    h = 1e-5
    A = gamma(kap) / (gamma(kap - 0.5) * np.sqrt(np.pi * kap) * np.sqrt(2))
    f = lambda x: A * (1 + x * x / (2 * kap)) ** (-kap)
    got, _, _ = vp_distribution(v, 2, kappa=kap)
    assert_allclose(got, (f(v + h) - f(v - h)) / (2 * h), rtol=2e-9, atol=2e-12)


def test_rk4_fourth_order_against_dense_exponential():
    s = vp_init(nv=20, nt=1, dt=0.02)
    v, g = s["vv"], s["df0dv"]
    k, dv = s["k"], s["dv"]
    matrix = -1j * k * np.diag(v) + (1j * dv / k) * np.outer(g, np.ones(v.size))
    errors = []
    for steps in (2, 4):
        f = s["df"].copy()
        E = s["dE"]
        dt = 0.4 / steps
        for _ in range(steps):
            f, E = vp_rk4_step(f, E, v, g, k, dv, dt)
        errors.append(np.linalg.norm(f - expm(0.4 * matrix) @ s["df"]))
        assert_allclose(E, vp_field(f, k, dv), atol=1e-15)
    assert 14 < errors[0] / errors[1] < 18


def test_unclosed_incoming_field_is_explicitly_rejected():
    s = vp_init(nv=16)
    with pytest.raises(ValueError, match="Poisson"):
        vp_rk4_step(s["df"], 0.01, s["vv"], s["df0dv"], s["k"], s["dv"], s["dt"])


def test_evolve_is_nonmutating_and_free_streaming_analytic():
    s = vp_init(nv=32, nt=20, dt=0.005)
    s["df0dv"] = np.zeros_like(s["vv"])
    initial = s["df"].copy()
    out = vp_evolve(s)
    assert_allclose(s["df"], initial)
    assert_allclose(
        out["df"], initial * np.exp(-1j * s["k"] * s["vv"] * 0.1), rtol=2e-10, atol=1e-13
    )
    assert out["dEt"].shape == (21,)
    assert_allclose(out["dEt"][-1], out["dE"])


def test_diagnostic_log_magnitude_and_correct_time_indices():
    t = np.linspace(0, 40, 4001)
    E = np.exp(-0.13 * t) * np.cos(1.7 * t)
    envelope = vp_envelope(E, t, wr=1.7, wi=-0.13)
    assert len(envelope["lndE"]) == len(t)
    diagnostic = vp_diagnostic(E, t, start=0, end=40)
    assert_allclose(diagnostic["omega"], 1.7, rtol=8e-4)
    assert_allclose(diagnostic["gamma"], -0.13, atol=2e-5)
    assert_allclose(envelope["lndE"], np.log(np.abs(E)))
    with pytest.raises(ValueError, match="two"):
        vp_diagnostic(np.ones(20), np.arange(20))


@pytest.mark.parametrize("selector", [1, 2, 3, 4])
def test_default_full_grid_and_steps(selector):
    out = solve_vlasov_poisson(Fn=selector)
    s = out["state"]
    assert s["df"].shape == (2049,) and s["dEt"].shape == (2001,)
    assert np.isfinite(s["dEt"]).all()
    assert_allclose(s["dE"], vp_field(s["df"], s["k"], s["dv"]), atol=1e-14)


def test_slowing_down_weak_cutoff_integration_by_parts():
    from scipy.integrate import quad

    v = np.linspace(-6, 6, 96001)
    dv = v[1] - v[0]
    g, _, _ = vp_distribution(v, 4)
    vt = np.sqrt(2)
    A = 3 * np.sqrt(3) * vt * vt / (4 * np.pi)
    # phi=sin(.7v); distributional derivative pairs to -integral f phi'.
    expected = -quad(
        lambda x: A / (abs(x) ** 3 + vt**3) * 0.7 * np.cos(0.7 * x), -4, 4, epsabs=1e-12
    )[0]
    assert_allclose(dv * np.dot(g, np.sin(0.7 * v)), expected, atol=2e-9)
    smooth, _, _ = vp_distribution(v, 4, cutoff_mode="smooth")
    jump = A / (4**3 + vt**3)
    assert_allclose(dv * np.sum(g - smooth), 0, atol=1e-15)
    assert_allclose(dv * np.dot(g - smooth, v), -8 * jump, atol=1e-12)
    assert abs(dv * np.dot(smooth, np.sin(0.7 * v)) - expected) > 0.005


def test_slowing_down_off_node_cutoff_deposition():
    v = np.linspace(-6, 6, 82)
    dv = v[1] - v[0]
    g, _, _ = vp_distribution(v, 4)
    smooth, _, _ = vp_distribution(v, 4, cutoff_mode="smooth")
    jump = 3 * np.sqrt(3) * 2 / (4 * np.pi) / (64 + np.sqrt(2) ** 3)
    assert_allclose(dv * np.dot(g - smooth, v), -8 * jump, atol=1e-14)
    assert np.count_nonzero(np.abs(g - smooth) > 1e-15) == 4
    with pytest.raises(ValueError, match="uniform"):
        vp_distribution(np.array([-5.0, -4.0, 1.0, 4.0, 5.0]), 4)


def test_envelope_and_peak_diagnostic_are_fourier_phase_invariant():
    t = np.linspace(0, 30, 3001)
    field = np.exp(-0.12 * t) * np.cos(1.4 * t)
    reference = vp_envelope(field, t)["lndE"]
    reference_diagnostic = vp_diagnostic(field, t)
    for phase in (1j, np.exp(0.71j)):
        shifted = phase * field
        assert_allclose(vp_envelope(shifted, t)["lndE"], reference, atol=2e-15)
        result = vp_diagnostic(shifted, t)
        assert_allclose(result["omega"], reference_diagnostic["omega"], atol=1e-15)
        assert_allclose(result["gamma"], reference_diagnostic["gamma"], atol=1e-15)


def test_vp_nonrepresentable_derived_values_fail_explicitly():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(FloatingPointError):
            vp_field(np.array([1e308, 1e308]), 1.0, 1.0)
        with pytest.raises(FloatingPointError):
            vp_rhs(np.array([1e308, 1e308]), 1.0, [10.0, 20.0], [1.0, -1.0], 1.0)


def test_slowing_down_smooth_cutoff_has_exact_zero_far_tail():
    # Outside the hard cutoff the derivative is exactly zero, even at huge
    # finite velocity. Do not mistake an unused inf/inf intermediate for a
    # physically nonrepresentable result, or demand failure for exact zeros.
    with np.errstate(over="raise", invalid="raise"):
        g, _, _ = vp_distribution(np.array([-1e308, 0.0, 1e308]), 4, cutoff_mode="smooth")
    assert_allclose(g, np.zeros(3), atol=0, rtol=0)
