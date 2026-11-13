from pathlib import Path
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_extraction_kit as kit  # noqa: E402


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    source = tmp_path / "source-checkout"
    source.mkdir()
    _git(source, "init", "--quiet", "--initial-branch", "main")
    (source / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(source, "add", "module.py")
    _git(source, "commit", "--quiet", "-m", "first")
    first = _git(source, "rev-parse", "HEAD")
    (source / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(source, "commit", "--quiet", "-am", "second")
    return source, first


def test_kit_freezes_a_non_tip_commit_with_its_real_id(repo, tmp_path):
    source, first = repo
    output = tmp_path / "kit"

    assert kit.build_kit(source, first[:10], output) == first

    clone = output / "scirel"
    assert _git(clone, "rev-parse", "HEAD") == first
    assert _git(clone, "branch", "--show-current") == kit.BRANCH
    assert _git(clone, "rev-list", "--count", "HEAD") == "1"
    assert (clone / "module.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert first in (output / "KIT.md").read_text(encoding="utf-8")


def test_kit_carries_no_path_of_the_building_machine(repo, tmp_path):
    source, first = repo
    output = tmp_path / "kit"
    kit.build_kit(source, first, output)

    git_dir = output / "scirel" / ".git"
    assert not (git_dir / "FETCH_HEAD").exists()
    assert _git(output / "scirel", "remote") == ""
    for path in git_dir.rglob("*"):
        if path.is_file() and path.stat().st_size < 1_000_000:
            assert b"source-checkout" not in path.read_bytes(), path
    assert "source-checkout" not in (output / "KIT.md").read_text(encoding="utf-8")


def test_patch_made_in_the_kit_applies_on_the_original_commit(repo, tmp_path):
    source, first = repo
    output = tmp_path / "kit"
    kit.build_kit(source, first, output)
    clone = output / "scirel"
    (clone / "added.py").write_text("NEW = 3\n", encoding="utf-8")
    _git(clone, "add", "added.py")
    _git(clone, "commit", "--quiet", "-m", "add relation")
    patches = tmp_path / "patch"
    _git(clone, "format-patch", "--quiet", first, "-o", str(patches))

    target = tmp_path / "merge-line"
    _git(source, "worktree", "add", "--quiet", "--detach", str(target), first)
    _git(target, "am", "--quiet", *sorted(str(p) for p in patches.iterdir()))
    assert (target / "added.py").read_text(encoding="utf-8") == "NEW = 3\n"


def test_existing_output_is_refused(repo, tmp_path):
    source, first = repo
    output = tmp_path / "kit"
    output.mkdir()
    with pytest.raises(kit.KitError, match="already exists"):
        kit.build_kit(source, first, output)


def test_unknown_commit_names_the_argument(repo, tmp_path):
    source, _ = repo
    with pytest.raises(kit.KitError, match="--commit 'no-such-rev' does not name a commit"):
        kit.build_kit(source, "no-such-rev", tmp_path / "kit")
    assert not (tmp_path / "kit").exists()


def test_cli_reports_failure_with_nonzero_exit(repo, tmp_path, capsys):
    source, _ = repo
    code = kit.main(
        ["--repo", str(source), "--commit", "no-such-rev", "--output", str(tmp_path / "k")]
    )
    assert code == 1
    assert "FAIL" in capsys.readouterr().err


def _clean_identity_env(tmp_path):
    """Return an environment with no usable git identity, like a fresh HOME."""
    home = tmp_path / "clean-home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ)
    for name in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "EMAIL",
    ):
        env.pop(name, None)
    env.update(
        {
            "HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(home / "no-global-config"),
            # git 2.54 can synthesize "user@hostname" when no identity is configured,
            # so "no config" does not guarantee a failed commit. Disable the guess
            # explicitly; this stays independent of the host's user name and hostname.
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "user.useConfigOnly",
            "GIT_CONFIG_VALUE_0": "true",
        }
    )
    return env


# 验证：按 KIT.md 的步骤在无 git 身份的干净环境里能提交；缺这一步时提交确实失败。
def test_documented_identity_step_makes_the_commit_work_in_a_clean_home(repo, tmp_path):
    source, first = repo
    output = tmp_path / "kit"
    kit.build_kit(source, first, output)
    text = (output / "KIT.md").read_text(encoding="utf-8")
    assert "git -C scirel config user.name" in text
    assert "git -C scirel config user.email" in text

    clone = output / "scirel"
    (clone / "added.py").write_text("NEW = 3\n", encoding="utf-8")
    env = _clean_identity_env(tmp_path)
    subprocess.run(["git", "add", "added.py"], cwd=clone, env=env, check=True)
    without_identity = subprocess.run(
        ["git", "commit", "--quiet", "-m", "add relation"],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
    )
    assert without_identity.returncode != 0
    assert "auto-detect" in (without_identity.stdout + without_identity.stderr)

    for command in (
        ["git", "-C", "scirel", "config", "user.name", "extractor"],
        ["git", "-C", "scirel", "config", "user.email", "extractor@example.invalid"],
    ):
        subprocess.run(command, cwd=output, env=env, check=True, capture_output=True)
    committed = subprocess.run(
        ["git", "commit", "--quiet", "-m", "add relation"],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
    )
    assert committed.returncode == 0, committed.stderr
    assert _git(clone, "rev-parse", "HEAD") != first
