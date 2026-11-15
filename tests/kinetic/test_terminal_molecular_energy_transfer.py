"""Contract tests for terminal H2 loss, momentum and energy-transfer rates."""

from fractions import Fraction

import numpy as np
import pytest

from scirel.neutrals import (
    assemble_neutral_boltzmann_rhs,
    reduce_terminal_molecular_energy_transfer,
)


@pytest.mark.parametrize("rhs_value", [-1.0, 1.0])
@pytest.mark.parametrize("external_source", [0.0, -1e20, 1e20])
def test_large_external_source_cannot_erase_the_lab_frame_energy(rhs_value, external_source):
    # A unit-speed monokinetic stream has lab energy source m/2 * RHS,
    # independently of the external-source bookkeeping and mean-flow split.
    f = np.ones((1, 1, 1))
    result = reduce_terminal_molecular_energy_transfer(
        [0.0], [1.0], 1.0, 1.0, f, rhs_value * f, [1.0], [1.0], [external_source]
    )
    expected = float(Fraction.from_float(1.6726231e-27) * Fraction.from_float(rhs_value))
    np.testing.assert_allclose(
        result["total_energy_transfer_rate_profile_w_m3"], [expected], rtol=1e-14, atol=1e-28
    )


def _case():
    vr = np.array([0.25, 0.75])
    vx = np.array([-1.0, 0.25, 1.5])
    f = np.array([[[1.0, 0.8], [0.6, 0.5], [0.3, 0.2]], [[0.7, 0.6], [0.5, 0.4], [0.2, 0.1]]])
    rhs = np.array(
        [[[0.2, -0.1], [-0.3, 0.4], [0.1, 0.2]], [[-0.2, 0.3], [0.5, -0.4], [-0.1, 0.1]]]
    )
    return (
        vr,
        vx,
        1.5,
        2.2e4,
        f,
        rhs,
        np.array([0.4, 0.9]),
        np.array([0.3, 0.5, 0.8]),
        np.array([0.05, -0.08]),
    )


@pytest.mark.parametrize("density_scale", [1.0, 2.0**40])
def test_physical_rhs_carries_centered_force_per_volume(density_scale):
    """F/s plus a density measure yields N/m^3, and velocity restores W/m^3."""
    distribution = density_scale * np.array([[[1.0], [3.0]]])
    zero = np.zeros_like(distribution)
    rhs = assemble_neutral_boltzmann_rhs(
        2.0,
        zero,
        zero,
        np.array([[[1.0], [0.0]]]),
        distribution,
        zero,
        zero,
    )["rhs"]
    np.testing.assert_array_equal(rhs, density_scale * np.array([[[-2.0], [0.0]]]))
    result = reduce_terminal_molecular_energy_transfer(
        [0.0], [-1.0, 1.0], 1.0, 2.0, distribution, rhs, [1.0], [1.0, 1.0], [0.0]
    )
    # Independent two-cell relation: density=4s, U=1 m/s, J=-2s.
    # Momentum is centered: 6*m*s, rather than laboratory momentum 4*m*s.
    molecule_mass = 2.0 * 1.6726231e-27
    factor = molecule_mass * density_scale
    np.testing.assert_allclose(
        result["momentum_transfer_rate_profile_n_m3"], [6.0 * factor], rtol=1e-14, atol=0.0
    )
    np.testing.assert_allclose(
        result["loss_rate_profile_m3_s"], [2.0 * density_scale], rtol=1e-14, atol=0.0
    )
    np.testing.assert_allclose(
        result["thermal_energy_transfer_rate_profile_w_m3"], [-9.0 * factor], rtol=1e-14, atol=0.0
    )
    np.testing.assert_allclose(
        result["total_energy_transfer_rate_profile_w_m3"], [-4.0 * factor], rtol=1e-14, atol=0.0
    )


