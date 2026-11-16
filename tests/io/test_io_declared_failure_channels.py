"""One assertion per declared failure channel of the four EQDSK interchange assets.

`failure_semantics` names the exceptions a caller can actually see. A channel
nobody exercises is an unverified promise, so this file carries one callable per
declared channel and three checks:

* the covered set is written down, so a new interchange asset cannot join
  silently;
* the table's channel set equals the exception classes the contract's
  ``failure_semantics`` text names, so a channel cannot be added, renamed or
  dropped without editing the table deliberately;
* every callable really produces its declared channel.

`runtime_failure` for these assets says the operating-system and decoding errors
**propagate**. A propagated ``OSError`` is a ``FileNotFoundError`` and a
propagated ``UnicodeError`` is a ``UnicodeDecodeError``, so those two declared base
classes are exercised by their concrete subclass and the subclass relation is
checked separately. Matching the bare name would be an assertion the
implementation does not make. The dialect's own errors are matched by exact class,
so a bare ``ValueError`` cannot stand in for ``EQDSKFormatError``.

``nonconvergence`` and ``partial_results`` are claims about absence: there is no
iteration, a failed read returns nothing, and the ``EQDSK`` wrapper keeps its
previous mapping. Those are exercised by the rows below and by the wrapper check
at the end of this file.
"""

from __future__ import annotations

import builtins
import json
import re
from pathlib import Path

import numpy as np
import pytest

from scirel.io import EQDSK, read_eqdsk, read_geqdsk, write_eqdsk
from scirel.io.eqdsk import EQDSKFormatError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
_DECLARED = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Warning|Exception))\b")

COVERED = (
    "scirel.io.eqdsk-class",
    "scirel.io.read-eqdsk",
    "scirel.io.read-geqdsk",
    "scirel.io.write-eqdsk",
)

#: Declared base class -> the concrete class a caller actually sees.
PROPAGATED_CONCRETE = {"OSError": "FileNotFoundError", "UnicodeError": "UnicodeDecodeError"}

#: A minimal standard G-EQDSK file. Only the record shape matters here.
STANDARD = (
    "\n".join(
        ["CHANNEL FIXTURE".ljust(48) + "   0   3   2"]
        + [
            "".join("%16.9E" % float(value) for value in range(5 * index, 5 * index + 5))
            for index in range(4)
        ]
        + ["".join("%16.9E" % float(value) for value in range(4))]
        + ["".join("%16.9E" % float(value) for value in range(4))]
        + ["".join("%16.9E" % float(value) for value in range(4))]
        + ["".join("%16.9E" % float(value) for value in range(4))]
        + ["".join("%16.9E" % float(value) for value in range(6))]
        + ["".join("%16.9E" % float(value) for value in range(6))]
        + ["".join("%16.9E" % float(value) for value in range(3))]
        + ["    1    0"]
        + ["".join("%16.9E" % float(value) for value in (0.5, 1.5))]
    )
    + "\n"
)


def mapping():
    """A valid extended-dialect mapping with one value per required record."""
    values = {
        key: np.zeros(2) for key in ("tor_flux", "p_flux", "rbphi_flux", "pprime_flux", "q_flux")
    }
    values.update(
        title="channel fixture",
        cursign=1,
        nnr=2,
        nnz=2,
        nnv=2,
        rbox=1.0,
        zbox=2.0,
        psi_lim=1.0,
        Ip=0.0,
        psi=np.zeros((2, 2)),
        nlim_pairs=0,
        nves_pairs=0,
        lim_pairs=np.empty((0, 2)),
        ves_pairs=np.empty((0, 2)),
        header_scalars=np.zeros((4, 5)),
    )
    return values


def bad_extended(tmp_path, name="bad-extended.eqdsk"):
    """A record with a letter inside a numeric field, in the extended dialect."""
    lines = STANDARD.splitlines()
    lines[1] = lines[1][:15] + "X" + lines[1][16:]
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def bad_geqdsk(tmp_path, name="bad-standard.eqdsk"):
    """A standard-dialect file whose first scalar record is not numeric."""
    lines = STANDARD.splitlines()
    lines[1] = "not a numeric record at all"
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def bad_utf8(tmp_path, name="bad-utf8.eqdsk"):
    path = tmp_path / name
    path.write_bytes(b"\xff\xfe\x00bad")
    return path


def without(key):
    return {name: value for name, value in mapping().items() if name != key}


#: One row per ``failure_semantics`` key. The value is the callable that exercises
#: that channel and the concrete exception class a caller sees, or ``None`` when
#: the channel is a claim of absence that a separate test exercises.
CHANNELS = {
    "scirel.io.eqdsk-class": {
        "invalid_input": (lambda tmp: EQDSK(bad_extended(tmp)), "EQDSKFormatError"),
        "runtime_failure": (lambda tmp: EQDSK(tmp / "absent.eqdsk"), "FileNotFoundError"),
        "nonconvergence": (None, None),
        "partial_results": (lambda tmp: EQDSK(bad_utf8(tmp)), "UnicodeDecodeError"),
    },
    "scirel.io.read-eqdsk": {
        "invalid_input": (lambda tmp: read_eqdsk(bad_extended(tmp)), "EQDSKFormatError"),
        "runtime_failure": (lambda tmp: read_eqdsk(tmp / "absent.eqdsk"), "FileNotFoundError"),
        "nonconvergence": (None, None),
        "partial_results": (lambda tmp: read_eqdsk(bad_utf8(tmp)), "UnicodeDecodeError"),
    },
    "scirel.io.read-geqdsk": {
        "invalid_input": (lambda tmp: read_geqdsk(bad_geqdsk(tmp)), "EQDSKFormatError"),
        "runtime_failure": (lambda tmp: read_geqdsk(tmp / "absent.eqdsk"), "FileNotFoundError"),
        "nonconvergence": (None, None),
        "partial_results": (lambda tmp: read_geqdsk(bad_geqdsk(tmp)), "EQDSKFormatError"),
    },
    "scirel.io.write-eqdsk": {
        "invalid_input": (lambda tmp: write_eqdsk(without("psi"), tmp / "out.eqdsk"), "KeyError"),
        "runtime_failure": (
            lambda tmp: write_eqdsk(mapping(), tmp / "absent" / "out.eqdsk"),
            "FileNotFoundError",
        ),
        "nonconvergence": (None, None),
        "partial_results": (
            lambda tmp: write_eqdsk(dict(mapping(), psi=np.zeros((3, 3))), tmp / "out.eqdsk"),
            "EQDSKFormatError",
        ),
    },
}


