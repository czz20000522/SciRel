"""check_all.py reports pytest counts, and refuses a report whose numbers do not add up."""

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

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

SAMPLE = """
import pytest


def test_passes():
    assert True


@pytest.mark.skip(reason="not applicable in this fixture")
def test_skipped():
    assert False


@pytest.mark.xfail(reason="known defect")
def test_xfails():
    assert False


@pytest.mark.xfail(reason="passes unexpectedly")
def test_xpasses():
    assert True


@pytest.mark.xfail(strict=True, reason="a strict xpass counts as a failure")
def test_strict_xpass_is_a_failure():
    assert True


@pytest.fixture
def broken():
    raise RuntimeError("setup fails on purpose")


def test_errors(broken):
    assert True


def test_fails():
    assert False
"""


def _plugins_env() -> dict[str, str]:
    env = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
    env["PYTHONPATH"] = str(SCRIPTS)
    return env


def _run(directory: Path, extra: list[str], *, with_plugin: bool) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        str(directory / "test_sample.py"),
        "-q",
        "-p",
        "no:cacheprovider",
        *extra,
    ]
    env = dict(os.environ)
    if with_plugin:
        command += [
            "-p",
            "scirel_pytest_counts",
            f"--scirel-counts={directory / 'counts.json'}",
        ]
        env = _plugins_env()
    return subprocess.run(command, cwd=directory, capture_output=True, text=True, env=env)


def _sample(tmp_path: Path) -> Path:
    (tmp_path / "test_sample.py").write_text(SAMPLE, encoding="utf-8")
    return tmp_path


def test_counts_cover_every_outcome(tmp_path):
    directory = _sample(tmp_path)
    _run(directory, [], with_plugin=True)
    report = check_all.read_counts(directory / "counts.json")
    assert report["selected"] == 7
    assert report["deselected"] == 0
    assert report["passed"] == 1
    # The failing test plus the strict xfail whose test passed unexpectedly.
    assert report["failed"] == 2
    assert report["error"] == 1
    assert report["skipped"] == 1
    assert report["xfailed"] == 1
    assert report["xpassed"] == 1
    assert list(report["skip_reasons"]) == ["not applicable in this fixture"]
    (skip_line,) = check_all.skip_lines(report)
    assert skip_line.startswith("SKIP  not applicable in this fixture  (1):")
    assert "test_skipped" in skip_line


def test_plugin_changes_no_test_outcome(tmp_path):
    """Installing the plugin must not alter a single result, only observe them."""
    directory = _sample(tmp_path)
    (directory / "test_sample.py").write_text(EXECUTION_SAMPLE, encoding="utf-8")
    plain = _run(directory, [f"--junitxml={directory / 'plain.xml'}"], with_plugin=False)
    watched = _run(directory, [f"--junitxml={directory / 'watched.xml'}"], with_plugin=True)
    assert watched.returncode == plain.returncode
    assert _outcomes(directory / "watched.xml") == _outcomes(directory / "plain.xml")


def test_plugin_without_a_report_path_fails_loudly(tmp_path):
    """A run that cannot produce the report must not look like an ordinary green run."""
    directory = _sample(tmp_path)
    done = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            str(directory / "test_sample.py"),
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "scirel_pytest_counts",
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        env=_plugins_env(),
    )
    assert done.returncode != 0
    assert "--scirel-counts" in done.stdout + done.stderr


def _outcomes(path: Path) -> dict[str, tuple[str, ...]]:
    import xml.etree.ElementTree as ElementTree

    root = ElementTree.parse(path).getroot()
    return {
        case.get("name"): tuple(
            child.tag if not child.get("type") else f"{child.tag}:{child.get('type')}"
            for child in case
        )
        for case in root.iter("testcase")
    }


def test_missing_counts_file_is_refused(tmp_path):
    with pytest.raises(check_all.CountsError, match="was not written"):
        check_all.read_counts(tmp_path / "absent.json")


def test_unreadable_counts_file_is_refused(tmp_path):
    report = tmp_path / "counts.json"
    report.write_text("{not json", encoding="utf-8")
    with pytest.raises(check_all.CountsError, match="not readable JSON"):
        check_all.read_counts(report)


def test_inconsistent_counts_are_refused(tmp_path):
    report = tmp_path / "counts.json"
    report.write_text(
        json.dumps(_report(consistent=False, inconsistency="1 selected but 0 outcomes"))
    )
    with pytest.raises(check_all.CountsError, match="inconsistency"):
        check_all.read_counts(report)


def test_counts_that_do_not_add_up_are_refused(tmp_path):
    broken = _report()
    broken["passed"] = 99
    report = tmp_path / "counts.json"
    report.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(check_all.CountsError, match="outcomes add up to"):
        check_all.read_counts(report)


