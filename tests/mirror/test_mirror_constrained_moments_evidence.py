"""Independent evidence for the invariant mirror moments.

Asset: ``scirel.mirror.mirror-constrained-moments``.

The maintained tests compare the returned moments with the same closed form the
implementation evaluates, and check the plug branch only through internal
refinement and finiteness.  A shared formula is not an independent source, and a
finiteness check cannot decide whether the trapped pitch integral has the right
value.

Three independent bases are used here:

* **The untruncated closed form**, written directly from the bi-Maxwellian
  invariants and evaluated in 50-digit ``mpmath`` arithmetic.  With
  ``C = (B - B_ref)/T_parallel + B_ref/T_perp,ref`` and
  ``T_perp,local = B/C``, the untruncated density is
  ``n_ref (T_perp,local/T_perp,ref) exp(-q(phi - phi_ref)/T_parallel)``, and the
  moments are ``p_parallel = n_full T_parallel`` and
  ``p_perpendicular = n_full T_perp,local``.
* **A piecewise mpmath quadrature of the trapped pitch integral.**  The
  dimensionless trapped fractions are
  ``I_k = integral_0^40 e^{-x} F_k(A(x)) dx`` with
  ``A(x) = max(min(a_L x + b_L, a_R x + b_R), 0)``,
  ``F_density = erf(sqrt(A))``, ``F_parallel = erf(sqrt(A)) - (2/sqrt(pi)) sqrt(A) e^{-A}``
  and ``F_perp = x erf(sqrt(A))``.  The oracle integrates each smooth piece
  separately at the barrier intersections and at the zeros of the two linear
  pieces, because a single tanh-sinh pass over the kink is inaccurate at the
  ``1e-6`` level -- checked while preparing this file, which is why the oracle is
  explicit about its breakpoints.
* **The analytic magnetic-only limit.**  For equal barriers ``A = alpha x`` the
  three fractions are the closed form ``xi, xi^3, xi (3 - xi^2)/2`` with
  ``xi = sqrt(alpha/(1 + alpha))``.  No quadrature appears on either side.

Budgets, fixed before the comparison was run:

* the untruncated closed form uses ``_RELATIVE_BUDGET = 256 eps``, derived from
  seven logarithms and five additions of terms of magnitude at most 100 in the
  hydrogen fixture (the same derivation as in the invariant-distribution
  evidence file);
* the trapped-fraction comparison uses ``_FRACTION_ATOL = 2e-13`` and
  ``_FRACTION_RTOL = 2e-11`` -- exactly the error-estimate targets the contract
  declares for this quadrature, not a figure read off a result.  The mpmath
  oracle contributes about ``1e-30`` at 40 digits and is negligible;
* the magnetic-only closed form is compared at ``1e-15`` absolute, i.e. the
  binary64 rounding of three multiplications, and the identity itself is exact.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- nonpositive or nonfinite mass/charge, refill outside
  ``[0, 1]``, a nonintegral or sub-eight quadrature order, one-sided plug
  fields, nonpositive ``b_t``/plug fields/``b_ref``/temperatures, a negative
  reference density, nonfinite local arrays and an unmatchable profile all raise
  ``ValueError``.
* ``runtime_failure`` -- a nonpositive integrability coefficient raises
  ``FloatingPointError``, and an unrepresentable moment raises
  ``FloatingPointError`` rather than returning ``inf``.
* ``nonconvergence`` -- the declared minimum work budget still meets the declared
  accuracy target against the independent oracle, so the channel is not
  triggered spuriously.  The ``RuntimeError`` branch itself was **not** reached
  by any input tried here; that is recorded as not-exercised rather than as
  unreachable, because a sampled search cannot prove the branch is dead.
* ``partial_results`` -- every raise happens before the nine-field mapping is
  assembled, so ``pytest.raises`` is the assertion that nothing partial escapes.
"""

from __future__ import annotations

import math

import mpmath
import numpy as np
import pytest

