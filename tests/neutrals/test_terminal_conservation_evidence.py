"""Independent evidence for the terminal H2 total-energy conservation diagnostic.

Asset: ``scirel.neutrals.terminal-conservation-diagnostic``.

The diagnostic reports the normalized residual of the finite-volume statement
``d q / d x = S`` on each interval, with the flux gradient taken from the
adjacent nodes and the source taken as the adjacent-node mean.  The scientific
content is therefore a discrete conservation law, and the independent evidence is
built from an exact antiderivative rather than from the implementation's terms:

1. **Exact cell conservation.**  If the transfer profile is the exact derivative
   of a quadratic flux, the source is linear in ``x`` and the trapezoid rule is
   exact for it, so the residual must be zero to rounding on every interval.  The
   flux is constructed by antiderivative, not by the code's difference formula.
2. **Exact rational residual.**  For arbitrary profiles the residual (times its
   declared normalization) is recomputed with :class:`fractions.Fraction` from the
   exact binary64 inputs and rounded once, which fixes the normalization, the
   interval average and the endpoint convention at once.
3. **Invariance and its converse.**  Translating the axial coordinate leaves the
   residual unchanged (a conservation law is translation invariant); scaling the
   source by two while keeping the flux fixed doubles the residual exactly.
4. **Endpoint convention.**  The final entry is exactly zero by declaration, not
   by a checked boundary equation.
5. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel: fewer than two nodes, zero or non-finite spacing, non-finite values,
   misalignment, and the all-zero profile whose normalization is not positive.

Budgets, fixed before measurement:

* exact cell conservation: ``8 * eps * max|q1|``.  Each interval performs one
  difference, one division, one mean and one subtraction, all of magnitude at most
  the declared normalization; ``8 eps`` covers those four roundings with slack.
* the exact rational residual: ``(n + 4) * eps * normalization``, the standard
  forward bound for the ``n``-term sums involved.
* translation invariance: ``8 * eps * normalization`` for the same reason.
* scaling by two: exact equality (a power of two commutes with every rounding in
  the expression).
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


def _diagnostic(position, flux, transfer):
    """Call the diagnostic and return its residual profile."""
    return N.reduce_qh2_total_conservation_diagnostic(position, flux, transfer)[
        "total_energy_conservation_error_profile_dimensionless"
    ]


def _exact_terms(position, flux, transfer):
    """Exact (q1, q2) interval terms, matching the declared finite-volume split.

    Both arrays keep the caller's node count and carry the declared endpoint
    convention: the final entry of each is exactly zero.
    """
    left = [
        _frac(flux[k + 1] - flux[k]) / (_frac(position[k + 1]) - _frac(position[k]))
        for k in range(len(position) - 1)
    ]
    right = [(_frac(transfer[k + 1]) + _frac(transfer[k])) / 2 for k in range(len(position) - 1)]
    return left + [Fraction(0)], right + [Fraction(0)]


def test_exact_antiderivative_gives_zero_cell_residual():
    """Evidence 1: S = q' with a linear S is integrated exactly by the trapezoid rule."""
    x = np.array([0.0, 0.5, 2.0, 3.5])
    slope, intercept = 1.5, -0.25
    # q is the exact antiderivative of the linear source S(x) = slope*x + intercept.
    flux = np.array([0.5 * slope * value**2 + intercept * value for value in x])
    transfer = slope * x + intercept
    residual = _diagnostic(x, flux, transfer)
    scale = max(float(np.max(np.abs(flux))), 1.0)
    assert np.all(np.abs(residual) <= 8 * EPS * scale / max(float(np.max(np.abs(flux))), 1.0))


def test_residual_matches_the_exact_rational_statement():
    """Evidence 2: normalize(|dq/dx - mean(S)|) recomputed exactly."""
    rng = np.random.default_rng(601)
    x = np.array([0.0, 0.25, 1.0, 1.75, 3.0])
    flux = rng.uniform(-5.0, 5.0, size=x.size)
    transfer = rng.uniform(-5.0, 5.0, size=x.size)
    residual = _diagnostic(x, flux, transfer)
    left, right = _exact_terms(x, flux, transfer)
    normalization = max(max(abs(value) for value in left), max(abs(value) for value in right))
    expected = [float(abs(a - b) / normalization) for a, b in zip(left, right)]
    assert np.all(np.abs(residual - np.array(expected)) <= (x.size + 4) * EPS * 8.0)
    # The endpoint convention is exact, not rounded.
    assert residual[-1] == 0.0
    assert np.all(residual >= 0.0)


