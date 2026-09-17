import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "catalog" / "examples"
sys.path.insert(0, str(SCRIPTS))

from build_catalog import build_catalog  # noqa: E402
from validate_asset_documents import (  # noqa: E402
    AssetDocumentError,
    load_document_set,
    validate_document,
)


def _task_graph_document():
    return json.loads(
        (EXAMPLES / "scirel.field.multi-coil-vacuum-field.json").read_text(
            encoding="utf-8"
        )
    )


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def test_contract_schemas_and_dependency_closed_examples_parse():
    asset_schema = json.loads(
        (ROOT / "contracts/scientific-asset-document.schema.json").read_text(
            encoding="utf-8"
        )
    )
    release_schema = json.loads(
        (ROOT / "contracts/scientific-catalog-release.schema.json").read_text(
            encoding="utf-8"
        )
    )
    documents = load_document_set(EXAMPLES)

    assert asset_schema["$schema"].endswith("2020-12/schema")
    assert release_schema["properties"]["schema"]["const"] == "scirel.catalog-release.v1"
    assert len(documents) == 4
    assert {item["kind"] for item in documents} == {"operator", "task_graph"}


def test_missing_units_and_private_governance_fields_fail_closed():
    missing_units = _task_graph_document()
    del missing_units["inputs"][0]["units"]
    with pytest.raises(AssetDocumentError, match="missing fields: units"):
        validate_document(missing_units)

    leaked = _task_graph_document()
    leaked["provenance"]["admission_ref"] = "private-owner-reference"
    with pytest.raises(AssetDocumentError, match="private governance fields"):
        validate_document(leaked)


def test_task_graph_ordinary_cycle_is_rejected_without_feedback_contract():
    document = _task_graph_document()
    document["graph"]["edges"].append(
        {
            "from": {"node": "superposition", "port": "psi"},
            "to": {"node": "rectangular_geometry", "port": "r0"},
            "description": "Invalid hidden iteration.",
            "condition": "Always.",
            "transform": "Identity.",
            "kind": "data",
            "required": True,
        }
    )

    with pytest.raises(AssetDocumentError, match="must be acyclic"):
        validate_document(document)


def test_dependency_lock_must_match_target_document(tmp_path):
    for source in EXAMPLES.glob("*.json"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    graph_path = tmp_path / "scirel.field.multi-coil-vacuum-field.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["version"]["dependencies"][0]["implementation_digest"] = "sha256:" + "0" * 64
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    with pytest.raises(AssetDocumentError, match="dependency digest differs"):
        load_document_set(tmp_path)


def test_runtime_signatures_source_digests_tests_and_examples_are_executable():
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "validate_asset_documents.py"),
            str(EXAMPLES),
            "--check-runtime",
            "--execute-examples",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["asset_count"] == 4
    assert report["runtime_checked"] is True
    assert report["examples_executed"] is True


def test_catalog_build_is_deterministic_progressive_and_framework_neutral(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    arguments = {
        "catalog_id": "scirel-development-pilot",
        "release_version": "0.1.0.dev5",
        "coverage_status": "partial",
        "declared_total": 52,
    }
    first_result = build_catalog(EXAMPLES, first, **arguments)
    second_result = build_catalog(EXAMPLES, second, **arguments)

    assert first_result["root_digest"] == second_result["root_digest"]
    first_files = {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files

    release = json.loads(first_files["release.json"])
    assert release["coverage"] == {
        "status": "partial",
        "included_asset_count": 4,
        "declared_total_asset_count": 52,
    }
    digest = release.pop("root_digest")
    assert digest == "sha256:" + hashlib.sha256(_canonical(release)).hexdigest()
    assert release["progressive_disclosure"] == [
        "routes",
        "summaries",
        "exact_records",
    ]

    routes = [json.loads(line) for line in first_files["routes/all.jsonl"].splitlines()]
    summaries = [
        json.loads(line) for line in first_files["summaries/all.jsonl"].splitlines()
    ]
    reverse = [
        json.loads(line)
        for line in first_files["reverse-dependencies/all.jsonl"].splitlines()
    ]
    assert len(routes) == len(summaries) == len(reverse) == 4
    for route in routes:
        exact = first / route["exact_record"]["path"]
        assert route["exact_record"]["digest"] == "sha256:" + hashlib.sha256(
            exact.read_bytes()
        ).hexdigest()

    serialized = b"\n".join(first_files.values())
    for private_term in (
        b"admission_ref",
        b"tenant_id",
        b"CodeFusion",
        b"workbench",
        b"session_id",
    ):
        assert private_term not in serialized


def test_complete_catalog_cannot_hide_missing_documents(tmp_path):
    with pytest.raises(ValueError, match="requires every declared asset"):
        build_catalog(
            EXAMPLES,
            tmp_path / "catalog",
            catalog_id="invalid-complete",
            release_version="0.1.0.dev5",
            coverage_status="complete",
            declared_total=52,
        )
