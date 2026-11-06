"""Neutral generation-distribution density reduction.

One leaf recovered from the saved the neutral-transport formulation ``中性分布密度归约`` package, integrated as
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
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric array") from error


def reduce_generation_density(distribution, cylindrical_weight, dvx):
    """Reduce one neutral generation distribution to per-cell densities.

    Parameters
    ----------
    distribution : array_like, shape (nvr, nvx, nx)
        Finite real generation distribution. Boolean, string and complex coercions
        are rejected. [source-discrete]
    cylindrical_weight : array_like, shape (nvr, nvx) or (nvr,)
        Finite nonnegative cylindrical quadrature weight. A one-dimensional input
        is a radial profile; a two-dimensional input must align with the leading
        distribution axes, and uniform columns take the radial projection path.
        [source-discrete measure]
    dvx : array_like, shape (nvx,)
        Finite nonnegative axial cell sizes aligned with the distribution velocity
        axis. [source-discrete measure]

    Returns
    -------
    density : ndarray, shape (nx,)
        Finite reduced density per spatial cell. Signed values are preserved; no
        nonnegativity clamp is applied. [source-discrete density]

    Raises
    ------
    ValueError
        If a field is non-real, non-finite, misaligned or negative where forbidden,
        or if the reduced density is non-finite.

    See Also
    --------
    reduce_axisymmetric_neutral_moments : Full neutral velocity-space moments.
    make_cylindrical_velocity_quadrature : Builds cylindrical velocity measures.

    Notes
    -----
    For each spatial cell the reduction is the sum of
    ``cylindrical_weight * distribution * dvx`` over both velocity axes. A
    one-dimensional radial weight computes the axial contraction first, then
    applies the radial weight. A two-dimensional weight uses the direct two-axis
    sum, except that equal columns are routed through the radial projection so
    the documented operation order is retained. The result follows the source's
    discrete density normalization and is checked for finiteness.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_generation_density
    >>> f = np.ones((2, 2, 2))
    >>> w2 = np.full((2, 2), 0.5)
    >>> dx = np.array([0.5, 1.0])
    >>> result = reduce_generation_density(f, w2, dx)
    >>> np.testing.assert_allclose(result, [1.5, 1.5])
    >>> radial = np.array([0.25, 0.75])
    >>> uniform = np.repeat(radial[:, None], 2, axis=1)
    >>> np.testing.assert_array_equal(reduce_generation_density(f, uniform, dx), reduce_generation_density(f, radial, dx))
    >>> try:
    ...     reduce_generation_density(f, np.ones((2, 2)), np.array([0.5, -1.0]))
    ... except ValueError as error:
    ...     assert 'aligned' in str(error)
    ... else:
    ...     raise AssertionError('a negative dvx must be rejected')

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
        projected = np.moveaxis(f, 2, 1) @ dx
        result = np.sum(w[:, None] * projected, axis=0)
    else:
        if w.shape != f.shape[:2]:
            raise ValueError("cylindrical weight must align with distribution")
        if np.all(w == w[:, :1]):
            projected = np.moveaxis(f, 2, 1) @ dx
            result = np.sum(w[:, :1] * projected, axis=0)
        else:
            result = np.sum(f * w[:, :, None] * dx[None, :, None], axis=(0, 1))
    # Declared r60 pre-review tightening: the saved arm does not gate the sum;
    # extreme-but-valid inputs can overflow to non-finite densities.  This
    # asset fail-closes on a non-finite result, per the exact document.
    if not np.all(np.isfinite(result)):
        raise ValueError("the reduced densities are not finite for the supplied inputs")
    return result
