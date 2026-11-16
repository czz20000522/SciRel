"""The C4 usage-acceptance list stays valid and keeps full-domain coverage.

The list is the frozen baseline a blind consumer runs against a delivered
package. These tests keep it honest on four fronts: it passes its own
validator, the validator rejects lists that lose coverage, the validator
rejects lists that invent contract facts (parameters, rejections, units,
excluded clauses), and any edit to the tasks shows up as a digest mismatch
unless the tracked digest is updated with it.
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


def task(document: dict, task_id: str) -> dict:
    for item in document["tasks"]:
        if item["id"] == task_id:
            return item
    raise AssertionError(f"no task {task_id}")


def failure_task(document: dict) -> dict:
    for item in document["tasks"]:
        if item["kind"] == "failure":
            return item
    raise AssertionError("no failure task")


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


def test_a_literal_key_outside_the_contract_inputs_is_rejected():
    """Regression: a literal binding invented its own argument names."""
    document = deepcopy(load())
    document["tasks"][0]["input_binding"] = {
        "mode": "literal",
        "values": {"incident_energy_keV": -1.0},
    }
    assert any("literal keys" in error for error in validate(document))


def test_a_stimulus_field_outside_the_contract_inputs_is_rejected():
    """Regression: a rejection task asked for a parameter that does not exist."""
    document = deepcopy(load())
    entry = failure_task(document)["stimulus"][0]
    entry["field"] = "incident_energy_keV"
    assert any("is not a declared input" in error for error in validate(document))


def test_a_stimulus_quoting_a_rejection_the_contract_lacks_is_rejected():
    """Regression: a rejection must be quoted from the contract, not assumed."""
    document = deepcopy(load())
    entry = failure_task(document)["stimulus"][0]
    entry["declared_rejection"] = "negative energy raises ValueError"
    assert any("is not verbatim" in error for error in validate(document))


def test_a_stimulus_exception_the_contract_lacks_is_rejected():
    document = deepcopy(load())
    entry = failure_task(document)["stimulus"][0]
    entry["expected_exception"] = "KeyError"
    assert any("is not stated by" in error for error in validate(document))


def test_exception_criteria_must_name_one_asset():
    document = deepcopy(load())
    for criterion in failure_task(document)["criteria"]:
        if criterion["kind"] == "exception":
            criterion.pop("asset")
            break
    assert any("must name one task asset" in error for error in validate(document))


def test_exception_criteria_cannot_be_satisfied_by_another_asset():
    document = deepcopy(load())
    target = None
    for item in document["tasks"]:
        kinds = [c["kind"] for c in item["criteria"]]
        if item["kind"] == "failure" and "exception" in kinds:
            target = item
            break
    assert target is not None
    entry = target["stimulus"][0]
    entry["expected_exception"] = "KeyError"
    entry["declared_rejection"] = "x"
    entry["field"] = "no_such_field"
    assert validate(document)


def test_a_failure_task_with_a_numeric_tolerance_is_rejected():
    document = deepcopy(load())
    failure_task(document)["criteria"].append(
        {
            "id": "sneaky",
            "kind": "tolerance",
            "quantity": "@declared_outputs",
            "unit": "as declared",
            "tolerance": {"rel": 1e-6, "abs": 0, "basis": "widened until the rejection passed"},
            "declared_before_run": True,
        }
    )
    assert any("no numeric tolerance" in error for error in validate(document))


def test_a_tolerance_unit_that_contradicts_the_declared_output_is_rejected():
    """Regression: unit was never checked when quantity named a declared output."""
    document = deepcopy(load())
    target = task(document, "source-profile-integral")
    target["criteria"].append(
        {
            "id": "unit-drift",
            "kind": "tolerance",
            "quantity": "profile",
            "unit": "furlong",
            "tolerance": {"rel": 1e-12, "abs": 0, "basis": "declared before any candidate run"},
            "declared_before_run": True,
        }
    )
    assert any("is not the declared unit" in error for error in validate(document))


def test_a_tolerance_quantity_that_is_not_a_declared_output_is_rejected():
    document = deepcopy(load())
    target = task(document, "source-profile-integral")
    target["criteria"].append(
        {
            "id": "ghost-quantity",
            "kind": "tolerance",
            "quantity": "pressure_at_axis",
            "unit": "Pa",
            "tolerance": {"rel": 1e-12, "abs": 0, "basis": "declared before any candidate run"},
            "declared_before_run": True,
        }
    )
    assert any("is not a declared output name" in error for error in validate(document))


def test_an_inapplicable_quote_the_contract_lacks_is_rejected():
    """Regression: the excluded clause was paraphrased instead of quoted."""
    document = deepcopy(load())
    for item in document["tasks"]:
        if item["kind"] == "inapplicable":
            item["excluded_quote"] = "relativistic corrections are out of scope here"
            break
    assert any("is not verbatim in applicability.excluded" in error for error in validate(document))


def test_min_calls_must_cover_every_named_asset():
    document = deepcopy(load())
    target = task(document, "field-filament-superposition")
    target["min_calls"] = 1
    assert any("cannot exercise" in error for error in validate(document))


def test_a_stimulus_on_a_nominal_task_is_rejected():
    document = deepcopy(load())
    task(document, "source-profile-integral")["stimulus"] = failure_task(document)["stimulus"]
    assert any("only failure tasks carry a stimulus" in error for error in validate(document))


def test_widening_a_tolerance_without_updating_the_digest_is_rejected():
    """Regression: the digest must make a silent tolerance edit impossible."""
    document = deepcopy(load())
    changed = False
    for item in document["tasks"]:
        for criterion in item["criteria"]:
            if criterion["kind"] == "tolerance" and not changed:
                criterion["tolerance"]["rel"] = 1e-3
                changed = True
    assert changed
    assert any("does not match the tasks" in error for error in validate(document))


def test_the_declared_digest_matches_the_shipped_tasks():
    assert load()["tasks_digest"] == checker.digest(load())


def test_an_invariant_describing_another_stimulus_is_rejected():
    """Regression: renamed tasks kept text about a stimulus they no longer use."""
    document = deepcopy(load())
    target = task(document, "numerics-rejects-invalid-rcond")
    for criterion in target["criteria"]:
        if criterion["kind"] == "invariant":
            criterion["statement"] = (
                "The consumer must not replace nonfinite matrix entries with zeros before the call."
            )
    assert any("must describe the rcond stimulus" in error for error in validate(document))


def test_a_readback_that_does_not_confirm_the_stimulus_is_rejected():
    document = deepcopy(load())
    target = task(document, "numerics-rejects-invalid-rcond")
    for criterion in target["criteria"]:
        if criterion["kind"] == "readback":
            criterion["statement"] = "Re-open calls.jsonl and confirm the raised status."
    assert any("must confirm the rcond argument" in error for error in validate(document))


def test_a_domain_losing_its_tasks_is_rejected():
    document = deepcopy(load())
    document["tasks"] = [item for item in document["tasks"] if item["domain"] != "neutrals"]
    errors = validate(document)
    assert any("neutrals" in error and "needs" in error for error in errors)


def test_a_domain_losing_its_failure_task_is_rejected():
    document = deepcopy(load())
    document["tasks"] = [
        item
        for item in document["tasks"]
        if not (item["domain"] == "collisions" and item["kind"] in ("failure", "inapplicable"))
    ]
    errors = validate(document)
    assert any("collisions" in error and "failure/inapplicable" in error for error in errors)


def test_a_cross_task_that_stays_inside_one_domain_is_rejected():
    document = deepcopy(load())
    for item in document["tasks"]:
        if item["kind"] == "cross":
            item["domains"] = ["field"]
            break
    assert any("at least two domains" in error for error in validate(document))


def test_tolerances_must_be_declared_before_the_run():
    document = deepcopy(load())
    changed = False
    for item in document["tasks"]:
        for criterion in item["criteria"]:
            if criterion["kind"] == "tolerance" and not changed:
                criterion["declared_before_run"] = False
                changed = True
    assert changed
    assert any("declared_before_run" in error for error in validate(document))


def test_an_input_placeholder_is_rejected():
    document = deepcopy(load())
    document["tasks"][0]["input_binding"] = {
        "mode": "literal",
        "values": {"kz": "TBD"},
    }
    assert any("placeholders" in error for error in validate(document))


def test_an_inapplicable_task_without_a_reason_is_rejected():
    document = deepcopy(load())
    for item in document["tasks"]:
        if item["kind"] == "inapplicable":
            item.pop("inapplicable_reason")
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
    assert report["declared_digest"] == report["digest"] == checker.digest(load())


def test_the_digest_is_stable_under_key_order_and_changes_with_content():
    document = load()
    reordered = json.loads(json.dumps(document, sort_keys=True))
    assert checker.digest(reordered) == checker.digest(document)
    edited = copy.deepcopy(document)
    edited["tasks"][0]["question"] = edited["tasks"][0]["question"] + " "
    assert checker.digest(edited) != checker.digest(document)
