"""Keep `tools/docs/rules-inventory.json` honest.

The inventory exists because a rule written only in prose is not enforced -- an
agent can read it and still not follow it, and nothing goes red. Listing which
rules have a machine judge is only useful if the list cannot quietly rot, so:

* every `judged_by` target must exist (a script file, or `file::test_name`);
* every `anchor` must still appear in its source document (a renamed or deleted
  rule makes the inventory red instead of silently describing a rule that is gone);
* a rule marked `machine` or `machine-partial` must say what it judges, and a
  `machine-partial` one must also say what it does **not** judge -- a partial
  judge that reads as complete is worse than no judge;
* a rule marked `unjudged` must say why it cannot be judged and who guarantees it.

That last pair is the point: the inventory distinguishes "enforced" from
"explained", and neither may masquerade as the other.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "tools" / "docs" / "rules-inventory.json"
STATES = {"machine", "machine-partial", "unjudged"}


def _load() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def _rules() -> list[dict]:
    return _load()["rules"]


def test_the_inventory_parses_and_covers_a_known_slice():
    document = _load()
    assert document["schema"] == "scirel.rules-inventory.v1"
    rules = document["rules"]
    assert rules, "an empty inventory would read as 'nothing to enforce'"
    ids = [rule["id"] for rule in rules]
    assert len(ids) == len(set(ids)), f"duplicate rule ids: {ids}"


def test_every_rule_declares_one_of_the_three_states():
    for rule in _rules():
        assert rule["state"] in STATES, f"{rule['id']}: state {rule['state']!r}"


@pytest.mark.parametrize("rule", _rules(), ids=lambda rule: rule["id"])
def test_a_machine_judge_names_what_it_judges(rule: dict) -> None:
    if rule["state"] == "unjudged":
        pytest.skip("unjudged rules are covered by the next test")
    assert rule.get("judged_by"), f"{rule['id']}: machine state needs judged_by"
    assert rule.get("judges"), f"{rule['id']}: machine state needs a `judges` sentence"
    if rule["state"] == "machine-partial":
        assert rule.get("does_not_judge"), (
            f"{rule['id']}: a partial judge must say what it does NOT judge, "
            "otherwise it reads as complete"
        )


@pytest.mark.parametrize("rule", _rules(), ids=lambda rule: rule["id"])
def test_an_unjudged_rule_says_why_and_who(rule: dict) -> None:
    if rule["state"] != "unjudged":
        pytest.skip("judged rules are covered by the previous test")
    assert rule.get("why"), f"{rule['id']}: unjudged needs a reason"
    assert rule.get("who"), f"{rule['id']}: unjudged needs to name who guarantees it"


@pytest.mark.parametrize("rule", _rules(), ids=lambda rule: rule["id"])
def test_every_named_judge_exists(rule: dict) -> None:
    for target in rule.get("judged_by") or []:
        path_part, _, test_name = target.partition("::")
        path = ROOT / path_part
        assert path.exists(), f"{rule['id']}: judge path does not exist: {path_part}"
        if test_name:
            body = path.read_text(encoding="utf-8")
            assert re.search(rf"\bdef {re.escape(test_name)}\(", body), (
                f"{rule['id']}: {path_part} has no test named {test_name}"
            )


def _squash(text: str) -> str:
    """Collapse every whitespace run to one space.

    Markdown wraps prose at a fixed width, so a rule that spans two source lines is
    still the same rule. Comparing raw text would make the inventory go red on a
    re-wrap -- a false alarm that trains people to ignore this test. The anchor is
    matched on squashed text; the rule text itself is not otherwise normalised.
    """
    return " ".join(text.split())


@pytest.mark.parametrize("rule", _rules(), ids=lambda rule: rule["id"])
def test_every_rule_anchor_still_appears_in_its_source(rule: dict) -> None:
    source = ROOT / rule["source"]
    assert source.exists(), f"{rule['id']}: source document missing: {rule['source']}"
    body = _squash(source.read_text(encoding="utf-8"))
    assert _squash(rule["anchor"]) in body, (
        f"{rule['id']}: the anchor text is no longer in {rule['source']}; the rule may have "
        "been renamed or removed, and this inventory is now describing something that is gone"
    )


def _unwired(rules: list[dict], plan: str, test_texts: dict[str, str]) -> list[str]:
    """Return `rule: judge` pairs whose judge never runs in the release plan.

    A guard that exists on disk but is not reached by the plan is the
    "installed but not wired" failure: the inventory would list it as
    enforcement while nothing executes it. Two wirings count:

    * the script appears in the acceptance plan's command list; or
    * a test under `tests/` references it, and the plan runs ``pytest tests``
      wholesale, so that test runs.
    """
    unwired = []
    for rule in rules:
        for judge in rule.get("judged_by") or []:
            path = judge.split("::")[0]
            if path.startswith("tests/"):
                continue  # covered by the plan's ``pytest tests`` step
            if path in plan:
                continue
            stem = Path(path).stem
            if any(re.search(rf"\b{re.escape(stem)}\b", text) for text in test_texts.values()):
                continue
            unwired.append(f"{rule['id']}: {judge}")
    return unwired


def test_every_cited_judge_is_executed_by_the_release_plan():
    """A judge nobody runs is a sentence, not enforcement.

    The plan runs ``pytest tests`` plus a fixed command list, so a cited script
    is wired when it is either a plan command or imported by some test. This
    catches the shape where a checker is added, cited in the inventory, and
    then never called -- the inventory would claim enforcement that the gate
    never performs.
    """
    plan = (ROOT / "skills/development/scirel-acceptance/scripts/check_all.py").read_text(
        encoding="utf-8"
    )
    test_texts = {
        path.as_posix(): path.read_text(encoding="utf-8") for path in (ROOT / "tests").rglob("*.py")
    }
    assert ("pytest" in plan and '"tests"' in plan) or "'tests'" in plan
    assert _unwired(_rules(), plan, test_texts) == []


def test_an_unwired_judge_is_reported():
    """Red case: the wiring test must not pass on an invented citation."""
    rules = [{"id": "demo-1", "judged_by": ["scripts/a_checker_nobody_runs.py"]}]
    assert _unwired(rules, plan="", test_texts={}) == ["demo-1: scripts/a_checker_nobody_runs.py"]
    assert _unwired(rules, plan="scripts/a_checker_nobody_runs.py", test_texts={}) == []
    assert (
        _unwired(
            rules, plan="", test_texts={"tests/x/test_demo.py": "import a_checker_nobody_runs"}
        )
        == []
    )
