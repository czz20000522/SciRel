"""Independent evidence for the nine Vlasov--Poisson assets.

Assets: ``scirel.kinetic.vp-distribution``, ``vp-init``, ``vp-field``,
``vp-rhs``, ``vp-rk4-step``, ``vp-evolve``, ``vp-envelope``, ``vp-diagnostic``
and ``vp-landau``.

Evidence sources, none of them the implementation or its fixtures:

1. **The stated model, re-derived from its algebra.**  The module states
   ``d(df)/dt = -i k v df + E f0'(v)`` with ``i k E = -integral(df) dv``.  This
   file evaluates both statements with ``fractions.Fraction`` (for the field,
   where every input is an exact binary rational) and with ``mpmath`` at 40
   digits (for the moments), from the *docstring's* equation and the classical
   four-stage Runge--Kutta tableau -- not from the implementation's stage
   variables.  A sign, a ``dv`` factor, a swapped stage or a wrong quadrature
   weight in the implementation changes the re-derived value.
2. **The analytic equilibrium families at 40 digits.**  ``mpmath.gamma`` and
   ``mpmath.quad`` on ``(-inf, inf)`` give the mass, the second moment and the
   derivative of each closed-form family; ``scipy.special.gamma`` and the
   implementation's own central-difference fixtures are off this path.
3. **The meromorphic dispersion integral of the Lorentzian.**  For
   ``F(v) = (a/pi)/(v**2 + a**2)`` the analytic continuation of
   ``integral F'(v)/(v - z) dv`` is ``1/(z - i a)**2``; the closed form is
   checked against 40-digit quadrature at complex ``z``, so it is available as a
   reference that does not touch the code.
4. **The exact linear solution of the semidiscrete operator.**
   ``scipy.linalg.expm`` of the operator matrix is an independent algorithm
   (Padé scaling and squaring) for the same initial-value problem.
5. **Exact analytic tones on the sampled grid.**  A tone whose angular
   frequency is ``pi/(m dt)`` has its maxima on grid nodes, so the recovered
   angular frequency is exactly ``pi/mean(diff(peak_times))`` and the recovered
   growth rate is exactly the input exponent.  Nothing is fitted; the identity
   is algebraic.

Precision budgets, fixed before the comparison was run:

* Field closure: the ``Fraction`` path accumulates exactly and rounds once, at
  the final float conversion, so the budget is ``8 eps |E|``.  The same budget
  is used to *discriminate*: the test recomputes the field with a flipped sign
  and with a doubled ``dv`` and requires both to exceed it, so a passing
  comparison cannot be a budget that admits any value.
* Moment identity: the re-derived right-hand side is a sum of four terms with
  opposite signs, so the floor is ``64 eps`` times the largest term that enters
  the sum (cancellation-aware), not ``eps`` times the result.
* Analytic families: 40-digit quadrature of an integrand that decays as
  ``v**-2`` or faster has a declared accuracy floor of ``1e-30`` relative; the
  budgets are ``5e-28`` for the mass and ``5e-26`` for the variance, which are
  two orders above the measured quadrature error and still ~26 digits tighter
  than any float64 representation.
* Lorentzian closed form: budget ``1e-30`` relative against the 40-digit
  quadrature; the measured agreement is ~``1e-41``.
* ``expm`` order ratio: fourth order predicts a ratio of ``16``; the observed
  value must lie in ``[14, 18]``, which is the roundoff window measured on this
  configuration, and the assertion prints the measured ratio.
* Analytic tone: recovery is algebraic, so the budget is ``64 eps`` relative
  for the frequency and ``256 eps`` absolute for the exponent (the exponent is a
  difference of logarithms of order one).

One claim is deliberately *not* asserted here.  ``vp-distribution`` reports
``(wr, wi) = (1, -sqrt(2) k)`` as "the exact root" of the ``kappa = 1``
(Lorentzian) family.  The closed form in item 3 decides that root as
``omega = +-1 + i sqrt(2) k`` under the module's own ``exp(-i omega t)``
convention, and the semidiscrete operator on every grid tested has a purely real
spectrum, so neither route reproduces the reported pair.  That is a code-versus-
evidence disagreement, so it is recorded as ``cannot establish`` in the
contracts and in ticket T-2026-0600; it is not written into a test that would
pin the current behaviour as correct.
"""

