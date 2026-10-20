"""Direct contract tests for ``scirel.dielectric.cold_plasma_tensor``.

The suite imports only the maintained SciRel package.  It verifies the public
input and failure contracts, representability guards, basis and sign
conventions, closed-form agreement, structural invariants and documented edge
cases.  Historical source comparisons and reviewer-only evidence remain outside
the maintenance suite; assertions here stand on the maintained implementation.
"""
from __future__ import annotations

import importlib
import math
import os
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np
import pytest

from scirel.dielectric import (
    ColdPlasmaOverflowError,
    ColdPlasmaResonanceError,
    cold_plasma_dielectric_tensor,
)
from scirel.dielectric.cold_plasma_tensor import (
    MODEL,
    OVERFLOW_MESSAGE,
    RESONANCE_MESSAGE,
    TIME_CONVENTION,
    VACUUM_PERMITTIVITY,
    _is_representable_product,
)

TARGET = importlib.import_module("scirel.dielectric.cold_plasma_tensor")

FREQUENCY_HZ = 60.0e6
OMEGA = 2.0 * math.pi * FREQUENCY_HZ
FIELD = np.array([0.0, 0.0, 0.3])

ELECTRON = {
    "density_m3": 1.0e19,
    "charge_c": -1.602176634e-19,
    "mass_kg": 9.1093837015e-31,
}
PROTON = {
    "density_m3": 5.0e18,
    "charge_c": 1.602176634e-19,
    "mass_kg": 1.67262192369e-27,
}

# The expert review's own measurement, reproduced here as a pinned witness.
REVIEW_COLLISIONAL_DEVIATION = 1188.0005607305914
REVIEW_COLLISION_RATE = 1.0e6

# |q| B / m at the field that makes the collisionless denominator vanish.
RESONANT_FIELD_T = OMEGA * ELECTRON["mass_kg"] / abs(ELECTRON["charge_c"])

# A field that is not aligned with any coordinate axis, so the caller's basis and
# a field-aligned frame are measurably different descriptions.
TILTED_FIELD = np.array([0.2, 0.0, 0.3])

# Measured agreement between this module and an independent re-derivation of the
# same relation in the test body.  See the module docstring.
INDEPENDENT_ASSEMBLY_RELATIVE_AGREEMENT = 1.0e-14


def evaluate(module, field, species, frequency_hz=FREQUENCY_HZ):
    """Call the module's single public function."""
    return module.cold_plasma_dielectric_tensor(frequency_hz, field, species)


def deviation(tensor):
    return float(np.max(np.abs(tensor - tensor.conj().T)))


def assert_agrees(actual, expected):
    """Agreement to a few ulp, with the bound asserted rather than implied."""
    scale = max(float(np.max(np.abs(expected))), 1.0)
    assert float(np.max(np.abs(actual - expected))) <= (
        INDEPENDENT_ASSEMBLY_RELATIVE_AGREEMENT * scale
    )


def stix_scalars(field, species):
    """``(S, D, P)`` in SI, re-derived from the module's own constants."""
    magnitude = float(np.linalg.norm(field))
    stix_s, stix_d, stix_p = 1.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j
    for item in species:
        plasma = item["density_m3"] * item["charge_c"] ** 2 / (
            VACUUM_PERMITTIVITY * item["mass_kg"]
        )
        cyclotron = item["charge_c"] * magnitude / item["mass_kg"]
        shifted = OMEGA + 1j * item.get("collision_rate_s_inv", 0.0)
        denominator = shifted * shifted - cyclotron * cyclotron
        stix_s -= plasma * shifted / (OMEGA * denominator)
        stix_d += cyclotron * plasma / (OMEGA * denominator)
        stix_p -= plasma / (OMEGA * shifted)
    return stix_s, stix_d, stix_p


def assemble(field, species):
    """Re-derive S*I + (P - S) b b + i*D*[b]x independently of the module."""
    direction = np.asarray(field, dtype=float) / np.linalg.norm(field)
    stix_s, stix_d, stix_p = stix_scalars(field, species)
    cross = np.array(
        [
            [0.0, -direction[2], direction[1]],
            [direction[2], 0.0, -direction[0]],
            [-direction[1], direction[0], 0.0],
        ],
        dtype=complex,
    )
    return (
        stix_s * np.eye(3, dtype=complex)
        + (stix_p - stix_s) * np.outer(direction, direction)
        + 1j * stix_d * cross
    )


def assemble_with_cyclotron_reading(field, species, *, signed_axial):
    """Re-derive the tensor for an axial field under one reading of the argument.

    The scalar cyclotron argument has two readings that differ only in sign, and
    only when the axial field is negative:

    * ``signed_axial=False`` -- ``q |B| / m``, the field *magnitude*.  This is the
      reading the module forms internally, and for an axial field it is
      ``q |B_z| / m``.
    * ``signed_axial=True`` -- ``q B_z / m``, the *signed projection*.  This is the
      argument the retained conductivity route's call site passes.

    The two coincide for a positive axial field, so a positive field cannot
    discriminate between them and a negative one can.  The helper asserts the
    field is axial, because a projection is only a projection there.
    """
    vector = np.asarray(field, dtype=float)
    assert vector.shape == (3,) and vector[0] == 0.0 and vector[1] == 0.0, (
        "this helper is the axial reading; it is not a general assembly"
    )
    magnitude = float(np.linalg.norm(vector))
    stix_s, stix_d, stix_p = 1.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j
    for item in species:
        plasma = item["density_m3"] * item["charge_c"] ** 2 / (
            VACUUM_PERMITTIVITY * item["mass_kg"]
        )
        argument = float(vector[2]) if signed_axial else magnitude
        cyclotron = item["charge_c"] * argument / item["mass_kg"]
        shifted = OMEGA + 1j * item.get("collision_rate_s_inv", 0.0)
        denominator = shifted * shifted - cyclotron * cyclotron
        stix_s -= plasma * shifted / (OMEGA * denominator)
        stix_d += cyclotron * plasma / (OMEGA * denominator)
        stix_p -= plasma / (OMEGA * shifted)
    direction = vector / magnitude
    cross = np.array(
        [
            [0.0, -direction[2], direction[1]],
            [direction[2], 0.0, -direction[0]],
            [-direction[1], direction[0], 0.0],
        ],
        dtype=complex,
    )
    return (
        stix_s * np.eye(3, dtype=complex)
        + (stix_p - stix_s) * np.outer(direction, direction)
        + 1j * stix_d * cross
    )


def exact_ratio(numerator, denominator):
    """The exact value of ``numerator / denominator`` as a ``Fraction``.

    The two arguments are Python floats, so they are exactly representable
    binary rationals and their quotient is exact.  This is the oracle the
    collapsed-intermediate sections use: it evaluates the division the double
    arithmetic could not, without any high-precision runtime dependency --
    ``fractions`` is standard library and is imported only by this test module,
    never by the package under test.
    """
    return Fraction(numerator) / Fraction(denominator)


def _exact_product(left, right):
    """The exact value of ``left * right`` as a ``Fraction``.

    The arguments are Python floats, so they are exactly representable binary
    rationals and the product is exact.  This is the oracle used to decide
    whether a double product collapsed because the exact product is zero or
    because it is outside the double range -- a distinction the double
    arithmetic cannot make, because both cases give the same ``0.0``.
    """
    return Fraction(left) * Fraction(right)


def _exact_cyclotron(charge, magnitude, mass):
    """``q |B| / m`` as a ``Fraction``, over the represented doubles.

    The point of the oracle is that the double arithmetic forms this quotient as
    ``0.0`` for the cyclotron counterexample while its exact value is non-zero
    and its product with the plasma contribution is an ordinary representable
    double.
    """
    return Fraction(charge) * Fraction(magnitude) / Fraction(mass)


# ---------------------------------------------------------------------------
# The module under test is the selected maintained runtime
# ---------------------------------------------------------------------------


def test_the_module_under_test_is_the_selected_maintained_runtime():
    """Use source in the inner loop and the installed wheel at release."""
    expected_root = (
        Path(sys.prefix).resolve()
        if os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1"
        else (Path(__file__).resolve().parents[2] / "src").resolve()
    )
    assert Path(TARGET.__file__).resolve().is_relative_to(expected_root)
    assert TARGET.__name__ == "scirel.dielectric.cold_plasma_tensor"
    assert TARGET.cold_plasma_dielectric_tensor is cold_plasma_dielectric_tensor


# ---------------------------------------------------------------------------
# Correction 1 -- a non-finite frequency is rejected before arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_a_non_finite_frequency_is_rejected_before_arithmetic(bad):
    """The V3 defect, closed.  V3 returned an all-NaN tensor for NaN and +inf.

    ``omega <= 0.0`` is false for NaN and for positive infinity, so V3's guard
    passed and the call returned a tensor in which nothing was finite.  The
    maintained module rejects the frequency before any arithmetic.  The
    divergence from the frozen V3 arm is recorded in the module docstring and is
    not replayed here; what is asserted is the current contract, and that the
    rejection is a guard rather than a reformulation is asserted by the
    ordinary-range sweep below.
    """
    with pytest.raises(ValueError, match="positive finite frequency"):
        evaluate(TARGET, FIELD, [ELECTRON], frequency_hz=bad)


def test_every_accepted_call_returns_a_finite_tensor():
    """The contract the review asked for: finite tensor or a documented exception.

    Swept over the accepted regime the asset documents -- non-resonant fields at
    several magnitudes and directions, with and without collisions, single and
    multiple species, and a full spatial grid -- because a single witness would
    not distinguish "finite here" from "finite by construction".
    """
    rng = np.random.default_rng(20260921)
    fields = [FIELD, TILTED_FIELD, np.zeros(3), np.array([12.0, 0.0, 0.0])]
    fields.extend(rng.uniform(-2.0, 2.0, size=(64, 3)))
    species_sets = [
        [],
        [ELECTRON],
        [PROTON],
        [ELECTRON, PROTON],
        [dict(ELECTRON, collision_rate_s_inv=REVIEW_COLLISION_RATE)],
        [dict(ELECTRON, collision_rate_s_inv=1.0e15), PROTON],
    ]
    checked = 0
    for field in fields:
        for species in species_sets:
            try:
                result = evaluate(TARGET, field, species)
            except ColdPlasmaResonanceError:
                continue
            assert np.all(np.isfinite(result)), (field, species)
            checked += 1
    assert checked > 300


# ---------------------------------------------------------------------------
# Correction 2 -- a zero-contribution species is skipped before the guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("zeroed", ["density_m3", "charge_c"])
def test_a_zero_contribution_species_is_skipped_before_the_resonance_guard(zeroed):
    """The V3 defect, closed.  V3 rejected the whole call for a species that moves nothing.

    ``wp2 = n q^2 / (eps0 m)`` vanishes identically when ``n == 0`` or ``q == 0``,
    so such a species cannot make the tensor singular, non-Hermitian, or anything
    else.  The maintained module skips it; V3 evaluated the guard first and
    raised.

    The reason the two zeroed fields are not symmetric is worth recording: V3's
    exact-zero test fired only when the resonance was collisionless *and* the
    cyclotron term was untouched.  A zero-density species keeps ``q`` and ``m``,
    so its denominator was the resonant one and V3 raised; a zero-charge species
    drives the cyclotron term to zero, so its denominator was ``omega^2`` and V3
    never raised.  The current contract is that both are skipped, and both are
    asserted to be observationally absent rather than merely accepted.
    """
    resonant = np.array([0.0, 0.0, RESONANT_FIELD_T])
    inert = dict(ELECTRON, **{zeroed: 0.0})
    result = evaluate(TARGET, resonant, [inert])
    assert np.all(np.isfinite(result))
    assert np.array_equal(result, evaluate(TARGET, FIELD, []))


