"""Evaluate the finite-harmonic kinetic dielectric tensor and determinant with local special-function backends."""

import operator as _operator

import numpy as _np

__all__ = ["evaluate_kinetic_dielectric_tensor"]

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


def evaluate_kinetic_dielectric_tensor(B0, qs, ms, ns0, Ts0, f, kz, kx, lmx=_LMX_DEFAULT):
    r"""Evaluate all nine dielectric and dispersion tensor components using the source's default 15 harmonics.

    Parameters
    ----------
    B0 : real numeric
        Background magnetic-field strength; scalar; unit T (tesla); must be a finite nonzero real number
        (`B0=0` degenerates `wcs` and `rhocs` and raises directly). [T] Shape: scalar. Must be a finite
        nonzero real number (`B0=0` degenerates `wcs` and `rhocs` and raises directly).
    qs : real numeric
        Charge of each species; scalar or one-dimensional array of length `S`; unit C (coulomb); must be
        finite and nonzero (zero charge gives `wps2=0` and `wcs=0`); the sign sets the gyration direction.
        [C] Shape: scalar or (S,) species array. Finite and nonzero (zero charge gives `wps2=0` and
        `wcs=0`); the sign sets the gyration direction.
    ms : real numeric
        Mass of each species; scalar or one-dimensional array of length `S`; unit kg; must be strictly
        positive and finite. [kg] Shape: scalar or (S,) species array. Strictly positive and finite.
    ns0 : real numeric
        Number density of each species; scalar or one-dimensional array of length `S`; unit m^-3; must be
        strictly positive and finite. [m^-3] Shape: scalar or (S,) species array. Strictly positive and
        finite.
    Ts0 : real numeric
        Temperature of each species; scalar or one-dimensional array of length `S`; unit K (kelvin, **not**
        eV); must be strictly positive and finite; the caller converts eV by multiplying by `1.6022e-19/kB`
        (the frozen source comment states this convention). [K] Shape: scalar or (S,) species array.
        Strictly positive and finite; the caller converts eV by multiplying by `1.6022e-19/kB` (the frozen
        source comment states this convention).
    f : real numeric
        Electromagnetic wave frequency; scalar; unit Hz; must be a finite nonzero real number (`w=2*pi*f=0`
        divides by zero); internally uses `w=2*pi*f` (frozen source). [Hz] Shape: scalar. Finite nonzero
        real number (`w=2*pi*f=0` divides by zero); internally uses `w=2*pi*f` (frozen source).
    kz : real numeric
        Parallel wavenumber; scalar; unit rad/m; must be a finite nonzero real number (`z0` and `zn` are
        both divided by `kz`, frozen source). [rad/m] Shape: scalar. Finite nonzero real number (`z0` and
        `zn` are both divided by `kz`, frozen source).
    kx : complex128
        Perpendicular wavenumber; scalar; unit rad/m; must be finite and may be real or complex (the source
        `fsolve` scan uses complex `kx`); at `kx=0`, `as=0` and `Xsn_xz/Xsn_zz` become `NaN` (the source
        implementation behaves the same way; this operator does not mask it). [rad/m] Shape: scalar. Finite
        and may be real or complex (the source `fsolve` scan uses complex `kx`); at `kx=0`, `as=0` and
        `Xsn_xz/Xsn_zz` become `NaN` (the source implementation behaves the same way; this operator does not
        mask it).
    lmx : integer
        Bessel harmonic-sum truncation limit; integer scalar; dimensionless; must be a nonnegative integer,
        default `15` (frozen source); increase it to check convergence. [dimensionless] Shape: scalar.
        Default: 15. Nonnegative integer, default `15` (frozen source); increase it to check convergence.

    Returns
    -------
    K : complex128 array
        Kinetic dielectric tensor `K_ij`; `(3,3)` complex `numpy.ndarray` (axis 0 is row i, axis 1 is column
        j); dimensionless; initialized to `diag(1,1,1)`; when `kx=0` or `kz` is near zero some components
        may be `NaN`/`inf`, matching the source implementation without replacement. [dimensionless] Shape:
        (3,3). Kinetic dielectric tensor `K_ij`; `(3,3)` complex `numpy.ndarray` (axis 0 is row i, axis 1 is
        column j); dimensionless; initialized to `diag(1,1,1)`; when `kx=0` or `kz` is near zero some
        components may be `NaN`/`inf`, matching the source implementation without replacement.
    D : complex128 array
        Dispersion tensor `D_ij`; `(3,3)` complex `numpy.ndarray`; dimensionless; obtained from `K` by
        adding `nx^2`, `nz^2` and `nx*nz`; when `K` is `NaN` the corresponding components are also `NaN`.
        [dimensionless] Shape: (3,3). Dispersion tensor `D_ij`; `(3,3)` complex `numpy.ndarray`;
        dimensionless; obtained from `K` by adding `nx^2`, `nz^2` and `nx*nz`; when `K` is `NaN` the
        corresponding components are also `NaN`.
    det_D : complex128
        Dispersion determinant `det(D)`; complex scalar; dimensionless; evaluated from the six-term
        expansion and agrees with `numpy.linalg.det(D)` within floating-point error (a relative deviation of
        about 1e-9 is allowed when the real and imaginary magnitudes differ greatly). [dimensionless] Shape:
        scalar. Dispersion determinant `det(D)`; complex scalar; dimensionless; evaluated from the six-term
        expansion and agrees with `numpy.linalg.det(D)` within floating-point error (a relative deviation of
        about 1e-9 is allowed when the real and imaginary magnitudes differ greatly).
    w : real numeric
        Angular frequency; real scalar; unit rad/s; equal to `2*pi*f` and defined only when `f` is nonzero.
        [rad/s] Shape: scalar. Angular frequency; real scalar; unit rad/s; equal to `2*pi*f` and defined
        only when `f` is nonzero.
    vts : float64 array
        Thermal speed `sqrt(2*kB*Ts0/ms)` of each species; real array of shape `(S,)`; unit m/s; must be
        strictly positive. [m/s] Shape: (S,) species array. Strictly positive.
    wcs : float64 array
        Cyclotron frequency `qs*B0/ms` of each species; real array of shape `(S,)`; unit rad/s; carries the
        charge sign and is nonzero when `B0` is nonzero. [rad/s] Shape: (S,) species array. Cyclotron
        frequency `qs*B0/ms` of each species; real array of shape `(S,)`; unit rad/s; carries the charge
        sign and is nonzero when `B0` is nonzero.
    wps2 : float64 array
        Plasma-frequency squared `ns0*qs^2/ms/epsilon0` of each species; real array of shape `(S,)`; unit
        s^-2; nonnegative. [s^-2] Shape: (S,) species array. Plasma-frequency squared `ns0*qs^2/ms/epsilon0`
        of each species; real array of shape `(S,)`; unit s^-2; nonnegative.
    rhocs : float64 array
        Gyroradius `sqrt(kB*Ts0/ms)/wcs` of each species; real array of shape `(S,)`; unit m; signed and
        defined when `wcs` is nonzero. [m] Shape: (S,) species array. Gyroradius `sqrt(kB*Ts0/ms)/wcs` of
        each species; real array of shape `(S,)`; unit m; signed and defined when `wcs` is nonzero.
    nx : complex128
        Perpendicular refractive index `sqrt(c2)*kx/w`; complex scalar; dimensionless; defined when `w` is
        nonzero and complex whenever `kx` is complex. [dimensionless] Shape: scalar. Perpendicular
        refractive index `sqrt(c2)*kx/w`; complex scalar; dimensionless; defined when `w` is nonzero and
        complex whenever `kx` is complex.
    nz : complex128
        Parallel refractive index `sqrt(c2)*kz/w`; complex scalar; dimensionless; a real scalar when `w` is
        nonzero. [dimensionless] Shape: scalar. Parallel refractive index `sqrt(c2)*kz/w`; complex scalar;
        dimensionless; a real scalar when `w` is nonzero.
    as : complex128 array
        `kx*rhocs` of each species; complex array of shape `(S,)`; dimensionless; reduces to real when `kx`
        is real. [dimensionless] Shape: (S,) species array. `kx*rhocs` of each species; complex array of
        shape `(S,)`; dimensionless; reduces to real when `kx` is real.
    bs : complex128 array
        `as.^2` of each species; complex array of shape `(S,)`; dimensionless; at `bs=0` (that is, `kx=0`)
        `Gamman(l,b)/b` becomes `NaN`, matching the source implementation. [dimensionless] Shape: (S,)
        species array. `as.^2` of each species; complex array of shape `(S,)`; dimensionless; at `bs=0`
        (that is, `kx=0`) `Gamman(l,b)/b` becomes `NaN`, matching the source implementation.
    z0s : complex128 array
        `z0=w/(kz*vts)` of each species; complex array of shape `(S,)`; dimensionless; diagnostic only and
        not accumulated downstream. [dimensionless] Shape: (S,) species array. `z0=w/(kz*vts)` of each
        species; complex array of shape `(S,)`; dimensionless; diagnostic only and not accumulated
        downstream.
    lmx : integer
        Harmonic truncation limit actually used; integer scalar; dimensionless; equals the supplied `lmx` so
        the summation range can be reproduced. [dimensionless] Shape: scalar. Harmonic truncation limit
        actually used; integer scalar; dimensionless; equals the supplied `lmx` so the summation range can
        be reproduced.

    Raises
    ------
    ValueError
        Raises ValueError for declared invalid inputs; numeric conversion errors may propagate for
        unsupported Python objects.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    Sum l=-lmx..lmx Maxwellian harmonic contributions, form D from K with Maxwell curl terms, and
    evaluate its explicit six-term determinant. homogeneous magnetized Maxwellian multi-species plasma
    Assumptions: Input units and normalization follow the declared ports; no physical parameters are
    inferred.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_kinetic_dielectric_tensor
    >>> r=evaluate_kinetic_dielectric_tensor(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19], Ts0=[11604941.036704937],f=1e10,kz=1,kx=1e4); assert r['K'].shape==(3,3)
    """
    try:
        lmx = _operator.index(lmx)
    except TypeError:
        raise ValueError("lmx must be a non-negative integer") from None
    if lmx < 0:
        raise ValueError("lmx must be a non-negative integer, got %d" % lmx)

    b0 = _real_scalar(B0, "B0")
    freq = _real_scalar(f, "f")
    kz_c = _real_scalar(kz, "kz")
    response_kz = kz_c if kz_c > 0.0 else -kz_c
    kx_c = _complex_scalar(kx, "kx")

    if b0 == 0:
        raise ValueError("B0 must be non-zero: wcs and rhocs degenerate at B0=0")
    if freq == 0:
        raise ValueError("f must be non-zero: w=2*pi*f=0 divides by zero")
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

    w = 2.0 * _np.pi * freq
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

        # bonk/fDtensor.m:45-47
        K = _np.zeros((3, 3), dtype=_np.complex128)
        K[0, 0] = 1.0
        K[1, 1] = 1.0
        K[2, 2] = 1.0

        z0s = _np.zeros(species_count, dtype=_np.complex128)
        sqrt2 = _np.sqrt(2.0)

        # bonk/fDtensor.m:48-78
        for j in range(species_count):
            z0 = w / (response_kz * vts[j])
            z0s[j] = w / (kz_c * vts[j])
            b = bs[j]
            a = as_[j]
            for l in range(-lmx, lmx + 1):
                zn = (w - l * wcs[j]) / (response_kz * vts[j])

                xsn_xx = l**2 * _gamman(l, b) / b
                xsn_xy = 1j * l * _gammapn(l, b)
                xsn_xz = sqrt2 * zn * l * _gamman(l, b) / a
                xsn_yx = -xsn_xy
                xsn_yy = l**2 / b * _gamman(l, b) - 2.0 * b * _gammapn(l, b)
                xsn_yz = -1j * sqrt2 * zn * a * _gammapn(l, b)
                xsn_zx = xsn_xz
                xsn_zy = -xsn_yz
                xsn_zz = 2.0 * zn**2 * _gamman(l, b)

                zn_val = _zfun(zn)
                term1 = wps2[j] / w**2 * (z0 * zn_val)

                K[0, 0] = K[0, 0] + term1 * xsn_xx
                K[0, 1] = K[0, 1] + term1 * xsn_xy
                K[0, 2] = K[0, 2] + term1 * xsn_xz
                K[1, 0] = K[1, 0] + term1 * xsn_yx
                K[1, 1] = K[1, 1] + term1 * xsn_yy
                K[1, 2] = K[1, 2] + term1 * xsn_yz
                K[2, 0] = K[2, 0] + term1 * xsn_zx
                K[2, 1] = K[2, 1] + term1 * xsn_zy
                K[2, 2] = K[2, 2] + term1 * xsn_zz

            # bonk/fDtensor.m:77：fDR.m 中被注释掉、此处 load-bearing 的收尾项
            K[2, 2] = K[2, 2] + wps2[j] / w**2 * 2.0 * z0**2

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
