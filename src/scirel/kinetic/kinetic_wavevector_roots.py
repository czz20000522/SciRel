"""Complex wavevector root solving for the kinetic dielectric determinant, with explicit residual and convergence diagnostics."""

from __future__ import annotations

import operator

import numpy as np

from .kinetic_dispersion_ronnmark import evaluate_kinetic_dispersion_ronnmark

__all__ = ["solve_kinetic_wavevector_roots"]

_KB = 1.38064852e-23
_MACHINE_EPS = 2.220446049250313e-16


def _dogleg(r, b, d, delta):
    """the reference solver ``__dogleg__``: double-dogleg trust-region step for a 1x1 system."""
    x = b / r
    xn = abs(d * x)
    if xn > delta:
        s = (np.conj(r) * b) / d
        sn = abs(s)
        if sn > 0.0:
            s = (s / sn) / d
            tn = abs(r * s)
            snm = (sn / tn) / tn
            if snm < delta:
                bn = abs(b)
                dxn = delta / xn
                snmd = snm / delta
                t = (bn / sn) * (bn / xn) * snmd
                t = t - dxn * snmd**2 + np.sqrt((t - dxn) ** 2 + (1.0 - dxn**2) * (1.0 - snmd**2))
                alpha = dxn * (1.0 - snmd**2) / t
            else:
                alpha = 0.0
        else:
            alpha = delta / xn
            snm = 0.0
        x = alpha * x + ((1.0 - alpha) * min(snm, delta)) * s
    return x


def _reference_fsolve(fcn, x0, tol_fun, tol_x, max_iterations, max_function_evals):
    """Port of the declared reference solver ``fsolve`` for one complex unknown.

    The declaration sets ``Display``/``TolFun``/``Tolx`` only, so the port keeps the reference solver's
    other defaults: ``FinDiffType=forward``, ``Updating=off``, ``AutoScaling=off``,
    ``Jacobian=off``, ``ComplexEqn=off``, ``TypicalX=1``, ``MaxIter=400`` and
    ``MaxFunEvals=100*numel(x0)``.
    """
    dg = 1.0
    x = complex(x0)
    fval = complex(fcn(x))
    fn = abs(fval)
    xn = abs(dg * x)
    delta = max(xn, 1.0)
    niter = 1
    nfev = 1
    info = 0
    while niter < max_iterations and nfev < max_function_evals and info == 0:
        signp = np.sign(x)
        if signp == 0:
            signp = 1.0
        h = np.sqrt(_MACHINE_EPS) * signp * max(abs(x), 1.0)
        fjac = (complex(fcn(x + h)) - fval) / h
        nfev += 1
        if abs(fjac) < _MACHINE_EPS:
            info = -2
            break
        last_ratio = 0.0
        nfail = 0
        nsuc = 0
        decfac = 0.5
        while niter <= max_iterations and nfev < max_function_evals and info == 0:
            step = -_dogleg(fjac, fval, dg, delta)
            sn = abs(dg * step)
            if niter == 1:
                delta = min(delta, sn)
            fval1 = complex(fcn(x + step))
            fn1 = abs(fval1)
            nfev += 1
            actred = 1.0 - (fn1 / fn) ** 2 if fn1 < fn else -1.0
            predicted = abs(fval + fjac * step)
            if predicted < fn:
                prered = 1.0 - (predicted / fn) ** 2
                ratio = actred / prered
            else:
                prered = 0.0
                ratio = 0.0
            if ratio < min(max(0.1, 0.8 * last_ratio), 0.9):
                nsuc = 0
                nfail += 1
                delta *= decfac
                decfac = decfac**1.4142
                if fn <= tol_fun * xn:
                    info = 1
                elif delta <= 1e1 * _MACHINE_EPS * xn:
                    info = -3
                    break
            else:
                last_ratio = ratio
                decfac = 0.5
                nfail = 0
                nsuc += 1
                if abs(1.0 - ratio) <= 0.1:
                    delta = 1.4142 * sn
                elif ratio >= 0.5 or nsuc > 1:
                    delta = max(delta, 1.4142 * sn)
            if ratio >= 1e-4:
                x = x + step
                xn = abs(dg * x)
                fval = fval1
                fn = fn1
            niter += 1
            if fn <= tol_fun * xn:
                info = 1
            elif ratio >= 1e-4:
                if sn <= tol_x * xn:
                    info = 2
                elif actred < tol_fun:
                    info = 3
            break
    return x, fval, info, niter, nfev


