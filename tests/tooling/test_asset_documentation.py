import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "catalog" / "examples"
FAST_ION_ASSET_ID = "scirel.plasma.fast-ion-heating"
ASSET_IDS = {
    "scirel.kinetic.spectral-plasma-state", "scirel.kinetic.spectral-temporal-matrix",
    "scirel.kinetic.spectral-temporal-spectrum", "scirel.kinetic.spectral-dispersion-scan",
}
sys.path.insert(0, str(SCRIPTS))

from build_catalog import build_catalog  # noqa: E402
from validate_asset_documents import (  # noqa: E402
    AssetDocumentError,
    load_document_set,
    resolve_test_reference,
    validate_document,
    validate_runtime,
)


# The shared document fixture lives with the docs tests; expose it here so this
# tooling test can import it without depending on collection order.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs"))
from _document_fixtures import (EXAMPLE_CLOSURE_COUNT, copy_example_closure, example_document_sources)


CATALOG_TEST_VERSION = "0.0.0+catalogtest"


def test_pytest_reference_resolves_file_and_preserves_collection_responsibility(tmp_path):
    file = tmp_path / "test_example.py"
    file.write_text("def test_example():\n    assert True\n")
    assert resolve_test_reference("test_example.py::test_example[value]", tmp_path) == file
    assert resolve_test_reference("test_example.py", tmp_path) == file
    for invalid in ("missing.py::test_example", "test_example.py::", "test_example.py::::case",
                    "../test_example.py::case", str(file) + "::case", "::case"):
        with pytest.raises(ValueError):
            resolve_test_reference(invalid, tmp_path)


@pytest.fixture
def release_examples(tmp_path):
    """Synthetic release of all current contracts, solely for catalog mechanics.

    Canonical documents carry several real implementation versions. Keep their
    bytes untouched; explicitly project only the version in temporary copies.
    Real mixed-version rejection is tested separately below.
    """
    target = tmp_path / "synthetic-release-documents"
    target.mkdir()
    sources = example_document_sources()
    originals = {path: path.read_bytes() for path in sources.values()}
    assert len(originals) == EXAMPLE_CLOSURE_COUNT
    for source, body in originals.items():
        document = json.loads(body)
        document["version"]["implementation_version"] = CATALOG_TEST_VERSION
        (target / (document["asset_id"] + ".json")).write_text(json.dumps(document), encoding="utf-8")
    assert len(load_document_set(target)) == EXAMPLE_CLOSURE_COUNT
    yield target
    assert all(path.read_bytes() == body for path, body in originals.items())


def _composition_document():
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


def test_contract_schemas_and_dependency_closed_examples_parse(tmp_path):
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
    documents = load_document_set(copy_example_closure(tmp_path / "documents"))

    assert asset_schema["$schema"].endswith("2020-12/schema")
    assert release_schema["properties"]["schema"]["const"] == "scirel.catalog-release"
    assert len(documents) == EXAMPLE_CLOSURE_COUNT
    assert len([doc for doc in documents if doc["asset_id"] not in ASSET_IDS | {FAST_ION_ASSET_ID}]) == EXAMPLE_CLOSURE_COUNT - len(ASSET_IDS) - 1
    assert {doc["asset_id"] for doc in documents} >= ASSET_IDS
    assert [doc["asset_id"] for doc in documents if doc["asset_id"] == FAST_ION_ASSET_ID] == [FAST_ION_ASSET_ID]
    assert any("composition" in item for item in documents)
    assert any("composition" not in item for item in documents)


def test_missing_units_and_private_governance_fields_fail_closed():
    missing_units = _composition_document()
    del missing_units["inputs"][0]["units"]
    with pytest.raises(AssetDocumentError, match="missing fields: units"):
        validate_document(missing_units)

    leaked = _composition_document()
    leaked["identity"]["admission_ref"] = "private-owner-reference"
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


def _discovery_block():
    return {
        "capability": [
            "Rectangular coil vacuum field",
            "Sum exact magnetostatic filament fields at caller-supplied points.",
        ],
        "operation": [
            "superpose finite straight-filament Biot-Savart contributions",
            "geometry and currents -> magnetic field",
        ],
        "model": "exact magnetostatic straight-filament Biot-Savart superposition.",
        "geometry": "caller-supplied Cartesian points and rectangular filament loops.",
        "boundary": "field is singular on a filament and decays outside the coil.",
        "device_scope": "generic",
    }


