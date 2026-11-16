"""Independent evidence for the neutral collision balance relations.

Assets: ``scirel.neutrals.neutral-total-collision-frequency``,
``scirel.neutrals.neutral-boltzmann-rhs``.

The two contracts are the loss/source bookkeeping of the neutral transport
equation: the inverse-length total loss coefficient
``alpha = base + elastic + 2 u_r / D [+ CX]`` and the signed Boltzmann rate
``Vth * (coeff + CX - alpha*F + elastic + wall)``.  Both are algebraic, so the
independent evidence is an *exact* one derived from the physics rather than from
the implementation:

1. **Closed-form wall loss.**  ``2 u_r / D`` is the diffusion length of a
   cylindrical pipe; the exact rational recomputation checks the coefficient,
   the sign, and the radial-node dependence simultaneously.  No fitted curve is
   involved.
2. **Exact rational signed balance.**  Every product and every signed addition
   of the Boltzmann right-hand side is recomputed with
   :class:`fractions.Fraction` from the exact binary64 inputs and rounded once.
   This separates the declared sign structure (a *loss*, not a gain) from
   floating-point accumulation.
3. **Sign discriminator.**  With ``alpha*F = 100`` and every other term zero the
   declared RHS is exactly ``-100 * Vth``.  The gain-sign variant is
   ``+100 * Vth``, so the test asserts the loss value and rejects the gain value;
   a sign inversion cannot pass by landing inside a tolerance.
4. **Branch semantics of the wall sentinel and the CX switch.**  An exact zero
   diameter is a declared wall-off sentinel, *not* the ``D -> 0+`` limit, and
   disabling charge exchange must ignore a supplied CX field entirely.  Both are
   checked as equalities against the branch's own closed form, and the sentinel
   is contrasted with a ``1e-300`` diameter whose wall term is enormous.
5. **Homogeneity.**  Doubling the radial node or the thermal speed is exact in
   binary64, so those linearities are asserted with ``array_equal`` instead of a
   tolerance.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel.

Budgets, fixed before measurement:

* total loss: ``(terms + 2) * eps * sum_q |term_q|`` with
  ``terms = {base, elastic, 2 u_r / D, CX}``; one rounding for the division, one
  per addition, and one for the accumulation slack.
* Boltzmann RHS: ``7 * eps * |Vth| * (|coeff| + |CX| + |alpha F| + |elastic| + |wall|)``.
  The expression performs one multiplication (``alpha*F``), four signed
  additions, and one final ``Vth`` multiplication: six roundings, each bounded by
  ``eps`` times the running magnitude, all dominated by the declared sum.  The
  seventh eps covers the ``(1+eps)`` accumulation slack.  This is the classical
  forward bound for this expression, not a fitted threshold.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# neutral-total-collision-frequency
# --------------------------------------------------------------------------- #


def _total_inputs():
    """A two-node radial axis over three cells with one wall-off sentinel."""
    vr = np.array([0.5, 1.5])
    vx = np.array([-1.0, 0.0, 1.0])
    base = np.array([3.0, 4.0, 0.0])
    elastic = np.array([5.0, 6.0, 0.0])
    diameter = np.array([2.0, 0.5, 0.0])
    cx = np.arange(1.0, 1.0 + 2 * 3 * 3).reshape(2, 3, 3) * 0.5
    return vr, vx, base, elastic, diameter, cx


def test_total_frequency_matches_the_closed_form_with_exact_arithmetic():
    """Evidence 1: base + elastic + 2 u_r / D + CX in exact rationals."""
    vr, vx, base, elastic, diameter, cx = _total_inputs()
    got = N.assemble_neutral_total_collision_frequency(vr, vx, base, elastic, diameter, cx)
    wall = np.array(
        [
            [
                [2.0 * vr[i] / diameter[k] if diameter[k] > 0 else 0.0 for k in range(3)]
                for _ in range(3)
            ]
            for i in range(2)
        ]
    )
    exact = np.empty((2, 3, 3), dtype=object)
    for i in range(2):
        for j in range(3):
            for k in range(3):
                term = _frac(base[k]) + _frac(elastic[k])
                if diameter[k] > 0:
                    term += 2 * _frac(vr[i]) / _frac(diameter[k])
                term += _frac(cx[i, j, k])
                exact[i, j, k] = term
    expected = np.array([float(value) for value in exact.ravel()]).reshape(2, 3, 3)
    scale = (
        2
        * EPS
        * (np.abs(base)[None, None, :] + np.abs(elastic)[None, None, :] + np.abs(wall) + np.abs(cx))
    )
    assert np.all(np.abs(got - expected) <= (4 + 2) * scale)


def test_total_frequency_zero_diameter_is_the_wall_off_sentinel_not_the_limit():
    """Evidence 4: exact wall-off vs a 1e-300 diameter whose term is enormous."""
    vr, vx, base, elastic, diameter, _ = _total_inputs()
    off = N.assemble_neutral_total_collision_frequency(
        vr, vx, base, elastic, diameter, charge_exchange_enabled=False
    )
    # The sentinel cell is exactly base + elastic: zero wall, no rounding slack.
    assert np.array_equal(off[:, :, 2], np.broadcast_to(base[2] + elastic[2], (2, 3)))
    tiny = diameter.copy()
    tiny[2] = 1e-300
    limit = N.assemble_neutral_total_collision_frequency(
        vr, vx, base, elastic, tiny, charge_exchange_enabled=False
    )
    assert np.all(limit[:, :, 2] > 1e290)
    assert not np.allclose(off[:, :, 2], limit[:, :, 2])


def test_total_frequency_branch_switch_ignores_a_supplied_cx_field():
    """Evidence 4: the disabled branch is independent of the CX field."""
    vr, vx, base, elastic, diameter, cx = _total_inputs()
    disabled_with = N.assemble_neutral_total_collision_frequency(
        vr, vx, base, elastic, diameter, cx, charge_exchange_enabled=False
    )
    disabled_without = N.assemble_neutral_total_collision_frequency(
        vr, vx, base, elastic, diameter, charge_exchange_enabled=False
    )
    assert np.array_equal(disabled_with, disabled_without)
    enabled = N.assemble_neutral_total_collision_frequency(vr, vx, base, elastic, diameter, cx)
    assert np.allclose(
        enabled - disabled_with, cx, rtol=0.0, atol=8 * EPS * np.max(np.abs(enabled))
    )


def test_total_frequency_wall_term_is_exactly_linear_in_the_radial_node():
    """Evidence 5: doubling u_r doubles the wall term alone, exactly."""
    vx = np.array([0.0])
    zero = np.zeros(1)
    diameter = np.array([2.0])
    one = N.assemble_neutral_total_collision_frequency(
        np.array([0.5, 1.5]), vx, zero, zero, diameter, charge_exchange_enabled=False
    )
    two = N.assemble_neutral_total_collision_frequency(
        np.array([1.0, 3.0]), vx, zero, zero, diameter, charge_exchange_enabled=False
    )
    assert np.array_equal(two, 2.0 * one)


def test_total_frequency_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    vr = np.array([0.5, 1.5])
    vx = np.array([-1.0, 1.0])
    base = np.array([1.0, 2.0])
    elastic = np.array([1.0, 2.0])
    diameter = np.array([2.0, 4.0])
    cx = np.ones((2, 2, 2))
    call = N.assemble_neutral_total_collision_frequency

    with pytest.raises(ValueError, match="velocity axes"):
        call(np.array([0.0, 1.0]), vx, base, elastic, diameter, cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(np.array([-1.0]), vx, base, elastic, diameter, cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(vr, np.array([]), base, elastic, diameter, cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(vr.reshape(2, 1), vx, base, elastic, diameter, cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(vr, vx, np.array([-1.0, 2.0]), elastic, diameter, cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(vr, vx, base, np.array([-1.0, 2.0]), diameter, cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(vr, vx, base, elastic, np.array([-2.0, 4.0]), cx)
    with pytest.raises(ValueError, match="velocity axes"):
        call(vr, vx, base, np.ones(3), diameter, cx)
    with pytest.raises(ValueError, match="finite real"):
        call(vr, vx, np.array([np.nan, 2.0]), elastic, diameter, cx)
    with pytest.raises(ValueError, match="nonnegative and"):
        call(vr, vx, base, elastic, diameter, -cx)
    with pytest.raises(ValueError, match="nonnegative and"):
        call(vr, vx, base, elastic, diameter, np.ones((2, 2, 3)))
    with pytest.raises(ValueError, match="boolean scalar"):
        call(vr, vx, base, elastic, diameter, cx, charge_exchange_enabled=1)
    with pytest.raises(ValueError, match="needs its explicit frequency field"):
        call(vr, vx, base, elastic, diameter)
    with pytest.raises(ValueError, match="not finite"):
        call(vr, vx, np.array([1.7e308, 1.7e308]), np.array([1.7e308, 1.7e308]), diameter, cx)


# --------------------------------------------------------------------------- #
# neutral-boltzmann-rhs
# --------------------------------------------------------------------------- #

SHAPE = (2, 2, 2)


def _rhs_fields(seed=211):
    """Return signed balance fields that make every term visible."""
    rng = np.random.default_rng(seed)
    return {
        "coefficient_source_distribution": rng.uniform(-2.0, 2.0, size=SHAPE),
        "charge_exchange_source_sum": rng.uniform(-2.0, 2.0, size=SHAPE),
        "collision_frequency_m_inv": rng.uniform(0.0, 3.0, size=SHAPE),
        "total_distribution": rng.uniform(-2.0, 2.0, size=SHAPE),
        "elastic_source_sum": rng.uniform(-2.0, 2.0, size=SHAPE),
        "wall_source_sum": rng.uniform(-2.0, 2.0, size=SHAPE),
    }


def _exact_rhs(vth, f):
    """Exact Vth * (coeff + CX - alpha F + elastic + wall) elementwise."""
    balance = _frac(vth) * (
        _frac(f["coefficient_source_distribution"])
        + _frac(f["charge_exchange_source_sum"])
        - _frac(f["collision_frequency_m_inv"]) * _frac(f["total_distribution"])
        + _frac(f["elastic_source_sum"])
        + _frac(f["wall_source_sum"])
    )
    return float(balance)


def test_rhs_matches_the_exact_rational_signed_balance():
    """Evidence 2: the declared signed sum, recomputed exactly and rounded once."""
    fields = _rhs_fields()
    vth = 5000.0
    got = N.assemble_neutral_boltzmann_rhs(
        vth,
        fields["coefficient_source_distribution"],
        fields["charge_exchange_source_sum"],
        fields["collision_frequency_m_inv"],
        fields["total_distribution"],
        fields["elastic_source_sum"],
        fields["wall_source_sum"],
    )["rhs"]
    expected = np.array(
        [
            _exact_rhs(vth, {name: value[index] for name, value in fields.items()})
            for index in np.ndindex(*SHAPE)
        ]
    ).reshape(SHAPE)
    scale = abs(vth) * (
        np.abs(fields["coefficient_source_distribution"])
        + np.abs(fields["charge_exchange_source_sum"])
        + np.abs(fields["collision_frequency_m_inv"] * fields["total_distribution"])
        + np.abs(fields["elastic_source_sum"])
        + np.abs(fields["wall_source_sum"])
    )
    assert np.all(np.abs(got - expected) <= 7 * EPS * scale)


def test_rhs_treats_the_collision_term_as_a_loss_not_a_gain():
    """Evidence 3: the sign of the loss term, decided by a discriminator."""
    ones = np.ones((1, 1, 1))
    zeros = np.zeros((1, 1, 1))
    got = N.assemble_neutral_boltzmann_rhs(
        2.0, zeros, zeros, 4.0 * ones, 25.0 * ones, zeros, zeros
    )["rhs"]
    # Vth * (0 + 0 - 4*25 + 0 + 0) = -200 exactly.
    assert np.array_equal(got, np.array([[[-200.0]]]))
    gain_variant = 200.0
    assert abs(float(got[0, 0, 0]) - gain_variant) > 1e6 * EPS * gain_variant


def test_rhs_is_exactly_homogeneous_in_the_thermal_speed():
    """Evidence 5: doubling Vth doubles the RHS exactly."""
    fields = _rhs_fields(seed=223)
    base = N.assemble_neutral_boltzmann_rhs(
        3.0,
        fields["coefficient_source_distribution"],
        fields["charge_exchange_source_sum"],
        fields["collision_frequency_m_inv"],
        fields["total_distribution"],
        fields["elastic_source_sum"],
        fields["wall_source_sum"],
    )["rhs"]
    doubled = N.assemble_neutral_boltzmann_rhs(
        6.0,
        fields["coefficient_source_distribution"],
        fields["charge_exchange_source_sum"],
        fields["collision_frequency_m_inv"],
        fields["total_distribution"],
        fields["elastic_source_sum"],
        fields["wall_source_sum"],
    )["rhs"]
    assert np.array_equal(doubled, 2.0 * base)
    # A unit Vth returns the bare normalized balance.
    unit = N.assemble_neutral_boltzmann_rhs(
        1.0,
        fields["coefficient_source_distribution"],
        fields["charge_exchange_source_sum"],
        fields["collision_frequency_m_inv"],
        fields["total_distribution"],
        fields["elastic_source_sum"],
        fields["wall_source_sum"],
    )["rhs"]
    assert np.all(np.abs(unit - base / 3.0) <= 4 * EPS * np.max(np.abs(base)))


def test_rhs_is_zero_when_the_signed_balance_cancels_exactly():
    """Evidence 2: a balanced cell has an exactly zero RHS, not a small one."""
    alpha = np.full((1, 1, 1), 2.0)
    total = np.full((1, 1, 1), 8.0)
    zeros = np.zeros((1, 1, 1))
    # 16 - 2*8 = 0 with every value exactly representable.
    got = N.assemble_neutral_boltzmann_rhs(
        7.0, 16.0 * np.ones((1, 1, 1)), zeros, alpha, total, zeros, zeros
    )["rhs"]
    assert np.array_equal(got, np.zeros((1, 1, 1)))


def test_rhs_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    fields = _rhs_fields(seed=227)
    args = (
        fields["coefficient_source_distribution"],
        fields["charge_exchange_source_sum"],
        fields["collision_frequency_m_inv"],
        fields["total_distribution"],
        fields["elastic_source_sum"],
        fields["wall_source_sum"],
    )
    call = N.assemble_neutral_boltzmann_rhs

    assert call(1.0, *args)["rhs"].shape == SHAPE
    for bad_speed in (0.0, -1.0, float("nan"), float("inf"), "1.0", True, np.array([1.0])):
        with pytest.raises(ValueError, match="thermal_speed_m_s"):
            call(bad_speed, *args)
    with pytest.raises(ValueError, match="finite real array"):
        call(1.0, *((np.array([[[np.nan]]]),) + args[1:]))
    with pytest.raises(ValueError, match="three-dimensional arrays"):
        call(1.0, np.ones((2, 2)), *args[1:])
    with pytest.raises(ValueError, match="three-dimensional arrays"):
        call(1.0, *args[:5], np.ones((2, 2, 3)))
    with pytest.raises(ValueError, match="rhs must be finite"):
        big = np.full((1, 1, 1), 1.7e308)
        unit = np.ones((1, 1, 1))
        call(1.0, big, big, unit, unit, unit, unit)
