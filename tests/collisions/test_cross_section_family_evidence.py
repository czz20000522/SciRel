"""Structural evidence for the seven cross-section contracts and the three rates.

These contracts declare a frozen logarithmic fit evaluated on a clipped interval
and converted from the unit the fit was regressed in.  What can be established
inside this repository about them is structural, and that is what this file
does:

* **unit factor** — the returned value is the fit's own value times the exact
  ``cm^2 -> m^2`` (``1e-4``) or ``cm^3/s -> m^3/s`` (``1e-6``) factor, and it
  lands in the dimension's order of magnitude rather than at zero, at the input,
  or at a constant off by a factor of ten;
* **branch seam** — where a contract joins two parameterizations it says so, and
  the join is continuous where the contract claims continuity and discontinuous
  where it declares the discontinuity;
* **asymptotics** — the log-log slope measured from the returned values equals
  the analytic derivative of the declared polynomial, so the evaluation really is
  the declared form and not a different curve through the same endpoints;
* **exact quadrature** — the charge-exchange rates are checked against an
  independent integration of the separately exposed cross-section contract, and
  the fit branch against that same integral at order-of-magnitude agreement.

**What this file does not do.**  It does not validate an absolute table value.
The published tables the fits were regressed from — Lindsay and Stebbings 2005
JGR Table 1, Janev 1995 ch. 11, the Janev ionization tables — are not in this
repository and are not reachable from it, so no absolute cross section or rate
is asserted as correct here.  The reference module repeats the frozen
coefficient literals at full precision: that makes a coefficient mutation
visible, and it is why the same evidence cannot be restated as physical
validation.

Every assertion here is also asked the audit question: would it go red if the
implementation returned zero, returned its input unchanged, or returned a
constant of the wrong magnitude?  The positivity and magnitude-band assertions
answer the first, the unit-factor and slope assertions the second, and the
exact-factor comparisons the third.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_charge_exchange_cross_section,
    evaluate_atomic_hydrogen_charge_exchange_rate,
    evaluate_atomic_hydrogen_elastic_cross_section,
    evaluate_hydrogen_h2_elastic_cross_section,
    evaluate_hydrogen2_charge_exchange_rate,
    evaluate_hydrogen2_hydrogen2_elastic_cross_section,
    evaluate_hydrogen2_proton_elastic_cross_section,
    evaluate_hydrogen_proton_elastic_cross_section,
    evaluate_janev_electron_impact_ionization_rate,
    evaluate_molecular_hydrogen_charge_exchange_cross_section,
)
import _cross_section_reference as reference

#: One row per fit the family exposes.  ``probe_ev`` lists the energies used for
#: the slope and unit-factor checks; each one is strictly inside the declared fit
#: interval, because at a clip endpoint the function is constant on one side and
#: the finite difference would measure the clip, not the fit.  Every row carries
#: one probe close to the upper edge on purpose: a moved clip boundary leaves the
#: interior values alone, so only a near-edge probe notices it.
CROSS_SECTION_CASES = (
    (
        "atomic-h-cx-janev",
        evaluate_atomic_hydrogen_charge_exchange_cross_section,
        (0.12, 1.0, 100.0, 1.0e3, 1.0e4),
    ),
    (
        "atomic-h-elastic-momentum",
        evaluate_atomic_hydrogen_elastic_cross_section,
        (0.04, 0.1, 1.0, 100.0, 9.0e3),
    ),
    (
        "h-h2-elastic",
        evaluate_hydrogen_h2_elastic_cross_section,
        (0.04, 0.1, 1.0, 100.0, 9.0e3),
    ),
    (
        "molecular-h-cx",
        evaluate_molecular_hydrogen_charge_exchange_cross_section,
        (0.12, 0.5, 10.0, 1.0e3, 1.8e4),
    ),
    (
        "h2-h2-elastic",
        evaluate_hydrogen2_hydrogen2_elastic_cross_section,
        (0.04, 0.1, 1.0, 100.0, 9.0e3),
    ),
    (
        "h2-h+-elastic",
        evaluate_hydrogen2_proton_elastic_cross_section,
        (0.04, 0.1, 1.0, 100.0, 9.0e3),
    ),
)

#: The declared cross sections are of order 1e-19 m^2 around 1 eV and fall by
#: several decades towards the upper edge of the fit interval.  The band is
#: therefore applied to the low and middle probes only, where "zero", "the input
#: echoed back" and "a constant of the wrong magnitude" are separable by an order
#: of magnitude.  It is a guard, not a check on the value; the exact unit-factor
#: assertion is what checks the value.
CROSS_SECTION_BAND_M2 = (1.0e-22, 1.0e-16)
CROSS_SECTION_BAND_CEILING_EV = 1.0e3

#: Rate coefficients in m^3/s on the same terms.
RATE_BAND_M3_S = (1.0e-18, 1.0e-12)

#: Relative budget for a value compared with the same arithmetic on another code
#: path: the four binary64 roundings an ``exp``/Horner chain can differ by.
SAME_FORMULA_RTOL = 8.0e-16

#: Relative budget for the composite seam.  The join constant is published to 16
#: digits and the two branches are fit to it; the observed gap is 5e-10 relative,
#: while a one-digit change in any Janev coefficient moves the value by 1e-2, so
#: this budget separates "the branches meet" from "a coefficient moved".
SEAM_RTOL = 1.0e-6

#: Budget for the slope identity.  The central difference of step h carries a
#: truncation term h^2/6 |d^3 ln(sigma)/d(ln E)^3|; with h = 1e-3 and a
#: logarithmic polynomial of order four on these intervals the bound is below
#: 1e-6, and the observed maximum is 1e-7.  The budget is stated per unit of the
#: slope's own magnitude so a steep branch is not held to a looser absolute band.
SLOPE_STEP = 1.0e-3
SLOPE_BUDGET = 1.0e-4

#: Budget for the rate quadrature.  The implementation integrates with adaptive
#: ``scipy.integrate.quad`` split at the beam speed; the reference uses composite
#: Simpson on a uniform grid.  Their observed spread is 1.6e-6 relative and the
#: reference's own two-grid error estimate is below 1e-7.
QUADRATURE_RTOL = 5.0e-5

#: Band for "the fitted rate and the integral of the separately fitted cross
#: section agree at order of magnitude".  This is an observed fit-to-fit spread,
#: not a validated accuracy: the sampled maximum is 2.8 % (atomic) and 1.8 %
#: (molecular).  The band exists to catch a ten-fold unit slip, which would land
#: at 0.1 or 10.
FIT_TO_INTEGRAL_BAND = (0.8, 1.2)


def _scalar(call, energy):
    return float(np.ravel(np.asarray(call(np.asarray([float(energy)]))))[0])


def _reference_cm2(fit_name, energy):
    return float(
        np.ravel(
            reference.log_polynomial_value(
                math.log(float(energy)), reference.FROZEN_FITS[fit_name]["coefficients"]
            )
        )[0]
    )


def _finite_difference_slope(call, energy):
    low = _scalar(call, math.exp(math.log(energy) - SLOPE_STEP))
    high = _scalar(call, math.exp(math.log(energy) + SLOPE_STEP))
    return (math.log(high) - math.log(low)) / (2.0 * SLOPE_STEP)


@pytest.mark.parametrize(
    "fit_name,call,probe_ev",
    CROSS_SECTION_CASES,
    ids=[case[0] for case in CROSS_SECTION_CASES],
)
def test_the_returned_value_is_the_fit_times_the_exact_area_factor(fit_name, call, probe_ev):
    """``sigma_m2 = fit_cm2 * 1e-4`` to within the last binary64 bits.

    The factor is taken from ``UNIT_FACTORS``, which stores it as the rational
    number 1/10000, so the assertion cannot be satisfied by a different power of
    ten and cannot be masked by an approximate ``atol``.
    """
    energy = np.asarray(probe_ev)
    actual = np.asarray(call(energy), dtype=float)
    expected = np.array([_reference_cm2(fit_name, value) for value in probe_ev]) * (
        reference.CM2_TO_M2
    )
    np.testing.assert_allclose(actual, expected, rtol=SAME_FORMULA_RTOL, atol=0.0)
    in_band = energy <= CROSS_SECTION_BAND_CEILING_EV
    lower, upper = CROSS_SECTION_BAND_M2
    assert np.all(actual[in_band] > lower) and np.all(actual[in_band] < upper), actual
    assert np.all(actual > 0.0) and np.all(np.isfinite(actual))
    assert np.all(actual < energy) or np.all(actual < 1.0), "a cross section is not an energy"
    assert len(set(actual.tolist())) == len(actual), (
        "the fit returned one value for several energies"
    )


@pytest.mark.parametrize(
    "fit_name,call,probe_ev",
    CROSS_SECTION_CASES,
    ids=[case[0] for case in CROSS_SECTION_CASES],
)
def test_the_log_slope_is_the_analytic_derivative_of_the_declared_polynomial(
    fit_name, call, probe_ev
):
    """``d ln(sigma)/d ln(E)`` measured from the values equals the analytic form.

    The analytic slope is differentiated from the declared coefficient vector, so
    this separates two claims: the implementation evaluates *this* polynomial,
    and the polynomial has the coefficients the contract records.  A sign flip, a
    dropped term or a truncated coefficient vector changes the slope by 1e-2 or
    more, far outside the budget.
    """
    coefficients = reference.FROZEN_FITS[fit_name]["coefficients"]
    for energy in probe_ev:
        predicted = float(np.ravel(reference.log_slope(math.log(energy), coefficients))[0])
        measured = _finite_difference_slope(call, energy)
        assert abs(predicted - measured) <= SLOPE_BUDGET * max(1.0, abs(predicted)), (
            energy,
            predicted,
            measured,
        )


def test_the_composite_charge_exchange_seam_is_continuous():
    """The Janev and Lindsay-Stebbings branches meet at the declared join.

    The contract declares one continuous relation below and above
    ``1.267317514018116e4 eV``; the two branches are independent
    parameterizations, so continuity is a property to check, not to assume.  The
    comparison is made across the join from the returned values themselves, and
    each side is also compared with its own reference formula.
    """
    join = reference.COMPOSITE_JOIN_EV
    below = _scalar(evaluate_atomic_hydrogen_charge_exchange_cross_section, join * (1.0 - 1.0e-9))
    at = _scalar(evaluate_atomic_hydrogen_charge_exchange_cross_section, join)
    above = _scalar(evaluate_atomic_hydrogen_charge_exchange_cross_section, join * (1.0 + 1.0e-9))
    assert abs(below / at - 1.0) <= SEAM_RTOL
    assert abs(above / at - 1.0) <= SEAM_RTOL
    janev = _reference_cm2("atomic-h-cx-janev", join) * reference.CM2_TO_M2
    lindsay = float(reference.lindsay_stebbings_value_cm2(join)) * reference.CM2_TO_M2
    assert abs(at / janev - 1.0) <= SAME_FORMULA_RTOL
    assert abs(at / lindsay - 1.0) <= SEAM_RTOL


def test_the_high_energy_branch_is_the_lindsay_stebbings_table_formula():
    """Above the join the contract evaluates the published Table 1 expression.

    The formula is recomputed here from its constants with ``E`` in keV, and the
    returned value is in ``m^2``, so this also re-checks the ``1e-20``/``1e-4``
    constants of that branch.
    """
    energy = np.array([2.0e4, 5.0e4, 1.0e5, 2.5e5])
    actual = np.asarray(evaluate_atomic_hydrogen_charge_exchange_cross_section(energy))
    expected = np.asarray(reference.lindsay_stebbings_value_cm2(energy)) * reference.CM2_TO_M2
    np.testing.assert_allclose(actual, expected, rtol=SAME_FORMULA_RTOL, atol=0.0)
    # The Table 1 branch falls to about 1.9e-23 m^2 at its 250 keV edge, so the
    # band only has to exclude zero and the input echoed back.
    assert np.all(actual > 1.0e-26)


def test_the_freeman_selector_is_a_distinct_comparison_branch():
    """``freeman=True`` evaluates the Freeman-Jones fit, not the default composite.

    The branch is an independent fit through 100 keV; the assertion is that it is
    the declared expression and that it is not a silent alias of the default.
    """
    energy = np.array([0.2, 1.0, 100.0, 1.0e4, 9.0e4])
    actual = np.asarray(
        evaluate_atomic_hydrogen_charge_exchange_cross_section(energy, freeman=True)
    )
    expected = np.asarray(reference.freeman_value_cm2(energy)) * reference.CM2_TO_M2
    np.testing.assert_allclose(actual, expected, rtol=SAME_FORMULA_RTOL, atol=0.0)
    composite = np.asarray(evaluate_atomic_hydrogen_charge_exchange_cross_section(energy))
    assert np.max(np.abs(actual / composite - 1.0)) > 0.05


def test_the_viscosity_selector_is_a_distinct_fit():
    """``viscosity=True`` is a second coefficient set, not the momentum-transfer one."""
    energy = np.array([0.1, 1.0, 100.0, 1.0e3])
    momentum = np.asarray(evaluate_atomic_hydrogen_elastic_cross_section(energy))
    viscosity = np.asarray(evaluate_atomic_hydrogen_elastic_cross_section(energy, viscosity=True))
    expected = np.array([_reference_cm2("atomic-h-elastic-viscosity", value) for value in energy])
    np.testing.assert_allclose(
        viscosity, expected * reference.CM2_TO_M2, rtol=SAME_FORMULA_RTOL, atol=0.0
    )
    assert np.all(np.abs(viscosity / momentum - 1.0) > 1.0e-2)


def test_the_proton_on_hydrogen_fit_uses_the_center_of_mass_energy():
    """The parameterized variable is ``E_cm = E_lab / 2``, and the seam is at 10 eV cm.

    Equal masses and a stationary target make the conversion exact, and the
    contract declares which side of ``E_cm = 10`` each polynomial covers.  A
    factor-of-two slip in the kinematics moves every value by a few per cent, and
    a wrong branch at the boundary moves it by the declared jump.
    """
    low = reference.FROZEN_FITS["h+-h-elastic-low"]["coefficients"]
    high = reference.FROZEN_FITS["h+-h-elastic-high"]["coefficients"]
    for laboratory in (0.01, 1.0, 10.0, 19.0):
        expected = (
            float(np.ravel(reference.log_polynomial_value(math.log(laboratory / 2.0), low))[0])
            * reference.CM2_TO_M2
        )
        actual = _scalar(evaluate_hydrogen_proton_elastic_cross_section, laboratory)
        assert abs(actual / expected - 1.0) <= SAME_FORMULA_RTOL, laboratory
    for laboratory in (20.0, 100.0, 1.0e4, 9.0e4):
        expected = (
            float(np.ravel(reference.log_polynomial_value(math.log(laboratory / 2.0), high))[0])
            * reference.CM2_TO_M2
        )
        actual = _scalar(evaluate_hydrogen_proton_elastic_cross_section, laboratory)
        assert abs(actual / expected - 1.0) <= SAME_FORMULA_RTOL, laboratory

    at_seam = _scalar(evaluate_hydrogen_proton_elastic_cross_section, 20.0)
    just_below = _scalar(evaluate_hydrogen_proton_elastic_cross_section, 20.0 * (1.0 - 1.0e-9))
    jump = abs(at_seam / just_below - 1.0)
    # The two empirical fits are not forced continuous: the contract declares a
    # jump at the seam, and this pins the measured size so that quietly forcing
    # continuity would also be a red test.
    assert 5.0e-3 < jump < 2.0e-2, jump


def test_the_relative_speed_density_is_normalized():
    """The reference distribution integrates to one, so it cannot be a zero or a constant."""
    for beam in (0.0, 0.5, 2.0):
        integral = reference.relative_speed_density_integral(beam, 14.0)
        assert abs(integral - 1.0) <= 1.0e-9, (beam, integral)
    values = reference.equal_mass_relative_speed_density(np.array([0.5, 1.0, 2.0]), 1.0)
    assert np.all(values > 0.0) and len(set(values.tolist())) == 3


def test_the_reference_quadrature_recovers_the_atomic_rate_at_high_energy():
    """Above the bivariate fit domain the rate is the integral of the cross section.

    The implementation integrates with adaptive ``quad`` split at the beam speed;
    the reference integrates the public cross-section callable with composite
    Simpson on a uniform grid.  Agreement at 5e-5 is agreement between two
    quadrature schemes over the same integrand, so a wrong integrand, a missing
    ``v`` factor or a ten-fold unit slip is red.
    """
    cases = ((3.0e4, 1.0e5), (3.0e4, 0.0), (1.0e5, 1.0e5), (2.5e4, 1.0e4))
    for temperature, energy in cases:
        expected, discretization = reference.rate_from_cross_section(
            temperature,
            energy,
            evaluate_atomic_hydrogen_charge_exchange_cross_section,
            reference.COMPOSITE_UPPER_EV,
        )
        assert discretization < QUADRATURE_RTOL / 10.0, (temperature, energy, discretization)
        actual = float(
            np.ravel(
                evaluate_atomic_hydrogen_charge_exchange_rate(
                    np.asarray([temperature]), np.asarray([energy])
                )
            )[0]
        )
        assert abs(actual / expected - 1.0) <= QUADRATURE_RTOL, (
            temperature,
            energy,
            actual,
            expected,
        )


@pytest.mark.parametrize(
    "call,cross_section,mass_amu,upper_ev",
    (
        (
            evaluate_atomic_hydrogen_charge_exchange_rate,
            evaluate_atomic_hydrogen_charge_exchange_cross_section,
            1.0,
            reference.COMPOSITE_UPPER_EV,
        ),
        (
            evaluate_hydrogen2_charge_exchange_rate,
            evaluate_molecular_hydrogen_charge_exchange_cross_section,
            2.0,
            2.01e4,
        ),
    ),
    ids=("atomic-cx", "molecular-cx"),
)
def test_the_fitted_rate_agrees_with_the_integral_of_its_cross_section(
    call, cross_section, mass_amu, upper_ev
):
    """The temperature/energy fit and the integral of the cross-section fit agree.

    These are two separate parameterizations of the same process, so this is
    cross-asset consistency at an order-of-magnitude band, and it is the check
    that pins which unit the fit is in: the integral is ``m^3/s`` by
    construction, so a ``cm^3/s``/``m^3/s`` slip lands at 0.1 or 10 and fails.
    """
    lower, upper = FIT_TO_INTEGRAL_BAND
    for temperature in (0.5, 1.0, 5.0, 20.0, 100.0, 1000.0):
        integral, discretization = reference.rate_from_cross_section(
            temperature, 1.0, cross_section, upper_ev, mass_amu=mass_amu
        )
        # The reference's own two-grid error is 4e-5 at worst, three orders below
        # the band this assertion uses, so it cannot be what makes the check pass.
        assert discretization < 1.0e-4, (temperature, discretization)
        fitted = float(np.ravel(call(np.asarray([temperature]), np.asarray([1.0])))[0])
        ratio = fitted / integral
        assert lower < ratio < upper, (temperature, ratio)
        low, high = RATE_BAND_M3_S
        assert low < fitted < high, fitted


@pytest.mark.parametrize("species,fit_name", (("H", "janev-h"), ("H2", "janev-h2")))
def test_the_ionization_rate_is_the_fit_times_the_exact_volume_rate_factor(species, fit_name):
    """``rate_m3_s = fit_cm3_s * 1e-6`` and the rate is in the m^3/s decade."""
    coefficients = reference.FROZEN_FITS[fit_name]["coefficients"]
    temperature = np.array([0.5, 1.0, 10.0, 100.0, 1.0e3])
    actual = np.asarray(evaluate_janev_electron_impact_ionization_rate(temperature, species))
    expected = (
        np.array(
            [
                float(np.ravel(reference.log_polynomial_value(math.log(value), coefficients))[0])
                for value in temperature
            ]
        )
        * reference.CM3_S_TO_M3_S
    )
    np.testing.assert_allclose(actual, expected, rtol=SAME_FORMULA_RTOL, atol=0.0)
    # The Janev fit spans many decades at low temperature (2e-29 m^3/s at 0.5 eV),
    # so the guard is positivity plus a decade band only where the rate is large:
    # a returned zero, a returned input or a ten-fold unit slip all leave it.
    assert np.all(actual > 0.0) and np.all(np.isfinite(actual))
    upper_half = actual[temperature >= 10.0]
    low, high = RATE_BAND_M3_S
    assert np.all(upper_half > low) and np.all(upper_half < high)


@pytest.mark.parametrize("species,fit_name", (("H", "janev-h"), ("H2", "janev-h2")))
def test_the_ionization_log_slope_is_the_analytic_derivative(species, fit_name):
    """The Janev fit's measured log-slope equals its analytic derivative."""
    coefficients = reference.FROZEN_FITS[fit_name]["coefficients"]
    for temperature in (1.0, 30.0, 300.0, 3.0e3, 1.5e4):
        predicted = float(np.ravel(reference.log_slope(math.log(temperature), coefficients))[0])
        measured = _finite_difference_slope(
            lambda value: evaluate_janev_electron_impact_ionization_rate(
                np.asarray([value]), species
            ),
            temperature,
        )
        assert abs(predicted - measured) <= SLOPE_BUDGET * max(1.0, abs(predicted)), (
            temperature,
            predicted,
            measured,
        )


def test_the_frozen_constants_are_inside_the_declared_codata_budget():
    """The two frozen constants differ from CODATA by 3.6e-3 in the thermal speed.

    Both rate contracts are built on constants frozen to their source rather than
    on CODATA.  The agreement budget for those rates therefore cannot be tighter
    than the constant difference, and this records the number instead of leaving
    it implicit.
    """
    for temperature in (1.0, 2.0e4):
        frozen = reference.frozen_thermal_speed(temperature)
        codata = reference.codata_thermal_speed(temperature)
        assert abs(codata / frozen - 1.0) <= 5.0e-3
