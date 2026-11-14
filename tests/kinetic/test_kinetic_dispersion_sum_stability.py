"""Issue #203: the truncated harmonic sum must be accurate as ``kz -> 0`` without a clamp.

The reference below is the *same* finite-N expression evaluated in 80-digit arithmetic with the
run's scales derived from the public inputs only (``B0``, ``qs``, ``ms``, ``ns0``, ``Ts0``, ``f``,
``kx``, ``kz``). It never reads the implementation's returned scales or tensor, so a scale or
normalisation error in the implementation cannot hide in the reference. Nothing here compares
determinants: the whole tensor is compared component by component, as issue #203 requires.
"""

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_kinetic_dispersion_sum, kinetic_dispersion_sum_n
from scirel.kinetic.kinetic_dispersion_sum_n import (
    _a_asymptotic,
    _a_function,
    _a_series,
    _gamma_partial_sum,
    _gamma_positive_tail,
)

Q = -1.60217662e-19
M = 9.1094e-31
KB = 1.38064852e-23
EPSILON0 = 8.854187817e-12
C2 = (2.99792458e8) ** 2
TEMPERATURE = 1000.0 * 1.6022e-19 / 1.38064852e-23
B0 = 1.0
DENSITY = 6.075e19
KX_B1 = 13261.94247879565  # kx that gives b = 1 for this species at this temperature

# The published accuracy goal for this batch, applied to max_ij |K - K_ref| / max(1, |K_ref_ij|).
TOLERANCE = 2e-12


def _plasma_z(zeta):
    """Faddeeva Z at 80 digits from its erfc definition; mpmath handles every magnitude."""
    zeta = mp.mpf(zeta)
    return 1j * mp.sqrt(mp.pi) * mp.exp(-zeta * zeta) * mp.erfc(-1j * zeta)


def _gamma(n, b):
    return mp.exp(-b) * mp.besseli(n, b)


def _reference_tensor(*, b_target, lmx, kz):
    """Same finite-N tensor in high-precision arithmetic, with scales derived from public inputs.

    The working precision is set here rather than at import time: other kinetic tests lower
    ``mp.mp.dps`` for their own references, and a module-level global would make this reference
    depend on test order.
    """
    with mp.workdps(90):
        return _reference_tensor_at_precision(b_target=b_target, lmx=lmx, kz=kz)


def _reference_tensor_at_precision(*, b_target, lmx, kz):
    kx = KX_B1 * np.sqrt(b_target)
    omega = 0.7 * abs(Q / M)
    vts = mp.sqrt(2 * mp.mpf(KB) * mp.mpf(TEMPERATURE) / mp.mpf(M))
    wcs = mp.mpf(Q) * mp.mpf(B0) / mp.mpf(M)
    wps2 = mp.mpf(DENSITY) * mp.mpf(Q) ** 2 / mp.mpf(M) / mp.mpf(EPSILON0)
    a = mp.mpf(kx) * mp.sqrt(mp.mpf(KB) * mp.mpf(TEMPERATURE) / mp.mpf(M)) / wcs
    b = a * a
    response_kz = abs(mp.mpf(kz))
    z0 = mp.mpf(omega) / (response_kz * vts)
    alpha = wps2 / mp.mpf(omega) ** 2

    tensor = mp.matrix(3, 3)
    for index in range(3):
        tensor[index, index] = 1
    for n in range(-lmx, lmx + 1):
        gamma = _gamma(n, b)
        gamma_prime = (_gamma(n - 1, b) + _gamma(n + 1, b)) / 2 - gamma
        zeta = (mp.mpf(omega) - n * wcs) / (response_kz * vts)
        z_value = _plasma_z(zeta)
        xx = mp.mpf(n) ** 2 * gamma / b
        xy = 1j * n * gamma_prime
        xz = mp.sqrt(2) * zeta * n * gamma / a
        yy = xx - 2 * b * gamma_prime
        yz = -1j * mp.sqrt(2) * zeta * a * gamma_prime
        zz = 2 * zeta**2 * gamma
        term = alpha * z0 * z_value
        tensor[0, 0] += term * xx
        tensor[0, 1] += term * xy
        tensor[0, 2] += term * xz
        tensor[1, 0] += term * (-xy)
        tensor[1, 1] += term * yy
        tensor[1, 2] += term * yz
        tensor[2, 0] += term * xz
        tensor[2, 1] += term * (-yz)
        tensor[2, 2] += term * zz
    tensor[2, 2] += alpha * 2 * z0**2
    if kz < 0:
        for row, column in ((0, 2), (1, 2), (2, 0), (2, 1)):
            tensor[row, column] = -tensor[row, column]
    return np.array([[complex(tensor[i, j]) for j in range(3)] for i in range(3)])


