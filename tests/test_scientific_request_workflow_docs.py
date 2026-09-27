from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_requirements_bind_reusable_intermediates_to_reuse_metadata():
    body = _read("docs/requirements/scientific-request-workflow.md")

    assert "可被后续请求复用的中间产物" in body
    assert "坐标轴" in body
    assert "support mask" in body
    assert "来源摘要" in body
    assert "不能证明原始运行的坐标字节一致" in body


def test_design_places_reusable_intermediate_binding_in_execution_evidence():
    body = _read("docs/design/scientific-request-workflow.md")
    section = body.split("### Execution Evidence", 1)[1].split("### Result Explanation", 1)[0]

    assert "可被后续请求复用的中间产物" in section
    assert "坐标轴" in section
    assert "support mask" in section
    assert "摘要绑定" in section


def test_requirements_require_rediscovery_when_later_request_adds_a_relation():
    body = _read("docs/requirements/scientific-request-workflow.md")

    assert "后续请求新增科学关系" in body
    assert "重新规范化" in body
    assert "重新检索" in body
    assert "早期 shortlist" in body
    assert "不能证明新关系不存在" in body


def test_design_separates_computed_observations_from_physical_mechanisms():
    body = _read("docs/design/scientific-request-workflow.md")
    section = body.split("### Result Explanation", 1)[1].split("## Harness 与 SciRel 的职责", 1)[0]

    assert "计算观察" in section
    assert "物理机制解释" in section
    assert "共振" in section
    assert "吸收" in section
    assert "额外关系或检查" in section


def test_solving_skill_blocks_unresolved_vacuum_flux_to_equilibrium_coupling():
    body = _read("skills/usage/scirel-solving/SKILL.md")

    assert "psi_vac" in body
    assert "vacuum" in body
    assert "equilibrium" in body
    assert "material support" in body
    assert "Wb/rad" in body
    assert "science owner" in body
    assert "flux definition" in body
    assert "Reassess the edge when the catalog version changes" in body
    assert "vacuum-field labels such as `Wb`" not in body


def test_workflow_document_changes_select_their_doc_contract_test():
    command = [
        sys.executable,
        str(ROOT / "scripts" / "select_affected_tests.py"),
        "--format",
        "json",
        "--changed-path",
        "docs/requirements/scientific-request-workflow.md",
        "--changed-path",
        "docs/design/scientific-request-workflow.md",
    ]

    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_scientific_request_workflow_docs.py"]


def test_outbound_method_changes_select_their_contract_test():
    method_paths = (
        "skills/usage/scirel-solving/SKILL.md",
        "skills/usage/scirel-solving/references/thin-adapter-run.md",
        "skills/usage/scientific-asset-navigation/SKILL.md",
        "skills/usage/scientific-project-implementation/SKILL.md",
    )
    for path in method_paths:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "select_affected_tests.py"),
                "--format",
                "json",
                "--changed-path",
                path,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, (path, completed.stderr)
        result = json.loads(completed.stdout)
        assert result["full_suite_required"] is False, path
        assert "tests/test_scientific_request_workflow_docs.py" in result["test_paths"], path
