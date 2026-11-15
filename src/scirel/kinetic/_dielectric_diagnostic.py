"""Evaluate the finite-harmonic kinetic dielectric tensor and determinant with local special-function backends."""

import math as _math
import operator as _operator

import numpy as _np


_SPECIAL = None


def _special_backend():
    """Load SciPy's special-function backend at the first numeric call."""
    global _SPECIAL
    if _SPECIAL is None:
        from scipy import special

        _SPECIAL = special
    return _SPECIAL


# bonk/fDtensor.m:22-25 的默认 SI 常数（原样照抄）
_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23

# bonk/zfun.m:6 的 Weideman 变换阶数
_ZFUN_N = 64
_SQRT_PI = _np.sqrt(_np.pi)

# bonk/fDtensor.m:43 的默认谐波截断
_LMX_DEFAULT = 15


def _zfun(z):
    """bonk/zfun.m:3-47 的等离子体色散函数 Z(zeta)=i*sqrt(pi)*w(z)。

    实部恰为 0 的点走 erfc 分支；其余点走 Weideman N=64 的 FFT 系数多项式分支，
    下半平面点先共轭到上半平面再共轭还原。标量与数组输入均可。
    """
    _sp = _special_backend()
    zz_in = _np.asarray(z, dtype=_np.complex128)
    scalar = zz_in.ndim == 0
    zz = _np.atleast_1d(zz_in).ravel().copy()
    w = _np.zeros(zz.shape, dtype=_np.complex128)

    idx = zz.real == 0
    if idx.any():
        z_imag = zz[idx]
        w[idx] = _np.exp(-(z_imag**2)) * _sp.erfc(z_imag.imag)

    if idx.all():
        zeta = 1j * _SQRT_PI * w
        return complex(zeta[0]) if scalar else zeta.reshape(zz_in.shape)

    idx = ~idx
    idx1 = idx & (zz.imag < 0)
    zz[idx1] = _np.conj(zz[idx1])

    m = 2 * _ZFUN_N
    m2 = 2 * m
    k = _np.arange(-m + 1, m, dtype=_np.float64)
    ell = _np.sqrt(_ZFUN_N / _np.sqrt(2.0))

    theta = k * _np.pi / m
    t = ell * _np.tan(theta / 2.0)
    f = _np.exp(-(t**2)) * (ell**2 + t**2)
    f = _np.concatenate((_np.zeros(1, dtype=_np.float64), f))
    a = _np.real(_np.fft.fft(_np.fft.fftshift(f))) / m2
    a = a[1 : _ZFUN_N + 1][::-1]

    z_sel = zz[idx]
    denom = ell - 1j * z_sel
    zeta_poly = (ell + 1j * z_sel) / denom
    p = _np.polyval(a, zeta_poly)
    w[idx] = 2.0 * p / denom**2 + (1.0 / _SQRT_PI) / denom

    if idx1.any():
        w[idx1] = _np.conj(2.0 * _np.exp(-(zz[idx1] ** 2)) - w[idx1])

    zeta = 1j * _SQRT_PI * w
    return complex(zeta[0]) if scalar else zeta.reshape(zz_in.shape)


def _gamman(n, x):
    """bonk/Gamman.m:2-6：besseli(n,x,1)*exp(-x+|Re x|)，x 可为复数。"""
    _sp = _special_backend()
    return _sp.ive(n, x) * _np.exp(-x + _np.abs(_np.real(x)))


def _gammapn(n, x):
    """bonk/Gammapn.m:2-6：(besseli(n-1,x,1)+besseli(n+1,x,1))/2-besseli(n,x,1) 的指数标度版。"""
    _sp = _special_backend()
    return ((_sp.ive(n - 1, x) + _sp.ive(n + 1, x)) / 2.0 - _sp.ive(n, x)) * _np.exp(
        -x + _np.abs(_np.real(x))
    )


def _complex_sum(values):
    """Sum the two components separately, including cancelling harmonics."""
    if not _np.all(_np.isfinite(values)):
        raise FloatingPointError("complex harmonic contributions must be finite")
    try:
        return complex(
            _math.fsum(value.real for value in values), _math.fsum(value.imag for value in values)
        )
    except OverflowError as error:
        raise FloatingPointError("complex harmonic sum is not representable") from error


