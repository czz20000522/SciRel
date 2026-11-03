"""The pre-commit scan catches private paths and secrets, and nothing else."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "precommit_check", ROOT / "skills/development/scirel-acceptance/scripts/precommit_check.py")
precommit_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(precommit_check)


def _scan(text, name="a.md"):
    return precommit_check.scan([name], read=lambda _: text.encode())


def test_clean_text_passes():
    assert _scan("ordinary text with psi/R") == []


def test_private_path_and_secret_are_rejected():
    assert any("private path" in e for e in _scan("see /home/someone/x"))
    assert any("secret" in e for e in _scan("token ghp_" + "a" * 30))


def test_binary_suffixes_are_skipped():
    assert _scan("/home/someone/x", name="a.png") == []
