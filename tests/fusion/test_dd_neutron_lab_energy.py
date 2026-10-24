"""Laboratory-ray DD kinematics, with independent velocity conservation oracles."""
from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction
import importlib
import inspect
import math

import numpy as np
import pytest

from scirel.fusion.dd_neutron_lab_energy import (
    ATOMIC_MASS_KG,
    DD_Q_VALUE_MEV,
    DEUTERON_MASS_AMU,
    DETECTOR_NORM_ATOL,
    HELIUM3_MASS_AMU,
    MEV_J,
    NEUTRON_MASS_AMU,
    NON_REPRESENTABLE_MESSAGE,
    calculate_dd_neutron_lab_energy_kev,
)

TARGET = importlib.import_module("scirel.fusion.dd_neutron_lab_energy")
DETECTOR_FORWARD = np.array([1.0, 0.0, 0.0])
STATIONARY = np.zeros(3)
STATIONARY_ANCHOR_KEV = 2450.47589941598


def call(v1, v2, detector=DETECTOR_FORWARD):
    return calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=v1,
        reactant2_velocity_cm_s=v2,
        detector_unit_vector=detector,
    )


def centre_of_mass_terms(v1, v2):
    """Independent double-precision mass partition and boost, in keV."""
    first, second = np.asarray(v1, dtype=float), np.asarray(v2, dtype=float)
    relative, centre = first - second, (first + second) / 2
    available = (
        0.5 * (DEUTERON_MASS_AMU / 2.0) * ATOMIC_MASS_KG
        * float(np.dot(relative, relative)) * 1.0e-4 / MEV_J + DD_Q_VALUE_MEV
    )
    cm = HELIUM3_MASS_AMU / (NEUTRON_MASS_AMU + HELIUM3_MASS_AMU) * available
    boost = 0.5 * NEUTRON_MASS_AMU * ATOMIC_MASS_KG * float(np.dot(centre, centre)) * 1.0e-4 / MEV_J
    return cm * 1000, boost * 1000


def conservation_data(v1, v2, detector):
    """Decimal laboratory velocity sphere from exact input-float values.

    This oracle does not call the production rational classifier or closed root.
    Unit conversion uses the same declared binary64 numerical factor 1e-4.
    """
    first, second, raw = (
        tuple(Decimal.from_float(float(component)) for component in vector)
        for vector in (v1, v2, detector)
    )
    md, mn, mh, unit, mev, conversion, q_value = (
        Decimal.from_float(value)
        for value in (DEUTERON_MASS_AMU, NEUTRON_MASS_AMU, HELIUM3_MASS_AMU,
                      ATOMIC_MASS_KG, MEV_J, 1.0e-4, DD_Q_VALUE_MEV)
    )
    centre = tuple((x + y) / 2 for x, y in zip(first, second))
    relative_squared = sum((x - y) ** 2 for x, y in zip(first, second))
    available = q_value + md * unit * conversion * relative_squared / (4 * mev)
    energy = mh * available / (mn + mh)
    coefficient = mn * unit * conversion / (2 * mev)
    norm = sum(x*x for x in raw).sqrt()
    direction = tuple(x / norm for x in raw)
    return centre, direction, energy / coefficient, coefficient


def bracketed_velocity_oracle(v1, v2, detector=DETECTOR_FORWARD):
    """Find the unique positive root by bisection of velocity conservation.

    Used only when the origin lies strictly inside the CM velocity sphere.  It
    evaluates the three Cartesian velocity differences, rather than the closed
    quadratic formula or the CM emission-angle expression.
    """
    with localcontext() as context:
        context.prec = 120
        centre, direction, u_squared, coefficient = conservation_data(v1, v2, detector)

        def residual(speed):
            return sum((speed*n - v)**2 for n, v in zip(direction, centre)) - u_squared

        lower = Decimal(0)
        assert residual(lower) < 0
        upper = 2 * (sum(v*v for v in centre).sqrt() + u_squared.sqrt())
        assert residual(upper) > 0
        for _ in range(500):
            midpoint = (lower + upper) / 2
            if midpoint == lower or midpoint == upper:
                break
            if residual(midpoint) > 0:
                upper = midpoint
            else:
                lower = midpoint
        speed = (lower + upper) / 2
        return float(1000 * coefficient * speed * speed)


