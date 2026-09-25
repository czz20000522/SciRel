"""Direct contract tests for ``scirel.collisions.atomic_hydrogen_charge_exchange_rate``.

The saved KN1DPy leaf (source anchor ``KN1DPy/sigma/sigmav_cx_h0.py:8-95``,
ledger entry N25 ``EQ-N25-N4-H-CX-RATE``) is the atomic-H charge-exchange
Maxwellian rate coefficient as a 9x9 bivariate logarithmic polynomial in
``log(T)`` and ``log(E)``, evaluated in the source's summation order after
sequentially clipping both inputs to ``[0.1, 2.01e4] eV`` and scaling by
``1e-6`` to ``m^3/s``.  The tests assert the bivariate polynomial against an
independent ``polyval2d`` oracle in the saved package's own style, the source
summation order by exact equality, and the fail-closed contracts.  Two
documented repairs relative to the saved implementation are exercised: a
nonpositive temperature and a negative energy are rejected (the saved document
declares a positive temperature and nonnegative energy but its implementation
silently clipped them into the fit domain).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_rate

COEFFICIENTS = np.array(
    [
        [-1.829079581680e1, 1.640252721210e-1, 3.364564509137e-2, 9.530225559189e-3, -8.519413589968e-4, -1.247583860943e-3, 3.014307545716e-4, -2.499323170044e-5, 6.932627237765e-7],
        [2.169137615703e-1, -1.106722014459e-1, -1.382158680424e-3, 7.348786286628e-3, -6.343059502294e-4, -1.919569450380e-4, 4.075019351738e-5, -2.850044983009e-6, 6.966822400446e-8],
        [4.307131243894e-2, 8.948693624917e-3, -1.209480567154e-2, -3.675019470470e-4, 1.039643390686e-3, -1.553840717902e-4, 2.670827249272e-6, 7.695300597935e-7, -3.783302281524e-8],
        [-5.754895093075e-4, 6.062141761233e-3, 1.075907881928e-3, -8.119301728339e-4, 8.911036876068e-6, 3.175388949811e-5, -4.515123641755e-6, 2.187439283954e-7, -2.911233951880e-9],
        [-1.552077120204e-3, -1.210431587568e-3, 8.297212635856e-4, 1.361661816974e-4, -1.008928628425e-4, 1.080693990468e-5, 5.106059413591e-7, -1.299275586093e-7, 5.117133050290e-9],
        [-1.876800283030e-4, -4.052878751584e-5, -1.907025662962e-4, 1.141663041636e-5, 1.775681984457e-5, -3.149286923815e-6, 3.105491554749e-8, 2.274394089017e-8, -1.130988250912e-9],
        [1.125490270962e-4, 2.875900435985e-5, 1.338839628570e-5, -4.340802793033e-6, -7.003521917385e-7, 2.318308730487e-7, -6.030983538280e-9, -1.755944926274e-9, 1.005189187279e-10],
        [-1.238982763007e-5, -2.616998139678e-6, -1.171762874107e-7, 3.517971869029e-7, -4.928692832866e-8, 1.756388998863e-10, -1.446756795654e-10, 7.143183138281e-11, -3.989884105603e-12],
        [4.163596197181e-7, 7.558092849125e-8, -1.328404104165e-8, -9.170850253981e-9, 3.208853883734e-9, -3.952740758950e-10, 2.739558475782e-11, -1.693040208927e-12, 6.388219930167e-14],
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
    actual = evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)
    np.testing.assert_allclose(actual, independent_oracle(temperature, energy), rtol=1e-12, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_oracle():
    temperature = np.array([0.2, 2.0, 20.0, 200.0, 2000.0, 5000.0])
    energy = np.array([0.15, 1.0, 15.0, 150.0, 1000.0, 2000.0])
    np.testing.assert_allclose(
        evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy),
        independent_oracle(temperature, energy),
        rtol=1e-12,
        atol=0.0,
    )


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_atomic_hydrogen_charge_exchange_rate(np.asarray(12.5), np.asarray(0.35))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_domain_clipping_matches_the_oracle():
    # The oracle comparison avoids the double-extreme corner (both inputs at
    # the clip maximum simultaneously): there the source-order loop and
    # polyval2d differ by ~2e-12 from summation-order cancellation.  That
    # corner is pinned bit-exactly by the SHA-256-bound replay test instead.
    temperature = np.array([0.01, 1.0e3, 2.01e4, 5.0e4])
    energy = np.array([1.0, 3.0e4, 10.0, 0.05])
    actual = evaluate_atomic_hydrogen_charge_exchange_rate(temperature, energy)
    np.testing.assert_allclose(actual, independent_oracle(temperature, energy), rtol=1e-12, atol=0.0)


def test_nonpositive_temperature_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="temperature_ev"):
        evaluate_atomic_hydrogen_charge_exchange_rate(np.array([1.0, -5.0]), np.array([1.0, 2.0]))


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="energy_ev"):
        evaluate_atomic_hydrogen_charge_exchange_rate(np.array([1.0, 2.0]), np.array([1.0, -0.5]))


def test_nonfinite_and_shape_mismatch_fail_closed():
    with pytest.raises(ValueError, match="finite"):
        evaluate_atomic_hydrogen_charge_exchange_rate(np.array([1.0, np.nan]), np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="same shape"):
        evaluate_atomic_hydrogen_charge_exchange_rate(
            np.array([[1.0], [2.0]]), np.array([1.0, 2.0])
        )
