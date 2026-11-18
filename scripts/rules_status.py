#!/usr/bin/env python3
"""Report, per inventory rule, whether its judges run and what they return now.

The inventory says *which* judge backs a rule. It cannot say whether that judge
still runs today, and a stored "passing" column would be a claim that goes stale
the moment anyone edits a contract. So nothing here is stored: the report
executes the judges and prints a three-state result.

* ``pass``          -- the judge ran and returned 0.
* ``fail``          -- the judge ran and returned another code.
* ``not-observed``  -- the judge did not produce a verdict: it needs arguments,
  timed out, or returned the repository's "no lock" exit code 75.

A test judge is reported as ``covered-by-tests``: the acceptance plan runs
``pytest tests`` wholesale, so it executes there and cannot be run in isolation
here without duplicating the plan. That label is deliberately not ``pass`` --
this script never witnessed that run.

Nothing is aggregated upward: a rule is ``pass`` only when every judge passed or
was covered, and a single ``not-observed`` keeps the rule out of ``pass``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
INVENTORY = REPOSITORY / "tools" / "docs" / "rules-inventory.json"
LOCK_HELD = 75
USAGE_ERROR = 2
TIMEOUT_SECONDS = 300
# Judges whose entry point needs a target on the command line. Kept here rather than in the
# inventory so the inventory stays a list of *which* judge decides a rule, not of how to call it.
JUDGE_ARGUMENTS = {
    "scripts/validate_asset_documents.py": ["catalog/examples"],
    "scripts/dev.py": ["run", "ruff", "check", "."],
    "scripts/tickets.py": ["check", "tickets"],
    "scripts/evidence_status.py": ["--summary"],
}


def load_rules(path: Path = INVENTORY) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["rules"]


def run_judge(judge: str, repository: Path) -> tuple[str, str]:
    """Run one judge and return ``(state, detail)`` without inventing a verdict."""
    if judge.startswith("tests/"):
        return "covered-by-tests", "the acceptance plan runs `pytest tests`"
    script = repository / judge
    if not script.exists():
        return "not-observed", f"{judge} does not exist"
    # Inherit the caller environment: a judge such as `dev.py` needs `uv` on PATH, and a
    # stripped PATH would report its absence as a rule failure rather than a missing tool.
    environment = {**os.environ, "PYTHONPATH": str(repository / "src")}
    try:
        with tempfile.TemporaryDirectory() as scratch:
            completed = subprocess.run(
                [sys.executable, "-B", str(script), *JUDGE_ARGUMENTS.get(judge, [])],
                capture_output=True,
                text=True,
                cwd=repository,
                env={**environment, "TMPDIR": scratch},
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
    except subprocess.TimeoutExpired:
        return "not-observed", f"timed out after {TIMEOUT_SECONDS}s"
    if completed.returncode == 0:
        return "pass", ""
    if completed.returncode == LOCK_HELD:
        return "not-observed", "did not acquire the repository lock (exit 75)"
    if completed.returncode == USAGE_ERROR:
        first = (completed.stderr or "").strip().splitlines()[:1]
        return "not-observed", f"needs arguments: {first[0] if first else 'usage error'}"
    first = (completed.stderr or completed.stdout or "").strip().splitlines()[:1]
    return "fail", f"exit {completed.returncode}: {first[0] if first else ''}".strip()


def judge_rules(rules: list[dict], repository: Path = REPOSITORY) -> list[dict]:
    """Attach a per-rule verdict built only from what actually ran."""
    report = []
    for rule in rules:
        if rule.get("state") == "unjudged":
            continue
        results = [
            {"judge": judge, "state": state, "detail": detail}
            for judge, (state, detail) in ((j, run_judge(j, repository)) for j in rule["judged_by"])
        ]
        states = {item["state"] for item in results}
        if "fail" in states:
            verdict = "fail"
        elif states <= {"pass", "covered-by-tests"}:
            verdict = "pass"
        else:
            verdict = "not-observed"
        report.append({"id": rule["id"], "verdict": verdict, "judges": results})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    arguments = parser.parse_args(argv)

    report = judge_rules(
        load_rules(arguments.repository / "tools/docs/rules-inventory.json"), arguments.repository
    )
    if arguments.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for item in report:
            print(f"{item['verdict'].ljust(13)} {item['id']}")
            for judge in item["judges"]:
                detail = f"  ({judge['detail']})" if judge["detail"] else ""
                print(f"    {judge['state'].ljust(17)} {judge['judge']}{detail}")
    counts = {
        state: sum(1 for item in report if item["verdict"] == state)
        for state in ("pass", "fail", "not-observed")
    }
    print(
        f"\n{len(report)} judged rules: pass {counts['pass']}, fail {counts['fail']}, "
        f"not-observed {counts['not-observed']}"
    )
    print("not-observed is not a pass; a rule stays out of `pass` until every judge returns 0.")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
