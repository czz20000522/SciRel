"""Assemble the finite-harmonic Maxwellian kinetic dielectric tensor with NumPy species and harmonic arrays."""

import math

import numpy as np
from scipy.special import hyp1f1

from .bessel_gamma import evaluate_bessel_gamma
from .plasma_dispersion import evaluate_plasma_dispersion


_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23


# Both representations are checked against independent high-precision values around +/-32.
# Those bounded checks support this dispatch threshold, not a global special-function error bound.
_A_SERIES_THRESHOLD = 32.0


def _a_series(zeta):
    """Return ``A(zeta)`` from ``hyp1f1`` on ``|zeta| < _A_SERIES_THRESHOLD``.

    ``A = hyp1f1(1, 1/2, -zeta^2) + i*sqrt(pi)*zeta*exp(-zeta^2)`` is the stable identity
    (damped-Dawson derivative relation). No pair of O(1) terms is subtracted, which is what made
    the previous ``zeta*Z`` evaluation lose the O(kz^-2) amplification (issue #203).
    """
    zeta = np.asarray(zeta, dtype=float)
    return hyp1f1(1.0, 0.5, -(zeta * zeta)) + 1j * np.sqrt(np.pi) * zeta * np.exp(-(zeta * zeta))


def _a_asymptotic(zeta):
    """Return ``A(zeta)`` from its asymptotic series ``-1/(2 zeta^2) - 3/(4 zeta^4) - ...``.

    For real zeta all algebraic terms have the same negative sign. At most 24 terms are kept;
    the loop stops earlier when the latest term is at most 1e-18 of the current sum. This is not
    a rigorous remainder bound or a search for the least term. Accuracy evidence is limited to
    the independent high-precision comparisons in the stability tests. Past the dispatch
    threshold the omitted exponential imaginary part is below binary64 range.
    """
    zeta = np.asarray(zeta, dtype=float)
    inv_square = 1.0 / (zeta * zeta)
    if not np.all(np.isfinite(inv_square)) or np.any(inv_square == 0):
        raise FloatingPointError("asymptotic response scale is not representable")
    term = -0.5 * inv_square
    total = term.copy()
    for k in range(1, 24):
        term = term * ((2.0 * k + 1.0) / 2.0) * inv_square
        total = total + term
        if np.all(np.abs(term) <= 1e-18 * np.abs(total)):
            break
    return total


def _a_function(zeta):
    """Return ``A(zeta) = 1 + zeta*Z(zeta)``, selecting the branch that stays accurate."""
    zeta = np.asarray(zeta, dtype=float)
    result = np.empty(zeta.shape, dtype=complex)
    small = np.abs(zeta) < _A_SERIES_THRESHOLD
    if np.any(small):
        result[small] = _a_series(zeta[small])
    if np.any(~small):
        result[~small] = _a_asymptotic(zeta[~small])
    return result


def _gamma_partial_sum(b, nmax):
    """Return ``sum_{n=-nmax..nmax} Gamma_n(b)`` from strictly positive terms."""
    pieces = []
    for first in range(0, nmax + 1, 256):
        orders = np.arange(first, min(first + 256, nmax + 1))
        try:
            values = np.real(evaluate_bessel_gamma(orders, b)["Gamma_n"])
        except ValueError as error:
            if str(error) != "Bessel-Gamma value is not representable":
                raise
            raise FloatingPointError(str(error)) from error
        if np.any(values < 0) or not np.all(np.isfinite(values)):
            raise FloatingPointError("harmonic tail terms must be finite and nonnegative")
        weights = np.where(orders == 0, 1.0, 2.0)
        pieces.append(math.fsum(weights * values))
    return math.fsum(pieces)


def _gamma_positive_tail(b, start, limit=20000):
    """Return ``2*sum_{n>N} Gamma_n(b)`` for ``N = start - 1``.

    Fixed positive b has its largest Gamma term at n=0. Use the complement only when the
    computed finite head is at most 1/2; this bounds subtraction conditioning, not SciPy's
    term errors. Otherwise sum positive terms with math.fsum and an independent remainder bound.

    DLMF 10.35.1 gives sum_j Gamma_j*exp(t*j)=exp[b*(cosh(t)-1)]. Positivity implies that the
    omitted one-sided tail starting at m is at most exp[b*(cosh(t)-1)-m*t]. Choose
    t=asinh(m/b), and compare the bound in log space to 1e-18 times the accumulated one-sided
    sum. This bounds omitted exact terms; it does not bound Bessel-backend or rounding errors.
    The finite term budget is only a cost bound: exhaustion, underflow or an unusable bound
    raises FloatingPointError rather than returning zero, a partial sum or a cancelling complement.
    """
    start = max(start, 1)
    if not np.isfinite(b) or b <= 0:
        raise ValueError("harmonic tail argument must be finite and positive")
    head = _gamma_partial_sum(b, start - 1)
    if 0.0 <= head <= 0.5:
        return 1.0 - head
    pieces = []
    for first in range(start, start + limit, 256):
        stop = min(first + 256, start + limit)
        try:
            values = np.real(evaluate_bessel_gamma(np.arange(first, stop), b)["Gamma_n"])
        except ValueError as error:
            if str(error) != "Bessel-Gamma value is not representable":
                raise
            raise FloatingPointError(str(error)) from error
        if np.any(values < 0) or not np.all(np.isfinite(values)):
            raise FloatingPointError("harmonic tail terms must be finite and nonnegative")
        pieces.append(math.fsum(values))
        total = math.fsum(pieces)
        if total < np.finfo(float).tiny:
            raise FloatingPointError(
                "positive harmonic tail is not representable with reliable precision"
            )
        m = float(stop)
        radius = math.hypot(m, b)
        ratio = m / b
        tilt = (
            math.asinh(ratio) if math.isfinite(ratio) else math.log(m) + math.log(2) - math.log(b)
        )
        log_bound = m * ((m / radius) / (1.0 + b / radius) - tilt)
        if math.isfinite(log_bound) and log_bound <= math.log(total) + math.log(1e-18):
            return 2.0 * total
    raise FloatingPointError("harmonic tail remainder could not be bounded within the term budget")


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


