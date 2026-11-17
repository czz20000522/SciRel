"""Require every contract to declare its evidence basis as data, not as prose.

Why this exists
---------------
``c1_evidence_coverage`` guesses "is there a basis?" from prose with a fixed phrase
list. Measured on this catalog, 106 assets that the phrase list does not recognise do
contain basis wording it simply does not know. The consequence is that the coverage
numbers cannot answer "which capability stands on evidence" -- they answer "which
prose matched a regex".

So the basis becomes a field: ``verification.basis = {kind, statement, source?}``.
This checker keeps that field honest for new work and does not retro-fit old work by
guessing:

* a contract that declares ``basis`` must use a known ``kind`` and a non-empty
  ``statement``;
* ``kind: none`` must be accompanied by a recorded ceiling or a known limitation --
  "no basis" is a claim that has to say what is missing;
* a contract that declares nothing must be listed in
  ``tools/docs/evidence-basis-baseline.json`` (the not-yet-migrated set, only shrinks);
* a baseline entry whose contract now declares ``basis`` is stale and must be deleted
  in the same commit, so the removal shows up in the diff.

What this does NOT do: it does not judge whether a declared basis is sound. That is
the reviewer's job; the field only makes the claim exist and be queryable.

Exit status is the repository's three states: 0 satisfies, 1 violates, 2 could not
observe (missing catalog, unreadable contract, broken baseline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = Path("catalog/examples")
BASELINE = Path("tools/docs/evidence-basis-baseline.json")

KINDS = frozenset(
    {
        "analytic-identity",
        "closed-form",
        "literature",
        "upstream-behaviour",
        "measured-comparison",
        "independent-recomputation",
        "specification",
        "none",
    }
)


def load_baseline(root: Path) -> dict[str, dict]:
    path = root / BASELINE
    if not path.is_file():
        raise SystemExit(f"unobservable: missing {BASELINE}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"unobservable: {BASELINE} is not readable JSON: {error}") from error
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise SystemExit(f"unobservable: {BASELINE} has no 'entries' list")
    out: dict[str, dict] = {}
    for entry in entries:
        asset = entry.get("asset_id")
        if not asset or not entry.get("reason"):
            raise SystemExit(f"unobservable: baseline entry needs asset_id and reason: {entry!r}")
        out[str(asset)] = entry
    return out


def problems_for(document: dict) -> list[str]:
    """Return the reasons this contract's basis declaration is unacceptable."""
    verification = document.get("verification") or {}
    basis = verification.get("basis")
    if basis is None:
        return []
    problems = []
    kind = basis.get("kind")
    if kind not in KINDS:
        problems.append(f"unknown basis kind {kind!r}")
    if not str(basis.get("statement") or "").strip():
        problems.append("basis.statement is empty")
    if kind == "none":
        ceiling = str(verification.get("evidence_ceiling") or "").strip()
        limitations = verification.get("known_limitations") or []
        if not ceiling and not limitations:
            problems.append(
                "kind=none must record what is missing (evidence_ceiling or known_limitations)"
            )
    return problems


def inspect(root: Path) -> tuple[list[str], list[str], list[str], int]:
    directory = root / CATALOG
    if not directory.is_dir():
        raise SystemExit(f"unobservable: {CATALOG} is not a directory")
    baseline = load_baseline(root)
    violations: list[str] = []
    stale: list[str] = []
    declared: list[str] = []
    total = 0
    for path in sorted(directory.glob("scirel.*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SystemExit(f"unobservable: {path.name} is not readable JSON: {error}") from error
        asset = str(document.get("asset_id") or path.stem)
        total += 1
        has_basis = (document.get("verification") or {}).get("basis") is not None
        for problem in problems_for(document):
            violations.append(f"{asset}: {problem}")
        if has_basis:
            declared.append(asset)
            if asset in baseline:
                stale.append(asset)
        elif asset not in baseline:
            violations.append(f"{asset}: declares no verification.basis and is not in the baseline")
    known = {str(path.stem) for path in directory.glob("scirel.*.json")}
    stale.extend(sorted(asset for asset in baseline if asset not in known))
    return violations, sorted(set(stale)), declared, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        violations, stale, declared, total = inspect(root)
    except SystemExit as stop:
        print(str(stop), file=sys.stderr)
        return 2
    if violations:
        print(f"{len(violations)} contract(s) do not declare an acceptable evidence basis:")
        for line in violations:
            print(f"  {line}")
    if stale:
        print(
            f"{len(stale)} baseline entr(ies) are stale (contract now declares a basis, or is gone); "
            "delete them in this commit:"
        )
        for asset in stale:
            print(f"  {asset}")
    if violations or stale:
        return 1
    print(
        f"evidence basis: {len(declared)}/{total} contracts declare verification.basis "
        f"({len(load_baseline(root))} still baselined)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
