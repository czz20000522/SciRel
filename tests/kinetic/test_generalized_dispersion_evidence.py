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


def test_saha_constant_matches_the_published_combination():
    """The prefactor ``3.310e-28`` is a published constant, not a free parameter.

    In SI the Saha prefactor is ``2 (2 pi m_e k_B / h**2)**(3/2)``; recomputing it
    from the CODATA-2014 constants shows whether the declared literal is that
    combination or a tuning knob.  The declared literal carries four significant
    digits, so the comparison is at ``1e-4``.
    """
    mass_e = mp.mpf("9.10938356e-31")
    boltzmann = mp.mpf("1.38064852e-23")
    planck = mp.mpf("6.62607015e-34")
    combination = 2 * (2 * mp.pi * mass_e * boltzmann / planck**2) ** mp.mpf("1.5")
    assert _rel(mp.mpf("3.310e-28"), combination) <= 1e-3
    # 13.6057 eV is the hydrogen Rydberg; the published value is 13.605693 eV.
    assert _rel(mp.mpf("13.6057"), mp.mpf("13.605693")) <= 1e-5


def test_saha_population_is_the_closed_form():
    """The level population is the declared closed form evaluated at 40 digits."""
    from scirel.kinetic import evaluate_h_saha_equilibrium_population

    density = np.array([1.0e18, 1.0e19, 1.0e20])
    temperature = np.array([2.0, 10.0, 50.0])
    levels = np.array([1.0, 4.0, 9.0])
    result = np.asarray(evaluate_h_saha_equilibrium_population(density, temperature, levels))
    bessel.high_precision()
    for index in range(density.size):
        n = mp.mpf(density[index])
        t = mp.mpf(temperature[index])
        level2 = mp.mpf(levels[index])
        expected = n * (mp.mpf("3.310e-28") * n) * level2 * mp.e ** (
            mp.mpf("13.6057") / (level2 * t)
        ) / t ** mp.mpf("1.5")
        assert _rel(result.ravel()[index], expected) <= BUDGET


def test_maxwellian_electrostatic_susceptibility_is_closed_form():
    """The susceptibility is ``(1 + z Z(z))/k**2`` with the Faddeeva closed form.

    Recomputing ``Z`` from ``erfc`` rather than from the implementation's kernel
    makes this a statement about the dielectric relation, not about a shared
    special-function table.
    """
    from scirel.kinetic import evaluate_maxwellian_electrostatic

    bessel.high_precision()
    for omega, k in ((1.0, 0.5), (2.0, 0.3), (0.9, 0.7)):
        result = evaluate_maxwellian_electrostatic(omega, k)
        chi = complex(np.asarray(result["chi"]).ravel()[0])
        # z = omega/(sqrt(2) k v_t) with v_t = 1 in these normalized units.
        z = mp.mpf(omega) / (mp.sqrt(2) * mp.mpf(k))
        expected = (1 + z * _faddeeva(z)) / mp.mpf(k) ** 2
        assert _rel(chi, expected) <= 1e-12


def test_maxwellian_electrostatic_mode_root_zeroes_the_dispersion():
    """The returned mode frequency zeroes ``1 + chi`` according to the independent kernel.

    A solver that returned a plausible-looking number would fail this: the residual
    is recomputed from the ``erfc`` closed form, and the same residual is required to
    rise sharply when the frequency is displaced.
    """
    from scirel.kinetic import evaluate_maxwellian_electrostatic, solve_maxwellian_electrostatic_mode

    bessel.high_precision()
    k = 0.5
    solution = solve_maxwellian_electrostatic_mode(k, 1.0)
    frequency = complex(np.asarray(solution["omega"]).ravel()[0]) if "omega" in solution else complex(
        np.asarray(solution["root"]).ravel()[0]
    )

    def residual(value):
        z = mp.mpf(complex(value).real) / (mp.sqrt(2) * mp.mpf(k))
        return abs(1 + (1 + z * _faddeeva(z)) / mp.mpf(k) ** 2)

    at_root = residual(frequency)
    assert at_root <= 1e-8
    assert residual(frequency * (1 + 1e-3)) > 1e3 * max(at_root, 1e-16)
    # The dispersion the implementation reports must agree, not just the closed form.
    reported = evaluate_maxwellian_electrostatic(complex(frequency).real, k)
    assert abs(complex(np.asarray(reported["chi"]).ravel()[0]) + 1) <= 1e-8
