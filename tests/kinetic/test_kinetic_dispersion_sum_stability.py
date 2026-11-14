"""Issues #203/#232: finite-N accuracy at small kz and small z, without a kz clamp.

The reference below is the *same* finite-N expression evaluated in 90-digit arithmetic with the
run's scales derived from the public inputs only (``B0``, ``qs``, ``ms``, ``ns0``, ``Ts0``, ``f``,
``kx``, ``kz``). It never reads the implementation's returned scales or tensor, so a scale or
normalisation error in the implementation cannot hide in the reference. Nothing here compares
determinants: the whole tensor is compared component by component, as issue #203 requires.

The small-z follow-up derives independent original K/D from arbitrary public inputs
at 140/180 digits and keeps those references unrounded through the comparisons.
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
    """Faddeeva Z from its erfc definition at the caller's working precision."""
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


def _small_z_case(*, order=15):
    """Issue #232's public real-kx counterexample, also valid for sum-n."""
    return dict(
        B0=1.0,
        qs=(Q,),
        ms=(M,),
        ns0=(3.1e18,),
        Ts0=(8123283.9767213175,),
        f=0.02799243954368732,
        kz=112083871.11918993,
        kx=-16312.089086095832,
        lmx=order,
    )


def _original_tensors_unrounded(arguments, digits=180):
    """Original finite-N K/D for arbitrary public inputs; no A/tail or production scales.

    Recompute every scale and each original tensor block with Bessel I and the
    erfc definition of Z. Keep mpmath components on return, including for the
    140/180-digit self-check. In particular kz is never clamped here.
    """
    with mp.workdps(digits):
        omega = 2 * mp.pi * mp.mpf(arguments["f"])
        kz, kx = mp.mpf(arguments["kz"]), mp.mpf(arguments["kx"])
        tensor = mp.eye(3)
        order = arguments["lmx"]
        for charge, mass, density, temperature in zip(
            arguments["qs"], arguments["ms"], arguments["ns0"], arguments["Ts0"], strict=True
        ):
            charge, mass, density, temperature = map(mp.mpf, (charge, mass, density, temperature))
            thermal = mp.sqrt(2 * mp.mpf(KB) * temperature / mass)
            cyclotron = charge * mp.mpf(arguments["B0"]) / mass
            alpha = density * charge**2 / (mass * mp.mpf(EPSILON0) * omega**2)
            a = kx * mp.sqrt(mp.mpf(KB) * temperature / mass) / cyclotron
            b = a**2
            z0 = omega / (abs(kz) * thermal)
            for n in range(-order, order + 1):
                g = _gamma(n, b)
                gp = (_gamma(n - 1, b) + _gamma(n + 1, b)) / 2 - g
                z = (omega - n * cyclotron) / (abs(kz) * thermal)
                xx, xy = n**2 * g / b, 1j * n * gp
                xz, yz = mp.sqrt(2) * z * n * g / a, -1j * mp.sqrt(2) * z * a * gp
                block = mp.matrix(
                    [[xx, xy, xz], [-xy, xx - 2 * b * gp, yz], [xz, -yz, 2 * z**2 * g]]
                )
                tensor += alpha * z0 * _plasma_z(z) * block
            tensor[2, 2] += 2 * alpha * z0**2
        if kz < 0:
            for row, column in ((0, 2), (1, 2), (2, 0), (2, 1)):
                tensor[row, column] = -tensor[row, column]
        nx, nz = mp.mpf(299792458) * kx / omega, mp.mpf(299792458) * kz / omega
        dispersion = tensor.copy()
        dispersion[0, 0] -= nz**2
        dispersion[1, 1] -= nx**2 + nz**2
        dispersion[2, 2] -= nx**2
        dispersion[0, 2] += nx * nz
        dispersion[2, 0] += nx * nz
        return tuple(
            tuple(tuple(matrix[row, column] for column in range(3)) for row in range(3))
            for matrix in (tensor, dispersion)
        )


