"""Pin the observation-integrity checker in both directions.

The checker exists to stop one class of defect: a check whose output cannot distinguish
"it failed" from "it did not run". A guard that only proves it catches bad code is half a
guard, so every case here has a compliant counterpart that must stay clean.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_observation_integrity.py"

SILENT = """
import subprocess

def go():
    return subprocess.run(["git", "status"], check=True, capture_output=True, text=True).stdout
"""

CARRIES_STDERR = """
import subprocess

def go():
    try:
        return subprocess.run(["git", "status"], check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as failed:
        raise AssertionError(f"git failed with {failed.returncode}: {failed.stderr!r}")
"""

MARKER = "observation-integrity: no-stderr-on-purpose"


def _marked(reason: str) -> str:
    """Put the marker where the checker looks for it: on the line above the call.

    ``reason`` is the prose that turns the marker into a decision rather than an absence.
    An empty reason is the bare marker, which must not silence anything.
    """
    above = f"    # {MARKER} {reason}".rstrip() + "\n    return subprocess.run"
    return SILENT.replace("    return subprocess.run", above)


def _scan(tmp_path: Path, source: str) -> list[dict]:
    target = tmp_path / "sample.py"
    target.write_text(source, encoding="utf-8")
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import check_observation_integrity as checker
    finally:
        sys.path.pop(0)
    return checker.scan_text(str(target), source)


def test_a_captured_failure_without_stderr_is_reported(tmp_path):
    problems = _scan(tmp_path, SILENT)
    assert len(problems) == 1
    assert "stderr" in problems[0]["message"]


def test_carrying_stderr_into_the_error_is_clean(tmp_path):
    assert _scan(tmp_path, CARRIES_STDERR) == []


def test_a_marker_without_a_reason_does_not_silence_the_check(tmp_path):
    bare = _marked("")
    assert len(_scan(tmp_path, bare)) == 1


def test_a_marker_with_a_reason_is_accepted(tmp_path):
    assert _scan(tmp_path, _marked("the caller asserts on the exit code")) == []


def test_the_ratchet_blocks_a_file_that_grows_or_is_new():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import check_observation_integrity as checker
    finally:
        sys.path.pop(0)

    problems = [
        {"path": "a.py", "line": 1, "message": "x"},
        {"path": "a.py", "line": 2, "message": "x"},
        {"path": "b.py", "line": 3, "message": "x"},
    ]
    blocking, tolerated = checker.apply_baseline(problems, {"a.py": 2})
    assert [p["path"] for p in blocking] == ["b.py"]
    assert len(tolerated) == 2

    blocking, _ = checker.apply_baseline(problems, {"a.py": 1})
    assert {p["path"] for p in blocking} == {"a.py", "b.py"}


def test_the_repository_itself_passes_the_checker():
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(ROOT)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_an_unobservable_root_is_not_a_pass(tmp_path):
    """Scanning nothing must not print the same line as scanning cleanly."""
    empty = tmp_path / "empty"
    empty.mkdir()
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(empty)], capture_output=True, text=True, check=False
    )
    assert done.returncode == 2, done.stdout + done.stderr
    assert "nothing was observed" in done.stdout


def test_every_baseline_entry_states_a_reason():
    document = json.loads(
        (ROOT / "tools" / "docs" / "observation-baseline.json").read_text("utf-8")
    )
    entries = document["entries"]
    assert entries
    for entry in entries:
        assert entry["count"] >= 1
        assert len(entry["reason"]) >= 20, entry