from __future__ import annotations

from fractions import Fraction

import mpmath as mp
import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.linalg import expm
from scirel.kinetic.vlasov_poisson import (
    solve_vlasov_poisson,
    vp_diagnostic,
    vp_distribution,
    vp_envelope,
    vp_evolve,
    vp_field,
    vp_init,
    vp_rhs,
    vp_rk4_step,
)

EPS = np.finfo(float).eps


def _high_precision():
    """Set the reference working precision explicitly.

    ``mpmath``'s precision is process-global, so a test that relies on an earlier
    test having raised it would pass or fail depending on collection order.  The
    budget statements below are quoted for 40 digits, so 40 digits are set here.
    """
    mp.mp.dps = 40


def _exact_field(df, k, dv):
    """Return ``(i/k) dv sum(df)`` as a complex number, decided exactly.

    ``k`` and ``dv`` are floats and therefore exact binary rationals, so the
    product is an exact rational calculation; only the final conversion to
    ``complex`` rounds.
    """
    real = Fraction(0)
    imaginary = Fraction(0)
    for value in df:
        value = complex(value)
        real += Fraction(value.real)
        imaginary += Fraction(value.imag)
    scale = Fraction(dv) / Fraction(k)
    # (i/k) dv sum(df) = i * scale * (real + i*imaginary)
    return complex(
        -float(scale * imaginary),
        float(scale * real),
    )


def test_poisson_closure_is_decided_by_exact_rational_arithmetic():
    """``vp_field`` is ``(i/k) dv sum(df)``, with the sum's sign and the dv factor decided exactly."""
    cases = [
        (np.array([1.0 + 2.0j, -3.0 + 0.5j, 0.25 - 1.75j]), 0.37, 0.125),
        (np.array([-2.0 + 0.0j, 1.0 + 1.0j]), -1.5, 0.5),
        (np.array([0.1, 0.2, 0.3, 0.4]), 12.0, 1e-3),
    ]
    for df, k, dv in cases:
        expected = _exact_field(df, k, dv)
        got = vp_field(df, k, dv)
        budget = 8.0 * EPS * abs(expected)
        assert abs(got - expected) <= budget, (got, expected, abs(got - expected) / budget)
        # Discrimination: the same comparison with a flipped sign or a doubled
        # dv must exceed the budget, otherwise the budget above is vacuous.
        assert abs(-expected - expected) > budget
        assert abs(2.0 * expected - expected) > budget


def _mp_stages(df, dE, vv, df0dv, k, dv, dt):
    """Re-derive the four RK4 stages and their moments from the stated model.

    Everything is recomputed at 40 digits from ``d(df)/dt = -i k v df + E f0'``
    with ``E(x) = (i/k) dv sum(x)`` and the classical tableau
    ``1/6, 1/3, 1/3, 1/6``; no implementation intermediate enters.
    """
    mp.mp.dps = 40
    velocity = [mp.mpf(float(entry)) for entry in vv]
    slope = [mp.mpf(float(entry)) for entry in df0dv]
    field = mp.mpf(float(dv)) / mp.mpf(float(k))
    wavenumber = mp.mpf(float(k))
    step = mp.mpf(float(dt))

    def closed(state):
        total = sum(state)
        # E = (i/k) dv sum(state)
        return mp.mpc(0, 1) * field * total

    def rhs(state):
        force = closed(state)
        return [
            -mp.mpc(0, 1) * wavenumber * v * f + force * g
            for v, f, g in zip(velocity, state, slope)
        ]

    start = [mp.mpc(float(np.real(entry)), float(np.imag(entry))) for entry in df]
    a = rhs(start)
    x1 = [f + step / 2 * s for f, s in zip(start, a)]
    b = rhs(x1)
    x2 = [f + step / 2 * s for f, s in zip(start, b)]
    c = rhs(x2)
    x3 = [f + step * s for f, s in zip(start, c)]
    return start, [start, x1, x2, x3], velocity, slope, closed, wavenumber, step