def _unrounded_error(actual, reference):
    with mp.workdps(180):
        return max(
            abs(actual[row][column] - reference[row][column])
            / max(mp.mpf(1), abs(reference[row][column]))
            for row in range(3)
            for column in range(3)
        )


def _assert_original_tensor(actual, reference, label):
    with mp.workdps(180):
        promoted = tuple(
            tuple(mp.mpc(float(value.real), float(value.imag)) for value in row) for row in actual
        )
        error = _unrounded_error(promoted, reference)
        assert error <= mp.mpf("2e-12"), f"{label}: scaled complex error={mp.nstr(error, 22)}"


@pytest.mark.parametrize("key,index", [("K", 0), ("D", 1)])
def test_small_z_issue232_matches_original_finite_sum(key, index):
    arguments = _small_z_case()
    reference = _original_tensors_unrounded(arguments)[index]
    result = evaluate_kinetic_dispersion_sum(**arguments)
    _assert_original_tensor(result[key], reference, key)


def test_small_z_issue232_reference_140_180_digits_agree_before_rounding():
    arguments = _small_z_case()
    low = _original_tensors_unrounded(arguments, digits=140)
    high = _original_tensors_unrounded(arguments, digits=180)
    with mp.workdps(180):
        for key, lower, higher in zip(("K", "D"), low, high, strict=True):
            error = _unrounded_error(lower, higher)
            assert error < mp.mpf("1e-45"), f"{key}: unrounded reference error={error}"


@pytest.mark.parametrize("frequency_sign", (-1, 1))
@pytest.mark.parametrize("kz_sign", (-1, 1))
def test_small_z_large_kz_xy_matches_original_sum(frequency_sign, kz_sign):
    arguments = _small_z_case()
    arguments["f"] *= frequency_sign
    arguments["kz"] = kz_sign * 1681258066.787961
    reference = _original_tensors_unrounded(arguments)
    result = evaluate_kinetic_dispersion_sum(**arguments)
    for key, expected in zip(("K", "D"), reference, strict=True):
        _assert_original_tensor(result[key], expected, key)


def _small_z_switch_case(frequency_sign, kz_sign, target):
    arguments = _small_z_case()
    arguments["f"] *= frequency_sign
    thermal = np.sqrt(2.0 * KB * arguments["Ts0"][0] / M)
    maximum_numerator = abs(2.0 * np.pi * arguments["f"]) + arguments["lmx"] * abs(Q / M)
    arguments["kz"] = kz_sign * maximum_numerator / (thermal * target)
    return arguments


def _unit_small_z_case(kz, *, pair=False, reverse=False):
    """Unit thermal speed: the max-|z_n|=1 endpoint is kz=4*pi for N=1."""
    arguments = dict(
        B0=2.0 * np.pi,
        qs=(-1.0,),
        ms=(1.0,),
        ns0=(EPSILON0,),
        Ts0=(1.0 / (2.0 * KB),),
        f=1.0,
        kz=float(kz),
        kx=-2.0 * np.pi * np.sqrt(2.0),
        lmx=1,
    )
    if pair:
        # The two species select different responses (max |z_n| = 0.5 and 5).
        arguments.update(
            qs=(-1.0, 1.0),
            ms=(1.0, 1.0),
            ns0=(EPSILON0, EPSILON0),
            Ts0=(1.0 / (2.0 * KB), 1.0 / (200.0 * KB)),
        )
        if reverse:
            for name in ("qs", "ms", "ns0", "Ts0"):
                arguments[name] = arguments[name][::-1]
    return arguments


