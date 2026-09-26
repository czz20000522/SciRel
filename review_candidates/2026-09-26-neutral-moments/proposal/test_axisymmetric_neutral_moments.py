"""Direct contract tests for ``scirel.kinetic.reduce_axisymmetric_neutral_moments``.

The saved KN1DPy package (anchor ``KN1DPy/kinetic_h.py:1443-1605`` /
``kinetic_h2.py:1612-1801`` as recorded by the saved bundle's provenance) is
reproduced bit for bit; no repair is claimed.  The saved behaviors called out
in the module docstring -- the sigma_zz = sigma_yy cylindrical identification
and the two empty-slice policies -- are witnessed here.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    compute_thermal_speed_m_s,
    reduce_axisymmetric_neutral_moments,
)

_RESULT_KEYS = {
    "density_m3",
    "axial_flux_m2_s",
    "axial_velocity_m_s",
    "pressure_ev_m3",
    "temperature_ev",
    "stress_xx_ev_m3",
    "stress_yy_ev_m3",
    "stress_zz_ev_m3",
    "random_heat_flux_w_m2",
}


def _fixture():
    rng = np.random.default_rng(21)
    vr = np.linspace(0.1, 1.0, 6)
    vx = np.linspace(-1.0, 1.0, 7)
    volume = (vr[:, None] * np.ones_like(vx[None, :])) * 0.2
    speed_squared = vr[:, None] ** 2 + vx[None, :] ** 2
    distribution = rng.random((6, 7, 5)) * np.exp(-speed_squared)[:, :, None]
    return distribution, vx, vr, volume


def test_default_policy_returns_all_nine_moments_with_saved_identification():
    distribution, vx, vr, volume = _fixture()
    result = reduce_axisymmetric_neutral_moments(
        distribution, vx, vr, volume,
        normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
    )
    assert set(result) == _RESULT_KEYS
    for name in _RESULT_KEYS:
        assert result[name].shape == (5,)
        assert np.all(np.isfinite(result[name]))
    # the saved cylindrical identification: sigma_zz is an independent copy
    assert np.array_equal(result["stress_zz_ev_m3"], result["stress_yy_ev_m3"])
    assert result["stress_zz_ev_m3"] is not result["stress_yy_ev_m3"]
    # density must be the plain cylindrical volume integral of the distribution
    expected_density = np.sum(volume[:, :, None] * distribution, axis=(0, 1))
    np.testing.assert_array_equal(result["density_m3"], expected_density)


def test_moments_match_an_independent_maxwellian_witness():
    """A shifted-Maxwellian-like distribution must recover its parameters:
    flow speed and temperature within quadrature accuracy.  Cell centers are
    offset half a cell so every cylindrical volume is strictly positive (the
    saved contract rejects nonpositive volume weights)."""
    nvr, nvx = 160, 200
    dv_r, dv_x = 4.0 / nvr, 10.0 / nvx
    vr = (np.arange(nvr) + 0.5) * dv_r
    vx = -4.0 + (np.arange(nvx) + 0.5) * dv_x
    volume = np.outer(vr * dv_r, np.full(nvx, dv_x))
    temperature = 2.0
    mass_amu = 1.0
    flow = 3.0e3  # m/s, far subthermal: normalized_flow ~ 0.15
    thermal_speed = compute_thermal_speed_m_s(temperature, mass_amu)["thermal_speed_m_s"]
    vr_grid, vx_grid = np.meshgrid(vr, vx, indexing="ij")
    normalized_shift = flow / thermal_speed
    maxwellian = np.exp(
        -(vr_grid[:, :, None] ** 2 + (vx_grid[:, :, None] - normalized_shift) ** 2)
    )
    distribution = np.broadcast_to(maxwellian, (nvr, nvx, 1)).copy()
    result = reduce_axisymmetric_neutral_moments(
        distribution, vx, vr, volume,
        normalization_temperature_ev=temperature, isotope_mass_amu=mass_amu, molecularity=1,
    )
    # flow speed: the exponential is even in the shifted variable
    assert abs(result["axial_velocity_m_s"][0] - flow) < 0.02 * flow
    # temperature: T = p / n with p from the second moment (quadrature error small)
    assert abs(result["temperature_ev"][0] - temperature) < 0.05 * temperature


def test_explicit_quadrature_reconstruction_contract_and_saved_summation_order():
    distribution, vx, vr, _ = _fixture()
    axial_weight = np.full(vx.size, 0.1)
    radial_weight = np.full(vr.size, 0.2)
    volume = radial_weight[:, None] * axial_weight[None, :]
    kw = dict(
        normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
        axial_quadrature=axial_weight, radial_quadrature=radial_weight,
    )
    result = reduce_axisymmetric_neutral_moments(distribution, vx, vr, volume, **kw)
    expected_density = np.array([
        np.sum(radial_weight * (distribution[:, :, k] @ axial_weight))
        for k in range(distribution.shape[2])
    ])
    np.testing.assert_array_equal(result["density_m3"], expected_density)
    bad_volume = volume.copy()
    bad_volume[0, 0] *= 1.5
    with pytest.raises(ValueError, match="explicit quadrature must match"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, bad_volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
            axial_quadrature=axial_weight, radial_quadrature=radial_weight,
        )


def test_empty_slice_policies_diverge_exactly_as_saved():
    distribution, vx, vr, volume = _fixture()
    distribution[:, :, 2] = 0.0
    kw = dict(normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2)
    with pytest.raises(ValueError, match="positive density"):
        reduce_axisymmetric_neutral_moments(distribution, vx, vr, volume, **kw)
    defaulted = reduce_axisymmetric_neutral_moments(
        distribution, vx, vr, volume, empty_slice_policy="source_default", **kw
    )
    assert defaulted["axial_velocity_m_s"][2] == 0.0
    assert defaulted["temperature_ev"][2] == 1.0


def test_species_and_quadrature_contracts_fail_closed():
    distribution, vx, vr, volume = _fixture()
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume,
            normalization_temperature_ev=0.0, isotope_mass_amu=2.0, molecularity=2,
        )
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=3,
        )
    with pytest.raises(ValueError, match="must be provided together"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
            axial_quadrature=np.ones(vx.size),
        )


def test_nonfinite_velocity_axes_fail_closed():
    """Pre-review regression: the saved arm accepts a NaN velocity axis and
    propagates NaN into the flow-speed and temperature moments; this asset
    fail-closes instead, per the exact document's finite-axes contract."""
    distribution, vx, vr, volume = _fixture()
    nan_vx = np.array([np.nan if i == 3 else v for i, v in enumerate(vx)])
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, nan_vx, vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
        )
    nan_vr = np.array([np.nan if i == 2 else v for i, v in enumerate(vr)])
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, nan_vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
        )


