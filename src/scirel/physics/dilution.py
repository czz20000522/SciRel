"""Main-ion dilution from a one-main/one-impurity charge model.

The relation is
``d = (Z_impurity - Z_eff) / (Z_i * (Z_impurity - Z_i))``.
Inputs are dimensionless charge numbers and the output is the dimensionless
ratio ``n_i / n_e``.  The SciRel boundary makes the source's implicit
one-species physical assumptions explicit: all charges are finite and
positive, the two charge states differ, and ``Z_eff`` lies between them.

The implementation validates the one-main/one-impurity applicability domain
before applying the dimensionless algebra. It is independent of the
quasineutral reference-density closure.
"""

from __future__ import annotations

import numpy as np

__all__ = ["calculate_main_ion_dilution_factor"]


def _real_array(value, name):
    """Return a finite float64 array while rejecting booleans and masks."""
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite real numeric value") from exc
    if (
        raw.dtype.kind not in "iuf"
        or raw.size == 0
        or np.ma.isMaskedArray(value)
        or any(isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat)
        or np.any(~np.isfinite(raw))
    ):
        raise ValueError(f"{name} must be a finite real numeric value")
    return np.asarray(raw, dtype=np.float64)


def calculate_main_ion_dilution_factor(Z_i, Z_impurity, Z_eff):
    """Return the main-ion dilution fraction ``n_i / n_e``.

    Parameters
    ----------
    Z_i : real scalar or 0-D array
        Main-ion charge state [dimensionless]. Must be finite and strictly
        positive.
    Z_impurity : real scalar or array_like
        Impurity charge state [dimensionless], broadcast with ``Z_eff`` and
        strictly positive.
    Z_eff : real scalar or array_like
        Effective charge [dimensionless], broadcast with ``Z_impurity`` and
        required to lie between ``Z_i`` and ``Z_impurity``.

    Returns
    -------
    result : float64 scalar or ndarray
        Main-ion density fraction [dimensionless], with the broadcast shape of
        ``Z_impurity`` and ``Z_eff``.

    Raises
    ------
    ValueError
        If an input is empty, non-real, masked, non-finite, nonpositive,
        non-scalar for ``Z_i``, incompatible for broadcasting, equal to the
        main charge, or outside the declared charge interval.
    FloatingPointError
        If accepted finite inputs produce an unrepresentable result.

    See Also
    --------
    calculate_stored_thermal_energy : Integrate thermal pressure profiles.

    Notes
    -----
    For one main-ion species and one impurity species,

    .. math:: d = (Z_{impurity}-Z_{eff}) / (Z_i (Z_{impurity}-Z_i)).

    The charges are dimensionless. The denominator is evaluated in stages to
    avoid an avoidable overflow. The relation does not infer a multi-ion
    composition or validate a transport model.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.physics import calculate_main_ion_dilution_factor
    >>> r=calculate_main_ion_dilution_factor(1., 6., 2.5)
    >>> assert np.isclose(r, .7)
    """
    zi = _real_array(Z_i, "Z_i")
    if zi.ndim != 0 or zi <= 0:
        raise ValueError("Z_i must be a finite positive scalar charge")
    zimp = _real_array(Z_impurity, "Z_impurity")
    zeff = _real_array(Z_eff, "Z_eff")
    try:
        zimp, zeff = np.broadcast_arrays(zimp, zeff)
    except ValueError as exc:
        raise ValueError("Z_impurity and Z_eff must be broadcast-compatible") from exc
    if np.any(zimp <= 0) or np.any(zeff <= 0):
        raise ValueError("Z_impurity and Z_eff must be strictly positive")
    if np.any(zimp == zi):
        raise ValueError("Z_impurity must differ from Z_i")
    low = np.minimum(zi, zimp)
    high = np.maximum(zi, zimp)
    if np.any((zeff < low) | (zeff > high)):
        raise ValueError("Z_eff must lie between the main and impurity charge states")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        # Divide in stages so a large but representable ratio does not create
        # an unnecessary product overflow in the denominator.
        impurity_fraction = (zimp - zeff) / (zimp - zi)
        result = impurity_fraction / zi
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("main-ion dilution result is not representable")
    return result
