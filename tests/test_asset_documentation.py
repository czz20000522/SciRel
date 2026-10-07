"""Schema and graph tooling checks over explicitly synthetic contracts."""

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_catalog import build_catalog
from validate_asset_documents import AssetDocumentError, load_document_set, validate_document


def fixture_document():
    return json.loads((ROOT / "tests/fixtures/contracts/fixture-identity.json").read_text())


def graph_document():
    document = fixture_document()
    document["kind"] = "task_graph"
    document["inputs"] = [document["inputs"][0]]
    def edge(source, source_port, target, target_port):
        return {"from": {"node": source, "port": source_port},
                "to": {"node": target, "port": target_port},
                "description": "Synthetic test edge.", "condition": "Always.",
                "transform": "Identity.", "kind": "data", "required": True}
    document["graph"] = {
        "nodes": [{"id": name, "kind": "controlled_glue", "description": "Synthetic fixture.",
                   "inputs": ["x"], "outputs": ["value"]} for name in ("first", "second")],
        "edges": [edge("$input", "x", "first", "x"), edge("first", "value", "second", "x"),
                  edge("second", "value", "$output", "value")],
        "execution": {"mode": "DAG", "ordering": "Topological.", "branches": [],
                      "state_ownership": "Caller.", "failure_propagation": "Raise.", "feedback": []},
    }
    return document


def test_synthetic_contracts_validate_but_are_outside_the_public_catalog():
    documents = load_document_set(ROOT / "tests/fixtures/contracts")
    assert len(documents) == 2
    assert not list((ROOT / "catalog/assets").glob("*.json"))
    assert all("fixture" in item["provenance"]["source_kinds"][0] for item in documents)


def test_missing_units_and_private_fields_are_rejected():
    document = fixture_document()
    del document["inputs"][0]["units"]
    with pytest.raises(AssetDocumentError, match="missing fields: units"):
        validate_document(document)
    document = fixture_document()
    document["provenance"]["admission_ref"] = "private"
    with pytest.raises(AssetDocumentError, match="private governance"):
        validate_document(document)


def test_optional_inputs_still_require_explicit_defaults():
    document = fixture_document()
    del document["inputs"][1]["default"]
    with pytest.raises(AssetDocumentError, match="optional ports"):
        validate_document(document)


def test_dag_contract_rejects_an_undeclared_cycle():
    document = graph_document()
    validate_document(document)
    cycle = copy.deepcopy(document["graph"]["edges"][1])
    cycle["from"]["node"] = "second"
    cycle["to"]["node"] = "first"
    document["graph"]["edges"].append(cycle)
    with pytest.raises(AssetDocumentError, match="acyclic"):
        validate_document(document)


def test_feedback_edge_requires_its_declared_bounded_contract():
    document = graph_document()
    feedback = copy.deepcopy(document["graph"]["edges"][1])
    feedback.update(kind="feedback", feedback_id="loop")
    feedback["from"]["node"] = "second"
    feedback["to"]["node"] = "first"
    document["graph"]["edges"].append(feedback)
    with pytest.raises(AssetDocumentError, match="feedback"):
        validate_document(document)
    document["graph"]["execution"]["feedback"] = [{
        "id": "loop", "state": "Fixture value.", "initialization": "Input.",
        "update_order": "After forward pass.", "continue_when": "Fixture predicate.",
        "stop_when": "Predicate false.", "iteration_bound": "At most two iterations.",
        "nonconvergence": "Raise fixture error.",
    }]
    validate_document(document)


def test_deterministic_catalog_uses_only_explicit_input_documents(tmp_path):
    arguments = dict(catalog_id="synthetic-fixture", release_version="0.1.0.dev5",
                     coverage_status="complete", declared_total=2)
    first = build_catalog(ROOT / "tests/fixtures/contracts", tmp_path / "first", **arguments)
    second = build_catalog(ROOT / "tests/fixtures/contracts", tmp_path / "second", **arguments)
    assert first["root_digest"] == second["root_digest"]


def test_empty_mainline_cannot_be_claimed_as_a_published_catalog(tmp_path):
    with pytest.raises(AssetDocumentError, match="no asset documents"):
        build_catalog(ROOT / "catalog/assets", tmp_path / "catalog", catalog_id="mainline",
                      release_version="0.2.0.dev0", coverage_status="complete", declared_total=0)