def _gamma_complex_tail(b, start, limit=20000):
    """Evaluate 2*sum(n>=start) exp(-b)*I_n(b), including complex/negative b.

    DLMF 10.25.2 implies |I_n(b)| <= I_n(|b|). The positive generating
    function (10.35.1) then bounds the omitted one-sided exact tail by
    exp[|b|-Re(b)+|b|*(cosh(t)-1)-m*t], t=asinh(m/|b|).
    Compare this bound to 1e-18*|sum| in log space. It bounds omitted exact
    terms only, not backend or rounding error. fsum reduces accumulation
    error; the absolute-sum check rejects severe cancellation, without claiming
    a global Bessel-backend error bound. Exhaustion, underflow and nonfinite
    terms raise FloatingPointError rather than returning zero or an unbounded partial sum.
    """
    b = complex(b)
    radius_b = abs(b)
    if not _math.isfinite(radius_b) or radius_b == 0:
        raise ValueError("complex harmonic tail argument must be finite and nonzero")
    start = max(start, 1)
    pieces = []
    magnitudes = []
    for first in range(start, start + limit, 64):
        stop = min(first + 64, start + limit)
        values = _gamman(_np.arange(first, stop), b)
        if not _np.all(_np.isfinite(values)):
            raise FloatingPointError("complex harmonic tail terms must be finite")
        pieces.append(_complex_sum(values))
        try:
            magnitudes.append(_math.fsum(abs(value) for value in values))
            total = _complex_sum(pieces)
            magnitude = abs(total)
        except OverflowError as error:
            raise FloatingPointError(
                "complex harmonic tail magnitude is not representable"
            ) from error
        if not _math.isfinite(magnitudes[-1]) or not _math.isfinite(magnitude):
            raise FloatingPointError("complex harmonic tail magnitude must be finite")
        if magnitude < _np.finfo(float).tiny:
            raise FloatingPointError(
                "complex harmonic tail is not representable with reliable precision"
            )
        m = float(stop)
        radius = _math.hypot(m, radius_b)
        ratio = m / radius_b
        tilt = (
            _math.asinh(ratio)
            if _math.isfinite(ratio)
            else _math.log(m) + _math.log(2) - _math.log(radius_b)
        )
        log_bound = radius_b - b.real + m * ((m / radius) / (1 + radius_b / radius) - tilt)
        if _math.isfinite(log_bound) and log_bound <= _math.log(magnitude) + _math.log(1e-18):
            try:
                if _np.finfo(float).eps * _math.fsum(magnitudes) > 1e-14 * magnitude:
                    raise FloatingPointError(
                        "complex harmonic tail is too ill-conditioned to evaluate reliably"
                    )
            except OverflowError as error:
                raise FloatingPointError(
                    "complex harmonic tail magnitude is not representable"
                ) from error
            if not _np.isfinite(2 * total):
                raise FloatingPointError("complex harmonic tail is not representable")
            return 2 * total
    raise FloatingPointError(
        "complex harmonic tail remainder could not be bounded within the term budget"
    )


def _gamma_tail(b, start):
    # The real positive kernel's positivity premise must not leak into complex b.
    if b.imag == 0 and b.real > 0:
        from ._dielectric_harmonic import _gamma_positive_tail

        return _gamma_positive_tail(b.real, start)
    return _gamma_complex_tail(b, start)


def _species_array(value, name):
    arr = _np.asarray(value)
    if arr.dtype.kind not in "iuf":
        raise ValueError("%s must be a real scalar or a 1-D array of real species values" % name)
    arr = _np.asarray(arr, dtype=_np.float64)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError("%s must be a scalar or a 1-D array, got %d axes" % (name, arr.ndim))
    if arr.size == 0:
        raise ValueError("%s must contain at least one species" % name)
    if not _np.all(_np.isfinite(arr)):
        raise ValueError("%s must be finite" % name)
    return arr


def _species_arrays(qs, ms, ns0, Ts0):
    named = (("qs", qs), ("ms", ms), ("ns0", ns0), ("Ts0", Ts0))
    arrays = [(_species_array(value, name), name) for name, value in named]
    lengths = sorted({arr.size for arr, _ in arrays if arr.size > 1})
    if len(lengths) > 1:
        raise ValueError(
            "mismatched species-array shapes: "
            + ", ".join("%s=%d" % (name, arr.size) for arr, name in arrays)
        )
    species_count = lengths[0] if lengths else 1
    out = []
    for arr, name in arrays:
        if arr.size == 1:
            out.append(_np.full(species_count, arr[0], dtype=_np.float64))
        else:
            out.append(arr)
    return species_count, out


def _real_scalar(value, name):
    arr = _np.asarray(value)
    if arr.ndim != 0 or arr.dtype.kind not in "iuf":
        raise ValueError("%s must be a real finite scalar" % name)
    out = float(arr)
    if not _np.isfinite(out):
        raise ValueError("%s must be finite" % name)
    return out


