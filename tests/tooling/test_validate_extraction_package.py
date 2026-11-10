"""The extraction package validator accepts a well-formed package and names each defect."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_extraction_package.py"
TEMPLATE = "scirel.fusion.dd-neutron-lab-energy"
NEW_ID = "scirel.fusion.demo-relation"
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@invalid",
}


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, env=GIT_ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


PACKAGE_MD = """# 演示拆解

- 状态：partial
- 范围：只要能力 演示关系
- 冻结 SciReL commit：{commit}
- 来源版本：见 private/source.md
- 完整检查：NOT_RUN（演示）
- 对账：关系卡 3 = 已有 1 + 新 method 0 + 全新 1 + 不收 1

## 未完成项
- 完整检查尚未运行
"""
MANIFEST = f"""| 关系 | 结论 | 合同 ID | 领域 / 层 | 族 / method | 题库题号 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 中子能量 | 已有 | {TEMPLATE} | fusion / L2 | — | — | 对照一致 |
| 演示关系 | 全新 | {NEW_ID} | fusion / L2 | — | — | — |
| 结果绘图 | 不收 | — | — | — | — | — |
"""
DISPOSITION = """| 来源部分（模块或文件的中性描述） | 类别 | 理由 |
| --- | --- | --- |
| 结果绘图 | 画图 | 不属于物理关系 |
"""
EVIDENCE = """## 测试矩阵
| 用例 | 类别 | 预期值依据 | 依据出处 | 结果 |
| --- | --- | --- | --- | --- |
| 零输入 | 退化 | 解析 | 推导 | passed |
| 同输入对照 | 正常 | 来源输出 | private/ | passed |
"""


@pytest.fixture
def setup(tmp_path):
    repo = tmp_path / "repo"
    (repo / "catalog/examples").mkdir(parents=True)
    for path in (ROOT / "catalog/examples").glob("*.json"):
        shutil.copy(path, repo / "catalog/examples" / path.name)
    _git(tmp_path, "init", "-q", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "frozen")
    commit = _git(repo, "rev-parse", "HEAD")

    contract = json.loads((ROOT / f"catalog/examples/{TEMPLATE}.json").read_text(encoding="utf-8"))
    contract["asset_id"] = NEW_ID
    api = contract["public_api"]["python"]
    api["signature"] = api["signature"].replace(api["symbol"], "compute_demo_relation")
    api.update(
        module="scirel.fusion.demo_relation",
        symbol="compute_demo_relation",
        canonical_symbol="compute_demo_relation",
    )
    contract["verification"]["tests"] = ["tests/fusion/test_demo_relation.py"]
    (repo / f"catalog/examples/{NEW_ID}.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2)
    )
    (repo / "tests/fusion").mkdir(parents=True)
    (repo / "tests/fusion/test_demo_relation.py").write_text(
        "def test_placeholder():\n    assert True\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "add demo relation")

    package = tmp_path / "package"
    for sub in ("patch", "evidence", "tickets", "private"):
        (package / sub).mkdir(parents=True)
    _git(repo, "format-patch", "-q", "-o", str(package / "patch"), commit)
    _git(repo, "reset", "-q", "--hard", commit)
    (package / "PACKAGE.md").write_text(PACKAGE_MD.format(commit=commit), encoding="utf-8")
    (package / "manifest.md").write_text(MANIFEST, encoding="utf-8")
    (package / "disposition.md").write_text(DISPOSITION, encoding="utf-8")
    (package / f"evidence/{NEW_ID}.md").write_text(EVIDENCE, encoding="utf-8")
    (package / "private/source.md").write_text("- 名称：AcmeSolver\n", encoding="utf-8")
    return package, repo


def _run(package, repo):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(package), "--repo", str(repo), "--fast"],
        capture_output=True,
        text=True,
    )
    return done.returncode, done.stdout + done.stderr


def test_well_formed_package_passes_but_fast_is_never_green(setup):
    code, out = _run(*setup)
    assert code == 2, out
    assert "PASS     contracts" in out
    assert "NOT_RUN  full check" in out and "NOT_RUN  mutation" in out


def test_reconciliation_mismatch_is_reported(setup):
    package, repo = setup
    text = (
        (package / "PACKAGE.md")
        .read_text(encoding="utf-8")
        .replace("不收 1", "不收 2")
        .replace("关系卡 3", "关系卡 4")
    )
    (package / "PACKAGE.md").write_text(text, encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 1 and "do not match PACKAGE.md 对账" in out, out


def test_source_identity_outside_private_is_rejected(setup):
    package, repo = setup
    (package / "manifest.md").write_text(
        MANIFEST.replace("对照一致", "与 acmesolver 对照一致"), encoding="utf-8"
    )
    code, out = _run(package, repo)
    assert code == 1 and "source identity 'AcmeSolver'" in out, out


def test_new_contract_needs_evidence(setup):
    package, repo = setup
    (package / f"evidence/{NEW_ID}.md").unlink()
    code, out = _run(package, repo)
    assert code == 1 and f"evidence/{NEW_ID}.md is missing" in out, out


def test_domain_column_must_match_the_id(setup):
    package, repo = setup
    (package / "manifest.md").write_text(
        MANIFEST.replace(
            "| 全新 | scirel.fusion.demo-relation | fusion / L2",
            "| 全新 | scirel.fusion.demo-relation | field / L3",
        ),
        encoding="utf-8",
    )
    code, out = _run(package, repo)
    assert code == 1 and "!= 领域 'field'" in out, out


def test_marking_an_existing_contract_as_new_is_rejected(setup):
    package, repo = setup
    (package / "manifest.md").write_text(
        MANIFEST.replace(f"| 已有 | {TEMPLATE}", f"| 全新 | {TEMPLATE}").replace(
            "已有 1 + 新 method 0 + 全新 1", "已有 0 + 新 method 0 + 全新 2"
        ),
        encoding="utf-8",
    )
    text = (
        (package / "PACKAGE.md")
        .read_text(encoding="utf-8")
        .replace("已有 1 + 新 method 0 + 全新 1", "已有 0 + 新 method 0 + 全新 2")
    )
    (package / "PACKAGE.md").write_text(text, encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 1 and "already exists in the frozen catalog" in out, out


def test_unknown_frozen_commit_is_rejected(setup):
    package, repo = setup
    text = (package / "PACKAGE.md").read_text(encoding="utf-8")
    commit = _git(repo, "rev-parse", "HEAD")
    (package / "PACKAGE.md").write_text(text.replace(commit, "0" * 40), encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 1 and "is not in" in out, out


def test_done_requires_a_green_full_check(setup):
    package, repo = setup
    text = (package / "PACKAGE.md").read_text(encoding="utf-8")
    text = text.replace("状态：partial", "状态：done").replace("- 完整检查尚未运行", "- 无")
    (package / "PACKAGE.md").write_text(text, encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 1 and "状态 done needs a full-check line" in out, out


def test_package_ticket_must_follow_the_format(setup):
    package, repo = setup
    (package / "tickets/T-2026-0001.md").write_text("---\nid: T-2026-0001\n---\n", encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 1 and "missing key: kind" in out, out


def _commit_onto_package(package, repo, change):
    """Rebuild the package patch with one more commit made by ``change(repo)``."""
    commit = [
        line
        for line in (package / "PACKAGE.md").read_text(encoding="utf-8").splitlines()
        if "冻结 SciReL commit" in line
    ][0].split("：")[1]
    for patch in sorted((package / "patch").glob("*.patch")):
        _git(repo, "am", "-q", str(patch))
    change(repo)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "extra change")
    for patch in (package / "patch").glob("*.patch"):
        patch.unlink()
    _git(repo, "format-patch", "-q", "-o", str(package / "patch"), commit)
    _git(repo, "reset", "-q", "--hard", commit)


def _edit_existing_contract(repo):
    path = repo / f"catalog/examples/{TEMPLATE}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["summary"] += " Changed."
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_unlisted_added_contract_is_rejected(setup):
    package, repo = setup

    def add_unlisted(repo):
        source = repo / f"catalog/examples/{NEW_ID}.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["asset_id"] = "scirel.fusion.hidden-relation"
        data["public_api"]["python"]["module"] = "scirel.fusion.hidden_relation"
        (repo / "catalog/examples/scirel.fusion.hidden-relation.json").write_text(
            json.dumps(data), encoding="utf-8"
        )

    _commit_onto_package(package, repo, add_unlisted)
    code, out = _run(package, repo)
    assert (
        code == 1 and "adds scirel.fusion.hidden-relation but manifest.md marks it nowhere" in out
    ), out


def test_changed_existing_contract_must_be_declared(setup):
    package, repo = setup
    _commit_onto_package(package, repo, _edit_existing_contract)
    code, out = _run(package, repo)
    assert code == 1 and f"the patch changes {TEMPLATE} but manifest.md marks it 已有" in out, out


def test_declared_correction_of_existing_contract_needs_evidence(setup):
    package, repo = setup

    def correct(repo):
        _edit_existing_contract(repo)
        for test in json.loads(
            (repo / f"catalog/examples/{TEMPLATE}.json").read_text(encoding="utf-8")
        )["verification"]["tests"]:
            (repo / test).parent.mkdir(parents=True, exist_ok=True)
            (repo / test).write_text("def test_placeholder():\n    assert True\n")

    _commit_onto_package(package, repo, correct)
    (package / "manifest.md").write_text(MANIFEST.replace("对照一致", "物理纠正"), encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 1 and f"{TEMPLATE}: evidence/{TEMPLATE}.md is missing" in out, out
    (package / f"evidence/{TEMPLATE}.md").write_text(EVIDENCE, encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 2, out
