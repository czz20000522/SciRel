"""Local evaluation of the Ronnmark harmonic response and its lambda derivative. The implementation selects stable Taylor, asymptotic, or quadrature expansions from the requested point."""
import math

import numpy as _np

__all__ = ["evaluate_ronnmark_r"]

_PI = _np.pi

_GL_ABSCISSA = (
    -0.989400934991649, -0.944575023073232, -0.865631202387831,
    -0.755404408355003, -0.617876244402643, -0.458016777657227,
    -0.281603550779258, -0.095012509837637, 0.989400934991649,
    0.944575023073232, 0.865631202387831, 0.755404408355003,
    0.617876244402643, 0.458016777657227, 0.281603550779258,
    0.095012509837637,
)

_GL_WEIGHT = (
    0.027152459411754, 0.062253523938647, 0.095158511682492,
    0.124628971255533, 0.149595988816576, 0.169156519395002,
    0.182603415044923, 0.189450610455068, 0.027152459411754,
    0.062253523938647, 0.095158511682492, 0.124628971255533,
    0.149595988816576, 0.169156519395002, 0.182603415044923,
    0.189450610455068,
)


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


def _rtay_fma(y, al):
    y = complex(y); al = complex(al)
    y2 = _cmul(y, y)
    pn = _cdiv(y, y2 - 1.0)
    pyn = _cdiv(_cmul(-y, y2 + 1.0), _cmul(y2 - 1.0, y2 - 1.0))
    r11 = pn; r21 = pyn; r12 = pn; r22 = pyn
    for i in range(2, 101):
        q1 = _cdiv(_rmul(float(2 * i - 1), 1.0), y2 - float(i * i))
        cot = _cmul(q1, al)
        pyn = _cmul(cot, pyn - _cmul(_cdiv(_rmul(2.0, y2), y2 - float(i * i)), pn))
        pn = _cmul(cot, pn)
        r11 = r11 + pn; r21 = r21 + pyn
        r12 = r12 + _rmul(float(i), pn); r22 = r22 + _rmul(float(i), pyn)
        if abs(pn) * 1e8 < abs(r11):
            break
    rc = _np.zeros((2, 2), dtype=_np.complex128)
    rc[0, 0] = r11; rc[0, 1] = r12; rc[1, 0] = r21; rc[1, 1] = r22
    return rc


def _rtay(y, al):
    """Taylor-series branch, bonk/RTAY.m:1-27."""
    rc = _np.zeros((2, 2), dtype=_np.complex128)
    y2 = y * y

    pn = y / (y2 - 1.0)
    pyn = -y * (y2 + 1.0) / (y2 - 1.0) ** 2
    rc[0, 0:2] = pn
    rc[1, 0:2] = pyn

    for i in range(2, 101):
        cot = (2.0 * i - 1.0) / (y2 - i * i) * al
        pyn = cot * (pyn - 2.0 * y2 / (y2 - i * i) * pn)
        pn = cot * pn
        rc[0, 0] = rc[0, 0] + pn
        rc[1, 0] = rc[1, 0] + pyn
        rc[0, 1] = rc[0, 1] + i * pn
        rc[1, 1] = rc[1, 1] + i * pyn

        if abs(pn) * 1e8 < abs(rc[0, 0]):
            break
    return rc


