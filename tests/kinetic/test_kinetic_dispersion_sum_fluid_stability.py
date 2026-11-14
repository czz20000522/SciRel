"""Issues #226/#232: bounded finite-N fluid accuracy, including small z and the kz clamp.

The reference evaluates the original finite harmonic expression in mpmath, not the
production A-function rearrangement. Every scale comes from public inputs; Gamma is
exp(-b)*I_n(b), and Z follows the Faddeeva erfc definition (DLMF 7.2.3). No production
scales, Gamma/Z values, rational coefficients or private numerical kernels are used.

These samples test full complex K and D componentwise at 2e-12. They do not establish
a continuous-domain error bound, harmonic convergence or determinant/root accuracy.
The 140/180-digit check retains mpmath values rather than comparing rounded complex128
references. It checks reference convergence at selected samples, not an error theorem.
"""

from functools import lru_cache

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_fluid_kinetic_dispersion_sum


Q = -1.60217662e-19
M = 9.1094e-31
MP = 1.6726219e-27
KB = 1.38064852e-23
EPSILON0 = 8.854187817e-12
C = 299792458
TEMPERATURE = 1000.0 * 1.6022e-19 / KB
DENSITY = 6.075e19
KX_B1 = 13261.94247879565
FREQUENCY = 0.7 * abs(Q / M) / (2.0 * np.pi)
CLAMP = 1e-10


def _case(*, b=1.0, order=30, kz=1e-7, frequency=FREQUENCY):
    """Construct public inputs; b is a target, never an oracle scale."""
    return dict(
        B0=1.0,
        qs=(Q,),
        ms=(M,),
        ns0=(DENSITY,),
        Ts0=(TEMPERATURE,),
        f=frequency,
        kz=float(kz),
        kx=float(KX_B1 * np.sqrt(b)),
        lmx=order,
    )


def _switch_case(sign, target):
    """Place the n=0 argument near +/-32 using public inputs only.

    The +/-1e-8 offsets straddle the switch despite input/scale rounding; the
    target=32 sample need not land on exactly 32 after binary64 scale arithmetic.
    """
    thermal = np.sqrt(2.0 * KB * TEMPERATURE / M)
    kz = 2.0 * np.pi * FREQUENCY / (thermal * target)
    return _case(order=5, kz=kz, frequency=sign * FREQUENCY)


def _resonance_case(frequency):
    """At f=1 the public float scales give omega=-Omega, hence z_-1=0.

    The oracle still recomputes omega with mp.pi, so it also keeps the tiny
    detuning implied by those same public binary64 inputs. Unit-scale synthetic
    species keep that distinction well conditioned instead of hiding it.
    """
    return dict(
        B0=2.0 * np.pi,
        qs=(-1.0,),
        ms=(1.0,),
        ns0=(EPSILON0,),
        Ts0=(1.0 / (2.0 * KB),),
        f=float(frequency),
        kz=1.0,
        kx=float(2.0 * np.pi * np.sqrt(2.0)),
        lmx=1,
    )


def _pair_case():
    arguments = _case(order=5, kz=-1e3, frequency=-FREQUENCY)
    arguments.update(
        B0=-1.0,
        kx=-KX_B1,
        qs=(Q, -Q),
        ms=(M, MP),
        ns0=(DENSITY, DENSITY),
        Ts0=(TEMPERATURE, TEMPERATURE / 2.0),
    )
    return arguments


def _small_z_issue232_case():
    """The real-kx regression reported in #232; keep the public inputs exact."""
    return dict(
        B0=1.0,
        qs=(Q,),
        ms=(M,),
        ns0=(3.1e18,),
        Ts0=(8123283.9767213175,),
        f=0.02799243954368732,
        kz=112083871.11918993,
        kx=-16312.089086095832,
        lmx=15,
    )