def solve_kinetic_wavevector_roots(
    *,
    B0,
    qs,
    ms,
    ns0,
    Ts0,
    omegas,
    kz,
    kx_start,
    tol_fun=1e-16,
    tol_x=1e-16,
    max_iterations=400,
    max_function_evals=100,
):
    r"""Solve the Ronnmark determinant for complex kx at each supplied angular frequency from one fixed seed.

    Parameters
    ----------
    B0 : real numeric
        Background magnetic-field strength, entering the cyclotron frequency through the dispersion
        determinant [T] Shape: scalar. Finite and nonzero.
    qs : real numeric
        Species charges, setting the sign of the cyclotron frequency [C] Shape: `(S,)` one-dimensional
        species axis. Finite; element count matches the other species arrays.
    ms : real numeric
        Species masses, entering the thermal speed and the cyclotron frequency [kg] Shape: `(S,)` one-
        dimensional species axis. Finite and strictly positive.
    ns0 : real numeric
        Species absolute number densities, entering the plasma frequency [m^-3] Shape: `(S,)` one-
        dimensional species axis. Finite and strictly positive.
    Ts0 : real numeric
        Species temperatures, already converted to kelvin under the declared convention [K] Shape: `(S,)`
        one-dimensional species axis. Finite and strictly positive.
    omegas : real numeric
        Angular-frequency sequence whose roots are sought; each frequency point is solved independently with
        the same `kx_start` initial value, with no continuation between frequencies [rad/s] Shape: `(F,)`
        one-dimensional frequency axis. Non-empty finite array with nonzero elements, because the frequency
        appears in the resonance denominator.
    kz : real numeric
        Wavevector component parallel to the magnetic field, held fixed and entering the parallel resonance
        argument [1/m] Shape: scalar. Finite; zero is allowed (case 2 uses `kz=0.0`), in which case the
        parallel resonance argument reduces to $\omega/\omega_{cs}$.
    kx_start : complex128
        Starting complex initial value for continuation root finding, `x01=(0.6+0.0i)*kn` [1/m] Shape:
        scalar complex. Finite; it only affects which root is converged to, not the existence of the root
        itself.
    tol_fun : real numeric
        Relative residual convergence tolerance corresponding to the reference runtime `TolFun`
        [dimensionless] Shape: scalar. Default: 1e-16. Finite and strictly positive; defaults to `1e-16`
        (the reference solver default).
    tol_x : real numeric
        Relative variable-step convergence tolerance corresponding to the reference runtime `Tolx`
        [dimensionless] Shape: scalar. Default: 1e-16. Finite and strictly positive; defaults to `1e-16`
        (the reference solver default).
    max_iterations : integer
        Maximum iterations per frequency point, corresponding to the reference runtime `MaxIter`
        [dimensionless] Shape: scalar integer. Default: 400. At least 1; defaults to 400 (the reference
        runtime default).
    max_function_evals : integer
        Maximum objective-function evaluations per frequency point, corresponding to the reference runtime
        `MaxFunEvals` [dimensionless] Shape: scalar integer. Default: 100. At least 1; defaults to 100 (the
        reference runtime uses `100*numel(x0)` for a scalar unknown).

    Returns
    -------
    roots : complex128
        Complex perpendicular-wavenumber root obtained at each frequency point [1/m] Shape: `(F,)` one-
        dimensional frequency-axis complex array. Finite complex.
    residuals : complex128
        Dispersion-determinant residual $\mathcal{D}$ at each root [dimensionless] Shape: `(F,)` one-
        dimensional frequency-axis complex array. Finite complex; the quality of the root must be judged
        from this residual together with `last_updates`.
    determinant_scale : real numeric
        Maximum modulus of the dielectric-tensor elements at each root, used as the cancellation scale of
        the determinant residual at that frequency point [dimensionless] Shape: `(F,)` one-dimensional
        frequency-axis floating-point array. Nonnegative finite; `abs(residuals)/determinant_scale` is the
        relative zero quality of that root.
    exit_flags : integer
        The reference runtime `fsolve` exit flag at each frequency point (`1` residual met, `2` step met,
        `3` residual decrease met, `-2` Jacobian degenerate, `-3` trust region shrank to meaninglessness,
        `0` iteration or evaluation limit reached) [not applicable] Shape: `(F,)` one-dimensional frequency-
        axis integer array. Restricted to `{1,2,3,0,-2,-3}`.
    iterations : integer
        Iteration count actually used at each frequency point [dimensionless] Shape: `(F,)` one-dimensional
        frequency-axis integer array. Does not exceed `max_iterations`.
    function_evals : integer
        Objective-evaluation count actually used at each frequency point [dimensionless] Shape: `(F,)` one-
        dimensional frequency-axis integer array. Does not exceed `max_function_evals`.
    converged : bool
        Whether the exit flag is positive at each frequency point (that is, the reference runtime judged
        convergence) [not applicable] Shape: `(F,)` one-dimensional frequency-axis boolean array. When
        false, the root is still a numerical stationary point or an unconverged point of the determinant;
        the caller must decide acceptance from `residuals` and `determinant_scale`.
    omegas : real numeric
        Angular-frequency sequence actually used in this call, echoing the input [rad/s] Shape: `(F,)` one-
        dimensional frequency axis. Same length as `roots`.
    kz : real numeric
        Parallel wavenumber used in this root finding, echoing the input [1/m] Shape: scalar. Matches the
        input.
    kx_start : complex128
        Starting initial value used in this root finding, echoing the input [1/m] Shape: scalar complex.
        Matches the input.
    tol_fun : real numeric
        Residual threshold used in this call, echoing the input [dimensionless] Shape: scalar. Matches the
        input.
    tol_x : real numeric
        Variable threshold used in this call, echoing the input [dimensionless] Shape: scalar. Matches the
        input.
    max_iterations : integer
        Iteration limit used in this call, echoing the input [dimensionless] Shape: scalar integer. Matches
        the input.
    max_function_evals : integer
        Evaluation limit used in this call, echoing the input [dimensionless] Shape: scalar integer. Matches
        the input.
    solver : string
        Text label for the root-finding algorithm, so the caller can check the numerical path used [not
        applicable] Shape: string. Fixed at `reference_fsolve_dogleg_on_fDR`.

    Raises
    ------
    ValueError
        Raises ValueError for declared invalid inputs; numeric conversion errors may propagate for
        unsupported Python objects.

    See Also
    --------
    scirel.kinetic.kinetic_dispersion_ronnmark.evaluate_kinetic_dispersion_ronnmark : Related contract dependency.

    Notes
    -----
    Each frequency independently starts from kx_start and solves det(D)=0 with source-compatible complex
    trust-region dogleg arithmetic and bounded iteration/evaluation counts. homogeneous magnetized
    Maxwellian multi-species plasma Assumptions: Input units and normalization follow the declared
    ports; no physical parameters are inferred.

    Examples
    --------
    >>> from scirel.kinetic import solve_kinetic_wavevector_roots
    >>> r=solve_kinetic_wavevector_roots(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19], Ts0=[11604941.036704937],omegas=[1e11],kz=0,kx_start=8000); assert len(r['roots'])==1
    """

    B0 = float(B0)
    kz = float(kz)
    qs = np.asarray(qs, dtype=float)
    ms = np.asarray(ms, dtype=float)
    ns0 = np.asarray(ns0, dtype=float)
    Ts0 = np.asarray(Ts0, dtype=float)
    omegas = np.atleast_1d(np.asarray(omegas, dtype=float))
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
    if np.any(ns0 <= 0.0) or np.any(Ts0 <= 0.0):
        raise ValueError("ns0 and Ts0 must be strictly positive")
    if B0 == 0.0:
        raise ValueError("B0 must be non-zero: the gyrofrequency is proportional to B0")
    if not np.isfinite(kz):
        raise ValueError("kz must be finite")
    if omegas.size == 0 or not np.all(np.isfinite(omegas)) or np.any(omegas == 0.0):
        raise ValueError("omegas must be a non-empty finite array of non-zero values")
    if not np.isfinite(tol_fun) or tol_fun <= 0.0:
        raise ValueError("tol_fun must be finite and strictly positive")
    if not np.isfinite(tol_x) or tol_x <= 0.0:
        raise ValueError("tol_x must be finite and strictly positive")
    try:
        if isinstance(max_iterations, (bool, np.bool_)):
            raise TypeError
        max_iterations = operator.index(max_iterations)
    except TypeError as error:
        raise ValueError("max_iterations must be an integer") from error
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    try:
        if isinstance(max_function_evals, (bool, np.bool_)):
            raise TypeError
        max_function_evals = operator.index(max_function_evals)
    except TypeError as error:
        raise ValueError("max_function_evals must be an integer") from error
    if max_function_evals < 1:
        raise ValueError("max_function_evals must be at least 1")
    seed = complex(kx_start)
    if not np.isfinite(seed):
        raise ValueError("kx_start must be finite")

    determinant = evaluate_kinetic_dispersion_ronnmark

    def residual(omega, kx):
        return complex(
            determinant(
                B0=B0,
                qs=qs,
                ms=ms,
                ns0=ns0,
                Ts0=Ts0,
                omega=omega,
                kz=kz,
                kx=kx,
            )["determinant"]
        )

    roots = np.zeros(omegas.size, dtype=complex)
    residuals = np.zeros(omegas.size, dtype=complex)
    scales = np.zeros(omegas.size, dtype=float)
    exit_flags = np.zeros(omegas.size, dtype=np.int64)
    iterations = np.zeros(omegas.size, dtype=np.int64)
    function_evals = np.zeros(omegas.size, dtype=np.int64)

    for index, omega in enumerate(omegas):
        omega = float(omega)

        def fcn(kx, omega=omega):
            return residual(omega, kx)

        root, fval, info, niter, nfev = _reference_fsolve(
            fcn, seed, tol_fun, tol_x, max_iterations, max_function_evals
        )
        roots[index] = root
        residuals[index] = fval
        scales[index] = float(
            np.abs(
                determinant(
                    B0=B0,
                    qs=qs,
                    ms=ms,
                    ns0=ns0,
                    Ts0=Ts0,
                    omega=omega,
                    kz=kz,
                    kx=root,
                )["K"]
            ).max()
        )
        exit_flags[index] = info
        iterations[index] = niter
        function_evals[index] = nfev

    return {
        "roots": roots,
        "residuals": residuals,
        "determinant_scale": scales,
        "exit_flags": exit_flags,
        "iterations": iterations,
        "function_evals": function_evals,
        "converged": exit_flags > 0,
        "omegas": omegas,
        "kz": kz,
        "kx_start": seed,
        "tol_fun": tol_fun,
        "tol_x": tol_x,
        "max_iterations": max_iterations,
        "max_function_evals": max_function_evals,
        "solver": "reference_fsolve_dogleg_on_fDR",
    }