def test_the_call_returns_a_plain_float_and_not_a_mapping():
    result = call((1e8, 0, 0), (5e7, 0, 0))
    assert type(result) is float
    assert not isinstance(result, dict)
    assert not hasattr(TARGET, "angular_weight")


def test_stationary_reactants_return_the_mass_partition_energy():
    closed_form = 1000 * HELIUM3_MASS_AMU * DD_Q_VALUE_MEV / (NEUTRON_MASS_AMU + HELIUM3_MASS_AMU)
    assert closed_form == pytest.approx(STATIONARY_ANCHOR_KEV, rel=1e-15)
    assert call(STATIONARY, STATIONARY) == STATIONARY_ANCHOR_KEV
    assert call(STATIONARY, STATIONARY, (0, 1, 0)) == STATIONARY_ANCHOR_KEV


def test_zero_boost_counterstreaming_reactants_have_direction_independent_energy():
    v1, v2 = (1.2e8, -4e7, 2e7), (-1.2e8, 4e7, -2e7)
    expected = bracketed_velocity_oracle(v1, v2)
    for detector in ((1, 0, 0), (0, -1, 0), (0, 0, 1)):
        assert call(v1, v2, detector) == pytest.approx(expected, rel=1e-12)


def test_perpendicular_laboratory_ray_obeys_velocity_conservation():
    velocity = np.array([1e8, 0, 0])
    centre, boost = centre_of_mass_terms(velocity, velocity)
    result = call(velocity, velocity, (0, 1, 0))
    assert result == pytest.approx(centre - boost, rel=1e-12)
    assert result == pytest.approx(bracketed_velocity_oracle(velocity, velocity, (0, 1, 0)), rel=1e-12)


def test_a_forward_detector_exceeds_a_reverse_detector():
    v1, v2 = (1e8, 0, 0), (5e7, 0, 0)
    assert call(v1, v2) > call(v1, v2, -DETECTOR_FORWARD) > 0


@pytest.mark.parametrize("speed", [5e7, 2e8, 5e8, 2e9])
def test_reachable_collinear_energy_is_the_two_body_square_root_bracket(speed):
    velocity = np.array([speed, 0, 0])
    centre, boost = centre_of_mass_terms(velocity, STATIONARY)
    lower = (math.sqrt(centre) - math.sqrt(boost))**2
    upper = (math.sqrt(centre) + math.sqrt(boost))**2
    reverse = call(velocity, STATIONARY, -DETECTOR_FORWARD)
    forward = call(velocity, STATIONARY)
    assert abs(reverse - lower) <= 1e-12 * max(lower, 1)
    assert abs(forward - upper) <= 1e-12 * max(upper, 1)
    assert lower >= 0
    assert forward > reverse


@pytest.mark.parametrize("speed", [2165199149.095274, 2165199149.0952773, 2165199149.095298])
@pytest.mark.parametrize("sign", [-1, 1])
def test_nearly_stationary_outgoing_neutrons_remain_positive(speed, sign):
    velocity = (sign * speed, 0, 0)
    detector = (-sign, 0, 0)
    result = call(velocity, velocity, detector)
    expected = bracketed_velocity_oracle(velocity, velocity, detector)
    assert result > 0
    assert result < 1e-24
    assert result == pytest.approx(expected, rel=1e-12, abs=0)


@pytest.mark.parametrize("detector, message", [
    ((-1, 0, 0), "no strictly positive"),
    ((0, 1, 0), "no real"),
    ((1, 0, 0), "two distinct positive"),
])
def test_high_boost_rays_reject_no_solution_and_two_solutions(detector, message):
    with pytest.raises(ValueError, match=message):
        call((3e9, 0, 0), (3e9, 0, 0), detector)


def geometric_energy(centre, u_squared, detector=(1, 0, 0)):
    """Exact, constructible velocity-sphere geometry for equality boundaries."""
    return TARGET._unique_lab_energy_kev(
        tuple(map(Fraction, centre)), Fraction(u_squared),
        tuple(map(Fraction, detector)), Fraction(1),
    )


def test_exact_positive_tangency_is_one_root_and_zero_speed_is_not_an_outgoing_ray():
    # Unit-radius sphere centred at (2,1,0) touches the x ray at speed 2.
    assert geometric_energy((2, 1, 0), 1) == 4000
    # At (0,1,0) the tangent is the ray origin: it cannot reach a detector.
    with pytest.raises(ValueError, match="no strictly positive"):
        geometric_energy((0, 1, 0), 1)
    with pytest.raises(ValueError, match="no strictly positive"):
        geometric_energy((-2, 1, 0), 1)
    # A zero root is excluded, but the other strictly positive root is unique.
    assert geometric_energy((1, 0, 0), 1) == 4000
    with pytest.raises(ValueError, match="no strictly positive"):
        geometric_energy((-1, 0, 0), 1)


