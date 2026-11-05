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

from scirel._result import Result

__all__ = ["compute_species_absorption_fraction"]

_SPECIES_COUNT = 4


def _finite_species_power_vector(value: object) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (_SPECIES_COUNT,):
        raise ValueError("species_power_values must be a length-four vector")
    if np.iscomplexobj(raw) or np.issubdtype(raw.dtype, np.bool_) or raw.dtype.kind in {"U", "S"}:
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

    Parameters
    ----------
    species_power_values : real array-like, shape (4,)
        Absorbed-power ledger in the caller's species order in
        ``[source power units]``.  Values must be exactly four finite real
        numbers after conversion to float64.  Complex, boolean, and string
        array dtypes are rejected; numeric object arrays are accepted when
        their values convert to finite real floats.

    Returns
    -------
    total_power : float
        Field of the returned ``scirel._result.Result`` mapping containing
        the sum of the four ledger entries in ``[source power units]``.  The
        value is finite and nonzero for a successful call.
    species_fraction_percent : ndarray of float64, shape (4,)
        Field containing each species percentage in caller order in
        ``[percent]``.  Entries may be negative when the corresponding ledger
        entry is negative.
    total_fraction_percent : float
        Field containing the sum of the actual returned binary64 shares in
        ``[percent]``.  Severe signed cancellation can make this sum differ
        substantially from 100.
    fraction_sum_residual_percent : float
        Field equal to ``total_fraction_percent - 100.0`` in ``[percent]``.
        It is the difference of the reported values, not an independently
        recomputed quantity.
    branch : str
        Field containing the literal ``"nonzero_total"`` in
        ``[dimensionless]``.  The zero-total branch is not returned because a
        zero total is rejected.

    Raises
    ------
    ValueError
        If the input is not a length-four vector, is complex, boolean, or
        string typed, contains non-finite entries, cannot be converted to
        float64, has an exactly zero derived total, or produces a required
        total, percentage, or returned-share sum that is not finite.

    See Also
    --------
    scirel.plasma.fast_ion_fractional_heating
        Related heating-partition relation; it does not consume this ledger or
        convert its dimensionless fraction into these percentages.

    Notes
    -----
    The five fields are returned together as one ``scirel._result.Result``
    mapping.  Mapping access remains available and each field can also be read
    as an attribute.  Signed totals use an exact rational sum before binary64
    rounding; ordinary same-sign ledgers retain their established floating
    reduction.  Caller species order is preserved and negative shares are
    reported without clipping or renormalization.  A zero derived total has no
    defined percentage split and is rejected.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.diagnostics import compute_species_absorption_fraction
    >>> result = compute_species_absorption_fraction([1.0, 2.0, 3.0, 4.0])
    >>> assert isinstance(result, Result)
    >>> np.testing.assert_allclose(result['species_fraction_percent'], [10.0, 20.0, 30.0, 40.0])
    >>> assert result.total_power == result['total_power']
    >>> assert result.branch == 'nonzero_total'
    >>> assert abs(result.fraction_sum_residual_percent) < 1e-12
    >>> try:
    ...     compute_species_absorption_fraction([0.0, 0.0, 0.0, 0.0])
    ... except ValueError:
    ...     pass
    ... else:
    ...     raise AssertionError('a zero-total ledger must be rejected')
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
            total_fraction = float(
                sum((Fraction.from_float(float(v)) for v in fractions), Fraction())
            )
    except (OverflowError, ValueError) as exc:
        raise ValueError("species percentages and their total must be finite") from exc
    if not np.all(np.isfinite(fractions)) or not np.isfinite(total_fraction):
        raise ValueError("species percentages and their total must be finite")
    return Result(
        {
            "total_power": total_power,
            "species_fraction_percent": fractions,
            "total_fraction_percent": total_fraction,
            "fraction_sum_residual_percent": total_fraction - 100.0,
            "branch": "nonzero_total",
        }
    )
