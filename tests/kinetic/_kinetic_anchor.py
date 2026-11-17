"""Shared cold-limit anchor for the kinetic dispersion and wavevector ports.

Both the relation port and the wavevector ports are anchored on the same cross-asset
quantity: the plasma frequency recomputed from the published relation
``omega_p**2 = sum n q**2/(eps0 m)`` by the B5 fluid reference helper, which is an
independent mpmath reimplementation and shares no code with the kinetic ports.

Keeping the anchor in one module matters for a reason beyond duplication: the two
ports take *different* argument conventions (``ns_unit``/``Ts_unit`` ratios versus
physical ``ns0``/``Ts0``), so a copied anchor would silently encode one convention and
then be used under the other.
"""

from __future__ import annotations

import mpmath as mp

import _cold_fluid_spectrum_reference as fluid

# Declared in the relation port's unit system: single species with q = m = n00 = T00 =
# B0 = 1, wavevector along z with a unit transverse fraction.
COLD_KWARGS = dict(
    B0=1.0,
    qs=[1.0],
    ms=[1.0],
    ns_unit=[1.0],
    n00=1.0,
    T00=1.0,
    kz=1.0,
    kx_frac=1.0,
)
T_COLD = 1e-4


def plasma_frequency_over_unit(ts_unit=T_COLD, temperature_unit=1.0):
    """``omega_p / omega_n`` from first principles, via the independent fluid helper."""
    fluid.high_precision()
    scales = fluid.case_scales([1.0], [1.0], [1.0], [ts_unit], 1.0, 1.0, temperature_unit)
    return mp.sqrt(sum(scales["wps2"])) / mp.mpf(float(scales["wcn"]))


def kinetic_determinant(omega_frac, method="ronnmark", ts_unit=T_COLD):
    """The kinetic determinant at one normalised frequency."""
    from scirel.kinetic.kinetic_dispersion_relation import evaluate_kinetic_dispersion_relation

    result = evaluate_kinetic_dispersion_relation(
        Ts_unit=[ts_unit], omega_frac=float(omega_frac), **COLD_KWARGS
    )
    return complex(complex(result[f"determinant_{method}"]))


def find_zero(bracket_low, bracket_high, function=None, iterations=60):
    """Bisect a real-valued function whose root lies inside the bracket.

    The loop body must test the **midpoint**, not the retained lower bound.  Testing
    ``function(low)`` looks correct and is not: the lower bound stays on its own side
    of the root for the whole loop, so the predicate never changes and the bracket
    collapses onto the upper edge.  That mistake produced ``1.05 * omega_p`` -- a
    2.5e-2 "agreement" that is exactly the bracket width and reads like a physical
    result.  This docstring is the reason the code below is written the way it is.
    """
    evaluate = function if function is not None else (lambda x: kinetic_determinant(x).real)
    low, high = mp.mpf(bracket_low), mp.mpf(bracket_high)
    for _ in range(iterations):
        middle = (low + high) / 2
        if evaluate(middle) < 0.0:
            low = middle
        else:
            high = middle
    return (low + high) / 2