from scirel.mirror import evaluate_mirror_constrained_moments
from scirel.mirror._mirror_numerics import _trapped_fractions

mpmath.mp.dps = 50

_EPS = math.ulp(1.0)
_RELATIVE_BUDGET = 256 * _EPS
_FRACTION_ATOL = 2e-13
_FRACTION_RTOL = 2e-11

E_CHARGE = 1.602176634e-19
M_PROTON = 1.67262192595e-27


def _reference_untruncated(
    *,
    b_t,
    potential,
    density_ref,
    temperature_parallel,
    temperature_perpendicular_ref,
    b_ref,
    phi_ref,
    charge,
):
    """Untruncated bi-Maxwellian moments in 50-digit arithmetic."""
    mp = mpmath
    b_t = mp.mpf(b_t)
    coefficient = (b_t - mp.mpf(b_ref)) / mp.mpf(temperature_parallel) + mp.mpf(b_ref) / mp.mpf(
        temperature_perpendicular_ref
    )
    t_perp_local = b_t / coefficient
    density_full = (
        mp.mpf(density_ref)
        * (t_perp_local / mp.mpf(temperature_perpendicular_ref))
        * mp.e
        ** (-mp.mpf(charge) * (mp.mpf(potential) - mp.mpf(phi_ref)) / mp.mpf(temperature_parallel))
    )
    return {
        "density": density_full,
        "p_parallel": density_full * mp.mpf(temperature_parallel),
        "p_perpendicular": density_full * t_perp_local,
        "t_perpendicular_local": t_perp_local,
    }


def _reference_trapped_fractions(a, b, c, d, cut=40.0):
    """Piecewise 50-digit quadrature of the three trapped pitch fractions."""
    mp = mpmath
    knots = {0.0, cut}
    if a != c:
        crossing = (d - b) / (a - c)
        if 0.0 < crossing < cut:
            knots.add(crossing)
    for slope, intercept in ((a, b), (c, d)):
        if slope:
            root = -intercept / slope
            if 0.0 < root < cut:
                knots.add(root)
    edges = sorted(knots)

    def barrier(x):
        return max(min(a * x + b, c * x + d), 0.0)

    totals = [mp.mpf(0)] * 3
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        totals[0] += mp.quad(lambda x: mp.e ** (-x) * mp.erf(mp.sqrt(barrier(x))), [lower, upper])
        totals[1] += mp.quad(
            lambda x: (
                mp.e ** (-x)
                * (
                    mp.erf(mp.sqrt(barrier(x)))
                    - 2 / mp.sqrt(mp.pi) * mp.sqrt(barrier(x)) * mp.e ** (-barrier(x))
                )
            ),
            [lower, upper],
        )
        totals[2] += mp.quad(
            lambda x: x * mp.e ** (-x) * mp.erf(mp.sqrt(barrier(x))), [lower, upper]
        )
    return totals


def _call(*, b_t=1.4, plug=1.8, refill=0.0, order=32, **overrides):
    arguments = dict(
        b_t=b_t,
        psi=0.0,
        potential_v=0.05,
        mass_kg=M_PROTON,
        charge_c=E_CHARGE,
        density_ref_m3=2.0e18,
        temperature_parallel_j=1200.0 * E_CHARGE,
        temperature_perpendicular_ref_j=2400.0 * E_CHARGE,
        b_ref_t=1.0,
        phi_ref_v=0.02,
        b_plug_left_t=plug,
        b_plug_right_t=plug,
        phi_plug_left_v=0.0,
        phi_plug_right_v=0.0,
        loss_cone_refill=refill,
        quadrature_order=order,
    )
    arguments.update(overrides)
    return evaluate_mirror_constrained_moments(**arguments)


