"""FIDASIM single-cell neutral population density merge.

Source: the density half of ``merge_neutral_populations`` (the saved
package ``中性库种群合并``; source anchor ``src/fidasim.f90:10484-10498``,
``pop1%dens = pop1%dens + pop2%dens`` at :10493) for one explicit grid
cell: the six-level target density owns the written result, the source
density is observed componentwise and never modified, and the merge
performs no truncation, normalization or implicit global state.  The
relation is level-resolved addition only -- signed finite source
components are added without clipping (a loss-only matrix can produce
net population loss, and the caller owns the physical interpretation).

Registered hardening against the saved arm: density inputs must not
carry boolean entries (the saved arm's ``np.asarray(value, dtype=float)``
silently coerces ``True`` to 1.0).  The grid-level counterpart over
``(6, nx, ny, nz)`` states is the integrated
``scirel.fusion.neutral-population-grid-merge``; the reservoir-sampling
half of the source relation is
``scirel.fusion.neutral-reservoir-merge``, and the source-ordered
composition of both halves is the task graph
``scirel.fusion.neutral-population-state-merge``.
"""
from __future__ import annotations

import numpy as np

__all__ = ["merge_neutral_population_density"]

_N_LEVELS = 6


def _density_vector(value, *, name: str) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.dtype == np.bool_ or (
        array.dtype == np.object_ and any(isinstance(item, (bool, np.bool_)) for item in array)
    ):
        raise ValueError(f"{name} must not contain boolean entries (registered hardening)")
    try:
        array = array.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.shape != (_N_LEVELS,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite six-level vector")
    return array.astype(float, copy=True)


def merge_neutral_population_density(*, target_population_density, source_population_density):
    """Replay ``pop1%dens = pop1%dens + pop2%dens`` with source ownership explicit."""
    target_before = _density_vector(target_population_density, name="target_population_density")
    source = _density_vector(source_population_density, name="source_population_density")
    target_after = target_before + source
    return {
        "target_population_density_before": target_before,
        "source_population_density_before": source.copy(),
        "target_population_density_after": target_after,
        "source_population_density_after": source.copy(),
        "density_contribution": source.copy(),
        "density_contribution_sum": float(source.sum()),
    }
