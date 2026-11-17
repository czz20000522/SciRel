"""A receipt anchor cannot make a shrunken, contradicted or unfinished run look green.

The fixtures here are receipts and anchors built by hand, never a real acceptance run: the point
is that the readers refuse a fabricated one, so the test asserts on the refusal, not on a suite.
"""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/development/scirel-acceptance/scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: check_all defines a dataclass, and dataclasses resolves the
    # defining module through sys.modules.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check_all = _load("check_all")
anchor_module = _load("acceptance_anchor")

PASSED_PHASES = [
    {"when": "setup", "outcome": "passed"},
    {"when": "call", "outcome": "passed"},
    {"when": "teardown", "outcome": "passed"},
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result(nodeid: str, outcome: str = "passed", reason: str | None = None) -> dict:
    if outcome == "passed":
        phases = [dict(phase) for phase in PASSED_PHASES]
    elif outcome == "xfailed":
        phases = [
            {"when": "setup", "outcome": "passed"},
            {"when": "call", "outcome": "skipped", "reason": reason, "wasxfail": reason},
            {"when": "teardown", "outcome": "passed"},
        ]
    else:
        phases = [
            {"when": "setup", "outcome": "skipped", "reason": reason},
            {"when": "teardown", "outcome": "passed"},
        ]
    return {"nodeid": nodeid, "outcome": outcome, "phases": phases}


def _counts(results: list[dict], deselected_nodeids: list[str] | None = None) -> dict:
    """A counts report that the plugin's own validator accepts, so only the test under
    examination can make it red."""
    totals = {name: 0 for name in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")}
    skip_reasons: dict[str, list[str]] = {}
    for item in results:
        totals[item["outcome"]] += 1
        if item["outcome"] == "skipped":
            reason = next(
                phase["reason"] for phase in item["phases"] if phase["outcome"] == "skipped"
            )
            skip_reasons.setdefault(reason, []).append(item["nodeid"])
    deselected = list(deselected_nodeids or [])
    report = {
        "schema": 3,
        "pytest_exitstatus": 0,
        "collection_finished": True,
        "collection_reports": [],
        "selected_nodeids": [item["nodeid"] for item in results],
        "deselected_nodeids": deselected,
        "results": results,
        "collected": len(results) + len(deselected),
        "selected": len(results),
        "deselected": len(deselected),
        **totals,
        "skip_reasons": skip_reasons,
    }
    from scirel_pytest_counts import validate_execution_records

    validate_execution_records(report)
    report.update(consistent=True, inconsistency="")
    return report


def _environment() -> dict:
    return {
        "python": {"implementation": "CPython", "version": "3.14.0"},
        "platform": "linux",
        "architecture": "x86_64",
        "dependencies": {"numpy": "2.5.4", "scipy": "1.18.1", "mpmath": "1.4.1"},
        "uv_lock_sha256": "a" * 64,
        "python_version_sha256": "b" * 64,
    }


def _receipt(tmp_path: Path, counts: dict, *, name: str = "result") -> Path:
    """A complete, sidecar-backed v2 receipt around one counts report."""
    log = tmp_path / f"{name}-step-00.log"
    log.write_text("complete fixture output\n", encoding="utf-8")
    identity = {
        "commit": "c" * 40,
        "tree": "d" * 40,
        "dirty": False,
        "worktree_sha256": "e" * 64,
    }
    receipt = {
        "schema": "scirel.acceptance.v2",
        "status": "complete",
        "stage": "release",
        "run_id": "fixture invocation",
        "exclusive": {
            "token_sha256": "f" * 64,
            "record": ".runtime/locks/acceptance-exclusive",
            "present": True,
        },
        "provenance": {
            "check_all_sha256": _sha(SCRIPTS / "check_all.py"),
            "counts_plugin_sha256": _sha(SCRIPTS / "scirel_pytest_counts.py"),
        },
        "candidate": {"before": dict(identity), "after": dict(identity)},
        "environment": {"before": _environment(), "after": _environment()},
        "binding_errors": [],
        "evidence": "clean_candidate",
        "steps": [{"name": "tests", "log": str(log), "log_sha256": _sha(log)}],
        "tests": counts,
        "exit_code": 0,
    }
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    path.with_name(path.name + ".sha256").write_text(_sha(path) + "\n", encoding="utf-8")
    return path


def _anchor_for(tmp_path: Path, receipt: Path, name: str = "anchor") -> Path:
    anchor = tmp_path / f"{name}.json"
    assert (
        anchor_module.export(receipt, anchor, checked_at="2026-01-01T00:00:00Z")
        == anchor_module.AGREE
    )
    return anchor


def test_two_passing_tests_used_to_be_indistinguishable_from_the_whole_suite(tmp_path):
    """The defect this feature exists for, pinned so it cannot come back silently.

    Without a floor, ``read_counts`` accepts any internally consistent report: two passing tests
    and 8,347 passing tests produce the same verdict. The floor is the only thing that tells
    "ran everything" apart from "ran almost nothing".
    """
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(_counts([_result("tests/a.py::test_one")])), encoding="utf-8")
    unfloored = check_all.Step("tests", ["pytest"], counts=path)
    assert check_all.step_status(unfloored, 0)[0] == "PASS"  # the defect, stated as a fact


def test_a_shrunken_selection_cannot_pass_the_floor(tmp_path):
    path = tmp_path / "counts.json"
    path.write_text(
        json.dumps(_counts([_result("tests/a.py::test_one"), _result("tests/a.py::test_two")])),
        encoding="utf-8",
    )
    floored = check_all.Step("tests", ["pytest"], counts=path, minimum_selected=5)
    status, detail, report = check_all.step_status(floored, 0)
    assert status == "FAIL"
    assert "selected 2" in detail and "5" in detail and "shrank" in detail
    assert report is not None, "the counts stay readable even though the step is red"


def test_a_run_that_meets_the_floor_stays_green(tmp_path):
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(_counts([_result("tests/a.py::test_one")])), encoding="utf-8")
    step = check_all.Step("tests", ["pytest"], counts=path, minimum_selected=1)
    assert check_all.step_status(step, 0)[0] == "PASS"


