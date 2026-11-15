"""Local evaluation of the Ronnmark harmonic response and its lambda derivative. The implementation selects stable Taylor, asymptotic, or quadrature expansions from the requested point."""

import math
from fractions import Fraction

import numpy as _np

from .._result import Result

__all__ = ["evaluate_ronnmark_r"]

_PI = _np.pi

_GL_ABSCISSA = (
    -0.989400934991649,
    -0.944575023073232,
    -0.865631202387831,
    -0.755404408355003,
    -0.617876244402643,
    -0.458016777657227,
    -0.281603550779258,
    -0.095012509837637,
    0.989400934991649,
    0.944575023073232,
    0.865631202387831,
    0.755404408355003,
    0.617876244402643,
    0.458016777657227,
    0.281603550779258,
    0.095012509837637,
)

_GL_WEIGHT = (
    0.027152459411754,
    0.062253523938647,
    0.095158511682492,
    0.124628971255533,
    0.149595988816576,
    0.169156519395002,
    0.182603415044923,
    0.189450610455068,
    0.027152459411754,
    0.062253523938647,
    0.095158511682492,
    0.124628971255533,
    0.149595988816576,
    0.169156519395002,
    0.182603415044923,
    0.189450610455068,
)


_SPLIT = 134217729.0


def _two_prod(a, b):
    p = a * b
    c = _SPLIT * a
    ah = c - (c - a)
    al = a - ah
    c = _SPLIT * b
    bh = c - (c - b)
    bl = b - bh
    return p, ((ah * bh - p) + ah * bl + al * bh) + al * bl


def _two_sum(a, b):
    s = a + b
    bb = s - a
    return s, (a - (s - bb)) + (b - bb)


def _fma(a, b, c):
    p, e = _two_prod(a, b)
    s, e2 = _two_sum(p, c)
    return s + (e + e2)


def _cmul(a, b):
    a = complex(a)
    b = complex(b)
    return complex(_fma(a.real, b.real, -(a.imag * b.imag)), _fma(a.real, b.imag, a.imag * b.real))


def _d(x, y):
    """IEEE-faithful float division: the reference solver yields +-inf / nan on a zero divisor, it never raises.

    Python's `/` on floats is the same correctly-rounded IEEE-754 double division numpy and
    the reference solver use, so this only changes the zero-divisor branch (the declared formulation's own Taylor
    series can hit ``Y^2 - I^2 == 0`` and continues with Inf/NaN rather than aborting).
    """
    try:
        return x / y
    except ZeroDivisionError:
        if x == 0.0 or x != x:
            return float("nan")
        return math.copysign(float("inf"), x) * math.copysign(1.0, y)


def _cdiv(a, b):
    a = complex(a)
    b = complex(b)
    ar, ai = a.real, a.imag
    br, bi = b.real, b.imag
    fab = -br if br < 0 else br
    fai = -bi if bi < 0 else bi
    if fab >= fai:
        t = _d(bi, br)
        d = _fma(bi, t, br)
        return complex(_d(_fma(ai, t, ar), d), _d(_fma(-ar, t, ai), d))
    t = _d(br, bi)
    d = _fma(br, t, bi)
    return complex(_d(_fma(ar, t, ai), d), _d(_fma(ai, t, -ar), d))


def _rmul(s, z):
    z = complex(z)
    return complex(s * z.real, s * z.imag)


def _zero_lambda_response(y):
    """Exact Taylor constant term, rounded only at the four returned components.

    R=H=(1/(y-1)+1/(y+1))/2.  If u=1/(y-1), v=1/(y+1),
    y*dR/dy=y*dH/dy=-(u+u*u+v-v*v)/2. Rational components avoid
    overflowing y*y and retain weak components next to the complex poles.
    This is only the exact lambda=0 endpoint, not a new expansion branch.
    """
    y = complex(y)
    real, imag = Fraction(y.real), Fraction(y.imag)

    def reciprocal(real):
        denominator = real * real + imag * imag
        if denominator == 0:
            raise FloatingPointError(
                f"Ronnmark RC has a genuine pole at x={y!r}, lambda_=0; "
                "see the ronnmark-r-function contract"
            )
        return real / denominator, -imag / denominator

    ur, ui = reciprocal(real - 1)
    vr, vi = reciprocal(real + 1)
    response = ((ur + vr) / 2, (ui + vi) / 2)
    scaled_dx = (
        -(ur + ur * ur - ui * ui + vr - vr * vr + vi * vi) / 2,
        -(ui + 2 * ur * ui + vi - 2 * vr * vi) / 2,
    )
    try:
        r = complex(float(response[0]), float(response[1]))
        dx = complex(float(scaled_dx[0]), float(scaled_dx[1]))
    except OverflowError as error:
        raise FloatingPointError(
            f"Ronnmark RC is not representable at x={y!r}, lambda_=0; "
            "the complete companion matrix is required by the ronnmark-r-function contract"
        ) from error
    return _np.array([[r, r], [dx, dx]], dtype=_np.complex128)


