"""Tests for the saved L1 project inventory adapter."""

from pathlib import Path
import json
import subprocess
import sys

from scirel_plugin import execute_automated_check
from scirel_workflow import CandidatePackage, build_inventory, build_project_inventory


def test_inventory_accepts_code_anchors_without_formal_operator_document(tmp_path):
    project = write_project(tmp_path)
    (project / "operators/leaf/operator.md").unlink()
    inventory = build_inventory(tmp_path)
    assert inventory.gaps() == ()
    assert inventory.projects[0].assets[0].contract_path is None


def test_inventory_marks_empty_asset_tree_as_incomplete(tmp_path):
    project = tmp_path / "empty"
    project.mkdir()
    for name in ("operators", "task_graphs"):
        (project / name).mkdir()
    for name in ("extraction_ledger.md", "program_framework_map.md"):
        (project / name).write_text("record", encoding="utf-8")
    inventory = build_inventory(tmp_path)
    assert inventory.asset_count == 0
    assert "empty: no_scientific_assets" in inventory.gaps()
    assert any(check["status"] == "failed" for check in inventory.automated_checks())


def test_inventory_accepts_standalone_c_operator_family(tmp_path):
    project = tmp_path / "c_project"
    operator = project / "operators/leaf"
    operator.mkdir(parents=True)
    for name in ("extraction_ledger.md", "program_framework_map.md"):
        (project / name).write_text("record", encoding="utf-8")
    for name in ("scientific_operator.c", "scientific_operator.h", "test_scientific_operator.c"):
        (operator / name).write_text("/* source-backed asset */", encoding="utf-8")
    inventory = build_inventory(tmp_path)
    assert inventory.gaps() == ()
    asset = inventory.projects[0].assets[0]
    assert asset.implementation_path == "operators/leaf/scientific_operator.c"
    assert asset.direct_test_path == "operators/leaf/test_scientific_operator.c"


def test_inventory_rejects_empty_implementation_and_test(tmp_path):
    project = write_project(tmp_path)
    (project / "operators/leaf/scientific_operator.py").write_text("", encoding="utf-8")
    (project / "operators/leaf/test_scientific_operator.py").write_text("", encoding="utf-8")
    inventory = build_inventory(tmp_path)
    checks = {check["name"]: check for check in inventory.automated_checks()}
    assert checks["asset_records"]["status"] == "failed"
    assert checks["direct_test_mapping"]["status"] == "failed"


def write_asset(root: Path, kind: str, name: str, *, missing: set[str] | None = None) -> None:
    missing = missing or set()
    directory = root / ("operators" if kind == "operator" else "task_graphs") / name
    directory.mkdir(parents=True)
    files = {
        "contract": "operator.md" if kind == "operator" else "task_graph.yaml",
        "implementation": "scientific_operator.py" if kind == "operator" else "graph.py",
        "test": "test_scientific_operator.py" if kind == "operator" else "test_task_graph.py",
    }
    for label, filename in files.items():
        if label not in missing:
            content = "asset_ref: operators/leaf\n" if filename == "task_graph.yaml" else f"# {name}\n"
            (directory / filename).write_text(content, encoding="utf-8")


def write_project(root: Path, name: str = "sample", *, missing: set[str] | None = None) -> Path:
    project = root / name
    project.mkdir()
    (project / "extraction_ledger.md").write_text("# ledger\n", encoding="utf-8")
    (project / "program_framework_map.md").write_text("# framework\n", encoding="utf-8")
    (project / "operators").mkdir()
    (project / "task_graphs").mkdir()
    write_asset(project, "operator", "leaf", missing=missing)
    write_asset(project, "task_graph", "pipeline", missing=missing)
    return project


def test_inventory_is_deterministic_and_projects_to_l1_payload(tmp_path):
    write_project(tmp_path)
    inventory = build_inventory(tmp_path)

    assert inventory.operator_count == 1
    assert inventory.task_graph_count == 1
    assert inventory.asset_count == 2
    assert inventory.gaps() == ()
    assert inventory.automated_checks()[1]["status"] == "passed"
    payload = inventory.to_l1_payload()
    assert payload["schema"] == "scirel.l1-inventory.dev"
    assert payload["counts"] == {"projects": 1, "operators": 1, "task_graphs": 1, "assets": 2}
    assert len(payload["assets"]) == 2
    assert inventory.inventory_digest.startswith("sha256:")
    project_payload = inventory.to_project_l1_payloads()[0]
    assert project_payload["project_id"] == "sample"
    assert [project["project_id"] for project in project_payload["projects"]] == [
        "sample"
    ]
    assert project_payload["gaps"] == []