@pytest.mark.parametrize("zeroed", ["density_m3", "charge_c"])
def test_a_zero_contribution_species_is_exact_at_any_field_and_any_collision(zeroed):
    """Skipping is exact: the inert species is equivalent to omitting it entirely.

    Asserted at collision rates up to 1e15 because ``0 * x`` is not ``0`` for every
    ``x``: a species that contributes nothing must be skipped rather than
    accumulated, or its own resonance can put a non-finite value into the sum.
    """
    for field in (FIELD, TILTED_FIELD, np.zeros(3)):
        without = evaluate(TARGET, field, [])
        for rate in (0.0, REVIEW_COLLISION_RATE, 1.0e15):
            inert = dict(ELECTRON, collision_rate_s_inv=rate, **{zeroed: 0.0})
            with_inert = evaluate(TARGET, field, [inert])
            assert np.array_equal(without, with_inert), (field, zeroed, rate)
        resonant = np.array([0.0, 0.0, RESONANT_FIELD_T])
        with_inert = evaluate(
            TARGET, resonant, [dict(ELECTRON, collision_rate_s_inv=1.0e15, **{zeroed: 0.0})]
        )
        assert np.array_equal(evaluate(TARGET, resonant, []), with_inert)


def test_a_contributing_species_at_exact_resonance_still_rejects():
    """The guard is narrowed to contributing species, not weakened.

    A named ``ValueError``, and the singularity test is exact equality on the
    computed denominator rather than a tolerance.  The review's evidence that the
    retained sibling conductivity route guards the identical denominator with the
    same exact-zero test is frozen in the snapshot; the maintained suite
    re-derives the sibling's closed form in
    :func:`test_the_conductivity_formulation_is_recovered_only_with_the_signed_projection`
    rather than loading it.
    """
    resonant = np.array([0.0, 0.0, RESONANT_FIELD_T])
    with pytest.raises(ColdPlasmaResonanceError) as caught:
        evaluate(TARGET, resonant, [ELECTRON])
    assert isinstance(caught.value, ValueError)
    assert str(caught.value).startswith(RESONANCE_MESSAGE)
    assert "(species index 0)" in str(caught.value)


def test_the_guard_names_the_contributing_species_index():
    """The inert species is skipped, so the reported index is the contributing one."""
    resonant = np.array([0.0, 0.0, RESONANT_FIELD_T])
    with pytest.raises(ColdPlasmaResonanceError) as caught:
        evaluate(
            TARGET,
            resonant,
            [dict(ELECTRON, density_m3=0.0), ELECTRON, PROTON],
        )
    assert "(species index 1)" in str(caught.value)


def test_one_resonant_point_rejects_the_whole_call():
    fields = np.array([[0.0, 0.0, 0.3], [0.0, 0.0, RESONANT_FIELD_T], [0.0, 0.0, 0.5]])
    with pytest.raises(ColdPlasmaResonanceError):
        evaluate(TARGET, fields, [ELECTRON])


def test_a_near_resonant_field_is_evaluated_and_a_collision_lifts_the_singularity():
    resonant = np.array([0.0, 0.0, RESONANT_FIELD_T])
    for offset in (1.0e-15, 1.0e-6):
        assert np.all(np.isfinite(evaluate(TARGET, resonant * (1.0 + offset), [ELECTRON])))
    lifted = evaluate(
        TARGET, resonant, [dict(ELECTRON, collision_rate_s_inv=REVIEW_COLLISION_RATE)]
    )
    assert np.all(np.isfinite(lifted))


# ---------------------------------------------------------------------------
# Corrections 3 and 4 -- the return type and the coordinate contract
# ---------------------------------------------------------------------------


def test_the_call_returns_the_tensor_and_not_a_mapping():
    """Correction 3: the bare ``ndarray`` return is kept.

    A predecessor returned a mapping carrying the time convention and the model
    label.  The review required the scientific result only, and the two labels are
    module constants instead -- asserted in
    :func:`test_the_time_convention_and_model_are_module_constants`.  That the
    retained route's mapping shape is gone is a statement about the predecessor,
    recorded in the module docstring, not replayed here.
    """
    ours = evaluate(TARGET, FIELD, [ELECTRON])
    assert isinstance(ours, np.ndarray), (
        "the review required the scientific result only; a mapping carrying the "
        "time convention and the model label is public contract, not a result"
    )
    assert ours.shape == (3, 3) and ours.dtype == np.complex128


def test_the_time_convention_and_model_are_module_constants():
    assert TIME_CONVENTION == "exp(-i*omega*t)"
    assert MODEL == "LOCAL_COLD_PLASMA"
    assert TARGET.TIME_CONVENTION == "exp(-i*omega*t)"
    assert TARGET.MODEL == "LOCAL_COLD_PLASMA"
    assert TARGET.__all__ == [
        "ColdPlasmaOverflowError",
        "ColdPlasmaResonanceError",
        "cold_plasma_dielectric_tensor",
    ]
    # The re-exported domain surface is the same three names.
    from scirel import dielectric

    assert dielectric.__all__ == TARGET.__all__


def test_the_matrix_is_in_the_callers_basis_and_not_a_field_aligned_frame():
    """Correction 4, measured on a field that is not aligned with any axis.

    The operator ``S I + (P - S) b b + i D [b]_x`` is coordinate-free in
    construction.  The matrix it returns is that operator in the caller's own
    Cartesian basis.  If the matrix were instead a field-aligned representation --
    the reading V3's wording invited -- the axial entry would be ``P`` for *every*
    field direction and ``eps @ b`` would be ``S b``.  Neither holds off axis, and
    both hold when the field is along a coordinate axis, which is exactly why V3's
    error survived: its own witnesses were all axial.
    """
    tilted = evaluate(TARGET, TILTED_FIELD, [ELECTRON])
    direction = TILTED_FIELD / np.linalg.norm(TILTED_FIELD)
    stix_s, stix_d, stix_p = stix_scalars(TILTED_FIELD, [ELECTRON])

    # The frame-invariant scalar is P, and it is recovered on axis and off it.
    assert_agrees(
        np.array([[direction.conj() @ tilted @ direction]]), np.array([[stix_p]])
    )
    # The axial entry is not P off axis, so the matrix is not field-aligned.
    assert abs(tilted[2, 2] - stix_p) > 1.0e-3 * abs(stix_p)
    # `eps @ b == S b` fails off axis for the same reason.
    assert not np.allclose(tilted @ direction, stix_s * direction, rtol=1.0e-9, atol=0.0)

    # On axis the two descriptions coincide: this is the case V3 tested.
    axial = evaluate(TARGET, FIELD, [ELECTRON])
    _, _, axial_p = stix_scalars(FIELD, [ELECTRON])
    assert_agrees(np.array([[axial[2, 2]]]), np.array([[axial_p]]))
    assert_agrees(
        axial @ np.array([0.0, 0.0, 1.0]), np.array([0.0, 0.0, axial_p])
    )


def test_the_off_diagonal_entries_are_the_cross_product_entries():
    """``i D [b]_x`` in the caller's basis, plus the ``(P - S) b b`` part.

    An off-diagonal entry is the sum of two terms: the antisymmetric purely
    imaginary ``i D [b]_x`` and the symmetric real ``(P - S) b_i b_j``.  A
    field-aligned reading would see only the first.  Both are asserted here
    against a body-local assembly, with the tolerance scaled by the magnitude of
    the term rather than by a unit reference.
    """
    tilted = evaluate(TARGET, TILTED_FIELD, [ELECTRON])
    direction = TILTED_FIELD / np.linalg.norm(TILTED_FIELD)
    stix_s, stix_d, stix_p = stix_scalars(TILTED_FIELD, [ELECTRON])
    outer = stix_p - stix_s

    def agrees_with_term(actual, term):
        assert abs(actual - term) <= INDEPENDENT_ASSEMBLY_RELATIVE_AGREEMENT * abs(term)

    agrees_with_term(tilted[0, 1], 1j * stix_d * -direction[2] + outer * direction[0] * direction[1])
    agrees_with_term(tilted[1, 2], 1j * stix_d * -direction[0] + outer * direction[1] * direction[2])
    # The x-z entry has no cross term at this field because b_y == 0, so it is
    # purely the symmetric outer-product part.
    assert direction[1] == 0.0
    agrees_with_term(tilted[0, 2], outer * direction[0] * direction[2])
    assert tilted[0, 2].imag == 0.0 and tilted[0, 2] != 0.0
    # The diagonal carries the outer-product part too, and its imaginary part is
    # the zero diagonal of the cross term.
    agrees_with_term(tilted[0, 0], stix_s + outer * direction[0] ** 2)
    assert tilted[0, 0].imag == 0.0 and tilted[2, 2].imag == 0.0


def test_the_matrix_is_the_independent_assembly_in_the_callers_basis():
    species = [ELECTRON, PROTON, dict(ELECTRON, density_m3=2.0e18, collision_rate_s_inv=3.0e5)]
    for field in (FIELD, TILTED_FIELD):
        assert_agrees(evaluate(TARGET, field, species), assemble(field, species))


def test_the_document_does_not_claim_a_field_aligned_frame():
    """The wording is part of the contract the review asked to correct.

    The phrase is allowed to appear where the module is explaining which reading it
    rejects; what it must not do is assert that the returned matrix *is* the
    field-aligned representation.  Both texts are checked for the affirmative claim
    and for the corrected one, so a later edit that reverts the wording fails here.
    """
    module_text = TARGET.__doc__ or ""
    function_text = TARGET.cold_plasma_dielectric_tensor.__doc__ or ""
    affirmative_claims = (
        "tensor is expressed in the local field-aligned frame",
        "expressed in the field-aligned frame",
        "in the local field-aligned frame built from",
    )
    for raw in (module_text, function_text):
        # The docstrings are reStructuredText wrapped at 79 columns; collapse the
        # markup and the line breaks so the claim is checked on the words.
        text = " ".join(raw.replace("**", "").split())
        assert "caller's supplied Cartesian basis" in text
        for claim in affirmative_claims:
            assert claim not in text, claim
    # The module must name the rejected reading and deny it; the function must name
    # the corrected one.
    module_text_normalised = " ".join(module_text.replace("**", "").split())
    assert "field-aligned frame" in module_text_normalised
    assert "is not a hidden field-aligned coordinate transform" in module_text_normalised
    function_text_normalised = " ".join(function_text.replace("**", "").split())
    assert "It is not a field-aligned coordinate transform" in function_text_normalised


# ---------------------------------------------------------------------------
# Correction 6 (V5) -- a finite input whose arithmetic is not representable
# ---------------------------------------------------------------------------


def test_the_review_witness_is_rejected_with_the_named_class():
    """The V4 defect, closed, on the expert review's own counterexample.

    ``cold_plasma_dielectric_tensor(1e308, [0, 0, 0.3], [electron])`` satisfies
    the stated input contract -- the frequency is finite and strictly positive --
    and a predecessor returned an all-NaN tensor for it, because
    ``omega * denominator`` overflows to infinity and the accumulation then
    evaluates ``inf / inf``, which is NaN rather than infinity.  The maintained
    module rejects the call.  The rejection is whole-call: no partial tensor is
    produced.  The predecessor's all-NaN answer is frozen in the snapshot and is
    not replayed here.
    """
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, FIELD, [ELECTRON], frequency_hz=1.0e308)
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)


def test_the_field_overflow_route_is_rejected_at_the_arithmetics_own_boundary():
    """The second route the review named: the field/species arithmetic.

    ``q B / m`` overflows for a finite field, so the denominator is infinite and
    the off-diagonal accumulation evaluates ``inf / inf``.  A predecessor returned
    an all-NaN tensor at ``1e300 T`` and a *finite* tensor at ``1e150 T`` -- the
    leading-order vacuum limit, reached because ``x / inf`` is exactly zero, which
    drops the species contribution instead of evaluating it.  Both are rejected
    here, and the second is the price of failing closed on an unrepresentable
    intermediate.

    The boundary is the arithmetic's own and is not a chosen threshold: the
    largest decade whose cyclotron square is still representable is accepted and
    the next decade is rejected.
    """
    for exponent in (150, 300):
        field = 10.0 ** exponent * np.array([0.0, 0.0, 1.0])
        # The overflow is the subject of the test, so the warning it raises is
        # silenced here rather than left to obscure a real failure elsewhere.
        with pytest.raises(ColdPlasmaOverflowError) as raised:
            with np.errstate(invalid="ignore", over="ignore"):
                evaluate(TARGET, field, [ELECTRON])
        assert str(raised.value).startswith(OVERFLOW_MESSAGE)
        assert "species index 0" in str(raised.value)
    accepted = evaluate(TARGET, 1.0e142 * np.array([0.0, 0.0, 1.0]), [ELECTRON])
    assert np.all(np.isfinite(accepted))
    with pytest.raises(ColdPlasmaOverflowError):
        with np.errstate(invalid="ignore", over="ignore"):
            evaluate(TARGET, 1.0e143 * np.array([0.0, 0.0, 1.0]), [ELECTRON])


