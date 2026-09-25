"""Direct contract tests for ``scirel.collisions.hydrogen2_charge_exchange_rate``.

The saved KN1DPy leaf (source anchor ``KN1DPy/sigma/sigmav_cx_hh.py:5-95``,
ledger entry N15 ``EQ-N15-H2-CX-RATE``) is the H2 charge-exchange Maxwellian
rate coefficient as a 9x9 bivariate logarithmic polynomial in ``log(T)`` and
``log(E)``, evaluated in the source's summation order after sequentially
clipping both inputs to ``[0.1, 2.01e4] eV`` and scaling by ``1e-6`` to
``m^3/s``.  The tests assert the bivariate polynomial against an independent
``polyval2d`` oracle in the saved package's own style, the source summation
order by exact equality, and the fail-closed contracts.  Two documented
repairs relative to the saved implementation are exercised: a nonpositive
temperature and a negative energy are rejected (the saved document declares a
positive temperature and nonnegative energy but its implementation silently
clipped them into the fit domain).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen2_charge_exchange_rate

COEFFICIENTS = np.array(
    [
        [-2.013143517466e01, 1.875197914224e-01, 6.865479604288e-02, 6.246595384100e-03, -5.017891372102e-03, -3.907644829287e-04, 2.786239030986e-04, -2.942576591004e-05, 9.352275354690e-07],
        [2.643458086299e-01, -1.177247941077e-01, -6.758032286178e-03, 8.585003721992e-03, -3.261863407467e-04, -3.322528542186e-04, 6.015471216449e-05, -4.039435357369e-06, 9.730479674748e-08],
        [7.295645990688e-02, 6.053418575149e-03, -1.068656224307e-02, -9.371235639464e-04, 9.735708783528e-04, -9.933049259228e-05, -6.786246802840e-06, 1.438327767305e-06, -5.530742535057e-08],
        [-1.022454343675e-02, 7.350954380641e-03, 6.814213275702e-04, -8.156435157073e-04, 2.903991825737e-05, 3.223596225946e-05, -5.199055182831e-06, 2.852443990256e-07, -4.825480212106e-09],
        [-4.801198168030e-03, -1.111612877392e-03, 8.373319888351e-04, 1.392977576749e-04, -9.316910697276e-05, 8.814981236658e-06, 6.675626166047e-07, -1.325441927019e-07, 5.012529587757e-09],
        [1.141613586234e-03, -1.371389288760e-04, -1.733761953296e-04, 1.602610140599e-05, 1.464235749797e-05, -2.944711701791e-06, 6.365231650682e-08, 1.872976659964e-08, -1.014883015867e-09],
        [-3.388853048483e-05, 4.426148343648e-05, 9.992317920676e-06, -5.333970870280e-06, -2.999105886511e-07, 2.275612517364e-07, -1.173422836715e-08, -1.364602870139e-09, 9.566404348683e-11],
        [-6.418225985394e-06, -3.652063962019e-06, 1.351312819077e-07, 4.285396408056e-07, -7.184302986068e-08, -3.265552364687e-10, 1.585228996542e-10, 6.431866226702e-11, -4.507074278992e-12],
        [3.555592819527e-07, 1.012701361110e-07, -1.993091213299e-08, -1.131561847140e-08, 3.678869095972e-09, -3.639982258214e-10, 2.056662091085e-11, -1.804254277469e-12, 9.042973335167e-14],
    ],
    dtype=float,
)


def independent_oracle(temperature, energy):
    clipped_temperature = np.minimum(np.maximum(np.asarray(temperature, dtype=float), 0.1), 2.01e4)
    clipped_energy = np.minimum(np.maximum(np.asarray(energy, dtype=float), 0.1), 2.01e4)
    return np.exp(
        np.polynomial.polynomial.polyval2d(
            np.log(clipped_energy), np.log(clipped_temperature), COEFFICIENTS.T
        )
    ) * 1.0e-6


def test_bivariate_fit_matches_independent_oracle():
    temperature = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 2.01e4, 5.0])
    energy = np.array([0.2, 0.2, 1.0, 10.0, 100.0, 1.0e3, 1.0, 2.01e4])
    actual = evaluate_hydrogen2_charge_exchange_rate(temperature, energy)
    np.testing.assert_allclose(actual, independent_oracle(temperature, energy), rtol=1e-12, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_oracle():
    temperature = np.array([0.2, 2.0, 20.0, 200.0, 2000.0, 5000.0])
    energy = np.array([0.15, 1.0, 15.0, 150.0, 1000.0, 2000.0])
    np.testing.assert_allclose(
        evaluate_hydrogen2_charge_exchange_rate(temperature, energy),
        independent_oracle(temperature, energy),
        rtol=1e-12,
        atol=0.0,
    )


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_hydrogen2_charge_exchange_rate(np.asarray(12.5), np.asarray(0.35))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_domain_clipping_matches_the_oracle():
    # The double-extreme clip corner is pinned bit-exactly by the SHA-256-bound
    # replay test; summation-order cancellation puts the source loop and
    # polyval2d ~2e-12 apart there, as recorded for the atomic sibling.
    temperature = np.array([0.01, 1.0e3, 2.01e4, 5.0e4])
    energy = np.array([1.0, 3.0e4, 10.0, 0.05])
    actual = evaluate_hydrogen2_charge_exchange_rate(temperature, energy)
    np.testing.assert_allclose(actual, independent_oracle(temperature, energy), rtol=1e-12, atol=0.0)


def test_nonpositive_temperature_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="temperature_ev"):
        evaluate_hydrogen2_charge_exchange_rate(np.array([1.0, -5.0]), np.array([1.0, 2.0]))


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="energy_ev"):
        evaluate_hydrogen2_charge_exchange_rate(np.array([1.0, 2.0]), np.array([1.0, -0.5]))


def test_nonfinite_and_shape_mismatch_fail_closed():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen2_charge_exchange_rate(np.array([1.0, np.nan]), np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="same shape"):
        evaluate_hydrogen2_charge_exchange_rate(np.array([[1.0], [2.0]]), np.array([1.0, 2.0]))
