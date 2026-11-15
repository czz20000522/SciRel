"""Incoming neutral boundary-flux normalization over the positive-vx half.

One leaf recovered from the saved the neutral-transport formulation ``入射中性边界通量归一化`` package, integrated as
:func:`normalize_incoming_neutral_boundary`:

scale a caller-owned H or H2 boundary shape distribution on the positive
axial-velocity half space to a requested incoming neutral particle flux,
returning the scaled incoming boundary distribution, the applied scalar
scale, and the pre-scale incoming flux integral
``Vth * sum(volume * shape * vx)`` over ``vx > 0``.

The positive-half normalization relation is retained. SciRel enforces real,
finite, nonnegative inputs and a relative budget on the flux actually carried
by the returned cells, using bounded arithmetic or exact binary-rational
integration. The nonpositive half of the returned distribution is exactly
zero. The continuous scale is ``abs(target_flux) / initial_flux``. Its reported
float must satisfy the same relative budget as the initial and returned flux.
Rounding it before scaling a shape may lose flux, so difficult cases round
each ideally normalized density only once. A negative
requested flux gives the same positive normalization; a zero target produces
a zero scale and zero boundary.

Evidence ceiling: maintained tests establish the normalization and the
fail-closed contracts. Finite valid-path comparison with the saved
implementation is bounded historical development evidence, not qualified-L1
provenance; the saved bundle's strict D1 qualification has been withdrawn.
"""

from __future__ import annotations

from fractions import Fraction
import math

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


_FLUX_RTOL = Fraction(64, 2**52)


def _exact_flux(shape, axial, volume, speed):
    """Integrate the original or returned binary64 cells without range loss."""
    positive = axial > 0.0
    return Fraction(speed) * sum(
        (
            Fraction(float(volume[i, j])) * Fraction(float(shape[i, j])) * Fraction(float(axial[j]))
            for j in np.flatnonzero(positive)
            for i in range(shape.shape[0])
            if volume[i, j] != 0.0 and shape[i, j] != 0.0
        ),
        Fraction(0),
    )


