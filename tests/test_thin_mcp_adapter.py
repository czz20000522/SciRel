import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "catalog" / "examples"
sys.path.insert(0, str(SCRIPTS))

from build_catalog import build_catalog  # noqa: E402
from scirel_adapter import ThinMcpAdapter, ThinMcpAdapterError  # noqa: E402


@pytest.fixture
def catalog(tmp_path):
    output = tmp_path / "catalog"
    result = build_catalog(
        EXAMPLES,
        output,
        catalog_id="scirel-development-pilot",
        release_version="0.1.0.dev5",
        coverage_status="partial",
        declared_total=52,
    )
    return output, result["root_digest"]


@pytest.fixture(autouse=True)
def installed_scirel_version():
    with mock.patch("scirel_adapter.mcp.metadata.version", return_value="0.1.0.dev5"):
        yield


def _adapter(catalog):
    root, digest = catalog
    return ThinMcpAdapter(
        root,
        expected_root_digest=digest,
    )


def test_documents_drive_progressive_discovery_and_retrieval(catalog):
    adapter = _adapter(catalog)
    source_document = json.loads(
        (EXAMPLES / "scirel.field.current-green-superposition.json").read_text(
            encoding="utf-8"
        )
    )

    discovery = adapter.handle(
        {
            "operation": "catalog.discover",
            "filters": {
                "kind": "operator",
                "relation": source_document["identity"]["relation"],
                "output": "psi",
            },
            "cursor": 0,
            "limit": 1,
        }
    )
    assert [item["asset_id"] for item in discovery["items"]] == [
        source_document["asset_id"]
    ]
    assert discovery["exhausted"] is True

    summaries = adapter.handle(
        {
            "operation": "asset.read",
            "asset_ids": [source_document["asset_id"]],
            "detail": "summary",
        }
    )
    assert summaries["items"][0]["evidence_ceiling"] == source_document["verification"][
        "evidence_ceiling"
    ]

    documents = adapter.handle(
        {
            "operation": "asset.read",
            "asset_ids": [source_document["asset_id"]],
            "detail": "document",
        }
    )
    assert documents["items"] == [source_document]
    assert documents["catalog"]["root_digest"] == catalog[1]


def test_discovery_and_document_reads_do_not_import_scientific_modules(catalog):
    with mock.patch(
        "scirel_adapter.mcp.importlib.import_module",
        side_effect=AssertionError("discovery imported a scientific module"),
    ):
        adapter = _adapter(catalog)
        result = adapter.discover(limit=2)
        adapter.read_assets(
            [item["asset_id"] for item in result["items"]], detail="document"
        )


def test_importing_adapter_does_not_import_scirel_runtime():
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import scirel_adapter; "
                "assert not any(name == 'scirel' or name.startswith('scirel.') "
                "for name in sys.modules)"
            ),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_callable_binding_and_invocation_are_document_driven(catalog):
    adapter = _adapter(catalog)
    asset_id = "scirel.field.current-green-superposition"

    binding = adapter.handle({"operation": "callable.resolve", "asset_id": asset_id})
    assert binding["binding"] == {
        "module": "scirel.field.current_green_superposition",
        "symbol": "superpose_current_green_field",
        "signature": "superpose_current_green_field(currents, gpsi, gBR, gBZ)",
    }

    response = adapter.handle(
        {
            "operation": "callable.invoke",
            "asset_id": asset_id,
            "arguments": {
                "currents": [2.0, -1.0],
                "gpsi": [[1.0, 3.0], [4.0, 5.0]],
                "gBR": [[2.0, 1.0], [0.0, 6.0]],
                "gBZ": [[-1.0, 2.0], [3.0, 4.0]],
            },
        }
    )
    assert response["result"] == {
        "psi": [-2.0, 1.0],
        "BR": [4.0, -4.0],
        "BZ": [-5.0, 0.0],
    }
    assert response["asset_id"] == asset_id
    assert response["implementation_version"] == "0.1.0.dev5"
    assert response["evidence_ceiling"]
    serialized = json.dumps(response, sort_keys=True)
    for forbidden in ("session_id", "project_id", "workbench_id", "admission_ref"):
        assert forbidden not in serialized


