"""AUDIT-B3 cross-family evidence for the rate coefficients and Saha.

The B3 audit found that four rate fits (radiative recombination, atomic/molecular
charge exchange, Janev ionization) and the Saha population had no independently
re-runnable check beyond their own formulas.  These tests add the evidence that
can be established inside this repository without inventing experimental truth:

* Saha against the standard CODATA Saha prefactor, with the frozen-constant
  tolerance documented in the asset contract;
* the analytic low/high-temperature asymptotics of the radiative-recombination
  fit;
* endpoint-clipping and invalid-input consistency across the four rate fits;
* the Maxwellian average of the separately exposed charge-exchange cross section
  against the charge-exchange rate fits;
* the Janev peak location and high-temperature slope envelope.

None of these is an experimental validation.  They are mathematical or
cross-asset consistency evidence and are labelled as such in the report.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import constants

from scirel.collisions import (
    average_cross_section_over_maxwellian,
    evaluate_atomic_hydrogen_1s_radiative_recombination_rate,
    evaluate_atomic_hydrogen_charge_exchange_cross_section,
    evaluate_atomic_hydrogen_charge_exchange_rate,
    evaluate_atomic_hydrogen_elastic_cross_section,
    evaluate_hydrogen_h2_elastic_cross_section,
    evaluate_hydrogen_proton_elastic_cross_section,
    evaluate_hydrogen2_charge_exchange_rate,
    evaluate_hydrogen2_hydrogen2_elastic_cross_section,
    evaluate_hydrogen2_proton_elastic_cross_section,
    evaluate_janev_electron_impact_ionization_rate,
    evaluate_molecular_hydrogen_charge_exchange_cross_section,
)
from scirel.kinetic import (
    evaluate_h_saha_equilibrium_population,
    make_cylindrical_velocity_quadrature,
)


def _codata_saha_population(density, temperature, level):
    """Standard Saha level population with U_ion = 1, g_n = 2 n^2.

    ``n_H+ = n_e`` and ``T`` in eV, matching the declaration of the frozen
    relation; the prefactor is evaluated from CODATA constants rather than from
    the asset's stored constant.
    """
    prefactor = (constants.h**2 / (2.0 * np.pi * constants.m_e * constants.e)) ** 1.5
    level_squared = float(level * level)
    return (
        density**2
        * prefactor
        * level_squared
        * np.exp(13.605693 / (level_squared * temperature))
        / temperature**1.5
    )


@pytest.mark.parametrize("level", [1, 2, 3])
def test_saha_matches_the_codata_relation(level):
    """The frozen relation is the standard Saha formula to the stored constants.

    The frozen constants (3.310e-28 m^3 eV^(3/2) and 13.6057 eV) differ from
    CODATA by at most 0.09 %, so the declared tolerance is 1.5e-3.
    """
    density = np.array([1.0e16, 1.0e18, 1.0e20])
    temperature = np.array([0.5, 1.0, 5.0])
    actual = evaluate_h_saha_equilibrium_population(density, temperature, level)
    expected = _codata_saha_population(density, temperature, level)
    np.testing.assert_allclose(actual, expected, rtol=1.5e-3, atol=0.0)


def test_radiative_recombination_analytic_asymptotic_slopes():
    """Low-T and high-T log slopes approach the analytic -1/2 and -3/2 limits."""
    temperature = np.geomspace(0.1, 2.01e4, 400)
    rate = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)

    def slope(low, high):
        index = np.searchsorted(temperature, [low, high])
        return float(
            (np.log(rate[index[1]]) - np.log(rate[index[0]]))
            / (np.log(temperature[index[1]]) - np.log(temperature[index[0]]))
        )

    assert -0.52 <= slope(0.15, 0.45) <= -0.49
    assert -1.52 <= slope(1.0e3, 1.8e4) <= -1.46


def test_janev_peak_and_high_temperature_slope():
    temperature = np.geomspace(0.1, 2.01e4, 400)
    for species, peak_range, slope_range in (
        ("H", (120.0, 160.0), (-0.60, -0.35)),
        ("H2", (135.0, 175.0), (-0.60, -0.35)),
    ):
        rate = evaluate_janev_electron_impact_ionization_rate(temperature, species)
        peak = float(temperature[int(np.argmax(rate))])
        assert peak_range[0] <= peak <= peak_range[1], (species, peak)
        high_slope = float(
            (np.log(rate[-1]) - np.log(rate[-20]))
            / (np.log(temperature[-1]) - np.log(temperature[-20]))
        )
        assert slope_range[0] <= high_slope <= slope_range[1], (species, high_slope)


RATE_CASES = (
    (
        "recombination",
        lambda value: evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.asarray([value])),
        0.1,
        2.01e4,
    ),
    (
        "atomic-cx",
        lambda value: evaluate_atomic_hydrogen_charge_exchange_rate(
            np.asarray([value]), np.asarray([1.0])
        ),
        0.1,
        2.5e5,
    ),
    (
        "molecular-cx",
        lambda value: evaluate_hydrogen2_charge_exchange_rate(
            np.asarray([value]), np.asarray([1.0])
        ),
        0.1,
        2.01e4,
    ),
    (
        "janev",
        lambda value: evaluate_janev_electron_impact_ionization_rate(np.asarray([value]), "H"),
        0.1,
        2.01e4,
    ),
)


@pytest.mark.parametrize("label,call,lower_limit,upper_limit", RATE_CASES)
def test_rate_family_positive_out_of_range_inputs_clip_to_endpoints(
    label, call, lower_limit, upper_limit
):
    """Positive out-of-range values repeat declared endpoints, with warnings above."""
    clipped = call(lower_limit * 0.1)
    lower = call(lower_limit)
    upper_clipped = call(upper_limit * 2.0)
    upper = call(upper_limit)
    assert clipped == lower
    assert upper_clipped == upper


@pytest.mark.parametrize("label,call,lower_limit,upper_limit", RATE_CASES)
@pytest.mark.parametrize("bad", [np.nan, np.inf, -1.0, 0.0, True, "1.0"])
def test_rate_family_invalid_inputs_fail_closed(label, call, lower_limit, upper_limit, bad):
    with pytest.raises(ValueError):
        call(bad)


@pytest.mark.parametrize(
    "cross_section,molecular",
    (
        (evaluate_atomic_hydrogen_charge_exchange_cross_section, False),
        (evaluate_molecular_hydrogen_charge_exchange_cross_section, True),
    ),
)
def test_cx_cross_section_average_is_consistent_with_rate_fit(
    cross_section,
    molecular,
):
    """Maxwellian-averaged cross section agrees with the separately fitted rate.

    This is cross-asset implementation consistency, not external physical truth:
    both capabilities fit the same charge-exchange data but through separate
    declarations (cross section versus temperature/energy rate fit).
    """
    vr = np.linspace(0.0, 4.0, 40)
    vx = np.linspace(-4.0, 4.0, 60)
    volume = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)["volume"]
    mass_amu = 2.0 if molecular else 1.0
    rate_fit = (
        evaluate_hydrogen2_charge_exchange_rate
        if molecular
        else (evaluate_atomic_hydrogen_charge_exchange_rate)
    )
    energies = np.array([1.0, 5.0, 20.0, 100.0, 500.0])
    for temperature in (1.0, 5.0, 20.0):
        averaged = average_cross_section_over_maxwellian(
            particle_energy_ev=energies,
            particle_mass_amu=mass_amu,
            target_temperature_ev=temperature,
            target_mass_amu=mass_amu,
            vx=vx,
            vr=vr,
            tnorm_ev=temperature,
            cylindrical_volume=volume,
            cross_section_m2=cross_section,
        )
        fitted = rate_fit(np.full(energies.shape, temperature), energies)
        ratio = np.asarray(averaged) / np.asarray(fitted)
        assert np.all((ratio > 0.95) & (ratio < 1.05)), (
            "temperature",
            temperature,
            "ratio",
            ratio,
        )


CROSS_SECTION_CASES = (
    (
        "atomic-cx-composite",
        evaluate_atomic_hydrogen_charge_exchange_cross_section,
        0.1,
        2.5e5,
    ),
    ("atomic-h-elastic", evaluate_atomic_hydrogen_elastic_cross_section, 0.03, 1.01e4),
    ("h-h2-elastic", evaluate_hydrogen_h2_elastic_cross_section, 0.03, 1.01e4),
    ("h2-h2-elastic", evaluate_hydrogen2_hydrogen2_elastic_cross_section, 0.03, 1.01e4),
    ("h2-h+-elastic", evaluate_hydrogen2_proton_elastic_cross_section, 0.03, 1.01e4),
    ("h+-h-elastic", evaluate_hydrogen_proton_elastic_cross_section, 0.001, 1.01e5),
    ("molecular-cx", evaluate_molecular_hydrogen_charge_exchange_cross_section, 0.1, 2.01e4),
)


@pytest.mark.parametrize("label,call,lower,upper", CROSS_SECTION_CASES)
def test_cross_section_positive_out_of_range_clips_to_endpoints(label, call, lower, upper):
    """Positive out-of-range energies repeat endpoints and warn above the upper edge."""
    below = call(lower * 0.5)
    at_lower = call(lower)
    above = call(upper * 2.0)
    at_upper = call(upper)
    assert np.array_equal(np.ravel(below), np.ravel(at_lower))
    assert np.array_equal(np.ravel(above), np.ravel(at_upper))
    with pytest.raises(ValueError):
        call(-1.0)


@pytest.mark.parametrize(
    "call,upper",
    [
        (evaluate_hydrogen_h2_elastic_cross_section, 1.01e4),
        (evaluate_hydrogen2_hydrogen2_elastic_cross_section, 1.01e4),
        (evaluate_hydrogen2_proton_elastic_cross_section, 1.01e4),
        (evaluate_molecular_hydrogen_charge_exchange_cross_section, 2.01e4),
    ],
)
def test_selected_upper_fit_limits_warn_before_endpoint_clipping(call, upper):
    with pytest.warns(RuntimeWarning, match="upper limit"):
        above = call(np.asarray([2.0 * upper]))
    edge = call(np.asarray([upper]))
    np.testing.assert_array_equal(above, edge)


@pytest.mark.parametrize(
    "call,upper,args",
    [
        (
            evaluate_hydrogen2_charge_exchange_rate,
            2.01e4,
            (np.asarray([1.0]), np.asarray([2.0 * 2.01e4])),
        ),
        (
            evaluate_janev_electron_impact_ionization_rate,
            2.01e4,
            (np.asarray([2.0 * 2.01e4]), "H"),
        ),
    ],
)
def test_selected_upper_rate_limits_warn_before_endpoint_clipping(call, upper, args):
    with pytest.warns(RuntimeWarning, match="upper limit"):
        above = call(*args)
    if call is evaluate_hydrogen2_charge_exchange_rate:
        edge = call(np.asarray([1.0]), np.asarray([upper]))
    else:
        edge = call(np.asarray([upper]), "H")
    np.testing.assert_array_equal(above, edge)
