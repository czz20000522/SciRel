"""One assertion per declared failure channel of the two finite-volume contracts.

`failure_semantics` names the exceptions a caller can actually see. A channel
nobody exercises is an unverified promise, so this file carries one callable per
declared channel and three checks:

* the covered set is written down, so a new finite-volume asset cannot join
  silently;
* the table's channel set equals the exception classes the contract's
  ``failure_semantics`` text names, so a channel cannot be added, renamed or
  dropped without editing the table deliberately;
* every callable really produces its declared channel, so the mapping stays
  executable rather than documentary.

Two of the declared channels are claims about absence rather than about an
exception. ``nonconvergence`` says there is no iteration whose failure could be
reported, and ``partial_results`` says a failed call returns nothing; both are
exercised by the rows below, where ``pytest.raises`` wraps a call that would
otherwise return a value.

Channels are matched by exception class name only; the message text stays owned
by the implementation and its own per-asset tests.
"""

from __future__ import annotations

import json
import re
from math import ldexp
from pathlib import Path

import numpy as np
import pytest

from scirel.fvm import CellVariable, theta_step

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
_DECLARED = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Warning|Exception))\b")

COVERED = (
    "scirel.fvm.cell-variable",
    "scirel.fvm.theta-step",
)


def _nonfinite_derivative():
    """Ask for a derivative whose true magnitude is past the float64 range.

    The two cells are one part in 2**540 apart in coordinate and 2**600 apart in
    value, so the secant is representable while the quadratic stencil's
    intermediate products are not. Both inputs are finite, which is what makes
    this the declared runtime channel rather than an input error.
    """
    tiny = ldexp(1.0, -540)
    variable = CellVariable([0.0, ldexp(1.0, 600)], [0.0, tiny, 2 * tiny])
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return variable.face_grad()


def _overflowing_implicit_matrix():
    """A finite diffusivity whose ``dt*d`` product leaves the float64 range."""
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    with np.errstate(over="ignore", invalid="ignore"):
        return theta_step(variable, variable, 1e308, theta=0.5, d_new=[4.0, 4.0, 4.0])


def _singular_banded_system():
    """Signed anti-diffusion at ``dt=0.5`` makes ``I - dt*C`` singular."""
    variable = CellVariable([1.0, -1.0], [0.0, 1.0, 2.0])
    return theta_step(variable, variable, 0.5, d_new=-np.ones(3))


CHANNELS = {
    "scirel.fvm.cell-variable": {
        "ValueError": lambda: CellVariable([0.0, 1.0], [1.0, 0.0, 2.0]),
        "TypeError": lambda: CellVariable(np.array(["a", "b"]), [0.0, 1.0, 2.0]),
        "FloatingPointError": _nonfinite_derivative,
    },
    "scirel.fvm.theta-step": {
        "ValueError": lambda: theta_step(
            CellVariable([0.0, 0.0], [0.0, 1.0, 2.0]),
            CellVariable([0.0, 0.0], [0.0, 1.0, 2.0]),
            1.0,
            d_new=[np.inf, np.inf, np.inf],
        ),
        "TypeError": lambda: theta_step(object(), CellVariable([0.0, 0.0], [0.0, 1.0, 2.0]), 1.0),
        "FloatingPointError": _overflowing_implicit_matrix,
        "LinAlgError": _singular_banded_system,
    },
}


def _declared_channels(asset_id):
    document = json.loads((EXAMPLES / f"{asset_id}.json").read_text(encoding="utf-8"))
    names = set()
    for text in document["failure_semantics"].values():
        if isinstance(text, str):
            names.update(_DECLARED.findall(text))
    return names


def test_the_covered_set_is_explicit():
    assert set(CHANNELS) == set(COVERED)


@pytest.mark.parametrize("asset_id", COVERED)
def test_every_declared_channel_has_exactly_one_assertion(asset_id):
    assert set(CHANNELS[asset_id]) == _declared_channels(asset_id)


@pytest.mark.parametrize(
    "asset_id,channel",
    [(asset, channel) for asset, table in CHANNELS.items() for channel in sorted(table)],
    ids=lambda value: value.replace("scirel.fvm.", ""),
)
def test_the_assertion_really_produces_its_channel(asset_id, channel):
    """The call raises its declared class and therefore hands back nothing."""
    with pytest.raises(Exception) as raised:
        CHANNELS[asset_id][channel]()
    assert type(raised.value).__name__ == channel, f"{asset_id}: {type(raised.value).__name__}"


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
def test_the_channel_class_does_not_depend_on_the_numpy_error_policy(policy):
    """A warn/ignore policy may suppress a NumPy warning; it cannot change the class.

    This is the boundary the theta-step contract states explicitly, and it is the
    one that would rot silently: an implementation that stopped calling the
    finite-value check would still raise under ``raise`` and would start
    returning nonfinite state under ``ignore``.
    """
    with np.errstate(over=policy, invalid=policy, divide=policy):
        with pytest.raises(FloatingPointError):
            _overflowing_implicit_matrix()
        with pytest.raises(FloatingPointError):
            _nonfinite_derivative()


@pytest.mark.parametrize("dt", [0.0, -1.0, np.inf])
def test_the_step_size_guard_rejects_nonpositive_and_nonfinite_values(dt):
    """``dt`` must be finite and strictly positive, before any operator is built.

    The declared channel is ``ValueError`` and the guard has two sides; a test
    that only checks a large finite step would leave the lower bound free to
    widen.
    """
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        theta_step(variable, variable, dt)


@pytest.mark.parametrize("theta", [-0.5, 1.5, np.nan])
def test_the_theta_guard_rejects_values_outside_the_closed_unit_interval(theta):
    """``theta`` is documented as a weight in ``[0, 1]``; both bounds are enforced."""
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        theta_step(variable, variable, 1.0, theta=theta)


@pytest.mark.parametrize("mode", ["ghost", "direct", "semi-implicit"])
def test_an_undocumented_boundary_mode_is_rejected_before_assembly(mode):
    """The enumeration is validated even when both convection terms are absent."""
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    for name, value in (("dirichlet_mode", mode + "-typo"), ("neumann_mode", mode + "-typo")):
        with pytest.raises(ValueError, match="invalid convection boundary mode"):
            theta_step(variable, variable, 1.0, **{name: value})
