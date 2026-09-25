"""Direct contract tests for ``scirel.kinetic.shifted_maxwellian_seed``.

The relation is the saved KN1DPy ``create_shifted_maxwellian`` seed leaf: the
normalized exponential distribution on a cylindrical ``(vr, vx)`` mesh before
any moment compensation, with per-shift temperatures, the molecule-count
factor in the exponent, the strict-interior ``-80`` clamp and the cell-volume
normalization.  The maintained tests re-derive every expected value from an
in-file loop formulation of the same discrete relation plus the analytic
uniform-floor limit; the environment-gated replay against the saved KN1DPy
implementation lives in ``test_shifted_maxwellian_seed_l1.py``.
"""
from __future__ import annotations

import inspect

import numpy as np
import pytest

import scirel
from scirel.kinetic import shifted_maxwellian_seed
from scirel.kinetic.shifted_maxwellian_seed import build_shifted_maxwellian_seed

AMU = 1.6726231e-27
E_CH = 1.602177e-19


def _independent_seed(vr, vx, tnorm_ev, shifted_vx_m_s, temperature_ev, mass_amu,
                      molecule_count, cylindrical_volume):
    """Loop-per-shift formulation of the same discrete relation."""
    vth = np.sqrt(2.0 * E_CH * tnorm_ev / (mass_amu * AMU))
    radial = np.asarray(vr, dtype=float)
    axial = np.asarray(vx, dtype=float)
    layers = []
    exponents = []
    for shift, temperature in zip(shifted_vx_m_s, temperature_ev):
        argument = -(
            radial[:, None] ** 2 + (axial[None, :] - shift / vth) ** 2
        ) * molecule_count * tnorm_ev / temperature
        seed = np.exp(np.where((-80.0 < argument) & (argument < 0.0), argument, -80.0))
        seed = seed / np.sum(cylindrical_volume * seed)
        layers.append(seed)
        exponents.append(argument)
    return {
        "distribution": np.stack(layers, axis=-1),
        "thermal_speed_m_s": vth,
        "exponent": np.stack(exponents, axis=-1),
    }


def _call(**overrides):
    arguments = dict(
        vr=np.array([0.5, 1.0]),
        vx=np.array([-1.0, 0.0, 1.0]),
        tnorm_ev=2.0,
        shifted_vx_m_s=np.array([0.0]),
        temperature_ev=np.array([2.0]),
        mass_amu=2.0,
        molecule_count=1,
        cylindrical_volume=np.ones((2, 3)),
    )
    arguments.update(overrides)
    return build_shifted_maxwellian_seed(**arguments)


# ---------------------------------------------------------------------------
# The public surface
# ---------------------------------------------------------------------------


def test_the_module_publishes_exactly_one_callable():
    assert shifted_maxwellian_seed.__all__ == ["build_shifted_maxwellian_seed"]


def test_the_package_and_root_namespace_export_the_callable():
    assert callable(scirel.build_shifted_maxwellian_seed)
    assert callable(scirel.kinetic.build_shifted_maxwellian_seed)


