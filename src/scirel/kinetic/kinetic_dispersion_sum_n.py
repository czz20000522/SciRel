"""Assemble the finite-harmonic Maxwellian kinetic dielectric tensor with NumPy species and harmonic arrays."""

import numpy as np

from .bessel_gamma import evaluate_bessel_gamma
from .plasma_dispersion import evaluate_plasma_dispersion


_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23


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


def evaluate_kinetic_dispersion_sum(*, B0, qs, ms, ns0, Ts0, f, kz, kx, lmx=5):
    r"""Assemble the x-z-plane kinetic dielectric tensor, Maxwell dispersion tensor and determinant for a magnetized Maxwellian species mixture using a finite cyclotron-harmonic sum.

    Parameters
    ----------
    B0 : real numeric
        Signed homogeneous background magnetic field along z. [T] Shape: scalar. Finite and nonzero; boolean
        and complex inputs are rejected.
    qs : real numeric
        Signed charges on the shared species axis. [C] Shape: (S,), S >= 1. Finite and nonzero, with the
        same S as ms, ns0 and Ts0.
    ms : real numeric
        Species masses. [kg] Shape: (S,), same S as qs. Finite and strictly positive.
    ns0 : real numeric
        Species absolute number densities. [m^-3] Shape: (S,), same S as qs. Finite and strictly positive.
    Ts0 : real numeric
        Species equilibrium temperatures already converted to kelvin. [K] Shape: (S,), same S as qs. Finite
        and strictly positive.
    f : real numeric
        Real wave frequency before angular-frequency conversion. [Hz] Shape: scalar. Finite and nonzero.
    kz : real numeric
        Wavevector component parallel to B0. [m^-1] Shape: scalar. Finite and nonzero; no silent near-zero
        replacement.
    kx : real numeric
        Wavevector component perpendicular to B0 in the x-z plane. [m^-1] Shape: scalar. Finite and nonzero
        because terms divide by a_s and b_s; zero is not regularized.
    lmx : Python or NumPy integer
        Inclusive cyclotron-harmonic cutoff for n=-lmx..lmx. [dimensionless integer] Shape: scalar. Default:
        5. Non-negative integer; booleans, floats and numeric strings are rejected.

    Returns
    -------
    K : complex128
        Kinetic dielectric tensor with source sign convention. [dimensionless] Shape: (3, 3), x-y-z
        component axes. Finite; K_yx=-K_xy, K_zy=-K_yz and K_zx=K_xz by assembly.
    D : complex128
        Dispersion tensor after Maxwell curl terms. [dimensionless] Shape: (3, 3), x-y-z component axes.
        Finite; D_xx=K_xx-nz^2, D_yy=K_yy-nx^2-nz^2, D_zz=K_zz-nx^2 and D_xz=D_zx=K_xz+nx*nz.
    determinant : complex numeric
        Complex determinant of D. [dimensionless] Shape: scalar. Finite and representable; zero may indicate
        a candidate mode but no root selection occurs.
    omega : float
        Angular frequency 2*pi*f. [rad/s] Shape: scalar. Finite and nonzero.
    nx : float
        Perpendicular refractive-index component c*kx/omega. [dimensionless] Shape: scalar. Finite.
    nz : float
        Parallel refractive-index component c*kz/omega. [dimensionless] Shape: scalar. Finite.
    vts : float64
        Species thermal speeds with sqrt(2) convention. [m/s] Shape: (S,). Finite and positive.
    wcs : float64
        Signed species cyclotron angular frequencies. [rad/s] Shape: (S,). Finite and nonzero.
    wps2 : float64
        Species plasma angular-frequency squared. [rad^2/s^2] Shape: (S,). Finite and positive.
    b : float64
        Species dimensionless squared Bessel arguments a_s^2. [dimensionless] Shape: (S,). Finite and
        positive for accepted nonzero kx.
    lmx : int
        Echo of the used harmonic cutoff. [dimensionless integer] Shape: scalar. Non-negative.
    tensor_convention : string
        Explicit sign-convention label. [not applicable] Shape: scalar. Exactly K_ij = delta_ij -
        sigma_ij/(i*omega*epsilon0).

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite, boolean, complex or zero scalar fields where prohibited;
        empty/mismatched/nonfinite species vectors, zero charge, nonpositive mass/density/temperature,
        or lmx that is not a non-negative integer. Raises ValueError if derived scales become nonfinite
        or zero where positivity is required, or if special-function contributions, tensors or
        determinant become nonfinite or unrepresentable; other unexpected NumPy/SciPy errors propagate.

    See Also
    --------
    scirel.kinetic.bessel_gamma.evaluate_bessel_gamma : Related contract dependency.
    scirel.kinetic.plasma_dispersion.evaluate_plasma_dispersion : Related contract dependency.

    Notes
    -----
    omega=2*pi*f; vts=sqrt(2*kB*T_s/m_s); wcs=q_s*B0/m_s; wps2=n_s*q_s^2/(m_s*epsilon0);
    a_s=kx*sqrt(kB*T_s/m_s)/wcs; b_s=a_s^2; z_n=(omega-n*wcs)/(kz*vts). Sum n=-lmx..lmx with Gamma_n(b),
    Gamma_prime_n(b) and analytic Z(z_n), weighting each species term by (wps2/omega^2)*z_0*Z(z_n).
    Assemble the source-convention susceptibility components and K, then subtract the Maxwell curl terms
    to obtain D and its determinant. K_ij = delta_ij - sigma_ij/(i*omega*epsilon0). Truncated
    conventional cyclotron-harmonic sum for a homogeneous magnetized Maxwellian species mixture;
    analytic SciRel Faddeeva Z rather than a finite Weideman implementation Assumptions: Each species
    has a Maxwellian equilibrium with positive mass, number density and temperature. The caller judges
    whether the chosen lmx gives sufficient harmonic convergence for its case. A determinant value is
    not by itself a selected physical mode or a root.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_kinetic_dispersion_sum
    >>> r = evaluate_kinetic_dispersion_sum(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19], Ts0=[1000.0 * 1.6022e-19 / 1.38064852e-23], f=175881684853.009 / (2*np.pi), kz=1326.1942478795652, kx=13261.94247879565)
    >>> assert r['K'].shape == (3, 3) and r['D'].shape == (3, 3)
    >>> assert abs(r['determinant'] - (1184249.3244493124 + 4322451.2861608062j)) < 1e-6
    """
    B0 = _finite_scalar("B0", B0, nonzero=True)
    f = _finite_scalar("f", f, nonzero=True)
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

    omega = 2.0 * np.pi * f
    vts = np.sqrt(2.0 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = ns0 * qs**2 / ms / _EPSILON0
    nx, nz = np.sqrt(_C2) * kx / omega, np.sqrt(_C2) * kz / omega
    a = kx * np.sqrt(_KB * Ts0 / ms) / wcs
    b = a**2
    if (
        not all(np.all(np.isfinite(values)) for values in (omega, vts, wcs, wps2, nx, nz, a, b))
        or np.any(a == 0)
        or np.any(wps2 <= 0)
    ):
        raise ValueError("derived kinetic scales must be finite and nonzero where divided")

    k_tensor = np.eye(3, dtype=complex)
    for s in range(qs.size):
        z0 = omega / (response_kz * vts[s])
        for n in range(-lmx, lmx + 1):
            zn = (omega - n * wcs[s]) / (response_kz * vts[s])
            gamma = evaluate_bessel_gamma(n, b[s])
            g = complex(gamma["Gamma_n"])
            gp = complex(gamma["Gamma_prime_n"])
            z = complex(evaluate_plasma_dispersion(zn)["Z"])
            xx = n**2 * g / b[s]
            xy = 1j * n * gp
            xz = np.sqrt(2.0) * zn * n * g / a[s]
            yy = xx - 2.0 * b[s] * gp
            yz = -1j * np.sqrt(2.0) * zn * a[s] * gp
            zz = 2.0 * zn**2 * g
            term = wps2[s] / omega**2 * z0 * z
            k_tensor += term * np.array(
                [
                    [xx, xy, xz],
                    [-xy, yy, yz],
                    [xz, -yz, zz],
                ]
            )
        k_tensor[2, 2] += wps2[s] / omega**2 * 2.0 * z0**2

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
        raise ValueError("kinetic dispersion tensor is not finite and representable")
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
        "b": b,
        "lmx": lmx,
        "tensor_convention": "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)",
    }


__all__ = ["evaluate_kinetic_dispersion_sum"]
