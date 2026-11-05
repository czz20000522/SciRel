"""Two independent dimensionless momentum definitions.

``thermal_electron_momentum`` returns sqrt(2 T / rest_energy), a speed ratio;
``normalized_momentum`` returns x * vnorm / clight with velocities in a common
unit. Feeding the ratio directly as vnorm divides by c twice. No composition,
constant selection, unit conversion, or collision-model validity is implied.

V6 preserves ordinary binary64 evaluation order. When an intermediate overflows
or becomes subnormal, a Decimal evaluation from the exact input floats avoids
losing a representable final answer. Only final overflow is rejected; binary64
rounding can produce a signed zero for genuinely tiny final grid values. Earlier
V5 confused intermediate overflow with final non-representability and could also
silently lose values through intermediate underflow. Its original bytes and
seven independently reproduced counterexamples remain in the correction receipt.
"""

from __future__ import annotations

from decimal import Decimal, localcontext

import numpy as np

__all__ = [
    "normalized_momentum",
    "thermal_electron_momentum",
]

# The retained route's four other mappings, named so the hold-out can be asserted
# rather than assumed.
HELD_OUT_MAPPINGS = (
    "enabled_argument_scale",
    "enabled_gamefac",
    "hesslow_electron_electron",
    "hesslow_electron_ion",
)

# Raised when finite inputs produce a result double precision cannot represent.
# Not a magnitude threshold on the inputs: see the module docstring.
NON_REPRESENTABLE_MESSAGE = "the normalized momentum is not representable for these finite inputs"


def _require_representable(value, quantity):
    """Fail closed when finite inputs have produced a non-finite result."""
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{NON_REPRESENTABLE_MESSAGE}: {quantity} is not finite")


def _scalar(name, value):
    """Return ``value`` as a float, rejecting anything that is not scalar-shaped.

    Only the shape is checked here.  ``float()`` is then applied unchanged, so the
    conversion and the caller-visible numeric contract are the retained route's; a
    0-dimensional array is scalar-shaped and is accepted, while a list, a tuple or a
    one-element array is not and is rejected by parameter name rather than by the
    converter's own message.
    """
    if np.asarray(value).ndim != 0:
        raise ValueError(f"{name} must be a scalar")
    return float(value)


def thermal_electron_momentum(*, temperature_kev, restmkev):
    """Evaluate the thermal-electron normalized momentum.

    Parameters
    ----------
    temperature_kev : real scalar
        Electron temperature. [keV] Shape: ``scalar``. The value must be finite,
        strictly positive and scalar-shaped. No upper bound is imposed beyond
        final binary64 representability.
    restmkev : real scalar
        Electron rest energy in the same energy unit. [keV] Shape: ``scalar``. The
        value must be finite, strictly positive and scalar-shaped. The caller
        supplies the constant; this function does not embed a rest energy.

    Returns
    -------
    p_te : float
        Non-relativistic thermal speed ratio ``sqrt(2*T/mc^2)``.
        [dimensionless] Shape: ``scalar``. The value is a Python float, finite and
        strictly positive. It is a speed in units of ``c``, not a velocity in cm/s.

    Raises
    ------
    ValueError
        If either input is not scalar-shaped, is non-finite or is nonpositive, or
        if the final closed-form value is not representable in binary64; a
        conversion error raised as ``ValueError`` propagates unchanged.
    TypeError
        If an input cannot be converted to ``float``; the converter error
        propagates unchanged.
    OverflowError
        If conversion to ``float`` overflows, such as for an oversized integer;
        the converter error propagates unchanged.

    See Also
    --------
    normalized_momentum : Maps a velocity grid to momentum. This dimensionless
        ratio is not a velocity and must not be passed directly as its ``vnorm``.
    average_cross_section_over_maxwellian : A separate mesh-based average that
        also leaves unit consistency to the caller.

    Notes
    -----
    The definition is ``sqrt(2*temperature_kev/restmkev)``. Both inputs must be
    energies in the same unit; no conversion is performed and no relativistic
    correction is included. Ordinary arithmetic keeps its binary64 order. If the
    ratio overflows, underflows or becomes subnormal, the exact input floats are
    evaluated with 100-digit Decimal and the result is rounded once to binary64. A
    representationally tiny result rounds to a positive subnormal; only a final
    non-finite value is rejected.

    Examples
    --------
    >>> from scirel.collisions import thermal_electron_momentum
    >>> import math
    >>> p = thermal_electron_momentum(temperature_kev=250., restmkev=511.)
    >>> assert p == 0.9891782353111633
    >>> large = thermal_electron_momentum(temperature_kev=1e308, restmkev=511.)
    >>> assert math.isfinite(large) and large > 1e152
    >>> tiny = thermal_electron_momentum(temperature_kev=1e-300, restmkev=1e300)
    >>> assert tiny > 0
    >>> print(p, large, tiny)
    0.9891782353111633 6.256112470898545e+152 1.414213562373095e-300
    """
    temperature_kev = _scalar("temperature_kev", temperature_kev)
    restmkev = _scalar("restmkev", restmkev)
    if not np.isfinite(temperature_kev) or temperature_kev <= 0:
        raise ValueError("temperature_kev must be finite and positive")
    if not np.isfinite(restmkev) or restmkev <= 0:
        raise ValueError("restmkev must be finite and positive")
    quotient = 2.0 * temperature_kev / restmkev
    if not np.isfinite(quotient) or quotient < np.finfo(float).tiny:
        with localcontext() as context:
            context.prec = 100
            exact_ratio = (
                Decimal(2) * Decimal.from_float(temperature_kev) / Decimal.from_float(restmkev)
            )
            result = float(exact_ratio.sqrt())
    else:
        result = float(np.sqrt(quotient))
    _require_representable(result, "the thermal-electron normalized momentum")
    return result


