#!/usr/bin/env python3
"""Report how many contracts state an independent basis or a documented gap.

This is a **tracking aid**, not a gate and not evidence by itself.  The C1 work
in #249 asks every public contract to say, in its own ``verification`` block,
either where an independent basis comes from (a published relation, an analytic
identity, an exact-rational or high-precision recomputation, a counterexample
that refuted a claim) or that no basis could be established.  Whether that
statement is *true* is a review question; this script only reports whether the
text is there, so that the count in the closeout record can be reproduced by
anyone instead of being quoted from a conversation.

Three outcomes per contract:

``basis``     the verification text names a source of independent evidence.
``gap``       it records that no basis could be established (``cannot
              establish`` / ``UNKNOWN``).
``neither``   it only describes observed behaviour, so a reader cannot tell
              whether any independent basis exists.

A contract may be both ``basis`` and ``gap``: part of the relation is
established and part is not.  The patterns are intentionally narrow English
phrasings plus ``独立依据``; a batch that invents new wording will show up as
``neither`` until its wording is either added here or rewritten.  That is the
intended failure mode -- it keeps the number honest.

Usage::

    python scripts/c1_evidence_coverage.py
    python scripts/c1_evidence_coverage.py --domain kinetic
    python scripts/c1_evidence_coverage.py --format json
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BASIS_PATTERNS = (
    r"independent (engine|oracle|reference|implementation|recomputation|high[- ]precision|expression|check)",
    r"independently (recomput|derived|verified|evaluated)",
    r"analytic(al)? (identity|solution|expression)",
    r"closed[- ]form",
    r"exact (rational|arithmetic|recomputation|recovery)",
    r"\bFraction\b|\bDecimal\(|mpmath|digit reference",
    r"counterexample|refuted|disproved",
    r"moment identit|Gram matrix|Kramers",
    r"独立依据",
)
GAP_PATTERN = r"cannot establish|cannot be established|\bUNKNOWN\b"


def verification_text(contract: dict) -> str:
    block = contract["verification"]
    parts = [
        " ".join(block.get("scope", [])),
        " ".join(block.get("known_limitations", [])),
        str(block.get("evidence_ceiling", "")),
    ]
    return " ".join(parts)


NEGATION = re.compile(
    r"(?:\bno\b|\bnot\b|\bnever\b|\bwithout\b|\bneither\b|\bnor\b|\blacks?\b|"
    r"\babsent\b|\bisn't\b|\bdoesn't\b|\bdoes not\b|\bcannot\b|\bno longer\b)",
    re.I,
)
CLAUSE_BREAK = re.compile(r"[.;:,]|\bbut\b|\bhowever\b|\balthough\b", re.I)


POST_NEGATION = re.compile(
    r"\b(?:is|are|was|were)\s+not\s+(?:used|available|present|performed|possible)\b|"
    r"\b(?:does|do|did)\s+not\s+exist\b|\bcannot\s+be\s+used\b",
    re.I,
)


def _is_negated(text: str, start: int, end: int = 0) -> bool:
    """Negation may precede the match ("no independent X") or follow it
    ("X is not used"), so both directions are checked inside the same clause."""
    """Return True when the match starting at ``start`` sits under a negation.

    A contract that says "no independent implementation exists" is recording a
    gap, not a basis; counting it as evidence would inflate the very number this
    report exists to keep honest. The window walks back to the nearest clause
    break so a negation in an earlier clause is not borrowed.
    """
    window_start = 0
    for break_match in CLAUSE_BREAK.finditer(text, 0, start):
        window_start = break_match.end()
    if NEGATION.search(text, window_start, start):
        return True
    if end:
        following = CLAUSE_BREAK.search(text, end)
        window_end = following.start() if following else min(len(text), end + 40)
        return bool(POST_NEGATION.search(text, end, window_end))
    return False


def classify(text: str) -> tuple[bool, bool]:
    asserted = False
    negated = False
    for pattern in BASIS_PATTERNS:
        for match in re.finditer(pattern, text, re.I):
            if _is_negated(text, match.start(), match.end()):
                negated = True
            else:
                asserted = True
    gap = bool(re.search(GAP_PATTERN, text, re.I)) or (negated and not asserted)
    return asserted, gap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", help="only report this asset-domain, e.g. kinetic")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument(
        "--fail-on-neither",
        action="store_true",
        help="exit 1 when any contract records neither a basis nor a gap (CI use)",
    )
    arguments = parser.parse_args()

    rows = []
    for path in sorted(glob.glob(str(ROOT / "catalog/examples/scirel.*.json"))):
        contract = json.loads(Path(path).read_text(encoding="utf-8"))
        asset_id = contract["asset_id"]
        domain = asset_id.split(".")[1]
        if arguments.domain and domain != arguments.domain:
            continue
        basis, gap = classify(verification_text(contract))
        rows.append({"asset_id": asset_id, "domain": domain, "basis": basis, "gap": gap})

    totals = {
        "contracts": len(rows),
        "basis": sum(1 for row in rows if row["basis"]),
        "gap": sum(1 for row in rows if row["gap"]),
        "either": sum(1 for row in rows if row["basis"] or row["gap"]),
        "neither": sum(1 for row in rows if not row["basis"] and not row["gap"]),
    }
    neither = [row["asset_id"] for row in rows if not row["basis"] and not row["gap"]]
    disclaimer = (
        "Text match only, not a gate. 'basis' means the contract says where its "
        "independent evidence comes from; it does not prove the claim. 'neither' "
        "needs a human decision per contract: name the basis, or record that none "
        "was established."
    )
    if arguments.format == "json":
        print(
            json.dumps(
                {
                    "totals": totals,
                    "gate": False,
                    "note": disclaimer,
                    "neither": neither,
                    "rows": rows,
                },
                indent=1,
            )
        )
        return 1 if (arguments.fail_on_neither and neither) else 0

    per_domain = collections.defaultdict(list)
    for row in rows:
        per_domain[row["domain"]].append(row)
    print(f"{'domain':18s} {'n':>4s} {'basis':>6s} {'gap':>5s} {'neither':>8s}")
    for domain, group in sorted(per_domain.items(), key=lambda item: -len(item[1])):
        basis_count = sum(1 for row in group if row["basis"])
        gap_count = sum(1 for row in group if row["gap"])
        neither_count = sum(1 for row in group if not row["basis"] and not row["gap"])
        print(f"{domain:18s} {len(group):4d} {basis_count:6d} {gap_count:5d} {neither_count:8d}")

    print(
        f"\nTOTAL {totals['contracts']} | basis {totals['basis']} | gap {totals['gap']} "
        f"| either {totals['either']} | neither {totals['neither']}"
    )
    for line in textwrap.wrap("NOTE: " + disclaimer, 88):
        print(line)
    if neither:
        print(f"\nneither ({len(neither)}):")
        for asset_id in neither[:40]:
            print("  " + asset_id)
        if len(neither) > 40:
            print(f"  ... and {len(neither) - 40} more")
    return 1 if (arguments.fail_on_neither and neither) else 0


if __name__ == "__main__":
    sys.exit(main())