def test_asset_schema_declares_the_optional_discovery_block():
    schema = json.loads(
        (ROOT / "contracts/scientific-asset-document.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert "discovery" in schema["properties"]
    assert "discovery" not in schema["required"]
    discovery = schema["$defs"]["discovery"]
    assert discovery["additionalProperties"] is False
    assert set(discovery["properties"]) == {
        "capability",
        "operation",
        "model",
        "geometry",
        "boundary",
        "device_scope",
    }
    assert "ports" not in discovery["properties"]
    assert "evidence" not in discovery["properties"]
    assert discovery["properties"]["device_scope"]["enum"] == [
        "generic",
        "device-parameterized",
        "device-bound",
        "unclassified",
    ]


def test_current_contracts_validate_with_or_without_discovery(tmp_path):
    documents = load_document_set(copy_example_closure(tmp_path / "documents"))

    assert len(documents) == EXAMPLE_CLOSURE_COUNT
    assert all(validate_document(document) is document for document in documents)


def test_a_complete_discovery_block_is_valid():
    document = _rectangular_coil_document()
    document["discovery"] = _discovery_block()

    assert validate_document(document) is document


def test_a_partial_discovery_block_can_record_only_device_scope():
    document = _rectangular_coil_document()
    document["discovery"] = {"device_scope": "device-bound"}

    assert validate_document(document) is document


@pytest.mark.parametrize(
    "scope",
    ["generic", "device-parameterized", "device-bound", "unclassified"],
)
def test_every_device_scope_value_is_valid(scope):
    document = _rectangular_coil_document()
    document["discovery"] = {"device_scope": scope}

    assert validate_document(document) is document


def test_discovery_rejects_an_unknown_device_scope():
    document = _rectangular_coil_document()
    document["discovery"] = _discovery_block()
    document["discovery"]["device_scope"] = "iter-bound"

    with pytest.raises(AssetDocumentError, match="discovery.device_scope: must be one of"):
        validate_document(document)


def test_discovery_rejects_wrong_field_types():
    document = _rectangular_coil_document()
    document["discovery"] = _discovery_block()
    document["discovery"]["capability"] = "rectangular coil vacuum field"
    with pytest.raises(AssetDocumentError, match="discovery.capability: must be a nonempty array"):
        validate_document(document)

    document = _rectangular_coil_document()
    document["discovery"] = _discovery_block()
    document["discovery"]["model"] = ["exact superposition"]
    with pytest.raises(AssetDocumentError, match="discovery.model: must be a nonempty string"):
        validate_document(document)

    document = _rectangular_coil_document()
    document["discovery"] = _discovery_block()


def test_discovery_rejects_unknown_keys_empty_blocks_and_duplicates():
    document = _rectangular_coil_document()
    document["discovery"] = {"ports": []}
    with pytest.raises(AssetDocumentError, match="discovery: unknown fields: ports"):
        validate_document(document)

    document = _rectangular_coil_document()
    document["discovery"] = {}
    with pytest.raises(AssetDocumentError, match="must declare at least one discovery field"):
        validate_document(document)

    document = _rectangular_coil_document()
    document["discovery"] = _discovery_block()
    document["discovery"]["capability"] = ["same", "same"]
    with pytest.raises(AssetDocumentError, match="discovery.capability: must not contain duplicates"):
        validate_document(document)


def test_runtime_input_defaults_must_match_the_document():
    document = _rectangular_coil_document()
    document["inputs"][-1]["default"] = 90.0

    with pytest.raises(AssetDocumentError, match="default differs for input: angle_deg"):
        validate_runtime(document)


def test_composition_ordinary_cycle_is_rejected_without_feedback_contract():
    document = _composition_document()
    document["composition"]["edges"].append(
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
    document = _composition_document()
    document["composition"]["edges"].extend(
        (
            _feedback_edge("loop-a"),
            _feedback_edge("loop-b", source_port="BR", target_port="z0"),
        )
    )
    document["composition"]["execution"]["feedback"] = [_feedback_contract("loop-a")]

    with pytest.raises(AssetDocumentError, match="missing contracts.*loop-b"):
        validate_document(document)


def test_multiple_feedback_edges_can_share_one_bounded_loop_contract():
    document = _composition_document()
    document["composition"]["edges"].extend(
        (
            _feedback_edge("picard-loop"),
            _feedback_edge("picard-loop", source_port="BR", target_port="z0"),
        )
    )
    document["composition"]["execution"]["feedback"] = [
        _feedback_contract("picard-loop")
    ]

    assert validate_document(document) is document


def test_feedback_contract_without_an_edge_is_rejected():
    document = _composition_document()
    document["composition"]["execution"]["feedback"] = [_feedback_contract("orphan-loop")]

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
    for node in graph["composition"]["nodes"]:
        if node.get("asset_id") == previous_id:
            node["asset_id"] = missing_id
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    with pytest.raises(AssetDocumentError, match="dependency is outside the document set"):
        load_document_set(tmp_path)


def test_runtime_signatures_tests_and_examples_are_executable(tmp_path):
    documents = copy_example_closure(tmp_path / "documents")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "validate_asset_documents.py"),
            str(documents),
            "--check-runtime",
            "--execute-examples",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["asset_count"] == EXAMPLE_CLOSURE_COUNT
    assert FAST_ION_ASSET_ID in report["asset_ids"]
    assert ASSET_IDS <= set(report["asset_ids"])
    assert len([asset_id for asset_id in report["asset_ids"] if asset_id not in ASSET_IDS | {FAST_ION_ASSET_ID}]) == EXAMPLE_CLOSURE_COUNT - len(ASSET_IDS) - 1
    assert report["runtime_checked"] is True
    assert report["runtime_origin"] == "source"
    assert report["examples_executed"] is True


def test_external_project_catalog_is_not_a_scirel_input():
    with pytest.raises(AssetDocumentError):
        load_document_set(ROOT / "catalog" / "algebra-grid")


def test_catalog_can_bind_a_git_revision_and_source_version(tmp_path, release_examples):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "pyproject.toml").write_text(
        f"[project]\nversion = \"{CATALOG_TEST_VERSION}\"\n",
        encoding="utf-8",
    )
    # The fixture can live under SciRel's ignored run root. Give it its own Git
    # identity rather than accidentally discovering the checkout's parent HEAD.
    subprocess.run(["git", "init", "-q"], cwd=source_root, check=True)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=source_root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=SciRel test", "-c",
         "user.email=scirel-test@example.invalid", "commit", "-qm", "initial source"],
        cwd=source_root, check=True,
    )
    source_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source_root, text=True,
    ).strip()
    output = tmp_path / "catalog"
    result = build_catalog(
        release_examples,
        output,
        catalog_id="scirel-bound-catalog",
        release_version=CATALOG_TEST_VERSION,
        coverage_status="partial",
        declared_total=EXAMPLE_CLOSURE_COUNT + 1,
        source_root=source_root,
        source_revision=source_revision,
    )
    release = json.loads((output / "release.json").read_text(encoding="utf-8"))
    assert release["source_revision"] == source_revision
    assert result["root_digest"] == release["root_digest"]


