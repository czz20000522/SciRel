"""Pure Python/NumPy/SciPy BONK and EM fluid dispersion operators.

The packaged the reference environment files are retained as source evidence only.  Public calls
execute locally and do not require Linux, the reference solver, or an external checkout.
"""

from __future__ import annotations

import copy
import math
import operator
import numpy as np


class _LazyModule:
    def __init__(self, name):
        self._name = name
        self._module = None

    def __getattr__(self, attr):
        if self._module is None:
            import importlib

            self._module = importlib.import_module(self._name)
        return getattr(self._module, attr)


optimize = _LazyModule("scipy.optimize")
special = _LazyModule("scipy.special")

from .fluid_dispersion_matrix import assemble_fluid_dispersion_matrix
from .fluid_wavevector_eigensolve import _source_runtime_eigvals
from .gamma_lpole_coefficients import get_gamma_lpole_coefficients
from .z_pole_coefficients import get_z_pole_coefficients

__all__ = [
    "evaluate_fluid_special",
    "derive_fluid_case",
    "evaluate_fluid_dispersion",
    "solve_fluid_bonk",
    "assemble_fluid_em",
    "solve_fluid_em",
]

_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23
_QE = 1.60217662e-19
_EV_TO_J = 1.6022e-19
_MP = 1.6726219e-27
_ME = 9.1094e-31


def _mat_scalar(value, dtype=float):
    """Represent a scalar as the historical binary array ``(1, 1)`` port."""
    return np.asarray([[value]], dtype=dtype)


def _mat_row(value, dtype=None):
    """Represent a vector as the declared row port."""
    array = np.asarray(value, dtype=dtype)
    return array.reshape(1, -1)


def _mat_value(value):
    """Convert NumPy scalars/vectors to the old MAT boundary shapes."""
    array = np.asarray(value)
    if array.ndim == 0:
        return _mat_scalar(array.item(), dtype=array.dtype)
    if array.ndim == 1:
        return _mat_row(array, dtype=array.dtype)
    return array


def _legacy_state(state, family, *, with_frequency=None):
    """Project the internal state onto the former native workspace contract."""
    # The native parameter functions exported every caller-workspace variable.
    # In particular, all scalars were MAT ``(1,1)`` arrays and all vectors were
    # row vectors.  Keep this projection at the public boundary so the numerical
    # implementation can continue using ordinary NumPy scalar/vector values.
    common = [
        "B0",
        "S",
        "T00",
        "Ts0",
        "Ts_unit",
        "c",
        "c2",
        "epsilon0",
        "jcase",
        "kB",
        "kn",
        "kz",
        "me",
        "mp",
        "ms",
        "mu0",
        "n00",
        "ns0",
        "ns_unit",
        "qe",
        "qs",
        "rhocn",
        "rhocs",
        "vts",
        "wcn",
        "wcs",
        "wcs2",
        "wn",
        "wp2",
        "wps2",
    ]
    if family == "bonk":
        common.insert(common.index("wps2"), "wps")
    else:
        common.extend(["absrhocs", "kDs", "lambdaDs", "nx", "runtime", "sgns", "xx"])
    projected = {}
    for name in common:
        if name not in state:
            continue
        value = state[name]
        if name == "xx":
            projected[name] = _mat_row(value)
        elif name in {
            "ms",
            "qs",
            "ns_unit",
            "Ts_unit",
            "ns0",
            "Ts0",
            "vts",
            "wcs",
            "wps",
            "wcs2",
            "wps2",
            "rhocs",
            "absrhocs",
            "sgns",
            "lambdaDs",
            "kDs",
        }:
            projected[name] = _mat_row(value, dtype=float)
        else:
            projected[name] = _mat_value(value)
    if "wps" not in projected and "wps2" in projected:
        projected["wps"] = _mat_row(np.sqrt(np.asarray(state["wps2"], dtype=float)), dtype=float)
    if with_frequency is not None:
        projected["w"] = _mat_value(with_frequency)
    return projected


def _legacy_state_after(state):
    """Return exactly the eight fields exposed by the native dispersion call."""
    names = ("S", "c2", "wcs", "wps2", "rhocs", "w", "kz", "vts")
    return {name: _mat_value(state[name]) for name in names}


