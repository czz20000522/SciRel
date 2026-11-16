"""One assertion per declared failure channel of the stored-thermal-energy contract.

`failure_semantics` names the exceptions a caller can actually see. A channel
nobody exercises is an unverified promise, so this file carries one callable per
declared channel and the same three checks used across the other domains:

* the covered set is written down;
* the table's channel set equals the exception classes the contract's
  ``failure_semantics`` text names;
* every callable really produces its declared channel.

The remaining channel keys, ``nonconvergence`` and ``partial_results``, are
claims about absence — the relation is one closed-form sum with no iteration and
a failed call returns no tuple — and are exercised by the same rows, where
``pytest.raises`` wraps a call that would otherwise return three floats.

The contract distinguishes two *different* runtime outcomes that a naive test
would confuse: an exact energy above float64 max is rejected even when nearest
rounding would still be finite, while an exact zero is accepted. Both are checked
below, because collapsing them is the failure this channel would hide.
"""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from scirel.physics import calculate_stored_thermal_energy

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
_DECLARED = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Warning|Exception))\b")

COVERED = ("scirel.physics.thermal-energy",)

MAXIMUM = float(np.finfo(np.float64).max)


def _exact_above_maximum():
    """``1.5 * (max + max)`` is three times float64 max, though each input is finite.

    A single cell holding ``max`` would round back to ``max``; two cells force the
    exact sum past the representable range, which is the case the contract says
    must be rejected rather than silently rounded.
    """
    return calculate_stored_thermal_energy(
        [MAXIMUM, MAXIMUM], [0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [1.0, 1.0]
    )


CHANNELS = {
    "scirel.physics.thermal-energy": {
        "ValueError": lambda: calculate_stored_thermal_energy(
            [1.0], [1.0, 2.0], [1.0], [1.0], [1.0]
        ),
        "FloatingPointError": _exact_above_maximum,
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
    ids=lambda value: value.replace("scirel.physics.", ""),
)
def test_the_assertion_really_produces_its_channel(asset_id, channel):
    """The call raises its declared class and therefore hands back no tuple."""
    with pytest.raises(Exception) as raised:
        CHANNELS[asset_id][channel]()
    assert type(raised.value).__name__ == channel, f"{asset_id}: {type(raised.value).__name__}"


def test_an_exact_zero_is_not_the_rejected_case():
    """``0`` is accepted, while a nonzero exact energy that rounds to zero is not.

    The two outcomes are one bit apart in the implementation and both live in the
    declared runtime channel. Checking only the raising side would leave the
    accepted side free to start raising.
    """
    zero = calculate_stored_thermal_energy([0.0], [0.0], [0.0], [1.0], [1.0])
    assert zero == (0.0, 0.0, 0.0)

    smallest = float(np.nextafter(0.0, 1.0))
    exact = Fraction(3, 2) * Fraction(smallest) * Fraction(1, 4)
    assert exact != 0  # the exact energy survives, its float64 rounding does not
    with pytest.raises(FloatingPointError):
        calculate_stored_thermal_energy([smallest], [0.0], [0.0], [1.0], [0.25])


@pytest.mark.parametrize(
    "profile",
    [
        [1.0, np.nan],
        [1.0, np.inf],
        [1.0, -np.inf],
    ],
    ids=("nan", "inf", "neg-inf"),
)
def test_non_finite_inputs_stay_in_the_input_channel(profile):
    """A non-finite input is an input error, not a runtime failure."""
    with pytest.raises(ValueError):
        calculate_stored_thermal_energy(profile, [0.0, 0.0], [0.0, 0.0], [1.0, 1.0], [1.0, 1.0])


@pytest.mark.parametrize("weight", [0.0, -1.0])
def test_nonpositive_weights_are_rejected(weight):
    """The volume weight and quadrature width must stay strictly positive."""
    with pytest.raises(ValueError):
        calculate_stored_thermal_energy([1.0], [1.0], [1.0], [weight], [1.0])
    with pytest.raises(ValueError):
        calculate_stored_thermal_energy([1.0], [1.0], [1.0], [1.0], [weight])
