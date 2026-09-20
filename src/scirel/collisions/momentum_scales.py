"""Momentum scales: two independent normalized-momentum definitions.

Two leaves recovered from the cql3d ``cfpgamma.f`` extraction saved in the L1
bundle ``库仑对数能量因子``:

* :func:`thermal_electron_momentum` -- the thermal-electron normalized momentum
  ``p_Te = sqrt(2T/mc^2)``, a **dimensionless** speed ratio in units of ``c``;
* :func:`normalized_momentum` -- the grid-to-momentum map
  ``p_n = x * vnorm / clight``, with ``vnorm`` and ``clight`` in a common
  **velocity** unit.

Both are *definitions*, not fits: each is evaluated from explicit inputs and is
asserted equal to its closed form in double precision rather than to a tolerance.

**The two leaves are independent assets, and the V3 candidate's composition claim
was wrong.**  V3 documented and tested ``p_Te`` as "the ``vnorm`` this map
consumes", and both V3 asset documents listed that composition under
``applicability.supported``.  It does not hold, and the reason is dimensional:

``p_Te`` is ``v/c`` -- dimensionless, a ratio of speeds -- while ``vnorm`` is a
speed in cm/s.  Feeding ``p_Te`` to ``vnorm`` and dividing by ``clight`` divides
by ``c`` twice, once implicitly in ``p_Te`` and once explicitly in the map.  The
result is smaller than the dimensionally consistent value by exactly the factor
``clight``:

    thermal_electron_momentum(250.0, 511.0)  = 0.9891782353111633
    normalized_momentum(x=GRID, vnorm=that, clight=2.99792458e10)
        = GRID * 0.9891782353111633 / 2.99792458e10
        = GRID * 3.2995...e-11

A caller wanting the dimensionless grid momentum ``x * p_Te`` gets a profile
eleven orders of magnitude too small, with no error and no warning.  V3 asserted
the composition was correct because both halves are individually correct and the
arithmetic of each matches its own closed form; that is exactly why the defect
survived a passing suite.  V4 therefore **removes the composition claim from both
assets** and replaces it with a test that measures the dimensional inconsistency
and the ``clight`` factor.  Neither leaf imports or references the other, and a
test asserts that.

A future TaskGraph may connect the two, but only through an explicit and
dimensionally valid conversion -- for example ``vnorm = p_Te * clight``, which
makes ``p_n = x * p_Te``.  This module performs no unit conversion and claims
none: the conversion is the caller's, and the two leaves are published as what
they are.

**What is held out, and why.**  The retained route exposes six mappings behind a
string dispatcher ``scientific_operator(operation, **kwargs)``.  Four are not here:

* ``enabled_argument_scale`` produces ``flamrp1``, which is a *Coulomb-log argument*
  scale, not a momentum scale -- the two are different relations and the module is
  named for what it contains;
* ``enabled_gamefac``, ``hesslow_electron_electron`` and ``hesslow_electron_ion``
  are dimensionless multipliers applied to a Coulomb logarithm, a third relation
  again.

None of the four is a refinement of these two leaves, so publishing them together
would make one asset document describe three relations and would make this unit's
evidence ceiling the weakest of the three.  The V2 candidate kept all six in one
module under the name ``coulomb_log_scales``; this unit keeps the two that are
momentum scales, and a test asserts the other four are absent from the module, so
the hold-out is visible rather than implied.  That the four remain callable
through the retained dispatcher was established by the frozen review against the
external route and is not replayed by the maintained tests, which cannot reach it.

**The dispatcher is not reproduced.**  ``operation`` is a routing string, not a
scientific input: it selects a relation rather than parameterising one, and a
caller that has already chosen a relation does not need to name it again.  The two
leaves are called directly by name.

**Every scalar input is required to be scalar-shaped.**  The V3 candidate delegated
the check to ``float(value)``.  ``float`` is a converter, not a check: it accepts a
0-dimensional array, and its treatment of a one-element container is a NumPy
conversion rule rather than part of this contract -- on this build it raises a
``TypeError`` whose message names ``float`` and not the parameter.  V4 checks the
shape before converting, so a non-scalar container is rejected deterministically and
by parameter name.  **Nothing else about the input contract changes:** the conversion
is still ``float(value)``, the finite/positive domain checks are unchanged, a
0-dimensional array is scalar-shaped and is accepted, and whether a convertible
non-numeric value such as ``True`` or the string ``"250.0"`` should be rejected is
outside this revision and is left exactly as the retained route has it.

**A finite input whose result is not representable is rejected.**  Both leaves
state that every accepted call returns a finite value, and neither input domain
is bounded above: ``temperature_kev`` and ``restmkev`` are required to be finite
and positive, ``vnorm`` finite and non-negative, ``clight`` finite and positive,
and ``x`` a finite array.  Two finite inputs therefore reached a non-finite
result on the V4 candidate, both returning positive infinity with no error:

    thermal_electron_momentum(temperature_kev=1.0e308, restmkev=511.0)
        2.0 * 1.0e308 overflows to inf, so sqrt(inf) is inf;
    normalized_momentum(x=[1.0e308], vnorm=1.0e308, clight=5.0e-324)
        1.0e308 * 1.0e308 overflows to inf, and inf / 5.0e-324 is still inf.

Both are now checked after the arithmetic and raise ``ValueError`` naming the
quantity that was not finite.  This is a representability check on finite inputs
and not a magnitude cutoff: no threshold is introduced, and an input that is
large but representable is evaluated and returned exactly as before.  The input
domain is deliberately not narrowed, because narrowing it would require inventing
a bound the retained route does not state.

Evidence ceiling: this module establishes the two normalized-momentum definitions
and their input contracts exactly, establishes that the two leaves are **not**
composable as V3 claimed and by what factor they differ when composed anyway, and
establishes that a finite input whose result is not representable is rejected
rather than returned.  The bit-for-bit agreement with the retained route and with
the frozen predecessors was established by the frozen review against those
external arms and is **not** replayed by the maintained tests, which cannot reach
them.  This module does **not** establish that ``p_Te = sqrt(2T/mc^2)`` is the
right thermal scale for any collision model, it does **not** establish the units
or the value of any caller-supplied constant, all of which are the caller's, and
it does **not** establish the dimensionally correct conversion between the two
leaves, which it deliberately does not perform.
"""
from __future__ import annotations

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
NON_REPRESENTABLE_MESSAGE = (
    "the normalized momentum is not representable for these finite inputs"
)


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

    A definition, not a fit: the returned value is exactly
    ``sqrt(2.0 * temperature_kev / restmkev)`` in double precision.

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
    result = float(np.sqrt(2.0 * temperature_kev / restmkev))
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
    # The overflow warning NumPy would raise here is the condition
    # `_require_representable` detects explicitly and reports as a ValueError, so
    # it is suppressed rather than reported twice.
    with np.errstate(over="ignore", invalid="ignore"):
        result = x * vnorm / clight
    _require_representable(result, "the grid momentum profile")
    return result