def test_the_species_route_overflow_is_in_the_quotient_not_the_numerator():
    """The third route, and the wording the review corrected.

    A finite density of ``1e308`` m^-3 is rejected, and the reason matters because
    an earlier document stated it wrongly: ``n q^2`` is **finite** there -- about
    ``2.57e270`` for an electronic charge -- and it is the *quotient* after the
    division by ``eps0 * m`` (about ``8.07e-42``) that overflows to infinity.  So
    the rejection comes from the plasma contribution being unrepresentable, not
    from the numerator.  The two facts are asserted separately here so the
    distinction cannot drift back out of the document.
    """
    numerator = 1.0e308 * ELECTRON["charge_c"] * ELECTRON["charge_c"]
    assert math.isfinite(numerator), (
        "the numerator is finite; the document must not claim n*q^2 overflows"
    )
    divisor = VACUUM_PERMITTIVITY * ELECTRON["mass_kg"]
    with np.errstate(over="ignore", invalid="ignore"):
        assert not math.isfinite(numerator / divisor), (
            "the quotient after division by eps0*m is what overflows"
        )
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, FIELD, [dict(ELECTRON, density_m3=1.0e308)])
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_the_overflow_class_is_distinct_from_the_resonance_class():
    """Two classes, because the causes and the remedies differ.

    A caller that catches ``ValueError`` still catches both; a caller that needs to
    tell a physical singularity from an arithmetic limit can.
    """
    assert issubclass(ColdPlasmaOverflowError, ValueError)
    assert issubclass(ColdPlasmaResonanceError, ValueError)
    assert not issubclass(ColdPlasmaOverflowError, ColdPlasmaResonanceError)
    assert not issubclass(ColdPlasmaResonanceError, ColdPlasmaOverflowError)
    with pytest.raises(ValueError):
        evaluate(TARGET, FIELD, [ELECTRON], frequency_hz=1.0e308)
    with pytest.raises(ValueError):
        evaluate(TARGET, np.array([0.0, 0.0, RESONANT_FIELD_T]), [ELECTRON])
    # Neither class is raised by an ordinary accepted call.
    assert np.all(np.isfinite(evaluate(TARGET, FIELD, [ELECTRON])))


# ---------------------------------------------------------------------------
# Correction 7 (V6) -- a finite subnormal mass underflows the divisor to zero
# ---------------------------------------------------------------------------

# The review's witness: the smallest positive double.  It satisfies the declared
# input contract (`mass_kg` finite and strictly positive) and makes the product
# `VACUUM_PERMITTIVITY * mass` underflow to exactly zero.
REVIEW_SUBNORMAL_MASS_KG = 5e-324


def test_the_review_subnormal_mass_is_rejected_with_the_named_class():
    """The V5 defect, closed, on the expert review's own counterexample.

    ``cold_plasma_dielectric_tensor(1.0, [0, 0, 0], [{density_m3: 1.0,
    charge_c: 1.0, mass_kg: 5e-324}])`` satisfies the declared input contract --
    every value is finite and the mass is strictly positive -- and a predecessor
    raised an undocumented ``ZeroDivisionError``, because ``VACUUM_PERMITTIVITY *
    mass`` underflows to exactly zero before the plasma contribution is divided by
    it.  That is not a ``ValueError`` and not part of the documented failure
    contract.

    The maintained module checks the divisor before the division and fails closed
    with the same named ``ColdPlasmaOverflowError``.  The predecessor's leaked
    ``ZeroDivisionError`` is frozen in the snapshot and is not replayed here.
    """
    species = [{"density_m3": 1.0, "charge_c": 1.0, "mass_kg": REVIEW_SUBNORMAL_MASS_KG}]
    assert VACUUM_PERMITTIVITY * REVIEW_SUBNORMAL_MASS_KG == 0.0
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, np.zeros(3), species, frequency_hz=1.0)
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_the_subnormal_mass_route_raises_the_named_class_and_no_partial_result():
    """What the review asked to be asserted directly, in one place.

    Three separate claims, because they fail for different reasons.  The
    exception is *named* -- catching ``ZeroDivisionError`` would pass even though
    the contract is broken, so the class itself is asserted rather than the fact
    that something was raised.  It is a ``ValueError``, so a caller that already
    treats this operator's input rejections as ``ValueError`` is unaffected.  And
    the rejection is whole-call: the call raises rather than returning anything,
    so no tensor and no partially assembled scalar escapes -- including when the
    offending species is not the first one, which is where a per-species
    accumulator could otherwise leak the work already done.
    """
    assert VACUUM_PERMITTIVITY * REVIEW_SUBNORMAL_MASS_KG == 0.0
    subnormal = {"density_m3": 1.0, "charge_c": 1.0, "mass_kg": REVIEW_SUBNORMAL_MASS_KG}

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, FIELD, [subnormal])
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)

    # A species that contributes is rejected after an earlier species has already
    # accumulated, and the index names the offending one.
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, FIELD, [ELECTRON, subnormal])
    assert "(species index 1)" in str(raised.value)

    # A species the caller declares inert -- zero density -- is skipped before
    # the divisor is used, so the same subnormal mass cannot reject a call it
    # does not move.  This is the skip rule, re-asserted where the divisor guard
    # changes the arithmetic around it.  The skip is decided on the *inputs*: a
    # species whose `n * q * q` merely underflows to zero is not inert, and is
    # covered below.
    inert = dict(subnormal, density_m3=0.0)
    assert np.array_equal(evaluate(TARGET, FIELD, [inert]), evaluate(TARGET, FIELD, []))


# The expert re-review's counterexample, and the defect it found in that pass.
#
# Both operands of `n * q * q` are non-zero and finite, but the product underflows
# to exactly zero; `eps0 * m` underflows to zero as well.  A predecessor answered
# this with the vacuum tensor, because the skip had been decided on the computed
# numerator -- which reads a non-zero species as an inert one and bypasses the
# divisor guard at the same time.
REVIEW_UNDERFLOWING_CHARGE_C = 5e-324


def test_a_nonzero_species_whose_numerator_underflows_is_not_treated_as_inert():
    """The counterexample: a zero *product* is not a zero *contribution*.

    ``density_m3 = 1.0`` and ``charge_c = 5e-324`` are both non-zero, so the
    species contributes; the product ``n * q * q`` is zero only because double
    precision cannot represent it, and ``eps0 * m`` is zero for the same reason.
    No representable contribution exists, so the call must fail closed.  A
    predecessor leaked ``ZeroDivisionError`` here; that is frozen in the snapshot
    and is not replayed.
    """
    species = [
        {
            "density_m3": 1.0,
            "charge_c": REVIEW_UNDERFLOWING_CHARGE_C,
            "mass_kg": REVIEW_SUBNORMAL_MASS_KG,
        }
    ]
    assert 1.0 * REVIEW_UNDERFLOWING_CHARGE_C * REVIEW_UNDERFLOWING_CHARGE_C == 0.0
    assert VACUUM_PERMITTIVITY * REVIEW_SUBNORMAL_MASS_KG == 0.0
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, np.zeros(3), species, frequency_hz=1.0)
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_only_an_explicitly_inert_species_is_skipped():
    """Three ways to get a zero contribution, and only one of them is inert.

    ``density == 0.0`` and ``charge == 0.0`` are the caller stating that the
    species contributes nothing, and both are skipped even with a subnormal mass
    that would fail the divisor check -- the guard must not reject a species for a
    mass it never uses.  That is now the only route on which a species leaves the
    loop without contributing.

    A non-zero density and charge whose *product* underflows is a different thing
    and is rejected, which the test above measures.  And a non-zero species whose
    quotient rounds to zero after a division between two representable positive
    operands is rejected too -- on the review's own counterexample, whose exact
    final contribution is ``0.14134361358724294``.  A predecessor treated that
    quotient as negligible and returned the vacuum tensor; that divergence is
    frozen in the snapshot, and what is asserted here is the current rejection.
    """
    underflowing = {
        "density_m3": 1.0,
        "charge_c": REVIEW_UNDERFLOWING_CHARGE_C,
        "mass_kg": REVIEW_SUBNORMAL_MASS_KG,
    }
    vacuum = evaluate(TARGET, FIELD, [])
    for declared_inert in (
        dict(underflowing, density_m3=0.0),
        dict(underflowing, charge_c=0.0),
    ):
        assert np.array_equal(evaluate(TARGET, FIELD, [declared_inert]), vacuum)

    # A zero quotient between two representable positive operands.  Both operands
    # are asserted representable before the quotient is taken, so the case really
    # is the one the old rule was written for.
    negligible = {"density_m3": 1.0e-160, "charge_c": 1.0e-80, "mass_kg": 1.0e15}
    numerator = negligible["density_m3"] * negligible["charge_c"] ** 2
    divisor = VACUUM_PERMITTIVITY * negligible["mass_kg"]
    assert numerator > 0.0 and divisor > 0.0
    assert numerator / divisor == 0.0
    with pytest.raises(ColdPlasmaOverflowError):
        evaluate(TARGET, FIELD, [negligible])


# ---------------------------------------------------------------------------
# Correction 8 (V8) -- a finite non-zero species whose numerator underflows
# ---------------------------------------------------------------------------

# The V7 expert review's own counterexample.  Every value is finite, so the
# declared input contract accepts it, and every one is non-zero, so the species is
# not inert.  The double-precision product `n * q * q` underflows to exactly zero
# while `eps0 * m` is the representable non-zero denormal `1e-323`.
REVIEW_NUMERATOR_UNDERFLOW = {
    "density_m3": 1.0e308,
    "charge_c": 5e-324,
    "mass_kg": 1.0e-312,
}
REVIEW_NUMERATOR_UNDERFLOW_FREQUENCY_HZ = 0.01

# The exact quotient, and its effect on P, measured in high precision and pinned
# here as decimals rather than recomputed in double precision -- the whole point
# of the witness is that double precision cannot form them.
REVIEW_EXACT_QUOTIENT = 2.7568972734915313e-16
REVIEW_P_CORRECTION = 6.983302373262393e-14
REVIEW_EXPECTED_P = 0.9999999999999302


