"""Direct contract tests for ``scirel.fusion.dd_neutron_lab_energy``.

Four claims are under contract here, and they build on each other.

**The retained route's non-positive fallback is removed, and this is a
correction.**  The fallback ``lab_mev if lab_mev > 0.0 else E_cm`` is not dead
code: because the guard is ``not lab_mev > 0.0`` it fires on every non-positive
value, including the small negatives that rounding produces near exact
cancellation of the two-body square root.  When it fires it replaces a lab energy
of zero with 2450.47589941598 keV.  The two witnesses are pinned below.

**The evaluated form is non-negative by construction, so no clamp is applied.**
An earlier revision answered the retained ordering's negative with an empirical
``max(0.0, value)`` clamp.  This module instead regroups the same relation into
the sum of a square and a product of non-negative factors, so no value is ever
replaced by zero.

**Arithmetic that is not representable fails closed.**  A finite input whose
intermediate or result is not finite is rejected rather than answered.

**The scientific boundary** the claims sit inside -- the source's own
mass-partition anchor, the two-body square-root bracket, and the input contract
-- is asserted directly.

This module tests the maintained implementation directly.  The review unit that
produced it additionally compared the route against the frozen V2/V3/V4
predecessors and the read-only L1 route; those arms live outside the repository
and are not reachable from the maintained baseline, so they are not replayed
here.  The claims they established -- what the removed guard returns at each
witness, and the retained ordering's rounding negative -- are asserted below from
their recorded values.
"""
from __future__ import annotations

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

# The two speeds pinned by the review, in cm/s, as ordinary neighbouring doubles
# of the speed that brings the neutron to rest in the laboratory.  One of them
# rounds to exactly zero under the retained ordering and the other to a small
# negative.
EXACT_ZERO_SPEED = 2165199149.095274
ROUNDING_NEGATIVE_SPEED = 2165199149.0952773

# The single double within +-4000 ulp of the cancellation speed at which
# E_boost equals E_cm exactly, so that the reformulated relation's first term is
# exactly zero; the detector is exactly backward, so its second term is exactly
# zero as well.  This is the complete-cancellation configuration.
EXACT_CANCELLATION_SPEED = 2165199149.095298

# What the removed guard returns at every witness, because it fires: the
# centre-of-mass energy, 2450.47589941598 keV, in place of a value of zero.
GUARDED_RESULT_KEV = 2450.47589941598
# What this module returns at the two witnesses.  They are one and three units in
# the last place away from the cancellation double, so E_cm != E_boost and the
# complete-cancellation argument does not apply: the value is zero to the
# precision of the arithmetic, and positive rather than floored.
AT_THE_WITNESSES_KEV = (2.9996435921028974e-25, 2.2132478772107012e-25)

# The reformulation changes where the roundings fall and nothing else, so the
# difference from the retained ordering is bounded by a few units in the last
# place of E_cm + E_boost.  Measured at no more than 5.16 over 840 inputs from
# 1e6 to 1e10 cm/s; the test asserts 8.
FORMULATION_DIFFERENCE_ULPS = 8.0
EPSILON = 2.0 ** -53

DETECTOR_FORWARD = np.array([1.0, 0.0, 0.0])
STATIONARY = np.zeros(3)


def centre_of_mass_terms(v1, v2, detector=DETECTOR_FORWARD):
    """``(E_cm, E_boost, cos_theta)`` in keV, re-derived from the asset's constants.

    The three quantities are not returned by the asset, so they are re-derived
    here from the constants it does publish.  This makes the assertions below
    independent of the asset's own evaluation order: the closed form is computed
    from the relation, not read out of the implementation.
    """
    v_centre_of_mass = 0.5 * (np.asarray(v1, dtype=float) + np.asarray(v2, dtype=float))
    v_relative = np.asarray(v1, dtype=float) - np.asarray(v2, dtype=float)
    available = (
        0.5 * (DEUTERON_MASS_AMU / 2.0) * ATOMIC_MASS_KG
        * float(np.dot(v_relative, v_relative)) * 1.0e-4 / MEV_J
        + DD_Q_VALUE_MEV
    )
    centre = HELIUM3_MASS_AMU / (NEUTRON_MASS_AMU + HELIUM3_MASS_AMU) * available
    boost = (
        0.5 * NEUTRON_MASS_AMU * ATOMIC_MASS_KG
        * float(np.dot(v_centre_of_mass, v_centre_of_mass)) * 1.0e-4 / MEV_J
    )
    norm = float(np.linalg.norm(v_centre_of_mass))
    cosine = (
        float(np.dot(v_centre_of_mass / norm, np.asarray(detector, dtype=float)))
        if norm > 0.0 else 0.0
    )
    return centre * 1000.0, boost * 1000.0, cosine


