"""Direct contract tests for ``scirel.collisions.hydrogen_proton_elastic_cross_section``.

The saved KN1DPy leaf (source anchor ``KN1DPy/sigma/sigma_el_p_h.py:1-42``,
caller ``KN1DPy/kinetic_h.py:996-1016``) fits the H+-on-H elastic
momentum-transfer cross section with a distinct logarithmic polynomial below
and above 10 eV, clipped to ``[0.001, 1.01e5] eV``. The Python source
incorrectly omitted the exact breakpoint. The corrected contract follows the
primary IDL low-energy branch at exactly 10 eV. The original leading singleton
output axis from ``np.array([E])`` remains unchanged. Negative energies are
rejected instead of silently clipped; all other fit coefficients and clipping
endpoints retain their original numerical assertions.
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
    low = clipped <= 10.0
    high = clipped > 10.0
    if np.any(low):
        result[low] = np.exp(
            np.polynomial.polynomial.polyval(np.log(clipped[low]), LOW_ENERGY_COEFFICIENTS)
        ) * 1.0e-4
    if np.any(high):
        result[high] = np.exp(
            np.polynomial.polynomial.polyval(np.log(clipped[high]), HIGH_ENERGY_COEFFICIENTS)
        ) * 1.0e-4
    return result


def test_piecewise_branches_match_independent_evaluation():
    energy = np.array([0.001, 1.0, 9.999, 10.001, 1.0e3, 1.01e5])
    actual = evaluate_hydrogen_proton_elastic_cross_section(energy)
    np.testing.assert_allclose(actual[0], independent_piecewise(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == (1, energy.size)


def test_breakpoint_uses_primary_idl_low_energy_branch():
    """The original IDL low branch includes the 10 eV breakpoint."""
    result = evaluate_hydrogen_proton_elastic_cross_section(np.array([9.999, 10.0, 10.001]))
    np.testing.assert_allclose(result[0][1], independent_piecewise(np.array([10.0]))[0], rtol=1e-15, atol=0)
    assert result[0][1] > 0
    assert result[0][0] > 0.0 and result[0][2] > 0.0


def test_leading_singleton_axis_is_preserved_for_any_input_rank():
    """Declared source convention: the result carries one extra leading axis."""
    one_d = evaluate_hydrogen_proton_elastic_cross_section(np.array([1.0, 100.0]))
    assert one_d.shape == (1, 2)
    two_d = evaluate_hydrogen_proton_elastic_cross_section(np.array([[1.0, 100.0]]))
    assert two_d.shape == (1, 1, 2)
    np.testing.assert_array_equal(two_d[0], one_d)


def test_endpoint_clipping_is_preserved():
    result = evaluate_hydrogen_proton_elastic_cross_section(np.array([0.0001, 0.001, 2.0e5, 1.01e5]))
    assert result[0][0] == result[0][1]
    assert result[0][-1] == result[0][-2]


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_hydrogen_proton_elastic_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen_proton_elastic_cross_section([1.0, np.nan])