def _small_z_switch_case(frequency_sign, kz_sign, target):
    """Place the finite-N maximum argument on either side of 1 from public inputs.

    Offsets of 1e-8 straddle the switch despite binary64 scale rounding; the
    center sample need not land on exactly 1. No production kernel is queried.
    """
    arguments = _small_z_issue232_case()
    arguments["f"] *= frequency_sign
    thermal = np.sqrt(2.0 * KB * arguments["Ts0"][0] / M)
    maximum_numerator = abs(2.0 * np.pi * arguments["f"]) + arguments["lmx"] * abs(Q / M)
    arguments["kz"] = kz_sign * maximum_numerator / (thermal * target)
    return arguments


def _mixed_response_pair_case(reverse):
    """Two species with maximum |z_n|=0.5 and 5, hence different representations."""
    arguments = _resonance_case(1.0)
    arguments.update(
        qs=(-1.0, 1.0),
        ms=(1.0, 1.0),
        ns0=(EPSILON0, EPSILON0),
        Ts0=(1.0 / (2.0 * KB), 1.0 / (200.0 * KB)),
        kz=-8.0 * np.pi,
        kx=-arguments["kx"],
    )
    if reverse:
        for name in ("qs", "ms", "ns0", "Ts0"):
            arguments[name] = arguments[name][::-1]
    return arguments


def _adjacent_small_z_switch_case(kz):
    """Unit thermal speed makes kz=4*pi the binary64 max-|z_n|=1 endpoint."""
    arguments = _resonance_case(1.0)
    arguments["kz"] = float(kz)
    return arguments


def _reference_tensors(arguments, digits=180):
    # Apply the declared clamp to the public float before any division/sign use.
    # Canonicalizing here lets all equivalent clamped inputs share one reference.
    kz = arguments["kz"]
    effective_kz = CLAMP if abs(kz) < CLAMP else kz
    return _finite_sum_at_precision(
        arguments["B0"],
        tuple(arguments["qs"]),
        tuple(arguments["ms"]),
        tuple(arguments["ns0"]),
        tuple(arguments["Ts0"]),
        arguments["f"],
        effective_kz,
        arguments["kx"],
        arguments["lmx"],
        digits,
    )


@lru_cache(maxsize=64)
def _finite_sum_at_precision(B0, qs, ms, ns0, Ts0, f, kz, kx, order, digits):
    """Return immutable, unrounded K/D from the original finite-N expression.

    For each species the block is multiplied by alpha*z0*Z(z_n), then the
    original +2*alpha*z0**2 term is added to zz. Thus the finite Gamma tail and
    yz endpoint are retained without using the production tail/A algorithm.
    """
    with mp.workdps(digits):
        omega = 2 * mp.pi * mp.mpf(f)
        parallel = abs(mp.mpf(kz))
        perpendicular = mp.mpf(kx)
        root_two = mp.sqrt(2)
        root_pi = mp.sqrt(mp.pi)
        terms = [[[] for _ in range(3)] for _ in range(3)]

        for charge, mass, density, temperature in zip(qs, ms, ns0, Ts0, strict=True):
            charge, mass = mp.mpf(charge), mp.mpf(mass)
            temperature = mp.mpf(temperature)
            thermal = mp.sqrt(2 * mp.mpf(KB) * temperature / mass)
            cyclotron = charge * mp.mpf(B0) / mass
            plasma_squared = mp.mpf(density) * charge**2 / mass / mp.mpf(EPSILON0)
            alpha = plasma_squared / omega**2
            a = perpendicular * mp.sqrt(mp.mpf(KB) * temperature / mass) / cyclotron
            b = a * a
            z0 = omega / (parallel * thermal)
            # I_-n = I_n for integer orders; neighbors include both cutoff endpoints.
            gamma = [mp.exp(-b) * mp.besseli(n, b) for n in range(order + 2)]

            for n in range(-order, order + 1):
                g = gamma[abs(n)]
                gp = (gamma[abs(n - 1)] + gamma[abs(n + 1)]) / 2 - g
                z = (omega - n * cyclotron) / (parallel * thermal)
                plasma_z = 1j * root_pi * mp.exp(-z * z) * mp.erfc(-1j * z)
                weight = alpha * z0 * plasma_z
                xx = n**2 * g / b
                xy = 1j * n * gp
                xz = root_two * z * n * g / a
                yy = xx - 2 * b * gp
                yz = -1j * root_two * z * a * gp
                block = ((xx, xy, xz), (-xy, yy, yz), (xz, -yz, 2 * z * z * g))
                for row in range(3):
                    for column in range(3):
                        terms[row][column].append(weight * block[row][column])
            terms[2][2].append(2 * alpha * z0**2)

        tensor = mp.matrix(3, 3)
        for row in range(3):
            for column in range(3):
                tensor[row, column] = int(row == column) + mp.fsum(terms[row][column])
        if kz < 0:
            for row, column in ((0, 2), (1, 2), (2, 0), (2, 1)):
                tensor[row, column] = -tensor[row, column]

        nx = mp.mpf(C) * perpendicular / omega
        nz = mp.mpf(C) * mp.mpf(kz) / omega
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


