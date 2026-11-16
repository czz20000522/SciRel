"""Every declared failure channel of the two source-profile contracts has one assertion.

`failure_semantics` names the exceptions a caller can actually see. A contract
that declares a channel nobody exercises is an unverified promise, so this file
carries one callable per declared channel and three checks:

* the covered set is written down, so a new source asset cannot join silently;
* the table's channel set equals the exception classes the contract's
  ``failure_semantics`` text names, so a channel cannot be added, renamed or
  dropped without editing the table deliberately;
* every callable really produces its declared channel, so the mapping stays
  executable rather than documentary.

The two remaining channel keys, ``nonconvergence`` and ``partial_results``, are
claims about *absence*: the relation is one closed-form normalization, so there
is no iteration to fail, and a raised exception returns no vector. Those are
exercised by the same rows — ``pytest.raises`` around a call that would otherwise
return an array proves the call produced no partial result and no convergence
state. They are not exception classes and so do not appear in the table.

Channels are matched by exception class name only; the message text stays owned
by the implementation and its own per-asset tests.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scirel.source import exponential_profile, gaussian_profile

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
_DECLARED = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Warning|Exception))\b")

COVERED = (
    "scirel.source.exponential",
    "scirel.source.gaussian",
)

#: A nonuniform three-cell grid on which both shapes stay finite.
_GRID = dict(
    rho_norm=[0.2, 0.6, 0.9],
    vpr=[2.0, 3.0, 4.0],
    drho_norm=[0.4, 0.4, 0.2],
)


def _exponential(**overrides):
    values = dict(_GRID, decay_start=0.8, width=0.2, total=4.0)
    values.update(overrides)
    rho = values.pop("rho_norm")
    vpr = values.pop("vpr")
    drho = values.pop("drho_norm")
    return exponential_profile(rho, vpr, drho, **values)


def _gaussian(**overrides):
    values = dict(_GRID, center=0.5, width=0.2, total=4.0)
    values.update(overrides)
    rho = values.pop("rho_norm")
    vpr = values.pop("vpr")
    drho = values.pop("drho_norm")
    return gaussian_profile(rho, vpr, drho, **values)


def _unrepresentable(function):
    """Ask for a finite integral whose per-cell value cannot be a float64.

    ``total`` is a finite float64 and every weight is a finite positive float64,
    so the inputs are legal: the profile amplitude itself is what leaves the
    representable range. That is the declared runtime channel, not an input
    error, and it must be reached without changing any tolerance.
    """
    return function(vpr=[1e-300, 1e-300, 1e-300], total=1e308)


CHANNELS = {
    "scirel.source.exponential": {
        "ValueError": lambda: _exponential(rho_norm=[0.2, 0.2, 0.9]),
        "FloatingPointError": lambda: _unrepresentable(_exponential),
    },
    "scirel.source.gaussian": {
        "ValueError": lambda: _gaussian(drho_norm=[0.4, 0.0, 0.2]),
        "FloatingPointError": lambda: _unrepresentable(_gaussian),
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
    ids=lambda value: value.replace("scirel.source.", ""),
)
def test_the_assertion_really_produces_its_channel(asset_id, channel):
    """The call raises its declared class and therefore hands back no vector."""
    with pytest.raises(Exception) as raised:
        CHANNELS[asset_id][channel]()
    assert type(raised.value).__name__ == channel, f"{asset_id}: {type(raised.value).__name__}"


@pytest.mark.parametrize("asset_id", COVERED)
def test_the_documented_nan_width_case_is_not_a_failure_channel(asset_id):
    """A zero or nonfinite width returns an all-NaN profile instead of raising.

    The contract states that separation explicitly, so it is part of the channel
    boundary: if this ever started raising, the declared ``invalid_input`` clause
    ("a numeric but nonfinite width is the documented NaN-return case") would be
    wrong.
    """
    call = _exponential if asset_id.endswith("exponential") else _gaussian
    for width in (0.0, float("inf"), float("-inf"), float("nan")):
        result = call(width=width)
        assert result.shape == (3,)
        assert bool((result != result).all()), width