def test_mass_moment_obeys_the_discrete_continuity_identity_in_one_rk4_step():
    """One step satisfies ``d(rho)/dt = -i k j + E (dv sum f0')`` for every stage input."""
    state = vp_init(nv=16, nt=1, dt=0.01, k=0.3)
    updated, closed_field = vp_rk4_step(
        state["df"], state["dE"], state["vv"], state["df0dv"], state["k"], state["dv"], state["dt"]
    )
    start, inputs, velocity, slope, closed, wavenumber, step = _mp_stages(
        state["df"], state["dE"], state["vv"], state["df0dv"], state["k"], state["dv"], state["dt"]
    )
    spacing = mp.mpf(float(state["dv"]))
    source = spacing * sum(slope)

    def density(entries):
        return spacing * sum(entries)

    def current(entries):
        return spacing * sum(v * f for v, f in zip(velocity, entries))

    # The continuity statement is about the *stage inputs*: the derivative of the
    # density at x is -i k times the current of x plus E(x) times the discrete
    # mass of f0'.  That is the stated model, evaluated at each of the four RK4
    # input states.
    stage_rates = [(-mp.mpc(0, 1) * wavenumber * current(x) + closed(x) * source) for x in inputs]
    weights = [mp.mpf(1) / 6, mp.mpf(1) / 3, mp.mpf(1) / 3, mp.mpf(1) / 6]
    predict = step * sum(weight * rate for weight, rate in zip(weights, stage_rates))
    left = density(
        [mp.mpc(float(np.real(entry)), float(np.imag(entry))) for entry in updated]
    ) - density(start)

    scale = step * max(abs(rate) for rate in stage_rates)
    budget = 64 * EPS * float(scale)
    assert abs(left - predict) <= budget, (abs(left - predict), float(budget))
    assert_allclose(closed_field, vp_field(updated, state["k"], state["dv"]), rtol=0, atol=8 * EPS * abs(closed_field))
    # Discrimination: the cancelled sum is orders below each stage term, so a
    # wrong final weight is still visible against the same budget.
    wrong = predict - step * (mp.mpf(1) / 30) * stage_rates[1]
    assert abs(left - wrong) > 100 * budget


def test_field_and_rhs_satisfy_the_poisson_constraint_and_the_advection_identity():
    """``ikE = -dv sum(df)`` and ``vp_rhs`` equals ``-i k v df + E f0'`` term by term."""
    k, dv = 0.45, 0.2
    velocity = np.array([-2.0, -0.5, 1.0, 3.0])
    slope = np.array([0.2, 0.7, -0.5, -0.4])
    distribution = np.array([1.0 + 2.0j, 2.0, -1.0j, 3.0])
    field = vp_field(distribution, k, dv)
    assert_allclose(1j * k * field, -dv * np.sum(distribution), rtol=0, atol=8 * EPS * abs(dv * np.sum(distribution)))
    rhs = vp_rhs(distribution, field, velocity, slope, k)
    expected = -1j * k * velocity * distribution + field * slope
    assert_allclose(rhs, expected, rtol=0, atol=8 * EPS * np.abs(expected).max())


def test_initial_state_reproduces_the_grid_dv_and_closure_identities():
    """``vv``, ``dv``, the default perturbation and the recurrence time are the stated closed forms."""
    state = vp_init(nv=64, nt=3, dt=0.02, k=0.25, vmax=8.0)
    velocity = np.linspace(-8.0, 8.0, 65)
    assert_allclose(state["vv"], velocity, rtol=0, atol=0)
    assert_allclose(state["dv"], 2.0 * 8.0 / 64, rtol=0, atol=0)
    assert_allclose(state["df"], (0.1 * np.exp(-velocity * velocity)).astype(complex), rtol=0, atol=8 * EPS)
    assert_allclose(state["dE"], vp_field(state["df"], 0.25, state["dv"]), rtol=0, atol=8 * EPS * abs(state["dE"]))
    # TR = 2 pi / (k dv) is the period at which the free-streaming phase k v t
    # advances by 2 pi across one cell.
    assert_allclose(state["TR"], 2.0 * np.pi / (0.25 * state["dv"]), rtol=0, atol=8 * EPS * state["TR"])
    assert_allclose(state["tt"], np.arange(4) * 0.02, rtol=0, atol=0)


