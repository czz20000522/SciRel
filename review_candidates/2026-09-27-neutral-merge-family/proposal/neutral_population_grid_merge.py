"""FIDASIM beam-grid neutral population density merge.

Source: the population-density part of ``merge_neutral_populations``
replayed over an explicit beam-grid state (the saved package
``中性库种群网格合并``; source anchor ``src/fidasim.f90:10484-10498``,
``pop1%dens = pop1%dens + pop2%dens`` at :10493).  Inputs are two
shape ``(6, nx, ny, nz)`` six-level density grids: the target owns the
written result, the source is observed and never modified, and the
per-cell, per-level addition performs no truncation, normalization,
clipping or cross-cell mixing (signed finite source components are
added as-is; the caller owns the physical interpretation).

Registered hardening against the saved arm: density inputs must not
carry boolean entries (the saved arm's ``np.asarray(value,
dtype=float)`` silently coerces ``True`` to 1.0).  The reservoir
half of the source relation and the source-ordered composition of both
halves are the integrated ``scirel.fusion.neutral-reservoir-merge`` and
the task graph ``scirel.fusion.neutral-population-state-merge``.
"""
from __future__ import annotations

import numpy as np

__all__ = ["merge_neutral_population_cells"]

_N_LEVELS = 6


def _density_grid(value, *, name: str) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.dtype == np.bool_ or (
        array.dtype == np.object_ and any(isinstance(item, (bool, np.bool_)) for item in array.flat)
    ):
        raise ValueError(f"{name} must not contain boolean entries (registered hardening)")
    try:
        array = array.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if (
        array.ndim != 4
        or array.shape[0] != _N_LEVELS
        or not np.all(np.isfinite(array))
    ):
        raise ValueError(f"{name} must be finite with shape (6,nx,ny,nz)")
    if any(size < 1 for size in array.shape[1:]):
        raise ValueError(f"{name} must have positive cell dimensions")
    return array.astype(float, copy=True)


def merge_neutral_population_cells(*, target_population_density, source_population_density):
    """Replay ``pop1%dens += pop2%dens`` over an explicit beam-grid state."""
    target_before = _density_grid(target_population_density, name="target_population_density")
    source_before = _density_grid(source_population_density, name="source_population_density")
    if target_before.shape != source_before.shape:
        raise ValueError("target and source density grids must have the same shape")
    target_after = target_before + source_before
    return {
        "target_population_density_before": target_before,
        "source_population_density_before": source_before.copy(),
        "target_population_density_after": target_after,
        "source_population_density_after": source_before.copy(),
        "density_contribution": source_before.copy(),
        "density_contribution_sum": float(source_before.sum()),
        "cell_shape": [int(size) for size in target_before.shape[1:]],
        "cell_count": int(np.prod(target_before.shape[1:])),
    }