def test_the_numerator_underflow_witness_is_rejected_whole_call():
    """The defect closed, on the expert review's own counterexample.

    A predecessor keyed its rejection on the divisor and never on the numerator,
    and said so.  For this input the divisor *is* representable, so it took its
    zero-quotient skip and returned the exact identity tensor -- a silent drop of
    a non-zero species whose exact contribution is representable and measurable.
    The maintained module rejects the call: the numerator collapse now surfaces at
    the quotient, which is exactly zero whenever the numerator is.

    Four things are asserted separately, because they fail for different reasons:
    the operands really do collapse as the review says (measured, not assumed);
    the exact quotient is an ordinary representable double, so the contribution
    was representable rather than negligible; the rejection is the *named* class,
    whole-call, with the offending species named; and the vacuum tensor this
    input is distinguished from is the identity.  The predecessor's vacuum answer
    is frozen in the snapshot and is not replayed here.
    """
    species = [dict(REVIEW_NUMERATOR_UNDERFLOW)]
    field = np.zeros(3)

    # The review's arithmetic, re-measured here rather than taken on trust.
    numerator = (
        REVIEW_NUMERATOR_UNDERFLOW["density_m3"]
        * REVIEW_NUMERATOR_UNDERFLOW["charge_c"]
        * REVIEW_NUMERATOR_UNDERFLOW["charge_c"]
    )
    divisor = VACUUM_PERMITTIVITY * REVIEW_NUMERATOR_UNDERFLOW["mass_kg"]
    assert numerator == 0.0, "the numerator must underflow to exactly zero"
    assert divisor > 0.0 and math.isfinite(divisor), (
        "the divisor must be a representable non-zero double, which is what made "
        "a divisor-keyed rejection silent here"
    )

    # The exact quotient is representable, and its effect on P is resolvable: it is
    # about 315 ulp of one.  So the skipped contribution was neither zero nor
    # below the representable range.
    assert math.isfinite(REVIEW_EXACT_QUOTIENT) and REVIEW_EXACT_QUOTIENT > 0.0
    assert REVIEW_P_CORRECTION > 300.0 * math.ulp(1.0)
    assert REVIEW_EXPECTED_P != 1.0
    # `REVIEW_EXPECTED_P` is the correctly rounded double nearest the exact
    # `1 - REVIEW_P_CORRECTION`, so it need not reproduce the correction exactly:
    # both literals carry one rounding, and the difference between them is the
    # ulp of a number near one.  The bound is asserted rather than the equality,
    # because the equality is not what the witness claims.
    assert abs((1.0 - REVIEW_EXPECTED_P) - REVIEW_P_CORRECTION) <= math.ulp(1.0)

    vacuum = evaluate(TARGET, field, [])
    assert np.array_equal(vacuum, np.eye(3, dtype=complex))

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, species,
            frequency_hz=REVIEW_NUMERATOR_UNDERFLOW_FREQUENCY_HZ,
        )
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_both_underflow_routes_are_rejected_with_the_same_named_message():
    """What the boundary move costs, and what it does not.

    A predecessor rejected exactly the entries whose *divisor* was
    unrepresentable.  The maintained module rejects those too -- same class, same
    message, same index -- and additionally rejects the entries whose *numerator*
    collapsed while their divisor was representable.  Both halves are asserted
    here; the predecessor's half is asserted through its own recorded behaviour
    (the vacuum tensor) only in the frozen snapshot.
    """
    field = np.zeros(3)
    frequency_hz = 1.0

    # Unchanged: the divisor route is rejected, with the named message and index.
    divisor_underflow = {
        "density_m3": 1.0,
        "charge_c": 1.0,
        "mass_kg": REVIEW_SUBNORMAL_MASS_KG,
    }
    with pytest.raises(ColdPlasmaOverflowError) as divisor_raised:
        evaluate(TARGET, field, [divisor_underflow], frequency_hz=frequency_hz)
    assert str(divisor_raised.value) == f"{OVERFLOW_MESSAGE} (species index 0)"

    # Added: the numerator route with a representable divisor.
    numerator_underflow = dict(REVIEW_NUMERATOR_UNDERFLOW)
    assert VACUUM_PERMITTIVITY * numerator_underflow["mass_kg"] > 0.0
    with pytest.raises(ColdPlasmaOverflowError) as numerator_raised:
        evaluate(
            TARGET, field, [numerator_underflow],
            frequency_hz=REVIEW_NUMERATOR_UNDERFLOW_FREQUENCY_HZ,
        )
    assert str(numerator_raised.value) == f"{OVERFLOW_MESSAGE} (species index 0)"


def test_a_zero_numerator_with_a_representable_divisor_is_not_a_negligible_contribution():
    """A collapsed numerator is not a negligible contribution, at either precision.

    Two species both produce a zero quotient and neither may be skipped.  The
    first has a numerator that collapsed to exactly zero and a representable
    divisor: its exact quotient is an ordinary double.  The second has a positive
    numerator and a positive divisor whose quotient merely rounds to zero: its
    exact quotient is below the double range, but that is a statement about the
    quotient, not about the contribution, which is rescaled by ``1 / omega**2``
    before it is used.  A predecessor treated both as negligible and returned the
    vacuum tensor; the maintained module rejects both.
    """
    field = FIELD

    collapsed = dict(REVIEW_NUMERATOR_UNDERFLOW)
    assert (
        collapsed["density_m3"] * collapsed["charge_c"] ** 2 == 0.0
    ), "the numerator collapsed"
    assert VACUUM_PERMITTIVITY * collapsed["mass_kg"] > 0.0, "the divisor is representable"
    with pytest.raises(ColdPlasmaOverflowError):
        evaluate(TARGET, field, [collapsed])

    negligible = {"density_m3": 1.0e-160, "charge_c": 1.0e-80, "mass_kg": 1.0e15}
    numerator = negligible["density_m3"] * negligible["charge_c"] ** 2
    divisor = VACUUM_PERMITTIVITY * negligible["mass_kg"]
    assert numerator > 0.0 and divisor > 0.0, "both operands are representable and positive"
    assert numerator / divisor == 0.0, "the quotient is what rounds to zero"
    with pytest.raises(ColdPlasmaOverflowError):
        evaluate(TARGET, field, [negligible])


def test_the_numerator_guard_does_not_reject_a_declared_inert_species():
    """The inert skip still comes first, on the review's own operands.

    The quotient guard fires on a computed zero, and the product of this species
    collapses too -- but the caller declared it inert, so it is skipped before the
    numerator is ever formed.  The guard must not reject a species for operands it
    never uses, and the skip is decided on the inputs rather than on the computed
    product.  Measured against the empty-species vacuum tensor, so the claim is
    that the entry is observationally absent rather than merely accepted.
    """
    vacuum = evaluate(TARGET, FIELD, [])
    for zeroed in ("density_m3", "charge_c"):
        inert = dict(REVIEW_NUMERATOR_UNDERFLOW, **{zeroed: 0.0})
        result = evaluate(
            TARGET,
            FIELD,
            [inert],
            frequency_hz=REVIEW_NUMERATOR_UNDERFLOW_FREQUENCY_HZ,
        )
        assert np.array_equal(result, vacuum), zeroed


# ---------------------------------------------------------------------------
# Correction 9 (V9) -- a zero plasma contribution is not a negligible one
# ---------------------------------------------------------------------------

# The V8 expert review's own counterexample.  Every value is finite, so the
# declared input contract accepts it, and every one is non-zero, so the species is
# not inert.  Both operands of the plasma contribution are representable and
# positive: the numerator `n * q^2` is the smallest positive subnormal double and
# the divisor `eps0 * m` is `3.5416751251200003`.  The quotient nevertheless
# underflows to exactly zero, and the *later* Stix division by `omega**2` -- which
# is itself `1e-323` -- restores the contribution to an ordinary representable
# number.
REVIEW_ZERO_QUOTIENT = {
    "density_m3": 5e-324,
    "charge_c": 1.0,
    "mass_kg": 4e11,
}
REVIEW_ZERO_QUOTIENT_FREQUENCY_HZ = 5e-163

# The review's high-precision values, re-derived in this file from exact rational
# arithmetic over the same doubles (see `exact_ratio` and the test body) and
# pinned here so a later edit cannot quietly restate them.  `math.pi` is used as
# the double the module itself uses.
REVIEW_ZERO_QUOTIENT_EXACT_WP2 = 1.3950055507265265e-324
REVIEW_ZERO_QUOTIENT_EXACT_STIX_CORRECTION = 0.14134361358724294
REVIEW_ZERO_QUOTIENT_EXPECTED_P = 0.8586563864127571


def test_the_zero_quotient_witness_is_rejected_whole_call():
    """The V8 defect, closed, on the V8 expert review's own counterexample.

    A predecessor kept the zero-quotient skip for a quotient formed between two
    representable positive operands, and stated that such a quotient "is at most
    one ulp of the smallest normal double, so no contribution of a magnitude the
    caller could resolve has been discarded".  For this input both operands are
    indeed representable and positive, the quotient is indeed exactly zero -- and
    the exact final contribution is ``0.14134361358724294``, so the statement was
    false and the predecessor returned the exact identity tensor for a species
    whose ``P`` is ``0.8586563864127571``.

    Five things are asserted separately, because they fail for different reasons:
    the numerator really is the smallest positive subnormal and the divisor really
    is a large positive double; the quotient really does underflow to zero; the
    exact quotient, and the exact Stix correction it produces after division by
    ``omega**2``, are ordinary representable numbers rather than below the range
    -- computed here from exact rational arithmetic over the same doubles, with no
    high-precision runtime dependency; the rejection is the *named* class,
    whole-call, with the offending species named; and the ``P`` the skip discarded
    differs from one by an amount no caller could mistake for the vacuum.  The
    predecessor's identity-tensor answer is frozen in the snapshot and is not
    replayed here.
    """
    species = [dict(REVIEW_ZERO_QUOTIENT)]
    field = np.zeros(3)

    # The review's operands, re-measured here rather than taken on trust.
    numerator = (
        REVIEW_ZERO_QUOTIENT["density_m3"]
        * REVIEW_ZERO_QUOTIENT["charge_c"]
        * REVIEW_ZERO_QUOTIENT["charge_c"]
    )
    divisor = VACUUM_PERMITTIVITY * REVIEW_ZERO_QUOTIENT["mass_kg"]
    assert numerator > 0.0, "the numerator is a positive subnormal, not a collapse"
    assert numerator == 5e-324 and math.ulp(0.0) == 5e-324, (
        "the numerator is the smallest positive subnormal double"
    )
    assert divisor > 0.0 and math.isfinite(divisor)
    assert divisor == 3.5416751251200003, "the divisor is a representable positive double"
    assert numerator / divisor == 0.0, "the quotient underflows to exactly zero"

    # The exact arithmetic, from exact rationals over the same doubles.
    omega = 2.0 * math.pi * REVIEW_ZERO_QUOTIENT_FREQUENCY_HZ
    omega_squared = omega * omega
    assert omega_squared == 1e-323, "the later Stix denominator is itself subnormal"
    exact_wp2 = exact_ratio(numerator, divisor)
    # The oracle evaluates `wp2 / omega**2` exactly, over the same two doubles the
    # module divides.  That is the quantity the skip discarded.
    exact_stix_correction = exact_wp2 / Fraction(omega_squared)
    # The exact quotient is far below the double range...
    assert float(exact_wp2) == 0.0
    # ...but the contribution it stands for is not: it is 0.1413..., an ordinary
    # double, and `P` is 0.8586... rather than one.
    assert exact_stix_correction > Fraction(1, 10)
    assert abs(float(exact_stix_correction) - REVIEW_ZERO_QUOTIENT_EXACT_STIX_CORRECTION) <= (
        2.0e-3 * REVIEW_ZERO_QUOTIENT_EXACT_STIX_CORRECTION
    ), (
        "the review's published value agrees with this file's exact rational "
        "evaluation to a rounding path, not to the last bit.  The review evaluated "
        "the quotient in high precision; this test evaluates it over the two "
        "doubles the module forms, and `omega**2` is the subnormal `1e-323`, which "
        "carries two significant bits, so the two differ by about 1.2e-3 relative. "
        "The bound is relative and stated rather than an equality that is not what "
        "either measurement claims."
    )
    assert math.isfinite(REVIEW_ZERO_QUOTIENT_EXACT_WP2)
    assert REVIEW_ZERO_QUOTIENT_EXPECTED_P < 0.99, (
        "the discarded contribution moves P by more than one percent"
    )

    vacuum = evaluate(TARGET, field, [])
    assert np.array_equal(vacuum, np.eye(3, dtype=complex))

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, species,
            frequency_hz=REVIEW_ZERO_QUOTIENT_FREQUENCY_HZ,
        )
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_the_boundary_moves_only_at_the_zero_quotient():
    """What the correction changed, and what it did not.

    Three entries, side by side, so the boundary is a measurement:

    * a species the caller declared inert: still skipped, and observationally
      absent;
    * a species whose numerator collapses with a representable divisor: rejected
      both before and after the correction, with the same named class and
      message -- the correction reaches it through the quotient guard instead of
      the numerator guard, which is not observable;
    * a species whose numerator and divisor are both representable and positive
      and whose quotient is zero: answered with the identity tensor before the
      correction and rejected now.  That is the whole of the correction.
    """
    field = np.zeros(3)
    vacuum = evaluate(TARGET, field, [])
    assert np.array_equal(vacuum, np.eye(3, dtype=complex))

    # 1. Declared inert: unchanged, and it is now the only skipping route.
    for zeroed in ("density_m3", "charge_c"):
        inert = dict(REVIEW_ZERO_QUOTIENT, **{zeroed: 0.0})
        assert np.array_equal(
            evaluate(
                TARGET, field, [inert],
                frequency_hz=REVIEW_ZERO_QUOTIENT_FREQUENCY_HZ,
            ),
            vacuum,
        )

    # 2. Collapsed numerator with a representable divisor: rejected.
    collapsed = dict(REVIEW_NUMERATOR_UNDERFLOW)
    with pytest.raises(ColdPlasmaOverflowError) as ours_raised:
        evaluate(
            TARGET, field, [collapsed],
            frequency_hz=REVIEW_NUMERATOR_UNDERFLOW_FREQUENCY_HZ,
        )
    assert str(ours_raised.value) == f"{OVERFLOW_MESSAGE} (species index 0)"

    # 3. Representable operands, zero quotient: rejected.
    representable = dict(REVIEW_ZERO_QUOTIENT)
    assert (
        representable["density_m3"] * representable["charge_c"] ** 2 > 0.0
    ), "the numerator is representable"
    assert VACUUM_PERMITTIVITY * representable["mass_kg"] > 0.0, (
        "the divisor is representable"
    )
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, [representable],
            frequency_hz=REVIEW_ZERO_QUOTIENT_FREQUENCY_HZ,
        )
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_the_zero_quotient_guard_subsumes_the_numerator_guard():
    """One statement covers both underflow routes, and the contract is identical.

    An earlier revision carried two guards: `not isfinite(numerator) or numerator
    == 0.0`, then the divisor check, then the skip.  The maintained module carries
    `not isfinite(numerator)`, the divisor check, then
    `plasma_frequency_squared == 0.0`.  The claim is that the second form accepts
    and rejects exactly the same inputs, because a numerator that collapses to zero
    makes the quotient zero while a numerator that is not finite is caught earlier
    -- and that the caller cannot tell the forms apart.

    Both halves are measured: the review's collapsed numerator still raises the
    same class, message and index, and an ordinary accepted input is unaffected.
    """
    field = np.zeros(3)
    collapsed = dict(REVIEW_NUMERATOR_UNDERFLOW)
    assert collapsed["density_m3"] * collapsed["charge_c"] ** 2 == 0.0
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, [collapsed],
            frequency_hz=REVIEW_NUMERATOR_UNDERFLOW_FREQUENCY_HZ,
        )
    assert str(raised.value) == f"{OVERFLOW_MESSAGE} (species index 0)"
    # A non-finite numerator is still rejected by the earlier check, and a species
    # with an ordinary numerator is still evaluated.
    assert np.all(np.isfinite(evaluate(TARGET, FIELD, [ELECTRON])))
    # The module carries the quotient guard and no numerator-zero test, so the
    # rule is stated once.  Checked on the source rather than on behaviour,
    # because the behaviour is identical either way.
    source = Path(TARGET.__file__).read_text(encoding="utf-8")
    assert "plasma_frequency_squared == 0.0" in source
    assert "numerator == 0.0" not in source