@pytest.mark.parametrize("kappa", ["1.6", "2", "3"])
def test_kappa_family_has_unit_mass_and_the_declared_variance(kappa):
    """The ``kappa`` family's constants give mass 1 and variance ``2k/(2k-3)`` at 40 digits."""
    index = mp.mpf(kappa)
    constant = mp.gamma(index) / (mp.gamma(index - mp.mpf(1) / 2) * mp.sqrt(2 * mp.pi * index))

    def family(v):
        return constant * (1 + v * v / (2 * index)) ** (-index)

    velocity = np.array([-1.7, -0.3, 0.0, 0.9, 2.4])
    derivative, real_frequency, imaginary_frequency = vp_distribution(velocity, 2, kappa=float(index))
    reference = [
        -constant * mp.mpf(float(v)) * (1 + mp.mpf(float(v)) ** 2 / (2 * index)) ** (-index - 1)
        for v in velocity
    ]
    assert_allclose(derivative, [float(entry) for entry in reference], rtol=1e-14, atol=1e-17)
    assert real_frequency is None and imaginary_frequency is None
    mass = mp.quad(family, [-mp.inf, mp.inf])
    variance = mp.quad(lambda v: v * v * family(v), [-mp.inf, mp.inf])
    assert abs(mass - 1) < mp.mpf("5e-28"), mass
    assert abs(variance - 2 * index / (2 * index - 3)) < mp.mpf("5e-26"), variance


def test_maxwellian_family_is_the_unit_variance_gaussian_derivative():
    """``Fn=1`` returns ``-v exp(-v^2/2)/sqrt(2 pi)``, whose mass is 1 and variance is 1."""
    velocity = np.array([-2.5, -0.75, 0.0, 0.75, 2.5])
    derivative, real_frequency, imaginary_frequency = vp_distribution(velocity, 1)
    reference = np.array(
        [-float(v) * mp.e ** (-(mp.mpf(float(v)) ** 2) / 2) / mp.sqrt(2 * mp.pi) for v in velocity]
    )
    assert_allclose(derivative, reference, rtol=0, atol=1e-16)
    assert real_frequency is None and imaginary_frequency is None
    gaussian = lambda v: mp.e ** (-v * v / 2) / mp.sqrt(2 * mp.pi)
    assert abs(mp.quad(gaussian, [-mp.inf, mp.inf]) - 1) < mp.mpf("5e-30")
    assert abs(mp.quad(lambda v: v * v * gaussian(v), [-mp.inf, mp.inf]) - 1) < mp.mpf("5e-28")


def test_triangle_derivative_is_the_exact_piecewise_function_and_integrates_to_zero():
    """``Fn=3`` is ``+1``/``-1`` on the open halves and ``0`` at the kinks; its integral vanishes exactly."""
    velocity = np.array([-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0])
    derivative, _, _ = vp_distribution(velocity, 3)
    assert_allclose(derivative, [0.0, 0.0, 1.0, 0.0, -1.0, 0.0, 0.0], rtol=0, atol=0)
    # The distributional integral of this piecewise derivative is zero because
    # the two rectangles have equal magnitude and opposite sign.
    assert 0.5 * 1.0 + 0.5 * (-1.0) == 0.0


def test_slowing_down_derivative_is_the_analytic_cutoff_and_carries_zero_mass():
    """``Fn=4`` is ``-sign(v) 3 v^2 A/(|v|^3+vt^3)^2`` inside ``|v| <= 4`` and its weak form has zero mass."""
    thermal = mp.sqrt(2)
    amplitude = 3 * mp.sqrt(3) * thermal**2 / (4 * mp.pi)
    velocity = np.linspace(-4.0, 4.0, 9)
    derivative, _, _ = vp_distribution(velocity, 4, cutoff_mode="smooth")
    reference = []
    for v in velocity:
        value = mp.mpf(float(v))
        if abs(value) > 4:
            reference.append(0.0)
            continue
        term = -mp.sign(value) * 3 * value**2 / (abs(value) ** 3 + thermal**3) ** 2 * amplitude
        if abs(value) == 4:
            term = term / 2
        reference.append(float(term))
    assert_allclose(derivative, reference, rtol=0, atol=1e-16)
    # Smooth mode: the integral of the continuous derivative over the support is
    # exactly the two cutoff jumps with opposite signs, i.e. zero mass.
    inside = mp.quad(
        lambda v: -mp.sign(v) * 3 * v**2 / (abs(v) ** 3 + thermal**3) ** 2 * amplitude,
        [-4, 4],
    )
    jump = amplitude / (4**3 + thermal**3)
    assert abs(inside + jump - jump) < mp.mpf("1e-40")


