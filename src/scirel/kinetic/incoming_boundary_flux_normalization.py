"""Incoming neutral boundary-flux normalization over the positive-vx half.

One leaf recovered from the saved the neutral-transport formulation ``入射中性边界通量归一化`` package, integrated as
:func:`normalize_incoming_neutral_boundary`:

scale a caller-owned H or H2 boundary shape distribution on the positive
axial-velocity half space to a requested incoming neutral particle flux,
returning the scaled incoming boundary distribution, the applied scalar
scale, and the pre-scale incoming flux integral
``Vth * sum(volume * shape * vx)`` over ``vx > 0``.

The saved positive-half arithmetic and operation order are retained for
finite real inputs. SciRel enforces the declared real, finite, nonnegative
quadrature and finite-output contract that the saved implementation did not
fully check. The negative half of the returned
distribution is exactly zero (the source's incoming-boundary semantics), and
the scale is ``abs(target_flux) / incoming_flux`` exactly as saved -- a
negative requested flux produces the same positive scale. A zero target
produces a zero scale and zero boundary.

Evidence ceiling: maintained tests establish the normalization and the
fail-closed contracts. Finite valid-path comparison with the saved
implementation is bounded historical development evidence, not qualified-L1
provenance; the saved bundle's strict D1 qualification has been withdrawn.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "normalize_incoming_neutral_boundary",
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


def _real_scalar(value, name):
    try:
        raw = np.asarray(value)
        if raw.ndim != 0 or raw.dtype.kind not in "iuf":
            raise ValueError
        return float(raw)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric scalar") from error


def _incoming_flux(shape, axial, volume, speed):
    """Contract the positive axial half-space without mutating the shape."""
    positive = axial > 0.0
    return speed * np.sum(volume[:, positive] * shape[:, positive] * axial[None, positive])


def normalize_incoming_neutral_boundary(
    boundary_shape, vx, cylindrical_volume, thermal_speed_m_s, target_flux_m2_s
):
    r"""Scale a caller-owned H or H2 boundary shape distribution on the positive axial-velocity half space to a requested incoming neutral particle flux, returning the scaled boundary distribution, the applied scale, and the pre-scale flux integral.

    Parameters
    ----------
    boundary_shape : real array-like, shape [nvr,nvx]
        The caller's boundary shape. [source-normalized].
        Constraints: Finite nonnegative real numeric values; axial velocity on the second axis. Boolean, string and complex coercions are rejected.
    vx : real array-like, shape [nvx]
        The axial velocity axis. [source-normalized].
        Constraints: Finite real numeric one-dimensional axis; must contain at least one positive node. Boolean, string and complex coercions are rejected.
    cylindrical_volume : real array-like, shape [nvr,nvx]
        The cylindrical quadrature weight. [source-normalized measure].
        Constraints: Finite nonnegative real numeric values, same shape as the boundary shape. Boolean, string and complex coercions are rejected.
    thermal_speed_m_s : real scalar, shape scalar
        The species thermal speed. [m/s].
        Constraints: Finite strictly positive real numeric scalar; booleans, strings, complex values and nonscalars are rejected.
    target_flux_m2_s : real scalar, shape scalar
        The requested incoming particle flux. [m^-2 s^-1].
        Constraints: Finite real numeric scalar of any sign, including zero; booleans, strings, complex values and nonscalars are rejected.

    Returns
    -------
    incoming_boundary : float64 array, shape [nvr,nvx]
        The scaled boundary distribution. [source-normalized].
        Constraints: Finite; zero on the nonpositive-vx half; the scaled shape on the positive half.
    scale : float scalar, shape scalar
        The applied scalar scale. [dimensionless].
        Constraints: Finite and nonnegative; positive for a nonzero target flux and exactly zero for a zero target.
    incoming_flux : float scalar, shape scalar
        The pre-scale positive-half flux integral. [m^-2 s^-1].
        Constraints: Finite and positive.

    Raises
    ------
    ValueError
        Raises ValueError for boolean, string, complex or nonscalar values outside the declared shapes, non-finite or negative shape/volume, non-finite vx or scalars, nonpositive thermal speed, no positive vx node, or nonpositive positive-half flux. Raises ValueError when the evaluated flux, scale or boundary is non-finite, or a nonzero target's scale underflows to zero; no fallback is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.normalize_spatial_source_shape : Related neutral-transport operation.

    Notes
    -----
        Only the positive-vx half enters the integral; the returned distribution is exactly zero on the nonpositive half; the scale is the abs(target)/flux form, so negative and positive targets of equal magnitude yield the same scale and a zero target yields zero scale and boundary
    finite nonnegative (nvr,nvx) shape and volume, finite positive thermal speed, finite target flux, at least one positive vx node, strictly positive positive-half flux; evaluated outputs must be finite

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import normalize_incoming_neutral_boundary
    >>> shape = np.ones((2, 3))
    >>> volume = np.ones((2, 3))
    >>> vx = np.array([-1.0, 0.5, 1.0])
    >>> result, scale, initial = normalize_incoming_neutral_boundary(shape, vx, volume, 2.0, -12.0)
    >>> assert initial == 6.0 and scale == 2.0
    >>> assert np.all(result[:, 0] == 0.0)
    >>> try:
    ...     normalize_incoming_neutral_boundary(shape, np.array([-1.0, -0.5, 0.0]), volume, 2.0, 12.0)
    ... except ValueError as error:
    ...     assert 'positive incoming half' in str(error)
    ... else:
    ...     raise AssertionError('a mesh without a positive-vx node must be rejected')
    """
    shape = _real_array(boundary_shape, "boundary_shape")
    axial = _real_array(vx, "vx")
    volume = _real_array(cylindrical_volume, "cylindrical_volume")
    speed = _real_scalar(thermal_speed_m_s, "thermal_speed_m_s")
    target = _real_scalar(target_flux_m2_s, "target_flux_m2_s")
    if (
        shape.ndim != 2
        or axial.ndim != 1
        or shape.shape[1] != axial.size
        or volume.shape != shape.shape
        or not np.all(np.isfinite(shape))
        or not np.all(np.isfinite(axial))
        or not np.all(np.isfinite(volume))
        or np.any(shape < 0.0)
        or np.any(volume < 0.0)
        or not np.isfinite(speed)
        or speed <= 0.0
        or not np.isfinite(target)
    ):
        raise ValueError("boundary shape, quadrature, thermal speed, or target flux is invalid")
    positive = axial > 0.0
    if not np.any(positive):
        raise ValueError("vx must contain a positive incoming half")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        incoming_flux = _incoming_flux(shape, axial, volume, speed)
    if not np.isfinite(incoming_flux):
        raise ValueError("incoming flux must be finite")
    if incoming_flux <= 0.0:
        raise ValueError("positive-vx boundary shape must have positive flux")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        scale = abs(target) / incoming_flux
    if not np.isfinite(scale) or (target != 0.0 and scale == 0.0):
        raise ValueError("boundary scale must be finite and positive for nonzero target flux")
    incoming_boundary = np.zeros_like(shape)
    with np.errstate(over="ignore", invalid="ignore"):
        incoming_boundary[:, positive] = shape[:, positive] * scale
    if not np.all(np.isfinite(incoming_boundary)):
        raise ValueError("incoming boundary must be finite")
    return incoming_boundary, float(scale), float(incoming_flux)
