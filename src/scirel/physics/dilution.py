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
        or any(
            isinstance(item, (bool, np.bool_))
            for item in np.asarray(value, dtype=object).flat
        )
        or np.any(~np.isfinite(raw))
    ):
        raise ValueError(f"{name} must be a finite real numeric value")
    return np.asarray(raw, dtype=np.float64)


def calculate_main_ion_dilution_factor(Z_i, Z_impurity, Z_eff):
    """Return the main-ion dilution fraction ``n_i / n_e``.

    ``Z_i`` follows the source signature and must be scalar-shaped.  The
    impurity charge and effective charge are broadcast to a common shape.
    Charges are dimensionless.  A ``ValueError`` denotes a non-real,
    non-finite, non-positive, singular, or physically out-of-range input;
    ``FloatingPointError`` denotes an unrepresentable finite result.
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
