from __future__ import annotations

import numpy as np
import scirel
import pytest

from scirel.neutrals import (
    build_compensated_shifted_maxwellian,
    compensate_velocity_slice,
    make_cylindrical_velocity_quadrature,
)


def _fixture():
    vr = np.array([0.25, 0.75, 1.5], dtype=float)
    vx = np.array([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5], dtype=float)
    cells = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    f = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))
    return vr, vx, cells, f


def test_compensation_preserves_slice_shape_and_returns_scale():
    vr, vx, cells, f = _fixture()
    adjusted, scale = compensate_velocity_slice(f, cells, vr, vx, 1.0, 0.0, 3.0)
    assert adjusted.shape == f.shape
    assert isinstance(scale, float)
    assert np.isfinite(adjusted).all()


def test_compensated_shifted_maxwellian_has_declared_shape_and_zero_temperature_branch():
    vr, vx, _, _ = _fixture()
    result = build_compensated_shifted_maxwellian(
        vr=vr,
        vx=vx,
        temperatures_eV=np.array([5.0, 0.0, -1.0]),
        shifts_ms=np.array([0.0, 100.0, -100.0]),
        mu=1,
        molecularity=1,
        tnorm_eV=5.0,
        moment_rtol=0.1,
    )
    assert result.shape == (vr.size, vx.size, 3)
    assert np.all(result[:, :, 1:] == 0.0)
    assert np.isfinite(result[:, :, 0]).all()


def test_compensated_slice_accepts_signed_mode():
    vr, vx, cells, f = _fixture()
    adjusted, scale = compensate_velocity_slice(-f, cells, vr, vx, 1.0, 0.0, 3.0, assume_pos=False)
    assert adjusted.shape == f.shape
    assert np.isfinite(scale) or np.isnan(scale)


def _mesh(nv=40):
    grid = np.linspace(3.5 / nv, 3.5, nv)
    return grid, np.r_[-grid[::-1], grid]


def _maxwellian(temperature, drift, **options):
    vr, vx = _mesh()
    return build_compensated_shifted_maxwellian(
        vr=vr,
        vx=vx,
        temperatures_eV=[temperature],
        shifts_ms=[drift],
        mu=1,
        molecularity=1,
        tnorm_eV=10.0,
        **options,
    )


@pytest.mark.parametrize("temperature, drift", [(10.0, 0.0), (10.0, 3e4), (20.0, 3e4)])
def test_adequate_mesh_returns_the_exact_maxwellian_moments(temperature, drift):
    """A Maxwellian has mean vx = U and mean speed squared U^2 + 3T/m exactly."""
    from scirel.neutrals.cylindrical_velocity_quadrature import make_cylindrical_velocity_quadrature

    vr, vx = _mesh()
    f = _maxwellian(temperature, drift)[:, :, 0]
    cells = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    mass, charge = 1.6726231e-27, 1.602177e-19
    speed = np.sqrt(2 * charge * 10.0 / mass)
    w = cells["volume"]
    assert np.sum(w * f) == pytest.approx(1.0)
    mean = speed * np.sum(w * f * vx) / np.sum(w * f)
    energy = speed**2 * np.sum(w * f * (vr[:, None] ** 2 + vx[None, :] ** 2)) / np.sum(w * f)
    assert mean == pytest.approx(
        drift, abs=1e-2 * max(drift, np.sqrt(3 * charge * temperature / mass))
    )
    assert (energy - mean**2) * mass / (3 * charge) == pytest.approx(temperature, rel=1e-2)


@pytest.mark.parametrize(
    "temperature, drift", [(50.0, 5e4), (50.0, 0.0), (60.0, 0.0), (40.0, 5e4), (80.0, 0.0)]
)
def test_mesh_too_small_for_the_temperature_raises_instead_of_returning_wrong_moments(
    temperature, drift
):
    """These used to return drifts up to -2e5 m/s and temperatures down to -380 eV with no error."""
    with pytest.raises(ValueError, match="velocity mesh cannot represent"):
        _maxwellian(temperature, drift)


def test_moment_tolerance_is_the_caller_s_choice():
    assert _maxwellian(40.0, 0.0, moment_rtol=0.2).shape[2] == 1


