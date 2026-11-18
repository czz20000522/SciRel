#!/usr/bin/env python3
"""Report the four engineering-constraint criteria from tracked artifacts only.

Each criterion is answered with one of three states: ``pass``, ``fail`` or
``not-observed``. Nothing is inferred from a claim, and a criterion no tracked
artifact can decide is printed as ``not-observed`` with the reason -- never as
``pass`` because the surrounding ones are green.

1. *rules inventory* -- ``tools/docs/rules-inventory.json`` parses, every rule
   carries the fields its state requires, and every judge the inventory cites is
   reached by the acceptance plan (directly, or through a test that imports it).
2. *judges completed* -- every ``unjudged`` rule states why it cannot be judged
   and who guarantees it instead, which is the only honest form of "done" for a
   rule no machine can decide.
3. *evidence queryable* -- every public contract declares
   ``verification.basis`` and the ratchet baseline is empty, so a contract cannot
   stay silent about what it is based on.
4. *PR integration* -- **not observable from the tree**: the receipt lives in the
   pull request and the acceptance output, so this script refuses to score it and
   says where to look instead.

This is a reporting tool, not a gate. The gates it summarises run in the
acceptance plan; ``pass`` here means the tracked artifacts agree with each other,
not that the suite ran during this call.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
INVENTORY = "tools/docs/rules-inventory.json"
BASELINE = "tools/docs/evidence-basis-baseline.json"
CATALOG = "catalog/examples"
PLAN = "skills/development/scirel-acceptance/scripts/check_all.py"
REQUIRED_FIELDS = {
    "machine": ("judged_by", "judges"),
    "machine-partial": ("judged_by", "judges", "does_not_judge"),
    "unjudged": ("why", "who"),
}


def _wired(judge: str, plan: str, test_texts: dict[str, str]) -> bool:
    path = judge.split("::")[0]
    if path.startswith("tests/"):
        return True
    if path in plan:
        return True
    stem = Path(path).stem
    return any(re.search(rf"\b{re.escape(stem)}\b", text) for text in test_texts.values())


def criterion_rules(root: Path) -> tuple[str, list[str]]:
    """Every rule carries the fields its state requires, and its judges are wired."""
    inventory = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    plan = (root / PLAN).read_text(encoding="utf-8")
    test_texts = {
        p.as_posix(): p.read_text(encoding="utf-8") for p in (root / "tests").rglob("*.py")
    }
    problems = []
    for rule in inventory["rules"]:
        state = rule.get("state")
        if state not in REQUIRED_FIELDS:
            problems.append(f"{rule.get('id')}: unknown state {state!r}")
            continue
        for field in REQUIRED_FIELDS[state]:
            if not rule.get(field):
                problems.append(f"{rule.get('id')}: {state} needs {field}")
        for judge in rule.get("judged_by") or []:
            if not _wired(judge, plan, test_texts):
                problems.append(f"{rule.get('id')}: judge {judge} is not reached by the plan")
    return ("fail" if problems else "pass"), problems


def criterion_unjudged(root: Path) -> tuple[str, list[str]]:
    """A rule no machine can decide must still say why and who guarantees it."""
    inventory = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    problems = []
    for rule in inventory["rules"]:
        if rule.get("state") != "unjudged":
            continue
        for field in ("why", "who"):
            text = str(rule.get(field) or "").strip()
            if len(text) < 20:
                problems.append(f"{rule.get('id')}: {field} is missing or too short to be a reason")
    return ("fail" if problems else "pass"), problems


def criterion_evidence(root: Path) -> tuple[str, list[str]]:
    """Every public contract names its basis, and the ratchet baseline is empty."""
    problems = []
    directory = root / CATALOG
    if not directory.is_dir():
        return "not-observed", [f"{CATALOG} does not exist"]
    for path in sorted(directory.glob("scirel.*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if (document.get("verification") or {}).get("basis") is None:
            problems.append(f"{path.stem}: no verification.basis")
    baseline_path = root / BASELINE
    if baseline_path.exists():
        for entry in json.loads(baseline_path.read_text(encoding="utf-8")).get("entries") or []:
            problems.append(f"{entry.get('asset_id')}: still baselined")
    return ("fail" if problems else "pass"), problems


def report(root: Path = REPOSITORY) -> list[dict]:
    """Score the three tree-decidable criteria and name the fourth as unobservable."""
    results = []
    for name, function in (
        ("rules inventory is complete and its judges are wired", criterion_rules),
        ("unjudged rules explain why and who guarantees them", criterion_unjudged),
        ("every public contract declares its basis", criterion_evidence),
    ):
        state, problems = function(root)
        results.append(
            {
                "criterion": name,
                "state": state,
                "problems": problems[:10],
                "problem_count": len(problems),
            }
        )
    results.append(
        {
            "criterion": "each batch merged with an exclusive check",
            "state": "not-observed",
            "problems": [
                "the receipt lives in the pull request and the acceptance output, not in the tree; "
                "run `python3 scripts/dev.py check` and read EXCLUSIVE, steps and RESULT SHA256"
            ],
            "problem_count": 0,
        }
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    arguments = parser.parse_args(argv)
    results = report(arguments.repository)
    if arguments.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for result in results:
            print(f"{result['state'].ljust(13)} {result['criterion']}")
            for problem in result["problems"]:
                print(f"    - {problem}")
        states = {result["state"] for result in results}
        verdict = (
            "fail"
            if "fail" in states
            else "no failure"
            if "not-observed" not in states
            else "no failure, but 1 criterion is not machine-observable"
        )
        print(f"\n{verdict}")
        print("not-observed is not a pass.")
    return 1 if any(result["state"] == "fail" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