def test_complex_distribution_fail_closed():
    """Pre-review regression: the saved arm silently casts a complex
    distribution to float (ComplexWarning, imaginary part dropped); the
    exact document requires real array-like input, so this asset
    fail-closes instead."""
    distribution, vx, vr, volume = _fixture()
    with pytest.raises(ValueError, match="real-valued"):
        reduce_axisymmetric_neutral_moments(
            distribution.astype(complex), vx, vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
        )


def test_zero_axial_node_is_a_valid_mesh_point():
    """A zero axial NODE (inside a one-dimensional mesh) is inside the saved
    mesh contract (the mesh is symmetric around vx=0) and must be accepted.
    The saved moment arithmetic over a single-node mesh yields T = 2/3 eV
    (pressure over density with all weight at vx=0), asserted exactly."""
    f = np.ones((1, 1, 1))
    result = reduce_axisymmetric_neutral_moments(
        f, np.array([0.0]), np.array([1.0]), np.array([[1.0]]),
        normalization_temperature_ev=1.0, isotope_mass_amu=1.0, molecularity=1,
    )
    assert result["axial_velocity_m_s"][0] == 0.0
    np.testing.assert_allclose(result["temperature_ev"][0], 2.0 / 3.0, rtol=0.0, atol=1e-15)


def test_scalar_zero_axial_input_fail_closed():
    """Pre-review regression: a scalar vx=0.0 (0-D) passed the r60c saved-arm
    ndim checks and raised a raw IndexError mid-arithmetic (reviewer report,
    reproduced on HEAD); this asset fail-closes with ValueError because the
    axes must be one-dimensional arrays."""
    f = np.ones((1, 1, 1))
    with pytest.raises(ValueError, match="one-dimensional array"):
        reduce_axisymmetric_neutral_moments(
            f, 0.0, np.array([1.0]), np.array([[1.0]]),
            normalization_temperature_ev=1.0, isotope_mass_amu=1.0, molecularity=1,
        )


def test_nonfinite_scalar_inputs_fail_closed():
    """Pre-review regression: the saved arm accepts NaN normalization
    temperature, NaN mass, and NaN volume (under source_default), each
    propagating NaN into the returned moments; this asset fail-closes on all
    of them, per the exact document's finite-inputs contract."""
    distribution, vx, vr, volume = _fixture()
    kw = dict(molecularity=1)
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume,
            normalization_temperature_ev=float("nan"), isotope_mass_amu=1.0, **kw,
        )
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume,
            normalization_temperature_ev=2.0, isotope_mass_amu=float("nan"), **kw,
        )
    volume_nan = volume.copy()
    volume_nan[0, 0] = np.nan
    with pytest.raises(ValueError, match="species contract is invalid"):
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume_nan,
            normalization_temperature_ev=2.0, isotope_mass_amu=1.0,
            empty_slice_policy="source_default", **kw,
        )
