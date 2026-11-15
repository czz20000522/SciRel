"""Direct contract tests for ``scirel.collisions.maxwellian_relative_speed_rate_average``.

The relation is the saved the neutral-transport formulation ``make_sigmav`` slice: a monoenergetic particle
directed along the axial velocity axis is averaged, through a caller-supplied
cross section, against a discretized Maxwellian target on a cylindrical
``(vr, vx)`` velocity mesh with caller-supplied cell volumes.  The maintained
tests are source-free: they re-derive every expected value from an independent
in-file formulation of the same discrete relation and from two analytic limits,
and they never import the saved bundle. A separate intake replay compares the
archived implementation when its root is supplied.
"""

from __future__ import annotations

import inspect
import math
from decimal import Decimal, localcontext

import numpy as np
import pytest

import scirel
from scirel.collisions import maxwellian_relative_speed_rate_average
from scirel.collisions.maxwellian_relative_speed_rate_average import (
    AMU_KG,
    ELEMENTARY_CHARGE_C,
    average_cross_section_over_maxwellian,
)

AMU = AMU_KG
E_CH = ELEMENTARY_CHARGE_C

PARTICLE_MASS_AMU = 1.0
TARGET_MASS_AMU = 2.0
TNORM_EV = 20.0
TARGET_TEMPERATURE_EV = 10.0
SIGMA_CONST = 3.0e-20


def _midpoint_mesh(nvr, nvx, tnorm_ev=TNORM_EV, target_mass_amu=TARGET_MASS_AMU):
    """Midpoint cylindrical mesh with vr-weighted cell volumes.

    Midpoint spacing keeps every cell volume strictly positive (the ``vr = 0``
    plane is never a node, and a nonpositive volume is rejected) while the inner
    hole shrinks with refinement, so quadrature converges.
    """
    dvr = 3.5 / nvr
    dvx = 7.0 / nvx
    vr = (np.arange(nvr) + 0.5) * dvr
    vx = (np.arange(nvx) + 0.5) * dvx - 3.5
    vth = np.sqrt(2.0 * E_CH * tnorm_ev / (target_mass_amu * AMU))
    volume = np.outer(vr * dvr, np.full(nvx, dvx)) * vth**3
    return vx, vr, volume


def _independent_average(
    particle_energy_ev,
    particle_mass_amu,
    target_temperature_ev,
    target_mass_amu,
    vx,
    vr,
    tnorm_ev,
    cylindrical_volume,
    cross_section_m2,
):
    """A from-scratch loop-per-energy formulation of the same discrete relation.

    The weights are normalized before the cross section enters and each beam
    energy is reduced separately, so the arithmetic differs from the maintained
    implementation's broadcasting path; agreement is therefore evidence about
    the relation, not about a shared code path.
    """
    vth = np.sqrt(2.0 * E_CH * tnorm_ev / (target_mass_amu * AMU))
    weight = cylindrical_volume * np.exp(
        -(vr[:, None] ** 2 + vx[None, :] ** 2) * tnorm_ev / target_temperature_ev
    )
    weight = weight / np.sum(weight)
    rates = []
    for energy in particle_energy_ev:
        vpx = np.sqrt(2.0 * E_CH * energy / (particle_mass_amu * AMU)) / vth
        vrel2 = vr[:, None] ** 2 + (vx[None, :] - vpx) ** 2
        e_coll = 0.5 * particle_mass_amu * AMU * vth**2 * vrel2 / E_CH
        sigma = np.asarray(cross_section_m2(e_coll), dtype=float)
        rates.append(vth * np.sum(weight * sigma * np.sqrt(vrel2)))
    return np.array(rates)


def _call(energies=None, sigma=None, vx=None, vr=None, volume=None, **overrides):
    vx_default, vr_default, volume_default = _midpoint_mesh(24, 36)
    arguments = dict(
        particle_energy_ev=np.array([0.0, 10.0, 100.0]) if energies is None else energies,
        particle_mass_amu=PARTICLE_MASS_AMU,
        target_temperature_ev=TARGET_TEMPERATURE_EV,
        target_mass_amu=TARGET_MASS_AMU,
        vx=vx_default if vx is None else vx,
        vr=vr_default if vr is None else vr,
        tnorm_ev=TNORM_EV,
        cylindrical_volume=volume_default if volume is None else volume,
        cross_section_m2=(lambda energy: np.full_like(energy, SIGMA_CONST))
        if sigma is None
        else sigma,
    )
    arguments.update(overrides)
    return average_cross_section_over_maxwellian(**arguments)


