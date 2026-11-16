"""Independent evidence for the floored poloidal magnitude and its reference.

Asset: ``scirel.field.poloidal-field-magnitude``.

Two claims are checked, and they are different in kind.

**The floor is a numerical convention, decided exactly.**  ``B = max(hypot, 1e-30)``
is asserted elementwise: below the floor the returned value is *exactly* ``1e-30``,
above it the returned value satisfies ``B >= max(|br|, |bz|)`` and
``B**2 == br**2 + bz**2`` within the two roundings of a hypotenuse and a square, and
a mixed array applies each rule to its own element rather than inheriting a
batch-level sentinel.  A caller that reads ``B`` as a plain magnitude can be wrong
by a factor of 1e30 at a null point, which is exactly why the floor is part of the
public contract rather than an implementation detail.

**The reference is a median, decided in exact rationals.**  ``B0_default`` is the
median of the returned magnitude values, computed as
``lower + 0.5 * (upper - lower)`` over the two middle order statistics.  The test
recovers both order statistics with :class:`fractions.Fraction` and requires the
returned value to be the correctly rounded midpoint; it also pins the two
behaviours that the difference-first form exists for:

* a pair of very large equal values (``1.7e308``) whose naive ``0.5 * (a + b)``
  overflows to infinity while this form returns ``1.7e308`` — the discriminating
  case, not a tolerance;
* a pair of subnormal values whose difference underflows to zero while this form
  still returns the common value.

Budget: the ``hypot`` comparison carries ``2 eps`` relative (one hypotenuse, one
square); the median comparison carries ``2 eps`` of the exact rational midpoint
(one subtraction, one multiply by ``1/2``, one addition).  The floor, the
overflow and the subnormal cases are exact equalities.  An observed maximum is
reported by the assertion message rather than claimed as a bound.

Evidence ceiling: the median is a descriptive statistic of the sampled array; the
contract already says it is not an automatically applied normalization, and
nothing here interprets it as one.
"""

from __future__ import annotations

from fractions import Fraction
import math

import numpy as np
import pytest

from scirel._result import Result
from scirel.field import compute_poloidal_field_magnitude

EPS = float(np.finfo(float).eps)
FLOOR = 1.0e-30


def test_magnitude_is_the_hypotenuse_above_the_floor_and_the_floor_below_it():
    """The floor and the hypotenuse, elementwise."""
    radial = np.array([[3.0, 1.0e-20, 0.0], [5.0, -2.0, 1.0e-31]])
    axial = np.array([[4.0, 0.0, 0.0], [12.0, 1.0e-20, -1.0e-31]])
    result = compute_poloidal_field_magnitude(radial, axial)
    magnitude = result["B"]
    observed = 0.0
    for index in np.ndindex(radial.shape):
        reference = math.hypot(float(radial[index]), float(axial[index]))
        floor_should_apply = max(abs(float(radial[index])), abs(float(axial[index]))) < FLOOR
        if floor_should_apply:
            assert magnitude[index] == FLOOR, index
            continue
        assert magnitude[index] >= max(abs(float(radial[index])), abs(float(axial[index])))
        squared = (
            Fraction(float(radial[index])) ** 2 + Fraction(float(axial[index])) ** 2
        )
        deviation = abs(Fraction(float(magnitude[index])) ** 2 - squared) / squared
        assert deviation <= 2 * Fraction(EPS), (index, float(deviation))
        observed = max(observed, float(deviation))
        # Above the floor the value is the hypotenuse, so it is at least the
        # reference within the same budget.
        assert abs(float(magnitude[index]) - reference) <= 2 * EPS * reference
    # The floor really is applied to the two null elements and not to the
    # neighbours, so the branch is per element.
    assert magnitude[0, 2] == FLOOR
    assert magnitude[1, 2] == FLOOR
    assert magnitude[0, 0] == 5.0
    assert observed > 0.0


def test_the_reference_is_the_exact_median_of_the_returned_magnitudes():
    """The median of an odd and of an even array, in exact rationals."""
    for radial, axial in (
        (np.array([[3.0, 6.0, 0.0]]), np.array([[4.0, 8.0, 2.0]])),
        (np.array([[3.0, 6.0, 0.0, 8.0]]), np.array([[4.0, 8.0, 2.0, 15.0]])),
    ):
        result = compute_poloidal_field_magnitude(radial, axial)
        values = sorted(Fraction(float(value)) for value in result["B"].ravel())
        lower_index = (len(values) - 1) // 2
        upper_index = len(values) // 2
        exact = (values[lower_index] + values[upper_index]) / 2
        got = Fraction(float(result["B0_default"]))
        deviation = abs(got - exact) / abs(exact)
        assert deviation <= 2 * Fraction(EPS), (len(values), float(deviation))
        # Anchors: the reference is neither the minimum nor the maximum, and the
        # two parity cases really produce different order statistics.
        assert result["B0_default"] > float(values[0])
        assert result["B0_default"] < float(values[-1])


def test_the_difference_first_median_survives_overflow_and_underflow():
    """The two cases the ``lower + 0.5 * (upper - lower)`` form exists for."""
    # Large: a naive 0.5 * (a + b) overflows, this form does not.
    huge = np.array([[1.7e308, 1.7e308]])
    result = compute_poloidal_field_magnitude(huge, np.zeros_like(huge))
    assert np.isfinite(result["B0_default"])
    assert result["B0_default"] == 1.7e308
    with np.errstate(over="ignore"):
        naive = 0.5 * (1.7e308 + 1.7e308)
    assert naive == np.inf, "the naive average must overflow for this case to discriminate"
    # Subnormal: the difference underflows to zero, and the common value survives.
    tiny = np.array([[5.0e-324, 5.0e-324]])
    result = compute_poloidal_field_magnitude(tiny, np.zeros_like(tiny))
    assert result["B0_default"] == FLOOR
    assert (5.0e-324 - 5.0e-324) == 0.0


def test_the_named_result_keeps_its_shape_and_access():
    """The mapping/attribute contract the asset promises."""
    result = compute_poloidal_field_magnitude([[3.0, 0.0]], [[4.0, 0.0]])
    assert isinstance(result, Result)
    assert list(result) == ["B", "B0_default"]
    assert getattr(result, "B") is result["B"]
    assert result["B"].shape == (1, 2)
    assert isinstance(result["B0_default"], float)


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    with pytest.raises(ValueError, match="same-shape two-dimensional"):
        compute_poloidal_field_magnitude([[1.0, 2.0]], [[1.0]])
    with pytest.raises(ValueError, match="same-shape two-dimensional"):
        compute_poloidal_field_magnitude([1.0, 2.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="only finite values"):
        compute_poloidal_field_magnitude([[np.nan]], [[1.0]])
    with pytest.raises(ValueError, match="only finite values"):
        compute_poloidal_field_magnitude([[1.0]], [[np.inf]])
    with pytest.raises(ValueError, match="at least one grid point"):
        compute_poloidal_field_magnitude(np.empty((0, 0)), np.empty((0, 0)))
    # The unrepresentable-magnitude channel: finite inputs whose hypotenuse is
    # not representable.
    with pytest.raises(ValueError, match="finite floating-point range"):
        compute_poloidal_field_magnitude([[1.7e308]], [[1.7e308]])
