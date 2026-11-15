"""Validated Maxwellian plasma dispersion with existing numerical methods."""

from __future__ import annotations

import operator

import numpy as np

from scirel._result import Result
from scirel._validation import finite_complex_array

__all__ = ["evaluate_plasma_dispersion"]

_ASSET = "scirel.kinetic.plasma-dispersion-function"
_METHODS = ("scipy", "rational", "weideman", "jpole")


def _controls(method, order):
    if not isinstance(method, str) or method not in _METHODS:
        raise TypeError(
            f"method must select an existing numerical path; received {method!r}; "
            f"legal values: {_METHODS}; see {_ASSET}"
        )
    if method in ("scipy", "weideman"):
        if order is not None:
            raise TypeError(
                f"order is unused by method={method!r}; received {order!r}; "
                f"legal value: None; see {_ASSET}"
            )
        return None
    if order is None:
        return 32 if method == "rational" else 8
    legal = "positive integers >= 1" if method == "rational" else "8, 12, 16, 24"
    message = (
        f"order must be a supported integer for method={method!r}; received {order!r}; "
        f"legal values: None or {legal}; see {_ASSET}"
    )
    if isinstance(order, (bool, np.bool_)):
        raise TypeError(message)
    try:
        n = operator.index(order)
    except TypeError:
        raise TypeError(message) from None
    if n < 1 or (method == "jpole" and n not in (8, 12, 16, 24)):
        raise TypeError(message)
    return n


def evaluate_plasma_dispersion(z, *, method="scipy", order=None):
    """Return Maxwellian Faddeeva ``w`` and plasma dispersion ``Z`` values.

    Parameters
    ----------
    z : real or complex numeric array-like, shape scalar or any nonempty array shape
        Already normalized complex phase argument [dimensionless], evaluated
        elementwise. All elements must be finite after complex128 conversion;
        masked, boolean, string and nonnumeric inputs are rejected.
    method : {'scipy', 'rational', 'weideman', 'jpole'}, optional
        Existing numerical path [dimensionless]. Default 'scipy' preserves the
        direct scipy.special.wofz calculation. 'rational' uses the tunable
        mathematical w approximation; 'weideman' retains the distinct fixed64
        kernel; 'jpole' uses the tabulated partial fractions.
    order : positive integer or None, optional
        Numerical truncation or pole count [count]. None selects rational32 or
        jpole8. Rational accepts any positive integer; jpole accepts 8, 12, 16,
        24. Scipy and fixed64 accept only None. Booleans are rejected.

    Returns
    -------
    w : complex128, shape same as z; scalar input yields a zero-dimensional array
        Faddeeva value or selected approximation [dimensionless]. For jpole,
        this is Z_J/(i sqrt(pi)), the same finite-order approximation as Z_J,
        not an exact Faddeeva value. Finite and representable on success.
    Z : complex128, shape same as z; scalar input yields a zero-dimensional array
        Maxwellian plasma dispersion value or selected approximation
        [dimensionless], normalized as i sqrt(pi) w. Both w and Z must be finite
        and representable for the entire call to succeed.

    Raises
    ------
    TypeError
        If z is masked, boolean, string or nonnumeric; method is unsupported;
        or order is unusable for the selected method.
    ValueError
        If z is empty, ragged or nonfinite after complex128 conversion.
    FloatingPointError
        If w or final Z is nonfinite; the entire array fails without partial
        output. Unexpected backend execution errors propagate.

    See Also
    --------
    scirel.numerics.evaluate_faddeeva : Tunable mathematical w with its own finite domain.
    evaluate_generalized_dispersion : Transform of non-Maxwellian densities.
    solve_maxwellian_electrostatic_mode : Langmuir/Landau root from this function.

    Notes
    -----
    The caller supplies z using an explicit thermal-speed/drift convention;
    this function does not infer or convert that convention. Lower-half-plane
    continuation, coefficients and numerical arithmetic retain the original
    kernels. Rational and fixed64 belong to one approximation family but keep
    distinct floating evaluations. J-pole uses all four existing pole counts.
    Accuracy is bounded only by each method's sampled evidence; no global
    error certificate, clipping, extrapolation or fallback is provided.
    Independent mathematical w can remain finite where the final Z overflows.
    Result contains exactly w and Z, without method or order metadata.

    References
    ----------
    Weideman (1994), Computation of the Complex Error Function,
    doi:10.1137/0731077.
    Xie (2013), Generalized Plasma Dispersion Function, arXiv:1305.6476.
    SciPy, scipy.special.wofz and scipy.special.erfcx.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_plasma_dispersion
    >>> result = evaluate_plasma_dispersion(0j, method='scipy')
    >>> assert result['w'] == 1
    >>> assert np.isclose(result['Z'], 1j * np.sqrt(np.pi))
    >>> rational = evaluate_plasma_dispersion(0.2+0.7j, method='rational', order=16)
    >>> fixed64 = evaluate_plasma_dispersion(0.2+0.7j, method='weideman')
    >>> jpole = evaluate_plasma_dispersion(0.2+0.7j, method='jpole', order=12)
    >>> assert all(set(r) == {'w', 'Z'} for r in (rational, fixed64, jpole))
    >>> assert all(np.isfinite(r['Z']) for r in (rational, fixed64, jpole))
    """
    n = _controls(method, order)
    values = finite_complex_array(z, "z", asset_id=_ASSET)
    if method == "weideman":
        from ._plasma_dispersion_weideman import _evaluate_weideman

        return _evaluate_weideman(values)
    if method == "jpole":
        from ._plasma_dispersion_variants import _evaluate_jpole

        return _evaluate_jpole(values, n)
    if method == "rational":
        from scirel.numerics import evaluate_faddeeva

        result = {"w": evaluate_faddeeva(values, order=n)}
        # Retain the original FFT final scaling expression and operation order.
        with np.errstate(over="ignore", invalid="ignore"):
            scaled = 1j * np.sqrt(np.pi) * result["w"]
        if not np.all(np.isfinite(scaled)):
            raise FloatingPointError(
                "Z must be finite complex128; received nonfinite rational scaling; "
                f"legal results: finite w and Z; see {_ASSET}"
            )
        return Result(w=result["w"], Z=scaled)
    # Import after validation; namespace discovery and rejected calls stay lazy.
    from scipy.special import wofz

    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        w_value = np.asarray(wofz(values), dtype=np.complex128)
        dispersion = np.asarray(1j * np.sqrt(np.pi) * w_value, dtype=np.complex128)
    if not np.all(np.isfinite(w_value)) or not np.all(np.isfinite(dispersion)):
        raise FloatingPointError(
            "w and Z must be finite complex128; received nonfinite scipy results; "
            f"legal results: finite w and Z; see {_ASSET}"
        )
    return Result({"w": w_value, "Z": dispersion})
