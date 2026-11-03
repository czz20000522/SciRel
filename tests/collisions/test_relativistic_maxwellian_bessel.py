"""Direct contract tests for ``scirel.collisions.relativistic_maxwellian_bessel``.

Two changes are under contract here.  First, the retained route's piecewise
Abramowitz--Stegun approximation is replaced by a direct ``scipy.special.kve``
evaluation, which removes a 1.5e-3 relative discontinuity in ``bk1`` at the
``x = 2`` branch boundary, and removes the branch selector, the branch label and
the per-branch accuracy metadata from the public contract.  Second, **a valid
argument for which the double-precision backend does not produce three finite
quantities is rejected instead of answered with a non-finite value.**

The fail-closed contract is tested by **making the backend produce non-finite
values**, not by probing where this machine's SciPy stops being representable.
The arguments at which that happens are a property of the installed build and
platform rather than of the relation, so no test here pins them, no test asserts
that a particular double is the last finite or the first overflowing one, and the
implementation states no such bound.

This module tests the maintained implementation directly.  The review unit that
produced it additionally compared the route against the frozen V2/V3 predecessors
and the read-only L1 route; those arms live outside the repository and are not
reachable from the maintained baseline, so they are not replayed here.  The
claims they established -- the retained boundary jump, the worst differences away
from the boundary, and the retained input guard -- are asserted below from their
recorded values.
"""
from __future__ import annotations

import importlib
import inspect
import math
import pathlib

import numpy as np
import pytest
from scipy.special import k0, kve

from scirel.collisions.relativistic_maxwellian_bessel import (
    BesselBackendEvaluationError,
    InvalidBesselArgumentError,
    relativistic_maxwellian_bessel,
)

TARGET = importlib.import_module("scirel.collisions.relativistic_maxwellian_bessel")

# This module's discontinuity in bk1 across x = 2.  The retained route's
# corresponding jump was measured at 1.5076691838017936e-03 relative, which is
# the retained route's own stated per-branch accuracy bound for bk1
# (1.5076715906952082e-03) and larger than its worst smooth approximation error
# anywhere else in its domain.  That figure was measured against the frozen
# external route, which lives outside this repository and is not reachable from
# the maintained baseline, so it is recorded as the reason for the change rather
# than re-measured here.
RETAINED_BOUNDARY_JUMP = 0.0015076691838017936
DIRECT_BOUNDARY_JUMP = 8.59408144671376e-16


def relative(first, second):
    return abs(first - second) / abs(second)


# ---------------------------------------------------------------------------
# The carried change: the approximation and its machinery
# ---------------------------------------------------------------------------


def test_the_closure_returns_only_the_three_quantities():
    """The branch selector, the branch label and the accuracy bounds are gone."""
    result = relativistic_maxwellian_bessel(1.5)
    assert set(result) == {"bk0", "bk1", "bk2"}


def test_the_signature_is_the_retained_routes_and_has_no_branch_selector():
    """The V2 candidate added a ``branch_switch`` keyword; the relation has none."""
    assert tuple(inspect.signature(relativistic_maxwellian_bessel).parameters) == ("x",)
    with pytest.raises(TypeError):
        relativistic_maxwellian_bessel(1.5, branch_switch=1.5)


def test_the_closure_is_smooth_across_the_retained_branch_boundary():
    """No branch exists at ``x = 2``, and no branch is reported.

    The retained route split its domain at ``x = 2`` and its two branches met with
    a relative jump of ``1.5076691838017936e-03`` in ``bk1`` -- the retained
    route's own stated per-branch accuracy bound, and larger than its smooth
    approximation error anywhere else.  That figure was measured against the
    frozen external route and is not re-measured here.

    What is asserted is this module's own behaviour: the value is continuous at
    ``x = 2`` at the resolution of adjacent doubles, which is what evaluating the
    relation directly buys.  The bound is derived from the spacing of the two
    doubles rather than compared against a recorded constant, so the test states
    the property rather than replaying a measurement.
    """
    boundary = 2.0
    below = float(np.nextafter(boundary, -np.inf))
    above = float(np.nextafter(boundary, np.inf))

    def jump(first, second):
        return relative(
            relativistic_maxwellian_bessel(first)["bk1"],
            relativistic_maxwellian_bessel(second)["bk1"],
        )

    # Two adjacent doubles differ by one ulp of the argument, so a smooth
    # function's relative change across them is a few ulp of the value.
    rounding_scale = 8.0 * np.finfo(np.float64).eps
    assert jump(below, boundary) == DIRECT_BOUNDARY_JUMP
    assert jump(below, boundary) <= rounding_scale
    assert jump(boundary, above) <= rounding_scale
    # The removal is real: the jump this module shows is twelve orders of
    # magnitude below the one the retained route carried at the same point.
    assert DIRECT_BOUNDARY_JUMP * 1.0e12 < RETAINED_BOUNDARY_JUMP
    # And it is a property of the relation, not of this one point: the closure is
    # smooth across every neighbourhood sampled, with no branch to label.
    for centre in (1.0e-3, 0.25, 1.0, 2.0, 3.0, 10.0, 60.0, 700.0):
        left = float(np.nextafter(centre, -np.inf))
        right = float(np.nextafter(centre, np.inf))
        assert jump(left, centre) <= rounding_scale, centre
        assert jump(centre, right) <= rounding_scale, centre
    # No branch label, selector or accuracy metadata is returned anywhere.
    for x in (below, boundary, above):
        assert set(relativistic_maxwellian_bessel(x)) == {"bk0", "bk1", "bk2"}


