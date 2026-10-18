"""Negative guards for FluidBW native files outside the current Python closure."""

from __future__ import annotations

import platform
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest


ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "src/scirel/kinetic/_fluidbw_native"
OCTAVE = shutil.which("octave")

pytestmark = pytest.mark.skipif(
    platform.system() != "Linux"
    or platform.machine() not in {"x86_64", "amd64"}
    or OCTAVE is None,
    reason="FluidBW negative native guards require Linux amd64 and GNU Octave",
)


def test_current_fluidbw_python_methods_do_not_call_retained_candidate_files(tmp_path: Path) -> None:
    guard = tmp_path / "guard"
    guard.mkdir()
    for name in ("fD", "fDtensor", "fb_dispersion", "fb_dispersion_observe"):
        (guard / f"{name}.m").write_text(
            textwrap.dedent(
                f"""
                function varargout={name}(varargin)
                  error('scirel:negativeCandidate', 'unexpected candidate {name} invocation');
                end
                """
            ).lstrip(),
            encoding="utf-8",
        )

    harness = tmp_path / "negative_guard.m"
    native = str(NATIVE).replace("'", "''")
    guarded = str(guard).replace("'", "''")
    harness.write_text(
        textwrap.dedent(
            f"""
            more off;
            addpath('{native}');
            addpath('{guarded}');
            state = struct('S', 1, 'c2', (2.99792458e8)^2, ...
                'wcs', 1, 'wps2', 1, 'rhocs', 1, 'w', 1, ...
                'kz', 0.1, 'vts', sqrt(2));
            fb_evaluate(0.1, state, 'fD');
            fb_evaluate(0.1, state, 'fDtensor');
            disp('SCIREL_NEGATIVE_CANDIDATE_GUARD_PASS');
            """
        ).lstrip(),
        encoding="utf-8",
    )
    result = subprocess.run(
        [OCTAVE, "--no-gui", "--quiet", "--no-init-file", "--no-site-file", str(harness)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SCIREL_NEGATIVE_CANDIDATE_GUARD_PASS" in result.stdout
