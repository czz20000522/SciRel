"""Evaluate the finite-harmonic fluid-dispersion kinetic dielectric tensor using local special-function terms."""

from __future__ import annotations

import operator
from functools import lru_cache
import numpy as np

_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23


def _evaluate(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, lmx=5):
    """Evaluate the original numerical path at the caller angular frequency."""

    B0 = float(B0)
    omega = float(omega)
    kz = float(kz)
    kx = float(kx)
    if not np.isfinite([B0, omega, kz, kx]).all():
        raise ValueError("B0, omega, kz and kx must be finite")
    if kz == 0.0:
        raise ValueError(
            f"kz must be nonzero; received {kz!r} 1/m. Legal range: finite kz < 0 or kz > 0. "
            "For the separate Ronnmark zero-kz model explicitly use "
            "evaluate_dielectric_response(method='ronnmark'); see scirel.kinetic.dielectric-response"
        )
    if isinstance(lmx, (bool, np.bool_)):
        raise ValueError("lmx must be a non-negative integer")
    try:
        lmx = operator.index(lmx)
    except TypeError:
        raise ValueError("lmx must be a non-negative integer") from None
    if lmx < 0:
        raise ValueError("lmx must be non-negative")
    qs = np.asarray(qs, dtype=float)
    ms = np.asarray(ms, dtype=float)
    ns0 = np.asarray(ns0, dtype=float)
    Ts0 = np.asarray(Ts0, dtype=float)
    if qs.ndim != 1 or qs.size == 0:
        raise ValueError("qs must be a non-empty one-dimensional array")
    if ms.shape != qs.shape or ns0.shape != qs.shape or Ts0.shape != qs.shape:
        raise ValueError("qs, ms, ns0 and Ts0 must share the same shape")
    if not np.all(np.isfinite(qs)) or not np.all(np.isfinite(ms)):
        raise ValueError("qs and ms must be finite")
    if not np.all(np.isfinite(ns0)) or not np.all(np.isfinite(Ts0)):
        raise ValueError("ns0 and Ts0 must be finite")
    if np.any(ms <= 0.0):
        raise ValueError("ms must be strictly positive")
    if np.any(qs == 0.0):
        raise ValueError("qs must be nonzero")
    if np.any(ns0 <= 0.0) or np.any(Ts0 <= 0.0):
        raise ValueError("ns0 and Ts0 must be strictly positive")
    if B0 == 0.0:
        raise ValueError("B0 must be non-zero: the gyrofrequency is proportional to B0")
    if omega == 0.0:
        raise ValueError("omega must be non-zero: it appears in the resonance denominators")
    # Loading the shared numerical helpers imports SciPy; reject invalid inputs first.
    from ._dielectric_harmonic import _a_function, _gamma_positive_tail

    response_kz = kz if kz > 0.0 else -kz

    n_species = qs.size
    vts = np.sqrt(2.0 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = ns0 * qs**2 / ms / _EPSILON0
    nx = np.sqrt(_C2) * kx / omega
    nz = np.sqrt(_C2) * kz / omega
    bs = (kx * np.sqrt(_KB * Ts0 / ms) / wcs) ** 2
    a_s = kx * np.sqrt(_KB * Ts0 / ms) / wcs
    if (
        not all(np.all(np.isfinite(values)) for values in (omega, vts, wcs, wps2, nx, nz, bs, a_s))
        or omega == 0
        or np.any(vts <= 0)
        or np.any(wcs == 0)
        or np.any(wps2 <= 0)
        or np.any(bs <= 0)
        or np.any(a_s == 0)
    ):
        raise FloatingPointError("derived kinetic scales must be finite and nonzero where divided")
    if not np.isfinite(np.square(omega)) or np.square(omega) == 0:
        raise FloatingPointError("squared kinetic frequency is not representable")
    if not np.all(np.isfinite(response_kz * vts)) or np.any(response_kz * vts == 0):
        raise FloatingPointError("kinetic resonance scale is not finite and nonzero")

    k_tensor = np.eye(3, dtype=complex)
    for s in range(n_species):
        z0 = omega / (response_kz * vts[s])
        alpha = wps2[s] / omega**2
        if not np.isfinite(z0) or z0 == 0 or not np.isfinite(alpha) or alpha <= 0:
            raise FloatingPointError("kinetic response scales are not representable")
        b = bs[s]
        a = a_s[s]
        # When all |z_n|<=1, keep the small z*Z response before multiplying
        # by large coefficients. Summing A near 1 then removing its constant
        # would lose it. Large-z cancellation still needs the analytic A path.
        direct_response = (abs(omega) + lmx * abs(wcs[s])) / (response_kz * vts[s]) <= 1.0
        sum_xz = 0.0j
        sum_yz = 0.0j
        sum_zz = 0.0j
        for l in range(-lmx, lmx + 1):
            zn = (omega - l * wcs[s]) / (response_kz * vts[s])
            if not np.isfinite(zn):
                raise FloatingPointError("kinetic harmonic argument is not finite")
            gam, gamp = _gamma_and_prime(l, b)
            try:
                zn_value = _zfun(zn)
            except (OverflowError, ZeroDivisionError) as error:
                raise FloatingPointError("kinetic Z evaluation is not representable") from error
            response = zn * zn_value if direct_response else complex(_a_function(np.asarray(zn)))
            sum_xz += l * gam * response
            sum_yz += gamp * response
            sum_zz += zn * gam * response
            x_xx = l**2 * gam / b
            x_xy = 1j * l * gamp
            x_yy = l**2 / b * gam - 2.0 * b * gamp
            # The ordinary components retain their fixed N=64 Z backend.
            term = alpha * (z0 * zn_value)
            k_tensor[0, 0] += term * x_xx
            k_tensor[0, 1] += term * x_xy
            k_tensor[1, 0] += term * (-x_xy)
            k_tensor[1, 1] += term * x_yy
        # z*Z=A-1 with symmetric finite sums: sum(l*Gamma_l)=0,
        # sum(Gamma'_l)=Gamma_(N+1)-Gamma_N. Keep both finite endpoints;
        # the positive tail computes 1-sum(Gamma_l), without changing N.
        # Direct z*Z needs no endpoint subtraction and retains the original
        # +2*alpha*z0**2. Otherwise keep the finite-N endpoint and tail exactly.
        tail = 1.0 if direct_response else _gamma_positive_tail(b, lmx + 1)
        edge = (
            0.0
            if direct_response
            else _gamma_and_prime(lmx + 1, b)[0] - _gamma_and_prime(lmx, b)[0]
        )
        cross_x = np.sqrt(2.0) * alpha * z0 / a * sum_xz
        cross_y = -1j * np.sqrt(2.0) * alpha * z0 * a * (sum_yz - edge)
        k_tensor[0, 2] += cross_x
        k_tensor[2, 0] += cross_x
        k_tensor[1, 2] += cross_y
        k_tensor[2, 1] -= cross_y
        k_tensor[2, 2] += 2.0 * alpha * z0 * sum_zz + 2.0 * alpha * z0**2 * tail

    if kz < 0.0:
        k_tensor[0, 2] = -k_tensor[0, 2]
        k_tensor[1, 2] = -k_tensor[1, 2]
        k_tensor[2, 0] = -k_tensor[2, 0]
        k_tensor[2, 1] = -k_tensor[2, 1]

    d_tensor = k_tensor.copy()
    d_tensor[0, 0] = k_tensor[0, 0] - nz**2
    d_tensor[0, 2] = k_tensor[0, 2] + nx * nz
    d_tensor[1, 1] = k_tensor[1, 1] - (nx**2 + nz**2)
    d_tensor[2, 0] = k_tensor[2, 0] + nx * nz
    d_tensor[2, 2] = k_tensor[2, 2] - nx**2

    determinant = np.linalg.det(d_tensor)
    if (
        not np.all(np.isfinite(k_tensor))
        or not np.all(np.isfinite(d_tensor))
        or not np.isfinite(determinant)
    ):
        raise FloatingPointError("dispersion tensor and determinant must be finite")
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
        "a": a_s,
        "b": bs,
        "lmx": lmx,
        "tensor_convention": "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)",
    }