_SMALL_Z_REPRESENTATION_CASES = (
    [
        pytest.param(
            _small_z_switch_case(frequency_sign, kz_sign, target),
            id=f"switch-f{frequency_sign:+d}-kz{kz_sign:+d}-{name}",
        )
        for frequency_sign in (-1, 1)
        for kz_sign in (-1, 1)
        for name, target in (("below", 1.0 - 1e-8), ("center", 1.0), ("above", 1.0 + 1e-8))
    ]
    + [
        pytest.param(_unit_small_z_case(kz), id=f"switch-adjacent-{name}")
        for name, kz in (
            ("outside", np.nextafter(4.0 * np.pi, 0.0)),
            ("endpoint", 4.0 * np.pi),
            ("inside", np.nextafter(4.0 * np.pi, np.inf)),
        )
    ]
    + [pytest.param(_small_z_case(order=order), id=f"finite-N{order}") for order in (0, 1, 5)]
    + [
        pytest.param(
            _unit_small_z_case(-8.0 * np.pi, pair=True, reverse=reverse),
            id=f"mixed-response-species-{reverse}",
        )
        for reverse in (False, True)
    ]
)


@pytest.mark.parametrize("arguments", _SMALL_Z_REPRESENTATION_CASES)
def test_small_z_representation_matches_original_full_tensors(arguments):
    reference = _original_tensors_unrounded(arguments)
    result = evaluate_kinetic_dispersion_sum(**arguments)
    for key, expected in zip(("K", "D"), reference, strict=True):
        _assert_original_tensor(result[key], expected, key)


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
        (8, 60, 1e-7),
        (8, 60, -1e-7),
        (40, 60, 1e-7),
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
    """``A(zeta) = 1 + zeta*Z(zeta)`` at 90 digits, from the ``erfc`` definition of ``Z``."""
    with mp.workdps(90):
        return complex(1 + mp.mpf(zeta) * _plasma_z(zeta))


def _rel(value, reference):
    return abs(value - reference) / abs(reference)


THRESHOLD = kinetic_dispersion_sum_n._A_SERIES_THRESHOLD


@pytest.mark.parametrize(
    "zeta",
    [THRESHOLD - 0.1, THRESHOLD, THRESHOLD + 0.1, 1.5 * THRESHOLD, 2 * THRESHOLD, 8.0],
)
@pytest.mark.parametrize("sign", [-1, 1])
def test_both_a_branches_are_accurate_at_and_past_the_switch_point(zeta, sign):
    """The near-zero-``kz`` fix mostly runs where ``|zeta|`` is large, so validate both branches.

    Each representation is checked against the independent 90-digit value for both signs.
    Comparing the representations as well cannot hide a bad formula behind the dispatch choice.
    No assumption about the internal arithmetic of SciPy's hyp1f1 backend is needed.
    """
    zeta *= sign
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