def test_unknown_platform_fields_and_undocumented_arguments_fail_closed(catalog):
    adapter = _adapter(catalog)
    asset_id = "scirel.field.current-green-superposition"

    with pytest.raises(ThinMcpAdapterError, match="unknown request fields") as request_error:
        adapter.handle(
            {
                "operation": "asset.read",
                "asset_ids": [asset_id],
                "session_id": "transport-owned",
            }
        )
    assert request_error.value.code == "invalid_request"

    with mock.patch(
        "scirel_adapter.mcp.importlib.import_module",
        side_effect=AssertionError("invalid arguments imported a scientific module"),
    ):
        with pytest.raises(ThinMcpAdapterError, match="undocumented input") as argument_error:
            adapter.invoke(
                asset_id,
                {
                    "currents": [1.0],
                    "gpsi": [[1.0]],
                    "gBR": [[1.0]],
                    "gBZ": [[1.0]],
                    "project_id": "not-a-scientific-input",
                },
            )
    assert argument_error.value.code == "invalid_arguments"

    with pytest.raises(ThinMcpAdapterError, match="missing required input") as missing_error:
        adapter.invoke(
            asset_id,
            {
                "currents": [1.0],
                "gpsi": [[1.0]],
                "gBR": [[1.0]],
            },
        )
    assert missing_error.value.code == "invalid_arguments"

    with pytest.raises(ThinMcpAdapterError, match="filter kind must be a string") as filter_error:
        adapter.discover(filters={"kind": ["operator"]})
    assert filter_error.value.code == "invalid_request"


def test_scientific_failure_is_preserved_as_the_adapter_error_cause(catalog):
    adapter = _adapter(catalog)
    with pytest.raises(ThinMcpAdapterError) as failure:
        adapter.invoke(
            "scirel.field.current-green-superposition",
            {
                "currents": [1.0, 2.0],
                "gpsi": [[1.0]],
                "gBR": [[1.0]],
                "gBZ": [[1.0]],
            },
        )

    assert failure.value.code == "invocation_failed"
    assert isinstance(failure.value.__cause__, ValueError)


def test_catalog_release_and_partitions_are_verified_before_serving(catalog):
    root, digest = catalog
    route_path = root / "routes" / "all.jsonl"
    route_path.write_bytes(route_path.read_bytes() + b"\n")

    with pytest.raises(ThinMcpAdapterError, match="catalog partition differs") as failure:
        ThinMcpAdapter(
            root,
            expected_root_digest=digest,
        )
    assert failure.value.code == "snapshot_mismatch"


def test_catalog_partition_paths_cannot_escape_the_snapshot_root(catalog):
    root, _ = catalog
    release_path = root / "release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["partitions"][0]["path"] = "../outside.json"
    unsigned = dict(release)
    unsigned.pop("root_digest")
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    release["root_digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    release_path.write_text(json.dumps(release), encoding="utf-8")

    with pytest.raises(ThinMcpAdapterError, match="escapes catalog root") as failure:
        ThinMcpAdapter(root, expected_root_digest=release["root_digest"])
    assert failure.value.code == "invalid_snapshot"


def test_document_partition_is_reverified_when_read_after_open(catalog):
    root, _ = catalog
    adapter = _adapter(catalog)
    route = adapter.discover(limit=1)["items"][0]
    record_path = root / route["exact_record"]["path"]
    record_path.write_bytes(record_path.read_bytes() + b"\n")

    with pytest.raises(ThinMcpAdapterError, match="catalog partition differs") as failure:
        adapter.read_assets([route["asset_id"]], detail="document")
    assert failure.value.code == "snapshot_mismatch"


def test_pagination_reports_remaining_catalog_scope(catalog):
    adapter = _adapter(catalog)

    first = adapter.discover(cursor=0, limit=1)
    second = adapter.discover(cursor=first["next_cursor"], limit=1)

    assert first["exhausted"] is False
    assert first["next_cursor"] == 1
    assert second["items"][0]["asset_id"] != first["items"][0]["asset_id"]


def test_installed_version_must_match_the_canonical_document(catalog):
    root, digest = catalog
    adapter = ThinMcpAdapter(root, expected_root_digest=digest)

    with mock.patch("scirel_adapter.mcp.metadata.version", return_value="0.1.0.dev4"):
        with pytest.raises(ThinMcpAdapterError, match="SciRel version differs") as failure:
            adapter.resolve_callable("scirel.field.current-green-superposition")
    assert failure.value.code == "callable_mismatch"