def test_catalog_source_root_rejects_a_version_not_owned_by_pyproject(
    tmp_path, release_examples
):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "pyproject.toml").write_text(
        "[project]\nversion = \"0.0.0\"\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="source_root pyproject.toml project.version"):
        build_catalog(
            release_examples,
            tmp_path / "catalog",
            catalog_id="scirel-bound-catalog",
            release_version=CATALOG_TEST_VERSION,
            coverage_status="partial",
            declared_total=EXAMPLE_CLOSURE_COUNT + 1,
            source_root=source_root,
            source_revision="a" * 40,
        )


def test_catalog_source_root_rejects_a_revision_not_at_git_head(
    tmp_path, release_examples
):
    import subprocess

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "pyproject.toml").write_text(
        f"[project]\nversion = \"{CATALOG_TEST_VERSION}\"\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=source_root, check=True)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=source_root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=SciRel test",
            "-c",
            "user.email=scirel-test@example.invalid",
            "commit",
            "-qm",
            "initial source",
        ],
        cwd=source_root,
        check=True,
    )
    with pytest.raises(ValueError, match="source_revision differs from source_root Git HEAD"):
        build_catalog(
            release_examples,
            tmp_path / "catalog",
            catalog_id="scirel-bound-catalog",
            release_version=CATALOG_TEST_VERSION,
            coverage_status="partial",
            declared_total=EXAMPLE_CLOSURE_COUNT + 1,
            source_root=source_root,
            source_revision="a" * 40,
        )
