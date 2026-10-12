"""Behavior checks for bounded material reads and private worker file writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scientific-computation-asset-extraction/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


query = load("query_material")
guard = load("guard_worker_write")


@pytest.mark.parametrize("document,pointer,expected", [
    ({"milestones": {"M1": {"state": "active"}}}, "/milestones/M1/state", "active"),
    ({"milestones": [{"status": "partial"}]}, "/milestones/0/status", "partial"),
    ({"a/b": {"~name": 4}}, "/a~1b/~0name", 4),
    ([{"path": "source/field.py"}], "/0/path", "source/field.py"),
])
def test_literal_selectors_support_real_shape_variants(document, pointer, expected):
    assert query.resolve(document, pointer) == expected


def test_missing_state_never_becomes_completion(tmp_path):
    path = tmp_path / "progress.json"
    path.write_text(json.dumps({"schema": "checkpoint/v2", "milestones": {"M1": {"state": "active"}}}))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Missing field"):
        query.query(path, ["/milestones/M1/status"])
    with pytest.raises(ValueError, match="Schema mismatch"):
        query.query(path, [], expected_schema="checkpoint/v1")
    assert path.read_bytes() == before
    old = hashlib.sha256(before).hexdigest()
    path.write_text('{"schema":"checkpoint/v2","milestones":{}}')
    with pytest.raises(ValueError, match="Material changed"):
        query.query(path, [], expected_sha256=old)


@pytest.mark.parametrize("pointer", ["/a~2b", "/a~", "/00", "/-1", "/99", "a"])
def test_bad_or_ambiguous_pointers_fail(pointer):
    with pytest.raises(ValueError):
        query.resolve([1, 2], pointer)


def test_bounded_query_does_not_truncate_or_print_large_payload(tmp_path):
    path = tmp_path / "capture.json"
    path.write_text(json.dumps({"capture": "x" * 10000, "state": "active"}))
    result = subprocess.run([sys.executable, str(SCRIPTS / "query_material.py"), str(path),
                             "--pointer", "/capture", "--max-output-bytes", "512"],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "Projection exceeds" in result.stdout and "x" * 100 not in result.stdout
    projected = query.query(path, ["/state"], include_shape=True)
    assert projected["values"] == {"/state": "active"}
    assert projected["shape"]["fields"]["capture"] == {"type": "string"}


def test_worker_write_hook_confines_native_file_tools(tmp_path):
    lane = tmp_path / "lanes/field"
    lane.mkdir(parents=True)
    shared = tmp_path / "bundle"
    shared.mkdir()
    assert guard.allowed(lane, "Write", {"file_path": "lanes/field/operator.py"}, tmp_path)
    assert guard.allowed(lane, "Edit", {"file_path": str(lane / "tests/test_field.py")}, tmp_path)
    for path in [shared / "operator.py", lane / "../other/operator.py", tmp_path / "source/field.py"]:
        assert not guard.allowed(lane, "Write", {"file_path": str(path)}, tmp_path)
    assert not guard.allowed(lane, "Bash", {"command": "true"}, tmp_path)
    assert not guard.allowed(lane, "NotebookEdit", {"file_path": str(lane / "x")}, tmp_path)
    link = lane / "link"
    link.symlink_to(shared, target_is_directory=True)
    assert not guard.allowed(lane, "Write", {"file_path": str(link / "x")}, tmp_path)
    event = {"tool_name": "Write", "tool_input": {"file_path": str(shared / "x")}, "cwd": str(tmp_path)}
    result = subprocess.run([sys.executable, str(SCRIPTS / "guard_worker_write.py"), str(lane)],
                            input=json.dumps(event), text=True, capture_output=True)
    assert result.returncode == 2 and "denied" in result.stderr