# ---------------------------------------------------------------------------
# The public surface
# ---------------------------------------------------------------------------


def test_the_module_publishes_exactly_one_callable_and_the_frozen_constants():
    assert maxwellian_relative_speed_rate_average.__all__ == [
        "AMU_KG",
        "ELEMENTARY_CHARGE_C",
        "average_cross_section_over_maxwellian",
    ]
    assert AMU_KG == 1.6726231e-27
    assert ELEMENTARY_CHARGE_C == 1.602177e-19


def test_only_the_domain_namespace_exports_the_callable():
    assert not hasattr(scirel, "average_cross_section_over_maxwellian")
    assert callable(scirel.collisions.average_cross_section_over_maxwellian)
    assert {"collisions"} <= set(scirel.__all__)


def test_the_signature_is_keyword_only_with_nine_required_arguments():
    signature = inspect.signature(average_cross_section_over_maxwellian)
    expected = [
        "particle_energy_ev",
        "particle_mass_amu",
        "target_temperature_ev",
        "target_mass_amu",
        "vx",
        "vr",
        "tnorm_ev",
        "cylindrical_volume",
        "cross_section_m2",
    ]
    assert list(signature.parameters) == expected
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


# ---------------------------------------------------------------------------
# The relation and its two analytic limits
# ---------------------------------------------------------------------------


def test_a_constant_cross_section_gives_a_finite_positive_energy_resolved_rate():
    rates = _call(energies=np.array([0.0, 10.0, 500.0]))
    assert rates.shape == (3,)
    assert rates.dtype == np.float64
    assert np.all(np.isfinite(rates)) and np.all(rates > 0.0)


def test_the_discrete_relation_matches_an_independent_formulation():
    vx, vr, volume = _midpoint_mesh(48, 72)
    energies = np.array([0.0, 1.0, 5.0, 50.0, 500.0])

    def sigma_linear(energy):
        return 2.0e-20 + 1.0e-22 * energy

    ours = _call(energies=energies, sigma=sigma_linear, vx=vx, vr=vr, volume=volume)
    theirs = _independent_average(
        energies,
        PARTICLE_MASS_AMU,
        TARGET_TEMPERATURE_EV,
        TARGET_MASS_AMU,
        vx,
        vr,
        TNORM_EV,
        volume,
        sigma_linear,
    )
    np.testing.assert_allclose(ours, theirs, rtol=1e-14, atol=0.0)


def test_the_rest_beam_limit_converges_to_sigma_times_the_mean_target_speed():
    """E = 0: the relative speed is the target speed, so <sigma v> -> sigma * <v>.

    The mean speed of a Maxwellian target whose temperature equals the
    normalization temperature is ``vth * 2/sqrt(pi)``; the discrete quadrature
    approaches it as the mesh is refined.
    """
    target_temperature = TNORM_EV
    vth = np.sqrt(2.0 * E_CH * TNORM_EV / (TARGET_MASS_AMU * AMU))
    analytic = SIGMA_CONST * vth * 2.0 / np.sqrt(np.pi)
    errors = []
    for nvr, nvx in ((60, 120), (120, 240), (240, 480)):
        vx, vr, volume = _midpoint_mesh(
            nvr, nvx, tnorm_ev=TNORM_EV, target_mass_amu=TARGET_MASS_AMU
        )
        rate = average_cross_section_over_maxwellian(
            particle_energy_ev=np.array([0.0]),
            particle_mass_amu=PARTICLE_MASS_AMU,
            target_temperature_ev=target_temperature,
            target_mass_amu=TARGET_MASS_AMU,
            vx=vx,
            vr=vr,
            tnorm_ev=TNORM_EV,
            cylindrical_volume=volume,
            cross_section_m2=lambda energy: np.full_like(energy, SIGMA_CONST),
        )
        errors.append(abs(float(rate[0]) - analytic) / analytic)
    assert errors[-1] < 5.0e-4
    assert errors[0] > errors[1] > errors[2], errors