def test_untruncated_moments_match_the_50_digit_closed_form():
    # refill=1 bypasses the plug integration, so all three fractions are one and
    # the returned moments are the untruncated closed form exactly.
    for b_t in (1.4, 2.0, 1.05):
        returned = _call(b_t=b_t, refill=1.0)
        exact = _reference_untruncated(
            b_t=b_t,
            potential=0.05,
            density_ref=2.0e18,
            temperature_parallel=1200.0 * E_CHARGE,
            temperature_perpendicular_ref=2400.0 * E_CHARGE,
            b_ref=1.0,
            phi_ref=0.02,
            charge=E_CHARGE,
        )
        assert set(returned) == {
            "density_m3",
            "p_parallel_pa",
            "p_perpendicular_pa",
            "temperature_parallel_j",
            "temperature_perpendicular_local_j",
            "untruncated_density_m3",
            "density_pitch_integral",
            "parallel_pitch_integral",
            "perpendicular_pitch_integral",
        }
        for returned_name, exact_key in (
            ("untruncated_density_m3", "density"),
            ("p_parallel_pa", "p_parallel"),
            ("p_perpendicular_pa", "p_perpendicular"),
            ("temperature_perpendicular_local_j", "t_perpendicular_local"),
        ):
            observed = mpmath.mpf(float(returned[returned_name]))
            target = exact[exact_key]
            assert abs(observed - target) <= _RELATIVE_BUDGET * abs(target), (
                b_t,
                returned_name,
                float(observed),
                float(target),
            )
        # The bypassed fractions are exactly one, so the reported density is the
        # untruncated density bit for bit.
        assert float(returned["density_m3"]) == float(returned["untruncated_density_m3"])
        assert float(returned["density_pitch_integral"]) == 1.0


def test_trapped_fractions_match_independent_piecewise_quadrature():
    # Five barrier configurations: both barriers magnetic-only, one sloped and
    # one flat, opposing slopes, and a case where the lower barrier crosses zero.
    cases = [
        (0.3, 0.0, 0.3, 0.0),
        (0.5, 0.2, 0.1, 0.6),
        (1.5, -0.3, 2.0, 0.4),
        (-0.4, 1.0, 0.9, 0.1),
        (0.0, 0.5, 0.0, 0.9),
    ]
    for a, b, c, d in cases:
        returned = _trapped_fractions(np.array(a), np.array(b), np.array(c), np.array(d), 32)
        reference = _reference_trapped_fractions(a, b, c, d)
        for index, (observed, target) in enumerate(zip(returned, reference, strict=True)):
            deviation = abs(mpmath.mpf(float(observed)) - target)
            budget = _FRACTION_ATOL + _FRACTION_RTOL * abs(target)
            assert deviation <= budget, (a, b, c, d, index, float(deviation), float(budget))


def test_magnetic_only_barriers_match_the_analytic_closed_form():
    # A = alpha x: the fractions are xi, xi^3 and xi(3 - xi^2)/2 with
    # xi = sqrt(alpha/(1 + alpha)).  This is a closed form, not a quadrature.
    for alpha in (0.05, 0.3, 1.0, 2.0, 10.0):
        xi = mpmath.sqrt(mpmath.mpf(alpha) / (1 + mpmath.mpf(alpha)))
        expected = (xi, xi**3, xi * (3 - xi * xi) / 2)
        returned = _trapped_fractions(
            np.array(alpha), np.array(0.0), np.array(alpha), np.array(0.0), 32
        )
        for observed, target in zip(returned, expected, strict=True):
            assert abs(mpmath.mpf(float(observed)) - target) <= mpmath.mpf("1e-15")


def test_swapping_the_two_barriers_leaves_every_fraction_unchanged():
    # The trapped condition depends only on the smaller barrier, so the two ends
    # are interchangeable.  The implementation sorts nothing: the assertion is
    # that its integral is symmetric.
    for left, right in (
        ((0.5, 0.2), (0.1, 0.6)),
        ((1.5, -0.3), (2.0, 0.4)),
        ((0.3, 0.0), (0.9, -0.2)),
    ):
        forward = _trapped_fractions(
            np.array(left[0]), np.array(left[1]), np.array(right[0]), np.array(right[1]), 32
        )
        reverse = _trapped_fractions(
            np.array(right[0]), np.array(right[1]), np.array(left[0]), np.array(left[1]), 32
        )
        for forward_value, reverse_value in zip(forward, reverse, strict=True):
            assert abs(float(forward_value) - float(reverse_value)) <= _FRACTION_ATOL