def backward_call(speed):
    """The neutron-at-rest configuration: both deuterons backwards, detector forward."""
    velocity = np.array([-speed, 0.0, 0.0])
    return calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=velocity,
        reactant2_velocity_cm_s=velocity,
        detector_unit_vector=DETECTOR_FORWARD,
    )


# ---------------------------------------------------------------------------
# The removed fallback
# ---------------------------------------------------------------------------


def test_the_call_returns_a_plain_float_and_not_a_mapping():
    """The energy and nothing else: the five diagnostic ports are gone.

    The V2 unit returned ``neutron_energy_kev``, ``angular_weight``,
    ``center_of_mass_neutron_energy_kev``, ``boost_energy_kev``,
    ``direction_cosine`` and ``used_nonpositive_fallback``.  Two of those are
    named constants or intermediates rather than results, and ``angular_weight``
    was a fixed ``1.0``.
    """
    result = calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=np.array([1.0e8, 0.0, 0.0]),
        reactant2_velocity_cm_s=np.array([5.0e7, 0.0, 0.0]),
        detector_unit_vector=DETECTOR_FORWARD,
    )
    assert type(result) is float
    assert not isinstance(result, dict)
    for name in (
        "angular_weight", "used_nonpositive_fallback", "direction_cosine",
        "center_of_mass_neutron_energy_kev", "boost_energy_kev",
    ):
        assert not hasattr(TARGET, name), name


@pytest.mark.parametrize("speed", [EXACT_ZERO_SPEED, ROUNDING_NEGATIVE_SPEED])
def test_the_witnesses_are_positive_and_never_the_cm_substitution(speed):
    """The removed guard's two witnesses, kept: the two-body value, not 2450 keV.

    A clamp would return exactly ``0.0`` at both.  This module does not clamp, and
    at these two speeds ``E_cm`` and ``E_boost`` are one and three units in the
    last place apart, so the value is not exactly zero: it is ``3.0e-25`` and
    ``2.2e-25`` keV.  Both are twenty-two orders of magnitude below the 1 keV
    scale of the relation, and neither is the guard's substitution.
    """
    result = backward_call(speed)
    assert result > 0.0
    assert result == AT_THE_WITNESSES_KEV[0 if speed == EXACT_ZERO_SPEED else 1]
    assert result < 1.0e-24
    assert result != GUARDED_RESULT_KEV


def test_no_value_in_the_cancellation_band_is_floored_or_negative():
    """The census the reformulation buys, over the 8001 doubles around cancellation.

    Exactly one of the 8001 doubles returns ``0.0`` -- the single one at which
    ``E_boost`` equals ``E_cm`` to the last bit -- and the other 8000 are
    **strictly positive**, none negative.  A clamp would have answered every
    non-positive value with ``0.0`` instead.

    The historical measurement that motivated the removal -- that the retained
    route's non-positive fallback fires 6983 times in this band, 997 of them on a
    strictly negative value -- was made against the frozen external route and is
    not replayed here.  It is recorded in the module docstring and in this
    document's verification scope as the reason for the change; what this test
    protects is the public relation's own behaviour in that band.
    """
    base = np.float64(EXACT_CANCELLATION_SPEED)
    exactly_zero = strictly_positive = strictly_negative = 0
    for offset in range(-4000, 4001):
        speed = base
        for _ in range(abs(offset)):
            speed = np.nextafter(speed, -np.inf if offset < 0 else np.inf)
        velocity = np.array([-float(speed), 0.0, 0.0])
        ours = calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=velocity,
            reactant2_velocity_cm_s=velocity,
            detector_unit_vector=DETECTOR_FORWARD,
        )
        # The relation is never a substitution anywhere in the band.
        assert 0.0 <= ours < 1.0e-9
        exactly_zero += ours == 0.0
        strictly_positive += ours > 0.0
        strictly_negative += ours < 0.0
    assert (exactly_zero, strictly_negative) == (1, 0)
    assert strictly_positive == 8000