def test_the_cold_target_limit_converges_to_sigma_of_the_beam_energy_times_the_beam_speed():
    """T_target << T_norm: the target is at rest, so <sigma v> -> sigma(E) * v."""
    beam_energy = 100.0
    vx, vr, volume = _midpoint_mesh(200, 300, tnorm_ev=TNORM_EV, target_mass_amu=TARGET_MASS_AMU)

    def sigma_linear(energy):
        return 2.0e-20 + 1.0e-22 * energy

    rate = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([beam_energy]),
        particle_mass_amu=PARTICLE_MASS_AMU,
        target_temperature_ev=0.05,
        target_mass_amu=TARGET_MASS_AMU,
        vx=vx,
        vr=vr,
        tnorm_ev=TNORM_EV,
        cylindrical_volume=volume,
        cross_section_m2=sigma_linear,
    )
    v_beam = np.sqrt(2.0 * E_CH * beam_energy / (PARTICLE_MASS_AMU * AMU))
    analytic = sigma_linear(np.array([beam_energy]))[0] * v_beam
    assert abs(float(rate[0]) - analytic) / analytic < 5.0e-3


def test_a_constant_rescaling_of_the_volume_weights_leaves_the_rate_unchanged():
    """The target distribution is normalized by the supplied weights, so only
    their relative sizes enter the quadrature."""
    vx, vr, volume = _midpoint_mesh(24, 36)
    base = _call(vx=vx, vr=vr, volume=volume)
    scaled = _call(vx=vx, vr=vr, volume=volume * 7.5)
    np.testing.assert_allclose(base, scaled, rtol=1e-14, atol=0.0)


def test_the_inputs_are_not_modified():
    vx, vr, volume = _midpoint_mesh(24, 36)
    energies = np.array([0.0, 10.0])
    kept = dict(
        particle_energy_ev=energies.copy(),
        vx=vx.copy(),
        vr=vr.copy(),
        cylindrical_volume=volume.copy(),
    )
    _call(
        energies=kept["particle_energy_ev"],
        vx=kept["vx"],
        vr=kept["vr"],
        volume=kept["cylindrical_volume"],
    )
    assert np.array_equal(kept["particle_energy_ev"], energies)
    assert np.array_equal(kept["vx"], vx)
    assert np.array_equal(kept["vr"], vr)
    assert np.array_equal(kept["cylindrical_volume"], volume)


# ---------------------------------------------------------------------------
# The composition contract of the saved single-node graph
# ---------------------------------------------------------------------------


def test_the_saved_graph_contract_consumes_one_immutable_mesh_snapshot():
    """The saved 粒子靶Maxwellian速率系数图 is an identity single-node composition:
    N1 owns mesh production and N2 consumes one immutable snapshot.  The
    maintained composition contract is that a caller-side snapshot feeds the
    operator by port name, is consumed unmodified, and the returned rate lands
    in a caller-side energy-resolved table without reshaping.
    """
    vx, vr, volume = _midpoint_mesh(24, 36)
    energies = np.array([1.0, 10.0, 100.0])
    snapshot = dict(vx=vx.copy(), vr=vr.copy(), tnorm_ev=TNORM_EV, cylindrical_volume=volume.copy())
    rate_table = {
        float(energy): average_cross_section_over_maxwellian(
            particle_energy_ev=np.array([energy]),
            particle_mass_amu=PARTICLE_MASS_AMU,
            target_temperature_ev=TARGET_TEMPERATURE_EV,
            target_mass_amu=TARGET_MASS_AMU,
            vx=snapshot["vx"],
            vr=snapshot["vr"],
            tnorm_ev=snapshot["tnorm_ev"],
            cylindrical_volume=snapshot["cylindrical_volume"],
            cross_section_m2=lambda energy: np.full_like(energy, SIGMA_CONST),
        )[0]
        for energy in energies
    }
    assert set(rate_table) == {1.0, 10.0, 100.0}
    assert all(np.isfinite(value) and value > 0.0 for value in rate_table.values())
    assert np.array_equal(snapshot["vx"], vx)
    assert np.array_equal(snapshot["vr"], vr)
    assert np.array_equal(snapshot["cylindrical_volume"], volume)


