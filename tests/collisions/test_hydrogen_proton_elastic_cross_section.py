"""Direct contract tests for ``scirel.collisions.hydrogen_proton_elastic_cross_section``.

The canonical KN1DPy commit ``bb22c872`` leaf fits the H+-on-H elastic
momentum-transfer cross section with a distinct logarithmic polynomial below
and at/above 10 eV, clipped to ``[0.001, 1.01e5] eV``. The canonical Python
source uses the low-energy branch for ``E < 10`` and the high-energy branch for
``E >= 10``; exactly 10 eV is therefore the high-energy polynomial. The output
shape is the input shape. Negative energies are rejected instead of silently
clipped; all fit coefficients and clipping endpoints retain their original
numerical assertions.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen_proton_elastic_cross_section

LOW_ENERGY_COEFFICIENTS = np.array(
    [-3.233966e1, -1.126918e-1, 5.287706e-3, -2.445017e-3, -1.044156e-3, 8.419691e-5, 3.824773e-5],
    dtype=float,
)
HIGH_ENERGY_COEFFICIENTS = np.array([-3.231141e1, -1.386002e-1], dtype=float)


def independent_piecewise(energy):
    clipped = np.clip(energy, 0.001, 1.01e5)
    result = np.zeros_like(clipped, dtype=float)
    low = clipped < 10.0
    high = clipped >= 10.0
    if np.any(low):
        result[low] = (
            np.exp(np.polynomial.polynomial.polyval(np.log(clipped[low]), LOW_ENERGY_COEFFICIENTS))
            * 1.0e-4
        )
    if np.any(high):
        result[high] = (
            np.exp(
                np.polynomial.polynomial.polyval(np.log(clipped[high]), HIGH_ENERGY_COEFFICIENTS)
            )
            * 1.0e-4
        )
    return result


def test_piecewise_branches_match_independent_evaluation():
    energy = np.array([0.001, 1.0, 9.999, 10.001, 1.0e3, 1.01e5])
    actual = evaluate_hydrogen_proton_elastic_cross_section(energy)
    np.testing.assert_allclose(actual, independent_piecewise(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == energy.shape


def test_breakpoint_uses_canonical_high_energy_branch():
    """Canonical source: low for E<10, high for E>=10; 10 eV is high."""
    result = evaluate_hydrogen_proton_elastic_cross_section(np.array([9.999, 10.0, 10.001]))
    high_at_10 = (
        np.exp(np.polynomial.polynomial.polyval(np.log(10.0), HIGH_ENERGY_COEFFICIENTS)) * 1.0e-4
    )
    low_at_10 = (
        np.exp(np.polynomial.polynomial.polyval(np.log(10.0), LOW_ENERGY_COEFFICIENTS)) * 1.0e-4
    )
    np.testing.assert_allclose(result[1], high_at_10, rtol=1e-15, atol=0.0)
    assert not np.isclose(result[1], low_at_10, rtol=1e-14, atol=0.0)
    assert result[0] > 0.0 and result[1] > 0.0 and result[2] > 0.0


def test_output_shape_preserves_input_shape_for_any_input_rank():
    """Canonical source convention: no extra leading singleton axis."""
    one_d = evaluate_hydrogen_proton_elastic_cross_section(np.array([1.0, 100.0]))
    assert one_d.shape == (2,)
    two_d = evaluate_hydrogen_proton_elastic_cross_section(np.array([[1.0, 100.0]]))
    assert two_d.shape == (1, 2)
    np.testing.assert_array_equal(two_d[0], one_d)


def test_endpoint_clipping_is_preserved():
    result = evaluate_hydrogen_proton_elastic_cross_section(
        np.array([0.0001, 0.001, 2.0e5, 1.01e5])
    )
    assert result[0] == result[1]
    assert result[-1] == result[-2]


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_hydrogen_proton_elastic_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen_proton_elastic_cross_section([1.0, np.nan])
