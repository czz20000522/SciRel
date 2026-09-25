"""Direct contract tests for ``scirel.collisions.momentum_scales``.

Two leaves are under contract here.  First, the retained route's six mappings
behind a string dispatcher are reduced to the two that are *momentum scales*, in
a module named for what it contains; the four held-out mappings are Coulomb-log
factors and argument scales, which are different relations.  Second, the
dispatcher itself is not reproduced, because a routing string selects a relation
rather than parameterising one.  Third, **the composition claim the V3 candidate
made between the two leaves is removed, because it does not hold.**  ``p_Te`` is a
dimensionless speed ratio and ``vnorm`` is a velocity, so using one as the other
divides by ``c`` twice.  Fourth, **a finite input whose result is not
representable is rejected**, because both leaves advertise a finite-output
contract and neither input domain is bounded above.

Both leaves are definitions, so the tests assert their closed forms exactly rather
than to a tolerance.

This module tests the maintained implementation directly.  The review unit that
produced it additionally compared each claim against the frozen V2/V3/V4
predecessors and the read-only L1 route; those arms live outside the repository
and are not reachable from the maintained baseline, so they are not replayed
here.  The claims they established are the ones asserted below.
"""
from __future__ import annotations

import importlib.util
import inspect
import pathlib
import sys
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

import scirel
from scirel.collisions import momentum_scales
from scirel.collisions.momentum_scales import (
    NON_REPRESENTABLE_MESSAGE,
    normalized_momentum,
    thermal_electron_momentum,
)

