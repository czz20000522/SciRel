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


def classify(text: str) -> tuple[bool, bool]:
    basis = any(re.search(pattern, text, re.I) for pattern in BASIS_PATTERNS)
    gap = bool(re.search(GAP_PATTERN, text, re.I))
    return basis, gap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", help="only report this asset-domain, e.g. kinetic")
    parser.add_argument("--format", choices=("table", "json"), default="table")
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

    if arguments.format == "json":
        totals = {
            "contracts": len(rows),
            "basis": sum(1 for row in rows if row["basis"]),
            "gap": sum(1 for row in rows if row["gap"]),
            "either": sum(1 for row in rows if row["basis"] or row["gap"]),
            "neither": sum(1 for row in rows if not row["basis"] and not row["gap"]),
        }
        print(json.dumps({"totals": totals, "rows": rows}, indent=1))
        return 0

    per_domain = collections.defaultdict(list)
    for row in rows:
        per_domain[row["domain"]].append(row)
    print(f"{'domain':18s} {'n':>4s} {'basis':>6s} {'gap':>5s} {'neither':>8s}")
    for domain, group in sorted(per_domain.items(), key=lambda item: -len(item[1])):
        basis = sum(1 for row in group if row["basis"])
        gap = sum(1 for row in group if row["gap"])
        neither = sum(1 for row in group if not row["basis"] and not row["gap"])
        print(f"{domain:18s} {len(group):4d} {basis:6d} {gap:5d} {neither:8d}")

    basis = sum(1 for row in rows if row["basis"])
    gap = sum(1 for row in rows if row["gap"])
    neither = [row["asset_id"] for row in rows if not row["basis"] and not row["gap"]]
    print(
        f"\nTOTAL {len(rows)} | basis {basis} | gap {gap} "
        f"| either {len(rows) - len(neither)} | neither {len(neither)}"
    )
    print(
        "NOTE: text match only. 'basis' means the contract says where its independent\n"
        "evidence comes from; it does not prove the claim. 'neither' needs a human\n"
        "decision per contract: name the basis, or record that none was established."
    )
    if neither and arguments.domain is None:
        print("\nneither (first 40):")
        for asset_id in neither[:40]:
            print("  " + asset_id)
    return 1 if neither else 0


if __name__ == "__main__":
    sys.exit(main())
