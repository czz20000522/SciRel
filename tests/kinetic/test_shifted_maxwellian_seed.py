"""Direct contract tests for ``scirel.neutrals.shifted_maxwellian_seed``.

The relation is the neutral-transport ``create_shifted_maxwellian`` seed leaf: the
normalized exponential distribution on a cylindrical ``(vr, vx)`` mesh before
any moment compensation, with per-shift temperatures, the molecule-count
factor in the exponent, the ``-80`` tail floor and the cell-volume
normalization. The tests combine an in-file loop of the same discrete relation
with independent Maxwell–Boltzmann peak ratios and the analytic uniform-floor
limit. The old zero-exponent floor expectation is intentionally corrected.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

import scirel
from scirel.neutrals import shifted_maxwellian_seed
from scirel.neutrals.shifted_maxwellian_seed import build_shifted_maxwellian_seed

AMU = 1.6726231e-27
E_CH = 1.602177e-19


def _independent_seed(
    vr, vx, tnorm_ev, shifted_vx_m_s, temperature_ev, mass_amu, molecule_count, cylindrical_volume
):
    """Loop-per-shift formulation of the same discrete relation."""
    vth = np.sqrt(2.0 * E_CH * tnorm_ev / (mass_amu * AMU))
    radial = np.asarray(vr, dtype=float)
    axial = np.asarray(vx, dtype=float)
    layers = []
    exponents = []
    for shift, temperature in zip(shifted_vx_m_s, temperature_ev):
        argument = (
            -(radial[:, None] ** 2 + (axial[None, :] - shift / vth) ** 2)
            * molecule_count
            * tnorm_ev
            / temperature
        )
        seed = np.exp(np.maximum(argument, -80.0))
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


def test_only_the_domain_namespace_exports_the_callable():
    assert not hasattr(scirel, "build_shifted_maxwellian_seed")
    assert callable(scirel.neutrals.build_shifted_maxwellian_seed)


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


def test_the_exact_zero_argument_preserves_the_analytic_peak():
    """Maxwell–Boltzmann f=C exp(-m|v-U|²/(2eT)) gives exp(0)=1.

    The former strict-interior assertion encoded a peak hole, not a tail
    approximation; #279 intentionally corrects that scientific expectation.
    """
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
    expected_raw = np.exp(expected_exponent)
    expected_distribution = expected_raw / np.sum(expected_raw)
    np.testing.assert_allclose(
        result["distribution"][:, :, 0], expected_distribution, rtol=1e-15, atol=0.0
    )


@pytest.mark.parametrize("molecule_count", [1, 2])
@pytest.mark.parametrize("mass_amu", [1.0, 2.0])
@pytest.mark.parametrize("shift_node", [0.0, 1.0])
def test_peak_ratio_from_boltzmann_definition(molecule_count, mass_amu, shift_node):
    from scirel.neutrals import make_cylindrical_velocity_quadrature

    vr = np.array([0.0, 1.0])
    vx = np.array([-1.0, 0.0, 1.0, 2.0])
    volume = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)["volume"]
    vth = np.sqrt(2 * E_CH / (mass_amu * AMU))
    result = _call(
        vr=vr,
        vx=vx,
        tnorm_ev=1.0,
        shifted_vx_m_s=[shift_node * vth],
        temperature_ev=[1.0],
        mass_amu=mass_amu,
        molecule_count=molecule_count,
        cylindrical_volume=volume,
    )
    f = result["distribution"][:, :, 0]
    peak = int(shift_node) + 1
    # A common normalization cancels; no production kernel supplies expected.
    assert result["exponent"][0, peak, 0] == 0.0
    np.testing.assert_allclose(
        f[0, peak] / f[0, peak + 1], np.exp(molecule_count), rtol=1e-15, atol=0
    )
    np.testing.assert_allclose(np.sum(volume * f), 1.0, rtol=1e-15, atol=0)


def test_peak_and_tail_floor_coexist_in_one_slice():
    result = _call(
        vr=[0.0],
        vx=[0.0, 1.0, 8.0, 9.0],
        tnorm_ev=1.0,
        temperature_ev=[1.0],
        mass_amu=1.0,
        cylindrical_volume=np.ones((1, 4)),
    )
    f = result["distribution"][0, :, 0]
    expected = np.exp([0.0, -1.0, -64.0, -80.0])
    np.testing.assert_allclose(f, expected / np.sum(expected), rtol=1e-15, atol=0)
    np.testing.assert_array_equal(result["exponent"][0, :, 0], [0.0, -1.0, -64.0, -81.0])


def test_the_molecule_count_scales_the_exponent():
    single = _call(molecule_count=1)
    double = _call(molecule_count=2)
    np.testing.assert_allclose(double["exponent"], 2.0 * single["exponent"], rtol=1e-15, atol=0.0)
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
    from scirel.neutrals import make_cylindrical_velocity_quadrature

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
    np.testing.assert_allclose(np.sum(volume * seed["distribution"][:, :, 0]), 1.0, rtol=1e-15)
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


@pytest.mark.parametrize("name", ["tnorm_ev", "mass_amu"])
def test_numeric_string_scalars_raise_parameter_named_value_error(name):
    with pytest.raises(ValueError, match=name):
        _call(**{name: "2.0"})


@pytest.mark.parametrize(
    "name,value",
    [
        ("vr", ["0.5", "1.0"]),
        ("vx", [False, True, False]),
        ("shifted_vx_m_s", ["0.0"]),
        ("temperature_ev", ["2.0"]),
        ("cylindrical_volume", [["1.0"] * 3] * 2),
        ("vr", [0.5 + 0j, 1.0 + 0j]),
    ],
)
def test_array_ports_reject_non_real_numeric_values(name, value):
    with pytest.raises(ValueError, match=name):
        _call(**{name: value})


@pytest.mark.parametrize("value", [True, 1.0, np.array(1)])
def test_molecule_count_requires_an_integer_scalar(value):
    with pytest.raises(ValueError, match="molecule_count"):
        _call(molecule_count=value)


def test_empty_shift_list_is_rejected():
    with pytest.raises(ValueError, match="shifted_vx_m_s"):
        _call(shifted_vx_m_s=[], temperature_ev=[])


def test_numpy_integer_molecule_count_is_accepted():
    assert _call(molecule_count=np.int64(2))["distribution"].shape == (2, 3, 1)


def test_thermal_speed_uses_the_existing_saved_hydrogen_mass_convention():
    from scirel.neutrals import compute_thermal_speed_m_s

    seed = _call(tnorm_ev=20.0, mass_amu=2.0)
    scale = compute_thermal_speed_m_s(20.0, 2.0)
    assert seed["thermal_speed_m_s"] == scale["thermal_speed_m_s"]


def test_the_inputs_are_not_modified():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 1.0])
    volume = np.ones((2, 3))
    _call(vr=vr, vx=vx, cylindrical_volume=volume)
    assert np.array_equal(vr, [0.5, 1.0])
    assert np.array_equal(vx, [-1.0, 0.0, 1.0])
    assert np.array_equal(volume, np.ones((2, 3)))


# ---------------------------------------------------------------------------
# Output representability
# ---------------------------------------------------------------------------


def test_a_nonrepresentable_thermal_speed_is_rejected():
    """tnorm_ev = 1e308 is a finite positive input, but the thermal-speed
    arithmetic overflows; the finite thermal_speed_m_s contract is enforced
    rather than returning infinity."""
    with pytest.raises(ValueError, match="not representable"):
        _call(tnorm_ev=1.0e308)


def test_a_nonrepresentable_exponent_is_rejected():
    """A tiny normalization temperature with a huge shift makes shift/vth
    overflow, so the raw exponent is -inf; the finite-exponent contract on
    the exponent output is enforced (the distribution itself stays finite
    through the clamp, which is not a reason to return it with a broken
    exponent companion)."""
    with pytest.raises(ValueError, match="not representable"):
        _call(tnorm_ev=1.0e-300, shifted_vx_m_s=np.array([1.0e308]))


def test_an_underflowing_normalization_denominator_is_rejected():
    """A single 1e-320 cell volume makes the normalization denominator
    underflow relative to the raw seed, so the divided distribution overflows
    to infinity -- violating the finite, strictly-positive contract."""
    with pytest.raises(ValueError, match="not representable"):
        _call(
            vr=np.array([0.5]),
            vx=np.array([0.0]),
            cylindrical_volume=np.array([[1.0e-320]]),
        )


def test_an_overflowing_normalization_denominator_is_rejected():
    """Two 1.7e308 volumes whose volume-weighted raw seed sums overflow make
    the divided distribution collapse to exact zeros -- violating the
    strictly-positive contract (the weighted normalization sum is then zero,
    not one)."""
    with pytest.raises(ValueError, match="not representable"):
        _call(
            vr=np.array([0.5, 1.0]),
            vx=np.array([0.0]),
            cylindrical_volume=np.array([[1.7e308], [1.7e308]]),
        )
