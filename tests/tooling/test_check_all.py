"""check_all.py reports pytest counts, and refuses a report whose numbers do not add up."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

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