def test_four_profiles_match_independent_centered_and_raw_rhs_moments():
    vr, vx, mass, speed, f, rhs, radial_weight, widths, external_source = _case()
    result = reduce_terminal_molecular_energy_transfer(
        vr, vx, mass, speed, f, rhs, radial_weight, widths, external_source
    )
    molecule_mass = 2.0 * mass * 1.6726231e-27
    expected_loss = []
    expected_thermal = []
    expected_momentum = []
    expected_total = []
    for k in range(f.shape[2]):
        cells = [(i, j) for i in range(vr.size) for j in range(vx.size)]
        density = sum(radial_weight[i] * widths[j] * f[i, j, k] for i, j in cells)
        normalized_flow = (
            sum(radial_weight[i] * widths[j] * vx[j] * f[i, j, k] for i, j in cells) / density
        )
        expected_loss.append(
            external_source[k] - sum(radial_weight[i] * widths[j] * rhs[i, j, k] for i, j in cells)
        )
        expected_thermal.append(
            0.5
            * molecule_mass
            * speed**2
            * sum(
                radial_weight[i]
                * widths[j]
                * rhs[i, j, k]
                * (vr[i] ** 2 + (vx[j] - normalized_flow) ** 2)
                for i, j in cells
            )
        )
        expected_momentum.append(
            molecule_mass
            * speed
            * sum(
                radial_weight[i] * widths[j] * rhs[i, j, k] * (vx[j] - normalized_flow)
                for i, j in cells
            )
        )
        expected_total.append(
            0.5
            * molecule_mass
            * speed**2
            * sum(
                radial_weight[i] * widths[j] * rhs[i, j, k] * (vr[i] ** 2 + vx[j] ** 2)
                for i, j in cells
            )
        )
    assert set(result) == {
        "loss_rate_profile_m3_s",
        "thermal_energy_transfer_rate_profile_w_m3",
        "momentum_transfer_rate_profile_n_m3",
        "total_energy_transfer_rate_profile_w_m3",
    }
    np.testing.assert_allclose(
        result["loss_rate_profile_m3_s"], expected_loss, rtol=1e-14, atol=1e-15
    )
    for key, expected in (
        ("thermal_energy_transfer_rate_profile_w_m3", expected_thermal),
        ("momentum_transfer_rate_profile_n_m3", expected_momentum),
        ("total_energy_transfer_rate_profile_w_m3", expected_total),
    ):
        np.testing.assert_allclose(result[key], expected, rtol=1e-14, atol=1e-28)


def test_external_source_changes_loss_only():
    arguments = list(_case())
    baseline = reduce_terminal_molecular_energy_transfer(*arguments)
    delta = np.array([0.2, -0.3])
    arguments[-1] = arguments[-1] + delta
    changed = reduce_terminal_molecular_energy_transfer(*arguments)
    np.testing.assert_allclose(
        changed["loss_rate_profile_m3_s"] - baseline["loss_rate_profile_m3_s"],
        delta,
        rtol=1e-15,
        atol=1e-15,
    )
    for key in set(baseline) - {"loss_rate_profile_m3_s"}:
        np.testing.assert_array_equal(changed[key], baseline[key])


def test_zero_quadrature_cells_allow_signed_rhs_when_density_stays_positive():
    arguments = list(_case())
    arguments[6] = np.array([0.0, 0.9])
    arguments[7] = np.array([0.3, 0.0, 0.8])
    result = reduce_terminal_molecular_energy_transfer(*arguments)
    assert all(np.isfinite(profile).all() for profile in result.values())


@pytest.mark.parametrize(
    "index,value",
    [
        (0, np.array([True, False])),
        (1, np.array(["-1", "0.25", "1.5"])),
        (2, True),
        (3, "22000"),
        (4, np.ones((2, 3, 2), dtype=bool)),
        (5, np.ones((2, 3, 2), dtype=complex)),
        (6, np.array([True, True])),
        (7, np.array([True, True, True])),
        (8, np.array(["0.05", "-0.08"])),
    ],
)
def test_nonreal_or_nonnumeric_inputs_fail_closed(index, value):
    arguments = list(_case())
    arguments[index] = value
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_energy_transfer(*arguments)


def test_empty_spatial_slice_and_nonfinite_output_fail_closed():
    arguments = list(_case())
    one_empty_slice = arguments[4].copy()
    one_empty_slice[:, :, 1] = 0.0
    arguments[4] = one_empty_slice
    with pytest.raises(ValueError, match="strictly positive density"):
        reduce_terminal_molecular_energy_transfer(*arguments)
    arguments = list(_case())
    arguments[3] = np.finfo(float).max
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="non-finite profile"):
            reduce_terminal_molecular_energy_transfer(*arguments)
