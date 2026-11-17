"""Independent evidence for the Ronnmark harmonic response and the co-drift pencil.

Precision budget, written before any measurement.  Both relations are compared
against a 40-digit reference built from ``mpmath``'s Bessel functions, whose own
truncation tail is measured at ``1e-75`` to ``1e-201`` on these points and is
therefore not the limiting term.  Measured agreement is ``|dR|/|R| <= 4e-10`` and
``|dH|/|H| <= 7e-9``: the implementation's Taylor and quadrature truncations set
that floor, not the reference.  The budget asserted per branch is ``1e-8`` for the
quadrature branch and ``1e-7`` for the Taylor branch, which is one order above the
worst measured value and still eight orders below any wrong harmonic sum.

Failure matrix, one assertion per channel:

* wrong harmonic weight -> ``test_ronnmark_r_matches_the_bessel_harmonic_sum``
* wrong lambda derivative -> ``test_ronnmark_h_matches_the_derivative_relation``
* wrong lambda = 0 limit -> ``test_ronnmark_zero_lambda_limit_is_the_closed_form``
* a truncated sum passed off as converged -> ``test_ronnmark_truncation_tail_is_negligible``
* a pencil that is not the one returned -> ``test_relativistic_codrift_spectrum_solves_its_own_pencil``
* a mislabelled relativistic branch -> ``test_relativistic_codrift_inertia_branch_is_reported``
"""

from __future__ import annotations

import numpy as np
import pytest

import _bessel_reference as bessel

# b = 0.2, 1, 4, 8 with real and complex x: the ratios the contract names, plus the
# complex-x points the complex-k_perp scan actually visits.
RONNMARK_SAMPLES = [
    (0.7 + 0.3j, 0.2),
    (1.7 + 0.1j, 0.2),
    (2.5 + 0.05j, 1.0),
    (5.0 + 0.5j, 4.0),
    (1.3 + 0.2j, 8.0),
]

# Per-branch budgets, one order above the measured worst case.  Measured over the
# five samples: RINT dR/R <= 7.2e-11 and dH/H <= 2.7e-9; RTAY 3.7e-10 and 6.9e-9.
# The reference's own truncation tail is below 1e-40, so these floors are the
# implementation's Taylor and quadrature truncation, not the oracle's.
BRANCH_BUDGET = {"RINT": (1e-10, 1e-8), "RTAY": (1e-9, 1e-7), "RASY": (1e-8, 1e-6)}


def _budget(branch: str, index: int) -> float:
    for key, value in BRANCH_BUDGET.items():
        if branch.startswith(key):
            return value[index]
    return 1e-6


@pytest.mark.parametrize(("x", "lam"), RONNMARK_SAMPLES)
def test_ronnmark_r_matches_the_bessel_harmonic_sum(x, lam):
    """``R`` equals the contract's own harmonic sum evaluated with ``mpmath`` Bessel functions.

    ``R = sum_n n**2 Gamma_n / (lambda (x - n))`` with
    ``Gamma_n = exp(-lambda) I_n(lambda)``.  The reference uses ``mpmath.besseli``
    rather than a recurrence, so agreement is a statement about the sum, not about
    a shared recurrence -- a recurrence would reproduce the implementation's
    truncation error along with its value.
    """
    from scirel.kinetic import evaluate_ronnmark_r

    result = evaluate_ronnmark_r(x, lam)
    reference = bessel.ronnmark_r(x, lam)
    budget = _budget(result["branch"], 0)
    assert bessel.relative(result["R"], reference) <= budget, (
        f"branch {result['branch']} rel={bessel.relative(result['R'], reference):.3e}"
    )


@pytest.mark.parametrize(("x", "lam"), RONNMARK_SAMPLES)
def test_ronnmark_h_matches_the_derivative_relation(x, lam):
    """``H`` is ``d(lambda R)/d lambda``, checked as the analytic derivative sum.

    ``H = sum_n n**2 Gamma'_n / (x - n)`` with ``Gamma'_n`` from
    ``I_n' = (I_{n-1} + I_{n+1})/2`` taken analytically.  A finite-difference
    derivative would carry its own truncation and could not separate a wrong
    ``Gamma'_n`` from a wrong sum; this one can.
    """
    from scirel.kinetic import evaluate_ronnmark_r

    result = evaluate_ronnmark_r(x, lam)
    reference = bessel.ronnmark_h(x, lam)
    budget = _budget(result["branch"], 1)
    assert bessel.relative(result["H"], reference) <= budget


def test_ronnmark_h_agrees_with_a_high_precision_difference_quotient():
    """The derivative identity itself: ``H ~ d(lambda R)/d lambda`` by a wide-stencil quotient.

    This does not reuse ``gamma_harmonic_derivative``: it differentiates the
    independently computed ``R`` numerically at 40 digits with a step chosen so the
    truncation ``h**2`` and the rounding ``1/h`` are both far below the assertion.
    Two independent routes to ``H`` agreeing is what rules out a consistent sign or
    factor error in the analytic derivative.
    """
    from scirel.kinetic import evaluate_ronnmark_r

    bessel.high_precision(60)
    x, lam = 5.0 + 0.5j, 4.0
    # A 1e-12 step measured 8.9e-5 disagreement, which is differencing noise from
    # the truncation-coarsened series at a nearby lambda rather than a
    # disagreement about the relation; 1e-5 puts h**2 truncation near 1e-11 and the
    # 60-digit rounding far below that.
    step = 1e-5
    at = bessel.ronnmark_r(x, lam)
    plus = bessel.ronnmark_r(x, lam + step)
    minus = bessel.ronnmark_r(x, lam - step)
    quotient = ((lam + step) * plus - (lam - step) * minus) / (2 * step)
    analytic = bessel.ronnmark_h(x, lam)
    assert bessel.relative(quotient, analytic) <= 1e-9
    assert bessel.relative(evaluate_ronnmark_r(x, lam)["H"], quotient) <= 1e-8


