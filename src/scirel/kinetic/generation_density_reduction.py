"""Neutral generation-distribution density reduction.

One leaf recovered from the saved KN1DPy ``中性分布密度归约`` package (source
anchors ``KN1DPy/kinetic_h.py:1410-1424`` and ``kinetic_h2.py:1548-1573``, as
recorded by the saved bundle's own provenance), integrated as
:func:`reduce_generation_density`:

the per-spatial-cell density of one neutral generation, reducing a
``(nvr, nvx, nx)`` distribution over the velocity axes with the cylindrical
quadrature: ``sum over (vr, vx) of weight * f * dvx`` per spatial cell.

The saved numerical paths and operation order are retained for valid finite
real arrays.  SciRel rejects non-real inputs before float coercion and rejects
non-finite outputs after reduction; the saved implementation did neither.
The two weight forms reproduce the saved split: a one-dimensional radial
weight uses the ``moveaxis`` projection path; a full two-dimensional weight
uses the direct ``sum over (0, 1)`` path.

Evidence ceiling: maintained tests establish the reduction against independent
recomputation and the alignment contracts. Integration replay found exact
agreement with the saved implementation on one finite case per weight path.
The saved bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "reduce_generation_density",
]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            not isinstance(value, np.ndarray)
            and any(isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat)
        ):
            raise ValueError
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric array") from error


def reduce_generation_density(distribution, cylindrical_weight, dvx):
    """Reduce one generation distribution to per-cell densities.

    Parameters
    ----------
    distribution
        The generation distribution as a finite ``(nvr, nvx, nx)`` array.
    cylindrical_weight
        The cylindrical quadrature weight: either a finite nonnegative
        ``(nvr,)`` radial profile or a finite nonnegative ``(nvr, nvx)``
        full cylindrical weight, aligned to the distribution's leading axes.
    dvx
        The axial cell sizes: a finite nonnegative ``(nvx,)`` array.

    Returns
    -------
    numpy.ndarray
        The per-spatial-cell densities, shape ``(nx,)``.

    Raises
    ------
    ValueError
        If the fields are not finite and aligned or the weights are negative.
    """
    f = _real_array(distribution, "distribution")
    w = _real_array(cylindrical_weight, "cylindrical_weight")
    dx = _real_array(dvx, "dvx")
    if (
        f.ndim != 3
        or w.ndim not in (1, 2)
        or dx.shape != (f.shape[1],)
        or not all(np.all(np.isfinite(x)) for x in (f, w, dx))
        or np.any(w < 0)
        or np.any(dx < 0)
    ):
        raise ValueError("distribution and quadrature must be finite and aligned")
    if w.ndim == 1:
        if w.shape != (f.shape[0],):
            raise ValueError("radial quadrature must align with distribution")
        result = np.sum(w[:, None] * (np.moveaxis(f, 2, 1) @ dx), axis=0)
    else:
        if w.shape != f.shape[:2]:
            raise ValueError("cylindrical weight must align with distribution")
        if np.all(w == w[:, :1]):
            result = np.sum(w[:, :1] * (np.moveaxis(f, 2, 1) @ dx), axis=0)
        else:
            result = np.sum(f * w[:, :, None] * dx[None, :, None], axis=(0, 1))
    # Declared r60 pre-review tightening: the saved arm does not gate the sum;
    # extreme-but-valid inputs can overflow to non-finite densities.  This
    # asset fail-closes on a non-finite result, per the exact document.
    if not np.all(np.isfinite(result)):
        raise ValueError("the reduced densities are not finite for the supplied inputs")
    return result