def _bounded_flux(shape, axial, volume, speed):
    """Return a fast integral and rigorous interval, or request exact arithmetic.

    Nonzero factors in [2^-128, 2^128] give normal products >=2^-384.
    At most np.intp-sized arrays keep even the largest positive sum and final
    speed product finite. Explicit paired addition has depth ceil(log2(N));
    two cell products and the final speed product add three rounding factors.
    No bound depends on a possibly underflowing reintegration or on sampling.
    """
    positive = axial > 0.0
    density, weight, velocity = shape[:, positive], volume[:, positive], axial[positive]
    for value in (density, weight, velocity, speed):
        if not np.all((value == 0.0) | ((value >= 2.0**-128) & (value <= 2.0**128))):
            return None
    terms = (weight * density * velocity[None, :]).reshape(-1)
    depth = 0
    while terms.size > 1:
        paired = terms[::2].copy()
        paired[: terms.size // 2] += terms[1::2]
        terms = paired
        depth += 1
    value = speed * float(terms[0]) if terms.size else 0.0
    gamma = Fraction(depth + 3, 2**53 - depth - 3)
    rounded = Fraction(value)
    return value, (rounded / (1 + gamma), rounded / (1 - gamma))


def _matches_target(boundary, axial, volume, speed, target):
    """Certify the actual returned cells against the relative flux budget."""
    bounded = _bounded_flux(boundary, axial, volume, speed)
    if bounded is not None:
        _, (low, high) = bounded
        if max(abs(low - target), abs(high - target)) <= _FLUX_RTOL * target:
            return True
    return abs(_exact_flux(boundary, axial, volume, speed) - target) <= _FLUX_RTOL * target


def _represents_interval(value, low, high):
    """Certify a public scalar against every exact value in its interval."""
    if not math.isfinite(value) or value <= 0.0 or low <= 0:
        return False
    represented = Fraction(value)
    return max(abs(represented / low - 1), abs(represented / high - 1)) <= _FLUX_RTOL


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
        Constraints: Finite; zero on the nonpositive-vx half. The positive-half flux of the actual returned cells matches abs(target_flux_m2_s) within 64*eps relative error and zero absolute error, where eps=2^-52. Tiny individual cells may round to zero.
    scale : float scalar, shape scalar
        The continuous normalization factor represented as a float64 scalar. [dimensionless].
        Constraints: Finite and nonnegative; positive for a nonzero target and zero for a zero target. Relative error against abs(target)/the exact original flux is at most 64*eps, with zero absolute error. Multiplying boundary_shape by this rounded scalar need not reproduce the returned cells bitwise.
    incoming_flux : float scalar, shape scalar
        The pre-scale positive-half flux integral. [m^-2 s^-1].
        Constraints: Finite and positive; relative error against the exact original positive-half flux is at most 64*eps, with zero absolute error.

    Raises
    ------
    ValueError
        Raises ValueError for boolean, string, complex or nonscalar values outside the declared shapes, non-finite or negative shape/volume, non-finite vx or scalars, nonpositive thermal speed, no positive vx node, or nonpositive positive-half flux. Raises ValueError if the initial flux or scale cannot be represented within 64*eps relative error and zero absolute error, a normalized cell cannot be finite, or the actual returned-cell flux misses that same relative budget against abs(target). No physical fallback or altered shape is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.neutrals.normalize_spatial_source_shape : Related neutral-transport operation.

    Notes
    -----
        Only the positive-vx half enters the integral; the returned distribution is exactly zero on the nonpositive half; the scale is the abs(target)/flux form, so negative and positive targets of equal magnitude yield the same scale and a zero target yields zero scale and boundary
    finite nonnegative (nvr,nvx) shape and volume, finite positive thermal speed, finite target flux, at least one positive vx node, strictly positive positive-half flux; evaluated outputs must be finite
    Successful results certify the actual returned-cell flux, not merely a
    positive scale or surviving cell. Ordinary inputs use a paired positive
    sum with a proven rounding interval; other cases use exact binary-rational
    products and sums, avoiding intermediate over/underflow. The relative
    acceptance budget is 64*eps, eps=2^-52, with no absolute allowance.
    This budget also applies separately to the public initial flux against
    the exact original integral and to scale against the exact continuous
    ratio abs(target)/original_flux. A tiny but nonzero scalar is insufficient
    if its relative representation error is too large, even for a zero target
    when the public initial flux is still required.

    If a tentative floating-scale product cannot satisfy the budget, form the
    original flux and continuous scale exactly, then round each normalized
    cell only once. The reported scale must itself meet the relative budget;
    using it to multiply the shape may nevertheless give different last bits.
    No cell is adjusted to force the integral. The call fails if this
    rounded normalized shape cannot meet the budget or a public scalar or
    cell cannot retain its required finite representation. True zero targets
    and representable tiny distributions remain supported.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.neutrals import normalize_incoming_neutral_boundary
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
    bounded = _bounded_flux(shape, axial, volume, speed)
    exact_initial = None
    if bounded is not None:
        incoming_flux, (initial_low, initial_high) = bounded
    else:
        exact_initial = _exact_flux(shape, axial, volume, speed)
        try:
            incoming_flux = float(exact_initial)
        except OverflowError as exc:
            raise ValueError("incoming flux must be finite") from exc
        initial_low = initial_high = exact_initial
    if incoming_flux <= 0.0:
        raise ValueError("positive-vx boundary shape must have positive flux")
    if not _represents_interval(incoming_flux, initial_low, initial_high):
        if exact_initial is None:
            exact_initial = _exact_flux(shape, axial, volume, speed)
            incoming_flux = float(exact_initial)
        if not _represents_interval(incoming_flux, exact_initial, exact_initial):
            raise ValueError("incoming flux is not representable within the relative budget")
        initial_low = initial_high = exact_initial
    incoming_boundary = np.zeros_like(shape)
    if target == 0.0:
        return incoming_boundary, 0.0, float(incoming_flux)
    exact_target = Fraction(abs(target))
    scale = abs(target) / incoming_flux
    # A tentative vectorized result is used only after its actual flux has
    # been certified. Suppression alone never establishes a successful result.
    with np.errstate(all="ignore"):
        incoming_boundary[:, positive] = shape[:, positive] * scale
    if (
        math.isfinite(scale)
        and scale > 0.0
        and _represents_interval(scale, exact_target / initial_high, exact_target / initial_low)
        and np.all(np.isfinite(incoming_boundary))
        and _matches_target(incoming_boundary, axial, volume, speed, exact_target)
    ):
        return incoming_boundary, float(scale), float(incoming_flux)

    # Round the continuous normalization only at each public output. Rounding
    # a subnormal scale before multiplying the shape can destroy half the flux.
    if exact_initial is None:
        exact_initial = _exact_flux(shape, axial, volume, speed)
    exact_scale = exact_target / exact_initial
    try:
        scale = float(exact_scale)
    except OverflowError as exc:
        raise ValueError(
            "boundary scale must be finite and positive for nonzero target flux"
        ) from exc
    if not math.isfinite(scale) or scale == 0.0:
        raise ValueError("boundary scale must be finite and positive for nonzero target flux")
    if not _represents_interval(scale, exact_scale, exact_scale):
        raise ValueError("boundary scale is not representable within the relative budget")
    for j in np.flatnonzero(positive):
        for i in range(shape.shape[0]):
            try:
                incoming_boundary[i, j] = float(Fraction(float(shape[i, j])) * exact_scale)
            except OverflowError as exc:
                raise ValueError("incoming boundary must be finite") from exc
    if not np.all(np.isfinite(incoming_boundary)):
        raise ValueError("incoming boundary must be finite")
    if not np.any((incoming_boundary[:, positive] > 0.0) & (volume[:, positive] > 0.0)):
        raise ValueError("every flux-carrying incoming boundary cell underflows to zero")
    if not _matches_target(incoming_boundary, axial, volume, speed, exact_target):
        raise ValueError("normalized flux is not representable within the relative budget")
    incoming_flux = float(exact_initial)
    return incoming_boundary, float(scale), float(incoming_flux)
