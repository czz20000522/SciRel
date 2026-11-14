"""#227: independent finite-N references for the real/complex-kx diagnostic.

All scales and the original finite harmonic expression are evaluated from public
inputs with mpmath. Z uses the erfc definition, Gamma uses exp(-b)*I_n(b).
The reference does not import production scales, A kernels, tails or Z backends.
140/180-digit comparisons retain the unrounded values. The full complex K/D
criterion remains 2e-12; these samples do not certify an entire complex domain,
harmonic convergence, roots, or determinant accuracy.
"""

from functools import lru_cache

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_kinetic_dielectric_tensor


Q = -1.60217662e-19
M = 9.1094e-31
KB = 1.38064852e-23
EPSILON0 = 8.854187817e-12
C = 299792458
TEMPERATURE = 1000.0 * 1.6022e-19 / KB
KX_B1 = 13261.94247879565
FREQUENCY = 0.7 * abs(Q / M) / (2 * np.pi)


def _case(*, b=1, order=15, kz=1e-7, frequency=FREQUENCY):
    return dict(
        B0=1.0,
        qs=(Q,),
        ms=(M,),
        ns0=(6.075e19,),
        Ts0=(TEMPERATURE,),
        f=frequency,
        kz=kz,
        kx=complex(KX_B1 * np.sqrt(complex(b))),
        lmx=order,
    )


def _switch_case(sign, target):
    thermal = np.sqrt(2 * KB * TEMPERATURE / M)
    return _case(
        b=1 + 0.4j,
        kz=2 * np.pi * FREQUENCY / (thermal * target),
        frequency=sign * FREQUENCY,
    )


def _broadcast_case():
    arguments = _case(b=0.8 - 0.6j, kz=-1e3, frequency=-FREQUENCY)
    arguments.update(B0=-1.0, qs=(Q, -Q), ms=M, ns0=6.075e19)
    arguments["Ts0"] = (TEMPERATURE, TEMPERATURE / 2)
    return arguments


def _resonance_case(frequency):
    # Public binary64 inputs place z_-1 at/next to zero in the float scales.
    # The independent oracle retains detuning from its own high-precision pi.
    return dict(
        B0=2 * np.pi,
        qs=-1.0,
        ms=1.0,
        ns0=EPSILON0,
        Ts0=1 / (2 * KB),
        f=float(frequency),
        kz=1.0,
        kx=complex(2 * np.pi * np.sqrt(2) * (1 + 0.1j)),
        lmx=1,
    )


def _small_z_case():
    # Independently found by reviewer B: A~1 loses the small yz response.
    return dict(
        B0=1.0,
        qs=-1.60217662e-19,
        ms=9.1094e-31,
        ns0=3.1e18,
        Ts0=8123283.9767213175,
        f=0.02799243954368732,
        kz=112083871.11918993,
        kx=complex(-16312.089086095832, -3850.761879351035),
        lmx=15,
    )


def _response_switch_case(sign, target):
    arguments = _small_z_case()
    arguments["f"] *= sign
    thermal = np.sqrt(2 * KB * arguments["Ts0"] / arguments["ms"])
    endpoint = abs(2 * np.pi * arguments["f"]) + arguments["lmx"] * abs(
        arguments["qs"] / arguments["ms"]
    )
    arguments["kz"] = endpoint / (thermal * target)
    return arguments


def _low_frequency_xy_case(f_sign, kz_sign):
    arguments = _small_z_case()
    arguments["f"] *= f_sign
    arguments["kz"] = kz_sign * 1681258066.787961
    return arguments


def _species(value):
    return (value,) if np.ndim(value) == 0 else tuple(value)


def _reference(arguments, digits=180):
    return _original_sum(
        arguments["B0"],
        *(_species(arguments[name]) for name in ("qs", "ms", "ns0", "Ts0")),
        arguments["f"],
        arguments["kz"],
        arguments["kx"],
        arguments.get("lmx", 15),
        digits,
    )


@lru_cache(maxsize=64)
def _original_sum(B0, qs, ms, ns0, Ts0, f, kz, kx, order, digits):
    with mp.workdps(digits):
        omega = 2 * mp.pi * mp.mpf(f)
        parallel = abs(mp.mpf(kz))  # There is deliberately no near-zero clamp.
        perpendicular = mp.mpc(kx)
        root_two = mp.sqrt(2)
        root_pi = mp.sqrt(mp.pi)
        terms = [[[] for _ in range(3)] for _ in range(3)]
        count = max(map(len, (qs, ms, ns0, Ts0)))
        species = [values * count if len(values) == 1 else values for values in (qs, ms, ns0, Ts0)]
        for charge, mass, density, temperature in zip(*species, strict=True):
            charge, mass = mp.mpf(charge), mp.mpf(mass)
            thermal = mp.sqrt(2 * mp.mpf(KB) * mp.mpf(temperature) / mass)
            cyclotron = charge * mp.mpf(B0) / mass
            alpha = mp.mpf(density) * charge**2 / mass / mp.mpf(EPSILON0) / omega**2
            a = perpendicular * mp.sqrt(mp.mpf(KB) * mp.mpf(temperature) / mass) / cyclotron
            b = a * a
            z0 = omega / (parallel * thermal)
            gamma = [mp.exp(-b) * mp.besseli(n, b) for n in range(order + 2)]
            for n in range(-order, order + 1):
                g = gamma[abs(n)]
                gp = (gamma[abs(n - 1)] + gamma[abs(n + 1)]) / 2 - g
                z = (omega - n * cyclotron) / (parallel * thermal)
                plasma_z = 1j * root_pi * mp.exp(-z * z) * mp.erfc(-1j * z)
                weight = alpha * z0 * plasma_z
                xx = n * n * g / b
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