# ---------------------------------------------------------------------------
# Non-negative by construction
# ---------------------------------------------------------------------------


def test_the_complete_cancellation_configuration_returns_exactly_zero():
    """Both terms vanish exactly, so the value is exactly zero and not a residue.

    ``E_boost`` equals ``E_cm`` to the last bit at this speed, so the square
    ``(sqrt(E_cm) - sqrt(E_boost))^2`` is exactly ``0.0``; the detector is
    exactly backward, so the direction cosine is exactly ``-1`` and the product
    ``2*sqrt(E_cm*E_boost)*(1 + c)`` is exactly ``0.0``.  The returned energy is
    therefore exactly ``0.0`` -- not a small positive residue, and not a negative
    that a clamp has to repair.

    The configuration is reflection-symmetric, so both lab-frame sign conventions
    are pinned.  The removed guard substitutes 2450.47589941598 keV at both.
    """
    for velocity, detector in (
        (np.array([-EXACT_CANCELLATION_SPEED, 0.0, 0.0]), DETECTOR_FORWARD),
        (np.array([EXACT_CANCELLATION_SPEED, 0.0, 0.0]), -DETECTOR_FORWARD),
    ):
        centre, boost, cosine = centre_of_mass_terms(velocity, velocity, detector)
        assert centre == boost, "the two terms cancel exactly at this speed"
        assert cosine == -1.0
        assert calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=velocity,
            reactant2_velocity_cm_s=velocity,
            detector_unit_vector=detector,
        ) == 0.0


def test_the_reformulation_agrees_with_the_retained_ordering_within_rounding():
    """The reformulation changes where the roundings fall, not the relation.

    The two forms are algebraically equal, so their difference is bounded by the
    rounding of the six operations that differ, that is by a few units in the
    last place of ``E_cm + E_boost``.  Measured at no more than 5.16 ulp over
    840 inputs from 1e6 to 1e10 cm/s; the assertion allows 8.

    The comparison is against the retained *ordering*
    ``E_cm + E_boost + 2*sqrt(E_cm*E_boost)*c``, which is re-derived here from the
    published constants rather than read from a frozen arm.  Bit-identity is
    deliberately not asserted: it was true of a clamped revision and is not a
    property the reformulation can have.  What is asserted exactly is the sign.
    """
    rng = np.random.default_rng(20260920)
    worst_ulps = 0.0
    checked = 0
    for scale in (1.0e6, 1.0e8, 4.0e8, 1.0e9, 2.0e9, 3.0e9, 1.0e10):
        for _ in range(120):
            v1 = rng.uniform(-scale, scale, size=3)
            v2 = rng.uniform(-scale, scale, size=3)
            detector = rng.normal(size=3)
            detector /= np.linalg.norm(detector)
            ours = calculate_dd_neutron_lab_energy_kev(
                reactant1_velocity_cm_s=v1,
                reactant2_velocity_cm_s=v2,
                detector_unit_vector=detector,
            )
            centre, boost, cosine = centre_of_mass_terms(v1, v2, detector)
            retained_ordering = (
                centre + boost
                + 2.0 * math.sqrt(centre * boost) * max(-1.0, min(1.0, cosine))
            )
            worst_ulps = max(
                worst_ulps,
                abs(ours - retained_ordering) / (EPSILON * (centre + boost)),
            )
            assert ours >= 0.0
            checked += 1
    assert checked == 840
    assert worst_ulps <= FORMULATION_DIFFERENCE_ULPS


