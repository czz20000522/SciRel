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
    """Return the thermal-electron normalized momentum ``p_Te = sqrt(2T/mc^2)``.

    A definition, not a fit. Ordinary arithmetic retains its binary64 order;
    dangerous intermediates use high precision before final binary64 rounding.

    The result is dimensionless -- a speed in units of ``c`` -- because both inputs
    are energies in the same unit.  It is **not** a velocity in cm/s, and it is
    therefore not a valid ``vnorm`` for :func:`normalized_momentum`; see the module
    docstring.

    Raises
    ------
    ValueError
        If an input is not scalar-shaped, is not finite and positive, or if the
        closed form is not representable in double precision for the supplied
        finite inputs.
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
    """Return the normalized momentum ``p_n = x * vnorm / clight`` on the ``x`` grid.

    ``x`` may carry either sign: the map is a signed grid-to-momentum scaling, and
    it is the downstream electron-ion leaf, not this one, that requires nonnegative
    momentum.  ``vnorm`` may be exactly zero, in which case the whole profile is
    exactly zero.  Both allowances are the retained route's and are kept rather than
    tightened, because tightening them would reject inputs the source accepts with no
    evidence that the source is wrong.  The input array is not modified.

    ``vnorm`` and ``clight`` must be in the same **velocity** unit.  A dimensionless
    speed ratio such as :func:`thermal_electron_momentum` is not a velocity and must
    not be passed as ``vnorm``; doing so divides by ``c`` twice.

    Raises
    ------
    ValueError
        If ``x`` is not a finite one-dimensional array, if ``vnorm`` or ``clight``
        is not scalar-shaped or leaves its domain, or if the profile is not
        representable in double precision for the supplied finite inputs.
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
