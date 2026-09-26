"""Spatial source-shape normalization with trapezoidal measure.

One leaf recovered from the saved KN1DPy ``空间源形状归一化`` package (source
anchor ``KN1DPy/kn1d.py:520-577``, the spatial source profile normalization
of the source-entry dual-branch graphs, as recorded by the saved bundle's own
provenance), integrated as :func:`normalize_spatial_source_shape`:

normalize a nonnegative one-dimensional spatial source profile to unit
integral under the trapezoidal measure, returning the unit-integral shape in
``m^-1`` and the original spatial integral.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (aligned finite one-dimensional profile and strictly
increasing coordinates with at least two nodes, nonnegative source, finite
strictly positive integral, and the unit-integral re-check on the normalized
shape with the saved ``rtol=1e-12, atol=1e-14`` tolerance) and is reproduced
bit for bit, messages included.  A zero profile is rejected, never silently
replaced -- the strict positivity is the saved precondition for the shape to
rebuild a total source.

Evidence ceiling: this module establishes the normalization against an
independent trapezoidal recomputation, the endpoint preservation, and -- in
the environment-gated replay test -- exact agreement with the saved KN1DPy
implementation.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "normalize_spatial_source_shape",
]


def normalize_spatial_source_shape(source, x_m):
    """Return a unit-integral shape and the original spatial integral.

    Parameters
    ----------
    source
        The source profile as a finite nonnegative one-dimensional array.
    x_m
        The strictly increasing spatial coordinates in ``m``, aligned to
        ``source`` with at least two nodes.

    Returns
    -------
    dict
        ``{'shape_m_inv': ndarray, 'integral_source': float}`` where the
        shape has unit trapezoidal integral and ``integral_source`` is the
        original profile's trapezoidal integral.

    Raises
    ------
    ValueError
        If the alignment, finiteness, monotonicity, or positivity contract
        is violated or the normalized shape fails its unit-integral check.
    """
    profile = np.asarray(source, dtype=float)
    coordinates = np.asarray(x_m, dtype=float)
    if (
        profile.ndim != 1
        or coordinates.ndim != 1
        or profile.size != coordinates.size
        or profile.size < 2
        or not np.all(np.isfinite(profile))
        or not np.all(np.isfinite(coordinates))
        or np.any(profile < 0.0)
        or np.any(np.diff(coordinates) <= 0.0)
    ):
        raise ValueError("source and x_m must be aligned finite one-dimensional profiles")
    integral = float(np.trapezoid(profile, coordinates))
    if not np.isfinite(integral) or integral <= 0.0:
        raise ValueError("source must have a positive spatial integral")
    shape = profile / integral
    normalized_integral = float(np.trapezoid(shape, coordinates))
    if not np.isclose(normalized_integral, 1.0, rtol=1.0e-12, atol=1.0e-14):
        raise ValueError("normalized source shape failed its unit-integral check")
    return {"shape_m_inv": shape, "integral_source": integral}
