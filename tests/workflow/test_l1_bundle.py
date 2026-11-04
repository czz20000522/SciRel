"""Tests for content-addressed directory/ZIP L1 transport."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import zipfile

import pytest

from scirel_plugin import FakeHost, SciRelBodyImportRequest, SciRelPlugin, execute_body_import
from scirel_workflow.l1_bundle import (
    L1_BUNDLE_SCHEMA,
    build_l1_bundle,
    canonical_l1_bundle_bytes,
    l1_bundle_to_payload,
)


def _write_project(root: Path, *, missing_operator_test: bool = False) -> Path:
    project = root / "Pleiades样例"
    project.mkdir()
    for name in (
        "asset_entry.py",
        "extraction_ledger.md",
        "extraction_report.md",
        "program_framework_map.md",
    ):
        (project / name).write_text(f"# {name}\n", encoding="utf-8")
    operator = project / "operators" / "极向磁场幅值"
    operator.mkdir(parents=True)
    (operator / "operator.md").write_text("# 极向磁场幅值\n", encoding="utf-8")
    (operator / "scientific_operator.py").write_text(
        "def scientific_operator(br, bz):\n    return br, bz\n", encoding="utf-8"
    )
    if not missing_operator_test:
        (operator / "test_scientific_operator.py").write_text(
            "def test_operator():\n    assert True\n", encoding="utf-8"
        )
    graph = project / "task_graphs" / "平衡图"
    graph.mkdir(parents=True)
    (graph / "task_graph.md").write_text("# 平衡图\n", encoding="utf-8")
    (graph / "task_graph.yaml").write_text(
        "nodes:\n  - {id: field, asset_ref: operators/极向磁场幅值}\n",
        encoding="utf-8",
    )
    (graph / "graph.py").write_text("def run_graph(inputs):\n    return inputs\n", encoding="utf-8")
    (graph / "test_task_graph.py").write_text(
        "def test_graph():\n    assert True\n", encoding="utf-8"
    )
    cache = graph / "__pycache__"
    cache.mkdir()
    (cache / "graph.pyc").write_bytes(b"generated")
    return project


def _zip_tree(root: Path, output: Path, *, wrapper: str = "") -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                archive.write(path, f"{wrapper}{relative}")


def test_directory_and_wrapped_zip_produce_the_same_content_identity(tmp_path):
    project = _write_project(tmp_path)
    archive = tmp_path / "Pleiades.zip"
    _zip_tree(project, archive, wrapper="Pleiades样例/")

    directory_bundle = build_l1_bundle(project, project_id="Pleiades")
    archive_bundle = build_l1_bundle(archive, project_id="Pleiades")

    assert directory_bundle == archive_bundle
    assert directory_bundle["schema"] == L1_BUNDLE_SCHEMA
    assert directory_bundle["file_count"] == 11
    assert all("__pycache__" not in item["path"] for item in directory_bundle["files"])


def test_body_import_maps_real_bundle_files_without_faking_scientific_checks(tmp_path):
    project = _write_project(tmp_path)
    body = canonical_l1_bundle_bytes(project, project_id="Pleiades")
    source_digest = "sha256:" + hashlib.sha256(body).hexdigest()

    response = execute_body_import(
        SciRelBodyImportRequest(
            operation="scirel.import_l1",
            artifact_ref="cf://artifact/l1/pleiades",
            artifact_digest=source_digest,
            media_type="application/json",
            body=body,
        )
    )
    candidate = json.loads(response.body)

    assert candidate["source_artifact_ref"] == "cf://artifact/l1/pleiades"
    assert candidate["source_digest"] == source_digest
    assert candidate["project_id"] == "Pleiades"
    assert len(candidate["assets"]) == 2
    assert {asset["asset_kind"] for asset in candidate["assets"]} == {
        "operator",
        "task_graph",
    }
    graph = next(
        asset for asset in candidate["assets"] if asset["asset_kind"] == "task_graph"
    )
    assert graph["dependency_refs"] == ["operators/极向磁场幅值"]
    assert {item["path"] for item in graph["package_files"]} == {
        "task_graphs/平衡图/graph.py",
        "task_graphs/平衡图/task_graph.md",
        "task_graphs/平衡图/task_graph.yaml",
        "task_graphs/平衡图/test_task_graph.py",
    }
    checks = {check["name"]: check for check in candidate["automated_checks"]}
    assert checks["l1_bundle_integrity"]["status"] == "passed"
    assert checks["dependency_closure"]["status"] == "passed"
    assert checks["direct_test_mapping"]["status"] == "passed"
    assert "scientific_correctness" not in checks


def test_artifact_import_appends_real_bundle_candidates_without_replacing_prior_one(tmp_path):
    project = _write_project(tmp_path)
    host = FakeHost(project_id="project-scirel")
    plugin = SciRelPlugin.for_development(host)
    candidates = []

    for project_id in ("PDRF", "PDRK"):
        source = host.put_artifact(
            L1_BUNDLE_SCHEMA, build_l1_bundle(project, project_id=project_id)
        )
        handoff = plugin.import_l1_artifact(source)
        candidates.append(
            (
                project_id,
                source,
                handoff,
                json.loads(host.read_artifact(handoff.artifact.ref)),
            )
        )

    assert len(host.jobs) == 2
    assert len({handoff.artifact.ref for _, _, handoff, _ in candidates}) == 2
    for project_id, source, handoff, candidate in candidates:
        assert candidate["source_artifact_ref"] == source.ref
        assert candidate["source_digest"] == source.digest
        assert candidate["project_id"] == project_id
        assert len(candidate["assets"]) == 2
        assert candidate["gaps"] == []
        assert json.loads(host.read_artifact(handoff.artifact.ref)) == candidate

    direct = plugin.import_l1(
        build_l1_bundle(project, project_id="direct"),
        source_artifact_ref="artifact://l1/direct",
    )
    direct_candidate = json.loads(host.read_artifact(direct.artifact.ref))
    direct_body = canonical_l1_bundle_bytes(project, project_id="direct")
    assert direct_candidate["source_digest"] == (
        "sha256:" + hashlib.sha256(direct_body).hexdigest()
    )
    assert len(direct_candidate["assets"]) == 2


def test_missing_real_test_file_is_reported_instead_of_marked_passed(tmp_path):
    project = _write_project(tmp_path, missing_operator_test=True)
    payload = l1_bundle_to_payload(build_l1_bundle(project, project_id="Pleiades"))
    checks = {check["name"]: check for check in payload["automated_checks"]}

    assert checks["direct_test_mapping"]["status"] == "failed"
    assert checks["direct_test_mapping"]["issues"] == [
        {
            "code": "missing_direct_test_mapping",
            "severity": "blocking",
            "asset_id": "Pleiades:operator:极向磁场幅值",
            "automation": "discover_or_generate_test",
        }
    ]


def test_import_accepts_scientific_packages_before_formal_markdown(tmp_path):
    project = _write_project(tmp_path)
    (project / "operators" / "极向磁场幅值" / "operator.md").unlink()
    (project / "task_graphs" / "平衡图" / "task_graph.md").unlink()
    body = canonical_l1_bundle_bytes(project, project_id="Pleiades")
    response = execute_body_import(
        SciRelBodyImportRequest(
            operation="scirel.import_l1",
            artifact_ref="cf://artifact/l1/without-formal-markdown",
            artifact_digest="sha256:" + hashlib.sha256(body).hexdigest(),
            media_type="application/json",
            body=body,
        )
    )
    candidate = json.loads(response.body)
    assets = {item["asset_kind"]: item for item in candidate["assets"]}
    assert candidate["gaps"] == []
    assert assets["operator"]["contract_path"] is None
    assert assets["operator"]["documentation_path"] is None
    assert assets["task_graph"]["documentation_path"] is None
    assert assets["task_graph"]["dependency_refs"] == ["operators/极向磁场幅值"]
    assert all(check["status"] == "passed" for check in candidate["automated_checks"])


def test_missing_graph_dependency_contract_still_blocks_import(tmp_path):
    project = _write_project(tmp_path)
    (project / "task_graphs" / "平衡图" / "task_graph.yaml").unlink()
    payload = l1_bundle_to_payload(build_l1_bundle(project, project_id="Pleiades"))
    graph = next(item for item in payload["assets"] if item["asset_kind"] == "task_graph")
    checks = {check["name"]: check for check in payload["automated_checks"]}
    assert graph["contract_path"] is None
    assert "missing_contract:task_graphs/平衡图/task_graph.yaml" in graph["gaps"]
    assert checks["asset_records"]["status"] == "failed"


def test_final_report_is_not_required_for_scientific_input_bundle(tmp_path):
    project = _write_project(tmp_path)
    (project / "extraction_report.md").unlink()
    payload = l1_bundle_to_payload(build_l1_bundle(project))
    assert payload["gaps"] == []


@pytest.mark.parametrize("filename,check", [
    ("scientific_operator.py", "asset_records"),
    ("test_scientific_operator.py", "direct_test_mapping"),
])
def test_empty_asset_material_does_not_pass_transport_checks(tmp_path, filename, check):
    project = _write_project(tmp_path)
    (project / "operators" / "极向磁场幅值" / filename).write_text("", encoding="utf-8")
    payload = l1_bundle_to_payload(build_l1_bundle(project))
    checks = {item["name"]: item for item in payload["automated_checks"]}
    assert checks[check]["status"] == "failed"


def test_bundle_rejects_content_tampering_and_unsafe_zip_paths(tmp_path):
    project = _write_project(tmp_path)
    bundle = build_l1_bundle(project, project_id="Pleiades")
    bundle["files"][0]["content_base64"] = "dGFtcGVyZWQ="
    with pytest.raises(ValueError, match="does not match content"):
        l1_bundle_to_payload(bundle)
    host = FakeHost(project_id="project-scirel")
    plugin = SciRelPlugin.for_development(host)
    source = host.put_artifact(L1_BUNDLE_SCHEMA, bundle)
    with pytest.raises(ValueError, match="does not match content"):
        plugin.import_l1_artifact(source)
    assert host.jobs == []

    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape/operator.md", "unsafe")
    with pytest.raises(ValueError, match="unsafe L1 bundle path"):
        build_l1_bundle(archive, project_id="unsafe")

    symlink_archive = tmp_path / "symlink.zip"
    link = zipfile.ZipInfo("operators/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(symlink_archive, "w") as output:
        output.writestr(link, "../outside")
    with pytest.raises(ValueError, match="may not contain symlinks"):
        build_l1_bundle(symlink_archive, project_id="unsafe")
