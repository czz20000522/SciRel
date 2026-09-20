"""Species absorption fraction closure for a four-species power ledger.

Two relations in the observed RF source compute the same closure from the same
four-entry species power ledger: the E-star-dot-J route and the Wdot route.
They differ only in the name of the entry point and the wording of the
docstring; the arithmetic, the validation, the failure boundary, and the
returned keys are identical.  SciRel therefore carries **one** scientific
identity here, with both source routes recorded as provenance rather than as
two competing implementations.

The source leaves the percentage temporaries undefined when the derived total is
zero.  This relation fails closed at that boundary instead of emitting a
non-finite or silently-zero split, and reports the non-zero branch explicitly.
"""
from __future__ import annotations

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
    """Compute source-ordered species absorption percentages from a power ledger.

    Returns the derived total, the per-species percentage split in caller order,
    the sum of those percentages, the residual against 100 percent, and the
    branch label.  A zero derived total is rejected: the source defines no
    percentage result there, so no split is invented.
    """
    values = _finite_species_power_vector(species_power_values)
    total_power = float(np.sum(values, dtype=float))
    if not np.isfinite(total_power):
        raise ValueError("derived total_power must be finite")
    if total_power == 0.0:
        raise ValueError("zero total_power has no source-defined percentage result")
    fractions = values / total_power * 100.0
    total_fraction = float(np.sum(fractions, dtype=float))
    return {
        "total_power": total_power,
        "species_fraction_percent": fractions,
        "total_fraction_percent": total_fraction,
        "fraction_sum_residual_percent": total_fraction - 100.0,
        "branch": "nonzero_total",
    }