def _anchor_document(selected: int, stage: str = "release", checked_at="2026-01-01T00:00:00Z"):
    return {
        "schema": check_all.ANCHOR_SCHEMA,
        "stage": stage,
        "checked_at": checked_at,
        "candidate": {"commit": "c" * 40},
        "tests": {"selected": selected},
    }


def test_the_floor_is_the_newest_anchor_of_the_same_stage(tmp_path):
    directory = tmp_path / check_all.ANCHOR_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "release-old.json").write_text(
        json.dumps(_anchor_document(8000, checked_at="2025-01-01T00:00:00Z")), encoding="utf-8"
    )
    (directory / "release-new.json").write_text(
        json.dumps(_anchor_document(8100, checked_at="2026-01-01T00:00:00Z")), encoding="utf-8"
    )
    (directory / "dev.json").write_text(
        json.dumps(_anchor_document(10, stage="dev")), encoding="utf-8"
    )
    floor = check_all.selection_floor("release", tmp_path)
    assert floor is not None
    assert floor.selected == 8100
    assert floor.anchor.endswith("release-new.json")


def test_a_stage_without_its_own_anchor_has_no_floor_rather_than_an_error(tmp_path):
    """Every "no anchor for this stage" case is informational, in both directions.

    The first version raised when the directory held anchors for a different stage, to stop
    a stage being exempted by deleting its file. That rule made the development stage
    unrunnable the moment a release anchor was committed, because the two stages select
    different test sets. Exemption is already visible: anchors are committed, so deleting one
    is a diff in the pull request that deletes it, and the run prints the floor it used.
    """
    assert check_all.selection_floor("release", tmp_path) is None
    directory = tmp_path / check_all.ANCHOR_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "README.md").write_text("# none\n", encoding="utf-8")
    assert check_all.selection_floor("release", tmp_path) is None
    (directory / "dev.json").write_text(json.dumps(_anchor_document(10, stage="dev")), "utf-8")
    assert check_all.selection_floor("release", tmp_path) is None
    floor = check_all.selection_floor("dev", tmp_path)
    assert floor is not None and floor.selected == 10


def test_a_malformed_anchor_is_a_binding_error_not_a_silent_skip(tmp_path):
    directory = tmp_path / check_all.ANCHOR_DIRECTORY
    directory.mkdir(parents=True)
    (directory / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(check_all.BindingError, match="not readable JSON"):
        check_all.selection_floor("release", tmp_path)


def test_an_outcome_that_its_phases_contradict_is_refused(tmp_path):
    """A per-test record that claims `passed` while its phases say `failed` cannot be green."""
    counts = _counts([_result("tests/a.py::test_one")])
    phases = [
        {"when": "setup", "outcome": "passed"},
        {"when": "call", "outcome": "failed"},
        {"when": "teardown", "outcome": "passed"},
    ]
    counts["results"][0]["phases"] = phases
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(counts), encoding="utf-8")
    with pytest.raises(check_all.CountsError, match="phase-derived|outcome|disagrees"):
        check_all.read_counts(path)


def test_a_collection_that_did_not_finish_is_refused(tmp_path):
    counts = _counts([_result("tests/a.py::test_one")])
    counts["collection_finished"] = False
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(counts), encoding="utf-8")
    with pytest.raises(check_all.CountsError, match="collection did not finish"):
        check_all.read_counts(path)


def test_a_failed_collection_report_is_refused(tmp_path):
    counts = _counts([_result("tests/a.py::test_one")])
    counts["collection_reports"] = [
        {"nodeid": "tests/b.py", "outcome": "failed", "reason": "ImportError: broken"}
    ]
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(counts), encoding="utf-8")
    with pytest.raises(check_all.CountsError, match="collection failed"):
        check_all.read_counts(path)


