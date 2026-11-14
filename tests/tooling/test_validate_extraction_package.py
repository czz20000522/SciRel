"""The extraction package validator accepts a well-formed package and names each defect."""

import json
import importlib.util
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
| 合同下界 | 下界 | 解析 | 边界推导 | passed |
| 合同上界 | 上界 | 解析 | 渐近推导 | passed |
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
    assert "NOT_RUN  contracts" in out, out
    assert "NOT_RUN  full check" in out, out
    assert "NOT_RUN  mutation" in out, out


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
    assert code == 1 and "原行为" in out, out
    (package / f"evidence/{TEMPLATE}.md").write_text(
        EVIDENCE
        + "\n## 物理纠正\n- 原行为：旧关系\n- 依据：独立推导\n- 改动：修正系数\n- 前后对比：同输入对比见测试\n",
        encoding="utf-8",
    )
    code, out = _run(package, repo)
    assert code == 2, out


@pytest.mark.parametrize("state", ["failed", "blocked", "NOT_RUN", "inapplicable"])
def test_unpassed_required_evidence_is_not_admission(setup, state):
    package, repo = setup
    (package / f"evidence/{NEW_ID}.md").write_text(EVIDENCE.replace("passed", state))
    code, out = _run(package, repo)
    assert code == 1 and "evidence" in out, out


@pytest.mark.parametrize(
    "path",
    [
        "pyproject.toml",
        "pytest.ini",
        "tests/conftest.py",
        "skills/development/scirel-acceptance/scripts/check_all.py",
    ],
)
def test_scientific_patches_cannot_change_the_admission_rules(setup, path):
    package, repo = setup

    def change(root):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# validation must not be rewritten by the scientific patch\n")

    _commit_onto_package(package, repo, change)
    code, out = _run(package, repo)
    assert code == 1 and path in out, out


def test_empty_cases_and_missing_boundaries_are_rejected(setup):
    package, repo = setup
    (package / f"evidence/{NEW_ID}.md").write_text("""| 用例 | 类别 | 预期值依据 | 依据出处 | 结果 |
| --- | --- | --- | --- | --- |
| | 正常 | 解析 | 推导 | passed |
""")
    code, out = _run(package, repo)
    assert code == 1 and "case name" in out and "下界" in out and "上界" in out, out


