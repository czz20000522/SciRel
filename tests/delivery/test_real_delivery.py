"""Consume one real current delivery, without checkout imports or substitute wheels.

Run on a clean committed candidate: build_pure_delivery binds that exact HEAD.
The module shares one wheel/catalog/index/three-skill export and an installation
under .runtime; TemporaryDirectory removes its owned artifacts after the run.
MCP remains optional via SCIREL_MCP_PYTHON, as in test_consumer_mcp.py.
These are delivery checks, not an independent physics evaluation.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = {"scirel-solving", "scirel-capability-discovery", "scirel-result-validation"}


def _run(argv, *, cwd, code=0, **kwargs):
    # Descendants inherit dev.py's project-local cache/temp locations and lock.
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTHONHOME", "SCIREL_REVIEW_HOLD"):
        env.pop(key, None)
    done = subprocess.run(
        list(map(str, argv)),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        **kwargs,
    )
    assert done.returncode == code, (done.args, done.returncode, done.stdout, done.stderr)
    return done


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _python(venv):
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@pytest.fixture(scope="module")
def real_delivery():
    status = _run(["git", "status", "--porcelain"], cwd=ROOT).stdout
    assert not status, "real delivery requires a clean committed candidate: " + status
    revision = _run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
    parent = ROOT / ".runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="real-delivery-", dir=parent) as temporary:
        work = Path(temporary)
        # A tracked source export keeps setuptools' build/egg-info inside .runtime.
        # This is the same HEAD, not a second clone or an invented wheel fixture.
        source_zip = work / "source.zip"
        _run(["git", "archive", "--format=zip", "--output", source_zip, revision], cwd=ROOT)
        source = work / "source"
        with ZipFile(source_zip) as archive:
            archive.extractall(source)
        wheels = work / "wheels"
        _run(["uv", "build", "--wheel", "--out-dir", wheels, source], cwd=ROOT)
        (wheel,) = wheels.glob("*.whl")
        package = work / "consumer"
        exported = _run(
            [
                sys.executable,
                "-B",
                ROOT / "scripts/build_pure_delivery.py",
                "--wheel",
                wheel,
                "--output",
                package,
            ],
            cwd=ROOT,
        )
        proof = json.loads(exported.stdout)
        identity = json.loads((package / "runtime.json").read_bytes())
        assert identity["source_revision"] == revision
        assert proof["snapshot_sha256"] == identity["snapshot_sha256"]
        assert proof["checks"]["wheel_inspection"]["status"] == "PASS"
        assert proof["checks"]["source_closure"]["source_signature_check"] == "PASS"
        delivered_wheel = package / "wheel" / identity["runtime"]["wheel"]
        assert _sha(wheel) == _sha(delivered_wheel) == identity["runtime"]["wheel_sha256"]

        venv = work / "installed"
        _run([sys.executable, "-I", "-B", "-m", "venv", venv], cwd=work)
        python = _python(venv)
        _run(["uv", "pip", "install", "--python", python, delivered_wheel], cwd=work)
        case = SimpleNamespace(
            work=work,
            package=package,
            python=python,
            venv=venv,
            wheel=delivered_wheel,
            identity=identity,
            revision=revision,
            proof=proof,
            query=package / "skills/scirel-capability-discovery/scripts/query.py",
            helper=package / "skills/scirel-solving/scripts/delivery.py",
            server=package / "skills/scirel-capability-discovery/scripts/server.py",
        )
        yield case
        assert _run(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip() == revision
        assert _run(["git", "status", "--porcelain"], cwd=ROOT).stdout == ""


def _query(case, *arguments, code=0):
    # -E -s ignores checkout Python paths and user site, while retaining the
    # actual delivered script's sibling imports. Default root is consumer cwd.
    done = _run(
        [case.python, "-E", "-s", "-B", case.query, *arguments], cwd=case.package, code=code
    )
    return json.loads(done.stdout)


def _pin_flags(case):
    return [
        "--expected-snapshot-sha256",
        case.identity["snapshot_sha256"],
        "--expected-wheel-sha256",
        case.identity["runtime"]["wheel_sha256"],
    ]


def _verify_package(case, *, code=0):
    # Invoke the exported Consumer, never the repository's query module.
    driver = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import query
assert Path(query.__file__).parent == Path(sys.argv[1])
try:
    print(json.dumps(query.Consumer(sys.argv[2]).verify()))
except (OSError, ValueError) as error:
    print(json.dumps({'error': str(error)}))
    raise SystemExit(2)
"""
    done = _run(
        [case.python, "-I", "-B", "-c", driver, case.query.parent, case.package],
        cwd=case.work,
        code=code,
    )
    return json.loads(done.stdout)