def test_the_module_no_longer_claims_a_zero_quotient_is_negligible():
    """The two refuted statements are gone from every public explanation.

    The review's requirement 6: remove or correct every statement that a final-zero
    `wp2` is necessarily negligible, including the inaccurate
    denormal-numerator/denormal-divisor residual-band description.  The check is on
    the module text because that is where the claim lived; the asset document is
    checked by the document validator.

    The refuted sentences may still appear *as quotations being refuted* -- the
    record is more honest that way than a silent deletion -- so the assertion is
    not that the words are absent but that they are never left standing: each one,
    where it appears, is followed by the sentence that refutes it.
    """
    module_text = " ".join((TARGET.__doc__ or "").replace("**", "").split())
    function_text = " ".join(
        (TARGET.cold_plasma_dielectric_tensor.__doc__ or "").replace("**", "").split()
    )
    quoted_and_refuted = (
        "so no contribution of a magnitude the caller could resolve has been discarded",
    )
    for text in (module_text, function_text):
        for claim in quoted_and_refuted:
            position = text.find(claim)
            while position != -1:
                following = text[position : position + len(claim) + 400]
                assert "The review refutes that" in following, (
                    "the refuted statement appears without its refutation"
                )
                position = text.find(claim, position + 1)
    # The corrected statements are present, in the words the review asks for.
    assert "an intermediate underflow is evidence about the intermediate" in (
        module_text.lower()
    )
    assert "is exactly zero" in function_text
    assert "the quotient of two positive subnormal doubles is at least" in module_text
    # The two claims the review named are gone as *claims*: neither the "at most
    # one ulp of the smallest normal double" reading of a zero quotient, nor the
    # denormal-numerator/denormal-divisor band, is stated anywhere.  Both appear
    # only inside the quotation that is refuted in the same sentence, which the
    # loop above has already checked.
    for text in (module_text, function_text):
        for claim in (
            "at most one ulp of the smallest normal double",
            "and the divisor is also a denormal can still round to a zero quotient",
        ):
            position = text.find(claim)
            while position != -1:
                assert "The review refutes that" in text[position : position + len(claim) + 400], (
                    claim
                )
                position = text.find(claim, position + 1)


# ---------------------------------------------------------------------------
# Correction 10 (V10) -- a representable factor does not make a representable
# product, and the Stix divisions consume products
# ---------------------------------------------------------------------------

# The V9 expert review's own counterexample.  Every value is finite, so the
# declared input contract accepts it, and every one is non-zero, so the species is
# not inert.  Every factor the earlier guards name is a representable non-zero
# double: the numerator is the smallest positive subnormal, the divisor is 1.0,
# the quotient is 5e-324, the cyclotron term is 8.8541878128e-162 and the Stix
# denominator is 1.579136704174297e-216.  The *product* `omega * denominator` is
# the failure: its exact value is 1.984e-324, below the smallest positive
# subnormal double, so the double product is exactly 0.0 and the division raised
# an undocumented ZeroDivisionError.
REVIEW_COLLAPSED_PRODUCT_FREQUENCY_HZ = 2e-109
REVIEW_COLLAPSED_PRODUCT_FIELD = [0.0, 0.0, 1e-150]
REVIEW_COLLAPSED_PRODUCT = {
    "density_m3": 5e-324,
    "charge_c": 1.0,
    "mass_kg": 112940906737.30191,
}

# The smallest positive subnormal double, pinned as a literal so the boundary the
# counterexample crosses is stated rather than implied.
SMALLEST_POSITIVE_SUBNORMAL = 5e-324

# The review's high-precision `D`, reproduced here from exact rational arithmetic
# over the same doubles.  It is quoted for one purpose only: to establish that the
# contribution the collapsed product discarded is an ordinary representable
# number, not a mathematical zero.  Nothing in the module computes it.
REVIEW_COLLAPSED_PRODUCT_HIGH_PRECISION_D = 2.2044679781874947e-161

# The V10 review's own counterexample, and a different witness from the one above.
# Here the shared denominator `omega * denominator` and the P denominator
# `omega * shifted` are both representable and non-zero, so every earlier guard
# passes.  The collapse is in the *S* numerator `wp2 * shifted`, which is `0j`:
# the S division does not raise, it silently drops the contribution, and a
# predecessor answered with a finite tensor whose transverse diagonal entry is
# exactly `1 + 0j`.  The field is *not* zero here -- its magnitude is `1e-150` T
# and `q / m` is non-zero -- so the represented `cyclotron` is `0.0` because the
# upstream `q |B| / m` rounds to zero, not because the field is absent.  That is
# the case the operand test in `_is_representable_product` deliberately does not
# decide, and the regression below measures it rather than describing it.
REVIEW_S_NUMERATOR_FREQUENCY_HZ = 1e-300 / (2.0 * math.pi)
REVIEW_S_NUMERATOR_FIELD = [0.0, 0.0, 1e-150]
REVIEW_S_NUMERATOR = {
    "density_m3": 1.0,
    "charge_c": 1e-150,
    "mass_kg": 2e34,
    "collision_rate_s_inv": 0.4,
}

# The magnitude of the exact imaginary part of the S correction the collapsed
# numerator discarded, reproduced here from exact rational arithmetic over the
# same doubles.  It is quoted for one purpose only: to establish that the entry
# the silent zero loses is an ordinary representable number, not a mathematical
# zero.  Nothing in the module computes it.
REVIEW_S_NUMERATOR_HIGH_PRECISION_S_IMAG = 1.2351641146031161e-23


