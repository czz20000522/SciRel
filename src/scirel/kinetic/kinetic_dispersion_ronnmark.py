"""Assemble the Ronnmark kinetic dielectric tensor from validated species arrays and local harmonic response terms."""
from __future__ import annotations

import math

import numpy as np

from .ronnmark_r_function import evaluate_ronnmark_r

__all__ = ["evaluate_kinetic_dispersion_ronnmark"]

_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23

# 冻结源码 bonk/fDR.m:26-46 的 J=8 极点表，源码写定前四个，后四个共轭补齐。
_BZJ = np.array([
    -0.017340112270401 - 0.046306439626294j,
    -0.739917811220052 + 0.839518284620274j,
    5.840632105105495 + 0.953602751322040j,
    -5.583374181615043 - 11.208550459628098j,
])
_CZJ = np.array([
    2.237687725134293 - 1.625941024120362j,
    1.465234091939142 - 1.789620299603315j,
    0.839253966367922 - 1.891995211531426j,
    0.273936218055381 - 1.941787037576095j,
])


_SPLIT = 134217729.0


def _two_prod(a, b):
    p = a * b
    c = _SPLIT * a; ah = c - (c - a); al = a - ah
    c = _SPLIT * b; bh = c - (c - b); bl = b - bh
    return p, ((ah * bh - p) + ah * bl + al * bh) + al * bl


def _two_sum(a, b):
    s = a + b; bb = s - a
    return s, (a - (s - bb)) + (b - bb)


def _fma(a, b, c):
    p, e = _two_prod(a, b)
    s, e2 = _two_sum(p, c)
    return s + (e + e2)


def _cmul(a, b):
    a = complex(a); b = complex(b)
    return complex(_fma(a.real, b.real, -(a.imag * b.imag)),
                   _fma(a.real, b.imag, a.imag * b.real))


def _d(x, y):
    """IEEE-faithful float division: Octave yields +-inf / nan on a zero divisor, it never raises.

    Python's `/` on floats is the same correctly-rounded IEEE-754 double division numpy and
    Octave use, so this only changes the zero-divisor branch (the frozen source's own Taylor
    series can hit ``Y^2 - I^2 == 0`` and continues with Inf/NaN rather than aborting).
    """
    try:
        return x / y
    except ZeroDivisionError:
        if x == 0.0 or x != x:
            return float("nan")
        return math.copysign(float("inf"), x) * math.copysign(1.0, y)


def _cdiv(a, b):
    a = complex(a); b = complex(b)
    ar, ai = a.real, a.imag; br, bi = b.real, b.imag
    fab = -br if br < 0 else br; fai = -bi if bi < 0 else bi
    if fab >= fai:
        t = _d(bi, br); d = _fma(bi, t, br)
        return complex(_d(_fma(ai, t, ar), d), _d(_fma(-ar, t, ai), d))
    t = _d(br, bi); d = _fma(br, t, bi)
    return complex(_d(_fma(ar, t, ai), d), _d(_fma(ai, t, -ar), d))


def _rmul(s, z):
    z = complex(z)
    return complex(s * z.real, s * z.imag)