def _rtay_fma(y, al):
    y = complex(y)
    al = complex(al)
    if al == 0:
        return _zero_lambda_response(y)
    y2 = _cmul(y, y)
    pn = _cdiv(y, y2 - 1.0)
    pyn = _cdiv(_cmul(-y, y2 + 1.0), _cmul(y2 - 1.0, y2 - 1.0))
    r11 = pn
    r21 = pyn
    r12 = pn
    r22 = pyn
    for i in range(2, 101):
        q1 = _cdiv(_rmul(float(2 * i - 1), 1.0), y2 - float(i * i))
        cot = _cmul(q1, al)
        pyn = _cmul(cot, pyn - _cmul(_cdiv(_rmul(2.0, y2), y2 - float(i * i)), pn))
        pn = _cmul(cot, pn)
        r11 = r11 + pn
        r21 = r21 + pyn
        r12 = r12 + _rmul(float(i), pn)
        r22 = r22 + _rmul(float(i), pyn)
        if abs(pn) * 1e8 < abs(r11):
            break
    rc = _np.zeros((2, 2), dtype=_np.complex128)
    rc[0, 0] = r11
    rc[0, 1] = r12
    rc[1, 0] = r21
    rc[1, 1] = r22
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
    qyn = qn * (2.0 - y * _PI * cot) - y * _PI**2 * y2 * a

    p = pn + qn
    py = pyn + qyn
    pp = -pn - 1.5 * qn
    ppy = -pyn - 1.5 * qyn
    ay = abs(y) + 2.0

    t = 0.0
    c = 7.2e35
    for n in range(1, 101):
        m = n - 1
        pyn = (pyn * (m**2 - y2) - 2.0 * y2 * pn) / ((2.0 * m + 1.0) * al)
        pn = pn * (m**2 - y2) / ((2.0 * m + 1.0) * al)
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
    d = pi * (1.0 + cot**2)
    c = yr / al
    xo = _np.log(c + _np.sqrt(1.0 + c**2))

    for i in range(16):
        x = ul / 2.0 * (1.0 + _GL_ABSCISSA[i])
        z = _np.sin(x)
        c = _np.cos(x)
        g = yr / al * x / z
        t = _np.sqrt(1.0 + g**2)
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
            f * (t * o - xy * p) - h * (t * p + xy * o) + ((t + xy * g) * c - (g * t - xy) * s) * d
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
    p = y**2 / 2.0
    rc[0, 0] = o * (y * rc[0, 0] / 2.0 - 1.0) * sig
    rc[1, 0] = 2.0 * rc[0, 0] + o * (p * rc[1, 0] + 1.0) * sig
    rc[0, 1] = y * o * rc[0, 1] / 2.0 * sig
    rc[1, 1] = 2.0 * rc[0, 1] + o * p * rc[1, 1] * sig
    return rc


def _is_real_scalar(value):
    """the reference solver ``isreal``: true when the value carries no imaginary part."""
    arr = _np.asarray(value)
    if not _np.iscomplexobj(arr):
        return True
    return _np.imag(arr.reshape(())) == 0.0


def _complex_gt(lhs, rhs):
    """Reproduce the reference solver ``>`` for a scalar pair.

    The declared formulation feeds ``AL = b = (k_perp*rho_c)^2``, which is complex
    whenever the source's ``fsolve`` scan works in the complex ``k_perp`` plane.
    the reference solver compares a complex operand carrying a non-zero imaginary part against
    another scalar by MAGNITUDE, and falls back to numeric comparison when both
    operands are real. Probe record:.
    """
    if _is_real_scalar(lhs) and _is_real_scalar(rhs):
        return _np.real(lhs) > _np.real(rhs)
    return abs(lhs) > abs(rhs)