# ---------------------------------------------------------------------------
# The input contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: _call(energies=np.array([])),
        lambda: _call(energies=np.array([[1.0]])),
        lambda: _call(energies=np.array([-1.0, 10.0])),
        lambda: _call(energies=np.array([1.0, np.nan])),
        lambda: _call(energies=np.array([1.0, np.inf])),
        lambda: _call(particle_mass_amu=0.0),
        lambda: _call(particle_mass_amu=-1.0),
        lambda: _call(particle_mass_amu=np.nan),
        lambda: _call(particle_mass_amu=np.array([1.0])),
        lambda: _call(target_temperature_ev=0.0),
        lambda: _call(target_temperature_ev=-5.0),
        lambda: _call(target_temperature_ev=np.inf),
        lambda: _call(target_mass_amu=0.0),
        lambda: _call(target_mass_amu=np.nan),
        lambda: _call(tnorm_ev=0.0),
        lambda: _call(tnorm_ev=-1.0),
        lambda: _call(tnorm_ev=np.array([20.0])),
        lambda: _call(vx=np.zeros((2, 2))),
        lambda: _call(vx=np.array([1.0, np.nan])),
        lambda: _call(vr=np.array([1.0, np.nan])),
        lambda: _call(vr=np.zeros((3,))),
        lambda: _call(volume=np.ones((36, 24))),
        lambda: _call(volume=np.ones((24, 36, 1))),
        lambda: _call(volume=np.full((24, 36), -1.0)),
        lambda: _call(volume=np.full((24, 36), 0.0)),
        lambda: _call(volume=np.full((24, 36), np.nan)),
        lambda: _call(sigma="not callable"),
    ],
)
def test_the_value_contract_rejects_every_out_of_domain_value(call):
    with pytest.raises(ValueError):
        call()


def test_a_nonpositive_or_nonfinite_volume_is_rejected():
    vx, vr, volume = _midpoint_mesh(24, 36)
    volume[5, 7] = 0.0
    with pytest.raises(ValueError) as raised:
        _call(vx=vx, vr=vr, volume=volume)
    assert "cylindrical_volume" in str(raised.value)


@pytest.mark.parametrize(
    "sigma",
    [
        lambda energy: np.full_like(energy, -1.0e-20),
        lambda energy: np.full_like(energy, np.nan),
        lambda energy: np.full_like(energy, np.inf),
    ],
)
def test_a_nonfinite_or_negative_cross_section_value_is_rejected(sigma):
    with pytest.raises(ValueError) as raised:
        _call(sigma=sigma)
    assert "cross_section_m2" in str(raised.value)


def test_a_cross_section_with_the_wrong_shape_is_rejected():
    def wrong_shape(energy):
        return np.ones(energy.shape[:2])

    with pytest.raises(ValueError) as raised:
        _call(sigma=wrong_shape)
    assert "cross_section_m2" in str(raised.value)


def test_the_rejection_messages_name_the_parameter():
    with pytest.raises(ValueError) as raised:
        _call(energies=np.array([-1.0]))
    assert "particle_energy_ev" in str(raised.value)
    with pytest.raises(ValueError) as raised:
        _call(target_temperature_ev=0.0)
    assert "target_temperature_ev" in str(raised.value)
    with pytest.raises(ValueError) as raised:
        _call(vx=np.zeros((2, 2)))
    assert "vx" in str(raised.value)


def test_a_nonrepresentable_rate_is_rejected_rather_than_returned():
    """A finite cross section whose product with the rate prefactor overflows
    cannot satisfy the finite-output contract and is rejected.

    This is a repair relative to the saved implementation, which returned the
    non-finite rate silently; the saved document itself declares the result
    finite.
    """

    def huge_sigma(energy):
        return np.full_like(energy, 1.0e305)

    with pytest.raises(ValueError) as raised:
        _call(sigma=huge_sigma)
    assert "not representable" in str(raised.value)


