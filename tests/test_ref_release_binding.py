from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_scirel_from_ref as builder  # noqa: E402


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _make_bound_source(root: Path) -> tuple[str, str]:
    revision = "a" * 40
    version = "0.0.1"
    asset_id = "scirel.geometry.test-operator"

    layout = {
        "schema": "scirel.wheel-layout.v1",
        "source_layout": "src/scirel",
        "domain_packages": ["geometry"],
        "organized_general_primitives": {"geometry": ["analysis"]},
    }
    layout_path = root / "release/wheel/layout.json"
    _write_json(layout_path, layout)

    document = {
        "asset_id": asset_id,
        "kind": "operator",
        "version": {"implementation_version": version},
        "public_api": {
            "python": {"module": "scirel.geometry.analysis", "symbol": "test_operator"}
        },
    }
    document_path = root / "catalog/examples/test-operator.json"
    document_digest = _write_json(document_path, document)
    selection_path = root / "provenance/selections/current.json"
    selection_digest = _write_json(
        selection_path,
        {
            "schema": "scirel.selected-document-set.v1",
            "records": [
                {
                    "asset_id": asset_id,
                    "path": "catalog/examples/test-operator.json",
                    "sha256": document_digest,
                }
            ],
        },
    )

    handbook = {
        "schema": "scirel.handbook.v1",
        "chapters": [{"topics": [{"assets": [asset_id]}]}],
    }
    handbook_path = root / "tools/docs/handbook.json"
    handbook_digest = _write_json(handbook_path, handbook)

    integration_path = root / "provenance/validation/integration.json"
    integration_digest = _write_json(
        integration_path,
        {
            "schema": "scirel.integration.v1",
            "status": "PASS",
            "project_version": version,
            "source_revision": revision,
            "selection": {
                "path": "provenance/selections/current.json",
                "sha256": selection_digest,
            },
            "handbook": {
                "path": "tools/docs/handbook.json",
                "sha256": handbook_digest,
            },
        },
    )

    matrix = {
        "schema": "scirel.platform-support-matrix.v1",
        "package": "scirel",
        "package_version": version,
        "platforms": [{"id": "linux-x86_64-cp314", "status": "NOT_RUN"}],
    }
    _write_json(root / "release/platform-support-matrix.json", matrix)

    current = {
        "schema": "scirel.release-current.v2",
        "package": "scirel",
        "version": version,
        "source_revision": revision,
        "wheel": {
            "package_layout": "release/wheel/layout.json",
            "selected_capabilities": {
                "operators": 1,
                "task_graphs": 0,
                "document_closure": 1,
            },
        },
        "documentation": {
            "source_documents": "provenance/selections/current.json",
            "handbook": "tools/docs/handbook.json",
            "integration_record": "provenance/validation/integration.json",
            "handbook_scope": "exact",
            "selection_sha256": selection_digest,
            "handbook_sha256": handbook_digest,
            "capability_counts": {
                "operators": 1,
                "task_graphs": 0,
                "document_closure": 1,
            },
        },
    }
    _write_json(root / "release/CURRENT.json", current)
    (root / "src/scirel/geometry").mkdir(parents=True, exist_ok=True)
    (root / "src/scirel/geometry/__init__.py").write_text("\n", encoding="utf-8")
    (root / "src/scirel/geometry/analysis.py").write_text(
        "def test_operator():\n    return 1\n", encoding="utf-8"
    )
    return revision, version


def _make_wheel(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("scirel/geometry/__init__.py", "\n")
        archive.writestr("scirel/geometry/analysis.py", "def test_operator():\n    return 1\n")
        archive.writestr("scirel-0.0.1.dist-info/METADATA", "Metadata-Version: 2.3\n")


def test_release_binding_covers_selection_handbook_and_wheel_members(tmp_path: Path) -> None:
    revision, version = _make_bound_source(tmp_path)
    wheel = tmp_path / "scirel-0.0.1-py3-none-any.whl"
    _make_wheel(wheel)

    contents = builder._wheel_content_binding(wheel)
    binding = builder._release_binding(
        tmp_path,
        revision=revision,
        version=version,
        wheel_contents=contents,
    )

    assert binding is not None
    assert binding["capability_counts"] == {
        "operators": 1,
        "task_graphs": 0,
        "document_closure": 1,
    }
    assert binding["selection"]["capabilities"][0]["wheel_member"] == (
        "scirel/geometry/analysis.py"
    )
    assert binding["integration"]["selection_sha256"] == binding["selection"]["sha256"]
    assert binding["integration"]["handbook_sha256"] == binding["handbook"]["sha256"]


def test_release_binding_rejects_integration_selection_drift(tmp_path: Path) -> None:
    revision, version = _make_bound_source(tmp_path)
    integration_path = tmp_path / "provenance/validation/integration.json"
    integration = json.loads(integration_path.read_text(encoding="utf-8"))
    integration["selection"]["sha256"] = "0" * 64
    _write_json(integration_path, integration)
    wheel = tmp_path / "scirel-0.0.1-py3-none-any.whl"
    _make_wheel(wheel)

    with pytest.raises(ValueError, match="integration selection digest"):
        builder._release_binding(
            tmp_path,
            revision=revision,
            version=version,
            wheel_contents=builder._wheel_content_binding(wheel),
        )


def test_release_binding_skips_stale_current_for_pre_coordination_build(tmp_path: Path) -> None:
    revision, version = _make_bound_source(tmp_path)
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["source_revision"] = "b" * 40
    _write_json(current_path, current)
    wheel = tmp_path / "scirel-0.0.1-py3-none-any.whl"
    _make_wheel(wheel)

    assert builder._release_binding(
        tmp_path,
        revision=revision,
        version=version,
        wheel_contents=builder._wheel_content_binding(wheel),
    ) is None


def test_native_resource_closure_binding_checks_wheel_bytes(tmp_path: Path) -> None:
    resource = tmp_path / "src/scirel/kinetic/_fluidbw_native/a.m"
    resource.parent.mkdir(parents=True)
    resource.write_bytes(b"function y=a; y=a; end\n")
    digest = hashlib.sha256(resource.read_bytes()).hexdigest()
    closure = {
        "schema": "scirel.native-resource-closure.v1",
        "package": "scirel",
        "groups": [
            {
                "id": "fluidbw-octave",
                "files": ["_fluidbw_native/a.m"],
                "file_digests": {
                    "_fluidbw_native/a.m": {
                        "sha256": digest,
                        "bytes": resource.stat().st_size,
                    }
                },
            }
        ],
    }
    _write_json(tmp_path / "release/wheel/native-resource-closure.json", closure)
    wheel = tmp_path / "scirel-0.0.1-py3-none-any.whl"
    with ZipFile(wheel, "w", ZIP_DEFLATED) as archive:
        archive.writestr("scirel/kinetic/_fluidbw_native/a.m", resource.read_bytes())
    binding = builder._native_resource_closure_binding(
        tmp_path,
        wheel_contents=builder._wheel_content_binding(wheel),
    )
    assert binding is not None
    assert binding["resource_count"] == 1

    with ZipFile(wheel, "w", ZIP_DEFLATED) as archive:
        archive.writestr("scirel/kinetic/_fluidbw_native/a.m", b"changed")
    with pytest.raises(ValueError, match="bytes differ from source closure"):
        builder._native_resource_closure_binding(
            tmp_path,
            wheel_contents=builder._wheel_content_binding(wheel),
        )
