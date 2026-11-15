"""Raw kinetic response diagnostics with explicit representability masks."""

import numpy as np

from .._result import Result
from .dielectric_response import _CONVENTION, _harmonics

__all__ = ["evaluate_dielectric_diagnostics"]


def evaluate_dielectric_diagnostics(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, harmonics=15):
    """Evaluate the raw finite-harmonic diagnostic and identify finite entries.

    Parameters
    ----------
    B0 : real scalar
        Finite nonzero background magnetic field [T].
    qs : real scalar or array_like
        Finite nonzero species charges [C]. Scalar or shape (S,).
    ms : real scalar or array_like
        Finite positive species masses [kg]. Scalar or shape (S,).
    ns0 : real scalar or array_like
        Finite positive equilibrium densities [m^-3]. Scalar or shape (S,).
    Ts0 : real scalar or array_like
        Finite positive Maxwellian temperatures [K]. Scalar or shape (S,).
    omega : real scalar
        Finite nonzero angular frequency [rad/s].
    kz : real scalar
        Finite nonzero signed parallel phase wavenumber [1/m].
    kx : real or complex scalar
        Finite perpendicular phase wavenumber [1/m]. Zero retains the original
        partial tensor diagnostic; nonzero values require complete finite output.
    harmonics : int, optional
        Non-negative symmetric cutoff n=-N..N [dimensionless], default 15.
        Bool and None are not integer cutoffs.

    Returns
    -------
    K_raw : ndarray of complex, shape (3, 3)
        Original dielectric entries [dimensionless], including the declared
        singular entries at kx=0; no repair or substitution is performed.
    D_raw : ndarray of complex, shape (3, 3)
        Original K plus Maxwell curl terms [dimensionless], same x,y,z axes.
    determinant_raw : complex
        Original six-term det(D_raw) [dimensionless]; may be nonfinite at kx=0.
    omega : float
        Actual angular frequency [rad/s].
    nx : complex
        Perpendicular refractive index [dimensionless].
    nz : complex
        Signed parallel refractive index [dimensionless].
    vts : ndarray, shape (S,)
        Thermal speeds sqrt(2*kB*Ts0/ms) [m/s].
    wcs : ndarray, shape (S,)
        Signed cyclotron angular frequencies [rad/s].
    wps2 : ndarray, shape (S,)
        Squared plasma angular frequencies [s^-2].
    a : ndarray of complex, shape (S,)
        Original signed/complex kx*rhocs [dimensionless].
    b : ndarray of complex, shape (S,)
        a squared, not abs(a) squared [dimensionless].
    rhocs : ndarray, shape (S,)
        Signed sqrt(kB*Ts0/ms)/wcs [m].
    z0s : ndarray of complex, shape (S,)
        Signed omega/(kz*vts), retaining the input kz sign [dimensionless].
    diagnostics : Result
        Actual harmonics, tensor_convention, finite_K/finite_D boolean (3,3)
        masks, finite_determinant, complete and message [dimensionless].
        complete only means all three raw outputs are representable; it does
        not certify scientific accuracy, harmonic convergence or a physical root.

    Raises
    ------
    TypeError
        If harmonics has the wrong kind, including bool; unsupported numeric
        conversion objects may also raise TypeError.
    ValueError
        For invalid physical input, inconsistent species axes, negative cutoff,
        or zero B0, omega or kz. Scalar/singleton species values broadcast to S.
    FloatingPointError
        For unrepresentable derived scales, exhausted or unreliable tails,
        or any lost required finite component. Only the original kx=0 singular
        entries and resulting raw determinant are exempt from full finiteness.

    See Also
    --------
    evaluate_dielectric_response : Complete response under three explicit methods.
    evaluate_plasma_dispersion : Maxwellian Z model family.

    Notes
    -----
    The original fixed Z64, signed scales, compensated component sums and
    six-term determinant are preserved. Species scalars and singletons may
    broadcast; finite methods in the complete-response entry do not broadcast.
    At kx=0 the K_raw and D_raw finite masks are exactly
    [[False,True,False],[True,False,True],[False,True,True]]. In particular zz
    remains a meaningful finite component; complete is False. Failure of an
    expected finite component still raises instead of expanding this exception.

    Complex-b tails use the original Bessel bound and term budget. Finite-grid
    high-precision comparisons at 2e-12 do not establish continuous-domain,
    determinant/root accuracy or a convergence guarantee for the default N15.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_dielectric_diagnostics
    >>> r = evaluate_dielectric_diagnostics(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19], Ts0=[11604941.036704937], omega=1e11, kz=1.0, kx=1e4)
    >>> assert r.K_raw.shape == r.D_raw.shape == (3, 3) and r.diagnostics.complete
    """
    if harmonics is None:
        raise TypeError(
            "harmonics must be a non-negative integer; received None; legal values: integers >= 0 "
            "(default 15); see scirel.kinetic.dielectric-diagnostics"
        )
    count = _harmonics(harmonics, default=15, asset="scirel.kinetic.dielectric-diagnostics")
    from ._dielectric_diagnostic import _evaluate

    raw = _evaluate(B0=B0, qs=qs, ms=ms, ns0=ns0, Ts0=Ts0, omega=omega, kz=kz, kx=kx, lmx=count)
    finite_k, finite_d = np.isfinite(raw["K"]), np.isfinite(raw["D"])
    finite_det = bool(np.isfinite(raw["det_D"]))
    complete = bool(finite_k.all() and finite_d.all() and finite_det)
    return Result(
        K_raw=raw["K"],
        D_raw=raw["D"],
        determinant_raw=raw["det_D"],
        omega=raw["w"],
        nx=raw["nx"],
        nz=raw["nz"],
        vts=raw["vts"],
        wcs=raw["wcs"],
        wps2=raw["wps2"],
        a=raw["as"],
        b=raw["bs"],
        rhocs=raw["rhocs"],
        z0s=raw["z0s"],
        diagnostics=Result(
            harmonics=raw["lmx"],
            tensor_convention=_CONVENTION,
            finite_K=finite_k,
            finite_D=finite_d,
            finite_determinant=finite_det,
            complete=complete,
            message=(
                "Complete finite raw response; accuracy and convergence are separate."
                if complete
                else "Original kx=0 partial response; inspect finite masks."
            ),
        ),
    )