# --- r22fslv2 staged FMA-contracted the reference solver fsolve port (patch_solver_fma.py) ---
# FMA-contracted port of the declared reference solver's scalar-complex fsolve, transcribed from the frozen
# source's own solver arithmetic. It mirrors the reference solver at every hard operation:
#
#   magnitude     -> the scaled LAPACK-style complex `norm` (NOT abs/hypot); see _norm
#   complex *     -> _cmul  (Dekker two-product + two-sum FMA contraction)
#   complex /     -> _cdiv  (Smith + FMA)
#   real * cmplx  -> _rmul  (componentwise, matching std::complex operator*(double, complex))
#   fdjac         -> err=sqrt(eps); signp=x/|x| (0->1); h=err*signp*max(|x|,1)
#   nfev          -> forward difference costs 1 per unknown
#   dogleg        -> double-dogleg with the same statement order as the reference solver __dogleg__.m
#   ratios        -> actred/prered with (fn1/fn)^2, delta update 1.4142*sn, decfac^1.4142
#   loop guards   -> identical to the reference solver fsolve.m (Updating=off -> single inner pass)
#
# The declared formulation's first divergent solver step on the capped rows is the magnitude function:
# the reference solver's scalar-complex `norm` rounds one ULP below a correctly-rounded hypot on that operand,
# so the shipped math.hypot-based port flipped the fsolve terminal there.