def _evaluate(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, lmx=5):
    """Evaluate the original numerical path at the caller angular frequency."""
    B0 = _finite_scalar("B0", B0, nonzero=True)
    omega = _finite_scalar("omega", omega, nonzero=True)
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

    vts = np.sqrt(2.0 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = ns0 * qs**2 / ms / _EPSILON0
    nx, nz = np.sqrt(_C2) * kx / omega, np.sqrt(_C2) * kz / omega
    a = kx * np.sqrt(_KB * Ts0 / ms) / wcs
    b = a**2
    if (
        not all(np.all(np.isfinite(values)) for values in (omega, vts, wcs, wps2, nx, nz, a, b))
        or np.any(a == 0)
        or np.any(b <= 0)
        or np.any(wps2 <= 0)
        or omega == 0
        or np.any(vts <= 0)
        or np.any(wcs == 0)
    ):
        raise FloatingPointError("derived kinetic scales must be finite and nonzero where divided")
    if not np.isfinite(np.square(omega)) or np.square(omega) == 0:
        raise FloatingPointError("squared kinetic frequency is not representable")
    if not np.all(np.isfinite(response_kz * vts)) or np.any(response_kz * vts == 0):
        raise FloatingPointError("kinetic resonance scale is not finite and nonzero")

    k_tensor = np.eye(3, dtype=complex)
    for s in range(qs.size):
        z0 = omega / (response_kz * vts[s])
        alpha = wps2[s] / omega**2
        if not np.isfinite(z0) or z0 == 0 or not np.isfinite(alpha) or alpha <= 0:
            raise FloatingPointError("kinetic response scales are not representable")
        # For small arguments keep z*Z itself, rather than losing that small
        # response by removing the O(1) part of A after summation (issue #232).
        direct_response = (abs(omega) + lmx * abs(wcs[s])) / (response_kz * vts[s]) <= 1.0
        # Otherwise the same finite sum is rewritten through A(zeta)=1+zeta*Z(zeta) so the
        # O(zeta^2) pieces that cancel the Maxwell curl term are never formed as differences of
        # O(zeta^2) floats (issue #203). Kxz/Kyz drop the exact zero of sum(n*Gamma_n) and pick up
        # the endpoint term of sum(Gamma_prime_n); Kzz keeps the truncation tail in the form that
        # converges for this ``b`` instead of returning a budgeted partial sum.
        sum_xz = 0.0j
        sum_yz = 0.0j
        sum_zz = 0.0j
        for n in range(-lmx, lmx + 1):
            zn = (omega - n * wcs[s]) / (response_kz * vts[s])
            if not np.isfinite(zn):
                raise FloatingPointError("kinetic harmonic argument is not finite")
            try:
                gamma = evaluate_bessel_gamma(n, b[s])
            except ValueError as error:
                if str(error) != "Bessel-Gamma value is not representable":
                    raise
                raise FloatingPointError(str(error)) from error
            g = complex(gamma["Gamma_n"])
            gp = complex(gamma["Gamma_prime_n"])
            z_value = complex(evaluate_plasma_dispersion(zn)["Z"])
            response = zn * z_value if direct_response else complex(_a_function(np.asarray(zn)))
            sum_xz += n * g * response
            sum_yz += gp * response
            sum_zz += zn * g * response
            # xx/xy/yy stay as before: their O(1) prefactors are not amplified by z0^2, and
            # alpha*z0*Z is evaluated the way the relation has always evaluated it.
            term = alpha * z0 * z_value
            xx = n**2 * g / b[s]
            xy = 1j * n * gp
            yy = xx - 2.0 * b[s] * gp
            k_tensor[0, 0] += term * xx
            k_tensor[0, 1] += term * xy
            k_tensor[1, 0] -= term * xy
            k_tensor[1, 1] += term * yy
        # Direct z*Z needs no endpoint subtraction and retains the original
        # +2*alpha*z0**2. The A branch keeps its finite-N endpoint and tail.
        tail = 1.0 if direct_response else _gamma_positive_tail(b[s], lmx + 1)
        try:
            edge = (
                0.0
                if direct_response
                else complex(evaluate_bessel_gamma(lmx + 1, b[s])["Gamma_n"])
                - complex(evaluate_bessel_gamma(lmx, b[s])["Gamma_n"])
            )
        except ValueError as error:
            if str(error) != "Bessel-Gamma value is not representable":
                raise
            raise FloatingPointError(str(error)) from error
        k_tensor[0, 2] += np.sqrt(2.0) * alpha * z0 / a[s] * sum_xz
        k_tensor[2, 0] += np.sqrt(2.0) * alpha * z0 / a[s] * sum_xz
        k_tensor[1, 2] += -1j * np.sqrt(2.0) * alpha * z0 * a[s] * (sum_yz - edge)
        k_tensor[2, 1] += 1j * np.sqrt(2.0) * alpha * z0 * a[s] * (sum_yz - edge)
        k_tensor[2, 2] += 2.0 * alpha * z0 * sum_zz + 2.0 * alpha * z0**2 * tail

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
        raise FloatingPointError("kinetic dispersion tensor is not finite and representable")
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
        "a": a,
        "b": b,
        "lmx": lmx,
        "tensor_convention": "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)",
    }
