from pathlib import Path

import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import select_affected_tests as selector  # noqa: E402


def test_development_skill_changes_use_one_lightweight_contract_test():
    changed = [
        "skills/development/README.md",
        "skills/development/references/development-lifecycle.md",
        "skills/development/references/scirel-development-core.md",
        "skills/development/integration/scirel-integration/SKILL.md",
    ]

    result = selector.select(changed)

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_development_skill_contract.py"]


def test_project_contract_keeps_ordinary_optimization_out_of_release_flow():
    project_contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "当前默认开发模式" in project_contract
    assert "普通任务默认处于 `development`" in project_contract
    assert "不会启动发布流程" in project_contract
    assert "数量只属于具体 manifest/revision" in project_contract
    assert "多个相互关联的小修复可以合并为一个变更批次" in project_contract


def test_lifecycle_keeps_incubation_counts_dynamic_and_release_gates_explicit():
    readme = (ROOT / "skills/development/README.md").read_text(encoding="utf-8")
    lifecycle = (
        ROOT / "skills/development/references/development-lifecycle.md"
    ).read_text(encoding="utf-8")

    assert "them once per task mode" in readme
    assert "Repeated guidance may be duplicated deliberately" not in readme
    assert "not project-wide invariants" in lifecycle
    assert "derive its members and counts from the same current" in lifecycle
    assert "Do not create a release receipt" in lifecycle
    assert "Linux amd64 with CPython 3.14" in lifecycle


def test_development_loop_keeps_related_evidence_together_without_release_work():
    readme = (ROOT / "skills/development/README.md").read_text(encoding="utf-8")
    lifecycle = (
        ROOT / "skills/development/references/development-lifecycle.md"
    ).read_text(encoding="utf-8")
    core = (
        ROOT / "skills/development/references/scirel-development-core.md"
    ).read_text(encoding="utf-8")
    integration = (
        ROOT / "skills/development/integration/scirel-integration/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "direct product development (default)" in readme
    assert "D1 integration" in readme
    assert "SciPy-style change-set loop" in lifecycle
    assert "callable docstring" in lifecycle
    assert "comparable benchmark" in lifecycle
    assert "public API change needs import" in lifecycle
    assert "Neither claim requires a wheel or catalog" in lifecycle
    assert "Unknown" in core
    assert "unrelated work" in integration
    assert "development lifecycle" in integration


def test_direct_product_work_does_not_synthesize_d1_or_full_aoci_proof():
    core = (
        ROOT / "skills/development/references/scirel-development-core.md"
    ).read_text(encoding="utf-8")

    assert "Without an exact D1 packet" in core
    assert "AOCI is a repository-maintenance aid, not a development gate" in core
    assert "one applicable `aoci_maintain`" in core


def test_routed_development_skills_reuse_one_loaded_shared_contract():
    skill_paths = [
        ROOT / "skills/development/scientific-computation-validation/SKILL.md",
        ROOT / "skills/development/scientific-runtime-dataset-construction/SKILL.md",
        ROOT / "skills/development/integration/scientific-asset-correctness/SKILL.md",
        ROOT / "skills/development/integration/scientific-asset-normalization/SKILL.md",
        ROOT / "skills/development/integration/scirel-integration/SKILL.md",
        ROOT / "skills/development/integration/scirel-review-preparation/SKILL.md",
    ]

    for path in skill_paths:
        text = path.read_text(encoding="utf-8")
        assert "shared operating contract already loaded for this task mode" in text
        assert "do not reload it for each routed sub-skill" in text


def test_integration_route_points_to_lifecycle_without_copying_release_gates():
    integration = (
        ROOT / "skills/development/integration/scirel-integration/SKILL.md"
    ).read_text(encoding="utf-8")

    assert "[development lifecycle](../../references/development-lifecycle.md)" in integration
    assert "do not reproduce those rules here" in integration
    assert "release/CURRENT.json" not in integration
    assert "full platform matrix" not in integration


def test_development_selector_reads_live_catalog_without_release_current(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    live_catalog = ROOT / "catalog" / "examples"
    monkeypatch.setattr(selector, "CATALOG", live_catalog)
    monkeypatch.setattr(selector, "CURRENT_RELEASE", tmp_path / "missing-current.json")

    assets = selector._load_catalog_assets()

    assert len(assets) == len(list((ROOT / "catalog" / "examples").glob("*.json")))
    assert all(asset.asset_ref.startswith("scirel.") for asset in assets)