import math

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
    """std::complex operator*(double, complex): componentwise real scaling."""
    z = complex(z)
    return complex(s * z.real, s * z.imag)


def _norm(z):
    """the declared reference solver's scalar-complex `norm`, identified empirically (r26dog-oct2 / r26norm4/5/6/9/10):
    NOT abs()/hypot. the reference solver computes the scaled LAPACK-style magnitude
    scale=max|x|, ssq=1+sum((|x_i|/scale)^2), result=scale*sqrt(ssq), which rounds one ULP below
    correctly-rounded hypot on the row-26 call-3 input. The shipped port used math.hypot, which is
    the arithmetic seat of the first divergent solver step."""
    z = complex(z)
    scale = 0.0
    ssq = 1.0
    for v in (abs(z.real), abs(z.imag)):
        if v != 0.0:
            if scale < v:
                r = scale / v
                ssq = 1.0 + ssq * r * r
                scale = v
            else:
                r = v / scale
                ssq = ssq + r * r
    return scale * math.sqrt(ssq) if scale != 0.0 else 0.0


_MACHINE_EPS = 2.220446049250313e-16


def _dogleg_fma(r, b, d, delta):
    x = _cdiv(b, r)
    xn = _norm(_rmul(d, x))
    if xn > delta:
        s = _cdiv(_cmul(complex(r.real, -r.imag), b), d)
        sn = _norm(s)
        if sn > 0.0:
            s = _cdiv(_cdiv(s, sn), d)
            tn = _norm(_cmul(r, s))
            snm = (sn / tn) / tn
            if snm < delta:
                bn = _norm(b)
                dxn = delta / xn
                snmd = snm / delta
                t = (bn / sn) * (bn / xn) * snmd
                t = t - dxn * snmd**2 + math.sqrt((t - dxn) ** 2 + (1.0 - dxn**2) * (1.0 - snmd**2))
                alpha = dxn * (1.0 - snmd**2) / t
            else:
                alpha = 0.0
        else:
            alpha = delta / xn
            snm = 0.0
        x = _rmul(alpha, x) + _rmul((1.0 - alpha) * min(snm, delta), s)
    return x


