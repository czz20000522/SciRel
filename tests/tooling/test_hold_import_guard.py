"""Held implementations are not importable from the default package."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("SCIREL_REVIEW_HOLD", None)
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                          capture_output=True, text=True, env=env)


def test_held_symbol_is_not_importable_by_default():
    completed = _run(
        "from scirel.physics import calculate_log_lambda_ii;"
        "calculate_log_lambda_ii(3., 2e19, 2.)")
    assert completed.returncode != 0
    assert "human review" in completed.stderr or "No module named" in completed.stderr


def test_held_symbol_is_review_importable():
    env = dict(os.environ, SCIREL_REVIEW_HOLD="1")
    code = (
        "import sys; sys.path.insert(0, 'src');"
        "import scirel.physics as p;"
        "p.__path__.append('catalog/review/candidates/src/scirel/physics');"
        "print(p.calculate_log_lambda_ii(3., 2e19, 2.))")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, capture_output=True, text=True, env=env)
    assert completed.returncode == 0, completed.stderr
