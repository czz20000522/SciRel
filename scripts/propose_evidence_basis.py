"""Print a migration worksheet for contracts that do not declare `verification.basis` yet.

Why this exists
---------------
Filling `verification.basis` for 249 contracts means reading each contract's
verification text. Doing that by hand from scratch is slow; doing it by regex is
dishonest -- the phrase list already misses 106 assets and cannot tell a basis from
a limitation. This tool therefore does the one thing that is both fast and safe: it
shows the reader the evidence, so the field is written from the text rather than
from a pattern.

For each pending asset it prints:

* the sentences that mention any basis phrase (the candidate claims);
* the sentences that mention an evidence ceiling or known limitation (the claims
  that must NOT be read as a basis);
* when no basis phrase matches, **the whole verification block**, because 87 pending
  assets phrase their basis in wording the recogniser does not know;
* the tests the contract names, which is where the `source` should point;
* the phrase that matched, as a hint for `kind` -- a hint, not an answer.

It writes nothing. The migration is a reading task; this only makes the reading
small enough to do in batches.

Usage:
    PYTHONPATH=src python3 -B scripts/propose_evidence_basis.py --limit 8
    PYTHONPATH=src python3 -B scripts/propose_evidence_basis.py --asset scirel.field.brb

Exit status: 0 printed, 2 could not read the catalog.
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
from c1_evidence_coverage import BASIS_PATTERNS  # noqa: E402

SENTENCE = re.compile(r"(?<=[.;])\s+")
LIMIT_WORDS = re.compile(
    r"cannot establish|cannot be established|does not establish|not establish|"
    r"no basis|not verified|unverified|UNKNOWN|limitation|ceiling",
    re.I,
)


def sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE.split(" ".join(text.split())) if part.strip()]


def worksheet(asset: str, root: Path) -> dict:
    document = json.loads((root / CATALOG / f"{asset}.json").read_text(encoding="utf-8"))
    verification = document["verification"]
    text = " ".join(
        [
            " ".join(verification.get("scope") or []),
            " ".join(verification.get("known_limitations") or []),
            str(verification.get("evidence_ceiling") or ""),
        ]
    )
    parts = sentences(text)
    claims, limits = [], []
    for sentence in parts:
        if any(re.search(pattern, sentence, re.I) for pattern in BASIS_PATTERNS):
            claims.append(sentence)
        if LIMIT_WORDS.search(sentence):
            limits.append(sentence)
    phrases = sorted(
        {match.group(0) for pattern in BASIS_PATTERNS for match in re.finditer(pattern, text, re.I)}
    )
    return {
        "asset": asset,
        "claims": claims,
        "all_sentences": parts,
        "limits": limits,
        "tests": verification.get("tests") or [],
        "matched_phrases": phrases,
        "evidence_ceiling": verification.get("evidence_ceiling") or "",
    }


def pending(root: Path) -> list[str]:
    baseline = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    return [entry["asset_id"] for entry in baseline["entries"]]


def render(record: dict) -> str:
    lines = [f"=== {record['asset']}"]
    if record["matched_phrases"]:
        lines.append(f"  matched: {', '.join(record['matched_phrases'])}")
    if record["claims"]:
        lines.append("  claims (may support a basis):")
        lines.extend(f"    - {sentence}" for sentence in record["claims"])
    elif record["all_sentences"]:
        # Measured on this catalog: 87 pending assets phrase their basis in wording the
        # recogniser does not know ("independent analytic and independent discrete-reference
        # comparisons"), so an empty claim list would hide exactly what the reader needs.
        # Print the whole block instead of a suggestion to go look elsewhere.
        lines.append("  claims: none recognised -- full verification block follows:")
        lines.extend(f"    - {sentence}" for sentence in record["all_sentences"])
    else:
        lines.append("  claims: none recognised and the verification block is empty")
    if record["limits"]:
        lines.append("  limits (must NOT be read as a basis):")
        lines.extend(f"    - {sentence}" for sentence in record["limits"])
    if record["evidence_ceiling"]:
        lines.append(f"  ceiling: {record['evidence_ceiling']}")
    if record["tests"]:
        lines.append(f"  tests: {', '.join(record['tests'][:3])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", help="one asset id")
    parser.add_argument("--limit", type=int, default=8, help="how many pending assets to show")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        assets = [args.asset] if args.asset else pending(root)[: args.limit]
        records = [worksheet(asset, root) for asset in assets]
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as error:
        print(f"unobservable: {error}", file=sys.stderr)
        return 2
    print("\n\n".join(render(record) for record in records))
    print(
        "\nWrite the field from these sentences, not from the matched phrase. "
        "`kind` follows from what the claim actually is."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