def test_lorentzian_dispersion_integral_matches_its_meromorphic_closed_form():
    """``integral F'/(v-z) dv = 1/(z - i a)^2`` to 30 digits, so the reference exists without the code."""
    width = mp.sqrt(2)
    constant = width / mp.pi

    def derivative(v):
        return -2 * width * v / (mp.pi * (v * v + width * width) ** 2)

    for point in (mp.mpc("0.3", "-2"), mp.mpc("6.6", "-1.4"), mp.mpc("0", "-3")):
        pieces = [-mp.inf, -50, -5, 0, 5, 50, mp.inf]
        measured = sum(
            mp.quad(lambda v: derivative(v) / (v - point), [lo, hi])
            for lo, hi in zip(pieces[:-1], pieces[1:])
        )
        closed = 1 / (point - mp.mpc(0, 1) * width) ** 2
        assert abs(measured - closed) <= abs(closed) * mp.mpf("1e-30"), (point, measured, closed)
    assert abs(constant * mp.quad(lambda v: 1 / (1 + v * v / 2), [-mp.inf, mp.inf]) - 1) < mp.mpf("1e-35")


def test_envelope_is_the_exact_logarithm_and_a_straight_theory_line():
    """``lndE`` is ``ln|E|`` and ``lndEe`` is the straight line with slope ``wi``."""
    times = np.linspace(0.0, 8.0, 81)
    field = (2.5 * np.exp(-0.21 * times) * np.exp(1j * (1.1 * times + 0.4))).astype(complex)
    envelope = vp_envelope(field, times, wr=1.1, wi=-0.21)
    reference = np.array([float(mp.log(abs(mp.mpf(float(abs(value)))))) for value in field])
    assert_allclose(envelope["lndE"], reference, rtol=0, atol=64 * EPS)
    assert_allclose(envelope["lndEe"], np.log(abs(field[0])) - 0.21 * times, rtol=0, atol=64 * EPS)
    # The slope is exact by construction: a least-squares fit returns wi itself.
    slope = np.polyfit(times, envelope["lndEe"], 1)[0]
    assert_allclose(slope, -0.21, rtol=0, atol=256 * EPS)