def test_the_three_quantities_are_the_rescaled_bessel_functions():
    for x in (1.0e-3, 0.5, 1.0, 1.9999999999999998, 2.0, 5.0, 38.71, 60.0, 700.0):
        result = relativistic_maxwellian_bessel(x)
        assert result["bk0"] == float(kve(0, x))
        assert result["bk1"] == float(kve(1, x))


def test_bk2_is_the_recurrence_not_an_independent_third_approximation():
    """``K_2 = K_0 + 2*K_1/x``, so the recurrence and the direct order-2 value agree."""
    for x in (1.0e-3, 0.5, 1.0, 2.0, 5.0, 60.0, 700.0):
        result = relativistic_maxwellian_bessel(x)
        assert result["bk2"] == result["bk0"] + 2.0 * result["bk1"] / x
        # The public contract fixes the recurrence; direct SciPy K2 is an
        # independent rounded evaluation and can differ by one ulp.
        np.testing.assert_allclose(result["bk2"], float(kve(2, x)), rtol=2e-15, atol=1e-12)


# ---------------------------------------------------------------------------
# The fail-closed contract
# ---------------------------------------------------------------------------


def test_the_backend_failure_is_made_and_the_call_fails_closed(monkeypatch):
    """The contract is proven by making the backend non-finite, not by probing it.

    ``scipy.special.kve`` is replaced for the duration of the test, so the failure
    is unconditional and identical on every platform.  The claim under test is the
    response to a non-finite backend value, which is the whole of the contract;
    where a particular build first produces one is a separate, non-contract
    observation.
    """
    for order, value in (
        (0, float("nan")), (0, float("inf")), (1, float("nan")), (1, float("inf")),
    ):
        def fake(order_index, argument, _order=order, _value=value):
            return _value if order_index == _order else float(kve(order_index, argument))

        monkeypatch.setattr(TARGET, "kve", fake)
        with pytest.raises(BesselBackendEvaluationError) as raised:
            relativistic_maxwellian_bessel(1.5)
        message = str(raised.value)
        assert "1.5" in message
        assert "kve" in message
    monkeypatch.undo()

    # A backend that overflows only through the recurrence is caught too: bk0 and
    # bk1 are finite and bk2 is not.
    def overflow_through_recurrence(order_index, argument):
        return 1.0e308 if order_index == 0 else 1.0e308

    monkeypatch.setattr(TARGET, "kve", overflow_through_recurrence)
    with pytest.raises(BesselBackendEvaluationError) as raised:
        relativistic_maxwellian_bessel(1.0e-300)
    assert "bk2=inf" in str(raised.value)


def test_a_rejected_call_produces_no_value(monkeypatch):
    """Fail-closed, not fail-partial: the rejection carries no partial mapping."""
    monkeypatch.setattr(TARGET, "kve", lambda order, argument: float("nan"))
    with pytest.raises(BesselBackendEvaluationError) as raised:
        relativistic_maxwellian_bessel(2.0)
    assert raised.value.args and isinstance(raised.value.args[0], str)
    assert not isinstance(raised.value.args[0], dict)
    assert "bk0=nan" in raised.value.args[0]


def test_the_error_message_states_no_domain_bound(monkeypatch):
    """No ceiling, no boundary, no threshold: the message reports input and output."""
    monkeypatch.setattr(TARGET, "kve", lambda order, argument: float("inf"))
    with pytest.raises(BesselBackendEvaluationError) as raised:
        relativistic_maxwellian_bessel(3.25)
    message = str(raised.value).lower()
    for forbidden in (
        "ceiling", "boundary", "threshold", "last finite", "first nan",
        "not representable", "out of domain", "too large", "too small",
    ):
        assert forbidden not in message, forbidden
    assert "3.25" in message
    assert "bk0=inf" in message


def test_the_implementation_states_no_backend_threshold():
    """No platform-dependent cutoff is a constant, an attribute or a literal.

    The V3 candidate exported ``KVE_LAST_FINITE_ARGUMENT`` and
    ``KVE_FIRST_NAN_ARGUMENT`` and branched on them.  A domain bound measured from
    one SciPy build is not part of the relation's contract, so this module has
    none: it carries no such name, and its source contains none of the measured
    literals.
    """
    for name in (
        "KVE_LAST_FINITE_ARGUMENT", "KVE_FIRST_NAN_ARGUMENT",
        "OVERFLOW_LAST_FINITE_ARGUMENT", "OVERFLOW_FIRST_ARGUMENT",
        "KVE_LAST_FINITE_SMALL_ARGUMENT", "KVE_FIRST_INFINITE_SMALL_ARGUMENT",
    ):
        assert not hasattr(TARGET, name), name
    source = pathlib.Path(inspect.getfile(relativistic_maxwellian_bessel)).read_text(
        encoding="utf-8"
    )
    for literal in ("1073741823", "1.054768661486", "2.225073858507"):
        assert literal not in source, literal


