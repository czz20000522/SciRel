"""Contract tests for terminal H2 random and total heat flux."""

import numpy as np
import pytest

from scirel.kinetic import reduce_axisymmetric_neutral_moments
from scirel.kinetic import reduce_terminal_molecular_heat_flux


def _case():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 2.0])
    distribution = np.array(
        [[[1.0, 0.5], [2.0, 1.0], [3.0, 2.0]],
         [[0.5, 2.0], [1.0, 3.0], [1.5, 4.0]]]
    )
    return vr, vx, 1.0, 5000.0, distribution, np.array([1.0, 2.0]), np.array([0.5, 1.0, 0.25])


def _pre_cache_reference(vr, vx, mass, speed, distribution, radial_weight, widths):
    """Evaluate the pre-cache slice reductions with the original order."""
    nx = distribution.shape[2]
    molecule_mass = 2.0 * mass * 1.6726231e-27
    density = np.zeros(nx, dtype=float)
    particle_flux = np.zeros(nx, dtype=float)
    for k in range(nx):
        density[k] = np.sum(radial_weight * (distribution[:, :, k] @ widths))
        particle_flux[k] = speed * np.sum(
            radial_weight * (distribution[:, :, k] @ (vx * widths))
        )
    mean_velocity = particle_flux / density
    normalized_mean_velocity = mean_velocity / speed
    random_velocity_squared = vr[:, None, None] ** 2 + (
        vx[None, :, None] - normalized_mean_velocity[None, None, :]
    ) ** 2
    pressure = np.zeros(nx, dtype=float)
    longitudinal_stress = np.zeros(nx, dtype=float)
    random_heat_flux = np.zeros(nx, dtype=float)
    thermal_squared = speed * speed
    thermal_cubed = thermal_squared * speed
    for k in range(nx):
        weighted_random_second = np.sum(
            radial_weight
            * ((random_velocity_squared[:, :, k] * distribution[:, :, k]) @ widths)
        )
        pressure[k] = molecule_mass * thermal_squared * weighted_random_second / (
            3.0 * 1.602177e-19
        )
        weighted_axial_second = np.sum(
            radial_weight
            * (
                distribution[:, :, k]
                @ (widths * (vx - normalized_mean_velocity[k]) ** 2)
            )
        )
        longitudinal_stress[k] = (
            molecule_mass * thermal_squared * weighted_axial_second / 1.602177e-19
        ) - pressure[k]
        random_heat_flux[k] = 0.5 * molecule_mass * thermal_cubed * np.sum(
            radial_weight
            * (
                (random_velocity_squared[:, :, k] * distribution[:, :, k])
                @ (widths * (vx - normalized_mean_velocity[k]))
            )
        )
    total_heat_flux = (
        (0.5 * density * molecule_mass * mean_velocity * mean_velocity
         + 2.5 * pressure * 1.602177e-19)
        * mean_velocity
        + 1.602177e-19 * longitudinal_stress * mean_velocity
        + random_heat_flux
    )
    return random_heat_flux, total_heat_flux


def test_random_and_total_heat_flux_match_independent_cell_moments():
    vr, vx, mass, speed, f, radial_weight, widths = _case()
    result = reduce_terminal_molecular_heat_flux(
        vr, vx, mass, speed, f, radial_weight, widths
    )
    molecule_mass = 2.0 * mass * 1.6726231e-27
    expected_random = []
    expected_total = []
    for k in range(f.shape[2]):
        cells = [(i, j) for i in range(vr.size) for j in range(vx.size)]
        density = sum(radial_weight[i] * widths[j] * f[i, j, k] for i, j in cells)
        normalized_flow = (
            sum(radial_weight[i] * widths[j] * vx[j] * f[i, j, k] for i, j in cells)
            / density
        )
        expected_random.append(
            0.5 * molecule_mass * speed ** 3
            * sum(radial_weight[i] * widths[j] * f[i, j, k]
                  * (vr[i] ** 2 + (vx[j] - normalized_flow) ** 2)
                  * (vx[j] - normalized_flow) for i, j in cells)
        )
        expected_total.append(
            0.5 * molecule_mass * speed ** 3
            * sum(radial_weight[i] * widths[j] * f[i, j, k]
                  * (vr[i] ** 2 + vx[j] ** 2) * vx[j] for i, j in cells)
        )
    assert set(result) == {"random_heat_flux_profile_w_m2", "total_heat_flux_profile_w_m2"}
    np.testing.assert_allclose(result["random_heat_flux_profile_w_m2"],
                               expected_random, rtol=1e-14, atol=1e-30)
    np.testing.assert_allclose(result["total_heat_flux_profile_w_m2"],
                               expected_total, rtol=1e-14, atol=1e-30)


