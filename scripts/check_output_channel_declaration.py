"""Require every single-output contract to state how its value is obtained.

Why this exists
---------------
138 of the 249 contracts declare exactly one output. Of those, the independent
consumer found 14 that say "returned positionally", 5 that name a ``Result``
mapping field, and **119 that say nothing** (``examples/c4-usage-acceptance/
closeout/GAPS.md``). A reader following such a contract cannot tell whether to
write ``result["cross_section_m2"]`` or ``result`` -- so the contract stops being
an interface and becomes a hint.

A single output must say how the caller obtains it. For a file-producing call,
its output description must say both that the data is written to the output file
and that the function returns None. This check does not ask for mapping keys.

What counts as "stated"
-----------------------
A declaration is accepted when any of these fields carries an explicit marker:

    outputs[0].description, outputs[0].dtype, identity, constraints, notes,
    public_api, summary

``POSITIONAL`` markers: "positional", "positionally", "直接返回", "按位置",
"not a field of a mapping", "不是映射里的字段".
``MAPPING`` markers: "result mapping", "Result", "field of the returned",
"mapping 中的字段", "映射中的字段".

The field list is deliberately wider than ``outputs[0].description`` alone: an
earlier consumer audit scanned only ``description`` and misjudged seven contracts
that state the channel elsewhere (``closeout/GAPS.md`` B7). Scanning one field and
reporting "unreadable" is the same failure mode as any other silent observation.

Exit codes are the repository's three states: 0 satisfies, 1 violates,
2 could not observe (missing directory, unparsable contract). 2 is never a pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = Path("catalog/examples")
BASELINE = Path("tools/docs/output-channel-baseline.json")

SCANNED_FIELDS = (
    "outputs[0].description",
    "outputs[0].dtype",
    "identity",
    "constraints",
    "notes",
    "public_api",
    "summary",
)
POSITIONAL = (
    r"positional",
    r"直接返回",
    r"按位置",
    r"not a field of a mapping",
    r"不是映射里的字段",
)
# A Result field is written several ways: "Field ``W_el`` of the returned ``Result``
# mapping", "field of the returned mapping", "映射中的字段". Exact-substring matching
# missed the first form, and broadening it to "mentions mapping anywhere" wrongly
# accepted contracts whose prose merely says "mapping state" or "mapping file".
# These patterns accept the three real phrasings and nothing looser.
MAPPING = (
    r"result mapping",
    r"of the returned\b.{0,40}\bmapping",
    r"field of the returned",
    r"映射(中|里)的字段",
)


def _text(document: dict, path: str) -> str:
    """Return one scanned field as text, tolerating str/dict/list shapes."""
    if path == "outputs[0].description":
        outputs = document.get("outputs") or []
        value = outputs[0] if outputs and isinstance(outputs[0], dict) else {}
        return str(value.get("description") or "")
    if path == "outputs[0].dtype":
        outputs = document.get("outputs") or []
        value = outputs[0] if outputs and isinstance(outputs[0], dict) else {}
        return str(value.get("dtype") or "")
    value = document.get(path.split(".")[0])
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value


def channel_of(document: dict) -> str | None:
    """Return the declared channel, or None if the contract is silent."""
    description = _text(document, "outputs[0].description").lower()
    if "written to the output file" in description and "returns none" in description:
        return "file"
    joined = " ".join(_text(document, field) for field in SCANNED_FIELDS)
    flat = " ".join(joined.replace("`", " ").split()).lower()
    for pattern in POSITIONAL:
        if re.search(pattern, flat):
            return "positional"
    for pattern in MAPPING:
        if re.search(pattern, flat):
            return "mapping"
    # A declaration whose dtype is a mapping/dict already tells the caller the
    # value is one mapping; it still does not name the keys, which is T-2026-1203's
    # question and not this check's.
    dtype = _text(document, "outputs[0].dtype").lower()
    if "mapping" in dtype or dtype.startswith("dict"):
        return "mapping"
    return None


def load_baseline(root: Path) -> dict[str, dict]:
    path = root / BASELINE
    if not path.is_file():
        raise SystemExit(f"missing baseline {BASELINE}: the ratchet needs a starting point")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"unobservable: {BASELINE} is not readable JSON: {error}") from error
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise SystemExit(f"{BASELINE}: 'entries' must be a list")
    out: dict[str, dict] = {}
    for entry in entries:
        asset = entry.get("asset_id")
        reason = entry.get("reason")
        if not asset or not reason:
            raise SystemExit(f"{BASELINE}: every entry needs asset_id and reason: {entry!r}")
        out[str(asset)] = entry
    return out


def inspect(root: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (violations, stale_baseline, observed) for the whole catalog."""
    directory = root / CATALOG
    if not directory.is_dir():
        raise SystemExit(f"unobservable: {CATALOG} is not a directory")
    baseline = load_baseline(root)
    violations: list[str] = []
    observed: list[str] = []
    states: dict[str, bool] = {}
    for path in sorted(directory.glob("scirel.*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SystemExit(f"unobservable: {path.name} is not readable JSON: {error}") from error
        asset = str(document.get("asset_id") or path.stem)
        outputs = document.get("outputs") or []
        if len(outputs) != 1:
            continue
        stated = channel_of(document) is not None
        observed.append(asset)
        states[asset] = stated
        if stated or asset in baseline:
            continue
        violations.append(asset)
    # A baseline entry is stale when its contract is gone, or when the contract now
    # states its channel. Both mean the fix must delete the entry in the same commit,
    # which is what puts the removal into the diff.
    stale = sorted(asset for asset in baseline if asset not in states or states[asset])
    return violations, stale, observed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        violations, stale, observed = inspect(root)
    except SystemExit as stop:
        print(str(stop), file=sys.stderr)
        return 2
    if violations:
        print(
            f"{len(violations)} single-output contract(s) do not state how the value is obtained:"
        )
        for asset in violations:
            print(f"  {asset}")
    if stale:
        print(
            f"{len(stale)} baseline entr(ies) are stale (fixed or gone); delete them in this commit:"
        )
        for asset in stale:
            print(f"  {asset}")
    if violations or stale:
        return 1
    print(
        f"output channel: {len(observed)} single-output contracts, all state their channel "
        f"({len(load_baseline(root))} baselined)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
