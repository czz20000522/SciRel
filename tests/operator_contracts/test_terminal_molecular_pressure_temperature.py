"""Contract tests for the terminal H2 pressure and temperature variant."""

import numpy as np
import pytest

from scirel.kinetic import reduce_axisymmetric_neutral_moments
from scirel.kinetic import reduce_terminal_molecular_pressure_temperature


def _case():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 2.0])
    distribution = np.array(
        [[[1.0, 0.5], [2.0, 1.0], [3.0, 2.0]],
         [[0.5, 2.0], [1.0, 3.0], [1.5, 4.0]]]
    )
    return vr, vx, 1.0, 5000.0, distribution, np.array([1.0, 2.0]), np.array([0.5, 1.0, 0.25])


def test_pressure_and_temperature_match_independent_centered_moment():
    vr, vx, mass, speed, f, radial_weight, widths = _case()
    result = reduce_terminal_molecular_pressure_temperature(
        vr, vx, mass, speed, f, radial_weight, widths
    )
    expected_density = []
    expected_pressure = []
    for k in range(f.shape[2]):
        density = sum(radial_weight[i] * widths[j] * f[i, j, k]
                      for i in range(vr.size) for j in range(vx.size))
        mean = speed * sum(radial_weight[i] * widths[j] * vx[j] * f[i, j, k]
                           for i in range(vr.size) for j in range(vx.size)) / density
        centered = sum(radial_weight[i] * widths[j] * f[i, j, k]
                       * (vr[i] ** 2 + (vx[j] - mean / speed) ** 2)
                       for i in range(vr.size) for j in range(vx.size))
        expected_density.append(density)
        expected_pressure.append(
            2.0 * mass * 1.6726231e-27 * speed ** 2 * centered
            / (3.0 * 1.602177e-19)
        )
    assert set(result) == {"pressure_profile_ev_m3", "temperature_profile_ev"}
    np.testing.assert_allclose(result["pressure_profile_ev_m3"], expected_pressure, rtol=1e-15)
    np.testing.assert_allclose(result["temperature_profile_ev"],
                               np.array(expected_pressure) / expected_density, rtol=1e-15)


def test_positive_weight_intersection_matches_nine_moment_relation():
    vr, vx, mass, _, f, radial_weight, widths = _case()
    temperature_ev = 2.0
    speed = np.sqrt(2.0 * 1.602177e-19 * temperature_ev / (mass * 1.6726231e-27))
    result = reduce_terminal_molecular_pressure_temperature(
        vr, vx, mass, speed, f, radial_weight, widths
    )
    moments = reduce_axisymmetric_neutral_moments(
        f, vx, vr, radial_weight[:, None] * widths[None, :],
        temperature_ev, mass, 2, axial_quadrature=widths,
        radial_quadrature=radial_weight,
    )
    np.testing.assert_allclose(result["pressure_profile_ev_m3"],
                               moments["pressure_ev_m3"], rtol=1e-15)
    np.testing.assert_allclose(result["temperature_profile_ev"],
                               moments["temperature_ev"], rtol=1e-15)


def test_zero_weight_cells_are_allowed_with_positive_density():
    vr, vx, mass, speed, f, radial_weight, widths = _case()
    radial_weight[0] = 0.0
    widths[1] = 0.0
    result = reduce_terminal_molecular_pressure_temperature(
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
        reduce_terminal_molecular_pressure_temperature(*arguments)


def test_zero_density_and_nonfinite_pressure_fail_closed():
    vr, vx, mass, speed, f, radial_weight, widths = _case()
    one_empty_slice = f.copy()
    one_empty_slice[:, :, 1] = 0.0
    with pytest.raises(ValueError, match="strictly positive density"):
        reduce_terminal_molecular_pressure_temperature(
            vr, vx, mass, speed, one_empty_slice, radial_weight, widths
        )
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="invalid pressure"):
            reduce_terminal_molecular_pressure_temperature(
                vr, vx, mass, np.finfo(float).max, f, radial_weight, widths
            )