def _assert_componentwise_close(actual, reference, *, tolerance, label):
    """Compare full complex components without rounding the high-precision reference."""
    with mp.workdps(180):
        for row in range(3):
            for column in range(3):
                expected = reference[row][column]
                observed = actual[row][column]
                error = abs(observed - expected) / max(mp.mpf(1), abs(expected))
                assert error <= mp.mpf(tolerance), (
                    f"{label}[{row},{column}]: scaled complex error={mp.nstr(error, 12)}; "
                    f"actual={mp.nstr(observed, 22)}, reference={mp.nstr(expected, 22)}"
                )


# Eight finite-cutoff cases. In particular, b=8,N=30,kz=1e-7 has Kzz~77445.395838;
# replacing it with the N=60 value ~3.0290608 must fail the full tensor comparison.
_CORE_CASES = [
    pytest.param(_case(order=0, kz=1e3), id="b1-N0-ordinary"),
    pytest.param(_case(order=1, kz=1e3), id="b1-N1-ordinary"),
    pytest.param(_case(b=8, order=5, kz=1e3), id="b8-N5-ordinary"),
    pytest.param(_case(kz=1e-7), id="b1-N30-small-positive"),
    pytest.param(_case(kz=-1e-7), id="b1-N30-small-negative"),
    pytest.param(_case(kz=1e3), id="b1-N30-ordinary"),
    pytest.param(_case(b=8, kz=1e-7), id="b8-N30-finite-tail"),
    pytest.param(_case(b=8, order=60, kz=1e-7), id="b8-N60-distinct-cutoff"),
]
_CLAMP_CASES = [
    pytest.param(_case(kz=kz), id=f"clamp-{name}")
    for name, kz in (
        ("zero", 0.0),
        ("positive-interior", 1e-12),
        ("negative-interior", -1e-12),
        ("positive-adjacent-inside", np.nextafter(CLAMP, 0.0)),
        ("positive-endpoint", CLAMP),
        ("positive-adjacent-outside", np.nextafter(CLAMP, np.inf)),
        ("negative-adjacent-inside", np.nextafter(-CLAMP, 0.0)),
        ("negative-endpoint", -CLAMP),
        ("negative-adjacent-outside", np.nextafter(-CLAMP, -np.inf)),
    )
]
_SWITCH_CASES = [
    pytest.param(_switch_case(sign, target), id=f"A-switch-sign{sign:+d}-{name}")
    for sign in (-1, 1)
    for name, target in (("below", 32.0 - 1e-8), ("center", 32.0), ("above", 32.0 + 1e-8))
]
_RESONANCE_CASES = [
    pytest.param(_resonance_case(frequency), id=f"A-zero-{name}")
    for name, frequency in (
        ("below", np.nextafter(1.0, 0.0)),
        ("center", 1.0),
        ("above", np.nextafter(1.0, np.inf)),
    )
]
_SMALL_Z_CASES = [
    pytest.param(_case(b=8, order=order, kz=1e8), id=f"small-z-b8-N{order}") for order in (0, 1, 5)
]
_SMALL_Z_SWITCH_CASES = [
    pytest.param(
        _small_z_switch_case(frequency_sign, kz_sign, target),
        id=f"small-z-switch-f{frequency_sign:+d}-kz{kz_sign:+d}-{name}",
    )
    for frequency_sign in (-1, 1)
    for kz_sign in (-1, 1)
    for name, target in (("below", 1.0 - 1e-8), ("center", 1.0), ("above", 1.0 + 1e-8))
]
_TENSOR_CASES = (
    _CORE_CASES
    + _CLAMP_CASES
    + _SWITCH_CASES
    + _RESONANCE_CASES
    + _SMALL_Z_CASES
    + _SMALL_Z_SWITCH_CASES
    + [
        pytest.param(_adjacent_small_z_switch_case(kz), id=f"small-z-switch-adjacent-{name}")
        for name, kz in (
            ("outside", np.nextafter(4.0 * np.pi, 0.0)),
            ("endpoint", 4.0 * np.pi),
            ("inside", np.nextafter(4.0 * np.pi, np.inf)),
        )
    ]
    + [
        pytest.param(_mixed_response_pair_case(reverse), id=f"mixed-response-pair-{reverse}")
        for reverse in (False, True)
    ]
    + [pytest.param(_pair_case(), id="two-species-negative-B-f-kx-kz")]
)


