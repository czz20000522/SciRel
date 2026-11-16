"""Independent evidence for the local gyrotropic tension and mirror pressure margins.

Assets: ``scirel.diagnostics.pointwise-firehose-margin``,
``scirel.diagnostics.firehose-mirror-margins``.

Evidence sources; none of them is the implementation or its regression fixtures:

1. **Exact rational recomputation.**  ``firehose_margin = B**2/mu0 + p_perp - p_parallel``
   is rebuilt here with ``fractions.Fraction`` from the original binary64 inputs and
   rounded once.  This is a second arithmetic path, not a second call: the
   implementation has its own exact-rational switch for cancellation and range
   loss, so the test separates the ordinary float path (which must agree to
   ``64 eps`` of scale) from the switch (which must agree exactly after rounding).
2. **The ideal-MHD criterion.**  The margin is a *verdict* as well as a value:
   ``firehose_margin > 0`` is exactly ``p_parallel - p_perp < B**2/mu0``.  The
   boundary is tested by constructing exactly representable equalities and both
   sign sides, so the inequality is verified as an equality of sign rather than
   through a tolerance.
3. **The declaration of the mirror term.**  ``mirror_margin = B**2/mu0 + B
   dp_perp/dB`` is checked on analytic ``p_perp(B)`` laws whose derivative is
   written out by hand (affine, power law), for both derivative sources the
   contract allows: an explicit array and a callable.
4. **Dimensional consistency of the two terms.**  Both terms are pressures in Pa.
   Scaling ``B`` by ``sqrt(k)`` and both pressures by ``k`` scales the margin by
   ``k``; that symmetry fails for any stray factor on one term only, so it is a
   cheap guard against a unit or power error.

Budgets, fixed before measurement: exact-rational comparisons ``64 * eps`` of the
local scale; analytic comparisons ``256 * eps`` because the products involve
three factors; sampled-derivative order is asserted as a refinement ratio, never
as a relaxed absolute tolerance.

Not established here: the reduction of the mirror criterion to
``1 - beta_perp (T_perp/T_parallel - 1)`` for an invariant bi-Maxwellian.  The
contract states it, this file does not verify it (that needs the distribution
model and is recorded as a limitation on the contract).
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel import diagnostics as D

EPS = np.finfo(float).eps
MU0 = 4e-7 * np.pi


def _exact_margin(magnetic_field, p_perp, p_parallel, mu0):
    """``B**2/mu0 + p_perp - p_parallel`` in exact rational arithmetic, rounded once."""
    value = (
        Fraction.from_float(float(magnetic_field)) ** 2 / Fraction.from_float(float(mu0))
        + Fraction.from_float(float(p_perp))
        - Fraction.from_float(float(p_parallel))
    )
    return float(value)


def test_firehose_margin_matches_an_exact_rational_recomputation():
    """Evidence 1: ordinary, well-conditioned samples."""
    field = np.array([0.5, 1.0, 2.5, 4.0])
    perp = np.array([10.0, 0.0, -3.0, 2.0e5])
    parallel = np.array([4.0, 1.0, 1.0, 1.0e5])
    got = np.asarray(D.compute_pointwise_firehose_margin(parallel, perp, field)["firehose_margin"])
    expected = np.array([_exact_margin(b, t, p, MU0) for b, t, p in zip(field, perp, parallel)])
    scale = np.maximum(1.0, np.abs(expected))
    assert np.max(np.abs(got - expected) / scale) <= 64.0 * EPS


def test_the_exact_rational_switch_agrees_with_the_independent_exact_value():
    """Evidence 1 on the branch that the cancellation guard selects.

    ``B**2/mu0`` is 1e300 and ``p_parallel`` cancels it to a small remainder, which
    is precisely the case the implementation routes to exact rationals.  The
    independent exact value is therefore the reference for the switch, and a naive
    float evaluation is *not* used as one.
    """
    field = np.array([1.0e150])
    perp = np.array([0.0])
    parallel = np.array([1.0e300])
    got = np.asarray(
        D.compute_pointwise_firehose_margin(parallel, perp, field, mu0=1.0)["firehose_margin"]
    )
    assert got[0] == _exact_margin(field[0], perp[0], parallel[0], 1.0)

    # The discriminating case: the naive float evaluation rounds the small
    # perpendicular term away, so only the exact branch keeps it.
    field = np.array([1.0e150])
    perp = np.array([3.0])
    parallel = np.array([1.0e300])
    naive = (1.0e300 + 3.0) - 1.0e300  # 0.0 in binary64
    exact = _exact_margin(1.0e150, 3.0, 1.0e300, 1.0)
    got = np.asarray(
        D.compute_pointwise_firehose_margin(parallel, perp, field, mu0=1.0)["firehose_margin"]
    )
    assert got[0] == exact
    assert got[0] != naive


def test_the_verdict_is_the_ideal_mhd_firehose_inequality():
    """Evidence 2: ``margin > 0`` is exactly ``p_parallel - p_perp < B**2/mu0``."""
    field = np.array([2.0, 2.0, 2.0])
    mu0 = 1.0
    critical = 2.0**2 / mu0  # = 4.0, exactly representable
    perp = np.array([0.0, 0.0, 0.0])
    parallel = np.array([np.nextafter(critical, 0.0), critical, np.nextafter(critical, np.inf)])
    got = np.asarray(
        D.compute_pointwise_firehose_margin(parallel, perp, field, mu0=mu0)["firehose_margin"]
    )
    assert got[0] > 0.0  # p_parallel just below B^2/mu0
    assert got[1] == 0.0  # exactly at the boundary
    assert got[2] < 0.0  # just above
    assert [bool(value > 0.0) for value in got] == [True, False, False]


def test_margin_scales_with_pressure_when_the_field_scales_by_the_square_root():
    """Evidence 4: both terms carry pressure units, so one factor must move both."""
    factor = 9.0
    field = np.array([1.0, 3.0])
    perp = np.array([2.0, -1.5])
    parallel = np.array([5.0, 0.5])
    base = np.asarray(D.compute_pointwise_firehose_margin(parallel, perp, field)["firehose_margin"])

    scaled = np.asarray(
        D.compute_pointwise_firehose_margin(
            factor * parallel, factor * perp, np.sqrt(factor) * field
        )["firehose_margin"]
    )
    assert np.max(np.abs(scaled - factor * base)) <= 256.0 * EPS * np.max(np.abs(factor * base))


@pytest.mark.parametrize(
    "law, derivative",
    [
        (lambda b: 2.5 * b + 0.75, lambda b: 2.5),
        (lambda b: 3.0 * b**3, lambda b: 9.0 * b**2),
        (lambda b: 1.5 / b, lambda b: -1.5 / b**2),
    ],
)
def test_mirror_margin_is_the_declared_total_pressure_slope(law, derivative):
    """Evidence 3: ``B**2/mu0 + B dp_perp/dB`` on analytic laws, explicit derivative."""
    field = np.array([0.5, 1.0, 2.0])
    perp = np.array([law(value) for value in field])
    slope = np.array([derivative(value) for value in field])
    parallel = np.zeros_like(field)

    result = D.compute_firehose_mirror_margins(parallel, perp, field, dp_perp_dB=slope)
    got = np.asarray(result["mirror_margin"])
    expected = np.array([b * b / MU0 + b * d for b, d in zip(field, slope)])
    assert np.max(np.abs(got - expected) / np.maximum(1.0, np.abs(expected))) <= 256.0 * EPS
    assert result["derivative_method"] == "explicit_fixed_flux_derivative"


def test_the_combined_firehose_margin_is_the_pointwise_relation():
    """The two assets share one kernel: the combined field must equal the pointwise one."""
    field = np.array([0.7, 1.3, 2.9])
    perp = np.array([4.0, -2.0, 0.0])
    parallel = np.array([1.0, 1.0, 6.0])
    pointwise = np.asarray(
        D.compute_pointwise_firehose_margin(parallel, perp, field)["firehose_margin"]
    )
    combined = np.asarray(
        D.compute_firehose_mirror_margins(parallel, perp, field, dp_perp_dB=np.zeros_like(field))[
            "firehose_margin"
        ]
    )
    assert np.array_equal(pointwise, combined)


def test_stability_flags_and_minima_follow_the_margin_signs():
    field = np.array([1.0, 1.0, 1.0])
    perp = np.zeros(3)
    parallel = np.array([0.1, 1.0, 2.0])  # signs: +, 0, -
    result = D.compute_firehose_mirror_margins(parallel, perp, field, dp_perp_dB=np.zeros(3))
    firehose = np.asarray(result["firehose_margin"])
    assert result["firehose_stable"] == bool(np.all(firehose > 0.0))
    assert result["min_firehose_margin"] == float(np.min(firehose))
    assert result["mirror_stable"] == bool(np.all(np.asarray(result["mirror_margin"]) > 0.0))


def test_sampled_fixed_flux_derivative_refines_at_second_order():
    """The ``field_axis`` source is a second-order gradient; measured, not assumed."""
    psi = np.zeros((4, 21))

    def law(b):
        return 2.0 * b**3

    def slope(b):
        return 6.0 * b**2

    errors = []
    for count in (21, 41):
        field = np.tile(np.linspace(0.5, 2.0, count), (4, 1))
        perp = law(field)
        result = D.compute_firehose_mirror_margins(
            np.zeros_like(field),
            perp,
            field,
            field_axis=1,
            psi=psi if count == 21 else np.zeros((4, count)),
        )
        used = np.asarray(result["dp_perp_dB"])
        errors.append(float(np.max(np.abs(used - slope(field)))))
        assert result["derivative_method"] == "declared_fixed_flux_axis_finite_difference"
    ratio = errors[0] / errors[1]
    assert 3.0 <= ratio <= 5.5, f"observed derivative refinement ratio {ratio:.2f} is not O(h^2)"


def test_rejection_channels_are_bound_to_their_contract():
    field = np.array([1.0, 2.0])
    perp = np.zeros(2)
    parallel = np.zeros(2)
    for call, fragment in [
        (lambda: D.compute_pointwise_firehose_margin(parallel, perp[:1], field), "same shape"),
        (lambda: D.compute_pointwise_firehose_margin([], [], []), "nonempty"),
        (lambda: D.compute_pointwise_firehose_margin([np.nan, 0.0], perp, field), "finite"),
        (lambda: D.compute_pointwise_firehose_margin(parallel, perp, field, mu0=0.0), "positive"),
        (
            lambda: D.compute_pointwise_firehose_margin(
                parallel, perp, field, mu0=np.array([1.0, 1.0])
            ),
            "scalar",
        ),
        (lambda: D.compute_firehose_mirror_margins(parallel, perp, field), "derivative"),
        (
            lambda: D.compute_firehose_mirror_margins(
                parallel, perp, field, dp_perp_dB=np.zeros(2), field_axis=1
            ),
            "not both",
        ),
    ]:
        with pytest.raises(ValueError) as caught:
            call()
        assert fragment in str(caught.value), (fragment, str(caught.value))