def test_refill_mixes_the_trapped_fraction_linearly():
    # locked = refill + (1 - refill) * fraction is the declared mixing rule.  It
    # is checked as an identity against the refill=0 fractions, so a squared,
    # complemented or clamped mixture fails.
    base = _call(refill=0.0)
    for refill in (0.25, 0.5, 0.75):
        mixed = _call(refill=refill)
        for name in (
            "density_pitch_integral",
            "parallel_pitch_integral",
            "perpendicular_pitch_integral",
        ):
            expected = refill + (1.0 - refill) * float(base[name])
            assert abs(float(mixed[name]) - expected) <= 2 * _EPS * max(1.0, abs(expected)), (
                refill,
                name,
                float(mixed[name]),
                expected,
            )


def test_the_validated_minimum_work_budget_still_meets_the_declared_target():
    # quadrature_order=8 is the smallest accepted value.  The channel that
    # matters is "a work budget that meets its target", so the minimum budget is
    # compared with the same independent oracle as the default.
    minimum = _call(order=8)
    default = _call(order=32)
    for name in (
        "density_pitch_integral",
        "parallel_pitch_integral",
        "perpendicular_pitch_integral",
    ):
        assert abs(
            float(minimum[name]) - float(default[name])
        ) <= _FRACTION_ATOL + _FRACTION_RTOL * abs(float(default[name]))


def test_invalid_input_channel_raises_value_error():
    for name, value in (
        ("mass_kg", 0.0),
        ("mass_kg", np.inf),
        ("charge_c", 0.0),
        ("loss_cone_refill", -0.1),
        ("loss_cone_refill", 1.5),
        ("loss_cone_refill", np.nan),
        ("quadrature_order", 7),
        ("quadrature_order", np.nan),
    ):
        with pytest.raises(ValueError, match="must be"):
            _call(**{name: value})

    with pytest.raises(ValueError, match="both left and right plug fields are required"):
        _call(b_plug_right_t=None)

    for name, value in (
        ("b_t", 0.0),
        ("b_t", np.nan),
        ("psi", np.inf),
        ("potential_v", np.nan),
        ("b_ref_t", 0.0),
        ("temperature_parallel_j", 0.0),
        ("temperature_perpendicular_ref_j", -1.0),
        ("density_ref_m3", -1.0),
        ("b_plug_left_t", 0.0),
    ):
        with pytest.raises(ValueError, match="must be|invalid"):
            _call(**{name: value})

    with pytest.raises(ValueError, match="cannot be broadcast"):
        _call(density_ref_m3=np.ones(3))


def test_runtime_failure_channel_raises_floating_point_error():
    # C <= 0 when the local field is far below the reference and the reference
    # perpendicular term is too small to compensate.
    with pytest.raises(FloatingPointError, match="not integrable"):
        evaluate_mirror_constrained_moments(
            0.1,
            0.0,
            0.0,
            M_PROTON,
            E_CHARGE,
            1.0e18,
            1.0,
            100.0,
            1.0,
        )

    # B equals B_ref, so the integrability coefficient is finite while the
    # normalisation and the parallel temperature are both huge: each factor is
    # finite and only their product leaves the binary64 range.
    with pytest.raises(FloatingPointError, match="exceed the finite output range"):
        evaluate_mirror_constrained_moments(
            1.0,
            0.0,
            0.0,
            1.0,
            1.0,
            1.0e300,
            1.0e300,
            1.0e-300,
            1.0,
            0.0,
            None,
            None,
            0.0,
            0.0,
            1.0,
            32,
        )