def test_real_export_and_installed_wheel(real_delivery, record_property):
    case = real_delivery
    identity = case.identity
    assert {p.name for p in (case.package / "skills").iterdir()} == SKILLS
    for skill in SKILLS:
        assert f"skills/{skill}/SKILL.md" in identity["files"]
    verified = _verify_package(case)
    assert verified["outcome"] == "ok"
    assert verified["files_verified"] == len(identity["files"]) + 1
    assert verified["snapshot_sha256"] == identity["snapshot_sha256"]
    assert verified["wheel_sha256"] == _sha(case.wheel)
    receipt_path = case.work / "installed-wheel.json"
    done = _run(
        [
            case.python,
            "-I",
            "-B",
            ROOT / "scripts/validate_installed_wheel.py",
            "--wheel",
            case.wheel,
            "--catalog-root",
            ROOT,
            "--source-revision",
            case.revision,
            "--expected-python",
            f"{sys.version_info.major}.{sys.version_info.minor}",
            "--output",
            receipt_path,
        ],
        cwd=case.work,
    )
    receipt = json.loads(done.stdout)
    assert receipt == json.loads(receipt_path.read_bytes())
    assert receipt["status"] == "PASS", receipt["errors"]
    assert receipt["runtime"]["is_virtualenv"] is True
    assert receipt["runtime"]["external_site_paths"] == []
    assert Path(receipt["runtime"]["prefix"]) == case.venv
    assert receipt["package"]["within_sys_prefix"] is True
    assert receipt["package"]["metadata_within_sys_prefix"] is True
    assert receipt["package"]["in_source_tree"] is False
    assert Path(receipt["package"]["module_file"]).is_relative_to(case.venv)
    assert receipt["artifact"]["sha256"] == identity["runtime"]["wheel_sha256"]
    assert receipt["catalog_wheel_closure"]["status"] == "PASS"
    assert receipt["pip_check"]["status"] == "PASS"
    assert receipt["dependencies"] and all(d["status"] == "PASS" for d in receipt["dependencies"])
    for key in ("source_revision", "snapshot_sha256"):
        record_property(key, identity[key])
    record_property("wheel_sha256", _sha(case.wheel))
    print(
        json.dumps(
            {
                "source_revision": case.revision,
                "snapshot_sha256": identity["snapshot_sha256"],
                "wheel_sha256": _sha(case.wheel),
                "asset_count": identity["asset_count"],
            }
        )
    )


def test_packaged_discovery_cli_reads_real_contract(real_delivery):
    case = real_delivery
    description = _query(case, "describe")
    assert description["source_revision"] == case.revision
    assert description["snapshot_sha256"] == case.identity["snapshot_sha256"]
    page = _query(case, "browse", *_pin_flags(case), "--limit", "1")
    assert page["outcome"] == "match"
    asset = page["result"]["items"][0]["asset_id"]
    document = _query(case, "get", asset, *_pin_flags(case))
    path = "catalog/contracts/" + asset + ".json"
    assert document["document"] == json.loads((case.package / path).read_bytes())
    assert document["digests"] == {path: _sha(case.package / path)}
    assert document["document"] == json.loads(
        (ROOT / "catalog/examples" / (asset + ".json")).read_bytes()
    )
    search = _query(case, "search", "--q", asset, *_pin_flags(case))
    assert asset in [item["asset_id"] for item in search["result"]["items"]]
    missing_pin = _run(
        [case.python, "-E", "-s", "-B", case.query, "browse"], cwd=case.package, code=2
    )
    assert "required" in missing_pin.stderr