def _report(**overrides) -> dict:
    report = {
        "schema": 2,
        "pytest_exitstatus": 0,
        "collection_finished": True,
        "collection_reports": [],
        "collected": 3,
        "selected": 3,
        "deselected": 0,
        "passed": 3,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "skip_reasons": {},
        "consistent": True,
        "inconsistency": "",
    }
    report.update(overrides)
    if "pytest_exitstatus" not in overrides and (report["failed"] or report["error"]):
        report["pytest_exitstatus"] = 1
    results = []
    skip_nodes = [
        (node, reason) for reason, nodes in report["skip_reasons"].items() for node in nodes
    ]
    for outcome in ("passed", "failed", "error", "skipped", "xfailed", "xpassed"):
        for index in range(report[outcome]):
            node = f"tests/fixture.py::test_{len(results)}"
            setup = {"when": "setup", "outcome": "passed"}
            call = {"when": "call", "outcome": "failed" if outcome == "failed" else "passed"}
            if outcome in ("skipped", "xfailed"):
                setup.update(outcome="skipped", reason="known defect")
                if outcome == "skipped" and index < len(skip_nodes):
                    node, setup["reason"] = skip_nodes[index]
                if outcome == "xfailed":
                    setup["wasxfail"] = "known defect"
            elif outcome == "error":
                setup["outcome"] = "failed"
            elif outcome == "xpassed":
                call["wasxfail"] = "known defect"
            phases = [
                setup,
                *([call] if setup["outcome"] == "passed" else []),
                {"when": "teardown", "outcome": "passed"},
            ]
            results.append({"nodeid": node, "outcome": outcome, "phases": phases})
    report["selected_nodeids"] = [item["nodeid"] for item in results]
    report["results"] = results
    return report


def test_tests_step_declares_the_counts_report(tmp_path):
    step = check_all.steps(tmp_path)[0]
    assert step.name == "tests"
    assert step.counts == tmp_path / "tests-counts.json"
    assert "-p" in step.command and "scirel_pytest_counts" in step.command
    assert any(part.startswith("--scirel-counts=") for part in step.command)


def test_a_green_pytest_run_without_usable_counts_is_not_green(tmp_path):
    step = check_all.Step("tests", ["true"], counts=tmp_path / "absent.json")
    status, detail, report = check_all.step_status(step, 0)
    assert status == "FAIL"
    assert "test counts unusable" in detail
    assert report is None


def test_a_green_pytest_run_with_counts_is_green(tmp_path):
    report_path = tmp_path / "counts.json"
    report_path.write_text(json.dumps(_report(skipped=0)), encoding="utf-8")
    step = check_all.Step("tests", ["true"], counts=report_path)
    status, detail, report = check_all.step_status(step, 0)
    assert (status, detail) == ("PASS", "")
    assert report["selected"] == report["passed"] == 3


def test_a_failed_pytest_run_retains_usable_counts(tmp_path):
    report_path = tmp_path / "counts.json"
    report_path.write_text(json.dumps(_report(passed=2, failed=1)), encoding="utf-8")
    step = check_all.Step("tests", ["pytest"], counts=report_path)
    status, _, report = check_all.step_status(step, 1)
    assert status == "FAIL" and report["selected"] == 3 and report["failed"] == 1


def test_a_filtered_green_pytest_run_is_not_full_acceptance(tmp_path):
    directory = _sample(tmp_path)
    done = _run(directory, ["-k", "test_passes"], with_plugin=True)
    assert done.returncode == 0
    report_path = directory / "counts.json"
    observed = json.loads(report_path.read_text(encoding="utf-8"))
    assert observed["selected"] == 1 and observed["deselected"] == 6
    step = check_all.Step("tests", ["pytest"], counts=report_path)
    status, detail, _ = check_all.step_status(step, done.returncode)
    assert status == "FAIL"
    assert "deselected" in detail


def test_a_step_runs_when_the_platform_has_no_sighup(monkeypatch):
    registered = []
    monkeypatch.setattr(
        check_all,
        "signal",
        SimpleNamespace(
            SIGTERM=15,
            getsignal=lambda signum: None,
            signal=lambda signum, handler: registered.append(signum),
        ),
    )
    done = check_all.run_step([sys.executable, "-c", "print('completed')"], {})
    assert done.returncode == 0
    assert done.stdout.strip() == "completed"
    assert registered == [15, 15]


def test_a_broken_counts_report_makes_the_whole_run_fail(tmp_path, monkeypatch, capsys):
    """End to end: pytest exits 0, the report is unreadable, and the run is not green."""
    report = tmp_path / "counts.json"
    report.write_text("{not json", encoding="utf-8")
    broken = check_all.Step("tests", [sys.executable, "-c", "pass"], counts=report)
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    monkeypatch.setattr(check_all, "steps", lambda output, **kwargs: [broken])
    monkeypatch.setattr(check_all.shutil, "which", lambda name: "/usr/bin/uv")

    assert check_all.main() == 1
    printed = capsys.readouterr().out
    assert "FAIL  tests" in printed
    assert "test counts unusable" in printed
    assert "FAILED: ['tests']" in printed


def test_summary_carries_both_the_step_and_the_test_counts():
    report = _report(skipped=1, passed=2, skip_reasons={"no engine": ["tests/a.py::test_x"]})
    line = check_all.counts_summary(9, 10, report)
    assert line.startswith("steps 9/10 passed; tests collected 3, selected 3")
    assert "skipped 1" in line
    assert "no engine (1)" in line


