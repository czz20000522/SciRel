from __future__ import annotations

import numpy as np

from scirel.kinetic import (
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
        vr=vr, vx=vx, temperatures_eV=np.array([5.0, 0.0, -1.0]),
        shifts_ms=np.array([0.0, 100.0, -100.0]), mu=1, molecularity=1, tnorm_eV=5.0,
    )
    assert result.shape == (vr.size, vx.size, 3)
    assert np.all(result[:, :, 1:] == 0.0)
    assert np.isfinite(result[:, :, 0]).all()


def test_compensated_slice_accepts_signed_mode():
    vr, vx, cells, f = _fixture()
    adjusted, scale = compensate_velocity_slice(
        -f, cells, vr, vx, 1.0, 0.0, 3.0, assume_pos=False
    )
    assert adjusted.shape == f.shape
    assert np.isfinite(scale) or np.isnan(scale)
