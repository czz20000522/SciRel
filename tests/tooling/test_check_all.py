"""check_all.py reports pytest counts, and refuses a report whose numbers do not add up."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/development/scirel-acceptance/scripts"


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
        "schema": 1,
        "pytest_exitstatus": 0,
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


def test_a_broken_counts_report_makes_the_whole_run_fail(tmp_path, monkeypatch, capsys):
    """End to end: pytest exits 0, the report is unreadable, and the run is not green."""
    report = tmp_path / "counts.json"
    report.write_text("{not json", encoding="utf-8")
    broken = check_all.Step("tests", [sys.executable, "-c", "pass"], counts=report)
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    monkeypatch.setattr(check_all, "steps", lambda output: [broken])
    monkeypatch.setattr(check_all.shutil, "which", lambda name: "/usr/bin/uv")

    assert check_all.main() == 1
    printed = capsys.readouterr().out
    assert "FAIL  tests" in printed
    assert "test counts unusable" in printed
    assert printed.rstrip().endswith("FAILED: ['tests']")


def test_summary_carries_both_the_step_and_the_test_counts():
    report = _report(skipped=1, passed=2, skip_reasons={"no engine": ["tests/a.py::test_x"]})
    line = check_all.counts_summary(9, 10, report)
    assert line.startswith("steps 9/10 passed; tests collected 3, selected 3")
    assert "skipped 1" in line
    assert "no engine (1)" in line