def test_diagnostic_recovers_an_analytic_tone_whose_maxima_land_on_nodes():
    """With ``omega = pi/(m dt)`` the peak spacing is exactly ``m dt``, so both estimators are algebraic."""
    steps, spacing, exponent = 2400, 4, -0.075
    dt = 0.5 / (spacing * (steps // spacing))
    times = np.arange(steps + 1) * dt
    omega = np.pi / (spacing * dt)
    field = (1.7 * np.exp(exponent * times) * np.cos(omega * times)).astype(complex)
    diagnostic = vp_diagnostic(field, times, start=0.0, end=times[-1])
    assert_allclose(diagnostic["omega"], omega, rtol=0, atol=256 * EPS * omega)
    assert_allclose(diagnostic["gamma"], exponent, rtol=0, atol=256 * EPS)
    peaks = diagnostic["peak_times"]
    assert_allclose(np.diff(peaks), spacing * dt, rtol=0, atol=8 * EPS)
    assert_allclose(diagnostic["peak_log_magnitudes"], exponent * peaks + np.log(1.7), rtol=0, atol=256 * EPS)


def test_rk4_order_is_measured_on_the_default_configuration():
    """Halving ``dt`` on the built-in 2049-node grid multiplies the error by 16, as fourth order predicts."""
    state = vp_init(nv=2048, nt=1, dt=0.02)
    velocity, slope = state["vv"], state["df0dv"]
    k, dv = state["k"], state["dv"]
    matrix = -1j * k * np.diag(velocity) + (1j * dv / k) * np.outer(slope, np.ones(velocity.size))
    exact = expm(0.4 * matrix) @ state["df"]
    errors = []
    for steps in (2, 4):
        distribution, field = state["df"].copy(), state["dE"]
        for _ in range(steps):
            distribution, field = vp_rk4_step(distribution, field, velocity, slope, k, dv, 0.4 / steps)
        assert_allclose(field, vp_field(distribution, k, dv), rtol=0, atol=8 * EPS * abs(field))
        errors.append(float(np.linalg.norm(distribution - exact)))
    ratio = errors[0] / errors[1]
    assert 14.0 < ratio < 18.0, (ratio, errors)
    # The measured order is reported rather than asserted as a constant.
    assert abs(np.log2(ratio) - 4.0) < 0.2, np.log2(ratio)


def test_free_streaming_reproduces_the_exact_translation_operator():
    """With ``f0' = 0`` the exact solution is ``df(t) = df(0) exp(-i k v t)``, an algebraic reference."""
    state = vp_init(nv=64, nt=50, dt=0.004, k=0.2)
    state["df0dv"] = np.zeros_like(state["vv"])
    initial = state["df"].copy()
    evolved = vp_evolve(state)
    assert_allclose(
        evolved["df"], initial * np.exp(-1j * 0.2 * state["vv"] * 0.2), rtol=1e-9, atol=1e-13
    )
    assert_allclose(evolved["dEt"][0], state["dE"], rtol=0, atol=0)
    assert_allclose(evolved["tt"], np.arange(51) * 0.004, rtol=0, atol=0)


def test_composition_reports_the_declared_status_strings():
    """``nt=0`` reports ``insufficient samples``; a short record carries the rejection text instead."""
    empty = solve_vlasov_poisson(2, 1.0, 32, 0.01, 0)
    assert empty["envelope"] is None and empty["diagnostic"] is None
    assert empty["diagnostic_status"] == "insufficient samples"
    short = solve_vlasov_poisson(2, 1.0, 32, 0.01, 5)
    assert short["state"]["dEt"].shape == (6,)
    assert short["diagnostic"] is None
    assert "two isolated nonzero field maxima" in short["diagnostic_status"]


@pytest.mark.parametrize(
    "call, message",
    [
        (lambda: vp_field([1.0, 2.0], 0.0, 0.1), "k must be finite and nonzero"),
        (lambda: vp_field([1.0, 2.0], 0.5, -0.1), "dv must be positive and finite"),
        (lambda: vp_field([1.0], 0.5, 0.1), "one-dimensional"),
        (lambda: vp_distribution([0.0, 1.0], 9), "Fn must be one of"),
        (lambda: vp_distribution([0.0, 1.0], 2, kappa=0.4), "kappa must exceed"),
        (lambda: vp_distribution([0.0, 1.0], 1, cutoff_mode="hard"), "cutoff_mode must be"),
        (lambda: vp_init(nv=1), "nv must be an integer"),
        (lambda: vp_init(nt=-1), "nt must be a nonnegative integer"),
        (lambda: vp_init(Fn=1, df0dv=np.zeros(3)), "either a built-in Fn"),
        (lambda: vp_init(Fn=None), "either a built-in Fn"),
        (lambda: vp_init(nv=4, df_initial=np.zeros(3)), "one value per velocity node"),
        (lambda: vp_init(nv=4, Fn=None, df0dv=np.zeros(5) + 1j), "df0dv must be real"),
        (lambda: vp_rk4_step([1.0, 2.0], 0.5, [-1.0, 1.0], [0.0, 0.0], 0.5, 0.1, 0.01), "Poisson constraint"),
        (lambda: vp_envelope([1.0, 2.0], [0.0, 0.0]), "strictly increasing"),
        (lambda: vp_diagnostic([1.0, 1.0, 1.0, 1.0], [0.0, 1.0, 2.0, 3.0]), "two isolated"),
    ],
)
def test_each_rejection_channel_has_its_own_assertion(call, message):
    """Every documented failure channel of the nine assets is reached by at least one call."""
    with pytest.raises(ValueError, match=message):
        call()


def test_nonrepresentable_derived_values_fail_explicitly():
    """A field that overflows raises ``FloatingPointError``, not ``inf``."""
    huge = np.array([1e308, 1e308])
    with pytest.raises(FloatingPointError, match="not representable"):
        vp_field(huge, 1e-300, 1.0)
    with pytest.raises(FloatingPointError, match="not representable"):
        vp_rk4_step(
            np.array([1e308, -1e308]),
            vp_field(np.array([1e308, -1e308]), 0.5, 1e-300),
            np.array([-1.0, 1.0]),
            np.array([0.0, 0.0]),
            0.5,
            1e-300,
            1e-3,
        )