def test_zero_execution_counts_do_not_support_a_green(tmp_path):
    report = _report(collected=0, selected=0, passed=0)
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(report))
    with pytest.raises(check_all.CountsError, match="no tests"):
        check_all.read_counts(path)


def test_all_skipped_tests_do_not_support_a_green(tmp_path):
    path = tmp_path / "counts.json"
    path.write_text(
        json.dumps(_report(passed=0, skipped=3, skip_reasons={"absent": ["a", "b", "c"]}))
    )
    with pytest.raises(check_all.CountsError, match="no tests executed"):
        check_all.read_counts(path)


def test_a_blank_skip_reason_is_refused(tmp_path):
    """A test that did not run needs a reason a reader can check, not an empty string."""
    report = _report(passed=0, skipped=1, collected=1, selected=1, skip_reasons={"": ["a"]})
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(report))
    with pytest.raises(check_all.CountsError, match="skip reason is blank"):
        check_all.read_counts(path)


def test_a_placeholder_skip_reason_is_refused(tmp_path):
    """Bare labels such as ``skip`` or ``n/a`` name nothing that can be audited."""
    report = _report(passed=0, skipped=1, collected=1, selected=1, skip_reasons={"n/a": ["a"]})
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(report))
    with pytest.raises(check_all.CountsError, match="bare placeholder"):
        check_all.read_counts(path)


def test_a_blank_xfail_reason_is_refused(tmp_path):
    report = _report(passed=0, xfailed=1, collected=1, selected=1)
    for phase in report["results"][0]["phases"]:
        if "wasxfail" in phase:
            phase["wasxfail"] = ""
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(report))
    with pytest.raises(check_all.CountsError, match="xfail reason is blank"):
        check_all.read_counts(path)


def test_an_xfail_reason_that_is_not_the_marker_reason_is_refused(tmp_path):
    """The recorded skip reason has to be the marker reason, so the two cannot drift apart."""
    report = _report(passed=0, xfailed=1, collected=1, selected=1)
    node = report["selected_nodeids"][0]
    for phase in report["results"][0]["phases"]:
        if phase["outcome"] == "skipped":
            phase["reason"] = "a different story"
    report["skip_reasons"] = {"a different story": [node]}
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(report))
    with pytest.raises(check_all.CountsError, match="xfail reason disagrees"):
        check_all.read_counts(path)


def test_exit_status_one_without_any_failure_is_refused(tmp_path):
    """A non-zero pytest exit status must be explained by a failed or error outcome."""
    report = _report()
    report["pytest_exitstatus"] = 1
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(report))
    with pytest.raises(check_all.CountsError, match="exit status 1 without failed/error"):
        check_all.read_counts(path)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provenance_result(tmp_path):
    """A v2 result envelope that binds the scripts, one step log and its own digest."""
    log = tmp_path / "step-00.log"
    log.write_text("complete fixture output\n", encoding="utf-8")
    result = {
        "schema": "scirel.acceptance.v2",
        "exclusive": {
            "token_sha256": "a" * 64,
            "record": str(tmp_path / "acceptance-exclusive"),
            "present": True,
        },
        "provenance": {
            "check_all_sha256": _sha(SCRIPTS / "check_all.py"),
            "counts_plugin_sha256": _sha(SCRIPTS / "scirel_pytest_counts.py"),
        },
        "steps": [{"name": "tests", "log": str(log), "log_sha256": _sha(log)}],
    }
    path = tmp_path / "result.json"
    _write_result(path, result)
    return path, result


def _write_result(path, result):
    path.write_text(json.dumps(result), encoding="utf-8")
    path.with_name(path.name + ".sha256").write_text(_sha(path) + "\n", encoding="utf-8")


def _provenance_status(path, result):
    return check_all.validate_provenance(
        result, report_path=path, check_all_path=SCRIPTS / "check_all.py"
    )


def test_a_v2_result_with_its_sidecar_is_accepted(tmp_path):
    path, result = _provenance_result(tmp_path)
    assert _provenance_status(path, result) == "verified_v2"


def test_a_v2_result_without_a_credential_digest_is_refused(tmp_path):
    path, result = _provenance_result(tmp_path)
    result.pop("exclusive")
    _write_result(path, result)
    with pytest.raises(ValueError, match="no exclusive lock credential"):
        _provenance_status(path, result)


def test_a_v2_result_with_a_blank_credential_digest_is_refused(tmp_path):
    path, result = _provenance_result(tmp_path)
    result["exclusive"]["token_sha256"] = ""
    _write_result(path, result)
    with pytest.raises(ValueError, match="no exclusive lock credential"):
        _provenance_status(path, result)


def test_a_step_log_changed_after_the_run_is_refused(tmp_path):
    path, result = _provenance_result(tmp_path)
    Path(result["steps"][0]["log"]).write_text("rewritten after the run\n", encoding="utf-8")
    with pytest.raises(ValueError, match="log_sha256 disagrees"):
        _provenance_status(path, result)


