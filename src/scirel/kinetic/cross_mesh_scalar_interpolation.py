"""One-dimensional scalar handoff between KN1DPy species spatial meshes.

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
            isinstance(item, (bool, np.bool_))
            for item in np.asarray(value, dtype=object).flat
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
    """Interpolate ``fa`` from spatial mesh ``xa`` onto ``xb`` with zero fill.

    The nodes of ``xb`` that fall within ``xa`` must form one contiguous
    index block. Unsorted nodes within that block retain their original order.
    ``do_warn`` is an integer threshold switch for the saved boundary warnings.
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

    # Keep the dependency at the numerical backend boundary.  All public
    # input rejection above is intentionally completed before importing
    # SciPy, so malformed calls preserve their failure order and remain
    # dependency-light in a fresh interpreter.
    from scipy import interpolate

    fb = np.zeros(xb.size)
    fb[k0:k1 + 1] = interpolate.interp1d(xa, fa)(xb[okk])
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