def _assert_close(actual, expected, tolerance, label):
    with mp.workdps(180):
        for row in range(3):
            for column in range(3):
                value = actual[row][column]
                observed = mp.mpc(float(value.real), float(value.imag))
                wanted = expected[row][column]
                error = abs(observed - wanted) / max(mp.mpf(1), abs(wanted))
                assert error <= mp.mpf(tolerance), (
                    f"{label}[{row},{column}]: scaled complex error={mp.nstr(error, 12)}; "
                    f"actual={mp.nstr(observed, 22)}, reference={mp.nstr(wanted, 22)}"
                )


_CASES = [
    pytest.param(_case(order=0, kz=1e3), id="real-N0"),
    pytest.param(_case(order=1, kz=1e3), id="real-N1"),
    pytest.param(_case(kz=1e3), id="real-default-N15"),
    pytest.param(_case(order=30), id="real-N30-small-positive"),
    pytest.param(_case(order=30, kz=-1e-7), id="real-N30-small-negative"),
    pytest.param(_case(b=8, order=30), id="real-b8-N30-finite-tail"),
    pytest.param(_case(b=8, order=60), id="real-b8-N60-distinct-tail"),
    pytest.param(_case(kz=1e-12, order=30), id="unclamped-positive"),
    pytest.param(_case(kz=-1e-12, order=30), id="unclamped-negative"),
    *[
        pytest.param(_case(b=b, kz=kz, order=30), id=f"complex-{name}-kz{kz}")
        for name, b in (("right", 1 + 0.5j), ("left", -1 + 0.5j), ("imaginary-kx", -1))
        for kz in (1e3, 1e-7, -1e-7)
    ],
    *[
        pytest.param(_switch_case(sign, target), id=f"A-switch-{sign}-{name}")
        for sign in (-1, 1)
        for name, target in (("below", 32 - 1e-8), ("center", 32), ("above", 32 + 1e-8))
    ],
    *[
        pytest.param(_resonance_case(frequency), id=f"resonance-{name}")
        for name, frequency in (
            ("below", np.nextafter(1.0, 0.0)),
            ("center", 1.0),
            ("above", np.nextafter(1.0, np.inf)),
        )
    ],
    pytest.param(_broadcast_case(), id="broadcast-negative-B-f-kz-complex-kx"),
    pytest.param(_small_z_case(), id="small-z-reviewer-counterexample"),
    *[
        pytest.param(_response_switch_case(sign, target), id=f"response-switch-{sign}-{name}")
        for sign in (-1, 1)
        for name, target in (("below", 1 - 1e-8), ("center", 1), ("above", 1 + 1e-8))
    ],
    *[
        pytest.param(_low_frequency_xy_case(f_sign, kz_sign), id=f"low-f-xy-{f_sign}-{kz_sign}")
        for f_sign in (-1, 1)
        for kz_sign in (-1, 1)
    ],
]


@pytest.mark.parametrize("arguments", _CASES)
def test_diagnostic_matches_independent_original_finite_sum(arguments):
    expected = _reference(arguments)
    result = evaluate_kinetic_dielectric_tensor(**arguments)
    for key, wanted in zip(("K", "D"), expected, strict=True):
        _assert_close(result[key], wanted, "2e-12", key)


@pytest.mark.parametrize(
    "arguments",
    [
        _case(b=8, order=30),
        _case(b=-1 + 0.5j, order=30),
        _small_z_case(),
        _low_frequency_xy_case(1, 1),
    ],
)
def test_unrounded_reference_is_stable_at_two_precisions(arguments):
    lower = _reference(arguments, 140)
    higher = _reference(arguments, 180)
    with mp.workdps(180):
        for low_matrix, high_matrix in zip(lower, higher, strict=True):
            for low_row, high_row in zip(low_matrix, high_matrix, strict=True):
                for low, high in zip(low_row, high_row, strict=True):
                    error = abs(low - high) / max(mp.mpf(1), abs(high))
                    assert error < mp.mpf("1e-95"), "unrounded finite-N reference must converge"


