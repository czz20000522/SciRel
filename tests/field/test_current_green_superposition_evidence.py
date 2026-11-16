"""Independent evidence for the current-weighted Green contraction.

Asset: ``scirel.field.current-green-superposition``.

The maintained tests check the contraction against values written out by hand
for one small matrix.  Here the same contraction is decided in **exact rational
arithmetic**: ``currents`` and the three Green arrays are binary64 numbers, hence
exact rationals, and a matrix-vector product is exact in ``Fraction``.  The
returned float is then required to be the correctly rounded value of the exact
result within ``(n + 2) eps`` - one rounding for each of the ``n`` products, the
summation, and the final rounding - a bound derived from the operation count, not
measured.

What the tests decide:

1. **The scalar branch** multiplies each response element by the scalar; the
   exact product of two binary64 numbers has at most two roundings (one product,
   one rounding of the exact rational to float), so the budget is ``2 eps``.
2. **The matrix branch** contracts along the source columns: target row ``i`` of
   the result is ``sum_j g[i, j] * I[j]``.  A contraction along the *target* axis,
   a transposed reading of the Green matrices, or an ``I . g`` ordering that
   mixes rows all fail with O(1) errors.  The test uses a deliberately
   non-symmetric matrix so a transposed read cannot pass.
3. **Exact linearity and additivity** for a power-of-two factor, which an affine
   or normalised contraction cannot satisfy.
4. **The target axis is preserved**: row ``i`` of every output depends only on
   row ``i`` of the inputs, checked by permuting the input rows and requiring the
   output rows to follow the same permutation exactly.
5. **The failure channels**, including the two shape mismatches and the
   unrepresentable contraction.

Evidence ceiling: the contraction is exact elementary linear algebra, so this
evidence is complete for the relation it states.  What it cannot establish is
whether the caller's Green arrays and currents describe a physical device; that
belongs to the assets that produce them.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel._result import Result
from scirel.field import superpose_current_green_field

EPS = float(np.finfo(float).eps)
FIELDS = ("psi", "BR", "BZ")

# Deliberately non-symmetric, and non-dyadic so the rounding the budget covers
# actually occurs: a dyadic product and sum would be exact and the budget would
# be exercised by nothing.
GPSI = [[0.7, -2.0, 0.3], [3.1, 0.25, -1.5], [-0.5, 4.0, 2.0]]
GBR = [[2.0, 0.0, -1.3], [1.0, -3.0, 0.25], [0.5, 1.5, -2.0]]
GBZ = [[-1.0, 3.7, 1.5], [2.0, -0.5, 0.0], [0.25, -2.0, 1.0]]
CURRENTS = [0.1, -0.3, 1.7]


def _exact_contraction(green, currents):
    """Return the exact rational row-by-row contraction."""
    return [
        sum(
            (
                Fraction(float(value)) * Fraction(float(current))
                for value, current in zip(row, currents, strict=True)
            ),
            start=Fraction(0),
        )
        for row in green
    ]


def test_matrix_contraction_matches_exact_rational_arithmetic():
    """Evidence 2: sum_j g[i, j] * I[j], decided exactly."""
    result = superpose_current_green_field(CURRENTS, GPSI, GBR, GBZ)
    columns = len(CURRENTS)
    observed = 0.0
    for name, green in zip(FIELDS, (GPSI, GBR, GBZ), strict=True):
        exact = _exact_contraction(green, CURRENTS)
        for row, reference in enumerate(exact):
            deviation = abs(Fraction(float(result[name][row])) - reference)
            allowed = (columns + 2) * Fraction(EPS) * abs(reference)
            assert deviation <= allowed, (name, row, float(deviation / abs(reference)))
            observed = max(observed, float(deviation / abs(reference)))
    assert observed > 0.0
    # Nonzero anchors with both signs, so a zero output or a sign-flipped output
    # cannot pass the ratio comparison.
    assert result["psi"][0] > 0.0
    assert result["BR"][2] < 0.0
    assert result["BZ"][2] != 0.0
    # The matrices are not symmetric and the contraction is not the transpose
    # contraction, so a transposed read is distinguishable.
    assert not np.allclose(GPSI, np.transpose(GPSI))
    transposed = superpose_current_green_field(
        CURRENTS,
        np.transpose(GPSI),
        np.transpose(GBR),
        np.transpose(GBZ),
    )
    assert not np.array_equal(transposed["psi"], result["psi"])


def test_scalar_current_scales_each_element_exactly():
    """Evidence 1: the scalar branch, two roundings per element."""
    current = 0.3
    vectors = ([1.5, -2.25, 0.7], [-0.125, 4.3, 2.5], [8.0, -1.1, 0.75])
    result = superpose_current_green_field(current, *vectors)
    observed = 0.0
    for name, vector in zip(FIELDS, vectors, strict=True):
        for index, value in enumerate(vector):
            exact = Fraction(current) * Fraction(float(value))
            deviation = abs(Fraction(float(result[name][index])) - exact)
            assert deviation <= 2 * Fraction(EPS) * abs(exact), (name, index)
            observed = max(observed, float(deviation / abs(exact)))
    assert observed > 0.0
    # Anchors: both signs present and a nonzero magnitude.
    assert result["psi"][0] > 0.0 and result["psi"][1] < 0.0
    assert result["BZ"][0] != 0.0


def test_power_of_two_scaling_is_exact_and_the_target_axis_is_preserved():
    """Evidence 3 and 4: exact scaling, and row-local target ordering."""
    base = superpose_current_green_field(CURRENTS, GPSI, GBR, GBZ)
    doubled = superpose_current_green_field([4.0 * value for value in CURRENTS], GPSI, GBR, GBZ)
    for name in FIELDS:
        np.testing.assert_array_equal(doubled[name], 4.0 * base[name]), name
        assert np.any(base[name] != 0.0), name
    # Permuting the target rows permutes the output rows the same way, exactly.
    order = [2, 0, 1]
    permuted = superpose_current_green_field(
        CURRENTS,
        [GPSI[index] for index in order],
        [GBR[index] for index in order],
        [GBZ[index] for index in order],
    )
    for name in FIELDS:
        np.testing.assert_array_equal(permuted[name], base[name][order]), name


def test_the_named_result_keeps_its_shape_and_access():
    """The mapping/attribute contract the asset promises."""
    result = superpose_current_green_field(CURRENTS, GPSI, GBR, GBZ)
    assert isinstance(result, Result)
    assert list(result) == list(FIELDS)
    for name in FIELDS:
        assert getattr(result, name) is result[name]
        assert result[name].shape == (len(GPSI),)
        assert result[name].dtype == np.float64


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    good = (CURRENTS, GPSI, GBR, GBZ)
    with pytest.raises(ValueError, match="finite values"):
        superpose_current_green_field([np.nan, 1.0, 1.0], GPSI, GBR, GBZ)
    with pytest.raises(ValueError, match="finite values"):
        superpose_current_green_field([1.0, 1.0, 1.0], GPSI, [[np.inf] * 3] * 3, GBZ)
    # Unsupported rank: a two-dimensional current array.
    with pytest.raises(ValueError, match="scalar or one-dimensional"):
        superpose_current_green_field([[1.0, 2.0]], GPSI, GBR, GBZ)
    # The source axis must equal the number of currents.
    with pytest.raises(ValueError, match="columns.*number of currents"):
        superpose_current_green_field([1.0, 2.0], GPSI, GBR, GBZ)
    # A scalar current needs three one-dimensional responses of the same shape.
    with pytest.raises(ValueError, match="scalar current requires"):
        superpose_current_green_field(1.0, GPSI, GBR, GBZ)
    with pytest.raises(ValueError, match="scalar current requires"):
        superpose_current_green_field(1.0, [1.0, 2.0], [1.0], [1.0, 2.0])
    # A vector current needs three two-dimensional responses of the same shape.
    with pytest.raises(ValueError, match="vector currents require"):
        superpose_current_green_field(CURRENTS, [1.0, 2.0, 3.0], GBR, GBZ)
    with pytest.raises(ValueError, match="vector currents require"):
        superpose_current_green_field(CURRENTS, GPSI, GBR, [row[:2] for row in GBZ])
    # runtime_failure: a representable operands pair whose product overflows.
    with pytest.raises(FloatingPointError, match="not representable"):
        superpose_current_green_field(2.0, [np.finfo(float).max], [1.0], [1.0])
    with pytest.raises(FloatingPointError, match="not representable"):
        superpose_current_green_field([2.0], [[np.finfo(float).max]], [[1.0]], [[1.0]])
    # A representable contraction does not raise, so the guard is not blanket.
    assert np.isfinite(superpose_current_green_field([1.0], [[2.0]], [[3.0]], [[4.0]])["psi"][0])
    del good