@pytest.mark.parametrize("arguments", _TENSOR_CASES)
def test_fluid_tensor_matches_independent_original_finite_sum(arguments):
    reference = _reference_tensors(arguments)
    result = evaluate_fluid_kinetic_dispersion_sum(**arguments)
    for key, expected in zip(("K", "D"), reference, strict=True):
        # Promote each observed binary64 component exactly; never cast the oracle down.
        with mp.workdps(180):
            observed = tuple(
                tuple(mp.mpc(float(value.real), float(value.imag)) for value in row)
                for row in result[key]
            )
        _assert_componentwise_close(observed, expected, tolerance="2e-12", label=key)


@pytest.mark.parametrize("key", ("K", "D"))
def test_fluid_small_z_issue232_matches_original_finite_sum(key):
    arguments = _small_z_issue232_case()
    reference = dict(zip(("K", "D"), _reference_tensors(arguments), strict=True))[key]
    result = evaluate_fluid_kinetic_dispersion_sum(**arguments)
    with mp.workdps(180):
        observed = tuple(
            tuple(mp.mpc(float(value.real), float(value.imag)) for value in row)
            for row in result[key]
        )
    _assert_componentwise_close(observed, reference, tolerance="2e-12", label=key)


@pytest.mark.parametrize("frequency_sign", (-1, 1))
@pytest.mark.parametrize("kz_sign", (-1, 1))
def test_fluid_small_z_large_kz_xy_matches_original_sum(frequency_sign, kz_sign):
    arguments = _small_z_issue232_case()
    arguments["f"] *= frequency_sign
    arguments["kz"] = kz_sign * 1681258066.787961
    reference = _reference_tensors(arguments)
    result = evaluate_fluid_kinetic_dispersion_sum(**arguments)
    for key, expected in zip(("K", "D"), reference, strict=True):
        with mp.workdps(180):
            observed = tuple(
                tuple(mp.mpc(float(value.real), float(value.imag)) for value in row)
                for row in result[key]
            )
        _assert_componentwise_close(observed, expected, tolerance="2e-12", label=key)


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(_case(kz=1e-12), id="worst-positive-clamp-b1-N30"),
        pytest.param(_case(b=8, kz=1e-7), id="large-finite-tail-b8-N30"),
        pytest.param(_small_z_issue232_case(), id="small-z-issue232"),
    ],
)
def test_reference_140_180_digits_agree_before_binary64_rounding(arguments):
    low = _reference_tensors(arguments, digits=140)
    high = _reference_tensors(arguments, digits=180)
    for key, lower, higher in zip(("K", "D"), low, high, strict=True):
        _assert_componentwise_close(lower, higher, tolerance="1e-45", label=f"reference-{key}")


def test_unrepresentable_positive_tail_fails_without_returning_a_partial_tensor():
    with pytest.raises(ValueError, match="positive harmonic tail.*reliable precision"):
        evaluate_fluid_kinetic_dispersion_sum(**_case(order=400))
