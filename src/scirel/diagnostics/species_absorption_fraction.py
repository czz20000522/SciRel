"""Convert a four-entry RF power ledger into a percentage split.

Signed entries are summed as exact binary64 rationals before percentages are
formed, which keeps a small net total observable instead of losing it to
reduction order.  A zero net power has no defined percentage split and is
rejected explicitly.
"""
from __future__ import annotations

from fractions import Fraction
import sys

import numpy as np

__all__ = ["compute_species_absorption_fraction"]

_SPECIES_COUNT = 4


def _finite_species_power_vector(value: object) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (_SPECIES_COUNT,):
        raise ValueError("species_power_values must be a length-four vector")
    if (
        np.iscomplexobj(raw)
        or np.issubdtype(raw.dtype, np.bool_)
        or raw.dtype.kind in {"U", "S"}
    ):
        raise ValueError("species_power_values must be real-valued and non-boolean")
    try:
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("species_power_values must be numeric") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError("species_power_values must be finite")
    return result


def compute_species_absorption_fraction(species_power_values):
    """Compute ordered species absorption percentages from a power ledger.

    Returns the derived total, the per-species percentage split in caller order,
    the stably summed returned percentages, the residual against 100 percent, and the
    branch label.  A zero derived total is rejected because no percentage split
    is defined. Signed totals are summed
    exactly before binary64 rounding. Cancellation can amplify rounding of
    individual returned shares; their reported sum need not be close to 100.
    Numeric object arrays are accepted when convertible to finite real floats.
    """
    values = _finite_species_power_vector(species_power_values)
    # Four terms only: sum their exact binary64 values before rounding the
    # total for signed ledgers. This preserves small signed contributions and avoids an overflowing
    # partial sum determining a mathematically finite (or zero) total.
    exact_values = [Fraction.from_float(float(value)) for value in values]
    exact_total = sum(exact_values, Fraction())
    if exact_total == 0:
        raise ValueError("zero total_power has no source-defined percentage result")
    try:
        total_power = float(exact_total)
    except OverflowError as exc:
        raise ValueError("derived total_power must be finite") from exc
    with np.errstate(over="ignore", invalid="ignore"):
        legacy_total = float(np.sum(values, dtype=float))
    # A same-sign ledger has no cancellation; retain its established reduction
    # rounding when representable. Signed ledgers use the exact sum above.
    if not (np.any(values > 0) and np.any(values < 0)) and np.isfinite(legacy_total):
        total_power = legacy_total
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        quotients = values / total_power
        fractions = quotients * 100.0
    # Keep the established two-operation rounding on ordinary ledgers. For
    # ill-conditioned cancellation or an intermediate range loss, evaluate
    # the defining rational percentage directly and round only at the end.
    cancellation = sum(abs(v) for v in exact_values) > abs(exact_total) * (1 << 26)
    unsafe_range = np.any((values != 0) & (np.abs(quotients) < sys.float_info.min))
    if cancellation or unsafe_range or not np.all(np.isfinite(fractions)):
        try:
            fractions = np.array([float(100 * v / exact_total) for v in exact_values])
        except OverflowError as exc:
            raise ValueError("species percentages must be finite") from exc
    try:
        # Sum the *returned* binary64 shares, not unrounded exact percentages.
        with np.errstate(over="ignore", invalid="ignore"):
            total_fraction = float(np.sum(fractions, dtype=float))
        if cancellation or not np.isfinite(total_fraction):
            total_fraction = float(sum((Fraction.from_float(float(v)) for v in fractions), Fraction()))
    except (OverflowError, ValueError) as exc:
        raise ValueError("species percentages and their total must be finite") from exc
    if not np.all(np.isfinite(fractions)) or not np.isfinite(total_fraction):
        raise ValueError("species percentages and their total must be finite")
    return {
        "total_power": total_power,
        "species_fraction_percent": fractions,
        "total_fraction_percent": total_fraction,
        "fraction_sum_residual_percent": total_fraction - 100.0,
        "branch": "nonzero_total",
    }