@pytest.fixture
def saved_result(real_delivery):
    with TemporaryDirectory(prefix="result-", dir=real_delivery.work) as temporary:
        root = Path(temporary)
        (root / "measured.csv").write_text("x_s,value\n0,-8\n1,2\n2,4\n3,6\n", encoding="utf-8")
        (root / "reference.csv").write_text("x_s,value\n3,8\n1,2\n0,-10\n2,4\n", encoding="utf-8")
        tables = {
            name: {
                "path": name + ".csv",
                "units": {"x_s": "s", "value": "T"},
                "coordinates": ["x_s"],
                "expected_rows": 4,
            }
            for name in ("measured", "reference")
        }
        tables["measured"]["expected_groups"] = {
            "columns": ["x_s"],
            "values": [[0], [1], [2], [3]],
            "rows_each": 1,
        }
        spec = {
            "schema": "scirel.result-delivery",
            "tables": tables,
            "claims": [
                {"op": "range", "table": "measured", "column": "value"},
                {
                    "op": "compare",
                    "table": "measured",
                    "column": "value",
                    "reference": "reference",
                    "keys": ["x_s"],
                    "atol": 1,
                    "rtol": 0.125,
                },
            ],
        }
        yield SimpleNamespace(root=root, spec=spec, path=root / "spec.json", out=root / "checked")


def _save(result):
    result.path.write_text(json.dumps(result.spec), encoding="utf-8")


def _helper(case, result, command, *options, code=0):
    done = _run(
        [case.python, "-I", "-B", case.helper, command, result.path, "--out", result.out, *options],
        cwd=result.root,
        code=code,
    )
    return json.loads(done.stdout)


@pytest.mark.parametrize(
    "rtol,code,status", [(0.125, 0, "CONSISTENT"), (0.0625, 3, "CHECK_FAILED")]
)
def test_packaged_helper_build_verify_tolerance(real_delivery, saved_result, rtol, code, status):
    result = saved_result
    result.spec["claims"][1]["rtol"] = rtol
    _save(result)
    assert _helper(real_delivery, result, "build", code=code)["status"] == status
    replay = _helper(
        real_delivery, result, "verify", "--answer", result.out / "ANSWER.md", code=code
    )
    assert replay["status"] == status
    assert replay["answer_text"] == (result.out / "ANSWER.md").read_text(encoding="utf-8")
    checks = json.loads((result.out / "checks.json").read_bytes())
    assert checks["tables"]["measured"]["rows"] == 4
    assert checks["tables"]["measured"]["units"] == {"x_s": "s", "value": "T"}
    assert checks["tables"]["measured"]["coordinates"] == {"x_s": [0, 1, 2, 3]}
    claim = checks["claims"][0]
    assert (claim["min"], claim["max"], claim["unit"]) == (-8, 6, "T")
    comparison = checks["claims"][1]
    assert (comparison["atol"], comparison["rtol"], comparison["max_absolute_error"]) == (
        1,
        rtol,
        2,
    )
    assert comparison["passed"] is (code == 0)


@pytest.mark.parametrize(
    "failure,error",
    [
        ("rows", "coverage: row count mismatch"),
        ("groups", "coverage: group mismatch"),
        ("measurement-unit", "comparison unit mismatch"),
        ("coordinate-unit", "comparison unit mismatch"),
        ("keys", "coverage: comparison keys must match uniquely and completely"),
        ("nonfinite", "nonfinite measurement"),
    ],
)
def test_packaged_helper_invalid_input_returns_two(real_delivery, saved_result, failure, error):
    result = saved_result
    tables = result.spec["tables"]
    if failure == "rows":
        tables["measured"]["expected_rows"] = 3
    elif failure == "groups":
        tables["measured"]["expected_groups"]["rows_each"] = 2
    elif failure.endswith("unit"):
        column = "value" if failure == "measurement-unit" else "x_s"
        tables["reference"]["units"][column] = "mT" if column == "value" else "ms"
    elif failure == "keys":
        (result.root / "reference.csv").write_text(
            "x_s,value\n3,8\n1,2\n0,-10\n4,4\n", encoding="utf-8"
        )
    else:
        (result.root / "measured.csv").write_text(
            "x_s,value\n0,NaN\n1,2\n2,4\n3,6\n", encoding="utf-8"
        )
    _save(result)
    response = _helper(real_delivery, result, "build", code=2)
    assert response["status"] == "INVALID"
    assert error in response["error"]
    assert not result.out.exists()