def test_the_retained_ordering_rounds_at_or_below_the_positive_result():
    """Why the reformulation is needed rather than a clamp.

    The retained ordering ``E_cm + E_boost + 2*sqrt(E_cm*E_boost)*c`` adds a large
    negative term to a large positive one near backward emission, so at these
    speeds it lands on ``0.0`` or below, where the relation is strictly positive.
    The ordering is re-derived here from the published constants rather than taken
    from the frozen route, whose intermediate scaling is not reproduced; what is
    asserted is the property the removal rests on -- the ordering is not strictly
    positive at these inputs, while this module's result is -- together with the
    size of the residue it can produce.
    """
    for speed in (EXACT_ZERO_SPEED, ROUNDING_NEGATIVE_SPEED):
        velocity = np.array([-speed, 0.0, 0.0])
        centre, boost, cosine = centre_of_mass_terms(velocity, velocity)
        retained_ordering = (
            centre + boost
            + 2.0 * math.sqrt(centre * boost) * max(-1.0, min(1.0, cosine))
        )
        assert retained_ordering <= 0.0, speed
        assert backward_call(speed) > 0.0
        # The residue is of the size the cancellation produces: a few units in the
        # last place of the two large terms, not a physically meaningful value.
        assert abs(retained_ordering) <= 8.0 * EPSILON * (centre + boost)


def test_a_detector_at_the_norm_tolerance_boundary_is_not_inflated():
    """The tolerance on the norm is what makes the cosine bound necessary.

    The input contract accepts a detector whose norm is within an absolute
    ``1e-12`` of one, so ``(1 + 1e-13, 0, 0)`` is an accepted input -- and its dot
    product with a unit ``v_cm_hat`` is ``1.0000000000001``, which no direction
    cosine can be.  Using it unclamped inflates the energy; this module bounds it
    to one, and the result is then **bit-identical** to the same inputs with an
    exactly unit detector, which is what the bound means.
    """
    v1, v2 = np.array([1.0e8, 0.0, 0.0]), np.array([5.0e7, 0.0, 0.0])
    boundary_detector = np.array([1.0 + 1.0e-13, 0.0, 0.0])
    assert np.linalg.norm(boundary_detector) > 1.0

    ours = calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=v1,
        reactant2_velocity_cm_s=v2,
        detector_unit_vector=boundary_detector,
    )
    unit = calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=v1,
        reactant2_velocity_cm_s=v2,
        detector_unit_vector=DETECTOR_FORWARD,
    )
    assert ours == unit
    # The unbounded dot product really does exceed one, so the bound is doing
    # work rather than restating an invariant that already held.  It is this
    # excess, left unbounded, that would inflate the energy past the maximum the
    # relation admits, which is the (sqrt(E_cm) + sqrt(E_boost))^2 extreme.
    v_cm = 0.5 * (v1 + v2)
    unbounded = float(np.dot(v_cm / np.linalg.norm(v_cm), boundary_detector))
    centre, boost, _ = centre_of_mass_terms(v1, v2)
    upper = (math.sqrt(centre) + math.sqrt(boost)) ** 2
    assert unbounded > 1.0
    assert ours <= upper
    inflated = (
        (math.sqrt(centre) - math.sqrt(boost)) ** 2
        + 2.0 * math.sqrt(centre * boost) * (1.0 + unbounded)
    )
    # The excess is 1e-13, which is at the resolution of these doubles, so the
    # inflated value lands on the extreme rather than measurably above it.  It is
    # still strictly above the bounded result, which is what the bound buys.
    assert inflated >= upper
    assert inflated > ours


