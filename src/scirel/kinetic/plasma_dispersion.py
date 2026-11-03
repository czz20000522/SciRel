"""Validated vector evaluation of the dimensionless plasma dispersion function."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_plasma_dispersion"]


def _complex_input(value):
    """Validate and promote a scalar or array of finite numeric arguments."""
    try:
        objects = np.asarray(value, dtype=object)
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise ValueError("z must contain finite numeric values") from error
    if (
        objects.size == 0
        or any(isinstance(item, (bool, np.bool_)) for item in objects.flat)
        or raw.dtype.kind not in "iufc"
    ):
        raise ValueError("z must contain finite numeric values")
    result = np.asarray(value, dtype=np.complex128)
    if not np.all(np.isfinite(result)):
        raise ValueError("z must contain finite numeric values")
    return result


def evaluate_plasma_dispersion(z):
    """Return Faddeeva ``w(z)`` and ``Z(z)=i*sqrt(pi)*w(z)``.

    Parameters
    ----------
    z : real or complex numeric array-like, shape scalar or any nonempty array shape
        Already normalized complex phase argument; evaluated elementwise. All
        elements finite after complex128 conversion; booleans, strings and empty
        arrays are rejected.

    Returns
    -------
    w : complex128, shape same as z; scalar input yields a zero-dimensional array
        Analytic Faddeeva value w(z). Finite and representable for accepted
        input.
    Z : complex128, shape same as z; scalar input yields a zero-dimensional array
        Plasma dispersion value i sqrt(pi) w(z). Finite and representable for
        accepted input.

    Raises
    ------
    ValueError
        Raises ValueError for empty, boolean, string, nonnumeric or nonfinite
        input, or values that become nonfinite on complex128 conversion. Raises
        ValueError when w or Z is not finite and representable; other unexpected
        SciPy execution errors propagate.

    See Also
    --------
    evaluate_generalized_dispersion : Transform of non-Maxwellian densities.
    solve_maxwellian_electrostatic_mode : Langmuir/Landau root from this function.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_plasma_dispersion
    >>> result = evaluate_plasma_dispersion(0j)
    >>> assert result['w'] == 1
    >>> assert np.isclose(result['Z'], 1j * np.sqrt(np.pi))
    """
    values = _complex_input(z)
    # SciPy is loaded only after validation so namespace discovery and rejected
    # calls remain independent of the optional numerical backend import path.
    from scipy.special import wofz

    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        w_value = np.asarray(wofz(values), dtype=np.complex128)
        dispersion = np.asarray(1j * np.sqrt(np.pi) * w_value, dtype=np.complex128)
    if not np.all(np.isfinite(w_value)) or not np.all(np.isfinite(dispersion)):
        raise ValueError("plasma dispersion value is not representable")
    return {"w": w_value, "Z": dispersion}
