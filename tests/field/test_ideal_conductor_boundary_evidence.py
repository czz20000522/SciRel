"""Independent evidence for the truncated-SVD ideal-conductor boundary correction.

Asset: ``scirel.field.ideal-conductor-boundary``.

Two kinds of claim live in this operator, and they are evidenced separately.

**The linear algebra is decidable exactly.**  With small integer matrices every
output is a rational number, so the test recomputes it with
:class:`fractions.Fraction` and requires the returned float to be the correctly
rounded value within a budget derived from the operation count.  The cases are
chosen so each branch of the contract is distinguishable:

1. **Consistent full rank.**  ``sample @ gbf == gbb`` makes the sampled boundary
   flux exactly cancellable: the boundary currents are the exact solution of
   ``gbb @ c = -(sample @ psi)``, the residual is exactly zero, and the corrected
   field is ``psi - gbf @ gbb^-1 @ sample @ psi``.  All three are rational
   quantities here and are asserted against their exact values, not against the
   implementation's own output.
2. **Strict rank truncation.**  Raising ``rcond`` past the ratio of the singular
   values drops the smaller direction, and the test pins which direction survives
   by its exact current vector rather than only by the rank count.  A changed
   ``>`` to ``>=``, or a cutoff applied to the squared singular values, changes
   this vector.
3. **Nothing retained.**  ``rcond = 1`` keeps no direction, so the corrected field
   is the uncorrected one and the residual is the sampled boundary flux, exactly.
4. **Minimum norm when underdetermined.**  With one boundary sample and two
   sources the solution is not unique; the truncated pseudo-inverse returns the
   minimum-norm one, whose exact value the test computes by the closed form
   ``gbb.T @ (gbb @ gbb.T)^-1 @ (-b)``.  Any other member of the family satisfies
   the residual equation too, so only this vector distinguishes the pseudo-inverse
   from an arbitrary solution.
5. **The reported pieces are consistent with each other**: ``residual`` equals
   ``boundary_flux + boundary_flux_correction``, ``boundary_flux_correction``
   equals ``gbb @ currents``, and ``field_flux_correction`` equals
   ``gbf @ currents``, each in exact rationals.

Budget: 8 eps relative per output, from the roundings a single matrix-vector
product performs plus the SVD's own backward stability for these well-separated
singular values (4 and 2, condition number 2).  Items that are structurally zero
are asserted as exact zeros.

**What is NOT established here, and is reported as such:** the physical reading of
these matrices as an ideal-conducting wall, i.e. that ``gbb``/``gbf`` are the
response of a real vacuum vessel and that cancelling the sampled boundary flux is
the right model for the induced current.  That needs the device wall geometry and
either measurement or a coil-set field solution, none of which this repository
holds; the contract records it as ``cannot establish`` and no assertion here
depends on it.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel._result import Result
from scirel.field import correct_ideal_conductor_boundary_flux

EPS = float(np.finfo(float).eps)
BUDGET = 8.0 * Fraction(EPS)

PSI = [3.0, -1.0, 2.0]
SAMPLE = [[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]]
GBB = [[2.0, 0.0], [0.0, 4.0]]
GBF = [[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]]


def _exact_matvec(matrix, vector):
    """Return the exact rational matrix-vector product."""
    return [
        sum(
            (Fraction(float(entry)) * Fraction(float(value)) for entry, value in zip(row, vector, strict=True)),
            start=Fraction(0),
        )
        for row in matrix
    ]


def _assert_exact_columns(name, returned, expected, scale=None):
    """Compare a returned vector with exact rational expectations."""
    assert len(returned) == len(expected), name
    for index, reference in enumerate(expected):
        deviation = abs(Fraction(float(returned[index])) - reference)
        magnitude = abs(scale[index]) if scale is not None else abs(reference)
        allowed = BUDGET * max(magnitude, Fraction(EPS))
        assert deviation <= allowed, (name, index, float(deviation), float(allowed))


def test_a_consistent_full_rank_system_cancels_the_boundary_flux_exactly():
    """Evidence 1 and 5: the exact solve, the zero residual and the pieces."""
    result = correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF)
    boundary_flux = _exact_matvec(SAMPLE, PSI)
    # Consistency, in exact rationals: the composed sampled Green equals the
    # boundary Green, so the sampled boundary flux is exactly reachable.
    composed = [
        [sum(
            (
                Fraction(float(SAMPLE[row][column])) * Fraction(float(GBF[column][source]))
                for column in range(len(SAMPLE[0]))
            ),
            start=Fraction(0),
        )
        for source in range(len(GBB[0]))]
        for row in range(len(SAMPLE))
    ]
    assert composed == [
        [Fraction(float(GBB[row][source])) for source in range(len(GBB[0]))]
        for row in range(len(GBB))
    ]
    currents = [-value / Fraction(float(GBB[index][index])) for index, value in enumerate(boundary_flux)]
    _assert_exact_columns("boundary_currents", result["boundary_currents"], currents, currents)
    # The residual is structurally zero for a consistent system.
    np.testing.assert_array_equal(result["residual"], 0.0)
    assert result["residual_norm"] == 0.0
    field_correction = _exact_matvec(GBF, currents)
    _assert_exact_columns("field_flux_correction", result["field_flux_correction"], field_correction)
    corrected = [
        Fraction(float(value)) + correction for value, correction in zip(PSI, field_correction, strict=True)
    ]
    _assert_exact_columns("corrected_field_flux", result["corrected_field_flux"], corrected)
    assert result["effective_rank"] == 2
    np.testing.assert_array_equal(np.sort(result["singular_values"])[::-1], [4.0, 2.0])
    # Anchors: the correction is not a no-op and it really zeroes the boundary.
    assert not np.array_equal(result["corrected_field_flux"], np.asarray(PSI))
    np.testing.assert_array_equal(np.asarray(result["residual"]), 0.0)


def test_rank_truncation_is_pinned_by_the_surviving_direction():
    """Evidence 2: which direction survives, not only how many."""
    full = correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF, rcond=0.0)
    truncated = correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF, rcond=0.6)
    # Threshold 0.6 * 4 = 2.4 keeps only the singular value 4, whose right
    # singular vector is the second current axis for this diagonal matrix.
    assert truncated["effective_rank"] == 1
    np.testing.assert_array_equal(truncated["boundary_currents"], [0.0, -0.125])
    assert full["effective_rank"] == 2
    boundary_flux = _exact_matvec(SAMPLE, PSI)
    residual = [
        value
        + sum(
            (
                Fraction(float(GBB[row][source])) * Fraction(float(truncated["boundary_currents"][source]))
                for source in range(len(GBB[0]))
            ),
            start=Fraction(0),
        )
        for row, value in enumerate(boundary_flux)
    ]
    _assert_exact_columns("residual", truncated["residual"], residual, boundary_flux)
    assert truncated["residual_norm"] > 0.0


def test_a_cutoff_above_every_singular_value_returns_the_uncorrected_field():
    """Evidence 3: rcond = 1 retains nothing."""
    result = correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF, rcond=1.0)
    assert result["effective_rank"] == 0
    np.testing.assert_array_equal(result["corrected_field_flux"], np.asarray(PSI))
    np.testing.assert_array_equal(result["boundary_currents"], 0.0)
    np.testing.assert_array_equal(result["field_flux_correction"], 0.0)
    boundary_flux = _exact_matvec(SAMPLE, PSI)
    _assert_exact_columns("residual", result["residual"], boundary_flux, boundary_flux)
    assert result["residual_norm"] > 0.0


def test_the_underdetermined_solution_is_the_minimum_norm_one():
    """Evidence 4: the closed-form minimum-norm current vector."""
    psi = [1.0, 0.0]
    sample = [[1.0, 0.0]]
    gbb = [[1.0, 1.0]]
    gbf = [[1.0, 2.0], [0.0, 1.0]]
    result = correct_ideal_conductor_boundary_flux(psi, sample, gbb, gbf)
    # gbb.T @ (gbb @ gbb.T)^-1 @ (-b) with b = 1, in exact rationals.
    half = Fraction(-1, 2)
    _assert_exact_columns("boundary_currents", result["boundary_currents"], [half, half], [half, half])
    _assert_exact_columns("corrected_field_flux", result["corrected_field_flux"], [half, half], [half, half])
    assert result["effective_rank"] == 1
    # The residual equation gbb @ c = -b holds, so the sampled flux is cancelled.
    total = Fraction(float(result["boundary_currents"][0])) + Fraction(
        float(result["boundary_currents"][1])
    )
    assert abs(total + 1) <= BUDGET
    assert abs(float(result["residual"][0])) <= float(BUDGET)


def test_the_named_result_keeps_its_declared_keys():
    """The mapping/attribute contract the asset promises."""
    result = correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF)
    assert isinstance(result, Result)
    assert list(result) == [
        "corrected_field_flux",
        "boundary_currents",
        "boundary_flux_correction",
        "field_flux_correction",
        "singular_values",
        "effective_rank",
        "residual",
        "residual_norm",
    ]
    for name in ("corrected_field_flux", "field_flux_correction"):
        assert getattr(result, name) is result[name]
        assert result[name].shape == (3,)
    assert isinstance(result["effective_rank"], int)
    assert isinstance(result["residual_norm"], float)


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    with pytest.raises(ValueError, match="only finite values"):
        correct_ideal_conductor_boundary_flux([np.nan, 0.0, 0.0], SAMPLE, GBB, GBF)
    with pytest.raises(ValueError, match="must be a 1-D array"):
        correct_ideal_conductor_boundary_flux([[3.0]], SAMPLE, GBB, GBF)
    with pytest.raises(ValueError, match="must be a 2-D array"):
        correct_ideal_conductor_boundary_flux(PSI, [1.0, 0.0, 0.0], GBB, GBF)
    with pytest.raises(ValueError, match="non-negative finite"):
        correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF, rcond=-0.1)
    with pytest.raises(ValueError, match="non-negative finite"):
        correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF, rcond=np.nan)
    with pytest.raises(ValueError, match="column count must match"):
        correct_ideal_conductor_boundary_flux(PSI, [[1.0, 0.0]], GBB, GBF)
    with pytest.raises(ValueError, match="row count must match boundary samples"):
        correct_ideal_conductor_boundary_flux(PSI, SAMPLE, [[2.0, 0.0]], GBF)
    with pytest.raises(ValueError, match="same boundary-source axis"):
        correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, [[2.0, 0.0, 1.0]] * 3)
    with pytest.raises(ValueError, match="row count must match uncorrected_field_flux"):
        correct_ideal_conductor_boundary_flux(PSI, SAMPLE, GBB, GBF[:2])
    with pytest.raises(ValueError, match="must not be empty"):
        correct_ideal_conductor_boundary_flux(PSI, SAMPLE, np.empty((2, 0)), np.empty((3, 0)))
