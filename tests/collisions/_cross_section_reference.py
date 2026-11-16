"""One reference module for the seven cross-section contracts and the rates built on them.

The seven collision cross sections and the three rate coefficients that stand on
them are one family: every one of them evaluates a frozen logarithmic fit and
returns either a cross section in ``m^2`` or a rate in ``m^3/s``.  They share

* the same evaluation shape (``exp(poly(log E))`` times a unit factor),
* the same declared fit interval and endpoint-clipping semantics,
* the same unit conversion (``cm^2 -> m^2`` is ``1e-4``; ``cm^3/s -> m^3/s`` is
  ``1e-6``),
* and, for the charge-exchange rates, the same equal-mass Maxwellian
  relative-speed integral.

Writing that reference once per asset would not be seven sources of evidence; it
would be seven places to keep in step.  This module is the single copy.

**What this module is not.**  It carries no atomic-physics table, no measured
cross section and no coefficient that was not already frozen in the contract it
belongs to.  The published tables the fits were regressed from (Lindsay and
Stebbings 2005 JGR Table 1, Janev 1995 ch. 11, the Janev ionization tables) are
not in this repository and cannot be read from it, so no absolute table value is
established here.  What the tests built on this module establish is structural:
the seam of a composite branch, the analytic log-slope of the declared
polynomial, the exact unit factor, and agreement between a rate and an
independent quadrature of the separately exposed cross-section contract.

**The frozen literals are a copy on purpose.**  ``FROZEN_FITS`` repeats the
coefficient values the implementation carries, at full binary64 precision, and
``SOURCE_CONSTANTS`` repeats the frozen constants.  A reference that imported
them would move with the thing it is checking and would stay green through a
coefficient or unit mutation; a copy disagrees instead.  When a fit legitimately
changes, this table and the contract's evidence are re-derived in the same
change, which is the audit signal the copy exists to produce.

``UNIT_FACTORS`` is exact rather than a float literal: the keys map to
``fractions.Fraction`` values so ``1e-4`` is declared as the rational number
1/10000 and no float rounding can hide a factor change.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
from scipy import constants

# ---------------------------------------------------------------------------
# Exact unit factors
# ---------------------------------------------------------------------------

UNIT_FACTORS = {
    ("cm^2", "m^2"): Fraction(1, 10**4),
    ("cm^3/s", "m^3/s"): Fraction(1, 10**6),
    ("cm", "m"): Fraction(1, 10**2),
}

#: The two factors the family's contracts declare, as plain floats, so a test
#: can compare an implementation's own literal against the exact rational value.
CM2_TO_M2 = float(UNIT_FACTORS[("cm^2", "m^2")])
CM3_S_TO_M3_S = float(UNIT_FACTORS[("cm^3/s", "m^3/s")])


def convert_unit(value, source, target):
    """Convert ``value`` with the exact tabulated factor for the unit pair."""
    factor = UNIT_FACTORS[(source, target)]
    return np.asarray(value, dtype=float) * float(factor)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Constants frozen by the relations that carry them (copied, not imported).
SOURCE_CONSTANTS = {
    "atomic_mass_kg": 1.6726231e-27,
    "elementary_charge_c": 1.602177e-19,
}

#: The same two quantities from CODATA, used only to state the budget the frozen
#: values buy: they are not the historical values, so a quadrature agreement
#: derived with them differs by a declared amount.
CODATA_CONSTANTS = {
    "electron_volt_j": constants.e,
    "atomic_mass_kg": constants.physical_constants["atomic mass constant"][0],
}


def frozen_thermal_speed(temperature_ev, mass_amu=1.0):
    """``sqrt(2 e T / m)`` in m/s with the frozen constants."""
    return math.sqrt(
        2.0
        * SOURCE_CONSTANTS["elementary_charge_c"]
        * float(temperature_ev)
        / (float(mass_amu) * SOURCE_CONSTANTS["atomic_mass_kg"])
    )


def codata_thermal_speed(temperature_ev, mass_amu=1.0):
    """``sqrt(2 e T / m)`` in m/s with CODATA constants."""
    return math.sqrt(
        2.0
        * CODATA_CONSTANTS["electron_volt_j"]
        * float(temperature_ev)
        / (float(mass_amu) * CODATA_CONSTANTS["atomic_mass_kg"])
    )


# ---------------------------------------------------------------------------
# The frozen fits, in the unit the fit is written in
# ---------------------------------------------------------------------------

#: Seven elastic/charge-exchange cross sections plus the two Janev ionization
#: branches.  Each entry carries the coefficient vector, the declared fit
#: interval in eV and the unit the coefficients were regressed in.
FROZEN_FITS = {
    # atomic-hydrogen-charge-exchange-cross-section (Janev branch)
    "atomic-h-cx-janev": {
        "coefficients": (
            -32.74123792568,
            -0.08916456579806,
            -0.03016990732025,
            0.009205482406462,
            0.002400266568315,
            -0.001927122311323,
            0.0003654750340106,
            -2.788866460622e-05,
            7.422296363524e-07,
        ),
        "interval_ev": (0.1, 1.267317514018116e04),
        "unit": "cm^2",
    },
    # atomic-hydrogen-elastic-cross-section, momentum-transfer branch
    "atomic-h-elastic-momentum": {
        "coefficients": (-33.30843, -0.5738374, -0.102861, -0.00392098, 0.0005964135),
        "interval_ev": (0.03, 1.01e04),
        "unit": "cm^2",
    },
    # atomic-hydrogen-elastic-cross-section, viscosity branch
    "atomic-h-elastic-viscosity": {
        "coefficients": (-33.4486, -0.4238982, -0.07477873, -0.007915053, -0.0002686129),
        "interval_ev": (0.03, 1.01e04),
        "unit": "cm^2",
    },
    # atomic-molecular-hydrogen-elastic-cross-section (H on H2)
    "h-h2-elastic": {
        "coefficients": (-34.95671, -0.4062257, -0.03820531, -0.009404486, 0.0003963723),
        "interval_ev": (0.03, 1.01e04),
        "unit": "cm^2",
    },
    # molecular-hydrogen-charge-exchange-cross-section
    "molecular-h-cx": {
        "coefficients": (
            -34.27958758517,
            -0.07121484125189,
            0.04690466187943,
            -0.00803394666054,
            -0.002265090924593,
            -0.0002102414848737,
            0.0001948869487515,
            -2.208124950005e-05,
            7.262446915488e-07,
        ),
        "interval_ev": (0.1, 2.01e04),
        "unit": "cm^2",
    },
    # molecular-hydrogen-elastic-cross-section (H2 on H2)
    "h2-h2-elastic": {
        "coefficients": (-34.30345, -0.2960406, -0.06382532, -0.007557519, 0.0002606259),
        "interval_ev": (0.03, 1.01e04),
        "unit": "cm^2",
    },
    # proton-molecular-hydrogen-elastic-cross-section (H2 on H+)
    "h2-h+-elastic": {
        "coefficients": (-33.55719, -0.5696568, -0.04089556, -0.01143513, 0.0005926596),
        "interval_ev": (0.03, 1.01e04),
        "unit": "cm^2",
    },
    # proton-atomic-hydrogen-elastic-cross-section (H+ on H), low-energy branch.
    # The parameterized variable of this fit is the center-of-mass energy.
    "h+-h-elastic-low": {
        "coefficients": (
            -32.33966,
            -0.1126918,
            0.005287706,
            -0.002445017,
            -0.001044156,
            8.419691e-05,
            3.824773e-05,
        ),
        "interval_ev": (0.0005, 10.0),
        "unit": "cm^2",
        "variable": "cm",
    },
    # proton-atomic-hydrogen-elastic-cross-section, high-energy branch.
    "h+-h-elastic-high": {
        "coefficients": (-32.31141, -0.1386002),
        "interval_ev": (10.0, 5.05e04),
        "unit": "cm^2",
        "variable": "cm",
    },
    # janev-electron-impact-ionization-rate
    "janev-h": {
        "coefficients": (
            -32.71396786375,
            13.53655609057,
            -5.739328757388,
            1.563154982022,
            -0.2877056004391,
            0.03482559773737,
            -0.002631976175590,
            0.0001119543953861,
            -2.039149852002e-06,
        ),
        "interval_ev": (0.1, 2.01e04),
        "unit": "cm^3/s",
    },
    "janev-h2": {
        "coefficients": (
            -35.68640293666,
            17.33468989961,
            -7.767469363538,
            2.211579405415,
            -0.4169840174384,
            0.05088289820867,
            -0.003832737518325,
            0.0001612863120371,
            -2.893391904431e-06,
        ),
        "interval_ev": (0.1, 2.01e04),
        "unit": "cm^3/s",
    },
}

#: Charge-exchange composite seam: the declared crossing of the Janev branch and
#: the Lindsay-Stebbings high-energy branch, and that branch's constants.
COMPOSITE_JOIN_EV = 1.267317514018116e04
LINDSAY_STEBBINGS = {"a": 4.15, "b": 0.531, "c": 67.3, "power": 4.5, "unit": "cm^2"}
COMPOSITE_UPPER_EV = 2.5e05
FREEMAN_UPPER_EV = 1.0e05
FREEMAN = {"scale": 0.6937e-14, "slope": 0.155, "denominator": 0.1112e-14, "exponent": 3.3}


def log_polynomial_value(log_argument, coefficients):
    """``exp(polyval(log_argument, coefficients))`` in the fit's own unit.

    This is a reference evaluation of the declared parameterization, not an
    independent physical oracle; it is written on a separate code path
    (ascending-coefficient Horner by hand) so the implementation's own
    accumulator cannot make both sides wrong together.
    """
    log_argument = np.asarray(log_argument, dtype=float)
    total = np.zeros_like(log_argument)
    for coefficient in reversed(coefficients):
        total = total * log_argument + coefficient
    return np.exp(total)


def lindsay_stebbings_value_cm2(energy_ev):
    """The 2005 Table 1 high-energy formula in cm^2, recomputed from its constants.

    The published expression is written for ``E`` in keV and yields ``m^2`` after
    its ``1e-20`` factor; expressed in ``cm^2`` the same factor is ``1e-16``.
    """
    energy_kev = np.asarray(energy_ev, dtype=float) / 1000.0
    log_energy = np.log(energy_kev)
    dimensionless = (LINDSAY_STEBBINGS["a"] - LINDSAY_STEBBINGS["b"] * log_energy) ** 2 * (
        1.0 - np.exp(-LINDSAY_STEBBINGS["c"] / energy_kev)
    ) ** LINDSAY_STEBBINGS["power"]
    return dimensionless * 1.0e-16


def freeman_value_cm2(energy_ev):
    """The Freeman-Jones comparison branch in cm^2, recomputed from its constants.

    ``0.6937e-14 (1 - 0.155 log10 E)^2 / (1 + 0.1112e-14 E^3.3)`` is the value in
    ``cm^2`` with ``E`` in eV; the implementation returns ``m^2``, so its extra
    ``1e-4`` is the unit factor this reference leaves out.
    """
    energy = np.asarray(energy_ev, dtype=float)
    return (
        FREEMAN["scale"]
        * (1.0 - FREEMAN["slope"] * np.log10(energy)) ** 2
        / (1.0 + FREEMAN["denominator"] * energy ** FREEMAN["exponent"])
    )


def log_slope(log_energy, coefficients):
    """Analytic ``d ln sigma / d ln E`` of ``exp(sum a_k (ln E)^k)``.

    Differentiating the declared form gives ``sum k * a_k * (ln E)^(k-1)``.  The
    identity holds for every coefficient vector, so comparing it with a slope
    measured from the implementation's own values separates "the evaluation is
    the declared polynomial" from "the coefficients are what they are".
    """
    log_energy = np.asarray(log_energy, dtype=float)
    total = np.zeros_like(log_energy)
    for order, coefficient in enumerate(coefficients):
        if order:
            total = total + order * coefficient * log_energy ** (order - 1)
    return total


# ---------------------------------------------------------------------------
# The equal-mass Maxwellian relative-speed distribution
# ---------------------------------------------------------------------------


def equal_mass_relative_speed_density(speed, beam_speed):
    """Density of ``|u1 - u2|`` for two unit-variance Maxwellians, in units of vth.

    For equal masses the difference of two Maxwellian velocities is again
    Maxwellian, so the magnitude is Maxwell-distributed about the beam offset:

    ``f(u) = u / (sqrt(pi) b) * (exp(-(u-b)^2) - exp(-(u+b)^2))``

    and ``4 u^2 / sqrt(pi) * exp(-u^2)`` at ``b = 0``.  Derived here from the
    convolution rather than read from the implementation, and checked against
    ``int f du = 1`` by :func:`relative_speed_density_integral`.
    """
    speed = np.asarray(speed, dtype=float)
    beam_speed = float(beam_speed)
    if abs(beam_speed) < 1.0e-12:
        return 4.0 * speed**2 / math.sqrt(math.pi) * np.exp(-(speed**2))
    return (
        speed
        / (math.sqrt(math.pi) * beam_speed)
        * (np.exp(-((speed - beam_speed) ** 2)) - np.exp(-((speed + beam_speed) ** 2)))
    )


def relative_speed_density_integral(beam_speed, upper, panels=40000):
    """``int_0^upper f(u) du`` by the composite trapezoid rule on a uniform grid.

    The distribution is normalized to one over ``[0, inf)``; over a finite upper
    edge the integral is ``1 - tail``, and the tail bound
    ``erfc(upper - b) + erfc(upper + b)`` is available.  A density that returned
    zero, or a constant, or the wrong scale would not reproduce this.
    """
    grid = np.linspace(0.0, float(upper), int(panels) + 1)
    values = equal_mass_relative_speed_density(grid, beam_speed)
    return float(np.trapezoid(values, grid))


# ---------------------------------------------------------------------------
# Reference quadrature of a rate against a cross-section contract
# ---------------------------------------------------------------------------


def rate_from_cross_section(
    temperature_ev, energy_ev, cross_section_m2, upper_ev, mass_amu=1.0, panels=2000
):
    """Integrate a cross-section contract into a rate coefficient in m^3/s.

    ``k(T, E) = vth * int_0^{u_max} f(u) sigma(T u^2) * u du`` with
    ``vth = sqrt(2 e T / m)``, ``u = v/vth`` and ``u_max = sqrt(E_upper / T)``.
    ``mass_amu`` is the reduced mass of the pair the cross section describes: 1
    for H/H+ and 2 for the H2/H2+ fit.
    The cross section is the *public contract callable*, so the integrand is the
    contract's own port and this is an integration of the exposed relation, not a
    second fit.

    The quadrature is deliberately not the implementation's: a composite Simpson
    rule on a fixed uniform panel grid, refined once, with the difference between
    the two grids returned as the observed discretization error.  The
    implementation uses adaptive ``scipy.integrate.quad`` with a split at the
    beam speed, so agreement tests the integral rather than repeating it.
    """
    temperature = float(temperature_ev)
    beam_speed = 0.0 if float(energy_ev) == 0.0 else math.sqrt(float(energy_ev) / temperature)
    upper = math.sqrt(float(upper_ev) / temperature)

    def integrand(grid):
        energy = np.minimum(temperature * grid**2, float(upper_ev))
        sigma = np.asarray(cross_section_m2(np.maximum(energy, 0.1)), dtype=float)
        return equal_mass_relative_speed_density(grid, beam_speed) * sigma * grid

    coarse = _simpson_on_grid(integrand, upper, int(panels))
    fine = _simpson_on_grid(integrand, upper, 2 * int(panels))
    return frozen_thermal_speed(temperature, mass_amu) * fine, abs(fine - coarse) / abs(fine)


def _simpson_on_grid(integrand, upper, panels):
    """Composite Simpson rule on ``panels`` even sub-intervals of ``[0, upper]``."""
    if panels % 2:
        panels += 1
    grid = np.linspace(0.0, upper, panels + 1)
    values = integrand(grid)
    weights = np.ones(panels + 1)
    weights[1:-1:2] = 4.0
    weights[2:-1:2] = 2.0
    step = upper / panels
    return float(np.sum(weights * values) * step / 3.0)