def test_an_anisotropic_direction_cosine_is_still_used_in_full():
    """Bounding is not clamping: an interior cosine passes through unchanged."""
    velocity = np.array([1.0e8, 0.0, 0.0])
    for detector in (
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([-1.0, 0.0, 0.0]),
        np.array([1.0, 1.0, 0.0]) / math.sqrt(2.0),
    ):
        centre, boost, cosine = centre_of_mass_terms(velocity, STATIONARY)
        expected = (
            (math.sqrt(centre) - math.sqrt(boost)) ** 2
            + 2.0 * math.sqrt(centre * boost)
            * (1.0 + max(-1.0, min(
                1.0,
                float(np.dot(velocity / np.linalg.norm(velocity), detector)),
            )))
        )
        assert calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=velocity,
            reactant2_velocity_cm_s=STATIONARY,
            detector_unit_vector=detector,
        ) == pytest.approx(expected, rel=1.0e-12)
        assert -1.0 <= cosine <= 1.0


# ---------------------------------------------------------------------------
# Arithmetic that is not representable fails closed
# ---------------------------------------------------------------------------


def test_the_review_witness_is_rejected_rather_than_answered_with_zero():
    """Two finite ``1e308`` cm/s velocities: the review's counterexample.

    ``v1 + v2`` overflows to ``inf``, ``inf / inf`` in the direction cosine is
    ``NaN``, and the sum is ``NaN``.  A ``max(0.0, value)`` clamp answers
    ``max(0.0, NaN)``, which is ``0.0``: a silent zero for an input whose energy
    is not zero.  This module rejects it instead, and the rejection names the
    intermediate that failed.
    """
    big = np.array([1.0e308, 0.0, 0.0])
    with pytest.raises(ValueError) as raised:
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=big,
            reactant2_velocity_cm_s=big,
            detector_unit_vector=DETECTOR_FORWARD,
        )
    assert str(raised.value).startswith(NON_REPRESENTABLE_MESSAGE)
    assert "centre-of-mass velocity" in str(raised.value)
    assert "is not finite" in str(raised.value)


def test_an_overflowing_boost_is_rejected_rather_than_returned_as_infinity():
    """A second, independently measured signature: a finite velocity, an infinite result.

    One ``1.0e150`` cm/s velocity leaves ``E_cm`` finite and overflows
    ``|v_cm|^2``, so the sum is ``inf``.  A clamp passes an infinity through
    unchanged, because ``max(0.0, inf)`` is ``inf``; the returned energy is not
    finite although the input is.  This module rejects it.
    """
    big = np.array([1.0e150, 0.0, 0.0])
    with pytest.raises(ValueError) as raised:
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=big,
            reactant2_velocity_cm_s=STATIONARY,
            detector_unit_vector=DETECTOR_FORWARD,
        )
    assert str(raised.value).startswith(NON_REPRESENTABLE_MESSAGE)


def test_large_but_representable_velocities_are_still_accepted():
    """The check is on representability, not a speed cutoff: no threshold is invented.

    ``1e10`` cm/s is four times the speed of light and far outside the
    non-relativistic regime the relation is applicable in, but its arithmetic is
    representable, so it is evaluated and returned.  The applicability limit
    stays a scientific statement in the document rather than a hard-coded bound
    on the input.
    """
    for speed in (1.0e6, 1.0e8, 2.165199149095298e9, 1.0e9, 3.0e9, 1.0e10):
        velocity = np.array([speed, 0.0, 0.0])
        result = calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=velocity,
            reactant2_velocity_cm_s=STATIONARY,
            detector_unit_vector=DETECTOR_FORWARD,
        )
        assert type(result) is float
        assert math.isfinite(result)
        assert result > 0.0