def evaluate_ronnmark_r(x, lambda_):
    """Evaluate R(x, lambda) and H=d(lambda*R)/dlambda via the RYLA selector.

    Parameters
    ----------
    x : complex scalar
        Ronnmark argument Y, typically (omega - kz*vt*czj)/wcs
        [dimensionless]. Real or complex; finite (no NaN/inf).
    lambda_ : real or complex scalar
        AL = lambda = (k_perp*rho_c)^2 [dimensionless], finite. It is real for
        real ``k_perp`` and complex when the caller works in the complex
        ``k_perp`` plane, which is what the declared formulation's ``fsolve``
        scan does.

    Returns
    -------
    R : complex
        Value ``R(x, lambda) = RC(0, 0)`` [dimensionless].
    H : complex
        Value ``RC(0, 1)``, equal to ``d(lambda*R)/dlambda`` [dimensionless].
    branch : str
        Selected algorithm branch [dimensionless]: ``'RTAY(AL<4)'``,
        ``'RTAY(|Y|^2>75*AL)'``, ``'RTAY(|Y|>40+AL/3)'``, ``'RASY'`` or
        ``'RINT'``.
    RC : ndarray of complex128, shape (2,2)
        Full RYLA response matrix [dimensionless], indexed as in the source
        implementation.

    Raises
    ------
    ValueError
        If ``x`` or ``lambda_`` is not a finite numeric scalar.
    FloatingPointError
        If the selected response has a genuine pole or any required R/H/RC
        component cannot be computed as a finite binary64 value. No alternate
        branch or partial response is substituted.

    See Also
    --------
    scirel.kinetic.evaluate_dielectric_response : Ronnmark
        dispersion-tensor assembly.
    scirel.kinetic.evaluate_plasma_dispersion : Maxwellian Z family with the SciPy default.

    Notes
    -----
    The selector uses Taylor, asymptotic, and quadrature expansions according
    to the arguments. For complex ``lambda_``, the source solver compares
    non-real operands by magnitude. The returned derivative includes the
    response's ``lambda`` factor, so it is not the derivative of ``R`` alone.

    Independently, R=sum_n n**2*Gamma_n/(lambda*(x-n)) and the reported
    companion H=sum_n n**2*Gamma'_n/(x-n)=d(lambda*R)/d lambda, where
    Gamma_n=exp(-lambda)*I_n(lambda). The existing N80/160 tests retain their
    1e-14 truncation check and rtol=1e-7, atol=1e-9 R/H comparisons at twelve
    fixed samples. They do not certify all branches or global tensor accuracy.

    At exact lambda=0, R=H=x/(x*x-1) and RC[1,0]=RC[1,1]
    =-x*(x*x+1)/(x*x-1)**2. The Taylor constant term is evaluated with
    exact rational real/imaginary components before rounding to binary64;
    x=+/-2 is removable in the old recurrence, while x=+/-1 is a genuine
    pole. An overflowing companion is a failure even when R alone is finite.
    For nonzero lambda, any exact nonzero integer x has a pole in R or H;
    a finite cot(pi*x) caused by rounding does not regularize that pole.
    At exact x=0 the paired harmonic responses are odd and analytic, so all
    four RC entries are zero for every finite lambda. This endpoint is
    evaluated analytically within the selected branch.

    References
    ----------
    H. S. Xie, Phys. Plasmas 32, 082110 (2025).

    Examples
    --------
    >>> from scirel.kinetic import evaluate_ronnmark_r
    >>> r=evaluate_ronnmark_r(0.5,0.25); assert r['branch']=='RTAY(AL<4)'
    """
    # The declared formulation is the reference solver, whose arithmetic follows the dtype of Y:
    # real input stays real double, complex input uses complex double. That
    # distinction is load-bearing, because complex division rounds differently
    # from real division and RASY/RINT amplify it through cancellation. numpy
    # Internal nonzero-lambda arithmetic retains the source's IEEE policy;
    # the public boundary below refuses nonfinite ordinary results.
    try:
        x_arr = _np.asarray(x)
        la = _np.asarray(lambda_)
        if x_arr.ndim != 0 or la.ndim != 0 or not _np.isfinite(x_arr) or not _np.isfinite(la):
            raise ValueError("x and lambda_ must be finite scalars")
    except TypeError as error:
        raise ValueError("x and lambda_ must be finite numeric scalars") from error
    if _np.iscomplexobj(x_arr):
        y = _np.complex128(x_arr.reshape(()))
    else:
        y = _np.float64(_np.real(x_arr.reshape(())))
    la = la.reshape(())
    al = _np.complex128(la) if _np.iscomplexobj(la) else _np.float64(_np.real(la))
    ay = abs(y) if al != 0 else 0.0

    point = complex(y)
    if al != 0 and point.imag == 0 and point.real != 0 and point.real.is_integer():
        raise FloatingPointError(
            f"Ronnmark R/H has a genuine harmonic pole at x={point!r}, lambda_={al!r}; "
            "see the ronnmark-r-function contract; cotangent rounding does not remove the pole"
        )

    if _complex_gt(4, al):
        evaluate, branch = _rtay_fma, "RTAY(AL<4)"
    elif _complex_gt(ay**2, 75 * al):
        evaluate, branch = _rtay_fma, "RTAY(|Y|^2>75*AL)"
    elif _complex_gt(ay, 40 + al / 3):
        evaluate, branch = _rtay_fma, "RTAY(|Y|>40+AL/3)"
    elif _complex_gt(3 * (al - 10), ay) and _complex_gt(15 * al, ay**2):
        evaluate, branch = _rasy, "RASY"
    else:
        evaluate, branch = _rint, "RINT"

    rc = _np.zeros((2, 2), dtype=_np.complex128) if y == 0 else evaluate(y, al)

    if not _np.all(_np.isfinite(rc)):
        raise FloatingPointError(
            f"Ronnmark RC is nonfinite in {branch} at x={y!r}, lambda_={al!r}; "
            "see the ronnmark-r-function contract; no alternate branch was used"
        )

    return Result(
        {
            "R": complex(rc[0, 0]),
            "H": complex(rc[0, 1]),
            "branch": branch,
            "RC": rc,
        }
    )
