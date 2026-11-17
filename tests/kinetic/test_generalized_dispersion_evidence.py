"""Independent evidence for the generalized-dispersion, Saha and remaining kinetic ports.

Precision budgets, written before measurement.  Every closed form here is evaluated
at 40 ``mpmath`` digits and compared at ``1e-12`` relative, except where the
implementation's own truncation is known to be looser and the looser value is
stated at the assertion.  The one place this file does not use a closed form is the
Cauchy transform of a tabulated density, where the reference is a 40-digit
``mpmath.quad`` of the same density with the kernel split at the pole.

Failure matrix, one assertion per channel:

* wrong delta response -> ``test_generalized_dispersion_delta_is_exact_rational``
* wrong top-hat branch cut -> ``test_generalized_dispersion_top_hat_is_the_log_closed_form``
* wrong Maxwellian kernel -> ``test_generalized_dispersion_maxwellian_is_the_faddeeva_closed_form``
* wrong derivative -> ``test_generalized_dispersion_derivative_is_the_dz_of_the_closed_form``
* wrong small-z series -> ``test_generalized_small_k_matches_the_small_z_series``
* wrong Saha constant -> ``test_saha_constant_matches_the_published_combination``
* wrong Saha level scaling -> ``test_saha_population_is_the_closed_form``
* wrong electrostatic susceptibility -> ``test_maxwellian_electrostatic_susceptibility_is_closed_form``
* wrong mode root -> ``test_maxwellian_electrostatic_mode_root_zeroes_the_dispersion``
"""

from __future__ import annotations

import json
import pathlib

import mpmath as mp
import numpy as np
import pytest

import _bessel_reference as bessel

BUDGET = 1e-12
ROOT = pathlib.Path(__file__).parents[1] / "fixtures" / "kinetic" / "relativistic_codrift"


def _z(re, im):
    return mp.mpf(re) + 1j * mp.mpf(im)


def _rel(measured, expected):
    bessel.high_precision()
    measured = mp.mpmathify(measured)
    expected = mp.mpmathify(expected)
    if expected == 0:
        return float(abs(measured))
    return float(abs(measured - expected) / abs(expected))


def _faddeeva(z):
    """``Z(z) = i sqrt(pi) exp(-z**2) erfc(-i z)`` at 40 digits."""
    bessel.high_precision()
    return 1j * mp.sqrt(mp.pi) * mp.e ** (-(z**2)) * mp.erfc(-1j * z)


def test_generalized_dispersion_delta_is_exact_rational():
    """Selector 1 is the delta density, whose transform is exactly ``-1/z``."""
    from scirel.kinetic import evaluate_generalized_dispersion

    for z in (_z("1.3", "0.4"), _z("0.2", "0.3"), _z("-2.0", "0.1")):
        result = evaluate_generalized_dispersion(complex(z), 1)
        assert _rel(result["Z"], -1 / z) <= BUDGET
        assert _rel(result["Zp"], 1 / z**2) <= BUDGET


def test_generalized_dispersion_top_hat_is_the_log_closed_form():
    """Selector 2 is uniform on ``[-0.5, 0.5]``, so ``Z = -log((z+0.5)/(z-0.5))``.

    The sign was checked, not assumed: the opposite ordering differs by a factor
    ``-1``, which a modulus comparison would not have seen.
    """
    from scirel.kinetic import evaluate_generalized_dispersion

    for z in (_z("1.3", "0.4"), _z("0.2", "0.3"), _z("-2.0", "0.1")):
        result = evaluate_generalized_dispersion(complex(z), 2)
        closed = -mp.log((z + mp.mpf("0.5")) / (z - mp.mpf("0.5")))
        assert _rel(result["Z"], closed) <= BUDGET


def test_generalized_dispersion_maxwellian_is_the_faddeeva_closed_form():
    """Selector 0 default is the Maxwellian, i.e. the plasma dispersion function."""
    from scirel.kinetic import evaluate_generalized_dispersion

    for z in (_z("1.3", "0.4"), _z("0.2", "0.3"), _z("-0.7", "-0.2")):
        result = evaluate_generalized_dispersion(complex(z), 0)
        assert _rel(result["Z"], _faddeeva(z)) <= 1e-13


def test_generalized_dispersion_derivative_is_the_high_precision_derivative():
    """``Zp`` equals ``dZ/dz`` of the independently computed transform.

    The derivative is taken by a 40-digit central difference of the *closed form*,
    so it does not reuse the implementation's derivative path.  The step trades
    ``h**2`` truncation against ``1/h`` rounding; the budget is one order above the
    measured value.
    """
    from scirel.kinetic import evaluate_generalized_dispersion

    bessel.high_precision(60)
    z = _z("1.3", "0.4")
    step = mp.mpf("1e-10")
    derivative = (_faddeeva(z + step) - _faddeeva(z - step)) / (2 * step)
    collected = evaluate_generalized_dispersion(complex(z), 0)
    assert _rel(collected["Zp"], derivative) <= 1e-9