def _gamma_and_prime(n, b):
    """Return scaled ``Gamma_n`` and its neighbor derivative together.

    Both quantities use the same three neighboring ``ive`` values.  Keeping
    the center subtraction and averaging order unchanged preserves the
    existing floating-point contract while avoiding a duplicate special
    function evaluation for every species/harmonic pair.
    """
    from scipy.special import ive

    previous, center, following = ive(np.asarray([n - 1, n, n + 1]), b)
    return float(center), float((previous + following) / 2.0 - center)


@lru_cache(maxsize=1)
def _weideman_coefficients():
    """Build the fixed 64-term Weideman map once on first valid use."""
    n = 64
    m = 2 * n
    m2 = 2 * m
    k = np.arange(-m + 1, m)
    length = np.sqrt(n / np.sqrt(2.0))
    theta = k * np.pi / m
    t = length * np.tan(theta / 2.0)
    f = np.exp(-(t**2)) * (length**2 + t**2)
    f = np.concatenate(([0.0], f))
    coefficients = np.real(np.fft.fft(np.fft.fftshift(f))) / m2
    return length, np.flipud(coefficients[1 : n + 1])


def _zfun(z):
    """Plasma dispersion function via the Weideman/Faddeeva rational expansion."""
    from scipy.special import erfc

    z = complex(z)
    if z.real == 0.0:
        return 1j * np.sqrt(np.pi) * np.exp(-(z**2)) * erfc(z.imag)
    zc = complex(z)
    flipped = False
    if zc.imag < 0.0:
        zc = zc.conjugate()
        flipped = True
    length, coefficients = _weideman_coefficients()
    zc_map = (length + 1j * zc) / (length - 1j * zc)
    p = np.polyval(coefficients, zc_map)
    w = 2.0 * p / (length - 1j * zc) ** 2 + (1.0 / np.sqrt(np.pi)) / (length - 1j * zc)
    if flipped:
        w = np.conjugate(2.0 * np.exp(-(zc**2)) - w)
    return 1j * np.sqrt(np.pi) * w