def test_nonrepresentable_collision_energies_are_rejected_before_the_callback():
    """An extreme-but-finite energy overflows the collision-energy arithmetic.

    ``2 e E / (m amu)`` overflows for ``E = 1e308``, so the sampled
    collision energies are infinite while every input satisfies the stated
    finite domain.  The public failure contract requires the asset itself to
    reject them *before* the cross-section callable is invoked: the saved
    implementation handed the non-finite array to the callback first, so a
    validating callback observed values the asset never declared, and the
    asset's own failure surfaced only after the callback had run.
    """
    observed = []

    def recording_sigma(energy):
        observed.append(np.asarray(energy))
        return np.full_like(energy, SIGMA_CONST)

    with pytest.raises(ValueError) as raised:
        _call(energies=np.array([1.0e308]), sigma=recording_sigma)
    assert "not representable" in str(raised.value)
    assert observed == [], "the callable must not observe non-finite collision energies"


@pytest.mark.parametrize(
    "name",
    [
        "particle_mass_amu",
        "target_mass_amu",
        "target_temperature_ev",
        "tnorm_ev",
    ],
)
def test_numeric_string_scalar_is_rejected_by_name(name):
    with pytest.raises(ValueError, match=name):
        _call(**{name: "2.0"})


@pytest.mark.parametrize(
    "name,value",
    [
        ("particle_energy_ev", ["1.0"]),
        ("vx", [False] * 36),
        ("vr", [0.5 + 0j] * 24),
        ("cylindrical_volume", [["1.0"] * 36] * 24),
    ],
)
def test_array_inputs_require_real_numeric_values(name, value):
    with pytest.raises(ValueError, match=name):
        if name == "particle_energy_ev":
            _call(energies=value)
        elif name == "cylindrical_volume":
            _call(volume=value)
        else:
            _call(**{name: value})


def test_cross_section_numeric_strings_are_rejected():
    with pytest.raises(ValueError, match="cross_section_m2"):
        _call(sigma=lambda energy: np.full(energy.shape, "1e-20"))


def test_maxwellian_weight_scale_invariance_at_finite_large_weights():
    # Original F1 witness: keep its inputs and 1e-14 assertion unchanged.
    kwargs = dict(
        particle_energy_ev=np.array([1.0]),
        particle_mass_amu=1.0,
        target_temperature_ev=1.0,
        target_mass_amu=1.0,
        vx=np.array([-1.0, 0.0, 1.0]),
        vr=np.array([0.5, 1.0]),
        tnorm_ev=1.0,
        cross_section_m2=lambda e: np.full_like(e, 1.0e-20),
    )
    ordinary = average_cross_section_over_maxwellian(cylindrical_volume=np.ones((2, 3)), **kwargs)
    scaled = average_cross_section_over_maxwellian(
        cylindrical_volume=np.full((2, 3), 1.0e308), **kwargs
    )
    # Every weight is finite. A common multiplier cancels algebraically.
    np.testing.assert_allclose(scaled, ordinary, rtol=1.0e-14, atol=0.0)


def _decimal_mesh_average(vr, vx, volume, sigma, energy=1.0):
    """90-digit scalar sum, with no production constants, weights or rates.

    The frozen mass/charge values and unit temperatures/masses are explicit.
    Decimal.from_float binds extreme weights and coordinates to the actual
    binary64 inputs rather than silently replacing them by decimal roundings.
    """
    with localcontext() as ctx:
        ctx.prec = 90
        d = Decimal.from_float
        thermal_speed = (2 * Decimal("1.602177e-19") / Decimal("1.6726231e-27")).sqrt()
        beam_speed = d(float(energy)).sqrt()
        numerator = denominator = Decimal(0)
        for i, r in enumerate(vr):
            for j, x in enumerate(vx):
                radial, axial = d(float(r)), d(float(x))
                weight = d(float(volume[i, j])) * (-(radial**2 + axial**2)).exp()
                speed = (radial**2 + (axial - beam_speed) ** 2).sqrt()
                denominator += weight
                numerator += weight * d(float(sigma[i, j])) * speed
        return float(thermal_speed * numerator / denominator)


def _unit_temperature_average(vr, vx, volume, sigma, energy=1.0):
    return average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([energy]),
        particle_mass_amu=1.0,
        target_temperature_ev=1.0,
        target_mass_amu=1.0,
        vr=np.asarray(vr),
        vx=np.asarray(vx),
        tnorm_ev=1.0,
        cylindrical_volume=volume,
        cross_section_m2=lambda sampled: np.broadcast_to(sigma, sampled.shape),
    )


