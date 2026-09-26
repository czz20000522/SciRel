"""Source-free cross-mesh scalar interpolation (the H<->H2 handoff seam).

One leaf recovered from the saved KN1DPy ``跨网格标量插值`` package (source
anchor ``KN1DPy/interp_scalarx.py``, consumed as the N5 H<->H2 handoff seam
``nHP -> nHPA``, ``THP -> THPA`` at ``KN1DPy/kn1d.py:485-486`` and
``SideWallH -> SideWallHM`` at ``KN1DPy/kn1d.py:521``, as recorded by the
saved bundle's own provenance), integrated as
:func:`interpolate_scalar_across_mesh`:

interpolate a 1-D spatial scalar profile from one species' spatial mesh onto
another's: mesh_b nodes inside the mesh_a range take the scipy linear
interpolation of the profile; out-of-range mesh_b nodes stay exactly zero
(the source contract: interpolations outside the phase space are set to
zero); the optional ``do_warn`` mode reproduces the source's boundary
warnings without changing the output.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (non-empty finite one-dimensional arrays, strictly
increasing ``xa``, fa/xa length agreement, at least one in-range mesh_b node,
finite output) and is reproduced bit for bit, messages included.  The
out-of-range zero fill is the saved physics contract, not a defect.

Evidence ceiling: this module establishes the interpolation against a
manufactured closed-form oracle (linear profiles, exact knot reproduction,
affine invariance), the out-of-range zero fill, and -- in the
environment-gated replay test -- bit-identical agreement with the saved
KN1DPy implementation.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.
"""
from __future__ import annotations

import numpy as np
from scipy import interpolate

__all__ = [
    "interpolate_scalar_across_mesh",
]


def _as_1d(arr, name):
    a = np.asarray(arr, dtype=float)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def interpolate_scalar_across_mesh(fa, xa, xb, do_warn=0):
    """Interpolate a scalar profile between two spatial meshes.

    Parameters
    ----------
    fa
        The scalar profile on the mesh_a spatial grid: a finite nonempty
        one-dimensional array.
    xa
        The mesh_a spatial nodes: finite, strictly increasing, aligned to
        ``fa``.
    xb
        The mesh_b spatial nodes: finite nonempty one-dimensional; nodes
        outside the mesh_a range receive exactly zero.
    do_warn
        ``0`` (default) skips the source boundary warnings; any other value
        enables them (warnings only, output unchanged).

    Returns
    -------
    numpy.ndarray
        The interpolated profile on mesh_b, shape ``xb.shape``, finite.

    Raises
    ------
    ValueError
        If any array contract is violated, ``xa`` is not strictly increasing,
        no mesh_b node falls inside the mesh_a range, or the result is
        non-finite.
    """
    fa = _as_1d(fa, "fa")
    xa = _as_1d(xa, "xa")
    xb = _as_1d(xb, "xb")
    if np.any(np.diff(xa) <= 0.0):
        raise ValueError("xa must be strictly increasing")

    nxa = xa.size
    if fa.size != nxa:
        raise ValueError("Number of elements in fa and Xa do not agree!")

    okk = np.where((xb <= np.max(xa)) & (xb >= np.min(xa)))[0]
    if len(okk) == 0:
        raise ValueError("No values of Xb are within range of Xa")

    k0, k1 = okk[0], okk[-1]
    # Declared r61 fail-closed narrowing: the saved arm assigns the
    # interpolated values positionally into the fb[k0:k1+1] slice; when the
    # in-range selection is non-contiguous the slice length differs from the
    # selection length and the saved arm raises numpy's raw broadcast error.
    # This asset fail-closes first with a named contract error; with a
    # contiguous selection the positional assignment maps every node
    # correctly, so no other behavior changes.
    if k1 - k0 + 1 != okk.size:
        raise ValueError(
            "in-range mesh_b nodes must form one contiguous block: "
            "the saved arm raises a raw broadcast error for this input"
        )
    nxb = xb.size
    fb = np.zeros(nxb)

    fb[k0:k1 + 1] = interpolate.interp1d(xa, fa)(xb[okk])

    if do_warn != 0:
        from warnings import warn
        big = max(abs(fb))
        if k0 > 0 and abs(fb[k0]) > (do_warn * big):
            warn("Non-zero value of fb detected at min(Xa) boundary")
        if k1 < (nxb - 1) and abs(fb[k1]) > (do_warn * big):
            warn("Non-zero value of fb detected at max(Xa) boundary")

    if not np.all(np.isfinite(fb)):
        raise ValueError("fb must be finite")
    return fb
