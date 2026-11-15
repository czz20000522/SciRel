"""Independent loop integrals for the bounded flux-reference checks.

The inputs below are dyadic numbers. No SciRel function, Green value or returned
current enters the reference. The coefficient is the declared magnetostatic
model's mu0/(4*pi)=1e-7, rather than an exact post-2019 SI definition of mu0.
"""

from fractions import Fraction
from functools import lru_cache

import mpmath as mp

RADIAL_R = (1.0, 1.5, 2.0)
RADIAL_Z = (0.5, 1.0, 1.5)
RADIAL_SOURCE = (2.0, 0.0, 1.0)
STEP_R = (1.0, 1.5)
STEP_Z = (-0.5, 0.5)
STEP_SOURCE = (1.0, -0.5, 1.0)
STEP_TARGET = (1.5, 0.5)
FULL_R = (0.5, 0.75, 1.0, 1.25, 1.5)
FULL_Z = (-0.5, 0.0, 0.5)
FULL_TARGETS = ((1.0, 0.5), (1.5, 0.5))


@lru_cache(maxsize=None)
def loop_integral(source, target, quantity, dps):
    """Integrate vector potential or Biot-Savart directly over source angle."""
    with mp.workdps(dps):
        a, z0, current = map(mp.mpf, source)
        r, z = map(mp.mpf, target)
        h = z - z0

        def distance(t):
            return mp.sqrt(a * a + r * r - 2 * a * r * mp.cos(t) + h * h)

        if quantity == "psi":
            factor = mp.mpf("1e-7") * current * a * r
            integrand = lambda t: mp.cos(t) / distance(t)
        elif quantity == "br":
            factor = mp.mpf("1e-7") * current * a * h
            integrand = lambda t: mp.cos(t) / distance(t) ** 3
        elif quantity == "bz":
            factor = mp.mpf("1e-7") * current * a
            integrand = lambda t: (a - r * mp.cos(t)) / distance(t) ** 3
        else:
            raise ValueError("unknown loop reference quantity")
        return factor * mp.quad(
            integrand, [0, mp.pi / 2, mp.pi, 3 * mp.pi / 2, 2 * mp.pi], method="tanh-sinh"
        )


def _check_precision(low, high):
    with mp.workdps(120):
        assert abs(low - high) <= mp.mpf("1e-70") + mp.mpf("1e-60") * abs(high)
    return high


@lru_cache(maxsize=None)
def checked_loop_integral(source, target, quantity):
    """Check 80/120-digit agreement before returning the reference value."""
    return _check_precision(
        loop_integral(source, target, quantity, 80),
        loop_integral(source, target, quantity, 120),
    )


def full_currents(clipped):
    """Analytic first-update currents, from P'=-1 and dR*dZ=1/8."""
    return tuple(
        Fraction(0) if r > 1.25 or (clipped and iz == 1 and ir == 1) else -Fraction(r) / 8
        for iz, _ in enumerate(FULL_Z)
        for ir, r in enumerate(FULL_R)
    )


@lru_cache(maxsize=None)
def full_flux(target, clipped, dps):
    """Sum original-input filament integrals with analytic, not returned, currents."""
    with mp.workdps(dps):
        terms = []
        sources = ((r, z) for z in FULL_Z for r in FULL_R)
        for point, current in zip(sources, full_currents(clipped), strict=True):
            if current == 0 or point == target:
                # Only the declared discrete exact self entry is set to zero.
                continue
            unit_flux = loop_integral((*point, 1.0), target, "psi", dps)
            terms.append(mp.mpf(current.numerator) / current.denominator * unit_flux)
        return mp.fsum(terms)


def checked_full_flux(target, clipped):
    """Check the complete independent sum at both frozen precisions."""
    return _check_precision(full_flux(target, clipped, 80), full_flux(target, clipped, 120))
