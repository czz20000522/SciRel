"""Direct contract tests for the r61 mesh/seam pair:
``scirel.kinetic.create_adaptive_neutral_velocity_mesh`` and
``scirel.kinetic.interpolate_scalar_across_mesh``.

The saved KN1DPy packages (anchors ``KN1DPy/create_vr_vx_mesh.py:16-56`` and
``KN1DPy/interp_scalarx.py``, as recorded by the saved bundle's provenance)
are reproduced bit for bit; no repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    create_adaptive_neutral_velocity_mesh,
    interpolate_scalar_across_mesh,
)


def test_nearly_uniform_temperature_uses_the_saved_uniform_3_5_mesh():
    vx, vr, tnorm, _, _ = create_adaptive_neutral_velocity_mesh(4, (1.0, 1.05))
    assert np.array_equal(vr, (0.875, 1.75, 2.625, 3.5))
    assert np.array_equal(vx, (-3.5, -2.625, -1.75, -0.875, 0.875, 1.75, 2.625, 3.5))
    assert tnorm == 1.025


def test_requested_energy_is_inserted_and_the_mesh_stays_symmetric():
    vx, vr, tnorm, _, _ = create_adaptive_neutral_velocity_mesh(4, (1.0, 4.0), (9.0,))
    assert np.any(vr == np.sqrt(9.0 / tnorm))
    assert np.array_equal(vx, -vx[::-1])


def test_nonuniform_temperature_uses_the_saved_quadratic_stretching():
    vx, vr, tnorm, _, _ = create_adaptive_neutral_velocity_mesh(4, (1.0, 9.0))
    # the saved stretching: ratio = sqrt(Tmin/Tmax), g and b follow, vr = v[1:]
    ratio = np.sqrt(1.0 / 9.0)
    g = 2.0 * 4 * ratio / (1.0 - ratio)
    b = 3.5 / (4 * (4 + g))
    v = g * b * np.arange(5) + b * np.arange(5) ** 2
    np.testing.assert_array_equal(vr, v[1:])
    assert np.array_equal(vx, -vx[::-1])


def test_temperature_cap_drops_selected_entries():
    with_cap = create_adaptive_neutral_velocity_mesh(4, (1.0, 9.0), temperature_cap_ev=4.0)
    # with the cap the selected population is only (1.0): near-uniform path
    vx, vr, tnorm, _, _ = with_cap
    assert np.array_equal(vr, (0.875, 1.75, 2.625, 3.5))
    assert tnorm == 1.0


def test_mesh_contracts_fail_closed():
    with pytest.raises(ValueError, match="nv must be positive"):
        create_adaptive_neutral_velocity_mesh(0, (1.0,))
    with pytest.raises(ValueError, match="nv must be positive"):
        create_adaptive_neutral_velocity_mesh(4, (0.0,))
    with pytest.raises(ValueError, match="nonempty and positive"):
        create_adaptive_neutral_velocity_mesh(4, (1.0,), temperature_cap_ev=0.5)


def test_linear_profile_is_reproduced_to_closed_form():
    xa = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    fa = np.array([1.0, 2.0, 3.0, 4.0, 5.0])  # fa = 1 + 2*xa
    xb = np.array([0.0, 0.25, 0.8, 1.1, 1.6, 2.0])
    fb = interpolate_scalar_across_mesh(fa, xa, xb, do_warn=0)
    np.testing.assert_allclose(fb, 1.0 + 2.0 * xb, rtol=0.0, atol=4.0 * np.finfo(float).eps)


def test_out_of_range_nodes_stay_exactly_zero_and_affine_invariance_holds():
    xa = np.array([0.1, 0.7, 1.3, 2.9])
    fa = np.array([-2.5, 4.0, 0.0, 7.25])
    xb = np.array([-1.0, 0.1, 1.0, 2.9, 5.0])
    fb = interpolate_scalar_across_mesh(fa, xa, xb)
    assert fb[0] == 0.0 and fb[4] == 0.0
    # affine invariance: scaling and offsetting fa scales/offsets the in-range part
    scaled = interpolate_scalar_across_mesh(3.0 * fa + 1.0, xa, xb)
    np.testing.assert_allclose(scaled[1:4], 3.0 * fb[1:4] + 1.0, rtol=0.0, atol=1e-12)


def test_interpolation_contracts_fail_closed():
    xa = np.array([0.0, 1.0, 2.0])
    fa = np.array([1.0, 2.0, 3.0])
    xb = np.array([0.5])
    with pytest.raises(ValueError, match="strictly increasing"):
        interpolate_scalar_across_mesh(fa, np.array([0.0, 1.0, 1.0]), xb)
    with pytest.raises(ValueError, match="do not agree"):
        interpolate_scalar_across_mesh(fa[:-1], xa, xb)
    with pytest.raises(ValueError, match="within range"):
        interpolate_scalar_across_mesh(fa, xa, np.array([5.0, 6.0]))
    with pytest.raises(ValueError, match="finite"):
        interpolate_scalar_across_mesh(np.array([1.0, np.nan, 3.0]), xa, xb)


def test_non_monotonic_xb_with_in_range_holes_keeps_the_saved_raw_error():
    """The saved assignment fb[k0:k1+1] = interp1d(...)(xb[okk]) raises numpy's
    raw broadcast ValueError when okk is non-contiguous (declared divergence
    from a named contract message); the physically meaningful zero fill for
    out-of-range nodes is unchanged."""
    xa = np.array([0.0, 1.0, 2.0])
    fa = np.array([0.0, 10.0, 20.0])
    xb = np.array([1.0, 5.0, 1.5])  # okk = [0, 2], non-contiguous
    with pytest.raises(ValueError, match="could not broadcast"):
        interpolate_scalar_across_mesh(fa, xa, xb, 0)