def test_the_representability_check_names_no_threshold():
    """The check reports the quantity that failed and states no bound.

    The module's prose names the thresholds it *declines* to introduce, which is
    the point, so the assertion is made against the executable logic rather than
    against the prose.  ``inspect.getsource`` returns the whole module including
    its comments, so the check is read from the compiled code object instead.
    """
    import dis

    instructions = [
        instruction
        for instruction in dis.get_instructions(TARGET._require_representable)
    ]
    rendered = " ".join(
        f"{instruction.opname} {instruction.argval}" for instruction in instructions
    )
    # The check is a finiteness test: isfinite, then negate, then raise.
    assert "isfinite" in rendered
    assert "RAISE_VARARGS" in rendered
    # No magnitude comparison and no literal bound is involved.
    for opname in ("COMPARE_OP",):
        comparisons = [
            instruction.argval
            for instruction in instructions
            if instruction.opname == opname
        ]
        assert set(comparisons) <= {">", ">=", "==", "!="}, comparisons
    constants = [
        instruction.argval
        for instruction in instructions
        if instruction.opname in ("LOAD_CONST", "LOAD_SMALL_INT")
    ]
    numbers = [value for value in constants if isinstance(value, (int, float))]
    assert not [value for value in numbers if abs(value) not in (0, 1)], numbers
    assert NON_REPRESENTABLE_MESSAGE in TARGET.__dict__.values()
    # The message the check raises is that constant plus the quantity that failed.
    with pytest.raises(ValueError) as raised:
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=np.array([1.0e308, 0.0, 0.0]),
            reactant2_velocity_cm_s=np.array([1.0e308, 0.0, 0.0]),
            detector_unit_vector=DETECTOR_FORWARD,
        )
    assert str(raised.value).startswith(f"{NON_REPRESENTABLE_MESSAGE}: ")
    assert str(raised.value).endswith("is not finite")
    assert "centre-of-mass velocity" in str(raised.value)
    # And the message states no bound of its own.
    for forbidden in ("too large", "too small", "cutoff", "threshold", "ceiling"):
        assert forbidden not in NON_REPRESENTABLE_MESSAGE, forbidden


# ---------------------------------------------------------------------------
# The scientific boundary the claims sit inside
# ---------------------------------------------------------------------------


def test_stationary_reactants_return_the_source_mass_partition_energy():
    """The retained route's own anchor: the mass ratio applied to the Q value."""
    closed_form = (
        1000.0 * HELIUM3_MASS_AMU * DD_Q_VALUE_MEV
        / (NEUTRON_MASS_AMU + HELIUM3_MASS_AMU)
    )
    assert closed_form == pytest.approx(GUARDED_RESULT_KEV, rel=1.0e-15)
    assert calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=STATIONARY,
        reactant2_velocity_cm_s=STATIONARY,
        detector_unit_vector=DETECTOR_FORWARD,
    ) == GUARDED_RESULT_KEV


def test_a_forward_detector_exceeds_a_reverse_detector():
    """The retained route's second anchor, on the retained route's own inputs."""
    v1, v2 = (1.0e8, 0.0, 0.0), (5.0e7, 0.0, 0.0)
    forward = calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=v1, reactant2_velocity_cm_s=v2,
        detector_unit_vector=DETECTOR_FORWARD,
    )
    reverse = calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=v1, reactant2_velocity_cm_s=v2,
        detector_unit_vector=-DETECTOR_FORWARD,
    )
    assert forward > reverse > 0.0


def test_the_energy_is_the_two_body_square_root_bracket():
    """``E_lab = (sqrt(E_cm) +- sqrt(E_boost))^2`` at the two extremes.

    Asserted to a bound rather than bit-wise: the bracket evaluated as a square
    and the bracket evaluated as the asset's sum of two non-negative terms are
    algebraically equal but round differently, by about 1e-15 MeV.  This is the
    reason the value can be asserted non-negative exactly rather than within a
    tolerance.
    """
    for speed in (5.0e7, 2.0e8, 5.0e8, 2.0e9):
        velocity = np.array([speed, 0.0, 0.0])
        centre, boost, _ = centre_of_mass_terms(velocity, np.zeros(3))
        lower = (math.sqrt(centre) - math.sqrt(boost)) ** 2
        upper = (math.sqrt(centre) + math.sqrt(boost)) ** 2
        reverse = calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=velocity, reactant2_velocity_cm_s=np.zeros(3),
            detector_unit_vector=-DETECTOR_FORWARD,
        )
        forward = calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=velocity, reactant2_velocity_cm_s=np.zeros(3),
            detector_unit_vector=DETECTOR_FORWARD,
        )
        assert abs(reverse - lower) <= 1.0e-12 * max(lower, 1.0)
        assert abs(forward - upper) <= 1.0e-12 * max(upper, 1.0)
        assert lower >= 0.0
        assert forward > reverse