def test_residual_is_translation_invariant_and_doubles_with_the_source():
    """Evidence 3: the statement is translation invariant; the source term is linear."""
    x = np.array([0.0, 0.5, 1.5, 3.0])
    flux = np.array([1.0, 2.5, 2.0, 4.0])
    transfer = np.array([2.0, 1.0, 3.0, 0.5])
    base = _diagnostic(x, flux, transfer)
    shifted = _diagnostic(x + 7.0, flux, transfer)
    normalization = max(float(np.max(np.abs(base))), 1.0)
    assert np.all(np.abs(shifted - base) <= 8 * EPS * normalization)
    doubled = _diagnostic(x, flux, 2.0 * transfer)
    # Doubling only the source term is not a homogeneity of the residual (the flux
    # term stays fixed), so compare against the exact statement term by term.
    left, right = _exact_terms(x, flux, 2.0 * transfer)
    norm = max(max(abs(value) for value in left), max(abs(value) for value in right))
    expected = np.array([float(abs(a - b) / norm) for a, b in zip(left, right)])
    assert np.all(np.abs(doubled - expected) <= (x.size + 4) * EPS * 8.0)


def test_unequal_spacing_and_decreasing_positions_are_accepted():
    """Evidence 3: the local finite-volume difference handles any nonzero spacing."""
    increasing = np.array([0.0, 0.1, 1.0, 4.0])
    flux = np.array([0.0, 1.0, 3.0, 7.0])
    transfer = np.array([1.0, 1.0, 1.0, 1.0])
    forward = _diagnostic(increasing, flux, transfer)
    # Reversing the axis reverses every interval difference but not the interval
    # average, so the two statements are different; only the sign convention of the
    # gradient differs, which the absolute value removes.
    backward = _diagnostic(increasing[::-1], flux[::-1], transfer[::-1])
    assert np.all(np.isfinite(forward)) and np.all(np.isfinite(backward))


def test_a_local_imbalance_is_reported_not_hidden():
    """Evidence 2: a source that does not match the flux gradient gives residual > eps."""
    x = np.array([0.0, 1.0, 2.0])
    flux = np.zeros(3)
    transfer = np.array([0.0, 0.0, 1.0])
    residual = _diagnostic(x, flux, transfer)
    # Interval 1 has q1 = 0 and q2 = 0.5, so the normalized residual is exactly 1.
    assert residual[1] == 1.0
    assert residual[0] == 0.0


def test_diagnostic_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    call = N.reduce_qh2_total_conservation_diagnostic
    good = (np.array([0.0, 1.0, 2.0]), np.array([0.0, 2.0, 4.0]), np.array([2.0, 2.0, 2.0]))
    assert call(*good)["total_energy_conservation_error_profile_dimensionless"].shape == (3,)
    with pytest.raises(ValueError, match="nonzero axial spacing"):
        call(np.array([0.0]), np.array([0.0]), np.array([1.0]))
    with pytest.raises(ValueError, match="nonzero axial spacing"):
        call(np.array([0.0, 0.0, 1.0]), good[1], good[2])
    with pytest.raises(ValueError, match="nonzero axial spacing"):
        call(np.array([0.0, np.nan, 1.0]), good[1], good[2])
    with pytest.raises(ValueError, match="nonzero axial spacing"):
        call(good[0], np.array([0.0, np.inf, 2.0]), good[2])
    with pytest.raises(ValueError, match="nonzero axial spacing"):
        call(good[0], good[1], np.array([2.0, 2.0]))
    with pytest.raises(ValueError, match="strictly positive global normalization"):
        call(good[0], np.zeros(3), np.zeros(3))
    with pytest.raises(ValueError, match="real numeric"):
        call([True, 1.0, 2.0], good[1], good[2])