def _tensor_error(actual, reference):
    worst = 0.0
    for i in range(3):
        for j in range(3):
            scale = max(1.0, abs(reference[i, j]))
            worst = max(worst, abs(actual[i, j] - reference[i, j]) / scale)
    return worst


@pytest.mark.parametrize(
    "b_target, lmx, kz",
    [
        (1, 30, 1e-7),
        (1, 30, -1e-7),
        (1, 30, 1e-12),
        (1, 30, -1e-12),
        (1, 30, 1e3),
        (8, 5, 1e3),
        (8, 30, 10.0),
    ],
)
def test_tensor_matches_the_independent_high_precision_reference(b_target, lmx, kz):
    result = evaluate_kinetic_dispersion_sum(
        B0=B0,
        qs=[Q],
        ms=[M],
        ns0=[DENSITY],
        Ts0=[TEMPERATURE],
        f=0.7 * abs(Q / M) / (2 * np.pi),
        kz=kz,
        kx=KX_B1 * np.sqrt(b_target),
        lmx=lmx,
    )
    reference = _reference_tensor(b_target=b_target, lmx=lmx, kz=kz)
    assert _tensor_error(result["K"], reference) <= TOLERANCE


def test_truncation_tail_survives_and_is_not_smoothed_away():
    """b=8, N=30, kz=1e-7 is genuinely ~7.7e4 from this finite N; only rounding was broken."""
    result = evaluate_kinetic_dispersion_sum(
        B0=B0,
        qs=[Q],
        ms=[M],
        ns0=[DENSITY],
        Ts0=[TEMPERATURE],
        f=0.7 * abs(Q / M) / (2 * np.pi),
        kz=1e-7,
        kx=KX_B1 * np.sqrt(8),
        lmx=30,
    )
    reference = _reference_tensor(b_target=8, lmx=30, kz=1e-7)
    assert _tensor_error(result["K"], reference) <= TOLERANCE
    assert abs(result["K"][2, 2].real - 77445.395838) < 1.0
    # The N=60 value is a different truncation, not a correction of this one.
    assert abs(result["K"][2, 2].real - 3.0290608) > 1.0


def test_kz_sign_only_flips_the_cross_components():
    common = dict(
        B0=B0,
        qs=[Q],
        ms=[M],
        ns0=[DENSITY],
        Ts0=[TEMPERATURE],
        f=0.7 * abs(Q / M) / (2 * np.pi),
        kx=KX_B1,
        lmx=30,
    )
    positive = evaluate_kinetic_dispersion_sum(kz=1e-7, **common)["K"]
    negative = evaluate_kinetic_dispersion_sum(kz=-1e-7, **common)["K"]
    for row, column in ((0, 2), (1, 2), (2, 0), (2, 1)):
        assert negative[row, column] == pytest.approx(-positive[row, column], abs=1e-18)
    for row, column in ((0, 0), (0, 1), (1, 0), (1, 1), (2, 2)):
        assert negative[row, column] == pytest.approx(positive[row, column], rel=1e-15)


def test_zero_kz_is_still_rejected():
    with pytest.raises(ValueError, match="kz"):
        evaluate_kinetic_dispersion_sum(
            B0=B0,
            qs=[Q],
            ms=[M],
            ns0=[DENSITY],
            Ts0=[TEMPERATURE],
            f=0.7 * abs(Q / M) / (2 * np.pi),
            kz=0.0,
            kx=KX_B1,
        )


def _reference_a(zeta):
    """``A(zeta) = 1 + zeta*Z(zeta)`` at 80 digits, from the ``erfc`` definition of ``Z``."""
    with mp.workdps(90):
        return complex(1 + mp.mpf(zeta) * _plasma_z(zeta))


def _rel(value, reference):
    return abs(value - reference) / abs(reference)


THRESHOLD = kinetic_dispersion_sum_n._A_SERIES_THRESHOLD


