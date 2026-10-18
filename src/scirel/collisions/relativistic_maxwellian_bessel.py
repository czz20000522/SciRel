"""Relativistic Maxwellian modified-Bessel closure -- ``exp(x) * K_order(x)``.

The three quantities the relativistic background-Maxwellian branch of the Coulomb
collision coefficient chain needs:

    bk0 = exp(x) * K_0(x)
    bk1 = exp(x) * K_1(x)
    bk2 = bk0 + 2 * bk1 / x          the K_2 recurrence

**The retained route's piecewise polynomial approximation is replaced by a direct
evaluation.**  The source route splits the argument at ``x = 2``: below it, the
Abramowitz--Stegun polynomial fits for ``I0``/``I1`` and the small-argument
``K0``/``K1`` series rescaled by ``exp(x)``; at and above it, the asymptotic
polynomials in ``2/x``.  The two branches represent the same function but do not
meet.  Measured, the ``bk1`` discontinuity across the boundary is
``1.5076691838017936e-03`` relative, and that jump is the largest error anywhere in
the route's domain ``(0, 60]`` -- larger than its smooth approximation error
anywhere else.  Evaluating ``exp(x) K_order(x)`` directly removes the
approximation, and with it three things that are not scientific output: the branch
selector, the branch label, and the per-branch accuracy metadata that the V2
candidate returned as ports.

Measured against the retained route:

============================  =========================  ==========
quantity                      worst relative difference  at
============================  =========================  ==========
``bk0``                       ``1.4592152808791253e-07``  ``x = 38.71200060003``
``bk1``                       ``0.0007518301076547563``  ``x = 1.9``
``bk2``                       ``0.00042540348489499393``  ``x = 1.9``
boundary jump, this module    ``8.59408144671376e-16``   ``x = 2``
boundary jump, retained route ``0.0015076691838017936``   ``x = 2``
============================  =========================  ==========

**The direct evaluation fails closed where the backend cannot represent the
closure.**  ``scipy.special.kve`` is a double-precision routine with a finite
domain, and the recurrence's ``2*bk1/x`` term can overflow; at some arguments the
three quantities are therefore not finite numbers.  The V3 candidate returned
those values to the caller and pinned them in tests.  That is the same contract
defect the AORSA unit's review rejected on the dielectric tensor: an accepted call
must not return a non-finite scientific result.

V4 computes the three quantities and then checks, once, that all three are finite.
If any is not, the call is rejected with :class:`BesselBackendEvaluationError` and
the message reports the input and the values that were produced.

**The rejection is not a claim about where the domain ends, and this module
deliberately does not state one.**  The arguments at which the installed SciPy
stops being representable are properties of this build and this platform, not
properties of the relation, so they are not constants of this asset, not branches
in its logic, not part of its error messages, and not part of its public contract.
A caller learns from a rejection only that *this* backend could not evaluate
*that* argument; a caller that needs a portable domain bound must derive it from
the relation and its own platform, or catch the exception.

The exception hierarchy has exactly two members, because there are exactly two
things a caller can do:

``InvalidBesselArgumentError``
    ``x`` is not a positive finite scalar.  This is the retained route's guard and
    its message, unchanged; V4 raises it as this class rather than as a bare
    ``ValueError`` so a caller can tell its own mistakes apart from the backend's.
``BesselBackendEvaluationError``
    ``x`` is a valid argument and ``scipy.special.kve`` did not return three finite
    quantities for it.

Both are subclasses of ``ValueError``, so ``except ValueError`` still catches
everything this relation raises.

Evidence ceiling: this module establishes that the closure is ``exp(x) K_order(x)``
as SciPy computes it, that ``bk2`` is the recurrence rather than an independent
third approximation, that every accepted call returns three finite floats, and
that its own value is smooth across the retained branch boundary.  The measured
distance from the retained route and from its boundary discontinuity was
established by the frozen review against that external route and is **not**
replayed by the maintained tests, which cannot reach it; the figures are recorded
above as the reason for the change.  This module does **not** establish the
physical accuracy of the closure for any distribution, it does **not** state or
bound the domain over which the backend can evaluate it, and it does **not**
establish that the source's Abramowitz--Stegun coefficients or its ``x = 2`` split
are the right ones to have replaced -- the retained bundle cites no reference for
either, and no independent special-function table was consulted.
"""
from __future__ import annotations

import math

__all__ = [
    "BesselBackendEvaluationError",
    "InvalidBesselArgumentError",
    "relativistic_maxwellian_bessel",
]


def kve(order, argument):
    """Load SciPy's scaled modified-Bessel backend at the numeric boundary.

    The name remains a module-local seam so the existing backend-failure tests
    can replace it without importing SciPy while this module is discovered.
    """
    from scipy.special import kve as scipy_kve

    return scipy_kve(order, argument)


class InvalidBesselArgumentError(ValueError):
    """``x`` is not a positive finite scalar.  The caller's input is wrong."""


class BesselBackendEvaluationError(ValueError):
    """``x`` is valid and ``scipy.special.kve`` did not return three finite values.

    The argument is a legitimate input; the failure is the double-precision
    backend's.  The message reports the input and the values produced, and states
    no domain bound, because the bound is a property of the installed SciPy rather
    than of the relation.
    """


def relativistic_maxwellian_bessel(x):
    """Return the ``{bk0, bk1, bk2}`` relativistic Maxwellian Bessel closure.

    Parameters
    ----------
    x
        The Bessel argument: a positive finite scalar.

    Returns
    -------
    dict
        ``bk0`` -- ``exp(x) * K_0(x)``.
        ``bk1`` -- ``exp(x) * K_1(x)``.
        ``bk2`` -- always the recurrence ``bk0 + 2*bk1/x``, not an independent
        third approximation.

        All three are finite floats on every accepted call.

    Raises
    ------
    InvalidBesselArgumentError
        If ``x`` is not positive and finite.  This is the retained route's guard
        and its message, unchanged; the class is narrowed, not the test.
    BesselBackendEvaluationError
        If ``scipy.special.kve`` did not return finite values for a valid ``x``.
        The rejection is whole-call: a partially non-finite closure is not a usable
        scientific result.  No domain bound is stated or implied.
    """
    value = float(x)
    if not math.isfinite(value) or value <= 0.0:
        raise InvalidBesselArgumentError("x must be positive and finite")
    bk0 = float(kve(0, value))
    bk1 = float(kve(1, value))
    bk2 = bk0 + 2.0 * bk1 / value
    # One check, after the arithmetic, over all three outputs.  The V3 candidate
    # returned non-finite values here; an accepted call may not.
    if not (math.isfinite(bk0) and math.isfinite(bk1) and math.isfinite(bk2)):
        raise BesselBackendEvaluationError(
            f"scipy.special.kve did not return a finite closure for x={value!r}: "
            f"bk0={bk0!r}, bk1={bk1!r}, bk2={bk2!r}"
        )
    return {"bk0": bk0, "bk1": bk1, "bk2": bk2}