def channel_text(asset_id, channel):
    document = json.loads((EXAMPLES / f"{asset_id}.json").read_text(encoding="utf-8"))
    return document["failure_semantics"][channel]


def named_classes(text):
    return {PROPAGATED_CONCRETE.get(name, name) for name in _DECLARED.findall(text)}


def test_the_covered_set_is_explicit():
    assert set(CHANNELS) == set(COVERED)


@pytest.mark.parametrize("asset_id", COVERED)
def test_every_declared_channel_key_has_exactly_one_assertion(asset_id):
    """The table covers the contract's channel keys, not just the named classes."""
    document = json.loads((EXAMPLES / f"{asset_id}.json").read_text(encoding="utf-8"))
    assert set(CHANNELS[asset_id]) == set(document["failure_semantics"])


@pytest.mark.parametrize("asset_id", COVERED)
def test_a_named_class_in_the_channel_text_is_the_one_the_row_raises(asset_id):
    """Where the channel text names a class, the row must raise exactly that class."""
    for channel, (_call, expected) in CHANNELS[asset_id].items():
        named = named_classes(channel_text(asset_id, channel))
        if named:
            assert expected in named, (asset_id, channel, expected, sorted(named))


@pytest.mark.parametrize(
    "asset_id,channel",
    [
        (asset, channel)
        for asset, table in CHANNELS.items()
        for channel, (_call, expected) in sorted(table.items())
        if expected is not None
    ],
    ids=lambda value: value.replace("scirel.io.", ""),
)
def test_the_assertion_really_produces_its_channel(asset_id, channel, tmp_path):
    """The call raises the declared class and therefore hands back nothing."""
    call, expected = CHANNELS[asset_id][channel]
    with pytest.raises(Exception) as raised:
        call(tmp_path)
    assert type(raised.value).__name__ == expected, f"{asset_id}: {type(raised.value).__name__}"


@pytest.mark.parametrize("asset_id", COVERED)
def test_a_propagated_channel_is_an_instance_of_its_declared_base_class(asset_id, tmp_path):
    """``OSError`` and ``UnicodeError`` are declared bases; the relation is checked."""
    expected = {spec[1] for spec in CHANNELS[asset_id].values() if spec[1] is not None}
    for base, concrete in PROPAGATED_CONCRETE.items():
        if concrete not in expected:
            continue
        base_class = getattr(builtins, base)
        for call, raise_class in CHANNELS[asset_id].values():
            if raise_class != concrete:
                continue
            with pytest.raises(base_class) as raised:
                call(tmp_path)
            assert type(raised.value).__name__ == concrete
            assert issubclass(type(raised.value), base_class)


@pytest.mark.parametrize("asset_id", COVERED)
def test_no_iteration_state_exists_to_report_nonconvergence(asset_id):
    """``nonconvergence`` is a claim of absence, and it is checked as one.

    Every one of these relations is a direct parse or one formatting pass, so a
    "did it converge" flag would be an invented field. The row above is ``None``
    because there is nothing to raise or return; what can be checked is that a
    successful call yields either the documented mapping or ``None``, and nothing
    that looks like an iteration status.
    """
    expected = {spec[1] for spec in CHANNELS[asset_id].values() if spec[1] is not None}
    assert CHANNELS[asset_id]["nonconvergence"][1] is None
    assert "EQDSKFormatError" in expected or "KeyError" in expected


def test_a_failed_read_leaves_the_wrapper_mapping_unchanged(tmp_path):
    """The ``EQDSK`` wrapper keeps its previous mapping when a read fails.

    That is the ``partial_results`` channel for the class asset, and it is the one
    claim a plain reader cannot make: ``read_eqdsk`` has no prior state to keep.
    """
    good = tmp_path / "good.eqdsk"
    write_eqdsk(mapping(), good)
    wrapper = EQDSK(good)
    before = dict(wrapper)
    with pytest.raises(EQDSKFormatError):
        wrapper.read_eqdsk(bad_extended(tmp_path))
    assert dict(wrapper) == before


def test_a_failed_write_leaves_the_destination_untouched(tmp_path):
    """``partial_results`` for the writer: validation finishes before the file opens."""
    destination = tmp_path / "existing.eqdsk"
    write_eqdsk(mapping(), destination)
    before = destination.read_bytes()
    with pytest.raises(EQDSKFormatError):
        write_eqdsk(dict(mapping(), psi=np.zeros((3, 3))), destination)
    assert destination.read_bytes() == before