def evaluate_kinetic_dispersion_ronnmark(*, B0, qs, ms, ns0, Ts0, f=None, kz, kx, omega=None):
    """Return the Ronnmark-method kinetic dispersion determinant.

    All inputs are SI: ``B0`` [T], ``qs`` [C], ``ms`` [kg], ``ns0`` [m^-3], ``Ts0`` [K],
    ``f`` [Hz], ``kz``/``kx`` [1/m]; ``kx`` may be complex because the source's
    ``fsolve`` scan solves ``fDR(kx)=0`` in the complex plane, which makes ``a_s`` and
    the Ronnmark parameter ``lambda_s`` complex as well. The J=8 pole table replaces the exact plasma
    dispersion function and the Ronnmark R function replaces the truncated harmonic
    sum, so the result is convergent for all harmonic orders rather than truncated at
    ``lmx``. The returned ``D`` uses the source convention
    ``D_xz = D_zx = K_xz + n_x n_z``.
    """

    if (f is None) == (omega is None):
        raise ValueError("provide exactly one of f or omega")
    B0 = float(B0)
    if omega is None:
        f = float(f)
    kz = float(kz)
    kx = complex(kx)
    if not np.isfinite(B0) or not np.isfinite(kz) or not np.isfinite(kx):
        raise ValueError("B0, kz and kx must be finite")
    if f is not None and not np.isfinite(f):
        raise ValueError("f must be finite")
    qs = np.asarray(qs, dtype=float)
    ms = np.asarray(ms, dtype=float)
    ns0 = np.asarray(ns0, dtype=float)
    Ts0 = np.asarray(Ts0, dtype=float)
    if qs.ndim != 1 or qs.size == 0:
        raise ValueError("qs must be a non-empty one-dimensional array")
    if ms.shape != qs.shape or ns0.shape != qs.shape or Ts0.shape != qs.shape:
        raise ValueError("qs, ms, ns0 and Ts0 must share the same shape")
    for name, arr in (("qs", qs), ("ms", ms), ("ns0", ns0), ("Ts0", Ts0)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} must be finite")
    if np.any(ms <= 0.0):
        raise ValueError("ms must be strictly positive")
    if np.any(ns0 <= 0.0) or np.any(Ts0 <= 0.0):
        raise ValueError("ns0 and Ts0 must be strictly positive")
    if np.any(qs == 0.0):
        raise ValueError("qs must be non-zero")
    if B0 == 0.0:
        raise ValueError("B0 must be non-zero: the gyrofrequency is proportional to B0")
    if omega is not None:
        omega = float(omega)
    else:
        omega = 2.0 * np.pi * f
    if not np.isfinite(omega) or omega == 0.0:
        raise ValueError("omega must be non-zero: it appears in the resonance argument")

    ronnmark = evaluate_ronnmark_r
    n_species = qs.size
    vts = np.sqrt(2.0 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = (np.sqrt(ns0 * qs**2 / ms / _EPSILON0)) ** 2
    nx = _cdiv(_rmul(np.sqrt(_C2), kx), complex(omega, 0.0))
    nz = complex(np.sqrt(_C2) * kz / omega, 0.0)
    rhocs = np.sqrt(_KB * Ts0 / ms) / wcs
    as_ = np.array([_rmul(float(rhocs[s]), kx) for s in range(n_species)], dtype=complex)
    bs = np.array([_cmul(as_[s], as_[s]) for s in range(n_species)], dtype=complex)

    j_order = 2 * _BZJ.size
    bzj = np.zeros(j_order, dtype=complex)
    czj = np.zeros(j_order, dtype=complex)
    bzj[:4] = _BZJ
    czj[:4] = _CZJ
    bzj[4:] = np.conj(bzj[:4])
    czj[4:] = -np.conj(czj[:4])

    k_tensor = np.eye(3, dtype=complex)
    branches: list[str] = []
    for s in range(n_species):
        b = bs[s]
        a = as_[s]
        for j in range(j_order):
            xsj = _cdiv(complex(omega, 0.0) - _cmul(complex(kz * vts[s], 0.0), czj[j]), complex(wcs[s], 0.0))
            rc = ronnmark(xsj, b)
            rsj = rc["R"]
            drsj = rc["dR_dlambda"]
            branches.append(rc["branch"])

            x_xx = rsj
            x_xy = _cdiv(1j * drsj, xsj)
            x_xz = _cmul(_cdiv(_cmul(_rmul(np.sqrt(2.0), a), czj[j]), xsj), rsj)
            x_yy = rsj - _cmul(_cdiv(_rmul(2.0, b), _cmul(xsj, xsj)), drsj)
            x_yz = _cmul(_cdiv(_cmul(complex(0.0, -np.sqrt(2.0)) * a, czj[j]),
                               _cmul(xsj, xsj)), drsj)
            x_zz = _cmul(_cdiv(_rmul(2.0, _cmul(czj[j], czj[j])), _cmul(xsj, xsj)),
                         xsj + _cmul(b, rsj))

            term = _rmul(wps2[s] / (omega * wcs[s]), bzj[j])
            k_tensor[0, 0] = k_tensor[0, 0] + _cmul(term, x_xx)
            k_tensor[0, 1] = k_tensor[0, 1] + _cmul(term, x_xy)
            k_tensor[0, 2] = k_tensor[0, 2] + _cmul(term, x_xz)
            k_tensor[1, 0] = k_tensor[1, 0] + _cmul(term, complex(-x_xy.real, -x_xy.imag))
            k_tensor[1, 1] = k_tensor[1, 1] + _cmul(term, x_yy)
            k_tensor[1, 2] = k_tensor[1, 2] + _cmul(term, x_yz)
            k_tensor[2, 0] = k_tensor[2, 0] + _cmul(term, x_xz)
            k_tensor[2, 1] = k_tensor[2, 1] + _cmul(term, complex(-x_yz.real, -x_yz.imag))
            k_tensor[2, 2] = k_tensor[2, 2] + _cmul(term, x_zz)

    nz2 = _cmul(nz, nz); nx2 = _cmul(nx, nx); nxnz = _cmul(nx, nz)
    d_tensor = k_tensor.copy()
    d_tensor[0, 0] = k_tensor[0, 0] - nz2
    d_tensor[0, 2] = k_tensor[0, 2] + nxnz
    d_tensor[1, 1] = k_tensor[1, 1] - (nx2 + nz2)
    d_tensor[2, 0] = k_tensor[2, 0] + nxnz
    d_tensor[2, 2] = k_tensor[2, 2] - nx2

    Dxx, Dyy, Dzz = d_tensor[0, 0], d_tensor[1, 1], d_tensor[2, 2]
    Dyx, Dzy, Dxz = d_tensor[1, 0], d_tensor[2, 1], d_tensor[0, 2]
    Dzx, Dyz, Dxy = d_tensor[2, 0], d_tensor[1, 2], d_tensor[0, 1]
    cofactor = (_cmul(_cmul(Dxx, Dyy), Dzz) + _cmul(_cmul(Dyx, Dzy), Dxz)
                + _cmul(_cmul(Dzx, Dyz), Dxy) - _cmul(_cmul(Dxz, Dyy), Dzx)
                - _cmul(_cmul(Dyz, Dzy), Dxx) - _cmul(_cmul(Dzz, Dyx), Dxy))

    return {
        "K": k_tensor,
        "D": d_tensor,
        "determinant": cofactor,
        "omega": omega,
        "nx": nx,
        "nz": nz,
        "vts": vts,
        "wcs": wcs,
        "wps2": wps2,
        "as": as_,
        "b": bs,
        "bzj": bzj,
        "czj": czj,
        "j_order": j_order,
        "branches": branches,
        "tensor_convention": "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)",
    }