def _reference_fsolve_fma(fcn, x0, tol_fun, tol_x, max_iterations, max_function_evals):
    dg = 1.0
    x = complex(x0)
    fval = complex(fcn(x))
    fn = _norm(fval)
    xn = _norm(_rmul(dg, x))
    delta = max(xn, 1.0)
    niter = 1
    nfev = 1
    info = 0
    while niter < max_iterations and nfev < max_function_evals and info == 0:
        ax = _norm(x)
        signp = _cdiv(x, complex(ax, 0.0)) if ax != 0.0 else 1.0
        h = math.sqrt(_MACHINE_EPS) * signp * max(ax, 1.0)
        x1 = x + h
        fjac = _cdiv(complex(fcn(x1)) - fval, x1 - x)
        nfev += 1
        if _norm(fjac) < _MACHINE_EPS:
            info = -2
            break
        last_ratio = 0.0
        nfail = 0
        nsuc = 0
        decfac = 0.5
        while niter <= max_iterations and nfev < max_function_evals and info == 0:
            step = -_dogleg_fma(fjac, fval, dg, delta)
            sn = _norm(_rmul(dg, step))
            if niter == 1:
                delta = min(delta, sn)
            fval1 = complex(fcn(x + step))
            fn1 = _norm(fval1)
            nfev += 1
            actred = 1.0 - (fn1 / fn) ** 2 if fn1 < fn else -1.0
            w = fval + _cmul(fjac, step)
            t = _norm(w)
            if t < fn:
                prered = 1.0 - (t / fn) ** 2
                ratio = actred / prered
            else:
                prered = 0.0
                ratio = 0.0
            if ratio < min(max(0.1, 0.8 * last_ratio), 0.9):
                nsuc = 0
                nfail += 1
                delta *= decfac
                decfac = decfac**1.4142
                if fn <= tol_fun * xn:
                    info = 1
                elif delta <= 1e1 * _MACHINE_EPS * xn:
                    info = -3
                    break
            else:
                last_ratio = ratio
                decfac = 0.5
                nfail = 0
                nsuc += 1
                if abs(1.0 - ratio) <= 0.1:
                    delta = 1.4142 * sn
                elif ratio >= 0.5 or nsuc > 1:
                    delta = max(delta, 1.4142 * sn)
            if ratio >= 1e-4:
                x = x + step
                xn = _norm(_rmul(dg, x))
                fval = fval1
                fn = fn1
            niter += 1
            if fn <= tol_fun * xn:
                info = 1
            elif ratio >= 1e-4:
                if sn <= tol_x * xn:
                    info = 2
                elif actred < tol_fun:
                    info = 3
            break
    return x, fval, info, niter, nfev


def install(module):
    """Wire the FMA-contracted solver (and its dogleg) into a loaded workcopy module."""
    module._reference_fsolve = _reference_fsolve_fma
    module._dogleg = _dogleg_fma
    return module


_reference_fsolve = _reference_fsolve_fma
_dogleg = _dogleg_fma
