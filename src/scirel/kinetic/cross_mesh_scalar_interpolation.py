"""One-dimensional scalar handoff between the neutral-transport formulation species spatial meshes.

In-range target nodes use the saved linear interpolation; nodes outside the
source mesh remain exactly zero. The saved bundle is historical development
evidence, not a qualified D1 source or an approved scientific asset.
"""

from __future__ import annotations

import numpy as np

__all__ = ["interpolate_scalar_across_mesh"]


def _real_1d(value, name):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        array = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real one-dimensional array") from exc
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite real one-dimensional array")
    return array


def interpolate_scalar_across_mesh(fa, xa, xb, do_warn=0):
    """Interpolate a one-dimensional scalar profile onto another spatial mesh.

    Parameters
    ----------
    fa : array_like, shape (nxa,)
        Finite real nonempty profile on ``xa``; boolean, string and complex
        coercions are rejected. [caller units]
    xa : array_like, shape (nxa,)
        Finite strictly increasing source spatial nodes with at least two values,
        aligned with ``fa``. [m]
    xb : array_like, shape (nxb,)
        Finite real nonempty destination spatial nodes. Out-of-range nodes receive
        exact zero. [m]
    do_warn : int, optional
        Default ``0`` disables warnings. A nonzero integer applies the saved
        ``do_warn * max(abs(fb))`` boundary threshold; output values are unchanged.
        Boolean, fractional and string switches are rejected. [dimensionless]

    Returns
    -------
    fb : ndarray, shape (nxb,)
        Finite interpolated profile. In-range nodes use piecewise linear
        interpolation and out-of-range nodes are exactly zero. [caller units]

    Raises
    ------
    ValueError
        If an array is not finite, real, nonempty and one-dimensional; ``xa`` is
        not strictly increasing or has fewer than two nodes; lengths disagree; no
        ``xb`` node is in range; in-range nodes are not contiguous; ``do_warn`` is
        invalid; or the result is non-finite.

    See Also
    --------
    interp_distribution_across_mesh : Conservative cylindrical distribution remap.

    Notes
    -----
    The saved transfer uses linear interpolation in the contiguous block of
    ``xb`` nodes inside ``[min(xa), max(xa)]``. Nodes outside that interval are
    zero-filled. The warning threshold is diagnostic only and never changes the
    returned values. The relation is a finite-mesh handoff, not a physical model
    of either neutral species.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import interpolate_scalar_across_mesh
    >>> xa = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    >>> fa = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    >>> xb = np.array([0.0, 0.25, 0.8, 1.1, 1.6, 2.0])
    >>> fb = interpolate_scalar_across_mesh(fa, xa, xb)
    >>> np.testing.assert_allclose(fb, 1.0 + 2.0 * xb, rtol=0.0, atol=4e-16)
    >>> fb2 = interpolate_scalar_across_mesh(fa, xa, np.array([-1.0, 0.5, 5.0]))
    >>> assert fb2[0] == 0.0 and fb2[2] == 0.0 and fb2[1] == 2.0
    >>> try:
    ...     interpolate_scalar_across_mesh(fa, xa, np.array([5.0, 6.0]))
    ... except ValueError as error:
    ...     assert 'within range' in str(error)
    ... else:
    ...     raise AssertionError('a fully out-of-range mesh_b must be rejected')

    """
    fa = _real_1d(fa, "fa")
    xa = _real_1d(xa, "xa")
    xb = _real_1d(xb, "xb")
    if isinstance(do_warn, (bool, np.bool_)) or not isinstance(do_warn, (int, np.integer)):
        raise ValueError("do_warn must be an integer scalar")
    if xa.size < 2 or np.any(np.diff(xa) <= 0.0):
        raise ValueError("xa must contain at least two strictly increasing nodes")
    if fa.size != xa.size:
        raise ValueError("Number of elements in fa and Xa do not agree!")

    okk = np.where((xb <= np.max(xa)) & (xb >= np.min(xa)))[0]
    if okk.size == 0:
        raise ValueError("No values of Xb are within range of Xa")
    k0, k1 = okk[0], okk[-1]
    # The saved positional slice raises a raw broadcast error for holes.
    if k1 - k0 + 1 != okk.size:
        raise ValueError("in-range mesh_b nodes must form one contiguous block")

    fb = np.zeros(xb.size)
    # Keep the declared optional numerical backend observable on a valid
    # call.  The interpolation itself is assembled locally below so the
    # transfer has no callable-object state.
    import scipy.interpolate  # noqa: F401

    # ``searchsorted`` gives the two source cells in one vectorized pass;
    # unlike a callable interpolator this keeps the transfer self-contained
    # and makes the zero-filled exterior explicit.
    right = np.searchsorted(xa, xb[okk], side="right").clip(1, xa.size - 1)
    left = right - 1
    fraction = (xb[okk] - xa[left]) / (xa[right] - xa[left])
    fb[k0 : k1 + 1] = fa[left] + fraction * (fa[right] - fa[left])
    if do_warn != 0:
        from warnings import warn

        big = max(abs(fb))
        if k0 > 0 and abs(fb[k0]) > do_warn * big:
            warn("Non-zero value of fb detected at min(Xa) boundary")
        if k1 < xb.size - 1 and abs(fb[k1]) > do_warn * big:
            warn("Non-zero value of fb detected at max(Xa) boundary")
    if not np.all(np.isfinite(fb)):
        raise ValueError("fb must be finite")
    return fb