def test_the_signature_is_keyword_only_with_eight_arguments():
    signature = inspect.signature(build_shifted_maxwellian_seed)
    assert list(signature.parameters) == [
        "vr",
        "vx",
        "tnorm_ev",
        "shifted_vx_m_s",
        "temperature_ev",
        "mass_amu",
        "molecule_count",
        "cylindrical_volume",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


# ---------------------------------------------------------------------------
# The relation against an independent formulation
# ---------------------------------------------------------------------------


def test_the_distribution_matches_an_independent_loop_formulation():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 1.0])
    volume = np.ones((2, 3))
    ours = _call(vr=vr, vx=vx, cylindrical_volume=volume)
    theirs = _independent_seed(vr, vx, 2.0, [0.0], [2.0], 2.0, 1, volume)
    np.testing.assert_allclose(ours["distribution"], theirs["distribution"], rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(ours["exponent"], theirs["exponent"], rtol=1e-15, atol=0.0)
    assert ours["thermal_speed_m_s"] == theirs["thermal_speed_m_s"]


def test_the_seed_is_volume_normalized_per_shift():
    result = _call(
        shifted_vx_m_s=np.array([0.0, 2.0e4]),
        temperature_ev=np.array([2.0, 2.0]),
    )
    distribution = result["distribution"]
    assert distribution.shape == (2, 3, 2)
    np.testing.assert_allclose(np.sum(distribution, axis=(0, 1)), [1.0, 1.0], rtol=1e-15)


def test_a_positive_shift_moves_the_axial_moment_positive():
    vx = np.array([-1.0, 0.0, 1.0])
    result = _call(shifted_vx_m_s=np.array([2.0e4]), temperature_ev=np.array([2.0]))
    moment = np.sum(result["distribution"][:, :, 0] * vx[None, :])
    assert moment > 0.0


def test_the_far_shift_floors_to_a_uniform_distribution():
    """Every exponent below the -80 floor makes the raw seed a constant, so the
    volume normalization leaves exactly the uniform distribution."""
    result = _call(shifted_vx_m_s=np.array([1.0e6]), temperature_ev=np.array([2.0]))
    assert result["exponent"][0, 0, 0] < -80.0
    np.testing.assert_allclose(
        result["distribution"][:, :, 0],
        np.full((2, 3), 1.0 / 6.0),
        rtol=1e-15,
        atol=0.0,
    )
    assert np.all(np.isfinite(result["distribution"]))


def test_the_exact_zero_argument_uses_the_strict_interior_clamp():
    """argument == 0 (mesh node exactly at the shifted peak) fails the strict
    ``-80 < argument < 0`` interior test and is floored to ``-80`` like the
    saved source; the exponent output still reports the raw zero."""
    result = _call(
        vr=np.array([0.0, 1.0]),
        vx=np.array([-2.0, 0.0, 2.0]),
        tnorm_ev=1.0,
        shifted_vx_m_s=np.array([0.0]),
        temperature_ev=np.array([1.0]),
        mass_amu=1.0,
        molecule_count=1,
        cylindrical_volume=np.ones((2, 3)),
    )
    expected_exponent = np.array([[-4.0, 0.0, -4.0], [-5.0, -1.0, -5.0]])
    np.testing.assert_allclose(result["exponent"][:, :, 0], expected_exponent, rtol=0, atol=0)
    expected_raw = np.exp(np.where(expected_exponent == 0.0, -80.0, expected_exponent))
    expected_distribution = expected_raw / np.sum(expected_raw)
    np.testing.assert_allclose(
        result["distribution"][:, :, 0], expected_distribution, rtol=1e-15, atol=0.0
    )


def test_the_molecule_count_scales_the_exponent():
    single = _call(molecule_count=1)
    double = _call(molecule_count=2)
    np.testing.assert_allclose(
        double["exponent"], 2.0 * single["exponent"], rtol=1e-15, atol=0.0
    )
    doubled = _independent_seed(
        np.array([0.5, 1.0]),
        np.array([-1.0, 0.0, 1.0]),
        2.0,
        np.array([0.0]),
        np.array([2.0]),
        2.0,
        2,
        np.ones((2, 3)),
    )
    np.testing.assert_allclose(
        double["distribution"], doubled["distribution"], rtol=1e-15, atol=0.0
    )
    np.testing.assert_allclose(np.sum(double["distribution"], axis=(0, 1)), [1.0], rtol=1e-15)


# ---------------------------------------------------------------------------
# The composition contract with the quadrature and the rate average
# ---------------------------------------------------------------------------


def test_the_quadrature_volumes_normalize_the_seed_and_feed_the_rate_average():
    from scirel.collisions import average_cross_section_over_maxwellian
    from scirel.kinetic import make_cylindrical_velocity_quadrature

    vr = np.array([0.5, 1.5])
    vx = np.array([-1.5, -0.5, 0.5, 1.5])
    quadrature = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    volume = quadrature["volume"]
    seed = build_shifted_maxwellian_seed(
        vr=vr,
        vx=vx,
        tnorm_ev=20.0,
        shifted_vx_m_s=np.array([0.0]),
        temperature_ev=np.array([10.0]),
        mass_amu=2.0,
        molecule_count=1,
        cylindrical_volume=volume,
    )
    np.testing.assert_allclose(
        np.sum(volume * seed["distribution"][:, :, 0]), 1.0, rtol=1e-15
    )
    rate = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([0.0, 10.0]),
        particle_mass_amu=1.0,
        target_temperature_ev=10.0,
        target_mass_amu=2.0,
        vx=vx,
        vr=vr,
        tnorm_ev=20.0,
        cylindrical_volume=volume,
        cross_section_m2=lambda energy: np.full_like(energy, 3.0e-20),
    )
    assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)


# ---------------------------------------------------------------------------
# The input contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: _call(tnorm_ev=0.0),
        lambda: _call(tnorm_ev=-1.0),
        lambda: _call(tnorm_ev=np.nan),
        lambda: _call(mass_amu=0.0),
        lambda: _call(mass_amu=np.nan),
        lambda: _call(molecule_count=0),
        lambda: _call(molecule_count=3),
        lambda: _call(molecule_count=1.5),
        lambda: _call(temperature_ev=np.array([0.0])),
        lambda: _call(temperature_ev=np.array([-2.0])),
        lambda: _call(temperature_ev=np.array([2.0, np.nan])),
        lambda: _call(temperature_ev=np.array([[2.0]])),
        lambda: _call(shifted_vx_m_s=np.array([[0.0]])),
        lambda: _call(vr=np.array([1.0, np.nan])),
        lambda: _call(vx=np.array([0.0, np.inf, 1.0])),
        lambda: _call(vr=np.array([])),
        lambda: _call(cylindrical_volume=np.ones((3, 3))),
        lambda: _call(cylindrical_volume=np.zeros((2, 3))),
        lambda: _call(cylindrical_volume=np.full((2, 3), np.nan)),
    ],
)
def test_the_value_contract_rejects_every_out_of_domain_value(call):
    with pytest.raises(ValueError):
        call()


def test_the_inputs_are_not_modified():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 1.0])
    volume = np.ones((2, 3))
    _call(vr=vr, vx=vx, cylindrical_volume=volume)
    assert np.array_equal(vr, [0.5, 1.0])
    assert np.array_equal(vx, [-1.0, 0.0, 1.0])
    assert np.array_equal(volume, np.ones((2, 3)))