def _validator():
    spec = importlib.util.spec_from_file_location("package_validator_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mock_lock_boundary(module, monkeypatch):
    """Report/environment protocol fixtures only; not real exclusive acceptance evidence."""
    monkeypatch.setattr(
        module, "require_exclusive", lambda tree, expected=None: expected or "fixture"
    )


def test_an_empty_full_check_is_not_passed(tmp_path, monkeypatch):
    module = _validator()
    _mock_lock_boundary(module, monkeypatch)
    tree = _acceptance_candidate(tmp_path)
    script = tree / "skills/development/scirel-acceptance/scripts/check_all.py"
    script.parent.mkdir(parents=True)
    script.write_text('def main():\n    raise AssertionError("gate never entered")\n')
    _git(tree, "add", ".")
    _git(tree, "commit", "-qm", "empty gate fixture")
    monkeypatch.setattr(
        module,
        "_run_in_candidate",
        lambda tree, command: subprocess.run(
            [sys.executable, *command[1:]], cwd=tree, capture_output=True, text=True
        ),
    )
    report = module.Report()
    module.run_full_check(tree, report)
    assert report.sections[-1][1] == "FAIL", report.sections


def test_successful_rerun_supersedes_the_same_case_failure(setup):
    package, repo = setup
    history = EVIDENCE.replace(
        "| 零输入", "| 同输入对照 | 正常 | 来源输出 | private/ | failed |\n| 零输入"
    )
    (package / f"evidence/{NEW_ID}.md").write_text(history, encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 2, out


def test_old_failed_independent_evidence_does_not_upgrade_source_only_reruns(setup):
    package, repo = setup
    current = EVIDENCE.replace("| 解析 |", "| 来源输出 |")
    current = current.replace(
        "| 零输入 |", "| 零输入 | 退化 | 解析 | 推导 | failed |\n| 零输入 |", 1
    )
    (package / f"evidence/{NEW_ID}.md").write_text(current, encoding="utf-8")
    code, out = _run(package, repo)
    assert code == 2 and "1 with source-output evidence only" in out, out


def _acceptance_candidate(directory):
    tree = directory / "candidate"
    tree.mkdir()
    _git(tree, "init", "-q")
    (tree / ".gitignore").write_text(".runtime/\n")
    for name in ("uv.lock", ".python-version"):
        shutil.copy(ROOT / name, tree / name)
    # The plan must be based on the actual patched tree, including newly added reports.
    example = tree / "examples/patched/REPORT.md"
    example.parent.mkdir(parents=True)
    example.write_text("fixture report\n")
    _git(tree, "add", ".")
    _git(tree, "commit", "-qm", "patched candidate fixture")
    return tree


@pytest.mark.parametrize("stage", ["full check", "mutation"])
def test_unlocked_candidate_never_starts_admission(tmp_path, monkeypatch, stage):
    module = _validator()
    tree = _acceptance_candidate(tmp_path)
    monkeypatch.setattr(
        module, "_run_in_candidate", lambda *args: pytest.fail("unlocked admission started")
    )
    report = module.Report()
    report.output_dir = tmp_path
    if stage == "full check":
        module.run_full_check(tree, report)
    else:
        module.run_mutation(tree, [NEW_ID], report)
    assert report.sections[-1][:2] == (stage, "FAIL")
    assert "exclusive" in " ".join(report.errors).lower()


@pytest.mark.parametrize("stage", ["full check", "mutation"])
@pytest.mark.parametrize("change", ["retired", "replaced"])
def test_admission_rechecks_the_same_live_credential(tmp_path, monkeypatch, stage, change):
    """Real EX lock and a real subprocess; the tiny probe is not a full acceptance run."""
    module = _validator()
    import dev

    tree = _acceptance_candidate(tmp_path)
    monkeypatch.setattr(dev, "ROOT", tree)
    report = module.Report()
    report.output_dir = tmp_path
    with dev.acceptance_lock(exclusive=True), dev.exclusive_credential() as token:
        monkeypatch.setenv(dev.EXCLUSIVE_MARKER, token)
        record = dev.runtime_paths()["locks"] / dev.EXCLUSIVE_RECORD

        def execute(candidate, command):
            # Do not manufacture a full-check result: only change the real lock record.
            done = subprocess.run(
                [sys.executable, "-B", "-c", "print('credential boundary probe only')"],
                capture_output=True,
                text=True,
                check=True,
            )
            if change == "retired":
                record.unlink()
            else:
                record.write_text("new-invocation")
                monkeypatch.setenv(dev.EXCLUSIVE_MARKER, "new-invocation")
            return done

        monkeypatch.setattr(module, "_run_in_candidate", execute)
        if stage == "full check":
            module.run_full_check(tree, report, exclusive_token=token)
        else:
            module.run_mutation(tree, [NEW_ID], report, exclusive_token=token)
    assert report.sections[-1][:2] == (stage, "FAIL")
    assert "exclusive" in " ".join(report.errors).lower()
    assert (
        "credential boundary probe only"
        in (tmp_path / f"{stage.replace(' ', '-')}.log").read_text()
    )


def test_full_validation_refuses_another_clone_before_applying_patches(
    setup, tmp_path, monkeypatch
):
    _validator()
    import dev

    package, candidate_repo = setup
    receiver = tmp_path / "receiver"
    _git(tmp_path, "clone", "--quiet", str(candidate_repo), str(receiver))
    monkeypatch.setattr(dev, "ROOT", receiver)
    with dev.acceptance_lock(exclusive=True), dev.exclusive_credential() as token:
        env = dict(os.environ, **{dev.EXCLUSIVE_MARKER: token})
        done = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(package), "--repo", str(candidate_repo)],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "exclusive lock required" in done.stdout
    assert "NOT_RUN  patch" in done.stdout


def _acceptance_result(module, directory, tree):
    records = []
    output = tree / ".runtime/tmp/fixture-check"
    executable = (
        tree / ".runtime/venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    for index, step in enumerate(
        module.acceptance_steps(output, root=tree, executable=str(executable))
    ):
        log = directory / f"step-{index}.log"
        log.write_text(f"complete output for {step.name}\n", encoding="utf-8")
        records.append(
            {
                "name": step.name,
                "status": "PASS",
                "returncode": 0,
                "log": str(log),
                "argv": step.command,
                "started": True,
            }
        )
    identity = module.candidate_identity(tree)
    import check_all

    environment = check_all.runtime_environment(tree)
    return {
        "schema": "scirel.acceptance.v1",
        "candidate": {"before": dict(identity), "after": dict(identity)},
        "environment": {"before": dict(environment), "after": dict(environment)},
        "run_id": "stale fixture invocation",
        "binding_errors": [],
        "evidence": "clean_candidate",
        "steps": records,
        "exit_code": 0,
        "tests": {
            "collected": 2,
            "selected": 2,
            "deselected": 0,
            "passed": 2,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "xfailed": 0,
            "xpassed": 0,
            "consistent": True,
            "skip_reasons": {},
        },
    }


@pytest.mark.parametrize(
    "defect", [None, "nonzero", "missing step", "missing counts", "NOT_RUN", "missing output"]
)
def test_full_result_protocol_preserves_the_actual_output(tmp_path, monkeypatch, defect):
    """Exercise the report consumer; this fixture is not a real package acceptance run."""
    module = _validator()
    _mock_lock_boundary(module, monkeypatch)
    tree = _acceptance_candidate(tmp_path)
    report = module.Report()
    report.output_dir = tmp_path
    result = _acceptance_result(module, tmp_path, tree)
    code = 0
    if defect == "nonzero":
        code = result["exit_code"] = 1
        result["steps"][0].update(status="FAIL", returncode=1)
    elif defect == "missing step":
        result["steps"].pop()
    elif defect == "missing counts":
        result["tests"] = None
    elif defect == "NOT_RUN":
        result["steps"][0].update(status="NOT_RUN", returncode=None)
    elif defect == "missing output":
        Path(result["steps"][0]["log"]).unlink()

    def execute(tree, command):
        result["run_id"] = command[command.index("--run-id") + 1]
        Path(command[-1]).write_text(json.dumps(result), encoding="utf-8")
        return subprocess.CompletedProcess(
            command, code, "earliest cause: fixture diagnostic\n", ""
        )

    monkeypatch.setattr(module, "_run_in_candidate", execute)
    module.run_full_check(tree, report)
    assert report.sections[-1][1] == ("PASS" if defect is None else "FAIL"), report.errors
    assert "earliest cause" in (tmp_path / "full-check.log").read_text()
    if defect is None:
        assert "selected 2" in report.sections[-1][2]


@pytest.mark.parametrize(
    "defect",
    [
        "missing identity",
        "same tree different commit",
        "all skipped",
        "not started",
        "missing argv",
        "wrong argv",
        "stale invocation",
        "identity drift",
        "environment drift",
        "missing lock digest",
        "dirty",
        "development",
        "missing report",
    ],
)
def test_unbound_green_is_refused(tmp_path, monkeypatch, defect):
    module = _validator()
    _mock_lock_boundary(module, monkeypatch)
    tree = _acceptance_candidate(tmp_path)
    report = module.Report()
    report.output_dir = tmp_path
    if defect == "dirty":
        (tree / "untracked.txt").write_text("development only\n")
    result = _acceptance_result(module, tmp_path, tree)
    if defect == "missing identity":
        del result["candidate"]
    if defect == "same tree different commit":
        _git(tree, "commit", "--allow-empty", "-qm", "same tree different commit")
        assert result["candidate"]["before"]["tree"] == _git(tree, "rev-parse", "HEAD^{tree}")
        assert result["candidate"]["before"]["commit"] != _git(tree, "rev-parse", "HEAD")
    elif defect == "all skipped":
        result["tests"].update(passed=0, skipped=2, skip_reasons={"absent": ["a", "b"]})
    elif defect == "not started":
        result["steps"][0]["started"] = False
    elif defect == "missing argv":
        del result["steps"][0]["argv"]
    elif defect == "wrong argv":
        result["steps"][0]["argv"].extend(["-k", "smoke"])
    elif defect == "missing lock digest":
        for environment in result["environment"].values():
            del environment["uv_lock_sha256"]
    elif defect == "development":
        result["evidence"] = "development"

    def execute(tree, command):
        if defect != "stale invocation":
            result["run_id"] = command[command.index("--run-id") + 1]
        path = tmp_path / "acceptance.json" if defect == "missing report" else Path(command[-1])
        path.write_text(json.dumps(result), encoding="utf-8")
        if defect == "identity drift":
            _git(tree, "commit", "--allow-empty", "-qm", "changed while running")
        elif defect == "environment drift":
            (tree / "uv.lock").write_text("changed during execution\n")
        return subprocess.CompletedProcess(command, 0, "fixture only\n", "")

    monkeypatch.setattr(module, "_run_in_candidate", execute)
    module.run_full_check(tree, report)
    assert report.sections[-1][1] == "FAIL", report.errors
    assert "fixture only" in (tmp_path / "full-check.log").read_text()


@pytest.mark.parametrize("use_frozen_identity", [False, True])
def test_full_check_binds_the_git_am_candidate_not_its_frozen_base(
    tmp_path, monkeypatch, use_frozen_identity
):
    module = _validator()
    _mock_lock_boundary(module, monkeypatch)
    tree = _acceptance_candidate(tmp_path)
    frozen = module.candidate_identity(tree)
    (tree / "patched.txt").write_text("candidate addition\n")
    _git(tree, "add", ".")
    _git(tree, "commit", "-qm", "candidate patch")
    patch = _git(tree, "format-patch", "--stdout", "HEAD^..HEAD")
    patch_path = tree / ".runtime/candidate.patch"
    patch_path.parent.mkdir()
    patch_path.write_text(patch + "\n")
    _git(tree, "reset", "--hard", frozen["commit"])
    _git(tree, "am", str(patch_path))
    patched = module.candidate_identity(tree)
    assert patched["commit"] != frozen["commit"]
    assert patched["tree"] != frozen["tree"]
    result = _acceptance_result(module, tmp_path, tree)
    if use_frozen_identity:
        result["candidate"] = {"before": frozen, "after": frozen}

    def execute(candidate, command):
        assert candidate == tree
        result["run_id"] = command[command.index("--run-id") + 1]
        Path(command[-1]).write_text(json.dumps(result), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "fixture output\n", "")

    monkeypatch.setattr(module, "_run_in_candidate", execute)
    report = module.Report()
    report.output_dir = tmp_path
    module.run_full_check(tree, report)
    assert report.sections[-1][1] == ("FAIL" if use_frozen_identity else "PASS"), report.errors


def test_candidate_interpreter_is_not_assumed_to_be_the_receivers(tmp_path, monkeypatch):
    module = _validator()
    _mock_lock_boundary(module, monkeypatch)
    tree = _acceptance_candidate(tmp_path)
    candidate_version = "3.12.9"
    assert candidate_version != ".".join(map(str, sys.version_info[:3]))
    (tree / ".python-version").write_text(candidate_version + "\n")
    _git(tree, "add", ".python-version")
    _git(tree, "commit", "-qm", "candidate interpreter pin fixture")
    result = _acceptance_result(module, tmp_path, tree)
    for environment in result["environment"].values():
        environment["python"] = {"implementation": "CPython", "version": candidate_version}

    def execute(candidate, command):
        result["run_id"] = command[command.index("--run-id") + 1]
        Path(command[-1]).write_text(json.dumps(result), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "fixture only\n", "")

    monkeypatch.setattr(module, "_run_in_candidate", execute)
    report = module.Report()
    report.output_dir = tmp_path
    module.run_full_check(tree, report)
    assert report.sections[-1][1] == "PASS", report.errors


def test_candidate_runtime_does_not_rebind_the_callers_environment(tmp_path, monkeypatch):
    module = _validator()
    _mock_lock_boundary(module, monkeypatch)
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts/dev.py", tmp_path / "scripts/dev.py")
    shutil.copy(ROOT / ".python-version", tmp_path / ".python-version")
    source = tmp_path / "src"
    source.mkdir()
    (source / "probe_candidate.py").write_text("VALUE = 'patched checkout'\n")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "caller-environment-must-not-change")
    monkeypatch.setenv("PYTHONPATH", "caller-source-must-not-load")
    env = module._candidate_environment(tmp_path)
    assert Path(env["UV_PROJECT_ENVIRONMENT"]) == tmp_path / ".runtime/venv"
    assert Path(env["TMPDIR"]) == tmp_path / ".runtime/tmp"
    assert env["PYTHONPATH"] == str(source)
    done = subprocess.run(
        [sys.executable, "-B", "-c", "import probe_candidate; print(probe_candidate.VALUE)"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0 and done.stdout.strip() == "patched checkout", done.stderr
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="candidate-probe"\nversion="0"\nrequires-python=">=3.12"\n'
        "[dependency-groups]\ntest=[]\n",
        encoding="utf-8",
    )
    locked = subprocess.run(["uv", "lock"], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert locked.returncode == 0, locked.stdout + locked.stderr
    actual = module._run_in_candidate(
        tmp_path,
        [
            "python",
            "-B",
            "-c",
            "import probe_candidate, sys; print(probe_candidate.VALUE); print(sys.prefix)",
        ],
    )
    assert actual.returncode == 0, actual.stdout + actual.stderr
    assert actual.stdout.splitlines() == ["patched checkout", str(tmp_path / ".runtime/venv")]
    assert os.environ["UV_PROJECT_ENVIRONMENT"] == "caller-environment-must-not-change"
