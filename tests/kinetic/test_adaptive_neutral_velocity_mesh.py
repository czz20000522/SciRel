"""Direct contract tests for the source-specific neutral velocity mesh."""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import create_adaptive_neutral_velocity_mesh


def test_nearly_uniform_temperatures_use_the_saved_uniform_mesh():
    vx, vr, tnorm, ix, ir = create_adaptive_neutral_velocity_mesh(4, (1.0, 1.05))
    np.testing.assert_array_equal(vr, (0.875, 1.75, 2.625, 3.5))
    np.testing.assert_array_equal(vx, (-3.5, -2.625, -1.75, -0.875, 0.875, 1.75, 2.625, 3.5))
    assert tnorm == 1.025
    assert ix.size == ir.size == 0


def test_temperature_spread_uses_the_saved_quadratic_stretching():
    vx, vr, tnorm, _, _ = create_adaptive_neutral_velocity_mesh(4, (1.0, 9.0))
    ratio = np.sqrt(1.0 / 9.0)
    g = 2.0 * 4 * ratio / (1.0 - ratio)
    b = 3.5 / (4 * (4 + g))
    v = g * b * np.arange(5) + b * np.arange(5) ** 2
    np.testing.assert_array_equal(vr, v[1:])
    np.testing.assert_array_equal(vx, -vx[::-1])
    assert tnorm == 5.0


def test_cap_changes_normalization_but_still_inserts_requested_energy():
    vx, vr, tnorm, ix, ir = create_adaptive_neutral_velocity_mesh(
        4, (1.0,), (2.0,), temperature_cap_ev=1.5
    )
    assert tnorm == 1.0
    assert np.count_nonzero(vr == np.sqrt(2.0)) == 1
    np.testing.assert_array_equal(vx, -vx[::-1])
    assert vr[ir] == np.sqrt(2.0)
    np.testing.assert_array_equal(abs(vx[ix]), np.full(2, np.sqrt(2.0)))


def test_negative_requested_energies_are_ignored_as_in_the_saved_formula():
    plain = create_adaptive_neutral_velocity_mesh(4, (1.0,))
    ignored = create_adaptive_neutral_velocity_mesh(4, (1.0,), (-5.0, 0.0))
    for a, b in zip(plain, ignored):
        np.testing.assert_array_equal(a, b)


def test_generated_mesh_feeds_quadrature_seed_and_moment_reduction():
    from scirel.kinetic import (
        build_shifted_maxwellian_seed,
        make_cylindrical_velocity_quadrature,
        reduce_axisymmetric_neutral_moments,
    )

    vx, vr, tnorm, _, _ = create_adaptive_neutral_velocity_mesh(4, (1.0, 1.05))
    quadrature = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    seed = build_shifted_maxwellian_seed(
        vr=vr, vx=vx, tnorm_ev=tnorm,
        shifted_vx_m_s=np.array([0.0]), temperature_ev=np.array([tnorm]),
        mass_amu=1.0, molecule_count=1,
        cylindrical_volume=quadrature["volume"],
    )
    moments = reduce_axisymmetric_neutral_moments(
        seed["distribution"], vx, vr, quadrature["volume"],
        normalization_temperature_ev=tnorm, isotope_mass_amu=1.0,
        molecularity=1,
    )
    np.testing.assert_allclose(moments["density_m3"], [1.0], rtol=1e-15)
    assert abs(moments["axial_velocity_m_s"][0]) < 1e-9
    assert np.all(np.isfinite(moments["temperature_ev"]))


@pytest.mark.parametrize("nv", [0, True, np.bool_(True), 2.0, 2.5, "2"])
def test_invalid_node_count_fails_closed(nv):
    with pytest.raises(ValueError, match="nv"):
        create_adaptive_neutral_velocity_mesh(nv, (1.0,))


@pytest.mark.parametrize(
    "temperatures", [
        (), (0.0,), (float("nan"),), (float("inf"),),
        np.array([1.0 + 0.0j]), np.array([True]), [1.0, True], ["1.0"],
        np.array([[1.0]]),
    ],
)
def test_invalid_temperature_array_fails_closed(temperatures):
    with pytest.raises(ValueError, match="ion_temperature_ev|temperatures"):
        create_adaptive_neutral_velocity_mesh(4, temperatures)


@pytest.mark.parametrize(
    "requested", [
        True, "2.0", ["2.0"], [1.0 + 0.0j], [1.0, True],
        np.array([np.inf]), np.array([np.nan]), np.array([[2.0]]),
    ],
)
def test_invalid_requested_energy_fails_by_parameter_name(requested):
    with pytest.raises(ValueError, match="requested_energy_ev"):
        create_adaptive_neutral_velocity_mesh(4, (1.0,), requested)


@pytest.mark.parametrize("cap", [True, "2.0", [2.0], -1.0, float("nan"), float("inf")])
def test_invalid_temperature_cap_fails_closed(cap):
    with pytest.raises(ValueError, match="temperature_cap_ev|cap nonnegative"):
        create_adaptive_neutral_velocity_mesh(4, (0.5,), temperature_cap_ev=cap)


@pytest.mark.parametrize(
    ("requested", "cap"),
    [((9.0, 9.0), 0.0), ((3.0625,), 2.0)],
)
def test_duplicate_inserted_node_fails_before_downstream_quadrature(requested, cap):
    with pytest.raises(ValueError, match="strictly increasing"):
        create_adaptive_neutral_velocity_mesh(
            4, (1.0,), requested, temperature_cap_ev=cap
        )


def test_valid_numpy_integer_node_count_is_accepted():
    vx, vr, _, _, _ = create_adaptive_neutral_velocity_mesh(np.int64(4), (1.0,))
    assert vx.size == 8 and vr.size == 4