@pytest.mark.parametrize(
    "zeta",
    [THRESHOLD - 0.1, THRESHOLD, THRESHOLD + 0.1, 1.5 * THRESHOLD, 2 * THRESHOLD, 8.0],
)
def test_both_a_branches_are_accurate_at_and_past_the_switch_point(zeta):
    """The near-zero-``kz`` fix mostly runs where ``|zeta|`` is large, so validate both branches.

    ``_a_series`` (``hyp1f1``) is the side that could have gone wrong: at ``zeta^2 ~ 1e3`` it has
    to cancel alternating terms of size ~1 down to ``1/(2 zeta^2) ~ 5e-4``. Measured on
    2026-11-14, both branches sit at ~2.2e-16 relative error at every one of the three seam points
    ``zeta = 31.9 / 32.0 / 32.1``, so the switch is not a step. ``zeta = 8`` is the lowest magnitude
    at which the asymptotic series is still at binary64 resolution (it degrades to 6.4e-13 at
    ``zeta = 6`` and 9.5e-5 at ``zeta = 4``), which is why the seam is not lowered.

    Each branch is asserted against the independent 90-digit value *and* against the other branch,
    so a dispatch choice cannot hide a bad formula on either side of the seam.
    """
    reference = _reference_a(zeta)
    series = complex(_a_series(np.asarray([zeta]))[0])
    asymptotic = complex(_a_asymptotic(np.asarray([zeta]))[0])
    assert _rel(series, reference) <= TOLERANCE
    assert _rel(asymptotic, reference) <= TOLERANCE
    assert _rel(series, asymptotic) <= TOLERANCE


@pytest.mark.parametrize("offset", [-1e-9, -1e-5, 1e-5, 1e-9])
def test_dispatch_across_the_threshold_has_no_step(offset):
    """A threshold that favoured one branch would show up as a jump in ``_a_function`` itself."""
    zeta = THRESHOLD + offset
    value = complex(_a_function(np.asarray([zeta]))[0])
    assert _rel(value, _reference_a(zeta)) <= TOLERANCE


def _large_argument_tail(nmax, b, terms=4):
    """``1 - sum_{|n|<=nmax} Gamma_n`` using the fixed-order large-argument form of ``I_n(b)``.

    ``I_n(b) ~ e^b/sqrt(2 pi b) * sum_k (-1)^k prod_{j<k}(4n^2-(2j+1)^2) / (k! (8b)^k)`` for fixed
    ``n`` and large ``b``. At ``b = 1e8`` the first omitted term is below ``1e-28`` relative, so
    this is an independent value the implementation has to reproduce rather than a copy of it.
    """
    inv = 1.0 / np.sqrt(2 * np.pi * b)
    total = 0.0
    for n in range(nmax + 1):
        mu = 4.0 * n * n
        series = 1.0
        coefficient = 1.0
        for k in range(1, terms + 1):
            coefficient *= (mu - (2 * k - 1) ** 2) / (k * 8.0 * b)
            series += (-1) ** k * coefficient
        total += (1.0 if n == 0 else 2.0) * inv * series
    return 1.0 - total


def test_truncation_tail_is_complete_when_the_peak_lies_beyond_the_term_budget():
    """Codex P2 on #215: a budgeted positive sum must not be returned as if it had converged.

    ``Gamma_n(1e8)`` peaks near ``n = 1e8``, so terms ``n = 6..2005`` are all about
    ``(2 pi b)^-1/2`` and their sum (0.1585107) is not the truncation tail (0.9995612). The tail is
    O(1) here, so the complement identity is exact and cannot cancel.
    """
    b, lmx = 1e8, 5
    tail = _gamma_positive_tail(b, lmx + 1)
    assert _rel(tail, _large_argument_tail(lmx, b)) <= 1e-12
    assert tail > 0.99  # the old budgeted partial sum returned 0.1585107 here
    result = evaluate_kinetic_dispersion_sum(
        B0=B0,
        qs=[Q],
        ms=[M],
        ns0=[DENSITY],
        Ts0=[TEMPERATURE],
        f=0.7 * abs(Q / M) / (2 * np.pi),
        kz=1e-7,
        kx=KX_B1 * np.sqrt(b),
        lmx=lmx,
    )
    assert np.all(np.isfinite(result["K"]))


@pytest.mark.parametrize("b", [100.0, 1000.0, 1900.0, 2005.0, 3000.0, 1e4])
def test_both_tail_representations_agree_across_the_term_budget_edge(b):
    """The branch that wins may change with ``b``; the value must not step at the switch."""
    lmx = 5
    positive = _gamma_positive_tail(b, lmx + 1)
    complement = 1.0 - _gamma_partial_sum(b, lmx)
    assert _rel(positive, complement) <= TOLERANCE


def test_tail_matches_high_precision_positive_summation_at_moderate_b():
    """``b=60`` keeps the peak inside the budget, so this exercises the positive-sum branch."""
    b, lmx = 60.0, 5
    with mp.workdps(90):
        excess = mp.mpf(0)
        for n in range(lmx + 1, 400):
            gamma = mp.exp(-mp.mpf(b)) * mp.besseli(n, mp.mpf(b))
            excess += gamma
            if gamma < mp.mpf("1e-50"):
                break
        reference = float(2 * excess)
    assert _rel(_gamma_positive_tail(b, lmx + 1), reference) <= TOLERANCE