def test_a_reserved_but_unfinished_receipt_is_not_a_result(tmp_path):
    """An interrupted run leaves `status: running`; reading it as a result would be a pass."""
    counts = _counts([_result("tests/a.py::test_one")])
    receipt = _receipt(tmp_path, counts)
    document = json.loads(receipt.read_text())
    document["status"] = "running"
    receipt.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="not a completed run"):
        check_all.validate_provenance(
            document, report_path=receipt, check_all_path=SCRIPTS / "check_all.py"
        )


def test_a_missing_receipt_cannot_be_checked(tmp_path):
    counts = _counts([_result("tests/a.py::test_one")])
    anchor = _anchor_for(tmp_path, _receipt(tmp_path, counts))
    # Through the CLI, because the exit status is the contract: 2 means "cannot check", never
    # "agrees" and never "the acceptance passed".
    assert (
        anchor_module.main(["verify", str(anchor), str(tmp_path / "absent.json")])
        == anchor_module.CANNOT_CHECK
    )


def test_an_anchor_whose_digest_disagrees_is_refused(tmp_path):
    counts = _counts([_result("tests/a.py::test_one"), _result("tests/a.py::test_two")])
    receipt = _receipt(tmp_path, counts)
    anchor = _anchor_for(tmp_path, receipt)
    assert anchor_module.verify(anchor, receipt) == anchor_module.AGREE
    document = json.loads(anchor.read_text())
    document["tests"]["nodeid_set_sha256"] = "0" * 64
    anchor.write_text(json.dumps(document), encoding="utf-8")
    assert anchor_module.verify(anchor, receipt) == anchor_module.DISAGREE


def test_a_rerun_with_one_test_removed_disagrees(tmp_path):
    """The set digest is what turns a shrunken rerun into a disagreement, not a quiet pass."""
    full = _receipt(
        tmp_path,
        _counts([_result("tests/a.py::test_one"), _result("tests/a.py::test_two")]),
        name="full",
    )
    anchor = _anchor_for(tmp_path, full)
    shrunken = _receipt(tmp_path, _counts([_result("tests/a.py::test_one")]), name="shrunken")
    assert anchor_module.verify(anchor, shrunken) == anchor_module.DISAGREE


def test_a_skip_reason_change_is_a_disagreement_even_with_the_same_count(tmp_path):
    first = _counts([_result("tests/a.py::test_one", "skipped", "Windows only path")])
    second = _counts([_result("tests/a.py::test_one", "skipped", "needs an external oracle")])
    anchor = _anchor_for(tmp_path, _receipt(tmp_path, first, name="first"))
    other = _receipt(tmp_path, second, name="second")
    assert anchor_module.verify(anchor, other) == anchor_module.DISAGREE


def test_the_digests_do_not_depend_on_the_platform_separator():
    """A Windows run and a POSIX run of the same suite must agree on identity."""
    forward = ["tests/domain/test_a.py::test_one", "tests/domain/test_a.py::test_two[3]"]
    backward = ["tests\\domain\\test_a.py::test_one", ".\\tests/domain/test_a.py::test_two[3]"]
    assert anchor_module._nodeid_set_digest(forward) == anchor_module._nodeid_set_digest(backward)
    assert anchor_module._per_test_digest(
        [_result(node) for node in forward]
    ) == anchor_module._per_test_digest([_result(node) for node in backward])


def test_a_xfail_reason_reaches_the_anchor(tmp_path):
    counts = _counts(
        [_result("tests/a.py::test_one"), _result("tests/a.py::test_two", "xfailed", "AUDIT-B3")]
    )
    anchor = _anchor_for(tmp_path, _receipt(tmp_path, counts))
    document = json.loads(anchor.read_text())
    assert document["xfail_reasons"] == {"AUDIT-B3": 1}
    assert document["tests"]["xfailed"] == 1


def test_export_refuses_a_run_that_did_not_pass(tmp_path):
    counts = _counts([_result("tests/a.py::test_one")])
    receipt = _receipt(tmp_path, counts)
    document = json.loads(receipt.read_text())
    document["exit_code"] = 1
    receipt.write_text(json.dumps(document), encoding="utf-8")
    anchor = tmp_path / "anchor.json"
    assert anchor_module.export(receipt, anchor) == anchor_module.CANNOT_CHECK
    assert not anchor.exists(), "a failed run must not leave an anchor behind"


def test_the_anchor_stays_small_enough_to_commit(tmp_path):
    """The whole point is a few kilobytes instead of the multi-megabyte receipt."""
    counts = _counts([_result(f"tests/a.py::test_{index}") for index in range(200)])
    anchor = _anchor_for(tmp_path, _receipt(tmp_path, counts))
    assert anchor.stat().st_size < 5000
    document = json.loads(anchor.read_text())
    assert "selected_nodeids" not in document["tests"]
    assert len(document["tests"]["nodeid_set_sha256"]) == 64
