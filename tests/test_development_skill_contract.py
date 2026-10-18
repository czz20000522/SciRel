from pathlib import Path

import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import select_affected_tests as selector  # noqa: E402


def compact(text: str) -> str:
    return " ".join(text.split())


def test_development_skill_changes_use_one_lightweight_contract_test():
    changed = [
        "AGENTS.md",
        "skills/development/README.md",
        "skills/development/references/development-lifecycle.md",
        "skills/development/references/scirel-development-core.md",
        "skills/development/integration/scirel-integration/SKILL.md",
        "skills/development/integration/scirel-review-preparation/SKILL.md",
    ]

    result = selector.select(changed)

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_development_skill_contract.py"]


def test_project_contract_routes_agents_changes_to_the_lightweight_contract():
    result = selector.select(["AGENTS.md"])

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_development_skill_contract.py"]


def test_project_contract_keeps_ordinary_optimization_out_of_release_flow():
    project_contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "当前默认开发模式" in project_contract
    assert "普通任务默认处于 `development`" in project_contract
    assert "不会启动发布流程" in project_contract
    assert "数量只属于具体 manifest/revision" in project_contract
    assert "多个相互关联的小修复可以合并为一个变更批次" in project_contract
    assert "长程 goal 只是待处理 claim 的队列" in project_contract
    assert "首次公开发布时才选择初始 `major.minor`" in project_contract
    assert "按 SciPy 式标准库结构维护一个当前源树" in project_contract
    assert "canonical direct test 路径" in project_contract
    assert "遵循该入口" in project_contract
    assert "一个主要 claim、一个 owned scope 和一个 stop condition" in project_contract
    assert "不因状态查询、继续或不变证据制造新提交" in project_contract


def test_lifecycle_requires_selector_visible_regressions():
    lifecycle = compact(
        (ROOT / "skills/development/references/development-lifecycle.md").read_text(
            encoding="utf-8"
        )
    )

    assert "canonical direct test path" in lifecycle
    assert "daily selector cannot reach" in lifecycle


def test_lifecycle_keeps_incubation_counts_dynamic_and_release_gates_explicit():
    readme = compact((ROOT / "skills/development/README.md").read_text(encoding="utf-8"))
    lifecycle = compact(
        (ROOT / "skills/development/references/development-lifecycle.md").read_text(
            encoding="utf-8"
        )
    )

    assert "them once per task mode" in readme
    assert "Repeated guidance may be duplicated deliberately" not in readme
    assert "not project-wide invariants" in lifecycle
    assert "derive its members and counts from the same current" in lifecycle
    assert "Do not create a release receipt" in lifecycle
    assert "Linux amd64 with CPython 3.14" in lifecycle
    assert "Reuse a previous result" in lifecycle
    assert "does not by itself justify replaying the same validation" in lifecycle
    assert "per-iteration release records" in lifecycle
    assert "one minimal pass" in lifecycle
    assert "initial claim-matched check set" in lifecycle
    assert "not reasons to start a companion route" in lifecycle
    assert "durable decision, blocker or next action" in lifecycle
    assert "queue of possible claims, not an execution scheduler" in lifecycle
    assert "Release acceptance means the frozen wheel/document/catalog" in lifecycle
    assert "exact clean ref" in readme
    assert "source_dirty" in readme
    assert "same-revision rule applies only when a wheel" in readme
    assert "For every task" not in readme


def test_development_loop_keeps_related_evidence_together_without_release_work():
    readme = (ROOT / "skills/development/README.md").read_text(encoding="utf-8")
    lifecycle = (
        ROOT / "skills/development/references/development-lifecycle.md"
    ).read_text(encoding="utf-8")
    core = compact(
        (ROOT / "skills/development/references/scirel-development-core.md").read_text(
            encoding="utf-8"
        )
    )
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


def test_skill_routes_structural_reference_adoption_without_native_build_drift():
    readme = (ROOT / "skills/development/README.md").read_text(encoding="utf-8")

    assert "domain self-contained" in readme
    assert "top-level namespace small" in readme
    assert "Do not add a native build system" in readme


def test_heavy_development_routes_are_explicit_only():
    for relative in (
        "skills/development/integration/scirel-integration/agents/openai.yaml",
        "skills/development/integration/scirel-review-preparation/agents/openai.yaml",
        "skills/development/post-acceptance-runtime-cleanup/agents/openai.yaml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "allow_implicit_invocation: false" in text

    integration = (
        ROOT / "skills/development/integration/scirel-integration/agents/openai.yaml"
    ).read_text(encoding="utf-8")
    assert "exact D1 packet" in integration


def test_scientific_validation_scopes_coverage_to_the_named_claim():
    text = (ROOT / "skills/development/scientific-computation-validation/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "target and affected capability closure" in compact(text)
    assert "only when the claim explicitly concerns a complete project" in compact(text)


def test_direct_product_work_does_not_synthesize_d1_or_full_aoci_proof():
    core = compact(
        (ROOT / "skills/development/references/scirel-development-core.md").read_text(
            encoding="utf-8"
        )
    )

    assert "Without an exact D1 packet" in core
    assert "AOCI is a repository-maintenance aid, not a development gate" in core
    assert "one applicable `aoci_maintain` after" in core
    assert "dirty artifact is explicitly requested" in core
    assert "minimal execution and stop rule" in core
    assert "**release_freeze**" not in core


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
