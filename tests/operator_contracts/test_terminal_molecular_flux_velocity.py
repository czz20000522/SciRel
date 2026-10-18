"""Contract tests for the terminal H2 axial flux and velocity variant."""

import numpy as np
import pytest

from scirel.kinetic import reduce_axisymmetric_neutral_moments
from scirel.kinetic import reduce_terminal_molecular_flux_velocity


def _case():
    vx = np.array([-1.0, 0.0, 2.0])
    radial_weight = np.array([1.0, 2.0])
    axial_width = np.array([0.5, 1.0, 0.25])
    distribution = np.array(
        [[[1.0, 0.5], [2.0, 1.0], [3.0, 2.0]],
         [[0.5, 2.0], [1.0, 3.0], [1.5, 4.0]]]
    )
    return vx, 5000.0, distribution, radial_weight, axial_width


def test_flux_and_flow_match_independent_cell_reduction():
    vx, vth, f, radial_weight, axial_width = _case()
    result = reduce_terminal_molecular_flux_velocity(vx, vth, f, radial_weight, axial_width)
    expected_density = np.array([
        sum(radial_weight[i] * sum(f[i, j, k] * axial_width[j]
                                       for j in range(vx.size))
            for i in range(radial_weight.size))
        for k in range(f.shape[2])
    ])
    expected_flux = np.array([
        vth * sum(radial_weight[i] * sum(vx[j] * f[i, j, k] * axial_width[j]
                                            for j in range(vx.size))
                  for i in range(radial_weight.size))
        for k in range(f.shape[2])
    ])
    assert set(result) == {"flux_profile_m2_s", "mean_velocity_profile_m_s"}
    np.testing.assert_allclose(result["flux_profile_m2_s"], expected_flux, rtol=1e-15)
    np.testing.assert_allclose(result["mean_velocity_profile_m_s"],
                               expected_flux / expected_density, rtol=1e-15)


def test_common_positive_weight_domain_agrees_with_existing_moment_relation():
    vx, _, f, radial_weight, axial_width = _case()
    temperature_ev = 2.0
    vth = np.sqrt(2.0 * 1.602177e-19 * temperature_ev / 1.6726231e-27)
    terminal = reduce_terminal_molecular_flux_velocity(vx, vth, f, radial_weight, axial_width)
    moments = reduce_axisymmetric_neutral_moments(
        f, vx, np.array([0.5, 1.0]), radial_weight[:, None] * axial_width[None, :],
        temperature_ev, 1.0, 2, axial_quadrature=axial_width,
        radial_quadrature=radial_weight,
    )
    np.testing.assert_allclose(terminal["flux_profile_m2_s"],
                               moments["axial_flux_m2_s"], rtol=1e-15)
    np.testing.assert_allclose(terminal["mean_velocity_profile_m_s"],
                               moments["axial_velocity_m_s"], rtol=1e-15)


def test_zero_weight_cells_are_allowed_when_density_stays_positive():
    vx, vth, f, radial_weight, axial_width = _case()
    radial_weight[0] = 0.0
    axial_width[1] = 0.0
    result = reduce_terminal_molecular_flux_velocity(vx, vth, f, radial_weight, axial_width)
    assert np.all(np.isfinite(result["mean_velocity_profile_m_s"]))
    with pytest.raises(ValueError, match="quadrature|contract"):
        reduce_axisymmetric_neutral_moments(
            f, vx, np.array([0.5, 1.0]),
            radial_weight[:, None] * axial_width[None, :], 2.0, 1.0, 2,
            axial_quadrature=axial_width, radial_quadrature=radial_weight,
        )


def test_spatial_batch_reduction_preserves_per_slice_float64_results():
    rng = np.random.default_rng(20261019)
    shape = (7, 11, 17)
    vx = rng.normal(size=shape[1])
    radial_weight = rng.lognormal(mean=0.0, sigma=2.0, size=shape[0])
    axial_width = rng.lognormal(mean=-1.0, sigma=1.5, size=shape[1])
    distribution = rng.lognormal(mean=0.0, sigma=4.0, size=shape)
    radial_weight[0] = 0.0
    axial_width[3] = 0.0
    thermal_speed = 3.7e4

    expected_density = np.zeros(shape[2], dtype=float)
    expected_flux = np.zeros(shape[2], dtype=float)
    for k in range(shape[2]):
        expected_density[k] = np.sum(
            radial_weight * (distribution[:, :, k] @ axial_width)
        )
        expected_flux[k] = thermal_speed * np.sum(
            radial_weight * (distribution[:, :, k] @ (vx * axial_width))
        )

    result = reduce_terminal_molecular_flux_velocity(
        vx, thermal_speed, distribution, radial_weight, axial_width
    )
    np.testing.assert_array_equal(result["flux_profile_m2_s"], expected_flux)
    np.testing.assert_array_equal(
        result["mean_velocity_profile_m_s"], expected_flux / expected_density
    )


@pytest.mark.parametrize("argument_index,value", [
    (0, np.array([True, False, True])),
    (1, True),
    (2, np.ones((2, 3, 2), dtype=bool)),
    (3, np.array(["1", "2"])),
    (4, np.array([1.0, 1.0, 1.0], dtype=complex)),
])
def test_nonreal_or_nonnumeric_inputs_fail_closed(argument_index, value):
    arguments = list(_case())
    arguments[argument_index] = value
    with pytest.raises(ValueError, match="real numeric"):
        reduce_terminal_molecular_flux_velocity(*arguments)


def test_zero_density_and_nonfinite_result_fail_closed():
    vx, vth, f, radial_weight, axial_width = _case()
    with pytest.raises(ValueError, match="strictly positive density"):
        reduce_terminal_molecular_flux_velocity(vx, vth, np.zeros_like(f),
                                                radial_weight, axial_width)
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="nonfinite flux"):
            reduce_terminal_molecular_flux_velocity(
                vx, np.finfo(float).max, f, radial_weight, axial_width
            )