@pytest.mark.parametrize("scale", [1.0, 7.5, 1e307, 1e308, 1e-307, 1e-308, 5e-324])
def test_extreme_common_weight_scales_match_decimal(scale):
    vr, vx = [0.5, 1.0], [-1.0, 0.0, 1.0]
    volume, sigma = np.full((2, 3), scale), np.full((2, 3), 1e-20)
    expected = _decimal_mesh_average(vr, vx, volume, sigma)
    actual = _unit_temperature_average(vr, vx, volume, sigma)
    assert expected > 0.0
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


@pytest.mark.parametrize("small,large", [(1e-300, 1e300), (1e-308, 1e308)])
def test_nonuniform_weights_and_gaussian_exponents_compensate(small, large):
    vr, vx = [0.0, np.sqrt(1400.0)], [0.0]
    volume, sigma = np.array([[small], [large]]), np.full((2, 1), 1e-20)
    expected = _decimal_mesh_average(vr, vx, volume, sigma)
    actual = _unit_temperature_average(vr, vx, volume, sigma)
    # Budget fixed before running: exponent evaluation at ~1400 can lose ~1e-13.
    np.testing.assert_allclose(actual, [expected], rtol=5e-13, atol=0.0)


def test_a_common_underflowing_gaussian_factor_cancels():
    vr, vx = [np.sqrt(1000.0)], [-1.0, 0.0, 1.0]
    volume, sigma = np.ones((1, 3)), np.full((1, 3), 1e-20)
    expected = _decimal_mesh_average(vr, vx, volume, sigma)
    actual = _unit_temperature_average(vr, vx, volume, sigma)
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


def test_tiny_probability_times_large_cross_section_is_not_lost():
    vr, vx = [0.0, np.sqrt(1000.0)], [0.0]
    volume, sigma = np.ones((2, 1)), np.array([[0.0], [1e300]])
    expected = _decimal_mesh_average(vr, vx, volume, sigma)
    actual = _unit_temperature_average(vr, vx, volume, sigma)
    assert expected > 0.0
    np.testing.assert_allclose(actual, [expected], rtol=5e-13, atol=0.0)


def test_intermediate_weight_cross_section_overflow_does_not_reject_a_finite_rate():
    vr, vx = [0.5, 1.0], [-1.0, 0.0, 1.0]
    volume, sigma = np.full((2, 3), 1e300), np.full((2, 3), 1e20)
    expected = _decimal_mesh_average(vr, vx, volume, sigma)
    actual = _unit_temperature_average(vr, vx, volume, sigma)
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


def test_a_positive_unrepresentable_rate_is_rejected_instead_of_zero():
    with pytest.raises(ValueError, match="not representable"):
        _unit_temperature_average(
            [1e-150], [0.0], np.ones((1, 1)), np.full((1, 1), 5e-324), energy=0.0
        )


@pytest.mark.parametrize("zero_speed", [False, True])
def test_exact_zero_rates_are_distinct_from_underflow(zero_speed):
    vr = [0.0] if zero_speed else [1.0]
    sigma = np.array([[1e308 if zero_speed else 0.0]])
    actual = _unit_temperature_average(vr, [0.0], np.ones((1, 1)), sigma, energy=0.0)
    np.testing.assert_array_equal(actual, [0.0])


@pytest.mark.parametrize("vr,vx", [([], [0.0]), ([0.0], [])])
def test_an_empty_mesh_has_no_normalizable_target_mass(vr, vx):
    observed = []

    def sigma(sampled):
        observed.append(sampled.copy())
        return np.ones_like(sampled)

    with pytest.raises(ValueError, match="target Maxwellian"):
        _call(vr=np.array(vr), vx=np.array(vx), volume=np.ones((len(vr), len(vx))), sigma=sigma)
    assert observed == []


@pytest.mark.parametrize("radius,energy", [(1e-200, 0.0), (1e-160, 0.0), (0.0, 5e-324)])
def test_underflowing_kinematics_are_rejected_before_the_callback(radius, energy):
    observed = []

    def sigma(sampled):
        observed.append(sampled.copy())
        return np.full_like(sampled, 1e300)

    with pytest.raises(ValueError, match="not representable"):
        _call(
            energies=np.array([energy]),
            vr=np.array([radius]),
            vx=np.array([0.0]),
            volume=np.ones((1, 1)),
            particle_mass_amu=1.0,
            target_mass_amu=1.0,
            tnorm_ev=1.0,
            target_temperature_ev=1.0,
            sigma=sigma,
        )
    assert observed == []


