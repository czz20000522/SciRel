"""验收证据渲染脚本只输出可复核的结论，匹配不上一律拒绝。"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "acceptance_evidence.py"
GREEN_WORDING = "ALL GREEN"


def _load():
    spec = importlib.util.spec_from_file_location("acceptance_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run_git(cwd, *arguments):
    env = {
        key: value for key, value in os.environ.items() if key not in {"GIT_DIR", "GIT_WORK_TREE"}
    }
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def clone(tmp_path, monkeypatch):
    """临时 Git 仓库加一份伪造的 receipt 缓存，脚本的根目录被指到这里。"""
    path = tmp_path / "clone"
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    _run_git(path, "config", "user.name", "SciRel test")
    _run_git(path, "config", "user.email", "scirel-test@example.invalid")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    _run_git(path, "add", "README.md")
    _run_git(path, "commit", "-m", "fixture")

    module = _load()
    monkeypatch.setattr(module.DEV, "ROOT", path)
    return module, path


def _head_tree(path):
    return _run_git(path, "rev-parse", "HEAD^{tree}").stdout.strip()


def _write_receipt(module, path, *, tree, architecture, checked_at_unix):
    """用脚本自己的命名规则伪造缓存条目，测试里不复制实现细节。"""
    directory = path / ".git" / "scirel-acceptance" / "receipts"
    directory.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": 3,
        "tree": tree,
        "architecture": architecture,
        "checked_at_unix": checked_at_unix,
        "command": module.DEV.CHECK_COMMAND,
        "image_id": "sha256:" + "a" * 64,
        "image_ref": module.DEV.IMAGE,
        "docker_context": "test-context",
    }
    filename = module.DEV._check_receipt_filename(tree, architecture)
    (directory / filename).write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    return directory / filename


def _assert_not_green(text):
    assert GREEN_WORDING not in text


def _template_block():
    text = (ROOT / "skills/development/scirel-acceptance/references/pr-evidence.md").read_text(
        encoding="utf-8"
    )
    start = text.index("```markdown\n") + len("```markdown\n")
    return text[start : text.index("\n```", start)]


def test_document_template_matches_the_rendered_block():
    """reference 里的模板就是脚本的输出，两边不许各改各的。"""
    module = _load()
    evidence = module.Evidence(
        tree="a" * 40,
        architecture="arm64",
        checked_at_unix=1_800_000_000.0,
        receipt_name="deadbeef.json",
        commit_short="1234abcd",
        commit_subject="示例提交标题",
        actor="Reviewer <reviewer@example.invalid>",
    )
    expected = (
        _template_block()
        .replace("<tree>", evidence.tree)
        .replace("<短 sha>", evidence.commit_short)
        .replace("<提交标题>", evidence.commit_subject)
        .replace("<arch>", evidence.architecture)
        .replace("<本地时间带时区>", module.local_time(evidence.checked_at_unix))
        .replace("<UTC 时间>", module.utc_time(evidence.checked_at_unix))
        .replace("<文件名>", evidence.receipt_name)
        .replace("<名字 <邮箱>>", evidence.actor)
    )
    assert expected.strip() == module.render(evidence).strip()


def test_matching_fresh_receipt_renders_the_paste_ready_block(clone, capsys):
    module, path = clone
    tree = _head_tree(path)
    architecture = platform.machine()
    _write_receipt(
        module, path, tree=tree, architecture=architecture, checked_at_unix=time.time() - 60
    )

    assert module.main(["--actor", "Reviewer"]) == 0
    captured = capsys.readouterr()

    assert captured.err == ""
    assert f"`{tree}`" in captured.out
    assert f"`{architecture}`" in captured.out
    assert "退出码 0" in captured.out
    assert "scripts/dev_container.py:867-873" in captured.out
    assert "schema 3" in captured.out
    assert "填表人：Reviewer" in captured.out
    assert ".git/scirel-acceptance/receipts/" in captured.out
    # 结论只能说到"本 clone 上某个 checkout"，receipt 不记录是谁、在哪个 checkout 里跑的。
    assert "本 clone 上某个 checkout 在该 tree 上跑过完整检查" in captured.out
    assert "真正跑检查的人未知" in captured.out
    # 措辞边界：不能声称知道谁跑的，也不能声称由哪个 checkout 写入。
    assert "在这个 worktree" not in captured.out
    assert "本 worktree" not in captured.out
    assert "谁跑的" not in captured.out


def test_tree_mismatch_is_refused_as_a_tree_mismatch(clone, capsys):
    module, path = clone
    architecture = platform.machine()
    _write_receipt(
        module,
        path,
        tree="0" * 40,
        architecture=architecture,
        checked_at_unix=time.time() - 60,
    )

    assert module.main([]) == 1
    captured = capsys.readouterr()

    assert "tree" in captured.err
    assert "不匹配" in captured.err
    assert captured.out == ""
    _assert_not_green(captured.err)


def test_architecture_mismatch_names_both_architectures(clone, capsys):
    module, path = clone
    tree = _head_tree(path)
    _write_receipt(
        module, path, tree=tree, architecture="other-arch", checked_at_unix=time.time() - 60
    )

    assert module.main([]) == 1
    captured = capsys.readouterr()

    assert "other-arch" in captured.err
    assert platform.machine() in captured.err
    assert "architecture" in captured.err
    _assert_not_green(captured.err)


def test_expired_receipt_is_refused(clone, capsys):
    module, path = clone
    _write_receipt(
        module,
        path,
        tree=_head_tree(path),
        architecture=platform.machine(),
        checked_at_unix=time.time() - 40 * 24 * 60 * 60,
    )

    assert module.main([]) == 1
    captured = capsys.readouterr()

    assert "过期" in captured.err
    assert "30" in captured.err
    _assert_not_green(captured.err)


def test_dirty_worktree_is_reported_before_a_missing_receipt(clone, capsys):
    module, path = clone
    (path / "scratch.txt").write_text("untracked\n", encoding="utf-8")

    assert module.main([]) == 1
    captured = capsys.readouterr()

    assert "未跟踪" in captured.err
    assert "#120" in captured.err
    assert "没有可用的验收 receipt" not in captured.err
    _assert_not_green(captured.err)


def test_empty_cache_says_the_cache_has_no_matching_receipt(clone, capsys):
    module, _path = clone

    assert module.main([]) == 1
    captured = capsys.readouterr()

    assert "缓存里没有任何匹配" in captured.err
    _assert_not_green(captured.err)