def _integer(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be an integer")
    try:
        return operator.index(value)
    except TypeError:
        raise ValueError(f"{name} must be an integer") from None


def _gamma(n, b):
    n, b = np.broadcast_arrays(np.asarray(n), np.asarray(b))
    if np.any(~np.isfinite(n)) or np.any(n != np.floor(n)) or np.iscomplexobj(n):
        raise ValueError("finite integer orders and finite Bessel arguments required")
    if np.any(~np.isfinite(b)):
        raise ValueError("finite integer orders and finite Bessel arguments required")
    n = n.astype(int)
    b = np.asarray(b, dtype=complex)
    return special.ive(n, b) * np.exp(-b + np.abs(np.real(b)))


def _gamma_prime(n, b):
    return (_gamma(np.asarray(n) - 1, b) + _gamma(np.asarray(n) + 1, b)) / 2 - _gamma(n, b)


def _r_harmonic(y, b):
    ya, ba = np.asarray(y), np.asarray(b)
    if ya.ndim or ba.ndim or not np.all(np.isfinite(ya)) or not np.all(np.isfinite(ba)):
        raise ValueError("Y and b must be finite scalars")
    y, b = ya.item(), ba.item()
    if b == 0:
        if y * y == 1:
            raise ValueError("Y=+/-1 is a genuine pole at b=0")
        if y == 0:
            return np.zeros((2, 2), complex)
        r = y / (y * y - 1)
        dr = -y * (y * y + 1) / (y * y - 1) ** 2
        return np.asarray([[r, r], [dr, dr]], complex)
    if y == 0:
        return np.zeros((2, 2), complex)
    if np.isreal(y) and float(np.real(y)).is_integer():
        raise ValueError("nonzero integer Y is a cyclotron harmonic pole")
    a = abs(b)
    N = max(32, int(np.ceil(2 * abs(y) + 2)))
    while True:
        if N > 65536:
            raise ValueError("harmonic tail cannot be bounded within 65536 terms")
        log_bound = -np.real(b) + N * np.log(a / 2) - special.gammaln(N + 1) + a * a / (4 * (N + 1))
        q = a / (2 * (N + 1))
        if q < 0.5 and log_bound < np.log(1e-15 / (64 * (1 + abs(y)) * (1 + 1 / a))):
            break
        N *= 2
    n = np.arange(1, N + 1)
    g = _gamma(n, b)
    gp = _gamma_prime(n, b)
    den = y * y - n * n
    c = 2 * y * n * n / den
    cy = -2 * y * n * n * (y * y + n * n) / den**2
    vals = np.sum(np.column_stack((c * g / b, c * gp, cy * g / b, cy * gp)), axis=0)
    if not np.all(np.isfinite(vals)):
        raise ValueError("harmonic cancellation or overflow prevents the declared accuracy")
    return np.asarray([[vals[0], vals[1]], [vals[2], vals[3]]], complex)


def evaluate_fluid_special(method, x, parameter=None):
    r"""Evaluate the fluid-dispersion special functions.

    Parameters
    ----------
    method : string
        Scientific method selector. Shape: string. Constraints: Gamman, Gammapn, zfun,
        RTAY, RASY, RINT or RYLA. Units: [dimensionless].
    x : real/complex
        Integer Bessel order, Z argument or R argument Y. Shape: array for Gamma/Z;
        scalar for R. Constraints: Integer real Gamma order; finite other arguments.
        Units: [dimensionless].
    parameter : real/complex or None, optional
        Bessel b or R b; unused for Z. Shape: array for Gamma; scalar for R; None for Z.
        Constraints: Required for Gamma/R; finite. Default: None. Units:
        [dimensionless].

    Returns
    -------
    value : complex numeric array
        Gamma/Gamma derivative or Z array, or full R response matrix. Shape: broadcast
        input shape or 2x2. Constraints: Finite or explicit precision/pole failure.
        Units: [dimensionless].

    Raises
    ------
    FloatingPointError
        If a required intermediate or returned quantity is not finite.
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_fluid_case
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_bonk
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        Gamma_n uses the scaled Bessel relation exp(-b) I_n(b). The R selectors evaluate
        the finite resonant sum with tail bounds, overflow checks and explicit
        zero-argument limits. Supported scope: Gamma_n=e^-b I_n(b) and its
        neighbor-identity derivative for integer n; finite scalar/array b;
        Z(z)=i*sqrt(pi)*wofz(z) via scipy.special; explicit overflow failure; Full
        scalar R response for complex Y,b with tail and floating cancellation checks,
        bounded at 65536 terms; b=0 and Y=0 analytic limits. Excluded scope: No
        execution or fidelity claim for the Taylor/asymptotic/integral selector; No
        certified entire-complex-plane precision claim.

    Examples
    --------
    >>> from scirel.kinetic.fluid_spectrum import evaluate_fluid_special
    >>> value=evaluate_fluid_special('RTAY',2,0)
    """
    if method == "zfun":
        arr = np.asarray(x)
        if arr.size == 0 or not np.all(np.isfinite(arr)):
            raise ValueError("finite nonempty Z arguments required")
        out = 1j * np.sqrt(np.pi) * special.wofz(np.asarray(arr, complex))
    elif method in {"Gamman", "Gammapn"}:
        if parameter is None:
            raise ValueError("Gamma parameter is required")
        n, b = np.broadcast_arrays(np.asarray(x), np.asarray(parameter))
        if (
            n.size == 0
            or np.any(~np.isfinite(n))
            or np.any(~np.isfinite(b))
            or np.iscomplexobj(n)
            or np.any(n != np.floor(n))
        ):
            raise ValueError("finite integer orders and finite Bessel arguments required")
        out = _gamma(n.astype(int), b) if method == "Gamman" else _gamma_prime(n.astype(int), b)
    elif method in {"RTAY", "RASY", "RINT", "RYLA"}:
        if parameter is None:
            raise ValueError("R parameter is required")
        out = _r_harmonic(x, parameter)
    else:
        raise ValueError("unknown special-function method")
    if not np.all(np.isfinite(out)):
        raise ValueError("special function is not representable")
    return _mat_value(out) if np.asarray(out).ndim <= 1 else np.asarray(out)


def _case_constants(family, jcase):
    if family == "bonk" and jcase == 1:
        return (
            np.array([_ME, 2 * _MP]),
            np.array([-1, 1]) * _QE,
            np.array([1.0, 1.0]),
            np.array([1.0, 1.0]),
            6.0,
            2e20,
            4e3,
            10.0,
        )
    if family == "bonk" and jcase == 2:
        return (
            np.array([_ME]),
            np.array([-_QE]),
            np.array([1.0]),
            np.array([1.0]),
            1.0,
            6.075e19,
            1e3,
            0.0,
        )
    if family == "bonk" and jcase == 3:
        return (
            np.array([_ME, 2 * _MP, 3 * _MP]),
            np.array([-1, 1, 1]) * _QE,
            np.array([1.0, 0.1, 0.9]),
            np.ones(3),
            6.0,
            2e20,
            2e3,
            1.0,
        )
    if family == "em" and jcase == 1:
        return (
            np.array([_ME, 2 * _MP]),
            np.array([-1, 1]) * _QE,
            np.array([1.0, 1.0]),
            np.array([1.0, 1.0]),
            6.0,
            2e20,
            4e3,
            10.0,
        )
    if family == "em" and jcase == 2:
        return (
            np.array([_ME]),
            np.array([-_QE]),
            np.array([1.0]),
            np.array([1.0]),
            1.0,
            6.075e19,
            1e3,
            0.0,
        )
    raise ValueError("undefined source case")


def derive_fluid_case(family, jcase=None):
    r"""Build a source-defined BONK or electromagnetic fluid case state.

    Parameters
    ----------
    family : string
        Source case family. Shape: string. Constraints: bonk or em. Units:
        [dimensionless].
    jcase : integer or None, optional
        Source case selector. Shape: scalar or None. Constraints: BONK1/2/3; EM1/2; None
        selects BONK1 or EM2. Default: None. Units: [dimensionless].

    Returns
    -------
    result : mapping
        Complete species scales and source material metadata; EM sets kz=0.1kn. Shape:
        mapping of MATLAB-shape arrays. Constraints: State and terminal diagnostics
        retain scientific meaning; no caller state mutation. Units: [mixed SI and
        dimensionless as described].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    evaluate_fluid_special
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_bonk
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The BONK and electromagnetic cases use their source-defined species tables,
        densities, temperatures, magnetic field and normalized axes. The returned
        mapping is an independent state assembled from those controls. Supported scope:
        BONK cases1/2/3 and EM cases1/2; complete fixed source constants/state. Excluded
        scope: No arbitrary species model construction through case controls; Global
        charge-neutral or self-consistent background equilibrium proof for electron-only
        case2.

    Examples
    --------
    >>> from scirel.kinetic.fluid_spectrum import derive_fluid_case
    >>> s=derive_fluid_case('bonk',3)
    """
    if family not in {"bonk", "em"}:
        raise ValueError("family must be bonk or em")
    jcase = _integer(
        1 if jcase is None and family == "bonk" else 2 if jcase is None else jcase, "jcase"
    )
    ms, qs, ns_unit, Ts_unit, B0, n00, T00, kz = _case_constants(family, jcase)
    ns0 = ns_unit * n00
    Ts0 = Ts_unit * T00 * _EV_TO_J / _KB
    vts = np.sqrt(2 * _KB * Ts0 / ms)
    wcs = qs * B0 / ms
    wps2 = ns0 * qs**2 / ms / _EPSILON0
    wps = np.sqrt(wps2)
    rhocs = np.sqrt(_KB * Ts0 / ms) / wcs
    absrhocs = np.abs(rhocs)
    sgns = np.sign(rhocs)
    wcn = np.min(np.abs(wcs))
    rhocn = np.max(absrhocs)
    kn = 1 / rhocn
    wn = wcn
    if family == "em":
        kz = 0.1 * kn
    state = {
        "S": np.asarray(ms.size),
        "c": np.asarray(np.sqrt(_C2)),
        "c2": np.asarray(_C2),
        "epsilon0": np.asarray(_EPSILON0),
        "mu0": np.asarray(1 / (_C2 * _EPSILON0)),
        "kB": np.asarray(_KB),
        "qe": np.asarray(_QE),
        "mp": np.asarray(_MP),
        "me": np.asarray(_ME),
        "ms": ms,
        "qs": qs,
        "ns_unit": ns_unit,
        "Ts_unit": Ts_unit,
        "B0": np.asarray(B0),
        "n00": np.asarray(n00),
        "T00": np.asarray(T00),
        "ns0": ns0,
        "Ts0": Ts0,
        "vts": vts,
        "wcs": wcs,
        "wps": wps,
        "wcs2": wcs**2,
        "wps2": wps2,
        "wp2": np.asarray(np.sum(wps2)),
        "rhocs": rhocs,
        "absrhocs": absrhocs,
        "sgns": sgns,
        "wcn": np.asarray(wcn),
        "rhocn": np.asarray(rhocn),
        "kn": np.asarray(kn),
        "wn": np.asarray(wn),
        "kz": np.asarray(kz),
        "jcase": np.asarray(jcase),
        "family": family,
    }
    if family == "em":
        lambdaDs = np.sqrt(_EPSILON0 * _KB * Ts0 / (ns0 * qs**2))
        state.update(
            lambdaDs=lambdaDs,
            kDs=1 / lambdaDs,
            xx=np.arange(0.05, 3.95 + 0.025, 0.05) * wn,
            nx=np.asarray(79),
            runtime=np.asarray(0.0),
        )
    return _legacy_state(state, family)


def _validate_state(state, require_w=True):
    names = ["S", "c2", "wcs", "wps2", "rhocs", "vts", "kz"] + (["w"] if require_w else [])
    if any(
        name not in state
        or np.asarray(state[name]).size == 0
        or not np.all(np.isfinite(state[name]))
        for name in names
    ):
        raise ValueError("missing, empty or nonfinite state field")
    S = _integer(np.asarray(state["S"]).item(), "S")
    if S < 1 or float(np.asarray(state["c2"]).item()) <= 0:
        raise ValueError("invalid species count or c2")
    if require_w and (float(np.asarray(state["w"]).item()) == 0 or not np.isrealobj(state["w"])):
        raise ValueError("real nonzero omega required")
    for name in ("wcs", "wps2", "rhocs", "vts"):
        arr = np.asarray(state[name], float).ravel()
        if (
            arr.size != S
            or (name == "wcs" and np.any(arr == 0))
            or (name == "rhocs" and np.any(arr == 0))
            or (name == "wps2" and np.any(arr <= 0))
            or (name == "vts" and np.any(arr <= 0))
        ):
            raise ValueError("species fields are incoherent")
    expected = np.asarray(state["vts"], float).ravel() / (
        np.sqrt(2) * np.asarray(state["wcs"], float).ravel()
    )
    if np.any(
        np.abs(np.asarray(state["rhocs"], float).ravel() - expected)
        > 128 * np.finfo(float).eps * np.maximum(np.abs(expected), np.finfo(float).tiny)
    ):
        raise ValueError(
            "rho must equal vthermal/(sqrt(2)*Omega) in the isotropic Maxwellian state"
        )
    return S


def _tensor(kx, state, lmx):
    _validate_state(state)
    lmx = _integer(lmx, "lmx")
    kx_array = np.asarray(kx)
    if kx_array.size == 1:
        kx = kx_array.item()
    if lmx < 1 or lmx > 4096 or np.asarray(kx).ndim or not np.isfinite(kx):
        raise ValueError("finite scalar kx and integer lmx in 1..4096 required")
    kx = complex(kx)
    w = float(np.asarray(state["w"]).item())
    kz = float(np.asarray(state["kz"]).item())
    kp = abs(kz)
    reflection = np.sign(kz)
    K = np.eye(3, dtype=complex)
    n = np.arange(-lmx, lmx + 1)
    for wc, wp, rho, vt in zip(
        np.asarray(state["wcs"], float).ravel(),
        np.asarray(state["wps2"], float).ravel(),
        np.asarray(state["rhocs"], float).ravel(),
        np.asarray(state["vts"], float).ravel(),
    ):
        a = kx * rho
        b = a * a
        g = _gamma(n, b)
        gp = _gamma_prime(n, b)
        if b == 0:
            xx = (np.abs(n) == 1) / 2
            na = np.zeros_like(n, complex)
        else:
            xx = n * n * g / b
            na = n * g / a
        xy = 1j * n * gp
        yy = xx - 2 * b * gp
        delta = w - n * wc
        weight = wp / w**2
        if kp == 0:
            active = (np.abs(xx) + np.abs(xy) + np.abs(yy) + np.abs(g)) > 0
            if np.any(delta[active] == 0):
                raise ValueError("zero-kz cyclotron resonance has no finite tensor")
            p = np.zeros_like(delta, complex)
            p[active] = -w / delta[active]
            K[0, 0] += weight * np.sum(p * xx)
            K[0, 1] += weight * np.sum(p * xy)
            K[1, 1] += weight * np.sum(p * yy)
            K[2, 2] += weight * np.sum(p * g)
        else:
            z0 = w / (kp * vt)
            z = delta / (kp * vt)
            Z = 1j * np.sqrt(np.pi) * special.wofz(z)
            Q = 1 + z * Z
            K[0, 0] += weight * np.sum(z0 * Z * xx)
            K[0, 1] += weight * np.sum(z0 * Z * xy)
            K[1, 1] += weight * np.sum(z0 * Z * yy)
            K[0, 2] += reflection * weight * np.sum(np.sqrt(2) * z0 * Q * na)
            K[1, 2] += reflection * weight * np.sum(-1j * np.sqrt(2) * z0 * Q * a * gp)
            K[2, 2] += weight * np.sum(2 * z0 * z * Q * g)
    K[1, 0] = -K[0, 1]
    K[2, 0] = K[0, 2]
    K[2, 1] = -K[1, 2]
    nx = np.sqrt(float(np.asarray(state["c2"]).item())) * kx / w
    nz = np.sqrt(float(np.asarray(state["c2"]).item())) * kz / w
    D = K + np.array(
        [[-nz * nz, 0, nx * nz], [0, -nx * nx - nz * nz, 0], [nx * nz, 0, -nx * nx]], complex
    )
    det = np.linalg.det(D)
    if not np.all(np.isfinite(D)) or not np.isfinite(det):
        raise ValueError("tensor or determinant is not representable")
    return det, K, D


def evaluate_fluid_dispersion(kx, state, method="fDR"):
    r"""Evaluate the local fluid dielectric response and determinant.

    Parameters
    ----------
    kx : real/complex
        Transverse wavevector. Shape: scalar. Constraints: Finite scalar. Units: [m^-1].
    state : mapping
        Explicit isotropic Maxwellian SI state. S species; c2; signed wcs and rhocs;
        positive wps2 and vts; w and signed kz. Matrix assembly additionally requires
        epsilon0. rho=vts/(sqrt(2)*wcs). Shape: mapping; species vectors length S;
        numeric arrays retain MATLAB shapes. Constraints: Finite numeric fields and
        coherent thermal/gyro scales; metadata cannot override explicit controls. Units:
        [c2 m²/s²; wcs,w rad/s; wps2 s^-2; rhocs m; vts m/s; kz m^-1; epsilon0 F/m].
    method : string, optional
        Numerical response approximation. Shape: string. Constraints: fD, fDR or
        fDtensor. Default: 'fDR'. Units: [dimensionless].

    Returns
    -------
    result : mapping
        determinant, K[3x3], D[3x3] dimensionless; unchanged explicit state_after.
        Shape: mapping of MATLAB-shape arrays. Constraints: State and terminal
        diagnostics retain scientific meaning; no caller state mutation. Units: [mixed
        SI and dimensionless as described].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_fluid_case
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_special
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_bonk
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The response builds the plasma susceptibility and Maxwell operator from an
        explicit isotropic Maxwellian state. The fD, fDR and fDtensor selectors use
        their declared finite-harmonic or rational approximations. Supported scope:
        Coherent SI state, complex kx, signed and zero kz; analytic nonresonant kx=0
        limits; Finite5/15 and full-harmonic J8 models, distinguished in output
        contract. Excluded scope: Genuine nonzero-residue cyclotron poles at zero kz;
        unmagnetized/zero-temperature/density/static-frequency limits.

    Examples
    --------
    >>> from scirel.kinetic.fluid_spectrum import derive_fluid_case,evaluate_fluid_dispersion
    >>> s=derive_fluid_case('bonk',2);s['w']=.63*s['wn']
    >>> r=evaluate_fluid_dispersion(0,s,'fD')
    """
    if method not in {"fD", "fDR", "fDtensor"}:
        raise ValueError("method must be fD, fDR or fDtensor")
    local = copy.deepcopy(state)
    _validate_state(local)
    local["kz"] = np.asarray(local["kz"])
    if method == "fDR":
        kz = float(np.asarray(local["kz"]).item())
        sign_kz = np.sign(kz)
        reflection = 1.0
        omega = float(np.asarray(local["w"]).item())
        c2 = float(np.asarray(local["c2"]).item())
        kx = complex(np.asarray(kx).item()) if np.asarray(kx).size == 1 else complex(kx)
        nx = np.sqrt(c2) * kx / omega
        nz = np.sqrt(c2) * abs(kz) / omega
        poles = get_z_pole_coefficients(j_order=8)
        K = np.eye(3, dtype=complex)
        rho = np.asarray(local["rhocs"], float).ravel()
        wcs = np.asarray(local["wcs"], float).ravel()
        wps2 = np.asarray(local["wps2"], float).ravel()
        vts = np.asarray(local["vts"], float).ravel()
        for wc, wp, vt, rho_s in zip(wcs, wps2, vts, rho):
            a_s = kx * rho_s
            b_s = a_s * a_s
            for bj, cj in zip(poles["bzj"], poles["czj"]):
                y = (omega - abs(kz) * vt * cj) / wc
                rc = _r_harmonic(y, b_s)
                R, dR = rc[0, 0], rc[0, 1]
                xx = R
                xy = 1j * dR / y
                xz = reflection * np.sqrt(2) * a_s * cj / y * R
                yy = R - 2 * b_s / y**2 * dR
                yz = -1j * reflection * np.sqrt(2) * a_s * cj / y**2 * dR
                zz = 2 * cj**2 / y**2 * (y + b_s * R)
                term = wp / (omega * wc) * bj
                K += term * np.array([[xx, xy, xz], [-xy, yy, yz], [xz, -yz, zz]])
        D = K + np.array(
            [[-nz * nz, 0, nx * nz], [0, -nx * nx - nz * nz, 0], [nx * nz, 0, -nx * nx]], complex
        )
        if sign_kz < 0:
            reflect = np.diag([1, 1, -1])
            K = reflect @ K @ reflect
            D = reflect @ D @ reflect
        return {
            "determinant": _mat_value(np.linalg.det(D)),
            "K": K,
            "D": D,
            "state_after": _legacy_state_after(local),
        }
    det, K, D = _tensor(kx, local, 5 if method == "fD" else 15)
    return {
        "determinant": _mat_value(det),
        "K": K,
        "D": D,
        "state_after": _legacy_state_after(local),
    }


def solve_fluid_bonk(jcase=1, omegas=None):
    r"""Solve the BONK fluid determinant over an angular-frequency axis.

    Parameters
    ----------
    jcase : integer, optional
        Source-defined case number. Shape: scalar. Constraints: Exactly BONK case1,2
        or3. Default: 1. Units: [dimensionless].
    omegas : real array or None, optional
        Angular frequency axis; None selects the source frequency ladder. Shape:
        nonempty vector or None. Constraints: Finite real nonzero elements in the
        caller's order. Default: None. Units: [rad/s].

    Returns
    -------
    result : mapping
        nf[m^-1], ordered xx[rad/s], root_valid, dual residuals, raw solver flags,
        iterations/evaluations, all attempts and complete source material state. Shape:
        mapping of MATLAB-shape arrays. Constraints: State and terminal diagnostics
        retain scientific meaning; no caller state mutation. Units: [mixed SI and
        dimensionless as described].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_fluid_case
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_special
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The determinant is evaluated with the fitted fDR response. Each frequency tries
        five complex seeds and accepts a candidate only when both the normalized wave
        residual and determinant residual are at most 1e-8. Unverified candidates remain
        in the returned attempt records. Supported scope: Three complete cases and
        source default78-frequency axis; arbitrary valid finite supplied axes; SciPy hybr
        tolerances (xtol=1e-12, maxfev=100); explicit bounded attempts and root
        verification. Excluded scope: No branch tracking, complete physical-mode
        enumeration or unconditional convergence.

    Examples
    --------
    >>> from scirel.kinetic.fluid_spectrum import derive_fluid_case,solve_fluid_bonk
    >>> s=derive_fluid_case('bonk',2)
    >>> r=solve_fluid_bonk(2,[.63*s['wn'].item()])
    """
    state = derive_fluid_case("bonk", jcase)
    xx = np.asarray(
        (np.arange(0.11, 3.95 + 0.025, 0.05) * float(np.asarray(state["wcn"]).item()))
        if omegas is None
        else omegas,
        float,
    ).ravel()
    if xx.size == 0 or not np.all(np.isfinite(xx)) or np.any(xx == 0):
        raise ValueError("nonempty finite nonzero real omega vector required")
    kn = float(np.asarray(state["kn"]).item())
    nf = np.empty((xx.size, 1), complex)
    residual = np.full((xx.size, 1), np.inf)
    normalized = np.full((xx.size, 1), np.inf)
    solver_residual = np.full((xx.size, 1), np.nan + 0j)
    valid = np.zeros((xx.size, 1), bool)
    status = np.zeros((xx.size, 1), int)
    iterations = np.zeros((xx.size, 1), int)
    attempts = np.empty((1, xx.size), object)
    for i, omega in enumerate(xx):
        local = copy.deepcopy(state)
        local["w"] = np.asarray(omega)
        best = np.inf
        rows = []
        for seed in [0.6 + 0j, 0.6 + 0.1j, 0.6 - 0.1j, 1 + 0j, 2 + 0j]:

            def fun(q):
                f = evaluate_fluid_dispersion((q[0] + 1j * q[1]) * kn, local, "fDR")[
                    "determinant"
                ].item()
                return [f.real, f.imag]

            try:
                sol = optimize.root(
                    fun,
                    [seed.real, seed.imag],
                    method="hybr",
                    options={"xtol": 1e-12, "maxfev": 100},
                )
                candidate = (sol.x[0] + 1j * sol.x[1]) * kn
                rr = evaluate_fluid_dispersion(candidate, local, "fDR")
                sv = np.linalg.svd(rr["D"], compute_uv=False)
                wave = float(np.min(sv) / max(1, np.max(sv)))
                detres = float(
                    abs(np.asarray(rr["determinant"]).item())
                    / max(1, np.prod(np.linalg.norm(rr["D"], axis=1)))
                )
                ok = np.isfinite(wave) and np.isfinite(detres) and wave <= 1e-8 and detres <= 1e-8
                rows.append(
                    {
                        "seed_kn": seed,
                        "candidate": candidate,
                        "solver_info": int(sol.status),
                        "raw_determinant": rr["determinant"].item(),
                        "scaled_fval": np.asarray(fun(sol.x)),
                        "wave_residual": wave,
                        "determinant_residual": detres,
                        "iterations": int(sol.nfev),
                        "function_evals": int(sol.nfev),
                    }
                )
                if wave < best or ok:
                    best = wave
                    nf[i, 0] = candidate
                    residual[i, 0] = wave
                    normalized[i, 0] = detres
                    solver_residual[i, 0] = np.asarray(rr["determinant"]).item()
                    status[i, 0] = int(sol.status)
                    iterations[i, 0] = int(sol.nfev)
                if ok:
                    valid[i, 0] = True
                    break
            except Exception as exc:
                rows.append({"seed_kn": seed, "error": str(exc)})
        attempts[0, i] = rows
    return _legacy_bonk_result(
        state, xx, nf, residual, normalized, valid, status, solver_residual, iterations, attempts
    )


def _poles(j_order, N):
    z = get_z_pole_coefficients(j_order=j_order)
    l = get_gamma_lpole_coefficients(max_harmonic=7)
    # The native pole producer always returned all eight source tables.  N is
    # a matrix control, not a pole-table truncation control.
    cn = np.empty((1, 8), object)
    for i in range(8):
        cn[0, i] = {"rl": l["residues"][i + 1].copy(), "pl": l["poles"][i + 1].copy()}
    return {
        "J": np.asarray(j_order),
        "L": np.asarray([l["order_lengths"][i + 1] for i in range(8)]),
        "cn": cn,
        "inverse_moment_diagnostics": _inverse_moment_diagnostics(cn),
        "bzj": z["bzj"],
        "czj": z["czj"],
        "n": np.asarray(j_order),
    }


def _complex_fsum(values):
    values = [complex(value) for value in values]
    return complex(
        math.fsum(value.real for value in values), math.fsum(value.imag for value in values)
    )


def _inverse_moment_diagnostics(cn):
    """Measure inverse pole moments of the sole finite coefficient table."""
    first = np.empty(7, dtype=complex)
    second = np.empty(7, dtype=complex)
    for n in range(1, 8):
        table = cn[0, n - 1]
        first[n - 1] = _complex_fsum(table["rl"] / table["pl"])
        second[n - 1] = _complex_fsum(table["rl"] / table["pl"] ** 2)
    return {
        "harmonics": np.arange(1, 8, dtype=int).reshape(1, -1),
        "sum_residue_over_pole": first.reshape(1, -1),
        "sum_residue_over_pole_squared": second.reshape(1, -1),
        "model_target": np.zeros((1, 1), dtype=complex),
    }


def _legacy_poles(poles):
    """Project pole tables to the old native workspace representation."""
    cn = np.empty((1, 8), object)
    for i in range(8):
        cn[0, i] = {
            "rl": _mat_row(poles["cn"][0, i]["rl"], dtype=complex),
            "pl": _mat_row(poles["cn"][0, i]["pl"], dtype=complex),
        }
    diagnostics = poles["inverse_moment_diagnostics"]
    return {
        "J": _mat_scalar(poles["J"].item()),
        "L": np.asarray(poles["L"], dtype=float).reshape(-1, 1),
        "bzj": _mat_row(poles["bzj"], dtype=complex),
        "cn": cn,
        "inverse_moment_diagnostics": {
            "harmonics": np.asarray(diagnostics["harmonics"], dtype=int),
            "sum_residue_over_pole": _mat_row(
                diagnostics["sum_residue_over_pole"].ravel(), dtype=complex
            ),
            "sum_residue_over_pole_squared": _mat_row(
                diagnostics["sum_residue_over_pole_squared"].ravel(), dtype=complex
            ),
            "model_target": np.asarray(diagnostics["model_target"], dtype=complex),
        },
        "czj": _mat_row(poles["czj"], dtype=complex),
        "n": _mat_scalar(poles["n"].item()),
    }


def _legacy_attempt_row(row):
    """Convert one SciPy attempt diagnostic to MAT scalar/column ports."""
    wave = row.get("wave_residual", np.nan)
    result = {
        "seed_kn": _mat_value(row.get("seed_kn", np.nan)),
        "candidate": _mat_value(row.get("candidate", np.nan)),
        "solver_info": _mat_scalar(row.get("solver_info", np.nan)),
        "raw_determinant": _mat_value(row.get("raw_determinant", np.nan)),
        "scaled_fval": np.asarray(row.get("scaled_fval", [np.nan]), dtype=float).reshape(-1, 1),
        "wave_residual": _mat_scalar(wave),
        "determinant_residual": _mat_scalar(row.get("determinant_residual", np.nan)),
        "dynamic_row_residual_diagnostic": _mat_scalar(
            row.get("dynamic_row_residual_diagnostic", wave)
        ),
        "iterations": _mat_scalar(row.get("iterations", np.nan)),
        "function_evals": _mat_scalar(row.get("function_evals", np.nan)),
    }
    return result


def _legacy_bonk_result(
    state, xx, nf, residual, normalized, valid, status, solver_residual, iterations, attempts
):
    """Restore the source sweep's complete workspace-shaped result graph."""
    frequencies = np.asarray(xx, float).ravel()
    rows_by_frequency = []
    for cell in attempts.flat:
        rows = [_legacy_attempt_row(row) for row in cell]
        obj = np.empty((1, len(rows)), object)
        for i, row in enumerate(rows):
            obj[0, i] = row
        rows_by_frequency.append(obj)
    solver_attempts = np.empty((1, len(rows_by_frequency)), object)
    for i, rows in enumerate(rows_by_frequency):
        solver_attempts[0, i] = rows
    final_rows = rows_by_frequency[-1]
    last = final_rows.flat[-1]
    final = evaluate_fluid_dispersion(nf[-1, 0], {**state, "w": np.asarray(frequencies[-1])}, "fDR")
    final_d = final["D"]
    final_k = final["K"]
    legacy = _legacy_state(state, "bonk")
    top = dict(legacy)
    top.update(
        {
            "D": final_d,
            "D0": final_d,
            "K": final_k,
            "attempt": _mat_scalar(len(final_rows.flat)),
            "attempt_rows": final_rows,
            "best": _mat_scalar(residual[-1, 0]),
            "candidate": _mat_value(nf[-1, 0]),
            "determinant_res": _mat_scalar(normalized[-1, 0]),
            "exit_status": _mat_value(status),
            "fDr": _mat_scalar(0.0),
            "function_evals": _mat_value(iterations),
            "info": _mat_scalar(status[-1, 0]),
            "iterations": _mat_value(iterations),
            "jx": _mat_scalar(len(frequencies)),
            "kx1": _mat_value(nf[-1, 0]),
            "nf": np.asarray(nf, dtype=complex),
            "normalized_determinant": np.asarray(normalized, dtype=float),
            "root_valid": np.asarray(valid, dtype=np.uint8),
            "nx": _mat_scalar(len(frequencies)),
            "options": {
                "xtol": _mat_scalar(1e-12),
                "maxfev": _mat_scalar(100),
            },
            "out": {
                "iterations": _mat_scalar(iterations[-1, 0]),
                "successful": _mat_scalar(status[-1, 0] == 1),
                "funcCount": _mat_scalar(iterations[-1, 0]),
            },
            "physical_sv": np.linalg.svd(final_d, compute_uv=False).reshape(-1, 1),
            "q": np.asarray(
                [
                    [
                        np.real(nf[-1, 0] / np.asarray(state["kn"]).item()),
                        np.imag(nf[-1, 0] / np.asarray(state["kn"]).item()),
                    ]
                ],
                dtype=float,
            ).T,
            "raw_f": _mat_value(final["determinant"]),
            "reference": _mat_scalar(1.0),
            "residual": np.asarray(residual, dtype=float),
            "result": legacy,
            "row_diagnostic": _mat_scalar(residual[-1, 0]),
            "runtime": _mat_scalar(0.0),
            "scale": np.ones((3, 1)),
            "scaled_fval": last["scaled_fval"],
            "seed": last["seed_kn"],
            "seeds": _mat_row([0.6 + 0j, 0.6 + 0.1j, 0.6 - 0.1j, 1 + 0j, 2 + 0j], dtype=complex),
            "solver_attempts": solver_attempts,
            "solver_residual": np.asarray(solver_residual, dtype=complex),
            "sv": np.linalg.svd(final_d, compute_uv=False).reshape(-1, 1),
            "valid": _mat_scalar(valid[-1, 0]),
            "w": _mat_scalar(frequencies[-1]),
            "wave_res": _mat_scalar(residual[-1, 0]),
            "xx": np.asarray(frequencies, dtype=float).reshape(1, -1),
            "complete_physical_modes": _mat_scalar(False),
            "root_contract": "bounded dimensionless fixed-seed searches; raw fsolve status retained; root_valid requires independent determinant and dimensionless normwise Maxwell residuals <=1e-8",
        }
    )
    return top


def assemble_fluid_em(state, omega, j_order=8, max_harmonic=6):
    r"""Assemble the electromagnetic fluid matrix at one frequency.

    Parameters
    ----------
    state : mapping
        Explicit isotropic Maxwellian SI state. S species; c2; signed wcs and rhocs;
        positive wps2 and vts; optional metadata w and signed kz. Matrix assembly
        additionally requires epsilon0. rho=vts/(sqrt(2)*wcs). Explicit omega is
        authoritative; state w is not required. Shape: mapping; species vectors length
        S; numeric arrays retain MATLAB shapes. Constraints: Finite numeric fields and
        coherent thermal/gyro scales; metadata cannot override explicit controls. Units:
        [c2 m²/s²; wcs,w rad/s; wps2 s^-2; rhocs m; vts m/s; kz m^-1; epsilon0 F/m].
    omega : real
        Explicit angular frequency, authoritative over state metadata. Shape: scalar.
        Constraints: Finite nonzero scalar. Units: [rad/s].
    j_order : integer, optional
        Source J-pole approximation order. Shape: scalar. Constraints: Exactly 8 or 12.
        Default: 8. Units: [dimensionless].
    max_harmonic : integer, optional
        Finite L-table maximum harmonic. Shape: scalar. Constraints: Integer 0..7.
        Default: 6. Units: [dimensionless].

    Returns
    -------
    result : mapping
        M entries carry mixed-state SI dimensions for kx X=M X; corrected poles,
        measured inverse_moment_diagnostics, state, omega and N. Shape: mapping of
        MATLAB-shape arrays. Constraints: State and terminal diagnostics retain
        scientific meaning; no caller state mutation. Units: [mixed SI and dimensionless
        as described].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_fluid_case
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_special
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_bonk
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The electromagnetic feedback terms are added to the fluid dielectric matrix at
        the caller-supplied frequency. Matrix completeness does not by itself identify
        which eigenvalues are physical modes. Supported scope: J8/J12, every N0..7,
        complete matrix state and source tables; Coherent SI state; signed/zero kz away
        from true rational resonance denominators. Excluded scope: No identity between
        finite fitted response and exact Bessel/Z kinetic dielectric.

    Examples
    --------
    >>> from scirel.kinetic.fluid_spectrum import derive_fluid_case,assemble_fluid_em
    >>> s=derive_fluid_case('em',2)
    >>> r=assemble_fluid_em(s,.83*s['wn'].item(),8,0)
    """
    j_order = _integer(j_order, "j_order")
    N = _integer(max_harmonic, "max_harmonic")
    if j_order not in (8, 12):
        raise ValueError("j_order must be one of 8 or 12")
    if N < 0 or N > 7:
        raise ValueError("max_harmonic must be an integer in 0..7")
    omega = float(omega)
    if not np.isfinite(omega) or omega == 0:
        raise ValueError("omega must be finite and non-zero")
    local = copy.deepcopy(state)
    local["w"] = np.asarray(omega)
    S = _validate_state(local, require_w=False)
    p = _poles(j_order, N)
    mat = assemble_fluid_dispersion_matrix(
        omega=omega,
        kz=float(np.asarray(local["kz"]).item()),
        c2=float(np.asarray(local["c2"]).item()),
        epsilon0=float(np.asarray(local["epsilon0"]).item()),
        wps2=np.asarray(local["wps2"]).ravel(),
        wcs=np.asarray(local["wcs"]).ravel(),
        vts=np.asarray(local["vts"]).ravel(),
        rhocs=np.asarray(local["rhocs"]).ravel(),
        sgns=np.sign(np.asarray(local["rhocs"]).ravel()),
        absrhocs=np.abs(np.asarray(local["rhocs"]).ravel()),
        cn_residues={i + 1: p["cn"][0, i]["rl"] for i in range(N + 1)},
        cn_poles={i + 1: p["cn"][0, i]["pl"] for i in range(N + 1)},
        order_lengths={i + 1: int(p["L"][i]) for i in range(N + 1)},
        bzj=p["bzj"],
        czj=p["czj"],
        max_harmonic=N,
        n_species=S,
    )
    # Restore the four polynomial conductivity terms omitted by the proper
    # fraction blocks.  This is the finite rational Maxwell correction from
    # the source derivation, expressed directly in NumPy scalars.
    A = 0j
    B = 0j
    C = 0j
    kz = float(np.asarray(local["kz"]).item())
    for si, (wp, wc, rho, sg, vt) in enumerate(
        zip(
            np.asarray(local["wps2"]).ravel(),
            np.asarray(local["wcs"]).ravel(),
            np.asarray(local["rhocs"]).ravel(),
            np.sign(np.asarray(local["rhocs"]).ravel()),
            np.asarray(local["vts"]).ravel(),
        )
    ):
        for bj, cj in zip(p["bzj"], p["czj"]):
            Y = (omega - abs(kz) * vt * cj) / wc
            for m in range(N + 1):
                signed = np.array([0]) if m == 0 else np.array([m, -m])
                cm = np.sum(0.5 / (Y - signed - 1) + 0.5 / (Y - signed + 1) - 1 / (Y - signed))
                rl = p["cn"][0, m]["rl"]
                pl = p["cn"][0, m]["pl"]
                pref = wp / (omega * wc) * bj * cm
                A += -2 * pref * abs(rho) * np.sum(rl)
                B += -2 * pref * np.sum(rl * pl)
                C -= 1j * np.sqrt(2) * pref * np.sign(kz) * sg * cj * np.sum(rl)
    c2 = float(np.asarray(local["c2"]).item())
    eps0 = float(np.asarray(local["epsilon0"]).item())
    n3 = int(mat["n_sl3"])
    alpha = -1j * omega * eps0 * A
    beta = -1j * omega * eps0 * B
    gamma = -1j * omega * eps0 * C
    M = mat["M"]
    M[n3 + 2, n3 + 0] += 1j * gamma / (c2 * eps0)
    M[n3 + 3, n3 + 0] += 1j * beta / (c2 * eps0)
    M[n3 + 3, n3 + 1] += 1j * gamma / (c2 * eps0)
    M[n3 + 3, n3 + 3] += 1j * alpha * omega / (c2 * eps0)
    mat["M"] = M
    return {
        "M": mat["M"],
        "poles": _legacy_poles(p),
        "state": _legacy_state(state, "em"),
        "omega": _mat_scalar(omega),
        "N": _mat_scalar(N),
    }


def solve_fluid_em(jcase=2, j_order=8, max_harmonic=6, omegas=None):
    r"""Solve the electromagnetic fluid spectrum over an angular-frequency axis.

    Parameters
    ----------
    jcase : integer, optional
        Source-defined case number. Shape: scalar. Constraints: Exactly EM case1 or2.
        Default: 2. Units: [dimensionless].
    j_order : integer, optional
        Source J-pole approximation order. Shape: scalar. Constraints: Exactly 8 or 12.
        Default: 8. Units: [dimensionless].
    max_harmonic : integer, optional
        Finite L-table maximum harmonic. Shape: scalar. Constraints: Integer 0..7.
        Default: 6. Units: [dimensionless].
    omegas : real array or None, optional
        Angular frequency axis; None selects the source frequency ladder. Shape:
        nonempty vector or None. Constraints: Finite real nonzero elements in the
        caller's order. Default: None. Units: [rad/s].

    Returns
    -------
    result : mapping
        kxx[axis length,5] m^-1; all spectra and selection candidates per frequency,
        matrix, exact tables, source case state and independent eigen diagnostics.
        Shape: mapping of MATLAB-shape arrays. Constraints: State and terminal
        diagnostics retain scientific meaning; no caller state mutation. Units: [mixed
        SI and dimensionless as described].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_fluid_case
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_special
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_fluid_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_bonk
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_em
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        Each frequency is assembled independently. Eigenvalues with positive real
        candidates are sorted by absolute imaginary part and the first five are
        selected; this is a deterministic heuristic rather than branch tracking.
        Supported scope: Two cases, J8/J12, all eight N controls and source79-frequency
        default; All finite spectra, original-order values, selection candidates and
        terminal matrices. Excluded scope: No claim that every auxiliary eigenvalue is a
        kinetic physical mode; no infinite-mode completeness or cross-thread invariance.

    Examples
    --------
    >>> from scirel.kinetic.fluid_spectrum import derive_fluid_case,solve_fluid_em
    >>> s=derive_fluid_case('em',2)
    >>> r=solve_fluid_em(2,8,0,[.83*s['wn'].item()])
    """
    state = derive_fluid_case("em", jcase)
    N = _integer(max_harmonic, "max_harmonic")
    xx = np.asarray(state["xx"] if omegas is None else omegas, float).ravel()
    if xx.size == 0 or not np.all(np.isfinite(xx)) or np.any(xx == 0):
        raise ValueError("nonempty finite nonzero real omega vector required")
    kxx = np.empty((xx.size, 5), complex)
    spectra = np.empty((1, xx.size), object)
    selected_cells = np.empty((1, xx.size), object)
    diagnostics = np.empty((1, xx.size), object)
    last = None
    for i, omega in enumerate(xx):
        out = assemble_fluid_em(state, omega, j_order, N)
        last = out
        d = _source_runtime_eigvals(out["M"])
        selected = d[np.real(d) > 1e-5 * float(np.asarray(state["kn"]).item())]
        selected = selected[np.argsort(np.abs(np.imag(selected)), kind="stable")]
        if selected.size < 5:
            raise ValueError("fewer than five positive-real candidate eigenvalues")
        kxx[i] = selected[:5]
        selected_cells[0, i] = selected.copy()
        spectra[0, i] = d.reshape(-1, 1)
        diagnostics[0, i] = {
            "eigenvalues": d,
            "eigenpair_residuals_computed": np.asarray(False, dtype=np.uint8),
            "finite_matrix_mode_count": np.asarray(d.size),
            "complete_finite_matrix_spectrum": np.asarray(d.size == out["M"].shape[0]),
            "complete_physical_modes": np.asarray(False),
            "selection_is_heuristic": np.asarray(True),
        }
    return _legacy_em_result(state, last, xx, kxx, spectra, selected_cells, diagnostics)


def _legacy_diagnostic(value):
    """Convert one eigen diagnostic record to native MAT shapes and dtypes."""
    return {
        "eigenvalues": np.asarray(value["eigenvalues"], complex).reshape(-1, 1),
        "eigenpair_residuals_computed": _mat_scalar(
            bool(value["eigenpair_residuals_computed"].item()), dtype=np.uint8
        ),
        "finite_matrix_mode_count": _mat_scalar(value["finite_matrix_mode_count"].item()),
        "complete_finite_matrix_spectrum": _mat_scalar(
            bool(value["complete_finite_matrix_spectrum"].item()), dtype=np.uint8
        ),
        "complete_physical_modes": _mat_scalar(
            bool(value["complete_physical_modes"].item()), dtype=np.uint8
        ),
        "selection_is_heuristic": _mat_scalar(
            bool(value["selection_is_heuristic"].item()), dtype=np.uint8
        ),
    }


def _legacy_em_result(state, last, xx, kxx, spectra, selected_cells, diagnostics):
    frequencies = np.asarray(xx, float).ravel()
    diagnostic_cells = np.empty((1, len(frequencies)), object)
    for i, value in enumerate(diagnostics.flat):
        diagnostic_cells[0, i] = _legacy_diagnostic(value)
    if len(frequencies) == 1:
        diagnostic_rows = diagnostic_cells[0, 0]
        spectrum = np.asarray(spectra[0, 0], complex).reshape(-1, 1)
        selected = np.asarray(selected_cells[0, 0], complex).reshape(-1, 1)
    else:
        diagnostic_rows = diagnostic_cells
        spectrum = spectra
        selected = selected_cells
    poles = last["poles"]
    legacy_state = _legacy_state(state, "em")
    last_diagnostic = _legacy_diagnostic(diagnostics[0, -1])
    if len(frequencies) == 1:
        d_value = np.asarray(spectra[0, 0], complex).reshape(-1, 1)
    else:
        d_value = np.empty((1, len(frequencies)), object)
        for i, value in enumerate(spectra[0]):
            d_value[0, i] = np.asarray(value, complex).reshape(-1, 1)
    top = dict(legacy_state)
    top.update(
        {
            "N": _mat_scalar(last["N"].item()),
            "d": d_value,
            "diagnostic_rows": diagnostic_rows,
            "eigen_diagnostics": last_diagnostic,
            "jx": _mat_scalar(len(frequencies)),
            "nx": _mat_scalar(len(frequencies)),
            "kx": selected,
            "kxx": np.asarray(kxx, complex),
            "matM": last["M"],
            "result": legacy_state,
            "roots": np.asarray(kxx[-1:, :], complex),
            "selected_candidates": selected,
            "spectra": spectrum,
            "w": last["omega"],
            "J": poles["J"],
            "cn": poles["cn"],
            "inverse_moment_diagnostics": poles["inverse_moment_diagnostics"],
            "bzj": poles["bzj"],
            "czj": poles["czj"],
            "xx": frequencies.reshape(1, -1),
        }
    )
    return top