def test_the_cross_section_callback_exception_is_propagated_unchanged():
    error = RuntimeError("caller cross-section failure")

    def sigma(energy):
        raise error

    with pytest.raises(RuntimeError) as raised:
        _call(sigma=sigma)
    assert raised.value is error


def test_compensating_weights_keep_readonly_inputs_and_callback_shape():
    vr, vx = np.array([0.0, np.sqrt(1400.0)]), np.array([0.0])
    volume = np.array([[1e-308], [1e308]])
    kept = [a.copy() for a in (vr, vx, volume)]
    for array in (vr, vx, volume):
        array.flags.writeable = False
    observed = []

    def sigma(energy):
        observed.append(energy.copy())
        return np.full_like(energy, 1e-20)

    actual = _call(
        energies=np.array([0.0, 1.0]),
        vr=vr,
        vx=vx,
        volume=volume,
        particle_mass_amu=1.0,
        target_mass_amu=1.0,
        tnorm_ev=1.0,
        target_temperature_ev=1.0,
        sigma=sigma,
    )
    assert actual.shape == (2,) and actual.dtype == np.float64
    assert len(observed) == 1 and observed[0].shape == (2, 2, 1)
    assert np.all(np.isfinite(observed[0]))
    for array, before in zip((vr, vx, volume), kept, strict=True):
        np.testing.assert_array_equal(array, before)
        assert not array.flags.writeable


def test_common_axial_exponent_keeps_radial_probability_for_comoving_beam():
    # Review A: the common exp(-1e16) cancels; it must not erase exp(-vr**2).
    # The retained float64 kinematics give beam=100000000.00000001, not 1e8.
    # Bind that original arithmetic independently, then use Decimal probabilities;
    # do not absorb the tiny nonzero relative speed into a changed tolerance.
    thermal = math.sqrt(2.0 * 1.602177e-19 / 1.6726231e-27)
    beam = math.sqrt(2.0 * 1.602177e-19 * 1e16 / 1.6726231e-27) / thermal
    assert beam == np.nextafter(1e8, np.inf)
    with localcontext() as context:
        context.prec = 100
        d = Decimal.from_float
        delta = abs(d(1e8) - d(beam))
        tail = Decimal(-1).exp()
        expected = float(
            d(thermal) * d(1e-20) * (delta + tail * (1 + delta * delta).sqrt()) / (1 + tail)
        )
    actual = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([1e16]),
        particle_mass_amu=1.0,
        target_temperature_ev=1.0,
        target_mass_amu=1.0,
        tnorm_ev=1.0,
        vr=np.array([0.0, 1.0]),
        vx=np.array([1e8]),
        cylindrical_volume=np.ones((2, 1)),
        cross_section_m2=lambda energy: np.full(energy.shape, 1e-20),
    )
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


@pytest.mark.parametrize("radius", [1e8, 1e100])
def test_common_radial_exponent_keeps_axial_probability(radius):
    # Review A: P(vx=1)=1/(1+exp(1)), independent of the single radial row.
    with localcontext() as context:
        context.prec = 110
        vth = (2 * Decimal("1.602177e-19") / Decimal("1.6726231e-27")).sqrt()
        r = Decimal.from_float(radius)
        expected = float(
            vth * (r * r + 1).sqrt() * Decimal.from_float(1e-20) / (1 + Decimal(1).exp())
        )
    actual = _unit_temperature_average(
        [radius], [0.0, 1.0], np.ones((1, 2)), np.array([[0.0, 1e-20]]), energy=0.0
    )
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


