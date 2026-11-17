#!/usr/bin/env python3
"""Summarise one acceptance receipt into a committed anchor, and check an anchor against one.

The full receipt lives in ``.runtime/logs/check-<id>/result.json``, which is gitignored, so the
evidence for a green run disappears when the worktree is cleaned. The anchor is the part that
stays: the run's identity, its environment, its counts, the reason for every skip and xfail, and
two digests over the 8,000-odd per-test records — small enough to commit, specific enough that a
rerun on the same revision can be reconciled with it.

This is not a second acceptance entry point. It starts no test, judges no step, prints no green,
and cannot turn anything red: ``export`` compresses a receipt that already exists, ``verify`` says
whether another receipt agrees with an anchor. The exit status is about agreement only —
0 agree, 1 disagree, 2 cannot check — and never about whether the acceptance itself passed.

Usage:
    python3 scripts/dev.py run python -B \
        skills/development/scirel-acceptance/scripts/acceptance_anchor.py export <receipt> <anchor>
    python3 scripts/dev.py run python -B \
        skills/development/scirel-acceptance/scripts/acceptance_anchor.py verify <anchor> <receipt>
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from check_all import (
    ANCHOR_SCHEMA,
    RESULT_SCHEMA,
    STATUS_COMPLETE,
    validate_provenance,
)

AGREE = 0
DISAGREE = 1
CANNOT_CHECK = 2

# Written into every anchor so the digests can be recomputed by someone who reads the file and
# not this script. Change the rules here only by rewriting this text, and the old anchors stop
# claiming an identity they no longer have.
NORMALIZATION = {
    "nodeid": (
        "pytest nodeid exactly as the counts plugin recorded it, with every backslash replaced by"
        " '/', a leading './' removed, and nothing else changed: the file path keeps its"
        " repository-relative form (no drive letter, no absolute prefix), the '::' separators"
        " stay, and a parametrised id keeps its '[param]' suffix verbatim"
    ),
    "order": "interpreter string sort (sorted()), which is code-point order and locale-free",
    "nodeid_set_sha256": (
        "sha256 of the UTF-8 bytes of every normalised selected nodeid joined by a newline with"
        " one trailing newline; duplicates are not collapsed, because the counts validator already"
        " refuses a selected list with duplicates"
    ),
    "per_test_sha256": (
        "sha256 of one JSON array per test, [nodeid, outcome, reason], serialised with"
        " separators (',', ':') and ensure_ascii=False, ordered by normalised nodeid, joined by"
        " newlines with one trailing newline; reason is the phase's wasxfail when present, else"
        " the phase's skip reason, else an empty string"
    ),
}

# Fields compared by ``verify``. Identity, environment and per-test digests are what make two
# runs "the same run"; the timestamps and the receipt digest are not.
COMPARED = (
    ("stage",),
    ("candidate", "commit"),
    ("candidate", "tree"),
    ("candidate", "worktree_sha256"),
    ("environment", "python"),
    ("environment", "platform"),
    ("environment", "architecture"),
    ("environment", "dependencies"),
    ("environment", "uv_lock_sha256"),
    ("environment", "python_version_sha256"),
    ("provenance", "check_all_sha256"),
    ("provenance", "counts_plugin_sha256"),
    ("tests", "collected"),
    ("tests", "selected"),
    ("tests", "deselected"),
    ("tests", "passed"),
    ("tests", "failed"),
    ("tests", "error"),
    ("tests", "skipped"),
    ("tests", "xfailed"),
    ("tests", "xpassed"),
    ("tests", "nodeid_set_sha256"),
    ("tests", "per_test_sha256"),
    ("skip_reasons",),
    ("xfail_reasons",),
)


class CannotCheck(Exception):
    """The anchor or the receipt cannot be read well enough to compare."""


def normalize_nodeid(nodeid: str) -> str:
    """Put a nodeid in the one form the digests are defined over (see NORMALIZATION)."""
    text = nodeid.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _nodeid_set_digest(nodeids: list[str]) -> str:
    payload = "\n".join(sorted(normalize_nodeid(node) for node in nodeids)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reason(item: dict) -> str:
    for phase in item["phases"]:
        if isinstance(phase.get("wasxfail"), str):
            return phase["wasxfail"]
    for phase in item["phases"]:
        if isinstance(phase.get("reason"), str):
            return phase["reason"]
    return ""


def _per_test_digest(results: list[dict]) -> str:
    rows = sorted(
        ((normalize_nodeid(item["nodeid"]), item["outcome"], _reason(item)) for item in results),
        key=lambda row: row[0],
    )
    payload = (
        "\n".join(json.dumps(list(row), ensure_ascii=False, separators=(",", ":")) for row in rows)
        + "\n"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reason_counts(results: list[dict], outcome: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        if item["outcome"] != outcome:
            continue
        reason = _reason(item)
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def build_anchor(receipt: dict, result_sha256: str, checked_at: str) -> dict:
    """Compress one complete receipt into the anchor a rerun can be reconciled against."""
    tests = receipt["tests"]
    results = tests["results"]
    counts = {
        field: tests[field]
        for field in (
            "collected",
            "selected",
            "deselected",
            "passed",
            "failed",
            "error",
            "skipped",
            "xfailed",
            "xpassed",
        )
    }
    counts["nodeid_set_sha256"] = _nodeid_set_digest(tests["selected_nodeids"])
    counts["per_test_sha256"] = _per_test_digest(results)
    return {
        "schema": ANCHOR_SCHEMA,
        "stage": receipt["stage"],
        "checked_at": checked_at,
        "candidate": dict(receipt["candidate"]["before"]),
        "environment": dict(receipt["environment"]["before"]),
        "provenance": dict(receipt["provenance"]),
        "receipt": {
            "result_sha256": result_sha256,
            "run_id": receipt["run_id"],
            "evidence": receipt["evidence"],
        },
        "tests": counts,
        "skip_reasons": _reason_counts(results, "skipped"),
        "xfail_reasons": _reason_counts(results, "xfailed"),
        "normalization": NORMALIZATION,
    }


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CannotCheck(f"{path.name} is missing") from error
    except (OSError, ValueError) as error:
        raise CannotCheck(f"{path.name} is not readable JSON: {error}") from error
    if not isinstance(payload, dict):
        raise CannotCheck(f"{path.name} is not a JSON object")
    return payload


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(receipt_path: Path, destination: Path, checked_at: str | None = None) -> int:
    """Write the anchor for one green receipt; refuse anything that is not a green run."""
    receipt = _read_json(receipt_path)
    if receipt.get("schema") != RESULT_SCHEMA:
        print(f"CANNOT EXPORT  {receipt_path.name} is not a {RESULT_SCHEMA} receipt")
        return CANNOT_CHECK
    if receipt.get("status") != STATUS_COMPLETE:
        print(f"CANNOT EXPORT  {receipt_path.name} is not a complete run")
        return CANNOT_CHECK
    if receipt.get("exit_code") != 0 or receipt.get("binding_errors"):
        print(
            "CANNOT EXPORT  this run did not pass, so it cannot anchor evidence"
            f" (exit_code {receipt.get('exit_code')!r}, binding {receipt.get('binding_errors')!r})"
        )
        return CANNOT_CHECK
    anchor = build_anchor(
        receipt,
        _digest(receipt_path),
        checked_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(anchor, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"ANCHOR  {destination}")
    print(f"ANCHOR SHA256 {_digest(destination)}")
    print(
        f"ANCHOR  {anchor['tests']['selected']} tests, {anchor['tests']['passed']} passed,"
        f" {anchor['tests']['skipped']} skipped, {anchor['tests']['xfailed']} xfailed;"
        f" nodeid_set_sha256 {anchor['tests']['nodeid_set_sha256']}"
    )
    return AGREE


def _lookup(document: dict, path: tuple[str, ...]):
    value = document
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise CannotCheck(f"missing field {'.'.join(path)}")
        value = value[key]
    return value


def verify(anchor_path: Path, receipt_path: Path) -> int:
    """Report whether one receipt agrees with one anchor; never report a verdict on the run."""
    anchor = _read_json(anchor_path)
    if anchor.get("schema") != ANCHOR_SCHEMA:
        raise CannotCheck(f"{anchor_path.name} is not a {ANCHOR_SCHEMA} anchor")
    receipt = _read_json(receipt_path)
    if receipt.get("schema") != RESULT_SCHEMA:
        raise CannotCheck(f"{receipt_path.name} is not a {RESULT_SCHEMA} receipt")
    if receipt.get("status") != STATUS_COMPLETE:
        raise CannotCheck(f"{receipt_path.name} is not a complete run")
    try:
        provenance = validate_provenance(
            receipt,
            report_path=receipt_path,
            check_all_path=Path(__file__).with_name("check_all.py"),
        )
    except (OSError, ValueError) as error:
        provenance = f"unprovenanced ({error})"
    # Recompute the digests from the receipt itself, so a tampered anchor cannot hide behind a
    # matching field name.
    try:
        tests = receipt["tests"]
        rebuilt = build_anchor(receipt, _digest(receipt_path), anchor.get("checked_at", ""))
    except (KeyError, TypeError, ValueError) as error:
        raise CannotCheck(
            f"{receipt_path.name} is missing a field the anchor compares: {error}"
        ) from error
    mismatches = []
    for path in COMPARED:
        name = ".".join(path)
        try:
            left = _lookup(anchor, path)
            right = _lookup(rebuilt, path)
        except CannotCheck as error:
            mismatches.append(f"{name}: {error}")
            continue
        if left != right:
            mismatches.append(f"{name}: anchor {left!r} != receipt {right!r}")
    same_bytes = anchor.get("receipt", {}).get("result_sha256") == _digest(receipt_path)
    if mismatches:
        for line in mismatches:
            print(f"MISMATCH  {line}")
        print(
            f"AGREEMENT  disagree  ({len(mismatches)} of {len(COMPARED)} fields); provenance {provenance}"
        )
        return DISAGREE
    print(
        f"AGREEMENT  agree  ({len(COMPARED)} fields; {tests['selected']} tests);"
        f" provenance {provenance}; receipt bytes {'identical' if same_bytes else 'different'}"
        f" (a rerun of the same revision is expected to differ)"
    )
    return AGREE


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export", help="write an anchor for one green receipt")
    export_parser.add_argument("receipt", type=Path)
    export_parser.add_argument("destination", type=Path)
    verify_parser = commands.add_parser("verify", help="compare a receipt with an anchor")
    verify_parser.add_argument("anchor", type=Path)
    verify_parser.add_argument("receipt", type=Path)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "export":
            return export(arguments.receipt, arguments.destination)
        return verify(arguments.anchor, arguments.receipt)
    except CannotCheck as error:
        print(f"CANNOT CHECK  {error}")
        return CANNOT_CHECK


if __name__ == "__main__":
    raise SystemExit(main())