def test_slice_cache_preserves_pre_cache_bitwise_results():
    rng = np.random.default_rng(20261019)
    vr = np.array([0.0, 0.25, 1.5])
    vx = np.array([-2.0, -0.125, 0.75, 3.0])
    distribution = rng.random((vr.size, vx.size, 3)) * 1e4
    radial_weight = rng.random(vr.size)
    widths = rng.random(vx.size)
    speed = 2.75e4
    result = reduce_terminal_molecular_heat_flux(
        vr, vx, 0.75, speed, distribution, radial_weight, widths
    )
    expected_random, expected_total = _pre_cache_reference(
        vr, vx, 0.75, speed, distribution, radial_weight, widths
    )
    np.testing.assert_array_equal(result["random_heat_flux_profile_w_m2"], expected_random)
    np.testing.assert_array_equal(result["total_heat_flux_profile_w_m2"], expected_total)


def test_random_heat_flux_agrees_with_nine_moment_relation():
    vr, vx, mass, _, f, radial_weight, widths = _case()
    temperature_ev = 2.0
    speed = np.sqrt(2.0 * 1.602177e-19 * temperature_ev / (mass * 1.6726231e-27))
    result = reduce_terminal_molecular_heat_flux(
        vr, vx, mass, speed, f, radial_weight, widths
    )
    moments = reduce_axisymmetric_neutral_moments(
        f, vx, vr, radial_weight[:, None] * widths[None, :],
        temperature_ev, mass, 2, axial_quadrature=widths,
        radial_quadrature=radial_weight,
    )
    np.testing.assert_allclose(result["random_heat_flux_profile_w_m2"],
                               moments["random_heat_flux_w_m2"], rtol=1e-15, atol=0)


def test_zero_weight_cells_are_allowed_with_positive_density():
    vr, vx, mass, speed, f, radial_weight, widths = _case()
    radial_weight[0] = 0.0
    widths[1] = 0.0
    result = reduce_terminal_molecular_heat_flux(
        vr, vx, mass, speed, f, radial_weight, widths
    )
    assert all(np.isfinite(profile).all() for profile in result.values())
    with pytest.raises(ValueError, match="quadrature|contract"):
        reduce_axisymmetric_neutral_moments(
            f, vx, vr, radial_weight[:, None] * widths[None, :],
            2.0, mass, 2, axial_quadrature=widths,
            radial_quadrature=radial_weight,
        )


@pytest.mark.parametrize("index,value", [
    (0, np.array([True, False])),
    (1, np.array(["-1", "0", "2"])),
    (2, True),
    (3, "5000"),
    (4, np.ones((2, 3, 2), dtype=bool)),
    (5, np.array([1.0, 2.0], dtype=complex)),
    (6, np.array([True, True, True])),
])
def test_nonreal_or_nonnumeric_inputs_fail_closed(index, value):
    arguments = list(_case())
    arguments[index] = value
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_heat_flux(*arguments)


def test_empty_spatial_slice_and_nonfinite_output_fail_closed():
    vr, vx, mass, speed, f, radial_weight, widths = _case()
    one_empty_slice = f.copy()
    one_empty_slice[:, :, 1] = 0.0
    with pytest.raises(ValueError, match="strictly positive density"):
        reduce_terminal_molecular_heat_flux(
            vr, vx, mass, speed, one_empty_slice, radial_weight, widths
        )
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="non-finite profile"):
            reduce_terminal_molecular_heat_flux(
                vr, vx, mass, np.finfo(float).max, f, radial_weight, widths
            )
