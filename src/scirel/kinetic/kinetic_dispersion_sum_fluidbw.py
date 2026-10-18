"""fluidBW's Weideman finite-harmonic tensor with its near-zero kz clamp."""

from __future__ import annotations

import operator
from functools import lru_cache
import numpy as np

_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23

__all__ = ["evaluate_fluidbw_kinetic_dispersion_sum"]

def evaluate_fluidbw_kinetic_dispersion_sum(*, B0, qs, ms, ns0, Ts0, f, kz, kx, lmx=5):
    """Return the fluidBW conventional harmonic sum and 3x3 tensors.

    All inputs are SI: ``B0`` [T], ``qs`` [C], ``ms`` [kg], ``ns0`` [m^-3], ``Ts0`` [K],
    ``f`` [Hz], ``kz``/``kx`` [1/m]. ``lmx`` is the Bessel harmonic truncation of the
    conventional sum over cyclotron harmonics; the source's ``fD.m`` uses ``lmx=5``.
    ``K`` follows the convention ``K_ij = delta_ij - sigma_ij / (i * omega * epsilon0)``
    and ``D`` is the ``K`` tensor with the Maxwell curl terms, whose determinant is the
    returned dispersion function.
    This source-method variant keeps bonk/fD.m's positive ``1e-10`` clamp for
    ``abs(kz)<1e-10``. The analytic SciRel sum has a distinct failure contract.
    """

    B0 = float(B0)
    f = float(f)
    kz = float(kz)
    kx = float(kx)
    if not np.isfinite([B0, f, kz, kx]).all():
        raise ValueError("B0, f, kz and kx must be finite")
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
    if f == 0.0:
        raise ValueError("f must be non-zero: omega appears in the resonance denominators")
    if abs(kz) < 1e-10:
        # Source fidelity: bonk/fD.m:16-18 clamps a near-zero parallel wavenumber with
        # `if(abs(kz)<1e-10) kz=1e-10; end` before any divisor (z0=w/(kz*vts),
        # zn=(w-l*wcs)/(kz*vts)). The clamp is sign-agnostic and observable: on the frozen
        # source it replaces a 1/kz blow-up by the finite kz=+1e-10 evaluation. The sibling
        # path bonk/fDR.m:22-23 has NO clamp, so this substitution is local to the
        # conventional sum_n operator and must not be shared with the Ronnmark operator.
        kz = 1e-10

    omega = 2.0 * np.pi * f
    n_species = qs.size
    vts = np.sqrt(2.0 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = ns0 * qs**2 / ms / _EPSILON0
    nx = np.sqrt(_C2) * kx / omega
    nz = np.sqrt(_C2) * kz / omega
    bs = (kx * np.sqrt(_KB * Ts0 / ms) / wcs) ** 2
    a_s = kx * np.sqrt(_KB * Ts0 / ms) / wcs

    k_tensor = np.eye(3, dtype=complex)
    for s in range(n_species):
        z0 = omega / (kz * vts[s])
        b = bs[s]
        a = a_s[s]
        for l in range(-lmx, lmx + 1):
            zn = (omega - l * wcs[s]) / (kz * vts[s])
            gam, gamp = _gamma_and_prime(l, b)
            x_xx = l**2 * gam / b
            x_xy = 1j * l * gamp
            x_xz = np.sqrt(2.0) * zn * l * gam / a
            x_yy = l**2 / b * gam - 2.0 * b * gamp
            x_yz = -1j * np.sqrt(2.0) * zn * a * gamp
            x_zz = 2.0 * zn**2 * gam
            term = wps2[s] / omega**2 * (z0 * _zfun(zn))
            k_tensor[0, 0] += term * x_xx
            k_tensor[0, 1] += term * x_xy
            k_tensor[0, 2] += term * x_xz
            k_tensor[1, 0] += term * (-x_xy)
            k_tensor[1, 1] += term * x_yy
            k_tensor[1, 2] += term * x_yz
            k_tensor[2, 0] += term * x_xz
            k_tensor[2, 1] += term * (-x_yz)
            k_tensor[2, 2] += term * x_zz
        k_tensor[2, 2] += wps2[s] / omega**2 * 2.0 * z0**2

    d_tensor = k_tensor.copy()
    d_tensor[0, 0] = k_tensor[0, 0] - nz**2
    d_tensor[0, 2] = k_tensor[0, 2] + nx * nz
    d_tensor[1, 1] = k_tensor[1, 1] - (nx**2 + nz**2)
    d_tensor[2, 0] = k_tensor[2, 0] + nx * nz
    d_tensor[2, 2] = k_tensor[2, 2] - nx**2

    determinant = np.linalg.det(d_tensor)
    if not np.all(np.isfinite(k_tensor)) or not np.all(np.isfinite(d_tensor)) or not np.isfinite(determinant):
        raise ValueError("dispersion tensor and determinant must be finite")
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
    f = np.exp(-t**2) * (length**2 + t**2)
    f = np.concatenate(([0.0], f))
    coefficients = np.real(np.fft.fft(np.fft.fftshift(f))) / m2
    return length, np.flipud(coefficients[1 : n + 1])


def _zfun(z):
    """Plasma dispersion function via the Weideman/Faddeeva rational expansion."""
    from scipy.special import erfc

    z = complex(z)
    if z.real == 0.0:
        return 1j * np.sqrt(np.pi) * np.exp(-z**2) * erfc(z.imag)
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
        w = np.conjugate(2.0 * np.exp(-zc**2) - w)
    return 1j * np.sqrt(np.pi) * w