@pytest.mark.parametrize(
    "target",
    [
        "measured.csv",
        "reference.csv",
        "spec.json",
        "checks.json",
        "ANSWER.md",
        "REPORT.md",
        "external-answer",
    ],
)
def test_packaged_helper_rejects_tampering(real_delivery, saved_result, target):
    result = saved_result
    _save(result)
    _helper(real_delivery, result, "build")
    options = []
    if target == "external-answer":
        path = result.root / "answer.md"
        path.write_bytes((result.out / "ANSWER.md").read_bytes() + b"Unverified claim.\n")
        options = ["--answer", path]
    else:
        path = (result.root if target.endswith((".csv", "spec.json")) else result.out) / target
        path.write_bytes(
            path.read_bytes()
            + (b"\n" if target.endswith((".csv", ".json")) else b"Unverified claim.\n")
        )
    before = {p.name: p.read_bytes() for p in result.out.iterdir()}
    assert _helper(real_delivery, result, "verify", *options, code=2)["status"] == "INVALID"
    assert {p.name: p.read_bytes() for p in result.out.iterdir()} == before


@pytest.mark.parametrize("member", ["wheel", "helper", "contract"])
def test_real_package_rejects_member_drift(real_delivery, member):
    case = real_delivery
    (contract,) = sorted((case.package / "catalog/contracts").glob("*.json"))[:1]
    path = {"wheel": case.wheel, "helper": case.helper, "contract": contract}[member]
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n")
        rejected = _verify_package(case, code=2)
        assert "member bytes changed" in rejected["error"]
        if member == "contract":
            response = _query(case, "get", contract.stem, *_pin_flags(case), code=2)
            assert response["outcome"] == "metadata_error"
    finally:
        path.write_bytes(original)
    assert _verify_package(case)["outcome"] == "ok"


@pytest.fixture(scope="module")
def real_sdk_python():
    configured = os.environ.get("SCIREL_MCP_PYTHON")
    if not configured:
        pytest.skip("NOT_RUN: set SCIREL_MCP_PYTHON to an isolated official MCP SDK interpreter")
    python = Path(configured).absolute()
    assert python.is_file(), "SCIREL_MCP_PYTHON does not exist: " + str(python)
    return python


@pytest.mark.parametrize("transport", ["stdio", "streamable-http"])
def test_official_sdk_consumes_the_same_real_package(
    real_sdk_python, real_delivery, transport, record_property
):
    case = real_delivery
    config = {
        "root": str(case.package),
        "server": str(case.server),
        "transport": transport,
        "identity": case.identity,
        "work": str(case.work),
    }
    probe = Path(__file__).with_name("_real_mcp_probe.py")
    done = _run([real_sdk_python, "-I", "-B", probe], cwd=case.work, input=json.dumps(config))
    evidence = json.loads(done.stdout)
    assert evidence["sdk_version"] == "2.3.0"
    assert evidence["server_exited"] is True
    assert evidence["asset_count"] == case.identity["asset_count"]
    assert evidence["snapshot_sha256"] == case.identity["snapshot_sha256"]
    assert evidence["wheel_sha256"] == _sha(case.wheel)
    assert evidence["protocol_version"] in evidence["supported_versions"]
    for key, value in evidence.items():
        record_property(key, value)
    assert _verify_package(case)["outcome"] == "ok"