def test_large_tail_uses_a_well_conditioned_complement():
    """Codex P2 on #215: a budgeted positive sum must not be returned as if it had converged.

    ``Gamma_n(1e8)`` has width of order sqrt(b), so terms ``n = 6..2005`` are all about
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
def test_large_tails_agree_with_the_well_conditioned_complement(b):
    """These large-tail cases test conditioning, not two independent tail algorithms."""
    lmx = 5
    positive = _gamma_positive_tail(b, lmx + 1)
    complement = 1.0 - _gamma_partial_sum(b, lmx)
    assert _rel(positive, complement) <= TOLERANCE


def test_tail_matches_high_precision_positive_summation_at_moderate_b():
    """``b=60,N=5`` has head > 1/2, so this exercises the positive-sum branch."""
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


def _independent_tiny_tail(dps):
    """DLMF 10.35.1 coefficient contour, independent of the production Bessel backend.

    Shift the Fourier coefficient contour by -i*t, sum its geometric tail, and set
    theta=u/sqrt(b*cosh(t)). This avoids subtracting a nearly unit finite head.
    """
    with mp.workdps(dps):
        b, first = mp.mpf(4000000), mp.mpf(20001)
        tilt = mp.asinh(first / b)
        curvature = b * mp.cosh(tilt)
        scale = mp.sqrt(curvature)
        leading = 2 * mp.exp(b * (mp.cosh(tilt) - 1) - first * tilt) / (mp.pi * scale)

        def integrand(u):
            theta = u / scale
            attenuation = mp.exp(-2 * curvature * mp.sin(theta / 2) ** 2)
            phase = first * (mp.sin(theta) - theta)
            return attenuation * mp.re(mp.exp(1j * phase) / (-mp.expm1(-tilt - 1j * theta)))

        value = leading * mp.quad(integrand, [0, 1, 2, 4, 8, 12, 20, 30])
        # Beyond u=30 the attenuation decreases up to pi*scale, and the geometric
        # denominator has modulus >= 1-exp(-tilt). Bound that whole omitted arc.
        remainder = (
            leading
            * (mp.pi * scale - 30)
            * mp.exp(-2 * curvature * mp.sin(30 / (2 * scale)) ** 2)
            / (-mp.expm1(-tilt))
        )
        assert remainder < mp.mpf("1e-150") * value
        return value


def test_tiny_positive_tail_does_not_fall_back_to_cancelling_complement():
    """DLMF 10.35.1 coefficient contour and Miller/90/120-digit checks agree.

    For b=4e6,N=20000, 2000 positive terms fail the old convergence test,
    but that does not make subtraction from one safe. The actual tail is
    smaller than 4e-22; the cancelling complement returns about 9.77e-15.
    """
    reference = 1.5202816368677509046184770723329128489563610079733588e-23
    low, high = _independent_tiny_tail(90), _independent_tiny_tail(120)
    with mp.workdps(130):
        assert abs(low - high) / high < mp.mpf("1e-70")
        assert _rel(reference, float(high)) <= TOLERANCE
    assert _rel(_gamma_positive_tail(4e6, 20001), reference) <= TOLERANCE


def test_tail_budget_exhaustion_cannot_return_an_unbounded_partial_sum():
    # A budget is a cost bound. It cannot certify either representation.
    with pytest.raises(ValueError, match="tail"):
        _gamma_positive_tail(4e6, 20001, limit=1)


def test_unrepresentable_positive_tail_is_rejected_instead_of_returned_as_zero():
    with pytest.raises(ValueError, match="tail"):
        _gamma_positive_tail(1.0, 501)


@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("direction", [-np.inf, np.inf])
def test_a_at_adjacent_floats_on_both_dispatch_seams(sign, direction):
    zeta = np.nextafter(sign * THRESHOLD, direction)
    assert _rel(complex(_a_function(np.asarray(zeta))), _reference_a(zeta)) <= TOLERANCE


@pytest.mark.parametrize("sign", [-1, 1])
def test_a_keeps_the_imaginary_part_near_the_zero_of_its_real_part(sign):
    zeta = sign * 0.9241388730045918
    reference = _reference_a(zeta)
    actual = complex(_a_function(np.asarray(zeta)))
    assert abs(actual.real - reference.real) <= TOLERANCE
    assert _rel(actual.imag, reference.imag) <= TOLERANCE
    assert np.signbit(actual.imag) == (sign < 0)


@pytest.mark.parametrize("kz", [-1e-12, 1e-12])
def test_large_b_tiny_tail_remains_accurate_through_the_public_tensor(kz):
    """Original finite-N Kzz from public inputs, independently recomputed at 90 and 120 digits.

    The reference uses mpmath I_0 and downward Miller ratios, then the original finite harmonic
    expression. All |zeta_n| exceed 1e15: the omitted 1/zeta^5 term in Z changes Kzz by <1e-27.
    It agrees with the independent coefficient-contour tail calculation; no output scale is read.
    The previous complement fallback gave Kzz about 1.12e19 instead of 1.67e10.
    """
    result = evaluate_kinetic_dispersion_sum(
        B0=B0,
        qs=[Q],
        ms=[M],
        ns0=[DENSITY],
        Ts0=[TEMPERATURE],
        f=0.7 * abs(Q / M) / (2 * np.pi),
        kz=kz,
        kx=KX_B1 * 2000,
        lmx=20000,
    )
    reference = 16711893312.470150912933564567938666119593682469824351
    assert _rel(result["K"][2, 2], reference) <= TOLERANCE