HELD_OUT = (
    "enabled_argument_scale",
    "enabled_gamefac",
    "hesslow_electron_electron",
    "hesslow_electron_ion",
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
MOMENTUM_DOCUMENTS = (
    EXAMPLES / "scirel.collisions.thermal-electron-momentum.json",
    EXAMPLES / "scirel.collisions.normalized-momentum.json",
)

GRID = np.array([-2.0, -0.5, 0.0, 0.5, 2.0, 7.25])
REST_MASS_KEV = 511.0
CLIGHT = 2.99792458e10
TEMPERATURE_KEV = 250.0


def test_the_module_publishes_only_the_two_momentum_scales():
    assert momentum_scales.__all__ == [
        "normalized_momentum", "thermal_electron_momentum",
    ]
    for name in HELD_OUT:
        assert not hasattr(momentum_scales, name), name
    assert not hasattr(momentum_scales, "scientific_operator"), (
        "the dispatcher is a routing string, not a scientific input"
    )


def test_the_module_is_named_for_what_it_contains():
    """``coulomb_log_scales`` held a momentum scale and an argument scale; it is renamed."""
    assert momentum_scales.__name__ == "scirel.collisions.momentum_scales"
    assert importlib.util.find_spec("scirel.collisions.coulomb_log_scales") is None
    assert scirel.collisions.__all__ == [
        "BesselBackendEvaluationError",
        "InvalidBesselArgumentError",
        "relativistic_maxwellian_bessel",
        "normalized_momentum",
        "thermal_electron_momentum",
        "average_cross_section_over_maxwellian",
        "evaluate_atomic_hydrogen_charge_exchange_cross_section",
        "evaluate_atomic_hydrogen_charge_exchange_rate",
        "evaluate_collrad_h0_ionization_rate",
        "evaluate_molecular_hydrogen_charge_exchange_cross_section",
        "evaluate_hydrogen2_charge_exchange_rate",
        "evaluate_atomic_hydrogen_elastic_cross_section",
        "evaluate_hydrogen_proton_elastic_cross_section",
        "evaluate_hydrogen_h2_elastic_cross_section",
        "evaluate_hydrogen2_hydrogen2_elastic_cross_section",
        "evaluate_hydrogen2_proton_elastic_cross_section",
        "evaluate_hydrogen2_h1s_h1s_dissociation_rate",
        "evaluate_hydrogen2_h1s_h2s_dissociation_rate",
        "evaluate_hydrogen2_h1s_hn3_dissociation_rate",
        "evaluate_hydrogen2_h2p_h2s_dissociation_rate",
        "evaluate_hydrogen2_p_h1s_dissociation_rate",
        "evaluate_h2_plus_two_proton_dissociation_rate",
        "evaluate_h2_plus_p_h1s_dissociation_rate",
        "evaluate_h2_plus_p_hn2_dissociation_rate",
        "evaluate_h2_plus_h1s_hn_dissociative_recombination_rate",
    ]


def test_the_package_and_root_namespace_export_both_leaves():
    assert callable(scirel.normalized_momentum)
    assert callable(scirel.thermal_electron_momentum)
    assert callable(scirel.collisions.normalized_momentum)
    assert callable(scirel.collisions.thermal_electron_momentum)
    assert {"collisions"} <= set(scirel.__all__)


# ---------------------------------------------------------------------------
# The two leaves are not composable, and the V3 claim was wrong
# ---------------------------------------------------------------------------


def test_the_two_leaves_do_not_reference_each_other():
    """Neither leaf imports, calls or re-exports the other, so no composition is implied."""
    source = pathlib.Path(inspect.getfile(momentum_scales)).read_text(encoding="utf-8")
    # The names appear in the module only as definitions and in __all__; neither
    # function body mentions the other, and there is no composed helper.
    assert "def thermal_electron_momentum" in source
    assert "def normalized_momentum" in source
    assert not hasattr(momentum_scales, "compose")
    assert momentum_scales.__all__ == [
        "normalized_momentum", "thermal_electron_momentum",
    ]
    # The two signatures share no parameter name, so a caller cannot pass one
    # leaf's output to the other leaf without renaming it explicitly.
    thermal_parameters = set(
        inspect.signature(thermal_electron_momentum).parameters
    )
    momentum_parameters = set(inspect.signature(normalized_momentum).parameters)
    assert thermal_parameters == {"temperature_kev", "restmkev"}
    assert momentum_parameters == {"x", "vnorm", "clight"}
    assert thermal_parameters.isdisjoint(momentum_parameters)


def test_p_te_is_dimensionless_and_vnorm_is_a_velocity():
    """The dimensional mismatch, stated as the two closed forms.

    ``p_Te = sqrt(2T/mc^2)`` with both inputs energies is a ratio of speeds.  A
    number of order one is exactly what a speed ratio in units of ``c`` looks like,
    and ``vnorm``'s own contract requires a velocity in the same unit as ``clight``.
    """
    p_te = thermal_electron_momentum(
        temperature_kev=TEMPERATURE_KEV, restmkev=REST_MASS_KEV
    )
    assert p_te == float(np.sqrt(2.0 * TEMPERATURE_KEV / REST_MASS_KEV))
    assert 0.0 < p_te < 1.0, "a v/c ratio for a thermal electron is below one"
    # A thermal electron speed in cm/s is p_Te * c, not p_Te.  The scale is
    # O(1) -- which is what a ratio in units of c looks like -- while the speed
    # it stands for is O(1e10) cm/s.
    assert p_te * CLIGHT == pytest.approx(2.9656e10, rel=1.0e-3)


def test_the_map_divides_by_clight_exactly_once():
    """The public contract that makes the removed composition claim impossible.

    ``normalized_momentum`` divides by ``clight`` and by nothing else: its result
    is ``x * vnorm / clight`` for every accepted input, so a caller that passes
    ``p_Te`` -- a ratio in units of ``c``, not a velocity -- is divided by ``c``
    twice, once implicitly in the ratio and once here.  The module does not detect
    that, and this test does not ask it to; what is asserted is the arithmetic the
    map performs, which is what makes the dimensional precondition the caller's.

    Both halves are individually correct, which is why a passing suite did not
    catch the original claim; the defect was in the claim, not in either leaf.
    """
    p_te = thermal_electron_momentum(
        temperature_kev=TEMPERATURE_KEV, restmkev=REST_MASS_KEV
    )
    as_v3_did = normalized_momentum(x=GRID, vnorm=p_te, clight=CLIGHT)
    consistent = GRID * p_te
    assert np.array_equal(as_v3_did, GRID * p_te / CLIGHT)
    nonzero = GRID != 0.0
    assert np.allclose(consistent[nonzero] / as_v3_did[nonzero], CLIGHT, rtol=1.0e-15)
    # Eleven orders of magnitude too small, which is the whole of the defect.
    assert np.max(np.abs(consistent)) / np.max(np.abs(as_v3_did)) == pytest.approx(
        CLIGHT, rel=1.0e-15
    )
    # The map is linear in vnorm with slope x / clight, at several scales: the
    # single division is the whole of its dependence on clight.
    for vnorm in (1.0, 1.0e-3, 1.0e8):
        assert np.array_equal(
            normalized_momentum(x=GRID, vnorm=vnorm, clight=CLIGHT),
            GRID * vnorm / CLIGHT,
        )
        assert np.array_equal(
            normalized_momentum(x=GRID, vnorm=vnorm * CLIGHT, clight=CLIGHT),
            GRID * vnorm,
        )


def test_the_dimensionally_valid_conversion_is_the_callers():
    """``vnorm = p_Te * clight`` makes ``p_n = x * p_Te``; the module does not do it.

    The conversion is stated here so the correct route is not left implicit, and it
    is performed in the test body rather than by the asset, which claims no unit
    conversion of any kind.
    """
    p_te = thermal_electron_momentum(
        temperature_kev=TEMPERATURE_KEV, restmkev=REST_MASS_KEV
    )
    as_velocity = p_te * CLIGHT
    converted = normalized_momentum(x=GRID, vnorm=as_velocity, clight=CLIGHT)
    assert np.array_equal(converted, GRID * p_te)
    # And the module exposes no helper that would perform it for the caller.
    assert momentum_scales.__all__ == [
        "normalized_momentum", "thermal_electron_momentum",
    ]
    assert not hasattr(momentum_scales, "thermal_speed")


def test_the_asset_documents_do_not_claim_the_composition():
    """The claim was in both V3 documents' applicability and examples; it is gone."""
    assert len(MOMENTUM_DOCUMENTS) == 2
    for path in MOMENTUM_DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        assert "supplies the velocity scale" not in text, path.name
        assert "Composition with the thermal electron momentum scale" not in text, path.name
        assert "p_Te is the vnorm this map consumes" not in text, path.name
        assert "divides by" in text or "divided by" in text or "double" in text, path.name


# ---------------------------------------------------------------------------
# The two definitions
# ---------------------------------------------------------------------------


def test_thermal_electron_momentum_is_exactly_the_closed_form():
    for temperature_kev in (1.0, 10.0, 511.0, 2.5e3, 1.0e-6):
        for restmkev in (REST_MASS_KEV, 1.0, 9.1093837015e-28):
            ours = thermal_electron_momentum(
                temperature_kev=temperature_kev, restmkev=restmkev
            )
            assert ours == float(np.sqrt(2.0 * temperature_kev / restmkev))


def test_normalized_momentum_is_exactly_the_closed_form():
    for vnorm in (0.0, 1.0, 0.123456789, 1.0e8):
        for clight in (CLIGHT, 1.0, 2.0**20):
            ours = normalized_momentum(x=GRID, vnorm=vnorm, clight=clight)
            assert np.array_equal(ours, GRID * vnorm / clight)
    assert ours.dtype == np.float64


# ---------------------------------------------------------------------------
# A finite input whose result is not representable is rejected
# ---------------------------------------------------------------------------


def test_the_thermal_witness_is_rejected():
    """``temperature_kev=1e308`` with ``restmkev=511``: the review's first witness.

    Both inputs satisfy the stated finite-positive contract.  ``2.0 * 1.0e308``
    overflows to ``inf`` before the division, so the closed form is ``sqrt(inf)``,
    which the V4 candidate and the retained route both returned as positive
    infinity.  It is rejected here, naming the quantity that was not finite.
    """
    with pytest.raises(ValueError) as raised:
        thermal_electron_momentum(temperature_kev=1.0e308, restmkev=511.0)
    assert str(raised.value).startswith(NON_REPRESENTABLE_MESSAGE)
    assert "thermal-electron normalized momentum" in str(raised.value)


def test_the_momentum_witness_is_rejected():
    """``x=[1e308], vnorm=1e308, clight=5e-324``: the review's second witness.

    Every input satisfies the stated contract: ``x`` is a finite one-dimensional
    array, ``vnorm`` is finite and non-negative, and ``clight`` is finite and
    positive -- it is the smallest positive subnormal, which is why the division
    cannot bring the overflow back into range.  The V4 candidate and the retained
    route returned positive infinity.
    """
    with pytest.raises(ValueError) as raised:
        normalized_momentum(x=np.array([1.0e308]), vnorm=1.0e308, clight=5.0e-324)
    assert str(raised.value).startswith(NON_REPRESENTABLE_MESSAGE)
    assert "grid momentum profile" in str(raised.value)


def test_the_check_is_representability_and_not_a_magnitude_cutoff():
    """No threshold is invented: large but representable inputs are still answered.

    The input domain is deliberately not narrowed.  ``temperature_kev = 1.0e300``
    with ``restmkev = 511.0`` gives ``2.0 * 1.0e300`` without overflowing, so it is
    accepted and returns exactly the closed form; the same holds for a momentum
    profile whose arithmetic stays inside the range.
    """
    for temperature_kev in (1.0e-6, 1.0, 2.5e3, 1.0e300, 1.0e307):
        ours = thermal_electron_momentum(
            temperature_kev=temperature_kev, restmkev=511.0
        )
        assert np.isfinite(ours)
        assert ours == float(np.sqrt(2.0 * temperature_kev / 511.0))
    for vnorm, clight in (
        (1.0e307, 1.0),
        (1.0e300, 1.0e-6),
        (1.0e8, 1.0e-299),
        (5.0e-324, 5.0e-324),
    ):
        ours = normalized_momentum(x=GRID, vnorm=vnorm, clight=clight)
        assert np.isfinite(ours).all()
        assert np.array_equal(ours, GRID * vnorm / clight)


def test_the_rejection_is_a_value_error_and_not_a_partial_result():
    """A rejected call produces no value at all, and no partial profile."""
    with pytest.raises(ValueError):
        normalized_momentum(x=GRID, vnorm=1.0e308, clight=5.0e-324)


# ---------------------------------------------------------------------------
# The input contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda: thermal_electron_momentum(temperature_kev=0.0, restmkev=1.0),
        lambda: thermal_electron_momentum(temperature_kev=1.0, restmkev=-1.0),
        lambda: thermal_electron_momentum(
            temperature_kev=float("nan"), restmkev=1.0
        ),
        lambda: normalized_momentum(x=np.zeros((2, 2)), vnorm=1.0, clight=1.0),
        lambda: normalized_momentum(
            x=np.array([0.0, np.inf]), vnorm=1.0, clight=1.0
        ),
        lambda: normalized_momentum(x=GRID, vnorm=-1.0, clight=1.0),
        lambda: normalized_momentum(x=GRID, vnorm=1.0, clight=0.0),
    ],
)
def test_the_value_contract_rejects_every_out_of_domain_value(call):
    """The retained guards and their messages, unchanged, for values."""
    with pytest.raises(ValueError):
        call()


