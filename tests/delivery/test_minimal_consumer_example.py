"""The consumer reference program must actually run and produce its artifact.

`examples/consumer/minimal_scirel_call.py` is the entry ticket for the
CodeFusion vertical slice: CodeFusion pastes it into its sandbox. If nothing
asserts its behaviour, its behaviour is not evidence. These two checks pin the
success path (artifact written, values match the bound contract example) and the
fail-closed path (missing `--out` exits nonzero instead of writing somewhere).
"""

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = ROOT / "examples" / "consumer" / "minimal_scirel_call.py"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-B", str(PROGRAM), *arguments],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_reference_program_writes_the_declared_artifact(tmp_path):
    out = tmp_path / "result.json"
    completed = _run("--out", str(out))

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "ok"

    alpha = np.asarray(json.loads(out.read_text(encoding="utf-8"))["alpha_m_inv"])
    assert alpha.shape == (2, 2, 2)
    np.testing.assert_allclose(alpha[:, :, 0], [[10.0, 10.0], [11.0, 11.0]])
    np.testing.assert_allclose(alpha[:, :, 1], [[11.0, 11.0], [11.0, 11.0]])


def test_reference_program_fails_closed_without_an_output_path(tmp_path):
    completed = _run()

    assert completed.returncode != 0
    assert not list(tmp_path.iterdir())
