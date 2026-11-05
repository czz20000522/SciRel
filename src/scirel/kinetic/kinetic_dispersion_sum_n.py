"""Assemble the finite-harmonic Maxwellian kinetic dielectric tensor with NumPy species and harmonic arrays."""

import numpy as np

from .bessel_gamma import evaluate_bessel_gamma
from .plasma_dispersion import evaluate_plasma_dispersion


_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23


def _finite_scalar(name, value, *, nonzero=False):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite numeric scalar")
    try:
        array = np.asarray(value)
        if array.ndim != 0 or array.dtype.kind not in "iuf":
            raise ValueError
        number = float(array)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite numeric scalar") from error
    if not np.isfinite(number) or (nonzero and number == 0.0):
        raise ValueError(
            f"{name} must be finite and non-zero" if nonzero else f"{name} must be finite"
        )
    return number


def _species_array(name, value):
    try:
        object_values = np.asarray(value, dtype=object)
        raw = np.asarray(value)
        if (
            raw.ndim != 1
            or raw.size == 0
            or raw.dtype.kind not in "iuf"
            or any(isinstance(item, (bool, np.bool_)) for item in object_values.flat)
        ):
            raise ValueError
        array = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a nonempty finite real species vector") from error
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a nonempty finite real species vector")
    return array


def evaluate_kinetic_dispersion_sum(*, B0, qs, ms, ns0, Ts0, f, kz, kx, lmx=5):
    """Return K, D and det(D) for a truncated magnetized Maxwellian sum.

    Inputs use SI units: B0 [T], q [C], m [kg], n [m^-3], T [K], f [Hz],
    and kx/kz [m^-1]. The x-z plane convention and gamma/Z normalizations
    follow the declared fluid-dispersion fD relation; no root finding is performed.
    """
    B0 = _finite_scalar("B0", B0, nonzero=True)
    f = _finite_scalar("f", f, nonzero=True)
    kz = _finite_scalar("kz", kz, nonzero=True)
    response_kz = kz if kz > 0.0 else -kz
    kx = _finite_scalar("kx", kx, nonzero=True)
    if isinstance(lmx, (bool, np.bool_)) or not isinstance(lmx, (int, np.integer)) or lmx < 0:
        raise ValueError("lmx must be a non-negative integer")
    lmx = int(lmx)
    qs, ms, ns0, Ts0 = (
        _species_array("qs", qs),
        _species_array("ms", ms),
        _species_array("ns0", ns0),
        _species_array("Ts0", Ts0),
    )
    if any(values.shape != qs.shape for values in (ms, ns0, Ts0)):
        raise ValueError("all species vectors must have the same shape")
    if np.any(qs == 0) or np.any(ms <= 0) or np.any(ns0 <= 0) or np.any(Ts0 <= 0):
        raise ValueError(
            "charges must be nonzero; masses, densities and temperatures must be positive"
        )

    omega = 2.0 * np.pi * f
    vts = np.sqrt(2.0 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = ns0 * qs**2 / ms / _EPSILON0
    nx, nz = np.sqrt(_C2) * kx / omega, np.sqrt(_C2) * kz / omega
    a = kx * np.sqrt(_KB * Ts0 / ms) / wcs
    b = a**2
    if (
        not all(np.all(np.isfinite(values)) for values in (omega, vts, wcs, wps2, nx, nz, a, b))
        or np.any(a == 0)
        or np.any(wps2 <= 0)
    ):
        raise ValueError("derived kinetic scales must be finite and nonzero where divided")

    k_tensor = np.eye(3, dtype=complex)
    for s in range(qs.size):
        z0 = omega / (response_kz * vts[s])
        for n in range(-lmx, lmx + 1):
            zn = (omega - n * wcs[s]) / (response_kz * vts[s])
            gamma = evaluate_bessel_gamma(n, b[s])
            g = complex(gamma["Gamma_n"])
            gp = complex(gamma["Gamma_prime_n"])
            z = complex(evaluate_plasma_dispersion(zn)["Z"])
            xx = n**2 * g / b[s]
            xy = 1j * n * gp
            xz = np.sqrt(2.0) * zn * n * g / a[s]
            yy = xx - 2.0 * b[s] * gp
            yz = -1j * np.sqrt(2.0) * zn * a[s] * gp
            zz = 2.0 * zn**2 * g
            term = wps2[s] / omega**2 * z0 * z
            k_tensor += term * np.array(
                [
                    [xx, xy, xz],
                    [-xy, yy, yz],
                    [xz, -yz, zz],
                ]
            )
        k_tensor[2, 2] += wps2[s] / omega**2 * 2.0 * z0**2

    if kz < 0.0:
        k_tensor[0, 2] = -k_tensor[0, 2]
        k_tensor[1, 2] = -k_tensor[1, 2]
        k_tensor[2, 0] = -k_tensor[2, 0]
        k_tensor[2, 1] = -k_tensor[2, 1]

    d_tensor = k_tensor.copy()
    d_tensor[0, 0] -= nz**2
    d_tensor[0, 2] += nx * nz
    d_tensor[1, 1] -= nx**2 + nz**2
    d_tensor[2, 0] += nx * nz
    d_tensor[2, 2] -= nx**2
    determinant = np.linalg.det(d_tensor)
    if (
        not np.all(np.isfinite(k_tensor))
        or not np.all(np.isfinite(d_tensor))
        or not np.isfinite(determinant)
    ):
        raise ValueError("kinetic dispersion tensor is not finite and representable")
    return {
        "K": k_tensor,
        "D": d_tensor,
        "determinant": determinant,
        "omega": omega,
        "nx": nx,
        "nz": nz,
        "vts": vts,
        "wcs": wcs,
        "wps2": wps2,
        "b": b,
        "lmx": lmx,
        "tensor_convention": "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)",
    }


__all__ = ["evaluate_kinetic_dispersion_sum"]
