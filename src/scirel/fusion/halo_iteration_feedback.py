"""FIDASIM halo one-round density feedback and marker-budget update.

Source: FIDASIM ``halo`` (``src/fidasim.f90:13293-13420``) -- one round of
the N3 HALO population iteration: the density growth guard
(``cur/previous > 1`` exits before updating previous/merge/seed), the
``merge_neutral_populations`` density update (addition order per
``src/fidasim.f90:10484-10500``), the ``seed_dcx`` fraction, and the next
``n_halo`` marker count ``int(source_budget * seed_dcx)`` with Fortran
truncation toward zero for the nonnegative product.  The seed exit
threshold is ``seed_dcx < 0.01``; equality continues.  All state is
caller-owned explicit density; no reservoir, HDF5, RNG or source runtime.

Registered hardenings against the saved arm: a non-finite density ratio or
seed fraction (finite extremes can overflow the division) fails closed
instead of returning Inf or crashing inside ``int(Inf)``, and a non-finite
merged density fails closed instead of being returned silently.
"""
from __future__ import annotations

import math
from numbers import Integral

import numpy as np

__all__ = ["advance_halo_iteration_feedback"]

_DENSITY_GROWTH_LIMIT = 1.0
_SEED_EXIT_FRACTION = 0.01


def _finite_scalar(value, name: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a real scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if nonnegative and result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _positive_integer(value, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def advance_halo_iteration_feedback(dcx_density_cm3, previous_halo_density_cm3, current_halo_density_cm3, previous_merged_halo_density_cm3, source_halo_marker_budget):
    """Replay one source ``halo`` density-feedback boundary."""
    dcx = _finite_scalar(dcx_density_cm3, "dcx_density_cm3", positive=True)
    previous = _finite_scalar(previous_halo_density_cm3, "previous_halo_density_cm3", positive=True)
    current = _finite_scalar(current_halo_density_cm3, "current_halo_density_cm3", nonnegative=True)
    merged_before = _finite_scalar(
        previous_merged_halo_density_cm3,
        "previous_merged_halo_density_cm3",
        nonnegative=True,
    )
    budget = _positive_integer(source_halo_marker_budget, "source_halo_marker_budget")

    ratio = current / previous
    # Registered hardening: finite extremes can overflow the division; the
    # saved arm returns Inf as the ratio (or crashes inside int(Inf) later).
    if not math.isfinite(ratio):
        raise ValueError(
            "density_ratio overflowed to a non-finite value for finite but "
            "extreme input magnitudes (registered hardening)")
    if ratio > _DENSITY_GROWTH_LIMIT:
        return {
            "density_ratio": ratio,
            "seed_dcx_fraction": None,
            "next_halo_marker_count": None,
            "next_previous_halo_density_cm3": previous,
            "merged_halo_density_after_cm3": None,
            "merge_applied": False,
            "continue_iteration": False,
            "stop_reason": "density_growth_exceeded",
        }

    seed = current / dcx
    # Registered hardening: seed and merge overflow fail closed; the saved
    # arm crashes inside int(Inf) or returns Inf silently.  The marker
    # product budget*seed is computed in double precision (the source's own
    # default-REAL counting arithmetic) and must stay representable: a
    # finite seed times a large budget can still overflow the product.
    if not math.isfinite(seed):
        raise ValueError(
            "seed fraction overflowed to a non-finite value for finite but "
            "extreme input magnitudes (registered hardening)")
    try:
        product = budget * seed
    except OverflowError as exc:
        raise ValueError(
            "marker product budget*seed is not representable in double "
            "precision (registered hardening)") from exc
    if not math.isfinite(product):
        raise ValueError(
            "marker product budget*seed overflowed to a non-finite value "
            "for finite but extreme input magnitudes (registered hardening)")
    next_markers = int(product)
    merged_after = merged_before + current
    if not math.isfinite(merged_after):
        raise ValueError(
            "merged density overflowed to a non-finite value for finite "
            "but extreme input magnitudes (registered hardening)")
    continue_iteration = seed >= _SEED_EXIT_FRACTION
    return {
        "density_ratio": ratio,
        "seed_dcx_fraction": seed,
        "next_halo_marker_count": next_markers,
        "next_previous_halo_density_cm3": current,
        "merged_halo_density_after_cm3": merged_after,
        "merge_applied": True,
        "continue_iteration": continue_iteration,
        "stop_reason": "continue" if continue_iteration else "seed_below_threshold",
    }