@pytest.mark.parametrize("molecularity", [1, 2])
@pytest.mark.parametrize("mu", [1, 2])
def test_internal_seed_keeps_peak_before_real_moment_compensation(monkeypatch, molecularity, mu):
    import scirel.neutrals.moment_compensation as module

    vr = np.linspace(0.0, 4.0, 61)
    vx = np.linspace(-4.0, 4.0, 121)
    cells = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    captured = []
    original = module._compensate_slice

    def observe_seed(f, *args, **kwargs):
        captured.append(f.copy())
        return original(f, *args, **kwargs)

    monkeypatch.setattr(module, "_compensate_slice", observe_seed)
    result = build_compensated_shifted_maxwellian(
        vr=vr,
        vx=vx,
        temperatures_eV=[1.0, 0.0, -1.0],
        shifts_ms=[0.0, 0.0, 0.0],
        mu=mu,
        molecularity=molecularity,
        tnorm_eV=1.0,
    )
    assert len(captured) == 1
    # Analytic Boltzmann definition, including the retained tail approximation.
    raw = np.exp(np.maximum(-molecularity * (vr[:, None] ** 2 + vx**2), -80.0))
    expected = raw / np.sum(cells["volume"] * raw)
    np.testing.assert_allclose(captured[0], expected, rtol=3e-15, atol=0)
    np.testing.assert_allclose(
        captured[0][0, 60] / captured[0][0, 75],
        np.exp(molecularity),
        rtol=1e-14,
        atol=0,
    )
    # The public call still executes the real correction and default moment gate.
    f = result[:, :, 0]
    weights = cells["volume"]
    vth = np.sqrt(2 * 1.602177e-19 / (mu * 1.6726231e-27))
    density = np.sum(weights * f)
    mean = vth * np.sum(weights * f * vx) / density
    energy = vth**2 * np.sum(weights * f * (vr[:, None] ** 2 + vx**2)) / density
    mass = molecularity * mu * 1.6726231e-27
    temperature = (energy - mean**2) * mass / (3 * 1.602177e-19)
    np.testing.assert_allclose(density, 1.0, rtol=1e-15, atol=0)
    assert abs(mean) <= 0.01 * np.sqrt(3 * 1.602177e-19 / mass)
    assert abs(temperature - 1.0) <= 0.01
    assert np.min(f) >= -0.01 * np.max(f)
    np.testing.assert_array_equal(result[:, :, 1:], 0.0)


@pytest.mark.parametrize(
    "tolerance", [np.nan, np.inf, -np.inf, 0.0, -0.01, True, "0.01", 1j, [0.01], None]
)
def test_compensated_builder_rejects_invalid_moment_tolerance(tolerance):
    with pytest.raises(ValueError, match="moment_rtol"):
        _maxwellian(10.0, 0.0, moment_rtol=tolerance)


def test_nan_moment_tolerance_cannot_accept_the_inadequate_mesh():
    with pytest.raises(ValueError, match="moment_rtol"):
        _maxwellian(50.0, 0.0, moment_rtol=np.nan)


def test_invalid_moment_tolerance_is_checked_for_zero_temperature_too():
    with pytest.raises(ValueError, match="moment_rtol"):
        _maxwellian(0.0, 0.0, moment_rtol=np.nan)


@pytest.mark.parametrize("tolerance", [np.float64(0.01), np.array(0.01), np.int64(1)])
def test_valid_numpy_scalar_moment_tolerance_keeps_the_same_distribution(tolerance):
    np.testing.assert_array_equal(
        _maxwellian(10.0, 0.0, moment_rtol=tolerance), _maxwellian(10.0, 0.0)
    )


def test_slice_warns_when_the_correction_changes_the_density():
    from scirel.neutrals.cylindrical_velocity_quadrature import make_cylindrical_velocity_quadrature

    vr, vx = _mesh()
    cells = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    mass, charge = 1.6726231e-27, 1.602177e-19
    speed = np.sqrt(2 * charge * 10.0 / mass)
    drift, temperature = 5e4, 50.0
    f = np.exp(-(vr[:, None] ** 2 + (vx[None, :] - drift / speed) ** 2) * 10.0 / temperature)
    f /= np.sum(cells["volume"] * f)
    with pytest.warns(scirel.ApplicabilityWarning, match="missed its moment targets"):
        compensate_velocity_slice(
            f, cells, vr, vx, speed, drift, drift**2 + 3 * charge * temperature / mass
        )