def test_inventory_keeps_missing_files_as_gaps(tmp_path):
    project = write_project(tmp_path, missing={"test"})
    inventory = build_project_inventory(project)

    assert any(
        gap.startswith("missing_test:")
        for asset in inventory.assets
        for gap in asset.gaps
    )
    checks = build_inventory(tmp_path).automated_checks()
    asset_records = next(
        check for check in checks if check["name"] == "asset_records"
    )
    assert asset_records["status"] == "passed"
    assert asset_records["issues"] == []
    assert any(
        check["name"] == "direct_test_mapping" and check["status"] == "failed"
        for check in checks
    )
    assert any(
        issue["code"] == "missing_direct_test_mapping"
        for check in checks
        for issue in check.get("issues", ())
    )
    assert build_inventory(tmp_path).to_l1_payload()["gaps"]


def test_missing_direct_test_inventory_routes_to_automated_retry(tmp_path):
    write_project(tmp_path, missing={"test"})
    payload = build_inventory(tmp_path).to_project_l1_payloads()[0]
    candidate = CandidatePackage.from_l1(
        payload,
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-missing-tests",
    )

    result = json.loads(
        execute_automated_check(
            json.dumps(candidate.to_dict()).encode("utf-8"),
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            result_id="check-missing-tests",
        )
    )

    assert result["next_action"] == "retry"
    assert result["status"] == "failed"
    assert all(
        issue.get("automation") != "request_rework"
        for check in result["checks"]
        for issue in check.get("issues", ())
    )


def test_unresolved_task_graph_dependency_routes_to_automated_retry(tmp_path):
    project = write_project(tmp_path)
    (project / "task_graphs" / "pipeline" / "task_graph.yaml").write_text(
        "asset_ref: operators/missing\n", encoding="utf-8"
    )
    payload = build_inventory(tmp_path).to_project_l1_payloads()[0]
    candidate = CandidatePackage.from_l1(
        payload,
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-unresolved-dependency",
    )

    result = json.loads(
        execute_automated_check(
            json.dumps(candidate.to_dict()).encode("utf-8"),
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            result_id="check-unresolved-dependency",
        )
    )

    assert result["next_action"] == "retry"
    assert any(
        issue.get("code") == "unresolved_task_graph_dependency"
        for check in result["checks"]
        for issue in check.get("issues", ())
    )