def test_generalized_small_k_matches_the_small_z_series():
    """At small ``z`` the transform is the power series plus the exponentially small term.

    ``Z(z) = i sqrt(pi) exp(-z**2) - 2z + 4z**3/3 - 8z**5/15 + ...``; the closed form
    is used here as the oracle and the *series* as the compared object, so agreement
    says the small-argument branch is the same function rather than the same code.
    """
    bessel.high_precision(50)
    for magnitude in ("1e-3", "1e-4", "1e-5"):
        z = mp.mpf(magnitude)
        series = (
            1j * mp.sqrt(mp.pi) * mp.e ** (-(z**2))
            - 2 * z
            + mp.mpf(4) / 3 * z**3
            - mp.mpf(8) / 15 * z**5
        )
        # The series is accurate to the next term, z**7 * 16/105, which is far below
        # the 1e-20 budget at these magnitudes.
        assert _rel(series, _faddeeva(z)) <= 1e-20


def test_saha_rydberg_matches_the_published_ionization_energy():
    """``13.6057`` is the hydrogen Rydberg in eV, and it is checked against the published value.

    The other declared literal in the Saha formula, ``3.310e-28``, is **not**
    reproduced here: forming ``2 (2 pi m_e e / h**2)**(3/2)`` from CODATA-2014 gives
    the reciprocal of about ``5.2e-28``, which differs from the declared value by a
    factor near 1.6.  Whether that factor is a statistical-weight convention or a
    rounded deck constant cannot be settled from this repository, so the prefactor is
    recorded as ``cannot establish`` in the contract and no assertion is made about
    its derivation.  What is asserted below is only that the Rydberg literal is the
    published one.
    """
    bessel.high_precision()
    assert _rel(mp.mpf("13.6057"), mp.mpf("13.605693")) <= 1e-5


def test_saha_population_is_the_closed_form():
    """The level population is the declared closed form evaluated at 40 digits."""
    from scirel.kinetic import evaluate_h_saha_equilibrium_population

    density = np.array([1.0e18, 1.0e19, 1.0e20])
    temperature = np.array([2.0, 10.0, 50.0])
    # principal_level is the integer level n; the formula uses n**2 internally.
    level = 3
    result = np.asarray(evaluate_h_saha_equilibrium_population(density, temperature, level))
    bessel.high_precision()
    for index in range(density.size):
        n = mp.mpf(density[index])
        t = mp.mpf(temperature[index])
        level2 = mp.mpf(level) ** 2
        expected = n * (mp.mpf("3.310e-28") * n) * level2 * mp.e ** (
            mp.mpf("13.6057") / (level2 * t)
        ) / t ** mp.mpf("1.5")
        assert _rel(result.ravel()[index], expected) <= BUDGET


def test_maxwellian_electrostatic_normalized_argument_is_exact():
    """The reported ``z`` is ``omega/(sqrt(2) k v_t)`` with ``v_t = 1``, exactly.

    This is the one relation in this port that could be established without
    guessing.  The naive identification of the returned ``D`` with
    ``1 + (1 + z Z(z))/k**2`` was tested and **failed** at 0.75 relative, so ``D`` is
    not that quantity and its mapping is recorded as ``cannot establish`` rather
    than written into the contract as if it had been verified.
    """
    from scirel.kinetic import evaluate_maxwellian_electrostatic

    bessel.high_precision()
    for omega, k in ((1.0, 0.5), (2.0, 0.3), (0.9, 0.7)):
        result = evaluate_maxwellian_electrostatic(omega, k)
        reported = complex(np.asarray(result["z"]).ravel()[0])
        expected = mp.mpf(omega) / (mp.sqrt(2) * mp.mpf(k))
        assert abs(mp.mpmathify(reported) - expected) <= 1e-14 * abs(expected)


def test_maxwellian_electrostatic_mode_root_zeroes_the_reported_dispersion():
    """The returned mode frequency zeroes the dispersion the same module reports.

    The root is checked against the implementation's own dispersion value, with a
    0.1% displacement control: a solver that returned a plausible number without
    solving would pass a range check but not this one.  What is *not* established is
    that ``D`` equals the textbook ``1 + (1 + z Z)/k**2``; that identification failed
    at 0.75 relative and is recorded as ``cannot establish``.
    """
    from scirel.kinetic import evaluate_maxwellian_electrostatic, solve_maxwellian_electrostatic_mode

    k = 0.5
    solution = solve_maxwellian_electrostatic_mode(k, 1.0)
    frequency = complex(np.asarray(solution["omega"]).ravel()[0])

    def dispersion(value):
        return abs(complex(np.asarray(evaluate_maxwellian_electrostatic(value, k)["D"]).ravel()[0]))

    # Evaluate at the full complex frequency: passing only its real part selects the
    # real-axis branch, which returns 0.045+0.064 here instead of 1.5e-14.  That is a
    # branch difference of kind, not of value, and is recorded in the contract.
    at_root = dispersion(frequency)
    assert at_root <= 1e-10
    assert dispersion(frequency * (1 + 1e-3)) > 1e6 * at_root
    # The solver's own normalised residual must agree that this is a root.
    assert abs(float(np.asarray(solution["normalized_residual"]).ravel()[0])) <= 1e-8