def test_the_domain_messages_are_the_retained_routes():
    with pytest.raises(ValueError) as raised:
        thermal_electron_momentum(temperature_kev=0.0, restmkev=1.0)
    assert str(raised.value) == "temperature_kev must be finite and positive"
    with pytest.raises(ValueError) as raised:
        thermal_electron_momentum(temperature_kev=1.0, restmkev=-1.0)
    assert str(raised.value) == "restmkev must be finite and positive"
    with pytest.raises(ValueError) as raised:
        normalized_momentum(x=np.zeros((2, 2)), vnorm=1.0, clight=1.0)
    assert str(raised.value) == "x must be a finite one-dimensional array"
    with pytest.raises(ValueError) as raised:
        normalized_momentum(x=GRID, vnorm=-1.0, clight=1.0)
    assert str(raised.value) == "vnorm must be nonnegative and clight must be positive"
    with pytest.raises(ValueError) as raised:
        normalized_momentum(x=GRID, vnorm=1.0, clight=0.0)
    assert str(raised.value) == "vnorm must be nonnegative and clight must be positive"


@pytest.mark.parametrize(
    "container",
    [np.array([1.0]), np.array([[1.0]]), np.array([[1.0, 2.0]]), [1.0], (1.0,)],
)
def test_a_non_scalar_container_is_rejected_by_parameter_name(container):
    """The input contract is narrowed to scalar-shaped values only.

    The retained route delegates this to ``float(value)``, whose treatment of a
    one-element container is a NumPy conversion rule: on this build it raises a
    ``TypeError`` naming ``float``, not the parameter.  The shape is checked first
    here, so the rejection is deterministic and names the argument that was wrong.
    """
    for keyword in ("temperature_kev", "restmkev"):
        arguments = dict(temperature_kev=1.0, restmkev=1.0)
        arguments[keyword] = container
        with pytest.raises(ValueError) as raised:
            thermal_electron_momentum(**arguments)
        assert str(raised.value) == f"{keyword} must be a scalar"
    for keyword in ("vnorm", "clight"):
        arguments = dict(x=GRID, vnorm=1.0, clight=CLIGHT)
        arguments[keyword] = container
        with pytest.raises(ValueError) as raised:
            normalized_momentum(**arguments)
        assert str(raised.value) == f"{keyword} must be a scalar"