def test_inventory_promotes_missing_asset_contract_to_blocking_check(tmp_path):
    write_project(tmp_path, missing={"contract"})
    inventory = build_inventory(tmp_path)

    asset_check = next(
        check for check in inventory.automated_checks() if check["name"] == "asset_records"
    )
    assert asset_check["status"] == "failed"
    assert any(
        issue["code"] == "missing_l1_asset_file"
        for issue in asset_check["issues"]
    )
    assert any("missing_contract:" in gap for gap in inventory.gaps())
    payload = inventory.to_project_l1_payloads()[0]
    assert any("asset_records:" in gap for gap in payload["gaps"])

    candidate = CandidatePackage.from_l1(
        payload,
        source_artifact_ref="artifact://l1/missing-contract",
        source_digest="sha256:" + "a" * 64,
        run_id="run-missing-contract",
    )
    result = json.loads(
        execute_automated_check(
            json.dumps(
                candidate.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            result_id="check-missing-contract",
        )
    )

    assert result["next_action"] == "rework_requested"
    assert any(
        issue.get("code") == "missing_l1_asset_file"
        and issue.get("automation") == "request_rework"
        for check in result["checks"]
        for issue in check.get("issues", ())
    )


def test_missing_project_record_routes_to_rework(tmp_path):
    project = write_project(tmp_path)
    (project / "extraction_ledger.md").unlink()
    inventory = build_inventory(tmp_path)
    project_check = next(
        check
        for check in inventory.automated_checks()
        if check["name"] == "required_project_records"
    )

    assert project_check["status"] == "failed"
    assert project_check["issues"] == [{
        "code": "missing_l1_project_record",
        "severity": "blocking",
        "project_id": "sample",
        "detail": "missing_extraction_ledger",
        "automation": "request_rework",
    }]

    candidate = CandidatePackage.from_l1(
        inventory.to_project_l1_payloads()[0],
        source_artifact_ref="artifact://l1/missing-project-record",
        source_digest="sha256:" + "c" * 64,
        run_id="run-missing-project-record",
    )
    result = json.loads(
        execute_automated_check(
            json.dumps(candidate.to_dict()).encode("utf-8"),
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            result_id="check-missing-project-record",
        )
    )

    assert result["next_action"] == "rework_requested"


def test_inventory_rejects_task_graph_cycles(tmp_path):
    project = write_project(tmp_path)
    first = project / "task_graphs" / "pipeline" / "task_graph.yaml"
    second = project / "task_graphs" / "nested"
    second.mkdir()
    (second / "task_graph.yaml").write_text(
        "asset_ref: task_graphs/pipeline\n", encoding="utf-8"
    )
    (second / "graph.py").write_text("# nested\n", encoding="utf-8")
    (second / "test_task_graph.py").write_text("# test\n", encoding="utf-8")
    first.write_text("asset_ref: task_graphs/nested\n", encoding="utf-8")

    inventory = build_inventory(tmp_path)
    dependency = next(
        check
        for check in inventory.automated_checks()
        if check["name"] == "dependency_closure"
    )

    assert dependency["status"] == "failed"
    assert dependency["cycles"] == [
        "task_graphs/nested -> task_graphs/pipeline -> task_graphs/nested"
    ]
    assert any("dependency_closure: task_graphs/" in gap for gap in inventory.gaps())


def test_inventory_extracts_asset_refs_from_yaml_flow_mappings(tmp_path):
    project = write_project(tmp_path)
    contract = project / "task_graphs" / "pipeline" / "task_graph.yaml"
    contract.write_text(
        "nodes:\n"
        "  - {id: leaf, asset_ref: operators/leaf, inputs: []}\n"
        "  - {id: nested, asset_ref: 'task_graphs/missing', inputs: []}\n",
        encoding="utf-8",
    )

    inventory = build_inventory(tmp_path)
    graph = next(
        asset
        for asset in inventory.projects[0].assets
        if asset.kind == "task_graph" and asset.name == "pipeline"
    )
    dependency = next(
        check
        for check in inventory.automated_checks()
        if check["name"] == "dependency_closure"
    )

    assert graph.dependency_refs == ("operators/leaf", "task_graphs/missing")
    assert dependency["status"] == "failed"
    assert dependency["missing"] == [
        "sample:task_graph:pipeline -> task_graphs/missing"
    ]


def test_inventory_ignores_yaml_null_asset_ref_and_rejects_other_prefixes(tmp_path):
    project = write_project(tmp_path)
    contract = project / "task_graphs" / "pipeline" / "task_graph.yaml"
    contract.write_text(
        "nodes:\n"
        "  - {id: glue, asset_ref: null, inputs: []}\n"
        "  - {id: external, asset_ref: external/leaf, inputs: []}\n",
        encoding="utf-8",
    )

    inventory = build_inventory(tmp_path)
    graph = next(
        asset
        for asset in inventory.projects[0].assets
        if asset.kind == "task_graph" and asset.name == "pipeline"
    )
    dependency = next(
        check
        for check in inventory.automated_checks()
        if check["name"] == "dependency_closure"
    )

    assert graph.dependency_refs == ("external/leaf",)
    assert dependency["status"] == "failed"
    assert dependency["invalid"] == [
        "sample:task_graph:pipeline -> external/leaf"
    ]
    assert dependency["issues"][0]["code"] == "invalid_task_graph_dependency_ref"

    candidate = CandidatePackage.from_l1(
        inventory.to_project_l1_payloads()[0],
        source_artifact_ref="artifact://l1/invalid-dependency",
        source_digest="sha256:" + "b" * 64,
        run_id="run-invalid-dependency",
    )
    candidate_body = json.dumps(
        candidate.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    result = json.loads(
        execute_automated_check(
            candidate_body,
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            result_id="check-invalid-dependency",
        )
    )

    assert result["next_action"] == "rework_requested"


def test_unknown_project_selection_fails(tmp_path):
    write_project(tmp_path)
    try:
        build_inventory(tmp_path, project_ids=["missing"])
    except ValueError as error:
        assert "unknown L1 projects" in str(error)
    else:
        raise AssertionError("unknown project should fail closed")


def test_project_payloads_isolate_gaps_between_projects(tmp_path):
    write_project(tmp_path, "clean")
    write_project(tmp_path, "needs-work", missing={"test"})
    payloads = {payload["project_id"]: payload for payload in build_inventory(tmp_path).to_project_l1_payloads()}

    assert payloads["clean"]["gaps"] == []
    assert payloads["needs-work"]["gaps"]


def test_inventory_cli_project_mode_writes_candidate_scoped_payload(tmp_path):
    write_project(tmp_path, "sample")
    output = tmp_path / "sample-l1.json"
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_l1_inventory.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            str(tmp_path),
            "--project",
            "sample",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert summary["candidate_scope"] == "sample"
    assert summary["candidate_scoped_input"] is True
    assert "candidate_ready_input" not in summary
    assert payload["project_id"] == "sample"
    assert [project["project_id"] for project in payload["projects"]] == ["sample"]
    assert payload["counts"]["projects"] == 1