def _rasy(y, al):
    """Asymptotic-series branch, bonk/RASY.m:1-53."""
    rc = _np.zeros((2, 2), dtype=_np.complex128)

    y2 = y * y
    cot = _np.cos(_PI * y) / _np.sin(_PI * y)

    pn = -y / al
    pyn = pn
    a = 1.0 / (al * _np.sqrt(2.0 * _PI * al))
    qn = _PI * y2 * cot * a
    qyn = qn * (2.0 - y * _PI * cot) - y * _PI ** 2 * y2 * a

    p = pn + qn
    py = pyn + qyn
    pp = -pn - 1.5 * qn
    ppy = -pyn - 1.5 * qyn
    ay = abs(y) + 2.0

    t = 0.0
    c = 7.2e35
    for n in range(1, 101):
        m = n - 1
        pyn = (pyn * (m ** 2 - y2) - 2.0 * y2 * pn) / ((2.0 * m + 1.0) * al)
        pn = pn * (m ** 2 - y2) / ((2.0 * m + 1.0) * al)
        qyn = (qyn * ((m + 0.5) ** 2 - y2) - 2.0 * y2 * qn) / (2.0 * n * al)
        qn = qn * ((m + 0.5) ** 2 - y2) / (2.0 * n * al)

        if m >= ay:
            c = n * (abs(pn) + abs(qn))
            if c <= 1e-7 * abs(pp) or c >= t:
                break

        p = p + pn + qn
        py = py + pyn + qyn
        pp = pp - (n + 1.0) * pn - (n + 1.5) * qn
        ppy = ppy - (n + 1.0) * pyn - (n + 1.5) * qyn
        t = c

    rc[0, 0] = p + pn + qn
    rc[1, 0] = py + pyn + qyn
    rc[0, 1] = pp + p
    rc[1, 1] = ppy + py
    return rc


def _rint(yy, al):
    """16-point Gauss-Legendre branch, bonk/RINT.m:1-77."""
    rc = _np.zeros((2, 2), dtype=_np.complex128)
    pi = _PI

    if _np.real(yy) < 0:
        y = -yy
        sig = -1.0
    else:
        y = yy
        sig = 1.0

    ya = _np.imag(y)
    yr = _np.real(y)
    ul = pi - 2.8 * y / (36.0 + y)
    cot = _np.cos(pi * y) / _np.sin(pi * y)
    d = pi * (1.0 + cot ** 2)
    c = yr / al
    xo = _np.log(c + _np.sqrt(1.0 + c ** 2))

    for i in range(16):
        x = ul / 2.0 * (1.0 + _GL_ABSCISSA[i])
        z = _np.sin(x)
        c = _np.cos(x)
        g = yr / al * x / z
        t = _np.sqrt(1.0 + g ** 2)
        b = _np.log(g + t)
        g = (1.0 / x - c / z) * g / t
        t = al * (t * c - 1.0)
        z = _np.exp(x * ya)
        c = 0.5 * (z + 1.0 / z)
        s = 0.5j * (z - 1.0 / z)
        f = cot + g
        h = 1.0 - g * cot
        exf = _np.exp(t - y * b)
        o = b * c + x * s
        p = x * c - b * s
        xy = x * yr
        r = (f * c + h * s) * exf
        ry = (f * o - h * p + d * (c - g * s)) * exf
        rp = ((f * t - h * xy) * c + (h * t + f * xy) * s) * exf
        rpy = (
            f * (t * o - xy * p)
            - h * (t * p + xy * o)
            + ((t + xy * g) * c - (g * t - xy) * s) * d
        ) * exf

        x = xo / 2.0 * (1.0 + _GL_ABSCISSA[i])
        z = _np.exp(x)
        c = (z + 1.0 / z) / 2.0 - 1.0
        p = _np.exp(al * c - y * x)
        rc[0, 0] = rc[0, 0] + _GL_WEIGHT[i] * (ul * r + xo * p)
        rc[1, 0] = rc[1, 0] - _GL_WEIGHT[i] * (ul * ry + xo * x * p)
        rc[0, 1] = rc[0, 1] + _GL_WEIGHT[i] * (ul * rp + xo * al * c * p)
        rc[1, 1] = rc[1, 1] - _GL_WEIGHT[i] * (ul * rpy + xo * al * x * c * p)

    o = y / al
    p = y ** 2 / 2.0
    rc[0, 0] = o * (y * rc[0, 0] / 2.0 - 1.0) * sig
    rc[1, 0] = 2.0 * rc[0, 0] + o * (p * rc[1, 0] + 1.0) * sig
    rc[0, 1] = y * o * rc[0, 1] / 2.0 * sig
    rc[1, 1] = 2.0 * rc[0, 1] + o * p * rc[1, 1] * sig
    return rc


def _is_real_scalar(value):
    """Octave ``isreal``: true when the value carries no imaginary part."""
    arr = _np.asarray(value)
    if not _np.iscomplexobj(arr):
        return True
    return _np.imag(arr.reshape(())) == 0.0