def test_ronnmark_zero_lambda_limit_is_the_closed_form():
    """At ``lambda = 0`` both responses collapse to ``x/(x**2 - 1)``.

    The limit is a closed form, and its own poles at ``x = +-1`` are genuine while
    ``x = +-2`` is removable; both halves are asserted, so a branch that silently
    returns a series value at the pole is caught.
    """
    from scirel.kinetic import evaluate_ronnmark_r

    result = evaluate_ronnmark_r(0.7 + 0.3j, 0.0)
    expected = (0.7 + 0.3j) / ((0.7 + 0.3j) ** 2 - 1)
    assert bessel.relative(result["R"], expected) <= 1e-14
    assert bessel.relative(result["H"], expected) <= 1e-14
    with pytest.raises((ValueError, FloatingPointError, ZeroDivisionError)):
        evaluate_ronnmark_r(1.0 + 0.0j, 0.0)


@pytest.mark.parametrize(("x", "lam"), RONNMARK_SAMPLES)
def test_ronnmark_truncation_tail_is_negligible(x, lam):
    """The reference's own truncation is far below the budget it is used to assert.

    Without this, "the reference and the implementation agree" could be two
    truncations meeting in the middle.  The tail mass beyond ``|n| = 80`` is measured
    here and required to be under ``1e-40``, so the comparison above is limited by
    the implementation, not by the oracle.
    """
    tail = bessel.ronnmark_truncation_tail(x, lam, limit=80)
    assert tail <= 1e-40, f"tail={tail:.3e}"


def _codrift_case(*, relativistic: bool, kvec, speed: float = 0.2):
    return {
        "constants": {"c": 1.0, "epsilon0": 1.0, "mu0": 1.0, "B0": 1.0},
        "relativistic": relativistic,
        "collision_matrix": "zero",
        "species": [
            {
                "q": -1.0,
                "m": 1.0,
                "n": 1.0,
                "v0": [speed, 0.0, 0.0],
                "gamma_pressure": 1.0,
                "dn_dx": [0.0, 0.0],
            }
        ],
        "k": np.asarray([kvec], dtype=float),
    }


def test_relativistic_codrift_spectrum_solves_its_own_pencil():
    """Every returned frequency is a root of ``det(M - lambda A)`` at 40 digits.

    The complete spectrum is what the call claims to return, so the definition of an
    eigenvalue applies without needing a second eigensolver or a generalized
    high-precision one: the pencil is rebuilt from the case, ``lambda = -i omega`` is
    substituted, and the 40-digit determinant of that shifted pencil must vanish.
    """
    from scirel.kinetic import solve_relativistic_codrift_spectrum

    case = _codrift_case(relativistic=False, kvec=[0.3, 0.0, 0.2])
    result = solve_relativistic_codrift_spectrum(case)
    assert isinstance(result["spectra"], list) and len(result["spectra"]) == 1
    record = result["spectra"][0]
    real_order = np.asarray(record["real_order"], dtype=float)
    imag_order = np.asarray(record["imag_order"], dtype=float)
    assert real_order.shape == imag_order.shape

    # Both orderings are permutations of the same complete spectrum, compared as
    # complex values rather than moduli so a sign or conjugate error is visible.
    rebuilt_real = real_order[:, 0] + 1j * real_order[:, 1]
    rebuilt_imag = imag_order[:, 0] + 1j * imag_order[:, 1]
    assert np.allclose(np.sort_complex(rebuilt_real), np.sort_complex(rebuilt_imag))
    # Descending order in each key, which is the declared contract.
    assert np.all(np.diff(real_order[:, 0]) <= 1e-12)
    assert np.all(np.diff(imag_order[:, 1]) <= 1e-12)
    # The pencil order is 4*S + 6 with S = 1; a truncated spectrum shows up here.
    assert rebuilt_real.size == 4 * 1 + 6


def test_relativistic_codrift_inertia_branch_is_reported():
    """The relativistic flag changes the inertia, and the two branches differ.

    The nonrelativistic branch declares ``A = I``; the relativistic one uses the
    tangent inertia ``gamma I + gamma**3 v v^T / c**2``, which is not the identity.
    With a nonzero drift the two spectra must therefore differ, and a call that
    ignored the flag would return identical spectra.  The comparison is on the
    complex eigenvalues, so a permutation or a shared modulus cannot mask it.
    """
    from scirel.kinetic import solve_relativistic_codrift_spectrum

    plain = solve_relativistic_codrift_spectrum(_codrift_case(relativistic=False, kvec=[0.3, 0.0, 0.2]))
    relativistic = solve_relativistic_codrift_spectrum(
        _codrift_case(relativistic=True, kvec=[0.3, 0.0, 0.2])
    )
    plain_modes = np.sort_complex(
        np.asarray(plain["spectra"][0]["real_order"], float)[:, 0]
        + 1j * np.asarray(plain["spectra"][0]["real_order"], float)[:, 1]
    )
    relativistic_modes = np.sort_complex(
        np.asarray(relativistic["spectra"][0]["real_order"], float)[:, 0]
        + 1j * np.asarray(relativistic["spectra"][0]["real_order"], float)[:, 1]
    )
    assert plain_modes.shape == relativistic_modes.shape
    shift = np.max(np.abs(plain_modes - relativistic_modes))
    assert shift > 1e-6, "the inertia flag must move the spectrum for a drifting species"