def test_large_common_radial_exponent_preserves_threshold_callback_average():
    # Review B: the callback selects vx=-1, whose probability is e^-1/(1+2e^-1).
    with localcontext() as context:
        context.prec = 110
        r = Decimal.from_float(1e8)
        vth = (2 * Decimal("1.602177e-19") / Decimal("1.6726231e-27")).sqrt()
        tail = Decimal(-1).exp()
        expected = float(
            vth * Decimal.from_float(1e-20) * (r * r + (r + 1) ** 2).sqrt() * tail / (1 + 2 * tail)
        )
    seen = []

    def sigma(energy):
        seen.append(energy.copy())
        return np.where(energy > 2e16, 1e-20, 0.0)

    actual = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([1e16]),
        particle_mass_amu=1.0,
        target_temperature_ev=1.0,
        target_mass_amu=1.0,
        tnorm_ev=1.0,
        vr=np.array([1e8]),
        vx=np.array([-1.0, 0.0, 1.0]),
        cylindrical_volume=np.ones((1, 3)),
        cross_section_m2=sigma,
    )
    assert len(seen) == 1
    np.testing.assert_array_equal(seen[0] > 2e16, [[[True, False, False]]])
    np.testing.assert_allclose(actual, [expected], rtol=5e-13, atol=0.0)


def test_neighboring_large_coordinates_keep_the_scaled_square_difference():
    radial = np.array([1e154, np.nextafter(1e154, np.inf)])
    norm = 1e-300
    with localcontext() as context:
        context.prec = 110
        d = Decimal.from_float
        a, b = map(d, radial)
        delta = (b * b - a * a) * d(norm)
        p1 = (-delta).exp() / (1 + (-delta).exp())
        # The original 2*e*T_norm intermediate is subnormal here. This test
        # isolates Gaussian accuracy; its speed unit binds the unchanged scalar
        # expression rather than claiming that expression is high precision.
        vth = d(math.sqrt(2.0 * 1.602177e-19 * norm / 1.6726231e-27))
        expected = float(vth * b * d(1e-20) * p1)
    actual = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([0.0]),
        particle_mass_amu=1.0,
        target_temperature_ev=1.0,
        target_mass_amu=1.0,
        tnorm_ev=norm,
        vr=radial,
        vx=np.array([0.0]),
        cylindrical_volume=np.ones((2, 1)),
        cross_section_m2=lambda energy: np.broadcast_to([[0.0], [1e-20]], energy.shape),
    )
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


@pytest.mark.parametrize("kind", ["divide", "under", "over", "invalid"])
def test_callback_retains_the_callers_numpy_error_policy(kind):
    observed = []

    def sigma(energy):
        observed.append(np.geterr())
        if kind == "divide":
            np.divide(np.float64(1.0), np.float64(0.0))
        elif kind == "under":
            np.multiply(np.float64(1e-300), np.float64(1e-300))
        elif kind == "over":
            np.multiply(np.float64(1e300), np.float64(1e300))
        else:
            np.sqrt(np.float64(-1.0))
        return np.full_like(energy, 1e-20)

    with np.errstate(all="raise"):
        with pytest.raises(FloatingPointError):
            _call(sigma=sigma)
        assert np.geterr() == dict(divide="raise", over="raise", under="raise", invalid="raise")
    assert observed == [dict(divide="raise", over="raise", under="raise", invalid="raise")]


@pytest.mark.parametrize("norm,temperature", [(1.0, 5e-324), (5e-324, 1e308)])
def test_unrepresentable_gaussian_differences_are_rejected_before_callback(norm, temperature):
    seen = []

    def sigma(energy):
        seen.append(energy.copy())
        return np.full_like(energy, 1e-20)

    with pytest.raises(ValueError, match="not representable"):
        _call(
            energies=np.array([1.0]),
            vr=np.array([0.0, 1.0]),
            vx=np.array([0.0]),
            volume=np.ones((2, 1)),
            tnorm_ev=norm,
            target_temperature_ev=temperature,
            sigma=sigma,
        )
    assert seen == []


def test_unrepresentable_combined_gaussian_difference_is_rejected_before_callback():
    seen = []

    def sigma(energy):
        seen.append(energy.copy())
        return np.full_like(energy, 1e-20)

    with pytest.raises(ValueError, match="target Maxwellian.*not representable"):
        _call(
            energies=np.array([1.0]),
            vr=np.array([0.0, 1e154]),
            vx=np.array([0.0, 1e154]),
            volume=np.ones((2, 2)),
            tnorm_ev=1.0,
            target_temperature_ev=1.0,
            sigma=sigma,
        )
    assert seen == []