def test_every_accepted_call_returns_a_non_negative_finite_float():
    """The invariant the reformulation buys, over a wide sweep including the cancellation band."""
    rng = np.random.default_rng(20260921)
    speeds = [1.0e6, 1.0e8, 1.0e9, 2.0e9, 2.165199149095298e9, 3.0e9]
    checked = 0
    for _ in range(300):
        speed = float(rng.choice(speeds))
        v1 = rng.uniform(-speed, speed, size=3)
        v2 = rng.uniform(-speed, speed, size=3)
        detector = rng.normal(size=3)
        detector /= np.linalg.norm(detector)
        result = calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=v1,
            reactant2_velocity_cm_s=v2,
            detector_unit_vector=detector,
        )
        assert type(result) is float
        assert math.isfinite(result)
        assert result >= 0.0
        checked += 1
    assert checked == 300


def test_the_anisotropy_leaf_is_not_composed():
    """The lab energy is unweighted; the caller applies the angular distribution."""
    calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=STATIONARY, reactant2_velocity_cm_s=STATIONARY,
        detector_unit_vector=DETECTOR_FORWARD,
    )
    assert "scirel.fusion.dd_neutron_anisotropy" not in __import__("sys").modules
    assert not hasattr(TARGET, "angular_weight")


# ---------------------------------------------------------------------------
# Input contract, the retained route's
# ---------------------------------------------------------------------------


def test_the_input_contract_is_the_retained_routes():
    stationary = (0.0, 0.0, 0.0)
    # A shape-(2,) vector is rejected.  (0, 0) also has norm 0, so this is the
    # shape check and not the norm check doing the rejecting.
    with pytest.raises(ValueError):
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=(0.0, 0.0),
            reactant2_velocity_cm_s=stationary,
            detector_unit_vector=(1.0, 0.0, 0.0),
        )
    # A non-unit detector is rejected rather than normalised.
    with pytest.raises(ValueError, match="unit norm"):
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=stationary, reactant2_velocity_cm_s=stationary,
            detector_unit_vector=(2.0, 0.0, 0.0),
        )
    # A non-finite component is rejected by the input contract rather than by the
    # representability check, which is why the message is the shape one.
    with pytest.raises(ValueError, match="finite shape"):
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=(float("nan"), 0.0, 0.0),
            reactant2_velocity_cm_s=stationary,
            detector_unit_vector=(1.0, 0.0, 0.0),
        )
    # The norm tolerance is absolute: just inside is accepted, at it is not.
    assert calculate_dd_neutron_lab_energy_kev(
        reactant1_velocity_cm_s=stationary, reactant2_velocity_cm_s=stationary,
        detector_unit_vector=(1.0 + 1.0e-13, 0.0, 0.0),
    ) == GUARDED_RESULT_KEV
    with pytest.raises(ValueError, match="unit norm"):
        calculate_dd_neutron_lab_energy_kev(
            reactant1_velocity_cm_s=stationary, reactant2_velocity_cm_s=stationary,
            detector_unit_vector=(1.0 + 1.0e-12, 0.0, 0.0),
        )
    assert DETECTOR_NORM_ATOL == 1.0e-12


def test_the_signature_is_keyword_only_and_requires_all_three_vectors():
    """The retained route's calling convention, kept rather than relaxed."""
    signature = inspect.signature(calculate_dd_neutron_lab_energy_kev)
    assert list(signature.parameters) == [
        "reactant1_velocity_cm_s",
        "reactant2_velocity_cm_s",
        "detector_unit_vector",
    ]
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    with pytest.raises(TypeError):
        calculate_dd_neutron_lab_energy_kev(
            (1.0e8, 0.0, 0.0), (5.0e7, 0.0, 0.0), (1.0, 0.0, 0.0)
        )