def test_distinct_roots_one_ulp_from_tangency_are_never_merged():
    inside = np.nextafter(1.0, 0.0)
    outside = np.nextafter(1.0, np.inf)
    with pytest.raises(ValueError, match="two distinct positive"):
        geometric_energy((2, inside, 0), 1)
    with pytest.raises(ValueError, match="no real"):
        geometric_energy((2, outside, 0), 1)


def test_public_near_tangent_rays_are_classified_without_a_root_merging_tolerance():
    with localcontext() as context:
        context.prec = 120
        _, _, u_squared, _ = conservation_data(STATIONARY, STATIONARY, DETECTOR_FORWARD)
        nearest_speed = float(u_squared.sqrt())
    below = np.nextafter(nearest_speed, 0.0)
    above = np.nextafter(nearest_speed, np.inf)
    with pytest.raises(ValueError, match="two distinct positive"):
        call((1e9, below, 0), (1e9, below, 0))
    with pytest.raises(ValueError, match="no real"):
        call((1e9, above, 0), (1e9, above, 0))


def test_a_detector_at_the_norm_tolerance_boundary_is_not_inflated():
    v1, v2 = (1e8, 0, 0), (5e7, 0, 0)
    boundary = np.array([1 + 1e-13, 0, 0])
    assert np.linalg.norm(boundary) > 1
    assert call(v1, v2, boundary) == call(v1, v2)
    direction = np.array([1.0, 2.0, 3.0]) / math.sqrt(14)
    assert call(v1, v2, direction * (1 + 1e-13)) == pytest.approx(call(v1, v2, direction), rel=1e-12)


