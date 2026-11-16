"""Independent evidence for the neutral thermal-speed scale.

Asset: ``scirel.neutrals.thermal-speed-scale``.

The contract states the explicit second-moment neutral thermal speed
``v = sqrt(2 e T_ev / (m_amu * m_H))`` with frozen constants.  A single value
compared against the same formula recomputed with the same constants is a
tautology, so the evidence is built from identities and invariances that hold
for *any* implementation of that relation, plus one physics anchor:

1. **Squared defining identity in exact rationals.**  ``v**2 * m_kg = 2 e T`` is
   checked with :class:`fractions.Fraction` over the returned binary64 speed and
   the exact binary64 inputs.  One correctly rounded square root followed by one
   rounding of the square leaves a relative residual of at most a few eps; a
   missing factor of two, a reciprocal, or a wrong mass would be off by a factor,
   not by eps.
2. **Exact scaling laws.**  ``sqrt(4x) = 2 sqrt(x)`` exactly in binary64, so
   ``v(4T) = 2 v(T)``, ``v(4m) = v(m)/2`` and ``v(2T, 2m) = v(T, m)`` must hold
   with ``==``, not with a tolerance.  These decide the square-root temperature
   scaling and the inverse-square-root mass scaling claimed by the contract, and
   they cannot be satisfied by an affine surrogate.
3. **Constant recovery.**  ``v**2 m / (2 T)`` recovers ``e / m_H`` from the
   returned value alone; requiring it to equal the frozen ratio
   ``1.602177e-19 / 1.6726231e-27`` within ``4 eps`` ties the output to the
   declared unit convention rather than to an arbitrary calibration.
4. **Published anchor.**  The NRL Plasma Formulary relation
   ``v_th = sqrt(2 T / m)`` for ``T`` in eV gives ``1.38e4 m/s`` for a proton at
   1 eV.  The anchor is quoted to three significant digits, so its own rounding
   half-width is ``0.005e4 = 50 m/s`` (``3.6e-3`` relative); the declared budget
   is therefore ``5e-3`` relative, set by the anchor's precision and not by the
   measured value.  At that level the anchor fixes the unit/scale convention
   only: it cannot distinguish the frozen ``m_H`` from the current CODATA proton
   mass, which differ by ``7e-7``.
5. **Declared rejections and the dangerous intermediate range.**  One executable
   assertion per ``failure_semantics`` channel, plus the subnormal-temperature
   case that must be recovered at 100-digit precision instead of being rejected.

Budgets, fixed before measurement:

* squared identity: relative residual ``<= 4 * eps``.  The returned ``v`` is one
  correctly rounded square root (relative error ``<= eps/2``), squaring doubles
  that (``<= eps``), and the exact-rational recomputation adds no rounding, so
  ``4 eps`` is dominated by the declared worst case and leaves room for the
  numerator/denominator rounding of the binary64 inputs.
* constant recovery: ``4 * eps`` relative, same reasoning.
* published anchor: ``5e-3`` relative, the rounding half-width of the anchor's
  three significant digits (``50 / 13800``), fixed from the quoted precision
  rather than from the observed difference.
* scaling laws: exact equality.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import math

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps
E_CHARGE = 1.602177e-19
M_HYDROGEN = 1.6726231e-27


def _speed(temperature_ev, mass_amu):
    """Return the scalar speed of the public mapping."""
    return N.compute_thermal_speed_m_s(temperature_ev, mass_amu)["thermal_speed_m_s"]


def test_speed_satisfies_the_squared_defining_identity_exactly():
    """Evidence 1: v**2 * m_kg / (2 e T) is one within 4 eps."""
    rng = np.random.default_rng(301)
    points = [(1.0, 1.0), (1.0, 2.0), (25.0, 0.5), (1e4, 4.0), (1e-6, 1e3)]
    points += [
        (float(rng.uniform(1e-60, 1e60)), float(rng.uniform(1e-30, 1e30))) for _ in range(20)
    ]
    for temperature, mass in points:
        speed = _speed(temperature, mass)
        residual = (
            Fraction(speed) ** 2
            * Fraction(mass * M_HYDROGEN)
            / (2 * Fraction(E_CHARGE) * Fraction(temperature))
        )
        assert abs(residual - 1) <= 4 * EPS, (temperature, mass, float(residual))


def test_speed_obeys_the_exact_square_root_scaling_laws():
    """Evidence 2: v(4T) = 2 v(T), v(4m) = v(m)/2, v(2T, 2m) = v(T, m)."""
    rng = np.random.default_rng(307)
    for _ in range(40):
        temperature = float(rng.uniform(1e-40, 1e40))
        mass = float(rng.uniform(1e-20, 1e20))
        base = _speed(temperature, mass)
        assert _speed(4.0 * temperature, mass) == 2.0 * base
        assert _speed(temperature, 4.0 * mass) == base / 2.0
        assert _speed(2.0 * temperature, 2.0 * mass) == base


def test_speed_recovers_the_frozen_constant_ratio_and_the_published_anchor():
    """Evidence 3 + 4: e/m_H recovered from the value, and the NRL anchor."""
    temperature, mass = 3.0, 2.5
    speed = _speed(temperature, mass)
    recovered = Fraction(speed) ** 2 * Fraction(mass) / (2 * Fraction(temperature))
    frozen = Fraction(E_CHARGE) / Fraction(M_HYDROGEN)
    assert abs(recovered / frozen - 1) <= 4 * EPS
    # Proton at 1 eV: sqrt(2 * 1.602177e-19 / 1.6726231e-27) = 1.38e4 m/s.
    assert abs(_speed(1.0, 1.0) - 1.38e4) <= 5e-3 * 1.38e4


def test_speed_recovers_the_dangerous_intermediate_range_at_high_precision():
    """Evidence 5: an underflowing intermediate is recomputed, not rejected."""
    temperature, mass = 1e-320, 1e-3
    speed = _speed(temperature, mass)
    assert math.isfinite(speed) and speed > 0.0
    with localcontext() as context:
        context.prec = 100
        exact = (
            Decimal(2)
            * Decimal.from_float(E_CHARGE)
            * Decimal.from_float(temperature)
            / (Decimal.from_float(mass) * Decimal.from_float(M_HYDROGEN))
        ).sqrt()
    reference = float(exact)
    assert abs(speed / reference - 1.0) <= 4 * EPS
    # The binary64 ratio really does underflow here, so the recovery path is the
    # one under test rather than an ordinary evaluation.
    assert 2.0 * E_CHARGE * temperature / (mass * M_HYDROGEN) == 0.0


def test_speed_accepts_the_representable_subnormal_and_rejects_the_true_overflow():
    """Evidence 5: a subnormal final speed is representable; true overflow is not."""
    assert math.isfinite(_speed(5e-324, 1.0))
    with pytest.raises(ValueError, match="finite and positive"):
        _speed(1.7e308, 1e-300)


def test_speed_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    call = N.compute_thermal_speed_m_s
    for bad in (0.0, -1.0, float("nan"), float("inf"), "-1.0", True, 1j, np.array([1.0])):
        with pytest.raises(ValueError, match="temperature_ev"):
            call(bad, 1.0)
    for bad in (0.0, -1.0, float("nan"), float("inf"), "-1.0", True, 1j, np.array([1.0])):
        with pytest.raises(ValueError, match="mass_amu"):
            call(1.0, bad)
    assert call(1.0, 1.0)["thermal_speed_m_s"] > 0.0