def test_the_collapsed_product_witness_is_rejected_without_leaking_zero_division():
    """The defect closed, on the expert review's own counterexample.

    Six things are asserted separately, because they fail for different reasons:
    every factor the earlier guards name really is finite and non-zero, so the call
    really does reach the accumulation; the *product* ``omega * denominator``
    really does collapse to exactly zero while both of its operands are
    representable and positive; the exact product really is non-zero, so the
    collapse is a representability failure rather than a mathematical zero; the
    exact ``D`` contribution is an ordinary representable double, so the collapsed
    product stood for a real scientific contribution; the rejection is the *named*
    class, whole-call, with the offending species named; and no
    ``ZeroDivisionError`` escapes.  The predecessor's leaked ``ZeroDivisionError``
    is frozen in the snapshot and is not replayed here.
    """
    species = [dict(REVIEW_COLLAPSED_PRODUCT)]
    field = np.array(REVIEW_COLLAPSED_PRODUCT_FIELD)

    # The factors the earlier guards checked, re-measured here rather than taken on
    # trust.  Each one is a representable non-zero double, which is why the call
    # reached the division.
    numerator = (
        REVIEW_COLLAPSED_PRODUCT["density_m3"]
        * REVIEW_COLLAPSED_PRODUCT["charge_c"]
        * REVIEW_COLLAPSED_PRODUCT["charge_c"]
    )
    divisor = VACUUM_PERMITTIVITY * REVIEW_COLLAPSED_PRODUCT["mass_kg"]
    omega = 2.0 * math.pi * REVIEW_COLLAPSED_PRODUCT_FREQUENCY_HZ
    wp2 = numerator / divisor
    cyclotron = (
        REVIEW_COLLAPSED_PRODUCT["charge_c"]
        * math.sqrt(sum(component * component for component in field))
        / REVIEW_COLLAPSED_PRODUCT["mass_kg"]
    )
    denominator = (omega + 0j) ** 2 - cyclotron * cyclotron
    for label, value in (
        ("numerator", numerator),
        ("divisor", divisor),
        ("omega", omega),
        ("wp2", wp2),
        ("cyclotron", cyclotron),
        ("denominator", denominator),
    ):
        assert value != 0 and np.all(np.isfinite(value)), label

    # The failure.  Both operands of the product are representable and positive,
    # and the double product is exactly zero.
    assert omega > 0.0 and denominator.real > 0.0
    assert omega * denominator == 0j, "the product collapses in double precision"

    # It collapses because the exact product is below the double range, not
    # because it is zero.  That distinction is the whole of the review's finding:
    # a double `0.0` here means "not representable", not "nothing".
    exact_product = _exact_product(omega, denominator.real)
    assert exact_product > 0, "the exact product is non-zero"
    assert exact_product < Fraction(SMALLEST_POSITIVE_SUBNORMAL), (
        "the exact product is below the smallest positive subnormal double, so "
        "the double product is a correct rounding of a value binary64 cannot "
        "represent"
    )

    # The contribution the collapse discarded is an ordinary representable double.
    exact_d = _exact_product(cyclotron, wp2) / exact_product
    assert abs(float(exact_d) - REVIEW_COLLAPSED_PRODUCT_HIGH_PRECISION_D) <= (
        1.0e-3 * REVIEW_COLLAPSED_PRODUCT_HIGH_PRECISION_D
    ), "the review's published high-precision D is reproduced by exact arithmetic"
    assert float(exact_d) > SMALLEST_POSITIVE_SUBNORMAL, (
        "the lost D contribution is representable; reading the collapsed product "
        "as a harmless zero would drop an ordinary number"
    )

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, species,
            frequency_hz=REVIEW_COLLAPSED_PRODUCT_FREQUENCY_HZ,
        )
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert not isinstance(raised.value, ZeroDivisionError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_the_s_numerator_witness_is_rejected_rather_than_silently_zeroed():
    """The fourth-product witness, closed.

    The product this witness collapses is the ``S`` numerator ``wp2 * shifted``,
    which the earlier guards did not test at all: they tested the numerator
    ``n q^2``, the divisor ``eps0 * m``, the quotient ``wp2`` and the *finiteness*
    of the cyclotron term, the shifted frequency and the denominator.  Every one of
    those passes here, so the call reaches the accumulation and the division
    silently zeroes ``S`` -- the silent-zero direction, and a different failure
    mode from the ``ZeroDivisionError`` the other counterexample leaked.

    The zero cyclotron term is measured rather than described, because it is the
    one value in this input that could be misread: the field magnitude is
    ``1e-150`` T, not zero, and the charge and mass are non-zero, so the
    represented ``cyclotron`` is ``0.0`` because the upstream ``q |B| / m``
    rounded to zero.  It is not a physical or mathematical zero, and the
    regression asserts the non-zero inputs alongside it so the witness cannot be
    confused with the legitimate zero-field case.  A predecessor accepted it
    because it tested the cyclotron term only for finiteness, never for
    non-zeroness; that predecessor's finite tensor with the zeroed entry is frozen
    in the snapshot and is not replayed here.
    """
    species = [dict(REVIEW_S_NUMERATOR)]
    field = np.array(REVIEW_S_NUMERATOR_FIELD)

    magnitude = math.sqrt(sum(component * component for component in field))
    numerator = REVIEW_S_NUMERATOR["density_m3"] * REVIEW_S_NUMERATOR["charge_c"] ** 2
    divisor = VACUUM_PERMITTIVITY * REVIEW_S_NUMERATOR["mass_kg"]
    omega = 2.0 * math.pi * REVIEW_S_NUMERATOR_FREQUENCY_HZ
    wp2 = numerator / divisor
    cyclotron = REVIEW_S_NUMERATOR["charge_c"] * magnitude / REVIEW_S_NUMERATOR["mass_kg"]
    shifted = omega + 1j * REVIEW_S_NUMERATOR["collision_rate_s_inv"]
    denominator = shifted * shifted - cyclotron * cyclotron
    shared_denominator = omega * denominator
    p_denominator = omega * shifted

    # The zero cyclotron term is a rounding of non-zero inputs, not an absent
    # field.  Stated first so no later assertion can be read as the zero-field case.
    assert magnitude > 0.0, "the field is not zero"
    assert REVIEW_S_NUMERATOR["charge_c"] != 0.0
    assert REVIEW_S_NUMERATOR["mass_kg"] > 0.0
    assert REVIEW_S_NUMERATOR["charge_c"] * magnitude > 0.0
    assert cyclotron == 0.0, (
        "the represented cyclotron term is 0.0 because q |B| / m underflows, and "
        "it is not a mathematical zero"
    )

    # Every factor the earlier guards require to be representable and non-zero is
    # both, which is why the call reached the division instead of failing closed.
    for label, value in (
        ("numerator", numerator),
        ("divisor", divisor),
        ("omega", omega),
        ("wp2", wp2),
        ("shifted", shifted),
        ("denominator", denominator),
    ):
        assert value != 0 and np.all(np.isfinite(value)), label

    # The other two products the divisions consume are representable and non-zero,
    # so this witness is the S-numerator route and not the shared-denominator
    # route the other counterexample reports.
    assert shared_denominator != 0j, "the shared S/D denominator is representable"
    assert p_denominator != 0j, "the P denominator is representable"

    # The fourth product, and the failure.
    assert wp2 == SMALLEST_POSITIVE_SUBNORMAL
    assert wp2 * shifted == 0j, "the S numerator collapses in double precision"
    exact_s_numerator_imag = _exact_product(
        wp2, REVIEW_S_NUMERATOR["collision_rate_s_inv"]
    )
    assert exact_s_numerator_imag > 0, "the exact S numerator is non-zero"
    assert exact_s_numerator_imag < Fraction(SMALLEST_POSITIVE_SUBNORMAL), (
        "the exact S numerator is below the smallest positive subnormal double, "
        "so the double product is a correct rounding of a value binary64 cannot "
        "represent"
    )

    # The contribution the collapse discarded is an ordinary representable double,
    # and its sign is the sign the S accumulation would have carried.
    exact_s_correction_imag = exact_s_numerator_imag / Fraction(shared_denominator.real)
    assert exact_s_correction_imag < 0, "the S correction is negative"
    s_correction_magnitude = -float(exact_s_correction_imag)
    assert abs(s_correction_magnitude - REVIEW_S_NUMERATOR_HIGH_PRECISION_S_IMAG) <= (
        1.0e-3 * REVIEW_S_NUMERATOR_HIGH_PRECISION_S_IMAG
    ), "the review's published high-precision S is reproduced by exact arithmetic"

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, species,
            frequency_hz=REVIEW_S_NUMERATOR_FREQUENCY_HZ,
        )
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert not isinstance(raised.value, ZeroDivisionError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_every_stix_division_has_its_product_guarded():
    """The review's requirement 6: an audit of all three accumulations.

    The three divisions consume four *distinct* products, and the audit is stated
    over the products rather than over the divisions, because one division can
    consume two of them and one product can be shared by two divisions:
    ``omega * denominator`` is the shared denominator of ``S`` and of ``D``,
    ``cyclotron * wp2`` is the numerator of ``D``, ``wp2 * shifted`` is the
    numerator of ``S``, and ``omega * shifted`` is the denominator of ``P``.
    Conflating the count of divisions with the count of products is the mistake
    this section is written to avoid.

    Each product is audited by driving it to the collapsed-product state and
    measuring the failure, so the expressions are covered individually rather than
    by one witness that happens to reach one of them.  Two things are asserted for
    each witness, and they are different claims: the product collapses to exactly
    zero in double precision *and* the exact product is non-zero, so the collapse
    is a representability failure; and the call fails closed with the named class
    rather than leaking ``ZeroDivisionError`` or silently returning a tensor.

    Three of the four products have an independent witness, and the count is
    stated rather than the routes being enumerated loosely: ``omega *
    denominator`` and ``cyclotron * wp2`` are driven here, and ``wp2 * shifted``
    is driven by
    :func:`test_the_s_numerator_witness_is_rejected_rather_than_silently_zeroed`.
    ``omega * shifted`` is the one product for which no independent witness is
    presented, and no claim is made either way about whether one exists. Because
    no witness reaches it, its guard is asserted on the module source instead --
    all four products appear as arguments of the guard, so the audit covers the
    four and not merely the three a witness happens to drive. Which guard fires
    is not observable to a caller anyway, since all of them raise the same class
    with the same message.
    """
    field = np.zeros(3)

    # The four products, as the guard's call sites rather than as prose.  The
    # fourth has no witness, so the source is what establishes that it is
    # guarded at all.
    source = Path(TARGET.__file__).read_text(encoding="utf-8")
    for product in (
        "_is_representable_product(omega, denominator)",
        "_is_representable_product(cyclotron, plasma_frequency_squared)",
        "_is_representable_product(plasma_frequency_squared, shifted)",
        "_is_representable_product(omega, shifted)",
    ):
        assert product in source, product

    # Witness 1 and 2: the review's own counterexample.  `omega * denominator` is
    # the denominator of the S accumulation and of the D accumulation, so this one
    # input drives both.
    collapsed_denominator = dict(REVIEW_COLLAPSED_PRODUCT)
    omega = 2.0 * math.pi * REVIEW_COLLAPSED_PRODUCT_FREQUENCY_HZ
    cyclotron = (
        REVIEW_COLLAPSED_PRODUCT["charge_c"] * REVIEW_COLLAPSED_PRODUCT_FIELD[2]
        / REVIEW_COLLAPSED_PRODUCT["mass_kg"]
    )
    denominator = (omega + 0j) ** 2 - cyclotron * cyclotron
    assert omega * denominator == 0j
    assert _exact_product(omega, denominator.real) > 0
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, [collapsed_denominator],
            frequency_hz=REVIEW_COLLAPSED_PRODUCT_FREQUENCY_HZ,
        )
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)

    # Witness 3: the D numerator `cyclotron * wp2` collapses while the shared
    # denominator stays representable -- the silent-zero direction of the same
    # failure class, reached through the D numerator rather than through the S
    # numerator the dedicated regression above drives.
    collapsed_numerator = {
        "density_m3": 5e-324,
        "charge_c": 1.0,
        "mass_kg": 1.0e8,
    }
    field_n = np.array([0.0, 0.0, 1.0])
    numerator = (
        collapsed_numerator["density_m3"] * collapsed_numerator["charge_c"] ** 2
    )
    divisor = VACUUM_PERMITTIVITY * collapsed_numerator["mass_kg"]
    wp2 = numerator / divisor
    cyclotron_n = (
        collapsed_numerator["charge_c"] * field_n[2] / collapsed_numerator["mass_kg"]
    )
    denominator_n = (omega + 0j) ** 2 - cyclotron_n * cyclotron_n
    assert wp2 != 0.0 and math.isfinite(wp2), "the quotient is a representable double"
    assert cyclotron_n != 0.0 and math.isfinite(cyclotron_n)
    assert cyclotron_n * wp2 == 0.0, "the numerator product collapses"
    assert _exact_product(cyclotron_n, wp2) > 0, "the exact numerator is non-zero"
    assert omega * denominator_n != 0j, (
        "the shared denominator stays representable, so this witness is the "
        "numerator route rather than the denominator route"
    )
    assert abs(omega * denominator_n) > SMALLEST_POSITIVE_SUBNORMAL
    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field_n, [collapsed_numerator],
            frequency_hz=REVIEW_COLLAPSED_PRODUCT_FREQUENCY_HZ,
        )
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_the_product_guard_is_exact_and_states_no_bound():
    """The guard's contract, measured at its own boundary rather than described.

    The review's requirement 3 asks for a check that fails closed on a zero or
    otherwise unrepresentable denominator product.  What makes that a
    representability check rather than a magnitude cutoff is that it tests exact
    zero and finiteness only: there is no tolerance, and no product that the
    double arithmetic forms as a non-zero value is rejected however small it is.

    Four claims, asserted on the module's own helper rather than through a
    scientific call, because this is a statement about the guard and not about the
    relation:

    * the smallest representable product is accepted -- ``1e-160`` squared is the
      subnormal ``1e-320``, near the floor of the double range, and it passes;
    * a genuine collapse is rejected: the smallest positive subnormal multiplied
      by itself has an exact product below half that subnormal, so it rounds to
      ``0.0`` while neither operand is zero;
    * a zero *operand* is accepted, because ``0 * x`` is zero by arithmetic and
      not by collapse.  That is a statement about this helper and not about the
      call: a contributing species whose field is non-zero and whose represented
      cyclotron term is zero is rejected before it reaches the helper, so the
      zero-cyclotron operand this branch accepts is the genuine zero-field one.
      The field and cyclotron regressions below measure the distinction on the
      call itself; and
    * a non-finite operand is rejected rather than silently accepted, which is
      the reason the operands are tested before the product: every comparison
      against a ``NaN`` is false, so a ``NaN`` operand would otherwise read as
      representable and the ``NaN`` would propagate into the tensor.
    """
    guard = _is_representable_product

    # Accepted: a product that is subnormal but representable, and the zero-operand
    # case, which is not a collapse.
    assert 1e-160 * 1e-160 == 1e-320
    assert guard(1e-160, 1e-160)
    assert guard(0.0, 1.0)
    assert guard(1.0, 0.0)
    assert guard(0.0, 0.0)

    # Rejected: two non-zero operands whose exact product rounds to zero.  The
    # exact product is below half the smallest positive subnormal, which is the
    # rounding boundary, so this is the smallest genuine collapse.
    assert SMALLEST_POSITIVE_SUBNORMAL * SMALLEST_POSITIVE_SUBNORMAL == 0.0
    assert _exact_product(
        SMALLEST_POSITIVE_SUBNORMAL, SMALLEST_POSITIVE_SUBNORMAL
    ) < Fraction(SMALLEST_POSITIVE_SUBNORMAL) / 2
    assert not guard(SMALLEST_POSITIVE_SUBNORMAL, SMALLEST_POSITIVE_SUBNORMAL)

    # Rejected: a non-finite operand, on either side.
    assert not guard(float("nan"), 1.0)
    assert not guard(1.0, float("nan"))
    assert not guard(float("inf"), 1.0)
    assert not guard(1.0, -float("inf"))

    # Accepted: a product that overflows to infinity, deliberately.  `inf` is a
    # representable zero divisor and `inf / inf` is a NaN the accumulation check
    # already rejects, so the field band from about 1e140 T is unaffected by this
    # guard; rejecting here instead would narrow the accepted set for no gain.
    assert 1e200 * 1e200 == float("inf")
    assert guard(1e200, 1e200)

    # The helper is a module-private predicate and not part of the public surface.
    assert "_is_representable_product" not in TARGET.__all__


