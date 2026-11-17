"""Answer one question per asset: does this capability stand on evidence, or on a recorded gap?

Why this exists
---------------
``c1_evidence_coverage`` prints domain totals. That answers "how many", not "which
one, and what exactly does its contract claim". Someone asking "is this capability
proven correct?" needs the asset's own sentence and where it lives, not a count.

What it does
------------
Reads one contract and reports its verification state with the text that produced
that state and a pointer to the file:

    basis   the contract asserts a basis (literature, analytic identity, upstream
            behaviour, measured comparison). This says the contract *claims* a
            basis; it is not a verdict that the basis is sound.
    gap     the contract records that no basis was established, or states an
            evidence ceiling / known limitation. **This is not proof.** It is an
            honest record of what is missing.
    neither both absent: the contract does not say.

The classification is the same code the coverage report uses (``classify``), so the
two can never disagree; this script only adds per-asset detail and provenance.

**``gap`` means "no basis phrase was recognised", not "no evidence exists".** The
recogniser is a fixed phrase list (``BASIS_PATTERNS``); a contract that says
"compared with independent Gauss-Legendre quadrature" is not in it and lands in
``gap`` even though it asserts a comparison. So this script also reports
``weak_basis_phrases``: un-negated words that usually signal a basis but that the
list does not recognise. That field is a **lead, not a verdict** -- it tells a reader
where to look, and ``--scan-weak-basis`` aggregates it over the catalog.

Usage:
    PYTHONPATH=src python3 -B scripts/evidence_status.py --asset scirel.field.brb
    PYTHONPATH=src python3 -B scripts/evidence_status.py --asset scirel.field.brb --format json

Exit status: 0 the asset was found and classified, 2 the asset could not be read
(unknown id, unparsable contract). There is no "pass/fail" here -- this reports what
the contract says, it does not judge it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path("catalog/examples")
BASELINE = Path("tools/docs/evidence-basis-baseline.json")

sys.path.insert(0, str(ROOT / "scripts"))
from c1_evidence_coverage import NEGATION, classify, verification_text  # noqa: E402

VERDICT = {
    "basis": "contract asserts a basis (claim recorded; not an audit of that basis)",
    "gap": "not recognised as a basis -- NOT proof either way; read the text",
    "neither": "neither a recognised basis nor a gap phrase is present",
}

# Un-negated wording that usually signals a basis but is not in BASIS_PATTERNS.
WEAK_BASIS = re.compile(
    r"independent|compared with|comparison|verif(?:y|ies|ied)|published|literature|"
    r"textbook|benchmark|reference values|quadrature|against the|agrees? with",
    re.I,
)


def contract_path(asset: str, root: Path = ROOT) -> Path | None:
    path = root / CATALOG / f"{asset}.json"
    return path if path.is_file() else None


def describe(asset: str, root: Path = ROOT) -> dict:
    path = contract_path(asset, root)
    if path is None:
        raise FileNotFoundError(f"no contract for {asset} under {CATALOG}")
    document = json.loads(path.read_text(encoding="utf-8"))
    text = verification_text(document)
    asserted, gap = classify(text)
    weak = []
    for match in WEAK_BASIS.finditer(text):
        prefix = text[max(0, match.start() - 40) : match.start()]
        if re.search(NEGATION, prefix):
            continue
        weak.append(match.group(0).lower())
    weak = sorted(set(weak))
    state = "basis" if asserted and not gap else "gap" if gap else "neither"
    return {
        "asset": asset,
        "source": path.relative_to(root).as_posix(),
        "domain": asset.split(".")[1] if asset.count(".") >= 2 else "",
        "state": state,
        "verdict": VERDICT[state],
        "basis_asserted": asserted,
        "gap_recorded": gap,
        "claims_basis": bool(asserted),
        "weak_basis_phrases": weak,
        "verification_scope": document["verification"].get("scope") or [],
        "known_limitations": document["verification"].get("known_limitations") or [],
        "evidence_ceiling": document["verification"].get("evidence_ceiling") or "",
    }


def summary(root: Path = ROOT) -> dict:
    """Count what each contract claims, without ever summing gaps into 'proven'."""
    baseline = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    pending = {entry["asset_id"] for entry in baseline["entries"]}
    by_kind: dict[str, int] = {}
    total = 0
    for path in sorted((root / CATALOG).glob("scirel.*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        total += 1
        basis = (document.get("verification") or {}).get("basis")
        kind = basis.get("kind") if basis else "not-declared"
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "contracts": total,
        "declared": sum(count for kind, count in by_kind.items() if kind != "not-declared"),
        "by_kind": dict(sorted(by_kind.items())),
        "pending": len(pending),
        "note": (
            "kind=none records a gap; it is not proof. not-declared means the contract has no "
            "verification.basis yet, so nothing is claimed either way."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", help="asset id, e.g. scirel.field.brb")
    parser.add_argument(
        "--scan-weak-basis",
        action="store_true",
        help="list assets that are not classified as basis but do contain un-recognised basis wording",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="count contracts by declared basis kind, keeping 'none' and 'not-declared' separate",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.summary:
        try:
            counts = summary(root)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"unobservable: {error}", file=sys.stderr)
            return 2
        if args.format == "json":
            print(json.dumps(counts, ensure_ascii=False, indent=2))
        else:
            print(f"contracts: {counts['contracts']}")
            for kind, count in counts["by_kind"].items():
                print(f"  {kind:28s} {count}")
            print(f"\n{counts['note']}")
        return 0
    if args.scan_weak_basis:
        found = []
        for path in sorted((root / CATALOG).glob("scirel.*.json")):
            try:
                record = describe(path.stem, root)
            except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
                print(f"unobservable: {error}", file=sys.stderr)
                return 2
            if record["state"] != "basis" and record["weak_basis_phrases"]:
                found.append(record)
        print(
            f"{len(found)} asset(s) are not classified as basis but do contain "
            f"un-recognised basis wording"
        )
        for record in found:
            print(
                f"  [{record['state']:7s}] {record['asset']}  "
                f"-> {', '.join(record['weak_basis_phrases'][:4])}"
            )
        print(
            "\nThis is a lead, not a verdict: read each contract's verification text "
            "before changing any count."
        )
        return 0
    if not args.asset:
        print(
            "unobservable: --asset is required unless --scan-weak-basis is given", file=sys.stderr
        )
        return 2
    try:
        record = describe(args.asset, root)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        print(f"unobservable: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    print(f"{record['asset']}")
    print(f"  state    {record['state']}")
    print(f"  verdict  {record['verdict']}")
    print(f"  source   {record['source']}")
    if record["verification_scope"]:
        print("  scope:")
        for line in record["verification_scope"]:
            print(f"    - {line}")
    if record["known_limitations"]:
        print("  known_limitations:")
        for line in record["known_limitations"]:
            print(f"    - {line}")
    if record["evidence_ceiling"]:
        print(f"  evidence_ceiling: {record['evidence_ceiling']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
