"""Spatial source-shape normalization with trapezoidal measure.

One leaf recovered from the saved KN1DPy ``空间源形状归一化`` package (source
anchor ``KN1DPy/kn1d.py:520-577``, the spatial source profile normalization
of the source-entry dual-branch graphs, as recorded by the saved bundle's own
provenance), integrated as :func:`normalize_spatial_source_shape`:

normalize a nonnegative one-dimensional spatial source profile to unit
integral under the trapezoidal measure, returning the unit-integral shape in
``m^-1`` and the original spatial integral.

The saved trapezoidal arithmetic and unit-integral re-check with
``rtol=1e-12, atol=1e-14`` are retained for finite real arrays. SciRel rejects
boolean, string and complex coercions that the saved implementation accepted
or raised inconsistently. A zero profile is rejected, never silently replaced.

Evidence ceiling: maintained tests establish the normalization against an
independent trapezoidal recomputation and the failure contract. Finite
valid-path comparison with the saved implementation is bounded historical
development evidence, not qualified-L1 provenance; the saved bundle's strict
D1 qualification has been withdrawn.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "normalize_spatial_source_shape",
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


def _trapezoid(values, coordinates):
    """Assemble the one-dimensional trapezoid rule locally with NumPy."""
    return np.sum(0.5 * (values[1:] + values[:-1]) * np.diff(coordinates))


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
    profile = _real_array(source, "source")
    coordinates = _real_array(x_m, "x_m")
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
    # For a nonnegative profile on a strictly increasing grid, an all-zero
    # profile has a zero integral by construction.  Reject it before loading
    # the integration backend so this invalid-input path stays dependency-light.
    if not np.any(profile > 0.0):
        raise ValueError("source must have a positive spatial integral")

    # Import on the valid path to preserve the package's optional-backend
    # visibility contract; the local assembler below remains the source of
    # the returned values.
    import scipy.integrate  # noqa: F401
    integral = float(_trapezoid(profile, coordinates))
    if not np.isfinite(integral) or integral <= 0.0:
        raise ValueError("source must have a positive spatial integral")
    shape = profile / integral
    if not np.all(np.isfinite(shape)):
        raise ValueError("normalized source shape must be finite")
    normalized_integral = float(_trapezoid(shape, coordinates))
    if not np.isclose(normalized_integral, 1.0, rtol=1.0e-12, atol=1.0e-14):
        raise ValueError("normalized source shape failed its unit-integral check")
    return {"shape_m_inv": shape, "integral_source": integral}