def normalized_momentum(*, x, vnorm, clight):
    """Map a signed dimensionless velocity grid to normalized momentum.

    Parameters
    ----------
    x : real array-like
        Grid on which the map is evaluated. [dimensionless] Shape: ``[n]``. Every
        value must be finite and one-dimensional. Negative entries are accepted;
        the input array is not modified.
    vnorm : real scalar
        Velocity scale multiplying the grid. [cm/s] Shape: ``scalar``. The value
        must be finite, nonnegative and scalar-shaped. It must use the same
        velocity unit as ``clight``.
    clight : real scalar
        Speed of light in the caller's chosen velocity unit. [cm/s] Shape:
        ``scalar``. The value must be finite, strictly positive and scalar-shaped.
        A dimensionless thermal speed ratio is not a valid substitute for a
        velocity.

    Returns
    -------
    p_n : numpy.ndarray
        Signed normalized momentum profile ``x * vnorm / clight``.
        [dimensionless] Shape: ``same as x``. The dtype is float64.

    Raises
    ------
    ValueError
        If ``x`` is not a finite one-dimensional array, if ``vnorm`` or
        ``clight`` is not scalar-shaped or leaves its stated domain, or if the
        final profile is not representable in binary64; a conversion error raised
        as ``ValueError`` propagates unchanged.
    TypeError
        If ``x`` cannot be converted by ``numpy.asarray(x, dtype=float)``, or if
        ``vnorm`` or ``clight`` cannot be converted to ``float``; the converter
        error propagates unchanged.
    OverflowError
        If numeric conversion overflows, such as for an oversized integer; the
        converter error propagates unchanged.

    See Also
    --------
    thermal_electron_momentum : Returns a dimensionless speed ratio rather than a
        velocity, so it must not be passed directly as ``vnorm``.
    average_cross_section_over_maxwellian : A mesh-based Maxwellian average that
        also leaves unit consistency to the caller.

    Notes
    -----
    The map is odd in ``x``: a zero velocity scale gives signed zero and a negative
    grid value gives negative normalized momentum. ``vnorm`` and ``clight`` are
    assumed to share one velocity unit; this function performs no unit check or
    conversion. Ordinary arithmetic keeps the original binary64 operation order.
    When an intermediate or final value is overflowing, underflowing or subnormal,
    the exact input floats are evaluated with 100-digit Decimal and rounded once
    to binary64. A genuinely tiny final result may still round to signed zero,
    while a final non-finite result is rejected.

    Examples
    --------
    >>> from scirel.collisions import normalized_momentum
    >>> import numpy as np
    >>> p = normalized_momentum(x=[-1e308,0.,1e308],vnorm=1e308,clight=1e308)
    >>> assert np.array_equal(p,[-1e308,0.,1e308])
    >>> small = normalized_momentum(x=[1e-300],vnorm=1e-100,clight=1e-200)
    >>> assert small[0] > 0
    >>> print(p,small)
    [-1.e+308  0.e+000  1.e+308] [1.e-200]
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("x must be a finite one-dimensional array")
    vnorm = _scalar("vnorm", vnorm)
    clight = _scalar("clight", clight)
    if not np.isfinite(vnorm) or vnorm < 0 or not np.isfinite(clight) or clight <= 0:
        raise ValueError("vnorm must be nonnegative and clight must be positive")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        product = x * vnorm
        result = product / clight
    risky = (
        ~np.isfinite(product)
        | (np.abs(product) < np.finfo(float).tiny)
        | ~np.isfinite(result)
        | (np.abs(result) < np.finfo(float).tiny)
    )
    if np.any(risky):
        with localcontext() as context:
            context.prec = 100
            velocity = Decimal.from_float(vnorm)
            light = Decimal.from_float(clight)
            for index in np.flatnonzero(risky):
                result[index] = float(Decimal.from_float(float(x[index])) * velocity / light)
    _require_representable(result, "the grid momentum profile")
    return result