def test_default_and_diagnostics_keep_the_original_controls_and_signs():
    arguments = _case(kz=-1e-7)
    del arguments["lmx"]
    result = evaluate_kinetic_dielectric_tensor(**arguments)
    assert set(result) == {
        "K",
        "D",
        "det_D",
        "w",
        "vts",
        "wcs",
        "wps2",
        "rhocs",
        "nx",
        "nz",
        "as",
        "bs",
        "z0s",
        "lmx",
    }
    assert result["lmx"] == 15, "the diagnostic default remains 15, not its siblings' 5"
    np.testing.assert_array_equal(result["z0s"], result["w"] / (arguments["kz"] * result["vts"]))
    np.testing.assert_array_equal(result["as"], arguments["kx"] * result["rhocs"])
    np.testing.assert_array_equal(result["bs"], result["as"] ** 2)
    _assert_close(result["K"], _reference(arguments)[0], "2e-12", "default K")
    d = result["D"]
    determinant = (
        d[0, 0] * d[1, 1] * d[2, 2]
        + d[1, 0] * d[2, 1] * d[0, 2]
        + d[2, 0] * d[1, 2] * d[0, 1]
        - d[0, 2] * d[1, 1] * d[2, 0]
        - d[1, 2] * d[2, 1] * d[0, 0]
        - d[2, 2] * d[1, 0] * d[0, 1]
    )
    assert result["det_D"] == determinant, "the diagnostic retains its six-term determinant"


def test_zero_wavevector_boundaries_are_preserved():
    arguments = _case()
    arguments["kz"] = 0
    with pytest.raises(ValueError, match="kz must be non-zero"):
        evaluate_kinetic_dielectric_tensor(**arguments)
    arguments.update(kz=1e3, kx=0)
    result = evaluate_kinetic_dielectric_tensor(**arguments)
    expected_mask = np.array([[False, True, False], [True, False, True], [False, True, True]])
    for key in ("K", "D"):
        np.testing.assert_array_equal(
            np.isfinite(result[key]),
            expected_mask,
            err_msg="kx=0 must retain each finite/singular component",
        )
    with mp.workdps(180):
        omega = 2 * mp.pi * mp.mpf(arguments["f"])
        thermal = mp.sqrt(2 * mp.mpf(KB) * mp.mpf(TEMPERATURE) / mp.mpf(M))
        z0 = omega / (mp.mpf(arguments["kz"]) * thermal)
        alpha = mp.mpf(6.075e19) * mp.mpf(Q) ** 2 / mp.mpf(M) / mp.mpf(EPSILON0) / omega**2
        plasma_z = 1j * mp.sqrt(mp.pi) * mp.exp(-z0 * z0) * mp.erfc(-1j * z0)
        expected = 1 + 2 * alpha * z0**2 * (1 + z0 * plasma_z)
        for key in ("K", "D"):
            value = mp.mpc(complex(result[key][2, 2]))
            assert abs(value - expected) / max(1, abs(expected)) < mp.mpf("2e-12"), (
                "kx=0 has an independently finite zz component"
            )


@pytest.mark.parametrize(
    "b,start",
    [(1 + 0.5j, 16), (-1 + 0.5j, 31), (-8 + 0j, 31), (8 + 4j, 61), (1 + 1e-15j, 31)],
)
def test_complex_tail_matches_independent_high_precision_complement(b, start):
    from scirel.kinetic.dielectric_tensor_diagnostic import _gamma_complex_tail

    with mp.workdps(180):
        argument = mp.mpc(b)
        # The 180-digit complement is independent of the production tail sum.
        head = mp.exp(-argument) * (
            mp.besseli(0, argument) + 2 * mp.fsum(mp.besseli(n, argument) for n in range(1, start))
        )
        expected = 1 - head
        observed = mp.mpc(_gamma_complex_tail(b, start))
        assert abs(observed - expected) / abs(expected) < mp.mpf("2e-12"), (
            "complex tail must keep both its phase and its finite-N magnitude"
        )


def test_public_diagnostic_rejects_an_exhausted_complex_tail(monkeypatch):
    from scirel.kinetic import dielectric_tensor_diagnostic as module

    original = module._gamma_complex_tail
    monkeypatch.setattr(module, "_gamma_complex_tail", lambda b, start: original(b, start, limit=0))
    with pytest.raises(ValueError, match="remainder could not be bounded"):
        evaluate_kinetic_dielectric_tensor(**_case(b=1 + 0.5j))


def test_complex_tail_rejects_nonfinite_bessel_backend(monkeypatch):
    from scirel.kinetic import dielectric_tensor_diagnostic as module

    monkeypatch.setattr(module, "_gamman", lambda orders, b: np.full(len(orders), np.nan))
    with pytest.raises(ValueError, match="terms must be finite"):
        module._gamma_complex_tail(1 + 0.5j, 16)