# ---------------------------------------------------------------------------
# The guards fire nowhere on the swept ordinary range
# ---------------------------------------------------------------------------


def test_the_guards_fire_nowhere_on_the_swept_ordinary_range():
    """The corrections are guards, not reformulations: the ordinary range is untouched.

    This is the single maintained analogue of the seven per-revision sweeps the
    review ran, each of which compared one revision against its predecessor's arm
    over this same field/species battery and asserted ``checked > 1000``.  Those
    bit-identity comparisons are frozen in the snapshot and are not replayed here;
    what the maintained suite asserts is the property they were used to establish
    and which the current contract still rests on -- over the same battery, every
    accepted call is finite, and the guards reject only inputs outside the
    ordinary range.

    The battery is deliberately the sweep's own: 200 fields uniform in ``[-2, 2]``
    and 50 log-spaced fields over twelve decades, crossed with six species sets,
    skipping the fields whose norm is below ``1e-6``.  The accept count is
    asserted to exceed one thousand, as it was in each review sweep, so the
    battery really does exercise the ordinary range and the claim is not vacuous;
    and the reject count is asserted to be exactly zero, which is the claim
    itself -- this is the ordinary range, and the guards added for the four
    collapsed-intermediate counterexamples fire nowhere on it.  A guard that
    rejected anything here would be a magnitude cutoff rather than a
    representability check, and would fail this test rather than pass silently.
    """
    rng = np.random.default_rng(20260923)
    fields = list(rng.uniform(-2.0, 2.0, size=(200, 3)))
    fields.extend(
        10.0 ** rng.uniform(-12.0, 12.0, size=(50, 1)) * rng.normal(size=(50, 3))
    )
    species_sets = [
        [],
        [ELECTRON],
        [PROTON],
        [ELECTRON, PROTON],
        [dict(ELECTRON, collision_rate_s_inv=REVIEW_COLLISION_RATE)],
        [dict(ELECTRON, collision_rate_s_inv=1.0e15), PROTON],
    ]
    checked = 0
    rejected = []
    for field in fields:
        if float(np.linalg.norm(field)) < 1.0e-6:
            continue
        for species in species_sets:
            with np.errstate(invalid="ignore", over="ignore"):
                try:
                    ours = evaluate(TARGET, field, species)
                except (ColdPlasmaResonanceError, ColdPlasmaOverflowError) as raised:
                    rejected.append((field, species, type(raised).__name__))
                    continue
            assert np.all(np.isfinite(ours)), (field, species)
            checked += 1
    assert checked > 1000
    assert rejected == [], (
        "the guards must fire nowhere on the ordinary range; rejecting here would "
        "make them a magnitude cutoff rather than a representability check"
    )


# ---------------------------------------------------------------------------
# The relation, carried and re-asserted because the guards around it changed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("magnitude_t", [0.3, 12.0])
@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_collisionless_hermiticity_is_exact_at_nonzero_field(magnitude_t, sign):
    result = evaluate(TARGET, sign * magnitude_t * np.array([0.0, 0.0, 1.0]), [ELECTRON])
    assert deviation(result) == 0.0, (
        "collisionless Hermiticity is exact at any field strength; it is not a "
        "tolerance and it is not conditional on the field being zero"
    )
    assert result[0, 1].real == 0.0 and result[0, 1] == -result[1, 0]
    assert result[0, 1].imag != 0.0


def test_a_contributing_collision_breaks_hermiticity_with_the_review_deviation():
    result = evaluate(
        TARGET, FIELD, [dict(ELECTRON, collision_rate_s_inv=REVIEW_COLLISION_RATE)]
    )
    assert deviation(result) == REVIEW_COLLISIONAL_DEVIATION
    assert result[0, 1].real != 0.0 and result[1, 1].imag != 0.0


@pytest.mark.parametrize("zeroed", ["density_m3", "charge_c"])
def test_a_non_contributing_collision_does_not_break_hermiticity(zeroed):
    """The counterexample the review asked for and recorded that it did not have."""
    vacuum = evaluate(TARGET, FIELD, [])
    for collision_rate in (0.0, REVIEW_COLLISION_RATE, 1.0e15):
        result = evaluate(
            TARGET,
            FIELD,
            [dict(ELECTRON, collision_rate_s_inv=collision_rate, **{zeroed: 0.0})],
        )
        assert deviation(result) == 0.0
        assert np.array_equal(result, vacuum)


def test_zero_field_collapses_to_the_isotropic_tensor():
    result = evaluate(TARGET, np.zeros(3), [ELECTRON])
    plasma_term = 1.0 - (
        ELECTRON["density_m3"] * ELECTRON["charge_c"] ** 2
        / (VACUUM_PERMITTIVITY * ELECTRON["mass_kg"])
    ) / (OMEGA * OMEGA)
    assert_agrees(result, plasma_term * np.eye(3, dtype=complex))
    assert result[0, 1] == 0.0 and result[0, 2] == 0.0 and result[1, 2] == 0.0


@pytest.mark.parametrize("collision_rate", [0.0, REVIEW_COLLISION_RATE])
@pytest.mark.parametrize("field_z_t", [0.3, -0.25])
def test_the_conductivity_formulation_is_recovered_only_with_the_signed_projection(
    collision_rate, field_z_t
):
    """The equivalence is a sign convention, and it is re-derived here.

    The review established two things against the retained conductivity route:
    that ``epsilon_r = I + i*sigma/(eps0*omega)`` holds to machine precision at
    *both* field signs and at every collision rate measured, and that the scalar
    cyclotron argument the route is handed carries the **signed** projection
    ``q B_z / m`` rather than the magnitude ``q |B_z| / m`` -- passing the
    magnitude instead is the review's measured ``1.7e-2`` relative error, so the
    equivalence is a convention about the argument and not an identity of
    magnitudes.

    The retained route is a source-project artifact that is not reachable from the
    maintained baseline, so its closed form is not loaded here.  What is
    re-derived is the relation the module itself implements, under the two
    readings of the argument:

    * under the module's own reading -- the field *magnitude* ``q |B| / m`` -- the
      body-local assembly agrees with the module to the asserted few-ulp bound, at
      both signs of the axial field and at both collision rates.  That is the
      machine-precision half of the review's claim, and it is what makes the
      relation an equivalence of formulations rather than a coincidence at one
      field;
    * under the *signed projection* ``q B_z / m`` it does not, when the axial field
      is negative: the relative deviation is the review's measured ``1.7e-2`` band.
      For a *positive* axial field the two readings are the same number, so a
      positive field alone cannot discriminate between them, which is why both
      signs are swept here.

    The retained route's own reconstruction carries the opposite off-diagonal
    handedness from this module's ``i D [b]_x``, which is why handing it the
    signed projection lands on the same tensor that the module builds from the
    magnitude.  That folding is the sign convention; the two readings' disagreement
    in isolation is what the second half measures, and it is asserted so that a
    later edit cannot quietly replace one reading with the other and still pass.
    """
    field = np.array([0.0, 0.0, field_z_t])
    species = [dict(ELECTRON, collision_rate_s_inv=collision_rate)]
    tensor = evaluate(TARGET, field, species)

    magnitude_reading = assemble_with_cyclotron_reading(
        field, species, signed_axial=False
    )
    assert_agrees(tensor, magnitude_reading)

    signed_reading = assemble_with_cyclotron_reading(field, species, signed_axial=True)
    if field_z_t > 0.0:
        # The two readings coincide, so this field cannot discriminate.
        assert np.array_equal(magnitude_reading, signed_reading)
        assert_agrees(tensor, signed_reading)
    else:
        relative = float(np.max(np.abs(tensor - signed_reading))) / float(
            np.max(np.abs(tensor))
        )
        assert 0.01 < relative < 0.03, (
            "the signed projection read as the module's own argument is the "
            "review's measured 1.7e-2 relative deviation, not a rounding "
            "difference"
        )
        assert not np.allclose(tensor, signed_reading, rtol=1.0e-3, atol=0.0)


def test_a_grid_and_a_pointwise_call_agree_within_one_ulp():
    """Inherited: the same field as a vector and as a grid row differ by about one ulp.

    The bound is asserted in the tests and is inherited from the retained route
    rather than introduced here; the review's evidence that a predecessor carried
    the same artefact is frozen in the snapshot and is not replayed.
    """
    fields = np.array([[0.0, 0.0, 0.3], [0.1, -0.2, 0.7]])
    grid = evaluate(TARGET, fields, [ELECTRON])
    for index, field in enumerate(fields):
        assert_agrees(grid[index], evaluate(TARGET, field, [ELECTRON]))
    # The artefact is real rather than masked by the bound: row 0 of the grid and
    # the same field passed pointwise are not bit-identical.
    assert not np.array_equal(grid[0], evaluate(TARGET, fields[0], [ELECTRON]))


def test_the_input_contract_is_enforced():
    """Representative cases only; the review's full validation matrix is frozen."""
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError, match="positive finite frequency"):
            evaluate(TARGET, FIELD, [ELECTRON], frequency_hz=bad)
    with pytest.raises(ValueError, match="magnetic field"):
        evaluate(TARGET, np.zeros(2), [ELECTRON])
    with pytest.raises(ValueError, match="magnetic field"):
        evaluate(TARGET, np.array([0.0, 0.0, float("nan")]), [ELECTRON])
    with pytest.raises(ValueError, match="mapping"):
        evaluate(TARGET, FIELD, [("electron", 1.0e19)])
    with pytest.raises(ValueError, match="collision_hz is ambiguous"):
        evaluate(TARGET, FIELD, [dict(ELECTRON, collision_hz=1.0e6)])
    with pytest.raises(ValueError, match="species values must be finite"):
        evaluate(TARGET, FIELD, [dict(ELECTRON, density_m3=-1.0)])


# ---------------------------------------------------------------------------
# Correction 11 (V11) -- a non-zero field cannot present as a zero cyclotron
# term, on either of the two routes that produce one
# ---------------------------------------------------------------------------

# The V10 expert review's own counterexample.  Every value is finite, so the
# declared input contract accepts it, and every one is non-zero, so the species
# is not inert.  Every earlier guard passes: the numerator, the divisor, the
# quotient, the shifted frequency, the Stix denominator and all four products the
# divisions consume are representable and non-zero.  The field magnitude is
# exactly 1e-150 T, not zero.  What collapses is the cyclotron term: `q |B| / m`
# is `1e-350`, below the smallest positive subnormal double, so the represented
# term is `0.0` and a predecessor read it as the legitimate zero-field operand.
REVIEW_CYCLOTRON_UNDERFLOW_FREQUENCY_HZ = 1e-100 / (2.0 * math.pi)
REVIEW_CYCLOTRON_UNDERFLOW_FIELD = [0.0, 0.0, 1e-150]
REVIEW_CYCLOTRON_UNDERFLOW = {
    "density_m3": 1e308,
    "charge_c": 1e-200,
    "mass_kg": 1.0,
    "collision_rate_s_inv": 0.0,
}

# The review's published exact `D`, reproduced below from exact rational
# arithmetic over the same represented doubles -- with the cyclotron term formed
# exactly rather than read from the rounded `0.0`.  Nothing in the module computes
# it; it is quoted to establish that the dropped contribution is an ordinary
# representable double and not a mathematical zero.
REVIEW_CYCLOTRON_UNDERFLOW_HIGH_PRECISION_D = 1.129409067373019e-131

