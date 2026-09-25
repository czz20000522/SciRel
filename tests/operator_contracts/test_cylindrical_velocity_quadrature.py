"""Direct contract tests for ``scirel.kinetic.cylindrical_velocity_quadrature``.

The relation is the saved KN1DPy ``make_dvr_dvx`` slice: from strictly
increasing normalized ``vr``/``vx`` meshes it builds the ghost-extended cell
faces, the annular radial measure, the ``(nvr, nvx)`` cylindrical cell
volumes, the ghosted finite-vission difference coefficients and the sign index
ranges of the axial axis.  The maintained tests are source-free: every
expected value is re-derived by hand on a different mesh than the saved
package test, and the environment-gated replay against the saved KN1DPy
implementation lives in ``test_cylindrical_velocity_quadrature_l1.py``.
"""
from __future__ import annotations

import numpy as np
import pytest

import scirel
from scirel.kinetic import cylindrical_velocity_quadrature
from scirel.kinetic.cylindrical_velocity_quadrature import (
    make_cylindrical_velocity_quadrature,
)


def _call(vr=None, vx=None):
    return make_cylindrical_velocity_quadrature(
        vr=np.array([0.5, 1.5]) if vr is None else np.asarray(vr, dtype=float),
        vx=np.array([-1.5, -0.5, 0.5, 1.5]) if vx is None else np.asarray(vx, dtype=float),
    )


# ---------------------------------------------------------------------------
# The public surface
# ---------------------------------------------------------------------------


def test_the_module_publishes_exactly_one_callable():
    assert cylindrical_velocity_quadrature.__all__ == [
        "make_cylindrical_velocity_quadrature"
    ]


def test_the_package_and_root_namespace_export_the_callable():
    assert callable(scirel.make_cylindrical_velocity_quadrature)
    assert callable(scirel.kinetic.make_cylindrical_velocity_quadrature)


def test_the_result_keys_are_exactly_the_saved_field_set():
    result = _call()
    assert set(result) == {
        "radial_measure",
        "radial_four_pi_measure",
        "dvx",
        "vr_left",
        "vr_right",
        "vx_left",
        "vx_right",
        "volume",
        "inv_dvx_ghost",
        "vx_over_dvx_ghost",
        "vr_over_dvr_ghost",
        "speed_squared",
        "positive_vx_indices",
        "positive_vx_first_index",
        "positive_vx_last_index",
        "negative_vx_indices",
        "negative_vx_first_index",
        "negative_vx_last_index",
    }


# ---------------------------------------------------------------------------
# The relation, re-derived by hand on a different mesh than the saved test
# ---------------------------------------------------------------------------


def test_the_hand_derived_oracle_on_a_four_point_axial_mesh():
    result = _call()
    np.testing.assert_allclose(result["radial_measure"], [np.pi, 3.0 * np.pi], rtol=0, atol=0)
    np.testing.assert_allclose(
        result["radial_four_pi_measure"],
        [4.0 * np.pi / 3.0, 28.0 * np.pi / 3.0],
        rtol=0,
        atol=0,
    )
    np.testing.assert_allclose(result["dvx"], [1.0, 1.0, 1.0, 1.0], rtol=0, atol=0)
    np.testing.assert_allclose(result["vr_left"], [0.0, 1.0], rtol=0, atol=0)
    np.testing.assert_allclose(result["vr_right"], [1.0, 2.0], rtol=0, atol=0)
    np.testing.assert_allclose(result["vx_left"], [-2.0, -1.0, 0.0, 1.0], rtol=0, atol=0)
    np.testing.assert_allclose(result["vx_right"], [-1.0, 0.0, 1.0, 2.0], rtol=0, atol=0)
    expected_volume = np.array(
        [[np.pi, np.pi, np.pi, np.pi], [3.0 * np.pi, 3.0 * np.pi, 3.0 * np.pi, 3.0 * np.pi]]
    )
    np.testing.assert_allclose(result["volume"], expected_volume, rtol=0, atol=0)
    expected_speed_squared = np.array(
        [[2.5, 0.5, 0.5, 2.5], [4.5, 2.5, 2.5, 4.5]]
    )
    np.testing.assert_allclose(result["speed_squared"], expected_speed_squared, rtol=0, atol=0)
    assert np.array_equal(result["positive_vx_indices"], [2, 3])
    assert np.array_equal(result["negative_vx_indices"], [0, 1])
    assert result["positive_vx_first_index"] == 2
    assert result["positive_vx_last_index"] == 3
    assert result["negative_vx_first_index"] == 0
    assert result["negative_vx_last_index"] == 1


def test_the_ghosted_coefficients_are_zero_on_the_boundary_shell_only():
    result = _call()
    for key in ("inv_dvx_ghost", "vx_over_dvx_ghost", "vr_over_dvr_ghost"):
        assert result[key].shape == (4, 6), key
        assert np.all(result[key][0, :] == 0.0), key
        assert np.all(result[key][-1, :] == 0.0), key
        assert np.all(result[key][:, 0] == 0.0), key
        assert np.all(result[key][:, -1] == 0.0), key
    assert np.all(result["inv_dvx_ghost"][1:-1, 1:-1] == 1.0)
    assert np.allclose(
        result["vx_over_dvx_ghost"][1:-1, 1:-1],
        np.asarray([-1.5, -0.5, 0.5, 1.5])[None, :],
    )
    assert np.allclose(result["vr_over_dvr_ghost"][1:-1, 1:-1], np.asarray([0.5, 1.5])[:, None])