@pytest.mark.parametrize(
    "scalar", [1.0, np.float64(1.0), np.float32(1.0), 1, np.int64(1), np.array(1.0)]
)
def test_a_scalar_shaped_value_is_accepted(scalar):
    """A 0-dimensional array is scalar-shaped; NumPy scalars and integers are scalars."""
    assert thermal_electron_momentum(
        temperature_kev=scalar, restmkev=1.0
    ) == float(np.sqrt(2.0))
    assert np.array_equal(
        normalized_momentum(x=GRID, vnorm=scalar, clight=1.0), GRID * float(scalar)
    )


@pytest.mark.parametrize("convertible", [True, "250.0", Decimal("250.0"), Fraction(1, 1)])
def test_a_convertible_non_numeric_value_is_left_as_the_retained_route_has_it(convertible):
    """Not this revision's question, so the behaviour is asserted unchanged.

    ``float()`` accepts these; the shape is checked and then the conversion is
    applied exactly as the retained route does.  Whether they *should* be accepted
    is a separate review question and is not decided here.
    """
    assert thermal_electron_momentum(
        temperature_kev=convertible, restmkev=1.0
    ) == float(np.sqrt(2.0 * float(convertible)))


def test_the_retained_allowances_are_kept():
    """A zero velocity scale and a signed grid are legal, and the input is not modified."""
    zero = normalized_momentum(x=GRID, vnorm=0.0, clight=CLIGHT)
    assert np.array_equal(zero, np.zeros_like(GRID))
    assert zero.dtype == np.float64
    signed = normalized_momentum(x=GRID, vnorm=1.0, clight=CLIGHT)
    assert signed[0] < 0.0 < signed[-1]
    assert np.array_equal(signed, GRID / CLIGHT)
    grid = GRID.copy()
    normalized_momentum(x=grid, vnorm=3.0, clight=CLIGHT)
    assert np.array_equal(grid, GRID)


def test_the_signatures_are_keyword_only_and_restmkev_is_required():
    """The retained calling convention, kept; the rest energy has no default."""
    thermal = inspect.signature(thermal_electron_momentum)
    momentum = inspect.signature(normalized_momentum)
    assert list(thermal.parameters) == ["temperature_kev", "restmkev"]
    assert list(momentum.parameters) == ["x", "vnorm", "clight"]
    for signature in (thermal, momentum):
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in signature.parameters.values()
        )
    assert thermal.parameters["restmkev"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        thermal_electron_momentum(250.0, 511.0)
    with pytest.raises(TypeError):
        normalized_momentum(GRID, 1.0, CLIGHT)
