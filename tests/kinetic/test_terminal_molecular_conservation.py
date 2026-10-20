"""Contract tests for the terminal H2 total-energy conservation diagnostic."""

import numpy as np
import pytest

from scirel.kinetic import (
    reduce_qh2_total_conservation_diagnostic,
    reduce_terminal_molecular_energy_transfer,
    reduce_terminal_molecular_heat_flux,
)


def test_signed_nonuniform_profiles_match_independent_cell_residuals():
    x = np.array([0.0, 0.02, 0.05, 0.08])
    flux = np.array([10.0, 8.0, 5.0, 4.0])
    transfer = np.array([90.0, 70.0, 40.0, 20.0])
    expected = np.array([1.8, 1.55, 19.0 / 30.0, 0.0])

    result = reduce_qh2_total_conservation_diagnostic(x, flux, transfer)

    assert set(result) == {"total_energy_conservation_error_profile_dimensionless"}
    np.testing.assert_allclose(
        result["total_energy_conservation_error_profile_dimensionless"],
        expected, rtol=1e-14, atol=1e-15,
    )


def test_linear_flux_and_matching_transfer_have_zero_error_on_decreasing_grid():
    x = np.array([2.0, 0.5, -1.0])
    flux = 3.0 * x - 5.0
    result = reduce_qh2_total_conservation_diagnostic(
        x, flux, np.array([3.0, 3.0, 3.0])
    )
    np.testing.assert_array_equal(
        result["total_energy_conservation_error_profile_dimensionless"],
        np.zeros(3),
    )


def test_local_nonmonotonic_grid_and_signed_source_are_supported():
    result = reduce_qh2_total_conservation_diagnostic(
        [0.0, 2.0, 1.0], [0.0, -4.0, -2.0], [-2.0, -2.0, -2.0]
    )
    np.testing.assert_array_equal(
        result["total_energy_conservation_error_profile_dimensionless"],
        np.zeros(3),
    )


def test_existing_total_profiles_compose_on_the_same_axial_mesh():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.5, 2.0])
    distribution = np.ones((2, 3, 3))
    weight = np.array([1.0, 2.0])
    widths = np.array([0.25, 0.5, 0.75])
    heat = reduce_terminal_molecular_heat_flux(
        vr, vx, 1.0, 5000.0, distribution, weight, widths
    )
    transfer = reduce_terminal_molecular_energy_transfer(
        vr, vx, 1.0, 5000.0, distribution,
        np.ones_like(distribution), weight, widths, np.zeros(3),
    )

    result = reduce_qh2_total_conservation_diagnostic(
        np.array([0.0, 0.5, 1.0]),
        heat["total_heat_flux_profile_w_m2"],
        transfer["total_energy_transfer_rate_profile_w_m3"],
    )
    np.testing.assert_allclose(
        result["total_energy_conservation_error_profile_dimensionless"],
        [1.0, 1.0, 0.0], rtol=1e-15, atol=1e-15,
    )


@pytest.mark.parametrize("arguments", [
    ([0.0], [1.0], [1.0]),
    ([0.0, 1.0], [1.0], [1.0, 2.0]),
    ([0.0, 0.0], [1.0, 2.0], [1.0, 2.0]),
    ([0.0, 1.0], [np.nan, 2.0], [1.0, 2.0]),
    ([0.0, 1.0], [1.0, 2.0], [np.inf, 2.0]),
])
def test_invalid_profile_or_spacing_fails_closed(arguments):
    with pytest.raises(ValueError):
        reduce_qh2_total_conservation_diagnostic(*arguments)


def test_zero_global_normalization_fails_closed():
    with pytest.raises(ValueError, match="strictly positive global normalization"):
        reduce_qh2_total_conservation_diagnostic([0.0, 1.0], [1.0, 1.0], [0.0, 0.0])


@pytest.mark.parametrize("index,value", [
    (0, [False, True]),
    (1, ["1", "2"]),
    (2, np.array([1.0 + 0j, 2.0 + 0j])),
])
def test_nonreal_or_nonnumeric_input_fails_closed(index, value):
    arguments = [[0.0, 1.0], [1.0, 2.0], [1.0, 2.0]]
    arguments[index] = value
    with pytest.raises(ValueError, match="real numeric"):
        reduce_qh2_total_conservation_diagnostic(*arguments)


def test_nonfinite_derived_gradient_fails_closed():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="non-finite"):
            reduce_qh2_total_conservation_diagnostic(
                [0.0, 1e-300], [0.0, 1e300], [1.0, 1.0]
            )