def test_a_v2_result_without_its_sidecar_is_refused(tmp_path):
    path, result = _provenance_result(tmp_path)
    path.with_name(path.name + ".sha256").unlink()
    with pytest.raises(ValueError, match="no sidecar digest"):
        _provenance_status(path, result)


def test_a_sidecar_that_disagrees_with_the_result_is_refused(tmp_path):
    path, result = _provenance_result(tmp_path)
    path.with_name(path.name + ".sha256").write_text("0" * 64 + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sidecar digest disagrees"):
        _provenance_status(path, result)


def test_a_producer_digest_that_disagrees_with_the_script_is_refused(tmp_path):
    path, result = _provenance_result(tmp_path)
    result["provenance"]["check_all_sha256"] = "0" * 64
    _write_result(path, result)
    with pytest.raises(ValueError, match="check_all_sha256 disagrees"):
        _provenance_status(path, result)


def test_a_v1_receipt_is_refused_by_default(tmp_path):
    """A forged v1 and a genuine historical v1 are indistinguishable, so neither is evidence."""
    path = tmp_path / "result.json"
    result = {"schema": "scirel.acceptance.v1", "steps": []}
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="v1 receipt cannot serve as new evidence"):
        _provenance_status(path, result)


def test_a_v1_receipt_is_readable_only_with_the_legacy_switch(tmp_path):
    path = tmp_path / "result.json"
    result = {"schema": "scirel.acceptance.v1", "steps": []}
    path.write_text(json.dumps(result), encoding="utf-8")
    tag = check_all.validate_provenance(
        result,
        report_path=path,
        check_all_path=SCRIPTS / "check_all.py",
        allow_legacy_receipts=True,
    )
    assert tag == "legacy_unprovenanced"


def test_editing_a_field_and_resealing_the_sidecar_is_accepted(tmp_path):
    """The documented boundary: this is not a signature, so a resealed forgery passes.

    Encoded as a test so the SKILL.md matrix cell cannot drift into a claim the code
    does not support.
    """
    path, result = _provenance_result(tmp_path)
    result["exit_code"] = 0
    result["steps"][0]["status"] = "PASS"
    result["exclusive"]["token_sha256"] = "b" * 64
    _write_result(path, result)
    assert _provenance_status(path, result) == "verified_v2"