def test_exchange_and_common_rotation_preserve_the_energy():
    v1 = np.array([1.3e8, 2e7, -1e7])
    v2 = np.array([-2e7, 4e7, 3e7])
    direction = np.array([0.3, -0.8, 0.5]); direction /= np.linalg.norm(direction)
    expected = call(v1, v2, direction)
    assert call(v2, v1, direction) == expected
    rotation = np.array([[0, -1, 0], [0, 0, 1], [-1, 0, 0]])
    assert call(rotation @ v1, rotation @ v2, rotation @ direction) == expected
    angle = 0.71
    rotation = np.array([[math.cos(angle), -math.sin(angle), 0],
                         [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
    assert call(rotation @ v1, rotation @ v2, rotation @ direction) == pytest.approx(expected, rel=1e-12)
    assert expected == pytest.approx(bracketed_velocity_oracle(v1, v2, direction), rel=1e-12)


def test_generated_cm_vectors_reconstruct_laboratory_direction_and_energy():
    # An independent generative oracle: boost a chosen CM neutron vector, then
    # ask the callable for the energy along that resulting laboratory velocity.
    with localcontext() as context:
        context.prec = 120
        _, _, u_squared, coefficient = conservation_data(STATIONARY, STATIONARY, DETECTOR_FORWARD)
        speed, factor = float(u_squared.sqrt()), float(coefficient)
    rng = np.random.default_rng(20261023)
    for _ in range(120):
        cm_direction = rng.normal(size=3); cm_direction /= np.linalg.norm(cm_direction)
        centre_velocity = rng.uniform(-1e8, 1e8, size=3)
        laboratory_velocity = centre_velocity + speed * cm_direction
        laboratory_speed = np.linalg.norm(laboratory_velocity)
        detector = laboratory_velocity / laboratory_speed
        expected = 1000 * factor * np.dot(laboratory_velocity, laboratory_velocity)
        actual = call(centre_velocity, centre_velocity, detector)
        assert actual == pytest.approx(expected, rel=1e-12)
        reconstructed = math.sqrt(actual / (1000 * factor)) * detector
        np.testing.assert_allclose(reconstructed, laboratory_velocity, rtol=1e-12, atol=1e-6)
        assert np.dot(reconstructed - centre_velocity, reconstructed - centre_velocity) == pytest.approx(speed**2, rel=1e-12)


@pytest.mark.parametrize("speed", [1e6, 1e8, 4e8, 1e9, 2e9, 3e9, 1e10])
def test_accepted_energies_across_velocity_scales_agree_with_velocity_conservation(speed):
    rng = np.random.default_rng(20260920)
    for _ in range(20):
        # Counterstreaming dominates the boost, giving one positive ray root.
        relative = rng.normal(size=3); relative *= speed / np.linalg.norm(relative)
        centre = rng.uniform(-0.1*speed, 0.1*speed, size=3)
        v1, v2 = centre + relative, centre - relative
        detector = rng.normal(size=3); detector /= np.linalg.norm(detector)
        result = call(v1, v2, detector)
        expected = bracketed_velocity_oracle(v1, v2, detector)
        assert type(result) is float and math.isfinite(result) and result > 0
        assert result == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("speed", [1e150, 1e161])
def test_large_but_representable_energies_do_not_overflow_an_unused_product(speed):
    result = call((speed, 0, 0), STATIONARY)
    assert math.isfinite(result) and result > 0
    assert result == pytest.approx(bracketed_velocity_oracle((speed, 0, 0), STATIONARY), rel=1e-12)


def test_genuinely_unrepresentable_final_energy_is_rejected():
    with pytest.raises(ValueError, match=NON_REPRESENTABLE_MESSAGE):
        call((1e162, 0, 0), STATIONARY)
    with pytest.raises(ValueError):
        call((1e308, 0, 0), (1e308, 0, 0))
    # A mathematically positive outgoing energy that rounds to zero is not a
    # representable result and must not be mistaken for a physical zero root.
    with pytest.raises(ValueError, match="underflows"):
        geometric_energy((0, 0, 0), Fraction(1, 10**400))


def test_large_evaluable_velocities_have_no_speed_cutoff():
    # 1e10 cm/s is approximately c/3. Model accuracy there is not established.
    for speed in (1e6, 1e8, 1e9, 2.165199149095298e9, 3e9, 1e10):
        result = call((speed, 0, 0), STATIONARY)
        assert type(result) is float and math.isfinite(result) and result > 0


def test_the_input_contract_keeps_shape_finiteness_and_absolute_unit_norm_gates():
    with pytest.raises(ValueError, match="finite shape"):
        call((0, 0), STATIONARY)
    with pytest.raises(ValueError, match="unit norm"):
        call(STATIONARY, STATIONARY, (2, 0, 0))
    with pytest.raises(ValueError, match="finite shape"):
        call((float("nan"), 0, 0), STATIONARY)
    assert call(STATIONARY, STATIONARY, (1 + 1e-13, 0, 0)) == STATIONARY_ANCHOR_KEV
    with pytest.raises(ValueError, match="unit norm"):
        call(STATIONARY, STATIONARY, (1 + 1e-12, 0, 0))
    assert DETECTOR_NORM_ATOL == 1e-12
    assert call([1e8, 0, 0], [5e7, 0, 0], [1, 0, 0]) == call(
        np.array([1e8, 0, 0], dtype=np.float64), np.array([5e7, 0, 0], dtype=np.float64))


@pytest.mark.parametrize("port", ["reactant1_velocity_cm_s", "reactant2_velocity_cm_s", "detector_unit_vector"])
def test_complex_vectors_are_rejected_before_float_conversion(port):
    supplied = dict(reactant1_velocity_cm_s=np.zeros(3), reactant2_velocity_cm_s=np.zeros(3),
                    detector_unit_vector=np.array([1, 0, 0]))
    supplied[port] = np.array([1+2j, 0, 0])
    with pytest.raises(ValueError, match="must be real"):
        calculate_dd_neutron_lab_energy_kev(**supplied)


def test_the_anisotropy_leaf_is_not_composed():
    call(STATIONARY, STATIONARY)
    assert "scirel.fusion.dd_neutron_anisotropy" not in __import__("sys").modules
    assert not hasattr(TARGET, "angular_weight")


def test_the_signature_is_keyword_only_and_requires_all_three_vectors():
    signature = inspect.signature(calculate_dd_neutron_lab_energy_kev)
    assert list(signature.parameters) == ["reactant1_velocity_cm_s", "reactant2_velocity_cm_s", "detector_unit_vector"]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in signature.parameters.values())
    with pytest.raises(TypeError):
        calculate_dd_neutron_lab_energy_kev((1e8, 0, 0), (5e7, 0, 0), (1, 0, 0))