# The field-magnitude route.  `np.linalg.norm` squares before it sums, so a field
# whose only non-zero component is subnormal has every square underflow and is
# represented as the zero field -- while the exact norm of that same double is
# itself a representable double.
REVIEW_NORM_COLLAPSE_FIELD = [5e-324, 0.0, 0.0]
REVIEW_NORM_COLLAPSE_SPECIES = {
    "density_m3": 1.0,
    "charge_c": 1.0,
    "mass_kg": 1.0,
    "collision_rate_s_inv": 0.0,
}


def test_the_cyclotron_underflow_witness_is_rejected_rather_than_zeroing_d():
    """The defect closed, on the expert review's own counterexample.

    Six things are asserted separately, because they fail for different reasons:
    every earlier guard really does pass, so the call really does reach the
    accumulation; the field magnitude, the density, the charge and the mass really
    are non-zero, so this is not the legitimate zero-field point; the represented
    cyclotron term really does collapse to exactly zero; the exact cyclotron term
    over the same represented doubles is non-zero, so the collapse is a
    representability failure rather than a mathematical zero; the exact ``D`` is an
    ordinary representable double, so the collapsed operand stood for a real
    scientific contribution; and the rejection is the *named* class, whole-call,
    with the offending species named.  The predecessor's finite tensor with the
    zeroed off-diagonal entries is frozen in the snapshot and is not replayed
    here.
    """
    species = [dict(REVIEW_CYCLOTRON_UNDERFLOW)]
    field = np.array(REVIEW_CYCLOTRON_UNDERFLOW_FIELD)

    # The guards the earlier revision carried, re-measured here rather than taken
    # on trust.  Each one is a representable non-zero double, which is why the call
    # reached the accumulation instead of failing closed.
    numerator = (
        REVIEW_CYCLOTRON_UNDERFLOW["density_m3"]
        * REVIEW_CYCLOTRON_UNDERFLOW["charge_c"]
        * REVIEW_CYCLOTRON_UNDERFLOW["charge_c"]
    )
    divisor = VACUUM_PERMITTIVITY * REVIEW_CYCLOTRON_UNDERFLOW["mass_kg"]
    omega = 2.0 * math.pi * REVIEW_CYCLOTRON_UNDERFLOW_FREQUENCY_HZ
    magnitude = float(np.linalg.norm(field))
    charge = REVIEW_CYCLOTRON_UNDERFLOW["charge_c"]
    mass = REVIEW_CYCLOTRON_UNDERFLOW["mass_kg"]
    wp2 = numerator / divisor
    cyclotron = charge * magnitude / mass
    shifted = omega + 0j
    denominator = shifted * shifted - cyclotron * cyclotron
    for label, value in (
        ("numerator", numerator),
        ("divisor", divisor),
        ("omega", omega),
        ("wp2", wp2),
        ("shifted", shifted),
        ("denominator", denominator),
        ("omega*denominator", omega * denominator),
        ("wp2*shifted", wp2 * shifted),
        ("omega*shifted", omega * shifted),
    ):
        assert value != 0 and np.all(np.isfinite(value)), label

    # The field is not zero and the species is not inert.  Stated first so no
    # later assertion can be read as the legitimate zero-field case.
    assert magnitude == 1e-150 and magnitude != 0.0, "the field magnitude is not zero"
    assert charge != 0.0 and mass > 0.0
    assert numerator != 0.0 and wp2 != 0.0
    assert abs(denominator) != 0.0

    # The failure.  Both operands of `q |B| / m` are non-zero and finite, and the
    # represented quotient is exactly zero because the exact one is below the
    # double range.
    exact_cyclotron = _exact_cyclotron(charge, magnitude, mass)
    assert exact_cyclotron != 0, "the exact cyclotron term is non-zero"
    assert float(exact_cyclotron) == 0.0, "the exact cyclotron term is below the double range"
    assert cyclotron == 0.0, "the represented cyclotron term collapses to zero"

    # The contribution the collapse discarded is an ordinary representable double,
    # so reading the zero operand as the zero-field case drops a real term.
    exact_d = exact_cyclotron * Fraction(wp2) / (Fraction(omega) * Fraction(denominator.real))
    assert exact_d != 0, "the exact D is non-zero"
    assert float(exact_d) > SMALLEST_POSITIVE_SUBNORMAL, (
        "the lost D contribution is representable; treating the collapsed "
        "cyclotron term as the zero-field case drops an ordinary number"
    )
    assert abs(float(exact_d) - REVIEW_CYCLOTRON_UNDERFLOW_HIGH_PRECISION_D) <= (
        math.ulp(REVIEW_CYCLOTRON_UNDERFLOW_HIGH_PRECISION_D)
    ), (
        "the review's published high-precision D agrees with this file's exact "
        "rational evaluation over the same represented doubles to one ulp.  The "
        "bound is stated rather than an equality, because the two are reached by "
        "different rounding paths -- the review evaluated the quotient in high "
        "precision, this file forms the cyclotron term exactly and then divides -- "
        "and an equality is not what either measurement claims."
    )

    # `D` enters the tensor as `i D [b]_x`, so with the field along z the
    # off-diagonal entries carry `-i D` and `+i D`.  That is the entry the
    # predecessor zeroed.
    expected_d_entry = -1j * float(exact_d)
    assert expected_d_entry != 0.0j and abs(expected_d_entry) == float(exact_d)

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(
            TARGET, field, species,
            frequency_hz=REVIEW_CYCLOTRON_UNDERFLOW_FREQUENCY_HZ,
        )
    assert type(raised.value) is ColdPlasmaOverflowError
    assert isinstance(raised.value, ValueError)
    assert not isinstance(raised.value, ZeroDivisionError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_a_genuine_zero_field_cyclotron_is_still_accepted():
    """The correction distinguishes the two cases; it does not reject zero fields.

    The review's requirement 3: preserve evaluation of the genuine zero-field
    point.  The counterexample above and this call carry the *same* species -- the
    same density, the same charge, the same mass and the same collision rate -- and
    differ only in the field.  Both have a represented cyclotron term of exactly
    ``0.0``; the first is rejected and this one is evaluated, so what the guard
    keys on is the field and not the cyclotron term alone.

    The zero-field tensor is then the isotropic plasma tensor, and the off-diagonal
    term is exactly zero -- not because a contribution was dropped, but because
    ``[b]_x`` vanishes when there is no field direction.
    """
    species = [dict(REVIEW_CYCLOTRON_UNDERFLOW)]
    zero_field = np.zeros(3)
    magnitude = float(np.linalg.norm(zero_field))
    assert magnitude == 0.0
    assert species[0]["charge_c"] != 0.0 and species[0]["mass_kg"] > 0.0

    result = evaluate(
        TARGET, zero_field, species,
        frequency_hz=REVIEW_CYCLOTRON_UNDERFLOW_FREQUENCY_HZ,
    )
    assert np.all(np.isfinite(result))
    assert result[0, 1] == 0.0 and result[1, 0] == 0.0
    assert result[0, 2] == 0.0 and result[2, 0] == 0.0
    assert result[1, 2] == 0.0 and result[2, 1] == 0.0

    # And the counterexample's own field is rejected, so the two calls are
    # distinguished by the field and by nothing else.
    with pytest.raises(ColdPlasmaOverflowError):
        evaluate(
            TARGET, np.array(REVIEW_CYCLOTRON_UNDERFLOW_FIELD), species,
            frequency_hz=REVIEW_CYCLOTRON_UNDERFLOW_FREQUENCY_HZ,
        )


def test_the_field_magnitude_route_is_rejected_rather_than_classified_as_zero():
    """The review's requirement 4: the immediately upstream field route.

    ``np.linalg.norm`` squares before it sums, so ``[5e-324, 0, 0]`` T -- a field
    that is not the zero field -- has its only square underflow to exactly zero and
    is represented as the zero field.  A predecessor then formed ``q |B| / m``
    against a magnitude of ``0.0`` and classified the call as a zero-field point,
    answering with exactly its answer for the genuine zero field, which is what
    made the misclassification silent.

    Four things are asserted separately: the represented field is non-zero and its
    represented norm is exactly zero; the exact norm of that same double is itself
    a representable double, so the classification is an arithmetic collapse and not
    a mathematical zero; the call is rejected rather than classified; and the
    genuine zero field is still evaluated, so the rejection is not a blanket
    refusal of zero cyclotron terms.  The predecessor's zero-field answer is frozen
    in the snapshot and is not replayed here.
    """
    field = np.array(REVIEW_NORM_COLLAPSE_FIELD)
    species = [dict(REVIEW_NORM_COLLAPSE_SPECIES)]

    component = REVIEW_NORM_COLLAPSE_FIELD[0]
    assert component != 0.0, "the field is not the zero field"
    assert component * component == 0.0, "every square of the field underflows"
    assert float(np.linalg.norm(field)) == 0.0, "the represented norm is exactly zero"
    assert float(Fraction(component)) == component, (
        "the exact norm of that component is itself a representable double"
    )
    assert float(Fraction(component)) >= SMALLEST_POSITIVE_SUBNORMAL

    # The genuine zero field with the same species is evaluated, not rejected.
    vacuum = evaluate(TARGET, np.zeros(3), species, frequency_hz=1.0)
    assert np.all(np.isfinite(vacuum))
    assert vacuum[0, 1] == 0.0 and vacuum[1, 0] == 0.0

    with pytest.raises(ColdPlasmaOverflowError) as raised:
        evaluate(TARGET, field, species, frequency_hz=1.0)
    assert type(raised.value) is ColdPlasmaOverflowError
    assert not isinstance(raised.value, ZeroDivisionError)
    assert str(raised.value).startswith(OVERFLOW_MESSAGE)
    assert "species index 0" in str(raised.value)


def test_a_declared_inert_species_does_not_reject_a_collapsed_field():
    """The guards come after the inert skip, so a species that moves nothing is skipped.

    A caller-declared inert species uses neither the field nor the cyclotron
    term, so a field the norm collapses must not reject a call the species cannot
    move.  The skip is still decided on the caller's two inputs.
    """
    field = np.array(REVIEW_NORM_COLLAPSE_FIELD)
    vacuum = evaluate(TARGET, np.zeros(3), [])
    for zeroed in ("density_m3", "charge_c"):
        inert = dict(REVIEW_NORM_COLLAPSE_SPECIES, **{zeroed: 0.0})
        assert np.array_equal(
            evaluate(TARGET, field, [inert]), vacuum
        ), zeroed
        assert np.array_equal(
            evaluate(TARGET, np.zeros(3), [inert]), vacuum
        ), zeroed


def test_the_field_and_cyclotron_guards_state_no_bound():
    """The guards are exact and state no magnitude cutoff.

    Three claims, asserted on ordinary calls rather than through the private
    helpers, because this is a statement about the accepted set and not about a
    predicate:

    * a small but representable field is accepted, and its cyclotron term is a
      representable non-zero double -- so the guard is not a magnitude cutoff;
    * the field magnitude boundary the *existing* overflow guard measures is
      unchanged: ``1e142 T`` is accepted and ``1e143 T`` is rejected, because
      the cyclotron square overflows there; and
    * a zero-field call and an ordinary call are both accepted, so the guards
      fire on neither.
    """
    tiny = 1.0e-6 * np.array([0.0, 0.0, 1.0])
    cyclotron = ELECTRON["charge_c"] * float(np.linalg.norm(tiny)) / ELECTRON["mass_kg"]
    assert cyclotron != 0.0 and math.isfinite(cyclotron)
    assert np.all(np.isfinite(evaluate(TARGET, tiny, [ELECTRON])))

    assert np.all(np.isfinite(evaluate(TARGET, 1.0e142 * np.array([0.0, 0.0, 1.0]), [ELECTRON])))
    with pytest.raises(ColdPlasmaOverflowError):
        with np.errstate(invalid="ignore", over="ignore"):
            evaluate(TARGET, 1.0e143 * np.array([0.0, 0.0, 1.0]), [ELECTRON])

    assert np.all(np.isfinite(evaluate(TARGET, np.zeros(3), [ELECTRON])))
    assert np.all(np.isfinite(evaluate(TARGET, FIELD, [ELECTRON])))