def test_the_written_result_carries_v2_provenance_and_a_sidecar(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SCIREL_EXCLUSIVE_TOKEN", "fixture-token")
    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    assert check_all.main(path) == 0
    result = json.loads(path.read_text())
    assert result["schema"] == "scirel.acceptance.v2"
    assert result["exclusive"]["present"] is True
    assert result["exclusive"]["token_sha256"] == hashlib.sha256(b"fixture-token").hexdigest()
    assert result["provenance"]["check_all_sha256"] == _sha(SCRIPTS / "check_all.py")
    assert all(_sha(Path(step["log"])) == step["log_sha256"] for step in result["steps"])
    # Wall-clock observation only: recorded so a slow step can be found, never compared.
    assert all(isinstance(step["seconds"], float) and step["seconds"] >= 0
               for step in result["steps"])
    sidecar = path.with_name(path.name + ".sha256")
    assert sidecar.read_text().strip() == _sha(path)
    assert f"RESULT SHA256 {_sha(path)}" in capsys.readouterr().out
    assert (
        check_all.validate_provenance(
            result, report_path=path, check_all_path=SCRIPTS / "check_all.py"
        )
        == "verified_v2"
    )


def _git(root, *arguments):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "fixture",
        "GIT_COMMITTER_NAME": "fixture",
        "GIT_AUTHOR_EMAIL": "fixture@invalid",
        "GIT_COMMITTER_EMAIL": "fixture@invalid",
    }
    return subprocess.run(
        ["git", *arguments], cwd=root, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def _candidate(root):
    _git(root, "init", "-q")
    (root / ".gitignore").write_text(".runtime/\n")
    (root / "uv.lock").write_text("fixture lock\n")
    (root / ".python-version").write_text("fixture python\n")
    (root / "tracked.txt").write_text("original\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture candidate")


def _mini_acceptance(root, monkeypatch, *, counts_report=None):
    """Run the real reporting loop with one tiny subprocess, never the full suite."""
    _candidate(root)
    monkeypatch.setattr(check_all, "ROOT", root)

    def plan(output, **kwargs):
        counts = output / "tests-counts.json"
        code = (
            f"from pathlib import Path; Path({str(counts)!r}).write_text({json.dumps(counts_report or _report())!r}); "
            "print('complete fixture output')"
        )
        return [check_all.Step("tests", [sys.executable, "-B", "-c", code], counts=counts)]

    monkeypatch.setattr(check_all, "steps", plan)
    return root / ".runtime/logs/result.json", plan


def test_report_binds_real_candidate_environment_and_started_argv(tmp_path, monkeypatch, capsys):
    import hashlib

    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    launched = []
    original = check_all.run_step

    def execute(command, env):
        launched.append(list(command))
        return original(command, env)

    monkeypatch.setattr(check_all, "run_step", execute)
    identity = check_all.candidate_identity(tmp_path)
    assert identity["commit"] == _git(tmp_path, "rev-parse", "HEAD")
    assert identity["tree"] == _git(tmp_path, "rev-parse", "HEAD^{tree}")
    assert identity["dirty"] is False
    assert check_all.main(path, run_id="fixture invocation") == 0
    result = json.loads(path.read_text())
    assert result["candidate"] == {"before": identity, "after": identity}
    assert result["run_id"] == "fixture invocation"
    assert result["evidence"] == "clean_candidate"
    environment = result["environment"]["before"]
    assert environment == result["environment"]["after"]
    assert set(environment) == {
        "python",
        "platform",
        "architecture",
        "uv_lock_sha256",
        "python_version_sha256",
    }
    assert set(environment["python"]) == {"implementation", "version"}
    assert (
        environment["uv_lock_sha256"]
        == hashlib.sha256((tmp_path / "uv.lock").read_bytes()).hexdigest()
    )
    assert (
        environment["python_version_sha256"]
        == hashlib.sha256((tmp_path / ".python-version").read_bytes()).hexdigest()
    )
    assert environment["python"]["version"] == ".".join(map(str, sys.version_info[:3]))
    (record,) = result["steps"]
    assert record["started"] is True
    assert record["argv"] == launched[0]
    assert Path(record["log"]).read_text() == "complete fixture output\n"
    assert result["tests"]["selected"] == 3
    assert capsys.readouterr().out.rstrip().endswith("ALL GREEN")


@pytest.mark.parametrize(
    "edit",
    ["commit", "tree", "dirty", "dirty content", "untracked content", "index", "staged content"],
)
def test_identity_drift_cannot_be_green(tmp_path, monkeypatch, edit):
    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    if edit == "dirty content":
        (tmp_path / "tracked.txt").write_text("first edit\n")
    if edit == "untracked content":
        (tmp_path / "extra.txt").write_text("first edit\n")
    if edit == "staged content":
        (tmp_path / "tracked.txt").write_text("first index edit\n")
        _git(tmp_path, "add", "tracked.txt")
        (tmp_path / "tracked.txt").write_text("working edit\n")
    original = check_all.run_step

    def execute(command, env):
        done = original(command, env)
        if edit == "commit":
            _git(tmp_path, "commit", "--allow-empty", "-qm", "same tree new commit")
        elif edit in ("index", "staged content"):
            (tmp_path / "tracked.txt").write_text("staged change\n")
            _git(tmp_path, "add", "tracked.txt")
            if edit == "staged content":
                (tmp_path / "tracked.txt").write_text("working edit\n")
        else:
            (tmp_path / ("extra.txt" if edit == "untracked content" else "tracked.txt")).write_text(
                "second edit\n"
            )
            if edit == "tree":
                _git(tmp_path, "add", "tracked.txt")
                _git(tmp_path, "commit", "-qm", "new tree")
        return done

    monkeypatch.setattr(check_all, "run_step", execute)
    assert check_all.main(path) == 1
    result = json.loads(path.read_text())
    assert result["evidence"] == "invalid"
    assert result["candidate"]["before"] != result["candidate"]["after"]
    if edit == "commit":
        assert result["candidate"]["before"]["tree"] == result["candidate"]["after"]["tree"]


def test_stable_dirty_candidate_is_development_only(tmp_path, monkeypatch, capsys):
    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    (tmp_path / "tracked.txt").write_text("development edit\n")
    assert check_all.main(path) == 0
    result = json.loads(path.read_text())
    assert result["evidence"] == "development"
    assert result["candidate"]["before"] == result["candidate"]["after"]
    assert "ALL GREEN" not in capsys.readouterr().out


def test_all_skipped_run_retains_counts_and_reasons_while_failing(tmp_path, monkeypatch, capsys):
    counts = _report(passed=0, skipped=3, skip_reasons={"absent": ["a", "b", "c"]})
    path, _ = _mini_acceptance(tmp_path, monkeypatch, counts_report=counts)
    assert check_all.main(path) == 1
    result = json.loads(path.read_text())
    assert result["tests"] == counts
    assert result["steps"][0]["status"] == "FAIL"
    output = capsys.readouterr().out
    assert "skipped 3" in output and "SKIP  absent  (3)" in output
    assert "ALL GREEN" not in output


@pytest.mark.parametrize("missing", ["uv.lock", ".python-version", "git"])
def test_missing_binding_cannot_be_green(tmp_path, monkeypatch, missing):
    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    if missing == "git":

        def unavailable(root):
            raise check_all.BindingError("git identity command could not start")

        monkeypatch.setattr(check_all, "candidate_identity", unavailable)
    else:
        (tmp_path / missing).unlink()
    assert check_all.main(path) == 1
    result = json.loads(path.read_text())
    assert result["binding_errors"]
    assert result["evidence"] == "invalid"


def test_lock_digest_drift_cannot_be_green(tmp_path, monkeypatch):
    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    original = check_all.run_step

    def execute(command, env):
        done = original(command, env)
        (tmp_path / "uv.lock").write_text("changed lock\n")
        return done

    monkeypatch.setattr(check_all, "run_step", execute)
    assert check_all.main(path) == 1
    result = json.loads(path.read_text())
    assert result["environment"]["before"] != result["environment"]["after"]


def test_missing_uv_records_planned_argv_without_claiming_a_start(tmp_path, monkeypatch):
    path, plan = _mini_acceptance(tmp_path, monkeypatch)
    monkeypatch.setattr(check_all.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        check_all,
        "steps",
        lambda output, **kwargs: [
            *plan(output),
            check_all.Step("lint", ["uv", "run", "ruff", "check"], requires_uv=True),
        ],
    )
    assert check_all.main(path) == 1
    tests, lint = json.loads(path.read_text())["steps"]
    assert tests["started"] is True
    assert lint["status"] == "NOT_RUN" and lint["returncode"] is None
    assert lint["started"] is False and lint["argv"] == ["uv", "run", "ruff", "check"]
    assert "uv is not on PATH" in lint["detail"]


def test_failed_spawn_does_not_claim_execution(tmp_path, monkeypatch):
    path, _ = _mini_acceptance(tmp_path, monkeypatch)

    def cannot_start(command, env):
        raise check_all.StepStartError("fixture executable absent")

    monkeypatch.setattr(check_all, "run_step", cannot_start)
    assert check_all.main(path) == 1
    (record,) = json.loads(path.read_text())["steps"]
    assert record["started"] is False and record["returncode"] is None
    assert record["status"] == "NOT_RUN"
    assert record["argv"][0] == sys.executable


def test_interrupted_step_retains_output_and_cannot_resume_the_plan(tmp_path, monkeypatch):
    path, plan = _mini_acceptance(tmp_path, monkeypatch)
    monkeypatch.setattr(
        check_all,
        "steps",
        lambda output, **kwargs: [*plan(output), check_all.Step("later", ["must-not-start"])],
    )

    def interrupted(command, env):
        raise check_all.StepInterrupted(
            subprocess.CompletedProcess(command, 130, "before interrupt\n", "")
        )

    monkeypatch.setattr(check_all, "run_step", interrupted)
    assert check_all.main(path) == 1
    first, later = json.loads(path.read_text())["steps"]
    assert first["started"] is True and first["status"] == "FAIL"
    assert Path(first["log"]).read_text() == "before interrupt\n"
    assert later["status"] == "NOT_RUN" and later["started"] is False


def test_an_old_green_result_is_never_overwritten_or_used(tmp_path, monkeypatch):
    path, _ = _mini_acceptance(tmp_path, monkeypatch)
    assert check_all.main(path) == 0
    original = path.read_bytes()
    assert check_all.main(path) == 2
    assert path.read_bytes() == original


@pytest.mark.parametrize("marker", ['skip(reason="fixture")', 'xfail(run=False, reason="fixture")'])
def test_a_suite_that_never_calls_a_test_body_is_not_green(tmp_path, marker):
    (tmp_path / "test_sample.py").write_text(
        f"import pytest\n@pytest.mark.{marker}\ndef test_not_called():\n    assert False\n"
    )
    done = _run(tmp_path, [], with_plugin=True)
    assert done.returncode == 0, done.stdout + done.stderr
    with pytest.raises(check_all.CountsError, match="no tests executed"):
        check_all.read_counts(tmp_path / "counts.json")


def test_spawn_failure_is_distinct_from_a_started_process(tmp_path, monkeypatch):
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    with pytest.raises(check_all.StepStartError):
        check_all.run_step([str(tmp_path / "missing-executable")], {})


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal fixture")
def test_run_step_retains_output_when_its_child_interrupts_it(tmp_path):
    # A separate driver receives the signal, never the pytest process or its outer dev.py lock.
    child = "import os, signal; print('before termination', flush=True); os.kill(os.getppid(), signal.SIGTERM)"
    driver = (
        f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import check_all\n"
        "try:\n"
        f"    check_all.run_step([sys.executable, '-B', '-c', {child!r}], {{}})\n"
        "except check_all.StepInterrupted as error:\n"
        "    print(error.completed.returncode)\n"
        "    print(error.completed.stdout, end='')\n"
        "else:\n"
        "    raise AssertionError('child did not interrupt the driver')\n"
    )
    done = subprocess.run(
        [sys.executable, "-B", "-c", driver], cwd=tmp_path, capture_output=True, text=True
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.splitlines() == [str(128 + 15), "before termination"]


def test_full_suite_discovery_cannot_be_replaced_by_smoke_testpaths(tmp_path, monkeypatch):
    (tmp_path / "tests").mkdir()
    (tmp_path / "smoke").mkdir()
    (tmp_path / "tests/test_regression.py").write_text(
        "def test_real_regression():\n    assert False\n"
    )
    (tmp_path / "smoke/test_smoke.py").write_text("def test_smoke():\n    assert True\n")
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths=["smoke"]\n')
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    step = check_all.steps(tmp_path)[0]
    done = subprocess.run(
        step.command, cwd=tmp_path, env={**os.environ, **step.env}, capture_output=True, text=True
    )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "test_real_regression" in done.stdout


EXECUTION_SAMPLE = (
    SAMPLE
    + """

@pytest.mark.xfail(run=False, reason="body must not run")
def test_xfail_without_call():
    raise AssertionError("unreachable body")


@pytest.fixture
def broken_teardown():
    yield
    raise RuntimeError("teardown fails on purpose")


def test_teardown_error(broken_teardown):
    assert True
"""
)


def test_same_run_records_selected_identities_final_outcomes_and_phases(tmp_path):
    (tmp_path / "test_sample.py").write_text(EXECUTION_SAMPLE)
    done = _run(tmp_path, [], with_plugin=True)
    assert done.returncode == 1
    report = check_all.read_counts(tmp_path / "counts.json")
    assert report["schema"] == 2
    selected = report["selected_nodeids"]
    assert len(selected) == len(set(selected)) == report["selected"] == 9
    results = {item["nodeid"]: item for item in report["results"]}
    assert list(results) == selected
    expected = {
        "test_passes": "passed",
        "test_skipped": "skipped",
        "test_xfails": "xfailed",
        "test_xpasses": "xpassed",
        "test_strict_xpass_is_a_failure": "failed",
        "test_errors": "error",
        "test_fails": "failed",
        "test_xfail_without_call": "xfailed",
        "test_teardown_error": "error",
    }
    assert {node.split("::")[-1]: item["outcome"] for node, item in results.items()} == expected
    by_name = {node.split("::")[-1]: item for node, item in results.items()}
    for name in ("test_skipped", "test_errors", "test_xfail_without_call"):
        assert "call" not in [p["when"] for p in by_name[name]["phases"]]
    teardown = by_name["test_teardown_error"]
    assert [(p["when"], p["outcome"]) for p in teardown["phases"]] == [
        ("setup", "passed"),
        ("call", "passed"),
        ("teardown", "failed"),
    ]
    assert report["error"] == 2 and report["passed"] == 1
    assert report["xfailed"] == 2 and report["collection_finished"] is True
    assert report["collection_reports"] == []


@pytest.mark.parametrize(
    "mode", ["collection", "interrupt", "teardown interrupt", "maxfail", "duplicate"]
)
def test_incomplete_or_duplicate_real_runs_retain_observations_and_are_red(tmp_path, mode):
    source = "def test_first():\n    assert True\n\ndef test_later():\n    assert True\n"
    extra = []
    if mode == "collection":
        source = "raise RuntimeError('collection failed on purpose')\n"
    elif mode == "interrupt":
        source = source.replace("assert True", "raise KeyboardInterrupt", 1)
    elif mode == "teardown interrupt":
        source = (
            "import pytest\n@pytest.fixture\ndef cleanup():\n    yield\n    raise KeyboardInterrupt\n"
            "def test_first(cleanup):\n    assert True\n"
        )
    elif mode == "maxfail":
        source = source.replace("assert True", "assert False", 1)
        extra = ["-x"]
    elif mode == "duplicate":
        (tmp_path / "conftest.py").write_text(
            "def pytest_collection_modifyitems(items):\n    items.append(items[0])\n"
        )
    (tmp_path / "test_sample.py").write_text(source)
    done = _run(tmp_path, extra, with_plugin=True)
    report = json.loads((tmp_path / "counts.json").read_text())
    assert report["consistent"] is False
    assert report["pytest_exitstatus"] == done.returncode
    assert "selected_nodeids" in report and "results" in report
    if mode == "collection":
        assert report["collection_reports"][0]["outcome"] == "failed"
    if mode in ("interrupt", "teardown interrupt", "maxfail"):
        assert any(item["outcome"] is None for item in report["results"])
    if mode == "teardown interrupt":
        assert report["passed"] == 0
        assert report["results"][0]["phases"][-1] == {"when": "call", "outcome": "passed"}
    status, _, _ = check_all.step_status(
        check_all.Step("tests", ["pytest"], counts=tmp_path / "counts.json"), done.returncode
    )
    assert status == "FAIL"


def test_collection_skip_is_retained_separately_from_selected_test_outcomes(tmp_path):
    (tmp_path / "test_sample.py").write_text(
        "import pytest\npytest.skip('optional module unavailable', allow_module_level=True)\n"
    )
    (tmp_path / "test_other.py").write_text("def test_passes():\n    assert True\n")
    done = _run(tmp_path, [str(tmp_path / "test_other.py")], with_plugin=True)
    assert done.returncode == 0
    counts = check_all.read_counts(tmp_path / "counts.json")
    assert counts["selected"] == counts["passed"] == 1
    assert counts["skipped"] == 0 and counts["skip_reasons"] == {}
    (collection,) = counts["collection_reports"]
    assert collection["outcome"] == "skipped"
    assert "optional module unavailable" in collection["reason"]
    assert collection["nodeid"].endswith("test_sample.py")


def _real_passing_record(tmp_path):
    (tmp_path / "test_sample.py").write_text(
        "def test_a():\n    assert True\n\ndef test_b():\n    assert True\n"
    )
    assert _run(tmp_path, [], with_plugin=True).returncode == 0
    return json.loads((tmp_path / "counts.json").read_text())


@pytest.mark.parametrize(
    "defect",
    [
        "missing selection",
        "duplicate selection",
        "missing result",
        "duplicate result",
        "wrong identity",
        "wrong outcome",
        "missing call",
        "duplicate phase",
        "wrong phase",
        "missing teardown",
        "wrong skip reasons",
        "wrong exit",
        "collection failure",
        "unfinished collection",
        "old schema",
    ],
)
def test_forged_execution_records_make_the_standard_reporting_loop_red(
    tmp_path, monkeypatch, capsys, defect
):
    counts = _real_passing_record(tmp_path)
    if defect == "missing selection":
        del counts["selected_nodeids"]
    elif defect == "duplicate selection":
        counts["selected_nodeids"][1] = counts["selected_nodeids"][0]
    elif defect == "missing result":
        counts["results"].pop()
    elif defect == "duplicate result":
        counts["results"][1] = counts["results"][0]
    elif defect == "wrong identity":
        counts["results"][0]["nodeid"] = "test_sample.py::unselected"
    elif defect == "wrong outcome":
        counts["results"][0]["outcome"] = "xfailed"
    elif defect == "missing call":
        counts["results"][0]["phases"].pop(1)
    elif defect == "duplicate phase":
        counts["results"][0]["phases"].append(counts["results"][0]["phases"][0])
    elif defect == "wrong phase":
        counts["results"][0]["phases"][0]["when"] = "unknown"
    elif defect == "missing teardown":
        counts["results"][0]["phases"].pop()
    elif defect == "wrong skip reasons":
        counts["skip_reasons"] = {"forged": [counts["selected_nodeids"][0]]}
    elif defect == "wrong exit":
        counts["pytest_exitstatus"] = 2
    elif defect == "collection failure":
        counts["collection_reports"] = [
            {"nodeid": "bad.py", "outcome": "failed", "reason": "broken"}
        ]
    elif defect == "unfinished collection":
        counts["collection_finished"] = False
    elif defect == "old schema":
        counts["schema"] = 1
    path, _ = _mini_acceptance(tmp_path, monkeypatch, counts_report=counts)
    assert check_all.main(path) == 1
    result = json.loads(path.read_text())
    assert result["steps"][0]["status"] == "FAIL"
    assert result["exit_code"] == 1 and result["evidence"] == "invalid"
    assert "ALL GREEN" not in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["passed", "collection", "interrupt", "call and teardown"])
def test_standard_result_retains_the_real_run_records_after_temporary_counts_are_removed(
    tmp_path, monkeypatch, mode
):
    source = "def test_a():\n    assert True\n\ndef test_b():\n    assert True\n"
    if mode == "collection":
        source = "raise RuntimeError('broken collection')\n"
    elif mode == "interrupt":
        source = source.replace("assert True", "raise KeyboardInterrupt", 1)
    elif mode == "call and teardown":
        source = (
            "import pytest\n@pytest.fixture\ndef cleanup():\n    yield\n    assert False\n"
            "def test_both_fail(cleanup):\n    assert False\n"
        )
    (tmp_path / "test_sample.py").write_text(source)
    _candidate(tmp_path)
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    observations = []

    def plan(output, **kwargs):
        counts = output / "tests-counts.json"
        observations.append(counts)
        return [
            check_all.Step(
                "tests",
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "pytest",
                    "test_sample.py",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "-p",
                    "scirel_pytest_counts",
                    f"--scirel-counts={counts}",
                ],
                counts=counts,
                env=_plugins_env(),
            )
        ]

    monkeypatch.setattr(check_all, "steps", plan)
    path = tmp_path / ".runtime/logs/result.json"
    assert check_all.main(path) == (0 if mode == "passed" else 1)
    result = json.loads(path.read_text())
    assert not observations[0].exists()
    counts = result["tests"]
    assert counts["schema"] == 2
    assert counts["pytest_exitstatus"] == result["steps"][0]["returncode"]
    assert counts["consistent"] is (mode in ("passed", "call and teardown"))
    assert Path(result["steps"][0]["log"]).is_file()
    if mode == "passed":
        assert counts["selected_nodeids"] == [item["nodeid"] for item in counts["results"]]
        assert len(counts["results"]) == counts["passed"] == 2
    elif mode == "collection":
        assert counts["collection_reports"][0]["outcome"] == "failed"
    elif mode == "interrupt":
        assert all(item["outcome"] is None for item in counts["results"])
    elif mode == "call and teardown":
        (item,) = counts["results"]
        assert item["outcome"] == "error" and counts["error"] == 1 and counts["failed"] == 0
        assert [(p["when"], p["outcome"]) for p in item["phases"]] == [
            ("setup", "passed"),
            ("call", "failed"),
            ("teardown", "failed"),
        ]
