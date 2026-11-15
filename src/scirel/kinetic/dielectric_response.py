"""Maxwellian dielectric response with explicit numerical-method selection."""

import operator

import numpy as np

from .._result import Result

__all__ = ["evaluate_dielectric_response"]

_ASSET = "scirel.kinetic.dielectric-response"
_METHODS = ("harmonic", "harmonic_weideman", "ronnmark")
_CONVENTION = "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)"


def _harmonics(value, *, default, asset):
    if value is None:
        return default
    legal = f"legal values: a non-negative integer, or None for {default}; see {asset}"
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"harmonics must be an integer, not bool; received {value!r}; {legal}")
    try:
        number = operator.index(value)
    except TypeError:
        raise TypeError(
            f"harmonics must be an integer; received type={type(value).__name__}; {legal}"
        ) from None
    if number < 0:
        raise ValueError(f"harmonics must be non-negative; received {number}; {legal}")
    return number


def evaluate_dielectric_response(
    *, B0, qs, ms, ns0, Ts0, omega, kz, kx, method="harmonic", harmonics=None
):
    """Evaluate a homogeneous magnetized Maxwellian dielectric response.

    Parameters
    ----------
    B0 : real scalar
        Finite nonzero background field [T].
    qs : array_like, shape (S,)
        Finite nonzero species charges [C]. No scalar broadcasting.
    ms : array_like, shape (S,)
        Finite positive species masses [kg].
    ns0 : array_like, shape (S,)
        Finite positive equilibrium number densities [m^-3].
    Ts0 : array_like, shape (S,)
        Finite positive Maxwellian temperatures [K].
    omega : real scalar
        Finite nonzero angular frequency [rad/s]. No frequency-unit inference.
    kz : real scalar
        Parallel phase wavenumber [1/m], with its actual sign. Nonzero for
        harmonic methods; zero is permitted by the fixed J8 model.
    kx : real or complex scalar
        Perpendicular phase wavenumber [1/m]. Harmonic methods require real
        nonzero kx; ronnmark accepts finite complex kx including zero, subject
        to its complete-response representability requirements.
    method : {'harmonic', 'harmonic_weideman', 'ronnmark'}, optional
        Default 'harmonic': finite conventional sum with analytic Maxwellian Z.
        'harmonic_weideman' retains the fixed N64 Z backend for ordinary
        components; both finite sums retain their checked parallel-response
        representations. 'ronnmark' uses the existing fixed J8 pole model.
        No method is selected automatically on failure or at zero kz.
    harmonics : int or None, optional
        Symmetric finite cutoff n=-N..N [dimensionless]. None means N=5 for
        the two harmonic methods. Any non-None value is rejected for ronnmark,
        whose J8 order is fixed. Bool is not a cutoff; N=0 is allowed.

    Returns
    -------
    K : ndarray of complex, shape (3, 3)
        Dielectric tensor [dimensionless], axes x,y,z with z parallel to B0.
    D : ndarray of complex, shape (3, 3)
        K with Maxwell curl terms [dimensionless], on the same axes.
    determinant : complex
        det(D) [dimensionless], evaluated by the selected original algorithm.
    omega : float
        Actual input angular frequency [rad/s], without an Hz round trip.
    nx : real or complex scalar
        Perpendicular refractive index [dimensionless].
    nz : real or complex scalar
        Signed parallel refractive index [dimensionless].
    vts : ndarray, shape (S,)
        Thermal speeds sqrt(2*kB*Ts0/ms) [m/s].
    wcs : ndarray, shape (S,)
        Signed cyclotron angular frequencies [rad/s].
    wps2 : ndarray, shape (S,)
        Squared plasma angular frequencies [s^-2].
    a : ndarray, shape (S,)
        Signed or complex kx*sqrt(kB*Ts0/ms)/wcs [dimensionless].
    b : ndarray, shape (S,)
        a squared, not abs(a) squared [dimensionless].
    diagnostics : Result
        Algorithm records [dimensionless]. All methods contain method and
        tensor_convention. Harmonic methods additionally contain the actual
        harmonics; ronnmark instead contains bzj/czj arrays of shape (8,),
        j_order=8, and branches in species-major then pole order. These are
        explicitly method-specific records, not missing scientific quantities.

    Raises
    ------
    TypeError
        For a wrong method/control kind or an unused numerical control.
        Unsupported numeric conversion objects may also raise TypeError.
    ValueError
        For an unknown method, negative cutoff, invalid physical values,
        unsupported shape, zero scales in the input domain or nonfinite input.
    FloatingPointError
        For unrepresentable required derived scales, exhausted or unreliable
        harmonic tails, genuine response poles or nonfinite complete K/D/det.
        No partial response, alternate method or penalty value is substituted.

    See Also
    --------
    evaluate_dielectric_diagnostics : Raw finite-harmonic diagnostic with broadcasting.
    evaluate_ronnmark_r : R and H=d(bR)/db for the J8 assembly.
    evaluate_plasma_dispersion : Maxwellian Z model family.

    Notes
    -----
    K_ij = delta_ij - sigma_ij/(i*omega*epsilon0). The species vectors share
    one nonempty axis. Constants, branch thresholds, accumulation order and
    each determinant algorithm are preserved from the original four paths.
    Finite N is a caller choice, not a convergence certificate; the default
    N5 has independent finite-sum evidence but is not sufficient everywhere.
    Negative kz reflects mixed z components after the absolute-kz response.

    For the finite methods, mixed/parallel components use direct z*Z when
    all species harmonic arguments satisfy |z|<=1; otherwise the analytic
    A=1+z*Z representation and exact finite-sum endpoints avoid cancellation.
    The omitted positive tail is bounded within the original term budget,
    without changing N. Complete Maxwellian and finite-N zero-kz limits are
    distinct; neither finite method supplies the former by clipping kz.

    The J8 model retains its actual binary64 poles and rounded moments. The
    independent sixteen-point B comparison at 2e-7 is a bounded numerical
    diagnostic for that model, separate from its Maxwellian model error.
    See tests/fixtures/kinetic_tensor/README.md for A/B definitions, original
    reference failures and independent regeneration. No continuous-domain,
    damping or root-accuracy guarantee follows from these finite samples.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_dielectric_response
    >>> p = dict(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19], Ts0=[11604941.036704937], omega=1e11, kz=1.0, kx=1e4)
    >>> for method in ('harmonic', 'harmonic_weideman', 'ronnmark'):
    ...     r = evaluate_dielectric_response(**p, method=method)
    ...     assert r.K.shape == r.D.shape == (3, 3)
    """
    if not isinstance(method, str):
        raise TypeError(
            f"method must be a string; received type={type(method).__name__}; "
            f"legal values: {_METHODS}; see {_ASSET}"
        )
    if method not in _METHODS:
        raise ValueError(
            f"method is unknown; received {method!r}; legal values: {_METHODS}; see {_ASSET}"
        )
    if method == "ronnmark":
        if harmonics is not None:
            raise TypeError(
                f"harmonics is unused for method='ronnmark'; received {harmonics!r}; "
                f"legal value: None (fixed J8), or choose a harmonic method; see {_ASSET}"
            )
        from ._dielectric_ronnmark import _evaluate

        raw = _evaluate(B0=B0, qs=qs, ms=ms, ns0=ns0, Ts0=Ts0, omega=omega, kz=kz, kx=kx)
        records = Result(
            bzj=raw["bzj"], czj=raw["czj"], j_order=raw["j_order"], branches=raw["branches"]
        )
        a = raw["as"]
    else:
        count = _harmonics(harmonics, default=5, asset=_ASSET)
        if method == "harmonic":
            from ._dielectric_harmonic import _evaluate
        else:
            from ._dielectric_weideman import _evaluate
        raw = _evaluate(B0=B0, qs=qs, ms=ms, ns0=ns0, Ts0=Ts0, omega=omega, kz=kz, kx=kx, lmx=count)
        records = Result(harmonics=raw["lmx"])
        a = raw["a"]
    records.update(method=method, tensor_convention=raw["tensor_convention"])
    return Result(
        K=raw["K"],
        D=raw["D"],
        determinant=raw["determinant"],
        omega=raw["omega"],
        nx=raw["nx"],
        nz=raw["nz"],
        vts=raw["vts"],
        wcs=raw["wcs"],
        wps2=raw["wps2"],
        a=a,
        b=raw["b"],
        diagnostics=records,
    )
