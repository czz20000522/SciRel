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
    validate_runtime,
)


def _task_graph_document():
    return json.loads(
        (EXAMPLES / "scirel.field.multi-coil-vacuum-field.json").read_text(
            encoding="utf-8"
        )
    )


def _rectangular_coil_document():
    return json.loads(
        (EXAMPLES / "scirel.field.rectangular-coil-filaments.json").read_text(
            encoding="utf-8"
        )
    )


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _feedback_edge(feedback_id, *, source_port="psi", target_port="r0"):
    return {
        "from": {"node": "superposition", "port": source_port},
        "to": {"node": "rectangular_geometry", "port": target_port},
        "description": "Feed the computed flux into the next controlled iteration.",
        "condition": "The loop continuation predicate is true.",
        "transform": "Identity for contract validation.",
        "kind": "feedback",
        "required": True,
        "feedback_id": feedback_id,
    }


def _feedback_contract(feedback_id):
    return {
        "id": feedback_id,
        "state": "The prior iteration flux.",
        "initialization": "Use the caller-provided initial state.",
        "update_order": "Update after the forward pass.",
        "continue_when": "The residual exceeds tolerance.",
        "stop_when": "The residual meets tolerance.",
        "iteration_bound": "At most maxiter updates.",
        "nonconvergence": "Raise the declared nonconvergence failure.",
    }


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
    assert len(documents) == 78
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


def test_optional_inputs_require_structured_defaults():
    missing_default = _rectangular_coil_document()
    del missing_default["inputs"][-1]["default"]
    with pytest.raises(AssetDocumentError, match="optional ports must declare a default"):
        validate_document(missing_default)

    default_on_required = _rectangular_coil_document()
    default_on_required["inputs"][0]["default"] = 1.0
    with pytest.raises(AssetDocumentError, match="required ports must not declare a default"):
        validate_document(default_on_required)


def test_runtime_input_defaults_must_match_the_document():
    document = _rectangular_coil_document()
    document["inputs"][-1]["default"] = 90.0

    with pytest.raises(AssetDocumentError, match="default differs for input: angle_deg"):
        validate_runtime(document)


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


def test_distinct_feedback_loops_require_matching_contracts():
    document = _task_graph_document()
    document["graph"]["edges"].extend(
        (
            _feedback_edge("loop-a"),
            _feedback_edge("loop-b", source_port="BR", target_port="z0"),
        )
    )
    document["graph"]["execution"]["feedback"] = [_feedback_contract("loop-a")]

    with pytest.raises(AssetDocumentError, match="missing contracts.*loop-b"):
        validate_document(document)


def test_multiple_feedback_edges_can_share_one_bounded_loop_contract():
    document = _task_graph_document()
    document["graph"]["edges"].extend(
        (
            _feedback_edge("picard-loop"),
            _feedback_edge("picard-loop", source_port="BR", target_port="z0"),
        )
    )
    document["graph"]["execution"]["feedback"] = [
        _feedback_contract("picard-loop")
    ]

    assert validate_document(document) is document


def test_feedback_contract_without_an_edge_is_rejected():
    document = _task_graph_document()
    document["graph"]["execution"]["feedback"] = [_feedback_contract("orphan-loop")]

    with pytest.raises(AssetDocumentError, match="contracts without feedback edges.*orphan-loop"):
        validate_document(document)


def test_dependency_must_resolve_to_a_canonical_document(tmp_path):
    for source in EXAMPLES.glob("*.json"):
        (tmp_path / source.name).write_bytes(source.read_bytes())
    graph_path = tmp_path / "scirel.field.multi-coil-vacuum-field.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    previous_id = graph["version"]["dependencies"][0]["asset_id"]
    missing_id = "scirel.field.missing"
    graph["version"]["dependencies"][0]["asset_id"] = missing_id
    for node in graph["graph"]["nodes"]:
        if node.get("asset_id") == previous_id:
            node["asset_id"] = missing_id
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    with pytest.raises(AssetDocumentError, match="dependency is outside the document set"):
        load_document_set(tmp_path)


def test_runtime_signatures_tests_and_examples_are_executable():
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
    assert report["asset_count"] == 78
    assert report["runtime_checked"] is True
    assert report["runtime_origin"] == "source"
    assert report["examples_executed"] is True


def test_installed_runtime_mode_rejects_the_source_checkout():
    document = _rectangular_coil_document()

    with pytest.raises(AssetDocumentError, match="resolved to the source checkout"):
        validate_runtime(document, installed_runtime=True)


def test_catalog_build_is_deterministic_progressive_and_framework_neutral(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    arguments = {
        "catalog_id": "scirel-development-pilot",
        "release_version": "0.1.0.dev5",
        "coverage_status": "partial",
        "declared_total": 114,
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
        "included_asset_count": 78,
        "declared_total_asset_count": 114,
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
    assert len(routes) == len(summaries) == len(reverse) == 78
    partition_paths = {item["path"] for item in release["partitions"]}
    for route in routes:
        assert set(route["exact_record"]) == {"path"}
        assert route["exact_record"]["path"] in partition_paths
    for summary in summaries:
        assert set(summary["exact_record"]) == {"path"}
        assert summary["exact_record"]["path"] in partition_paths
    rectangular_summary = next(
        item
        for item in summaries
        if item["asset_id"] == "scirel.field.rectangular-coil-filaments"
    )
    assert rectangular_summary["identity"] == {
        "model": "geometric discretization without a magnetic-field model",
        "geometry": "axisymmetric rectangular coil cross-section represented by circular filaments",
        "coordinates": "cylindrical R-Z coordinates",
        "boundary": "all generated cylindrical radii must remain nonnegative",
    }
    assert rectangular_summary["inputs"][-1] == {
        "name": "angle_deg",
        "units": "degree",
        "shape": "scalar",
        "dtype": "real",
        "required": False,
        "default": 0.0,
    }
    assert rectangular_summary["outputs"][0]["name"] == "rz_pts"
    assert rectangular_summary["known_limitations"]

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
            declared_total=114,
        )


def test_catalog_release_version_must_match_every_document(tmp_path):
    with pytest.raises(ValueError, match="implementation_version must match"):
        build_catalog(
            EXAMPLES,
            tmp_path / "catalog",
            catalog_id="version-mismatch",
            release_version="0.1.0.dev4",
            coverage_status="partial",
            declared_total=114,
        )