def test_the_volumes_sum_to_the_ghost_faced_cylindrical_box():
    """The total volume is the annulus up to the ghost face times the ghosted
    axial span -- the closure that makes the measure a partition of the box."""
    result = _call()
    total = float(np.sum(result["volume"]))
    radial_span = np.pi * float(result["vr_right"][-1]) ** 2
    axial_span = float(result["vx_right"][-1] - result["vx_left"][0])
    assert total == pytest.approx(radial_span * axial_span, rel=1e-15)


def test_a_nonuniform_radial_mesh_keeps_exact_annular_measures():
    """Faces: inner at zero, midpoints between nodes, and the outer face at
    the midpoint between the last node and its mirrored ghost."""
    result = _call(vr=[0.5, 1.0, 4.0])
    np.testing.assert_allclose(
        result["radial_measure"],
        [np.pi * 0.75**2, np.pi * (2.5**2 - 0.75**2), np.pi * (5.5**2 - 2.5**2)],
        rtol=1e-15,
        atol=0.0,
    )
    np.testing.assert_allclose(result["vr_left"], [0.0, 0.75, 2.5], rtol=0, atol=0)
    np.testing.assert_allclose(result["vr_right"], [0.75, 2.5, 5.5], rtol=0, atol=0)


# ---------------------------------------------------------------------------
# The composition contract with the Maxwellian rate average
# ---------------------------------------------------------------------------


def test_the_quadrature_feeds_the_maxwellian_rate_average():
    """The documented N1->N2 composition: the quadrature's volume weights are
    the cylindrical_volume port of the collisions-domain rate average."""
    from scirel.collisions import average_cross_section_over_maxwellian

    result = _call()
    rate = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([0.0, 10.0, 100.0]),
        particle_mass_amu=1.0,
        target_temperature_ev=10.0,
        target_mass_amu=2.0,
        vx=np.array([-1.5, -0.5, 0.5, 1.5]),
        vr=np.array([0.5, 1.5]),
        tnorm_ev=20.0,
        cylindrical_volume=result["volume"],
        cross_section_m2=lambda energy: np.full_like(energy, 3.0e-20),
    )
    assert rate.shape == (3,)
    assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)


# ---------------------------------------------------------------------------
# The input contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: _call(vr=[2.0, 1.0]),
        lambda: _call(vr=[1.0, 1.0]),
        lambda: _call(vx=[1.0, 0.0]),
        lambda: _call(vr=[1.0]),
        lambda: _call(vx=[]),
        lambda: _call(vr=[1.0, np.nan, 2.0]),
        lambda: _call(vx=[-1.0, np.inf, 1.0]),
        lambda: _call(vx=[0.0, 1.0, 2.0]),
        lambda: _call(vx=[-2.0, -1.0, 0.0]),
    ],
)
def test_the_value_contract_rejects_every_out_of_domain_value(call):
    with pytest.raises(ValueError):
        call()


def test_the_rejection_messages_name_the_quantity():
    with pytest.raises(ValueError, match="strictly increasing"):
        _call(vr=[2.0, 1.0])
    with pytest.raises(ValueError, match="both negative and positive"):
        _call(vx=[0.0, 1.0, 2.0])


def test_the_inputs_are_not_modified():
    vr = np.array([0.5, 1.5])
    vx = np.array([-1.5, -0.5, 0.5, 1.5])
    _call(vr=vr, vx=vx)
    assert np.array_equal(vr, [0.5, 1.5])
    assert np.array_equal(vx, [-1.5, -0.5, 0.5, 1.5])


# ---------------------------------------------------------------------------
# The radial domain and output representability
# ---------------------------------------------------------------------------


def test_a_negative_radial_mesh_is_rejected():
    """vr is a radial-speed axis (the saved source's final positive-radial
    convention): a negative node makes the annular measure negative -- for
    vr = [-2, -1] the second cell's measure is pi*(0.25 - 2.25) = -2*pi -- so
    the domain is restricted to nonnegative meshes instead of weakening the
    positive-output contract."""
    with pytest.raises(ValueError, match="vr"):
        _call(vr=[-2.0, -1.0])


def test_nonrepresentable_quadrature_outputs_are_rejected():
    """vr = [1e308, 1.5e308] is finite and strictly increasing, but the
    mirrored ghost face and the squared faces overflow, so the measure and
    volume are not finite.  The finite-output contract is enforced rather
    than returned as infinity or NaN."""
    with pytest.raises(ValueError, match="not representable"):
        _call(vr=[1.0e308, 1.5e308])


def test_an_overflowing_axial_ghost_is_rejected():
    with pytest.raises(ValueError, match="not representable"):
        _call(vx=[-1.7e308, 0.5, 1.0])


def test_an_underflowing_radial_mesh_is_rejected():
    """vr = [0.0, 1e-200] is finite, nonnegative and strictly increasing, but
    the squared faces underflow to zero, so radial_measure, the four-pi
    measure and the volumes are exactly zero -- contradicting the
    strictly-positive output contract."""
    with pytest.raises(ValueError, match="underflow"):
        _call(vr=[0.0, 1e-200])