def _complex_scalar(value, name):
    arr = _np.asarray(value)
    if arr.ndim != 0 or arr.dtype.kind not in "iufc":
        raise ValueError("%s must be a finite scalar" % name)
    out = complex(arr)
    if not (_np.isfinite(out.real) and _np.isfinite(out.imag)):
        raise ValueError("%s must be finite" % name)
    return out


def _evaluate(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, lmx=_LMX_DEFAULT):
    """Evaluate the original numerical path at the caller angular frequency."""
    try:
        lmx = _operator.index(lmx)
    except TypeError:
        raise ValueError("lmx must be a non-negative integer") from None
    if lmx < 0:
        raise ValueError("lmx must be a non-negative integer, got %d" % lmx)

    b0 = _real_scalar(B0, "B0")
    w = _real_scalar(omega, "omega")
    kz_c = _real_scalar(kz, "kz")
    response_kz = kz_c if kz_c > 0.0 else -kz_c
    kx_c = _complex_scalar(kx, "kx")

    if b0 == 0:
        raise ValueError("B0 must be non-zero: wcs and rhocs degenerate at B0=0")
    if w == 0:
        raise ValueError("omega must be non-zero: it divides the response")
    if kz_c == 0:
        raise ValueError("kz must be non-zero: z0 and zn divide by kz")

    species_count, (qs_a, ms_a, ns0_a, ts0_a) = _species_arrays(qs, ms, ns0, Ts0)
    if _np.any(qs_a == 0):
        raise ValueError("qs must be non-zero: wcs and rhocs degenerate at zero charge")
    if _np.any(ms_a <= 0):
        raise ValueError("ms must be strictly positive")
    if _np.any(ns0_a <= 0):
        raise ValueError("ns0 must be strictly positive")
    if _np.any(ts0_a <= 0):
        raise ValueError("Ts0 must be strictly positive (Kelvin, not eV)")

    c = _np.sqrt(_C2)

    with _np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        # bonk/fDtensor.m:31-41
        vts = _np.sqrt(2.0 * _KB * ts0_a / ms_a)
        wcs = qs_a * b0 / ms_a
        wps2 = ns0_a * qs_a**2 / ms_a / _EPSILON0
        rhocs = _np.sqrt(_KB * ts0_a / ms_a) / wcs

        nx = c * kx_c / w
        nz = c * kz_c / w
        as_ = kx_c * rhocs
        bs = as_**2
        if (
            not all(
                _np.all(_np.isfinite(values))
                for values in (w, vts, wcs, wps2, rhocs, nx, nz, as_, bs)
            )
            or w == 0
            or _np.any(vts <= 0)
            or _np.any(wcs == 0)
            or _np.any(wps2 <= 0)
            or _np.any(rhocs == 0)
            or (kx_c != 0 and (_np.any(as_ == 0) or _np.any(bs == 0)))
        ):
            raise FloatingPointError(
                "derived kinetic scales must be finite and nonzero where divided"
            )
        if not _np.isfinite(_np.square(w)) or _np.square(w) == 0:
            raise FloatingPointError("squared kinetic frequency is not representable")
        if not _np.all(_np.isfinite(response_kz * vts)) or _np.any(response_kz * vts == 0):
            raise FloatingPointError("kinetic resonance scale is not finite and nonzero")

        # bonk/fDtensor.m:45-47
        K = _np.zeros((3, 3), dtype=_np.complex128)
        K[0, 0] = 1.0
        K[1, 1] = 1.0
        K[2, 2] = 1.0

        z0s = _np.zeros(species_count, dtype=_np.complex128)
        sqrt2 = _np.sqrt(2.0)

        # bonk/fDtensor.m:48-78
        from ._dielectric_harmonic import _a_function

        for j in range(species_count):
            z0 = w / (response_kz * vts[j])
            z0s[j] = w / (kz_c * vts[j])
            if not _np.isfinite(z0) or z0 == 0 or not _np.isfinite(z0s[j]):
                raise FloatingPointError("kinetic response scales are not representable")
            b = bs[j]
            a = as_[j]
            # Here A is close to 1, so subtracting its constant loses the
            # small response. The original z*Z expression has no large-z
            # cancellation when every harmonic argument is inside [-1, 1].
            direct_response = (abs(w) + lmx * abs(wcs[j])) / (response_kz * vts[j]) <= 1.0
            xy_terms, xz_terms, yz_terms, zz_terms = [], [], [], []
            for l in range(-lmx, lmx + 1):
                zn = (w - l * wcs[j]) / (response_kz * vts[j])
                if not _np.isfinite(zn):
                    raise FloatingPointError("kinetic harmonic argument is not finite")

                gam = _gamman(l, b)
                gamp = _gammapn(l, b)
                xsn_xx = l**2 * gam / b
                xsn_xy = 1j * l * gamp
                xsn_yy = l**2 / b * gam - 2.0 * b * gamp
                zn_val = _zfun(zn)
                # zn remains real even for complex kx. Outside the small-z
                # regime use analytic A, not 1 + the fixed N64 approximation.
                response = zn * zn_val if direct_response else complex(_a_function(_np.asarray(zn)))
                xz_terms.append(l * gam * response)
                yz_terms.append(gamp * response)
                zz_terms.append(zn * gam * response)

                term1 = wps2[j] / w**2 * (z0 * zn_val)

                K[0, 0] = K[0, 0] + term1 * xsn_xx
                xy_terms.append(term1 * xsn_xy)
                K[1, 1] = K[1, 1] + term1 * xsn_yy

            alpha = wps2[j] / w**2
            if not _np.isfinite(alpha) or alpha <= 0:
                raise FloatingPointError("kinetic response scales are not representable")
            cross_xy = _complex_sum(xy_terms)
            K[0, 1] += cross_xy
            K[1, 0] -= cross_xy
            # Sum(n*Gamma_n)=0, sum(Gamma'_n)=Gamma_(N+1)-Gamma_N.
            # Keep the finite-N complement: changing it would change the model.
            # The direct z*Z representation keeps the original +2*alpha*z0^2.
            # At b=0 Gamma_n=delta_n0, so the exact omitted tail is zero;
            # preserve both the old finite zz and the other singular entries.
            tail = 1.0 if direct_response else (_gamma_tail(b, lmx + 1) if b != 0 else 0.0)
            edge = 0.0 if direct_response else _gamman(lmx + 1, b) - _gamman(lmx, b)
            cross_x = sqrt2 * alpha * z0 / a * _complex_sum(xz_terms)
            cross_y = -1j * sqrt2 * alpha * z0 * a * (_complex_sum(yz_terms) - edge)
            K[0, 2] += cross_x
            K[2, 0] += cross_x
            K[1, 2] += cross_y
            K[2, 1] -= cross_y
            K[2, 2] += 2 * alpha * z0 * _complex_sum(zz_terms) + 2 * alpha * z0**2 * tail

        if kz_c < 0.0:
            K[0, 2] = -K[0, 2]
            K[1, 2] = -K[1, 2]
            K[2, 0] = -K[2, 0]
            K[2, 1] = -K[2, 1]

        # bonk/fDtensor.m:80-83：Maxwell 旋度项（21-11-12 19:37 的符号修正版）
        D = _np.zeros((3, 3), dtype=_np.complex128)
        D[0, 0] = K[0, 0] - nz**2
        D[1, 0] = K[1, 0]
        D[0, 1] = K[0, 1]
        D[0, 2] = K[0, 2] + nx * nz
        D[1, 1] = K[1, 1] - (nx**2 + nz**2)
        D[2, 0] = K[2, 0] + nx * nz
        D[2, 1] = K[2, 1]
        D[1, 2] = K[1, 2]
        D[2, 2] = K[2, 2] - nx**2

        # bonk/fDtensor.m:85-86：六项展开式行列式（非 LU 分解）
        det_d = (
            D[0, 0] * D[1, 1] * D[2, 2]
            + D[1, 0] * D[2, 1] * D[0, 2]
            + D[2, 0] * D[1, 2] * D[0, 1]
            - D[0, 2] * D[1, 1] * D[2, 0]
            - D[1, 2] * D[2, 1] * D[0, 0]
            - D[2, 2] * D[1, 0] * D[0, 1]
        )

    if kx_c == 0:
        # Only these original singular entries may remain nonfinite; retain raw values.
        finite_components = _np.array(
            [[False, True, False], [True, False, True], [False, True, True]]
        )
        if not all(_np.array_equal(_np.isfinite(tensor), finite_components) for tensor in (K, D)):
            raise FloatingPointError("kx=0 diagnostic lost its finite tensor components")
    elif not _np.all(_np.isfinite(K)) or not _np.all(_np.isfinite(D)) or not _np.isfinite(det_d):
        raise FloatingPointError("kinetic diagnostic tensor and determinant must be finite")

    return {
        "K": K,
        "D": D,
        "det_D": complex(det_d),
        "w": float(w),
        "vts": vts,
        "wcs": wcs,
        "wps2": wps2,
        "rhocs": rhocs,
        "nx": complex(nx),
        "nz": complex(nz),
        "as": _np.asarray(as_, dtype=_np.complex128),
        "bs": _np.asarray(bs, dtype=_np.complex128),
        "z0s": z0s,
        "lmx": int(lmx),
    }