def _octave_gt(lhs, rhs):
    """Reproduce Octave ``>`` for a scalar pair.

    The frozen source feeds ``AL = b = (k_perp*rho_c)^2``, which is complex
    whenever the source's ``fsolve`` scan works in the complex ``k_perp`` plane.
    Octave compares a complex operand carrying a non-zero imaginary part against
    another scalar by MAGNITUDE, and falls back to numeric comparison when both
    operands are real. Probe record:
    ``lanes/shared-evidence/octave-complex-comparison-semantics.txt``.
    """
    if _is_real_scalar(lhs) and _is_real_scalar(rhs):
        return _np.real(lhs) > _np.real(rhs)
    return abs(lhs) > abs(rhs)


def evaluate_ronnmark_r(x, lambda_):
    """Evaluate R(x, lambda) and dR/dlambda(x, lambda) via the RYLA selector.

    Parameters
    ----------
    x : complex scalar
        Ronnmark argument Y, typically (omega - kz*vt*czj)/wcs. Real or
        complex; finite (no NaN/inf).
    lambda_ : real or complex scalar
        AL = lambda = (k_perp*rho_c)^2, finite. It is real for real ``k_perp``
        and complex when the caller works in the complex ``k_perp`` plane, which
        is what the frozen source's ``fsolve`` scan does.

    Returns
    -------
    dict with keys
        ``R``          : complex scalar; R(x, lambda) = RC(1,1).
        ``dR_dlambda`` : complex scalar; RC(1,2), the column read as ``dRsj``
                         by bonk/fDR.m:70. It equals d(lambda*R)/dlambda,
                         i.e. R + lambda*dR/dlambda.
        ``branch``     : str; selector arm taken, one of
                         ``'RTAY(AL<4)'``, ``'RTAY(|Y|^2>75*AL)'``,
                         ``'RTAY(|Y|>40+AL/3)'``, ``'RASY'``, ``'RINT'``.
        ``RC``         : (2, 2) complex ndarray; full RYLA matrix, indexed as
                         in the Octave source (RC[0, 0] is RC(1,1)).
    """
    # The frozen source is Octave, whose arithmetic follows the dtype of Y:
    # real input stays real double, complex input uses complex double. That
    # distinction is load-bearing, because complex division rounds differently
    # from real division and RASY/RINT amplify it through cancellation. numpy
    # scalars also give the source's IEEE division semantics, so the RTAY pole
    # Y^2 == I^2 yields inf/NaN rather than a Python ZeroDivisionError.
    try:
        x_arr = _np.asarray(x)
        la = _np.asarray(lambda_)
        if (x_arr.ndim != 0 or la.ndim != 0
                or not _np.isfinite(x_arr) or not _np.isfinite(la)):
            raise ValueError("x and lambda_ must be finite scalars")
    except TypeError as error:
        raise ValueError("x and lambda_ must be finite numeric scalars") from error
    if _np.iscomplexobj(x_arr):
        y = _np.complex128(x_arr.reshape(()))
    else:
        y = _np.float64(_np.real(x_arr.reshape(())))
    la = la.reshape(())
    al = _np.complex128(la) if _np.iscomplexobj(la) else _np.float64(_np.real(la))
    ay = abs(y)

    if _octave_gt(4, al):
        rc, branch = _rtay_fma(y, al), "RTAY(AL<4)"
    elif _octave_gt(ay ** 2, 75 * al):
        rc, branch = _rtay_fma(y, al), "RTAY(|Y|^2>75*AL)"
    elif _octave_gt(ay, 40 + al / 3):
        rc, branch = _rtay_fma(y, al), "RTAY(|Y|>40+AL/3)"
    elif _octave_gt(3 * (al - 10), ay) and _octave_gt(15 * al, ay ** 2):
        rc, branch = _rasy(y, al), "RASY"
    else:
        rc, branch = _rint(y, al), "RINT"

    return {
        "R": complex(rc[0, 0]),
        "dR_dlambda": complex(rc[0, 1]),
        "branch": branch,
        "RC": rc,
    }
