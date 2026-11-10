"""The pre-commit scan catches private paths and secrets, and nothing else."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/development/scirel-acceptance/scripts/precommit_check.py"
spec = importlib.util.spec_from_file_location("precommit_check", SCRIPT)
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


def test_script_runs_in_an_isolated_interpreter_without_pythonpath():
    """The hook runs this with ``python3 -I`` on a host that has no project environment.

    ``-S`` drops site-packages as well, so an import of any third-party package fails here instead of
    working by accident in the development container.
    """
    env = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}
    done = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "Traceback" not in done.stdout + done.stderr
    assert done.returncode == 0
    assert done.stdout.startswith("pre-commit: PASS")
