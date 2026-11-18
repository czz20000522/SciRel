"""The rules-status report must not promote an unobserved judge to `pass`.

`tools/docs/rules-inventory.json` says which judge backs each rule. This script
adds the part a stored column cannot: whether the judge runs *today* and what it
returns. The whole value rests on the rollup staying three-state -- a judge that
needed arguments or timed out did not decide anything, so the rule it backs must
not be reported as passing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import rules_status  # noqa: E402


def _script(directory: Path, name: str, body: str) -> str:
    (directory / name).write_text(f"import sys\n{body}\n", encoding="utf-8")
    return name


def test_a_zero_exit_is_a_pass(tmp_path):
    name = _script(tmp_path, "ok.py", "sys.exit(0)")
    assert rules_status.run_judge(name, tmp_path)[0] == "pass"


def test_a_nonzero_exit_is_a_failure_carrying_its_reason(tmp_path):
    name = _script(tmp_path, "bad.py", "sys.stderr.write('contract is wrong\\n'); sys.exit(1)")
    state, detail = rules_status.run_judge(name, tmp_path)
    assert state == "fail"
    assert "contract is wrong" in detail


def test_the_lock_exit_is_not_observed_rather_than_failed(tmp_path):
    """Exit 75 means the judge never got to look, so it cannot be a verdict."""
    name = _script(tmp_path, "locked.py", "sys.exit(75)")
    assert rules_status.run_judge(name, tmp_path)[0] == "not-observed"


def test_a_usage_error_is_not_observed(tmp_path):
    name = _script(tmp_path, "needs_args.py", "sys.exit(2)")
    assert rules_status.run_judge(name, tmp_path)[0] == "not-observed"


def test_a_test_judge_is_reported_as_covered_and_never_as_pass():
    state, _ = rules_status.run_judge("tests/x/test_demo.py::test_case", ROOT)
    assert state == "covered-by-tests"


def test_a_missing_judge_is_not_observed(tmp_path):
    assert rules_status.run_judge("scripts/absent.py", tmp_path)[0] == "not-observed"


def test_a_rule_with_one_unobserved_judge_is_not_reported_as_passing(tmp_path):
    """The rollup is the part that could lie, so it gets its own assertion."""
    name = _script(tmp_path, "locked.py", "sys.exit(75)")
    rules = [{"id": "demo-1", "state": "machine", "judged_by": [name]}]
    report = rules_status.judge_rules(rules, tmp_path)
    assert report == [
        {
            "id": "demo-1",
            "verdict": "not-observed",
            "judges": [
                {"judge": name, "state": "not-observed", "detail": report[0]["judges"][0]["detail"]}
            ],
        }
    ]


def test_a_failing_judge_outranks_a_passing_one(tmp_path):
    ok = _script(tmp_path, "ok.py", "sys.exit(0)")
    bad = _script(tmp_path, "bad.py", "sys.exit(1)")
    rules = [{"id": "demo-2", "state": "machine-partial", "judged_by": [ok, bad]}]
    assert rules_status.judge_rules(rules, tmp_path)[0]["verdict"] == "fail"


def test_unjudged_rules_are_left_out(tmp_path):
    rules = [{"id": "demo-3", "state": "unjudged", "judged_by": []}]
    assert rules_status.judge_rules(rules, tmp_path) == []


def test_the_real_inventory_has_no_failing_judge():
    """This repository's own rules must not be reported as broken."""
    report = rules_status.judge_rules(rules_status.load_rules())
    failing = [item["id"] for item in report if item["verdict"] == "fail"]
    assert failing == []
    assert report, json.dumps(report[:1])
