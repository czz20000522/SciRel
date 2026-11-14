"""Evaluate the finite-harmonic fluid-dispersion kinetic dielectric tensor using local special-function terms."""

from __future__ import annotations

import operator
from functools import lru_cache
import numpy as np

from .kinetic_dispersion_sum_n import _a_function, _gamma_positive_tail

_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23

__all__ = ["evaluate_fluid_kinetic_dispersion_sum"]


def evaluate_fluid_kinetic_dispersion_sum(*, B0, qs, ms, ns0, Ts0, f, kz, kx, lmx=5):
    r"""Assemble the Maxwellian 3x3 kinetic tensor by finite cyclotron-harmonic sum with the source's positive near-zero kz clamp.

    Parameters
    ----------
    B0 : real numeric
        Background magnetic-field strength, setting the cyclotron frequency [T] Shape: scalar. Finite and
        nonzero; the cyclotron frequency is proportional to B0.
    qs : real numeric
        Charge of each species, setting the sign of the cyclotron frequency [C] Shape: `(S,)` one-
        dimensional species axis. Finite; element count matches the other species arrays.
    ms : real numeric
        Mass of each species, entering the thermal speed and cyclotron frequency [kg] Shape: `(S,)` one-
        dimensional species axis. Finite and strictly positive.
    ns0 : real numeric
        Absolute number density of each species, entering the plasma frequency [m^-3] Shape: `(S,)` one-
        dimensional species axis. Finite and strictly positive.
    Ts0 : real numeric
        Temperature of each species, already converted to kelvin under the source convention [K] Shape:
        `(S,)` one-dimensional species axis. Finite and strictly positive.
    f : real numeric
        Electromagnetic wave frequency, converted to angular frequency and then entering the resonance
        denominators and normalized refractive index [Hz] Shape: scalar. Finite and nonzero; omega is used
        as a divisor.
    kz : real numeric
        Wavevector component parallel to the magnetic field, entering the parallel-resonance argument and
        the Maxwell curl term [1/m] Shape: scalar. Finite; before division the frozen source implementation
        clamps `abs(kz)<1e-10` (including `kz=0`) to `+1e-10`.
    kx : real numeric
        Wavevector component perpendicular to the magnetic field, giving the Bessel argument and the
        refractive index [1/m] Shape: scalar. Finite.
    lmx : integer
        Bessel harmonic truncation order; the sum range is $|n|\le$ `lmx` [dimensionless] Shape: integer
        scalar. Default: 5. Optional, default 5 (matching the frozen source implementation); must be a
        nonnegative integer.

    Returns
    -------
    K : complex128
        Dielectric tensor under the convention
        $K_{ij}=\delta_{ij}-\sigma_{ij}/(\mathrm{i}\omega\varepsilon_0)$ [dimensionless] Shape: `(3, 3)`
        complex matrix with component axis order x, y, z. Finite complex numbers; the off-diagonal
        antisymmetric pairs satisfy $K_{yx}=-K_{xy}$ and $K_{zy}=-K_{yz}$.
    D : complex128
        Dispersion tensor including the Maxwell curl term, that is, the matrix in which the dispersion
        relation is expressed [dimensionless] Shape: `(3, 3)` complex matrix with component axis order x, y,
        z. Finite complex numbers; $D_{xx}=K_{xx}-n_z^2$, $D_{yy}=K_{yy}-(n_x^2+n_z^2)$,
        $D_{zz}=K_{zz}-n_x^2$, $D_{xz}=D_{zx}=K_{xz}+n_xn_z$.
    determinant : complex128
        Dispersion determinant $\mathcal{D}=\det D$; its zeros give the eigenmodes [dimensionless] Shape:
        complex scalar. Finite complex numbers.
    omega : real numeric
        Angular frequency converted from the input frequency [rad/s] Shape: scalar. Finite and nonzero.
    nx : real numeric
        Perpendicular refractive index $c k_\perp/\omega$ [dimensionless] Shape: scalar. Finite.
    nz : real numeric
        Parallel refractive index $c k_\parallel/\omega$ [dimensionless] Shape: scalar. Finite.
    vts : real numeric
        Thermal speed of each species $\sqrt{2k_BT_s/m_s}$ [m/s] Shape: `(S,)`. Strictly positive.
    wcs : real numeric
        Signed cyclotron frequency of each species [rad/s] Shape: `(S,)`. Nonzero, with the sign following
        qs*B0.
    wps2 : real numeric
        Plasma-frequency squared of each species [rad^2/s^2] Shape: `(S,)`. Strictly positive.
    b : real numeric
        Bessel argument of each species $b_s=(k_\perp\rho_{cs})^2$ [dimensionless] Shape: `(S,)`.
        Nonnegative.
    lmx : integer
        Harmonic truncation order actually used, echoing the input [dimensionless] Shape: integer scalar.
        Nonnegative integer.
    tensor_convention : string
        Text label of the tensor convention, for the caller to check the sign convention [not applicable]
        Shape: string. Fixed to `K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)`.

    Raises
    ------
    ValueError
        Raises ValueError for declared invalid inputs; numeric conversion errors may propagate for
        unsupported Python objects. Raises ValueError if the calculated tensor or function value is
        nonfinite, or if a positive harmonic tail cannot be represented reliably or bounded within
        the evaluation budget. No partial tail or tensor is returned.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    Sum harmonics -lmx..lmx using scaled Bessel Gamma terms. The xx/xy/yy components retain N=64
    Weideman Z. For each species with (abs(omega)+lmx*abs(wcs))/(abs(effective_kz)*vts)<=1,
    xz/yz/zz use z*Z(z) directly with the same Weideman Z, retaining the original +2*alpha*z0**2
    in zz. Otherwise they use the analytic real-argument response A(z)=1+z*Z(z), evaluated
    directly without subtracting two nearly equal terms. In that branch symmetric finite-sum
    identities retain the endpoint Gamma_(N+1)-Gamma_N and the tail 1-sum(Gamma_n); the tail is
    formed from positive terms when its complement is ill-conditioned. effective_kz includes
    the declared positive near-zero clamp. D adds Maxwell curl terms to K and
    determinant=det(D). Homogeneous magnetized Maxwellian plasma. Assumptions: Input units and
    normalization follow the declared ports; no physical parameters are inferred.

    This is a numerical-method correction of the same finite-harmonic model, not parity with
    the frozen N=64 rational expression. The real-argument A and positive-tail evaluators are
    shared with the conventional sum; the positive near-zero kz clamp and caller's lmx stay
    unchanged. Bounded tests compare full complex K/D against independent high-precision finite
    sums; they do not prove a continuous-domain error bound or harmonic convergence. An insufficient
    lmx can give a genuinely large tensor. An exhausted tail budget or unreliable positive tail
    raises ValueError instead of returning a partial sum or changing lmx. Root and determinant
    accuracy are not established by the tensor comparisons.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_fluid_kinetic_dispersion_sum
    >>> r=evaluate_fluid_kinetic_dispersion_sum(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19], Ts0=[11604941.036704937], f=1e10, kz=1.0, kx=1.0); assert r['D'].shape==(3,3)
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

    response_kz = kz if kz > 0.0 else -kz

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
        z0 = omega / (response_kz * vts[s])
        alpha = wps2[s] / omega**2
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
            gam, gamp = _gamma_and_prime(l, b)
            zn_value = _zfun(zn)
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
