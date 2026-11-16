"""Independent evidence for the frozen Z-function and L-pole tables.

Assets: ``scirel.kinetic.z-pole-coefficients``,
``scirel.kinetic.rational-z-poles``, ``scirel.kinetic.rational-jpole-coefficients``,
``scirel.kinetic.gamma-lpole-coefficients``.

Evidence sources, none of them the implementation or its fixtures:

1. **The large-|z| expansion of Z as an oracle for every table.**  The Maxwellian
   dispersion function has ``Z(z) = -1/z - 1/(2 z**3) - 3/(4 z**5) - ...`` for
   ``|z| -> infinity``.  A table declared as ``Z_J(z) = sum_j b_j/(z - c_j)``
   therefore has to satisfy, exactly and for *any* pole count,

   ``sum b_j = -1``, ``sum b_j c_j = 0``, ``sum b_j c_j**2 = -1/2``.

   These three moment identities are consequences of the target function alone.
   They hold for the tables here, they fail for a table with a wrong residue, and
   they are not derivable from the implementations.
2. **The definition at 40 digits.**  ``Z(z) = i sqrt(pi) w(z)`` with
   ``w(z) = exp(-z**2) erfc(-i z)`` from ``mpmath`` at ``mp.dps = 40``.  The
   rational sum is compared with it, which measures the table's *model* error.
3. **The construction residual.**  ``jpole_coefficients`` declares the matching
   equations to be solved at a decimal precision (default 80); its own
   ``high_precision_linear_residual`` and per-pole root residuals are the
   construction's algebraic residual and must be far below the binary64 output
   rounding.  This is a check of the declared construction, not of Z.

Budgets, fixed before the comparison was run.  The moment identities are
algebraic, so they are asserted at ``1e-12`` absolute (a few hundred ulp of the
``O(1)`` sums).  The Z comparison is a model-error observation with a ceiling
chosen from the pole count, not from the data: four poles cannot be held to more
than ``1e-1`` relative on the sampled upper half plane, while eight or more poles
are held to ``1e-5``, the ceiling this project already declares for the tabulated
family.  The construction residual is held below ``1e-60``, twenty orders of
magnitude under the ``1e-80`` decimal precision the function declares, so a
construction that silently falls back to binary64 arithmetic fails.

``gamma-lpole-coefficients`` is recorded as **cannot establish**: see the last
test of this module and the contract's ``known_limitations``.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import (
    get_gamma_lpole_coefficients,
    get_z_pole_coefficients,
)
from scirel.kinetic.dispersion import magnetized, rational

mp.mp.dps = 40

UPPER_HALF_PLANE = [
    0.1 + 0.2j,
    0.5 + 0.5j,
    1.0 + 0.3j,
    -2.0 + 0.4j,
    2.0 + 1.0j,
    3.0 + 0.5j,
]


def _z_reference(z: complex):
    value = mp.mpc(z)
    return mp.sqrt(mp.pi) * mp.mpc(0, 1) * mp.exp(-(value**2)) * mp.erfc(-mp.mpc(0, 1) * value)


def _rational(z: complex, residues, poles) -> complex:
    return complex(np.sum(np.asarray(residues) / (complex(z) - np.asarray(poles))))


def _assert_moments(residues, poles):
    """Evidence 1: the three exact consequences of the Z asymptotic."""
    b = np.asarray(residues)
    c = np.asarray(poles)
    assert abs(np.sum(b) - (-1.0)) <= 1e-12
    assert abs(np.sum(b * c) - 0.0) <= 1e-12
    assert abs(np.sum(b * c * c) - (-0.5)) <= 1e-12


def _assert_matches_z(residues, poles, ceiling):
    """Evidence 2: model error against the 40-digit definition."""
    worst = 0.0
    for z in UPPER_HALF_PLANE:
        got = _rational(z, residues, poles)
        want = complex(_z_reference(z))
        worst = max(worst, abs(got - want) / abs(want))
    assert worst <= ceiling, (worst, ceiling)


@pytest.mark.parametrize("j_order", [8, 12])
def test_z_pole_table_satisfies_the_moments_and_bounds_its_model_error(j_order):
    """Evidence 1 and 2 for ``get_z_pole_coefficients``."""
    table = get_z_pole_coefficients(j_order=j_order)
    _assert_moments(table["bzj"], table["czj"])
    _assert_matches_z(table["bzj"], table["czj"], 1e-5)
    # The returned closed-form diagnostics are those same sums.
    assert abs(table["sum_bzj"] - np.sum(table["bzj"])) <= 1e-15
    assert abs(table["sum_bzcj"] - np.sum(table["bzj"] * table["czj"])) <= 1e-15
    assert abs(table["sum_bzcj2"] - np.sum(table["bzj"] * table["czj"] ** 2)) <= 1e-15


def test_z_pole_table_second_half_is_the_declared_conjugate_completion():
    """The stored half-table and the completed half obey the stated pairing."""
    for j_order in (8, 12):
        table = get_z_pole_coefficients(j_order=j_order)
        half = j_order // 2
        np.testing.assert_array_equal(table["bzj"][half:], np.conj(table["bzj"][:half]))
        np.testing.assert_array_equal(table["czj"][half:], -np.conj(table["czj"][:half]))


@pytest.mark.parametrize("j_order", [4, 8, 12])
def test_magnetized_pole_table_satisfies_the_moments(j_order):
    """Evidence 1 on the J4/J8/J12 table selected by ``pole_coefficients``."""
    state = magnetized.pole_coefficients(j_order).state
    residues = np.ravel(state["bzj"])
    poles = np.ravel(state["czj"])
    assert residues.size == j_order
    _assert_moments(residues, poles)
    _assert_matches_z(residues, poles, 1e-1 if j_order == 4 else 1e-5)


def test_jpole_construction_residual_is_far_below_binary64():
    """Evidence 3: the declared 80-digit construction, asserted before rounding."""
    state = rational.jpole_coefficients()
    assert state["J"] == 12
    assert state["precision_digits"] == 80
    linear = abs(mp.mpf(str(state["high_precision_linear_residual"])))
    roots = [abs(mp.mpf(str(value))) for value in state["high_precision_root_residual"]]
    assert linear <= mp.mpf("1e-60")
    assert max(roots) <= mp.mpf("1e-60")
    moments = np.asarray(state["moments"], dtype=complex)
    np.testing.assert_allclose(moments, [-1.0, 0.0, -0.5], atol=1e-12)


def test_jpole_coefficients_and_evaluate_agree_with_z_and_each_other():
    """The coefficients' own sum and the public evaluator both target ``Z_J``.

    ``jpole_evaluate`` is declared as ``Z_J(z) = sum b_j/(z - c_j)``.  The two
    routes are compared with each other only to pin the declared shape and pole
    alignment; the accuracy claim comes from the 40-digit comparison.
    """
    state = rational.jpole_coefficients()
    residues = np.ravel(np.asarray(state["bzj"]))
    poles = np.ravel(np.asarray(state["czj"]))
    _assert_moments(residues, poles)
    _assert_matches_z(residues, poles, 1e-5)
    points = np.array(UPPER_HALF_PLANE)
    evaluated = np.asarray(rational.jpole_evaluate(residues, poles, points)["ZJ"])
    direct = np.array([_rational(z, residues, poles) for z in points])
    np.testing.assert_allclose(evaluated, direct, rtol=1e-14, atol=1e-15)


def test_jpole_evaluate_preserves_shape_and_rejects_the_declared_channels():
    """Shape matrix plus the declared rejection channels of the evaluator."""
    residues = np.array([1.0 + 0j, -1.0 + 0j])
    poles = np.array([2.0 + 0j, -2.0 + 0j])
    assert np.asarray(rational.jpole_evaluate(residues, poles, np.array([]))["ZJ"]).shape == (0,)
    for shape in [(1,), (2, 3)]:
        points = np.zeros(shape, dtype=complex)
        assert np.asarray(rational.jpole_evaluate(residues, poles, points)["ZJ"]).shape == shape
    with pytest.raises(ValueError, match="aligned"):
        rational.jpole_evaluate(residues, np.array([1.0]), np.array([0j]))
    with pytest.raises(ValueError, match="finite"):
        rational.jpole_evaluate(residues, poles, np.array([np.nan]))
    with pytest.raises(ZeroDivisionError, match="pole"):
        rational.jpole_evaluate(residues, poles, np.array([2.0 + 0j]))


def test_gamma_lpole_table_structure_and_declared_rejections():
    """Only the structural facts are established for the L-pole table.

    The table is frozen data with no in-repository derivation and no public
    tabulation, so its numeric values are ``cannot establish``; what is asserted
    here is the declared key convention, the pole count, the conjugate pairing of
    the stored entries, and every declared rejection channel.
    """
    table = get_gamma_lpole_coefficients(max_harmonic=7)
    assert table["orders"] == list(range(1, 9))
    counts = [table["order_lengths"][order] for order in range(1, 9)]
    # Higher harmonics need at least as many poles as lower ones to resolve the
    # |n| oscillation, and the total is the sum of the per-order counts.
    assert counts == sorted(counts)
    assert table["total_poles"] == sum(counts)
    for order in range(1, 9):
        residues = table["residues"][order]
        poles = table["poles"][order]
        assert residues.size == poles.size == table["order_lengths"][order]
        assert np.all(np.isfinite(residues)) and np.all(np.isfinite(poles))
        # Every pole has a conjugate partner: the frozen table is Hermitian.
        for pole in poles:
            assert np.min(np.abs(poles - np.conj(pole))) <= 1e-12 * max(1.0, abs(pole))

    with pytest.raises(ValueError, match="non-negative integer"):
        get_gamma_lpole_coefficients(max_harmonic=-1)
    with pytest.raises(ValueError, match="non-negative integer"):
        get_gamma_lpole_coefficients(max_harmonic=1.5)
    with pytest.raises(ValueError, match="non-negative integer"):
        get_gamma_lpole_coefficients(max_harmonic=True)
    with pytest.raises(ValueError, match="frozen table only reaches"):
        get_gamma_lpole_coefficients(max_harmonic=8)


def test_the_gamma_lpole_sum_is_not_a_pointwise_scaled_bessel_value():
    """A measured negative result, recorded so no contract claims otherwise.

    Whatever the frozen L-pole table represents, ``sum_l r_l/(p_l - p)`` is not
    ``exp(-b) I_n(b)`` at real ``b``: the deviation is tens of percent, far above
    any rounding or model-error reading of a 12-pole approximation.  This test
    pins the measurement; it does not license a reinterpretation of the table.
    """
    table = get_gamma_lpole_coefficients(max_harmonic=2)
    for order, n in ((1, 0), (2, 1)):
        residues = table["residues"][order]
        poles = table["poles"][order]
        for b in (0.8, 2.0, 4.0):
            approximant = complex(np.sum(residues / (poles - b)))
            if n == 0:
                want = complex(mp.besseli(0, mp.mpf(b)) * mp.exp(-mp.mpf(b)))
            else:
                want = complex(mp.besseli(n, mp.mpf(b)) * mp.exp(-mp.mpf(b)))
            assert abs(approximant - want) > 0.05 * abs(want), (n, b)


def test_z_pole_and_gamma_lpole_reject_unsupported_orders():
    """One assertion per declared rejection channel of the two table readers."""
    with pytest.raises(ValueError, match="8 or 12"):
        get_z_pole_coefficients(j_order=6)
    with pytest.raises(ValueError, match="must be an integer"):
        get_z_pole_coefficients(j_order=8.5)
    with pytest.raises(ValueError, match="must be an integer"):
        get_z_pole_coefficients(j_order=True)
    with pytest.raises(ValueError, match="J must be 4, 8 or 12"):
        magnetized.pole_coefficients(6)
