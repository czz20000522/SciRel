"""Runtime construction uses captured contracts/readers, never a rendered snapshot.

All science records, source modules and ZIP members here are synthetic. The
full wheel inspector is replaced at its boundary because this fixture is not
an installable wheel; the public catalog, signature and catalog/wheel closure
validators, unchanged skill capture, publisher and exported CLI run normally.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_pure_delivery as delivery  # noqa: E402
from capability_catalog import PublicCatalog  # noqa: E402
from query import Consumer, encode, sha  # noqa: E402
import validate_installed_wheel  # noqa: E402

SOURCE = "0" * 40
ASSET = "scirel.synthetic.alpha"
NOTICE = b"Synthetic notice; no scientific validation.\n"


def _write(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def _document():
    port = {
        "name": "x",
        "description": "Synthetic input",
        "units": "1",
        "shape": "scalar",
        "dtype": "float",
        "required": True,
        "constraints": "Synthetic fixture only",
    }
    return {
        "schema": "scirel.asset-document",
        "asset_id": ASSET,
        "title": {"en": "Synthetic scalar", "zh": "合成示例"},
        "summary": "Synthetic fixture; no scientific validation.",
        "taxonomy": ["synthetic"],
        "aliases": ["synthetic", "alpha"],
        "identity": {
            "relation": "Synthetic relation",
            "direction": "input to output",
            "definition": "Synthetic scalar fixture",
            "model": "Synthetic algebra",
            "geometry": "scalar",
            "coordinates": "none",
            "boundary": "unknown",
            "assumptions": [],
        },
        "inputs": [port],
        "outputs": [{**port, "name": "value"}],
        "applicability": {
            "preconditions": ["Synthetic input"],
            "supported": ["Synthetic scalar"],
            "excluded": [],
        },
        "failure_semantics": {
            key: "Synthetic boundary"
            for key in ("invalid_input", "runtime_failure", "nonconvergence", "partial_results")
        },
        "public_api": {
            "python": {"module": "scirel.synthetic", "symbol": "alpha", "signature": "alpha(x)"}
        },
        "version": {"implementation_version": "0", "dependencies": []},
        "example": {
            "description": "Synthetic example",
            "code": "print(0)",
            "expected": "Synthetic output, no science claim",
        },
        "verification": {
            "scope": ["Synthetic fixture"],
            "tests": ["tests/test_synthetic.py::test_alpha"],
            "evidence_ceiling": "No scientific validation",
            "known_limitations": ["Synthetic fixture only"],
        },
    }


def _reader(document, contract):
    return {
        "asset_id": ASSET,
        "source_sha256": sha(contract),
        "summary": "合成示例",
        "definition": "合成定义",
        "model": "合成模型",
        "boundary": "未知",
        **{
            side: [
                {**port, "description": "合成端口", "dtype": "合成类型", "constraints": "仅测试"}
                for port in document[side]
            ]
            for side in ("inputs", "outputs")
        },
        "applicability": {"preconditions": ["合成输入"], "supported": ["合成标量"], "excluded": []},
        "verification": {
            "scope": ["合成示例"],
            "known_limitations": ["仅测试"],
            "evidence_ceiling": "未作科学验证",
        },
        "assumptions": [],
        "failure_semantics": {
            key: "合成边界"
            for key in ("invalid_input", "runtime_failure", "nonconvergence", "partial_results")
        },
        "example": {"description": "合成示例", "expected": "不作科学断言"},
    }


def _rewrite_contract(case, document):
    contract = encode(document)
    _write(case.source, "catalog/examples/" + ASSET + ".json", contract)
    _write(
        case.source,
        "tools/docs/zh/synthetic.json",
        encode(
            {
                "schema": "scirel.reader-translation",
                "language": "zh-CN",
                "records": [_reader(document, contract)],
            }
        ),
    )
    case.document, case.contract = document, contract


@pytest.fixture
def export_case(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _write(
        source,
        "catalog/review/excluded_from_package.json",
        '{"schema": "scirel.excluded-from-package", "ids": []}\n',
    )
    case = SimpleNamespace(
        source=source,
        wheel=tmp_path / "synthetic-0-py3-none-any.whl",
        output=tmp_path / "runtime",
        dirty=False,
    )
    _rewrite_contract(case, _document())
    _write(source, "licenses/NOTICE.txt", NOTICE)
    _write(source, "pyproject.toml", '[project]\nname = "synthetic"\nversion = "0"\n')
    for name in delivery.BUILD_INPUTS:
        _write(source, "scripts/" + name, (ROOT / "scripts" / name).read_bytes())
    _write(source, "tools/docs/mcp-requirements.txt", "mcp==2.3.0\nmcp-types==2.3.0\n")
    _write(source, "tests/test_synthetic.py", "def test_alpha():\n    pass\n")
    _write(source, "src/scirel/__init__.py", "__all__ = []\n")
    _write(
        source, "src/scirel/synthetic.py", '__all__ = ["alpha"]\n\ndef alpha(x):\n    return x\n'
    )
    case.skill = source / "skills/development/usage/scirel-solving"
    _write(
        case.skill,
        "SKILL.md",
        "---\nname: scirel-solving\ndescription: Synthetic method.\n---\n"
        "# Method\n\n[Checks](references/checks.md)\n",
    )
    _write(case.skill, "references/checks.md", "# Checks\n\n[Helper](../scripts/delivery.py)\n")
    _write(case.skill, "scripts/delivery.py", 'print("synthetic helper")\n')
    with ZipFile(case.wheel, "w") as wheel:
        wheel.writestr(
            "synthetic-0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: synthetic\nVersion: 0\n"
            "Requires-Python: >=3.11\nRequires-Dist: numpy==2.5.4\n\n",
        )
        wheel.writestr("synthetic-0.dist-info/licenses/licenses/NOTICE.txt", NOTICE)
        for path in sorted((source / "src/scirel").rglob("*.py")):
            wheel.writestr(path.relative_to(source / "src").as_posix(), path.read_bytes())
    module = ModuleType("scirel.synthetic")
    exec((source / "src/scirel/synthetic.py").read_bytes(), module.__dict__)
    monkeypatch.setitem(sys.modules, "scirel.synthetic", module)
    monkeypatch.setattr(delivery, "ROOT", source)
    monkeypatch.setattr(PublicCatalog, "_git_identity", lambda self: (SOURCE, case.dirty))
    real_run = subprocess.run

    def run(command, **kwargs):
        if command == ["git", "-C", str(source), "rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout=SOURCE + "\n")
        return real_run(command, **kwargs)

    monkeypatch.setattr(validate_installed_wheel.subprocess, "run", run)
    monkeypatch.setattr(
        delivery,
        "inspect_wheel",
        lambda path, **kwargs: {
            "status": "PASS",
            "sha256": sha(path.read_bytes()),
            "scope": "synthetic inspector boundary only",
        },
    )
    return case


def _cli(case, *arguments, expected_exit=0):
    identity = json.loads((case.output / "runtime.json").read_bytes())
    pins = (
        []
        if arguments[0] == "describe"
        else [
            "--expected-snapshot-sha256",
            identity["snapshot_sha256"],
            "--expected-wheel-sha256",
            identity["runtime"]["wheel_sha256"],
        ]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-B",
            str(case.output / "tools/query.py"),
            "--root",
            str(case.output),
            *arguments,
            *pins,
        ],
        cwd=case.output.parent,
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        check=False,
        timeout=20,
    )
    assert result.returncode == expected_exit, result.stderr or result.stdout
    assert not result.stderr
    return json.loads(result.stdout)


def test_runtime_from_original_contracts_and_bound_readers_is_standalone(export_case):
    case = export_case
    result = delivery.build(case.wheel, case.output)
    expected = {
        "runtime.json",
        "runtime-requirements.txt",
        "mcp-requirements.txt",
        "mcp-connections.json",
        "wheel/" + case.wheel.name,
        "tools/query.py",
        "tools/capability_query.py",
        "tools/consumer_tools.py",
        "tools/server.py",
        "skills/scirel-solving/SKILL.md",
        "skills/scirel-solving/references/checks.md",
        "skills/scirel-solving/scripts/delivery.py",
        "catalog/capability-index.json",
        "catalog/contracts/" + ASSET + ".json",
    }
    assert {
        path.relative_to(case.output).as_posix()
        for path in case.output.rglob("*")
        if path.is_file()
    } == expected
    identity = json.loads((case.output / "runtime.json").read_bytes())
    assert result["agent"] == identity
    assert identity["asset_count"] == 1 and identity["source_revision"] == SOURCE
    assert identity["snapshot_sha256"] == sha(
        encode({key: value for key, value in identity.items() if key != "snapshot_sha256"})
    )
    assert set(identity["files"]) == expected - {"runtime.json"}
    for relative, record in identity["files"].items():
        data = (case.output / relative).read_bytes()
        assert record == {"sha256": sha(data), "bytes": len(data)}
    assert (case.output / "catalog/contracts" / (ASSET + ".json")).read_bytes() == case.contract
    for relative in ("SKILL.md", "references/checks.md", "scripts/delivery.py"):
        assert (case.output / "skills/scirel-solving" / relative).read_bytes() == (
            case.skill / relative
        ).read_bytes()
    index = json.loads((case.output / "catalog/capability-index.json").read_bytes())
    assert index["assets"][0]["asset_id"] == ASSET
    assert "合成示例" in index["search_text"][ASSET]
    assert (case.output / "runtime-requirements.txt").read_text().splitlines()[-1] == "numpy==2.5.4"
    with ZipFile(case.output / "wheel" / case.wheel.name) as wheel:
        assert wheel.read("synthetic-0.dist-info/licenses/licenses/NOTICE.txt") == NOTICE
    closure = result["checks"]["source_closure"]
    assert closure["source_signature_check"] == "PASS"
    assert closure["catalog_wheel_closure"]["status"] == "PASS"
    assert closure["scientific_runtime_revalidated"] is False
    for relative in (
        "catalog/examples/" + ASSET + ".json",
        "tools/docs/zh/synthetic.json",
        "src/scirel/synthetic.py",
        "tests/test_synthetic.py",
    ):
        assert closure["source_inputs"][relative] == sha((case.source / relative).read_bytes())
    assert Consumer(case.output).verify()["files_verified"] == len(expected)
    assert _cli(case, "describe")["asset_count"] == 1
    assert _cli(case, "search", "--q", "合成示例")["result"]["items"][0]["asset_id"] == ASSET
    selected = _cli(case, "get", ASSET)
    assert selected["document"] == case.document
    assert selected["digests"]["catalog/contracts/" + ASSET + ".json"] == sha(case.contract)
    _write(case.output, "catalog/contracts/" + ASSET + ".json", b'{"asset_id":"changed"}\n')
    assert _cli(case, "get", ASSET, expected_exit=2)["outcome"] == "metadata_error"


@pytest.mark.parametrize(
    "relative",
    [
        "catalog/examples/" + ASSET + ".json",
        "tools/docs/zh/synthetic.json",
        "scripts/query.py",
        "tools/docs/mcp-requirements.txt",
        "skills/development/usage/scirel-solving/scripts/delivery.py",
        "tests/test_synthetic.py",
        "pyproject.toml",
    ],
)
def test_captured_runtime_inputs_cannot_drift_during_export(export_case, monkeypatch, relative):
    case = export_case
    original = delivery.inspect_wheel

    def change_after_capture(*args, **kwargs):
        result = original(*args, **kwargs)
        path = case.source / relative
        path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(delivery, "inspect_wheel", change_after_capture)
    with pytest.raises(ValueError, match="changed|closure failed"):
        delivery.build(case.wheel, case.output)
    assert not case.output.exists()
    assert not list(case.output.parent.glob(".scirel-runtime-stage-*"))


@pytest.mark.parametrize(
    "failure",
    [
        "signature",
        "reader_binding",
        "dependency",
        "dirty",
        "catalog_member_added",
        "reader_member_added",
        "helper_member_added",
    ],
)
def test_public_binding_and_membership_checks_fail_closed(export_case, monkeypatch, failure):
    case = export_case
    if failure == "signature":
        document = _document()
        document["public_api"]["python"]["signature"] = "alpha(x, y)"
        _rewrite_contract(case, document)
    elif failure == "reader_binding":
        reader_path = case.source / "tools/docs/zh/synthetic.json"
        payload = json.loads(reader_path.read_bytes())
        payload["records"][0]["source_sha256"] = "f" * 64
        reader_path.write_bytes(encode(payload))
    elif failure == "dependency":
        document = _document()
        document["version"]["dependencies"] = [{"asset_id": "scirel.synthetic.missing"}]
        _rewrite_contract(case, document)
    elif failure == "dirty":
        case.dirty = True
    else:
        original = delivery.inspect_wheel

        def add_after_capture(*args, **kwargs):
            result = original(*args, **kwargs)
            if failure == "catalog_member_added":
                _write(case.source, "catalog/examples/scirel.synthetic.new.json", "{}\n")
            elif failure == "reader_member_added":
                _write(case.source, "tools/docs/zh/new.json", "{}\n")
            else:
                _write(case.skill, "references/new.md", "# New method\n")
                entry = case.skill / "SKILL.md"
                entry.write_text(entry.read_text() + "\n[new](references/new.md)\n")
            return result

        monkeypatch.setattr(delivery, "inspect_wheel", add_after_capture)
    with pytest.raises(ValueError):
        delivery.build(case.wheel, case.output)
    assert not case.output.exists()


@pytest.mark.parametrize(
    "failure",
    ["inspector_fail", "wheel_hash", "missing_module", "module_bytes", "version", "notice"],
)
def test_exact_wheel_and_source_closure_reject_mismatches(export_case, monkeypatch, failure):
    case = export_case
    if failure in {"inspector_fail", "wheel_hash"}:
        monkeypatch.setattr(
            delivery,
            "inspect_wheel",
            lambda path, **kwargs: {
                "status": "FAIL" if failure == "inspector_fail" else "PASS",
                "sha256": "f" * 64,
            },
        )
    else:
        with ZipFile(case.wheel) as wheel:
            members = {name: wheel.read(name) for name in wheel.namelist()}
        if failure == "missing_module":
            del members["scirel/synthetic.py"]
        elif failure == "module_bytes":
            members["scirel/synthetic.py"] += b"# mismatched wheel bytes\n"
        elif failure == "version":
            key = "synthetic-0.dist-info/METADATA"
            members[key] = members[key].replace(b"Version: 0\n", b"Version: 1\n")
        else:
            members["synthetic-0.dist-info/licenses/licenses/NOTICE.txt"] = b"Wrong notice\n"
        with ZipFile(case.wheel, "w") as wheel:
            for name, data in members.items():
                wheel.writestr(name, data)
    with pytest.raises(ValueError):
        delivery.build(case.wheel, case.output)
    assert not case.output.exists()


def test_failed_stage_is_removed_without_publishing_a_partial_runtime(tmp_path, monkeypatch):
    def fail(wheel, output):
        output.mkdir()
        (output / "partial").write_bytes(b"incomplete")
        raise ValueError("synthetic staged failure")

    monkeypatch.setattr(delivery, "_export", fail)
    with pytest.raises(ValueError, match="synthetic staged failure"):
        delivery.build(tmp_path / "unused-wheel", tmp_path / "runtime")
    assert not list(tmp_path.iterdir())


def test_successful_stage_publishes_one_complete_runtime(tmp_path, monkeypatch):
    def export(wheel, output):
        output.mkdir()
        (output / "runtime.json").write_bytes(b"complete")
        return {"complete": True}

    monkeypatch.setattr(delivery, "_export", export)
    output = tmp_path / "runtime"
    assert delivery.build(tmp_path / "unused-wheel", output) == {"complete": True}
    assert (output / "runtime.json").read_bytes() == b"complete"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["runtime"]
    with pytest.raises(FileExistsError):
        delivery.build(tmp_path / "unused-wheel", output)
    assert (output / "runtime.json").read_bytes() == b"complete"