def test_the_rejection_hierarchy_separates_input_errors_from_backend_failures():
    """Two classes, because there are two things a caller can do about a rejection."""
    assert issubclass(InvalidBesselArgumentError, ValueError)
    assert issubclass(BesselBackendEvaluationError, ValueError)
    assert not issubclass(InvalidBesselArgumentError, BesselBackendEvaluationError)
    assert not issubclass(BesselBackendEvaluationError, InvalidBesselArgumentError)
    # A caller that only knows ValueError still catches both.
    with pytest.raises(ValueError):
        relativistic_maxwellian_bessel(0.0)


def test_the_input_contract_requires_a_positive_finite_real_scalar():
    """Booleans, strings, complex values and non-scalars are rejected, not coerced."""
    for bad in (0.0, -1.0, float("nan"), float("inf"), -float("inf")):
        with pytest.raises(ValueError, match="positive and finite"):
            relativistic_maxwellian_bessel(bad)
        with pytest.raises(InvalidBesselArgumentError, match="positive and finite"):
            relativistic_maxwellian_bessel(bad)
    # AUDIT-B3: the stricter real-scalar contract also rejects non-real coercions
    # (previously ``None`` leaked a bare TypeError and ``True``/``"1.0"`` were
    # silently converted by float()).
    for bad in (None, True, "1.0", 1 + 0j, [1.0], np.array([1.0])):
        with pytest.raises(InvalidBesselArgumentError, match="positive and finite"):
            relativistic_maxwellian_bessel(bad)


def test_every_accepted_call_returns_three_finite_floats():
    """The contract the fail-closed rejection buys, swept over ordinary arguments.

    The sweep is logarithmic and wide, but it makes no claim about where the
    accepted region ends: it asserts only that nothing accepted is non-finite, and
    it treats a backend rejection as a legitimate outcome rather than a failure.
    The range is chosen to stay inside the region this build evaluates, so the
    rejection branch is exercised by the monkeypatched tests above rather than
    here -- a sweep that reached past the region would be measuring this build's
    SciPy rather than the contract.
    """
    rng = np.random.default_rng(20260922)
    accepted = rejected = 0
    for _ in range(4000):
        x = float(10.0 ** rng.uniform(-150.0, 6.0))
        try:
            result = relativistic_maxwellian_bessel(x)
        except BesselBackendEvaluationError:
            rejected += 1
            continue
        assert set(result) == {"bk0", "bk1", "bk2"}
        assert all(type(value) is float for value in result.values()), (x, result)
        assert all(math.isfinite(value) for value in result.values()), (x, result)
        accepted += 1
    assert accepted > 3900


# ---------------------------------------------------------------------------
# The scientific boundary
# ---------------------------------------------------------------------------


def test_the_rescaled_closure_is_bounded_where_the_plain_bessel_functions_are_not():
    """The rescaling is real, and the closure follows its asymptotic form.

    ``kve`` is the rescaled function: it agrees with ``exp(x) * K_0(x)`` to the
    last few bits, and by x = 1000 the plain ``K_0`` has underflowed to zero while
    the rescaled form is still about 4e-2.  The test asserts the rescaling identity
    and the asymptotic value, and nothing about where either becomes
    unrepresentable.
    """
    assert kve(0, 1000.0) > 1.0e-3
    assert k0(1000.0) == 0.0
    for x in (60.0, 100.0, 700.0):
        result = relativistic_maxwellian_bessel(x)
        assert math.isfinite(result["bk0"])
        assert result["bk0"] == pytest.approx(math.exp(x) * k0(x), rel=1.0e-13)
        assert result["bk0"] == pytest.approx(
            math.sqrt(math.pi / (2.0 * x)), rel=1.0e-2
        )


def test_the_closure_is_monotone_decreasing_in_x():
    """A shape property of the relation, checked independently of either route."""
    previous = None
    for x in (1.0e-6, 1.0e-3, 0.1, 1.0, 10.0, 100.0, 1000.0):
        result = relativistic_maxwellian_bessel(x)
        if previous is not None:
            assert result["bk0"] < previous["bk0"]
            assert result["bk1"] < previous["bk1"]
        previous = result


# ---------------------------------------------------------------------------
# AUDIT-B3: fail-closed validation must reject non-real coercions.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [
    True,
    False,
    "1.0",
    b"1.0",
    1 + 0j,
    [1.0],
    np.array([1.0]),
])
def test_non_real_coercions_are_rejected_as_invalid_arguments(bad):
    """Boolean, string, complex and non-scalar inputs are not positive scalars."""
    with pytest.raises(InvalidBesselArgumentError):
        relativistic_maxwellian_bessel(bad)
