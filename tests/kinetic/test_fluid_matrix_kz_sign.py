"""The wavevector eigenproblem respects the z-reflection symmetry of a uniform Maxwellian plasma.

Reflecting z leaves B_z unchanged, so eps_xz and eps_yz are odd in k_z, the other elements are
even, and det D is even: the k_x roots at given omega must be the same for +k_z and -k_z. The
Landau prescription fixes the damping sign for either sign of k_z (Stix, Waves in Plasmas, 1992,
ch. 10; Swanson, Plasma Waves, 2003, ch. 4). The reference tensor below uses only SciPy.
"""

import numpy as np
from scipy.special import ive, wofz

from scirel.kinetic.fluid_spectrum import assemble_fluid_em, derive_fluid_case

KB, EPS0, C = 1.38064852e-23, 8.854187817e-12, 2.99792458e8


def stix_dispersion(b0, qs, ms, ns, ts, omega, kz, kx, harmonics=60):
    """Stix (1992) eqs. 10.45-10.57 for an isotropic Maxwellian without drift, in SI units."""
    tensor = np.eye(3, dtype=complex)
    for q, m, n, t in zip(qs, ms, ns, ts):
        wth2 = 2 * KB * t / m
        wth, gyro, wp2 = np.sqrt(wth2), q * b0 / m, n * q * q / EPS0 / m
        lam = kx * kx * wth2 / (2 * gyro * gyro)
        scale = np.exp(-lam + abs(np.real(lam)))
        for l in range(-harmonics, harmonics + 1):
            zeta = (omega - l * gyro) / (abs(kz) * wth)
            a = 1j * np.sqrt(np.pi) * wofz(zeta) / (abs(kz) * wth)
            b = 1.0 / kz + (omega - l * gyro) / kz * a
            i0 = ive(l, lam) * scale
            ip = (ive(l - 1, lam) + ive(l + 1, lam)) / 2 * scale
            tensor = tensor + wp2 / omega * np.array(
                [
                    [l * l * i0 / lam * a, -1j * l * (i0 - ip) * a, kx / gyro * l * i0 / lam * b],
                    [
                        1j * l * (i0 - ip) * a,
                        (l * l * i0 / lam + 2 * lam * i0 - 2 * lam * ip) * a,
                        1j * kx / gyro * (i0 - ip) * b,
                    ],
                    [
                        kx / gyro * l * i0 / lam * b,
                        -1j * kx / gyro * (i0 - ip) * b,
                        2 * (omega - l * gyro) / (kz * wth2) * i0 * b,
                    ],
                ],
                dtype=complex,
            )
    nx, nz = C * kx / omega, C * kz / omega
    return tensor + np.array(
        [[-nz * nz, 0, nx * nz], [0, -nx * nx - nz * nz, 0], [nx * nz, 0, -nx * nx]], dtype=complex
    )


def _setup():
    state = derive_fluid_case("em", 2)
    values = {
        k: np.asarray(state[k], float).ravel()
        for k in ("ms", "qs", "ns0", "Ts0", "B0", "kn", "wn", "kz")
    }
    return state, values


def _spectrum(state, kz, omega):
    local = dict(state)
    local["kz"] = np.asarray([[kz]])
    return np.linalg.eigvals(assemble_fluid_em(local, omega, 8, 6)["M"])


def _smallest_singular_ratio(values, omega, kz, kx):
    d = stix_dispersion(
        values["B0"][0], values["qs"], values["ms"], values["ns0"], values["Ts0"], omega, kz, kx
    )
    singular = np.linalg.svd(d, compute_uv=False)
    return singular[-1] / singular[0]


def test_kx_spectrum_is_the_same_for_both_signs_of_kz():
    state, values = _setup()
    kz, omega = values["kz"][0], 1.25 * values["wn"][0]
    plus, minus = _spectrum(state, kz, omega), _spectrum(state, -kz, omega)
    scale = values["kn"][0]
    distance = np.array([np.min(np.abs(plus - root)) for root in minus]) / scale
    assert np.quantile(distance, 0.9) < 1e-6


def test_damped_root_at_negative_kz_matches_the_exact_tensor_not_its_conjugate():
    state, values = _setup()
    kz, omega, scale = values["kz"][0], 1.25 * values["wn"][0], values["kn"][0]
    roots = _spectrum(state, -kz, omega)
    roots = roots[
        (roots.real > 0.2 * scale)
        & (np.abs(roots) < 3 * scale)
        & (np.abs(roots.imag) > 1e-3 * scale)
    ]
    ratios = [
        (
            _smallest_singular_ratio(values, omega, -kz, r),
            _smallest_singular_ratio(values, omega, -kz, np.conj(r)),
            r,
        )
        for r in roots
    ]
    best = min(ratios, key=lambda item: item[0])
    assert best[0] < best[1] / 10, ratios[:3]
