"""The C4 usage-acceptance list stays valid and keeps full-domain coverage.

The list is the frozen baseline a blind consumer runs against a delivered
package. These tests keep it honest on three fronts: it passes its own
validator, the validator actually rejects lists that lose coverage or invent
contract facts, and the stored digest matches the tasks so an edit is visible
in review.
"""

from copy import deepcopy
import copy
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_c4_tasklist as checker  # noqa: E402

TASKLIST = ROOT / "examples" / "c4-usage-acceptance" / "tasklist.json"


def load() -> dict:
    return json.loads(TASKLIST.read_text(encoding="utf-8"))


def validate(document: dict) -> list[str]:
    assets, excluded = checker.load_catalog(ROOT)
    errors, _table, _cross = checker.check(document, assets, excluded)
    return errors


def test_the_shipped_task_list_passes_its_own_validator():
    assert validate(load()) == []


def test_every_catalog_domain_carries_its_quota():
    document = load()
    assets, excluded = checker.load_catalog(ROOT)
    errors, table, cross = checker.check(document, assets, excluded)
    domains = {checker.domain_of(asset) for asset in assets}
    assert set(table) == domains
    assert cross >= document["quota"]["min_cross_domain"]
    assert table and all(row["nominal"] >= row["required"] for row in table.values())


def test_rejections_and_scope_exclusions_are_covered_in_every_domain():
    document = load()
    kinds: dict[str, set[str]] = {}
    for task in document["tasks"]:
        if task["kind"] == "cross":
            continue
        kinds.setdefault(task["domain"], set()).add(task["kind"])
    for domain, present in kinds.items():
        assert present & {"failure", "inapplicable"}, domain


def test_a_task_naming_an_unknown_asset_is_rejected():
    document = deepcopy(load())
    document["tasks"][0]["assets"] = ["scirel.absent.not-an-asset"]
    assert any("unknown asset ids" in error for error in validate(document))


def test_a_task_claiming_an_undeclared_parameter_is_rejected():
    document = deepcopy(load())
    document["tasks"][0]["criteria"].append(
        {"id": "bogus", "kind": "parameters", "expect": ["not_a_declared_parameter"]}
    )
    assert any("not declared inputs" in error for error in validate(document))


def test_a_failure_task_with_a_numeric_tolerance_is_rejected():
    document = deepcopy(load())
    for task in document["tasks"]:
        if task["kind"] == "failure":
            task["criteria"].append(
                {
                    "id": "sneaky",
                    "kind": "tolerance",
                    "quantity": "@declared_outputs",
                    "unit": "as declared",
                    "tolerance": {
                        "rel": 1e-6,
                        "abs": 0,
                        "basis": "widened until the rejection passed",
                    },
                    "declared_before_run": True,
                }
            )
            break
    assert any("no numeric tolerance" in error for error in validate(document))


def test_a_domain_losing_its_tasks_is_rejected():
    document = deepcopy(load())
    document["tasks"] = [task for task in document["tasks"] if task["domain"] != "neutrals"]
    errors = validate(document)
    assert any("neutrals" in error and "needs" in error for error in errors)


def test_a_domain_losing_its_failure_task_is_rejected():
    document = deepcopy(load())
    document["tasks"] = [
        task
        for task in document["tasks"]
        if not (task["domain"] == "collisions" and task["kind"] in ("failure", "inapplicable"))
    ]
    errors = validate(document)
    assert any("collisions" in error and "failure/inapplicable" in error for error in errors)


def test_a_cross_task_that_stays_inside_one_domain_is_rejected():
    document = deepcopy(load())
    for task in document["tasks"]:
        if task["kind"] == "cross":
            task["domains"] = ["field"]
            break
    assert any("at least two domains" in error for error in validate(document))


def test_tolerances_must_be_declared_before_the_run():
    document = deepcopy(load())
    changed = False
    for task in document["tasks"]:
        for criterion in task["criteria"]:
            if criterion["kind"] == "tolerance" and not changed:
                criterion["declared_before_run"] = False
                changed = True
    assert changed
    assert any("declared_before_run" in error for error in validate(document))


def test_an_input_placeholder_is_rejected():
    document = deepcopy(load())
    for task in document["tasks"]:
        if task["input_binding"]["mode"] == "literal":
            task["input_binding"]["values"]["width"] = "TBD"
            break
    assert any("placeholders" in error for error in validate(document))


def test_an_inapplicable_task_without_a_reason_is_rejected():
    document = deepcopy(load())
    for task in document["tasks"]:
        if task["kind"] == "inapplicable":
            task.pop("inapplicable_reason")
            break
    assert any("why the model does not apply" in error for error in validate(document))


def test_the_freeze_assertion_cannot_be_silently_dropped():
    document = deepcopy(load())
    document["freeze"]["tolerances_declared_before_any_candidate_run"] = False
    assert any(
        "tolerances_declared_before_any_candidate_run" in error for error in validate(document)
    )


def test_the_cli_fails_closed_on_a_missing_task_list(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts" / "check_c4_tasklist.py"),
            "--repo",
            str(ROOT),
            "--tasklist",
            str(tmp_path / "absent.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "not found" in result.stdout


def test_the_cli_reports_the_shipped_list_as_ok():
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts" / "check_c4_tasklist.py"),
            "--repo",
            str(ROOT),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] is True
    assert report["errors"] == []
    assert report["domains_in_catalog"] == len(report["quota"])
    assert report["digest"] == checker.digest(load())


def test_the_digest_is_stable_under_key_order_and_changes_with_content():
    document = load()
    reordered = json.loads(json.dumps(document, sort_keys=True))
    assert checker.digest(reordered) == checker.digest(document)
    edited = copy.deepcopy(document)
    edited["tasks"][0]["question"] = edited["tasks"][0]["question"] + " "
    assert checker.digest(edited) != checker.digest(document)
