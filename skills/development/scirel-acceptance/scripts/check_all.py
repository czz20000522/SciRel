#!/usr/bin/env python3
"""Run the complete local acceptance: everything must pass for the tree to be green."""

from __future__ import annotations

import fcntl
import hashlib
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
VALIDATE_REPORT = "skills/development/usage/scirel-solving/scripts/validate_report.py"
WHEEL = "scirel-0.0.0-py3-none-any.whl"


NOT_RUN_WITHOUT_UV = ("lint", "format", "lockfile", "wheel build", "wheel exposure")


def steps(output: Path) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """Return the steps to run and the steps uv is required for but cannot run."""
    python = [sys.executable, "-B"]
    plan = [
        ("tests", [*python, "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
        (
            "contracts and examples",
            [
                *python,
                "scripts/validate_asset_documents.py",
                "catalog/examples",
                "--check-runtime",
                "--execute-examples",
            ],
        ),
        (
            "contract sync",
            [*python, "skills/development/scirel-acceptance/scripts/check_contract_sync.py"],
        ),
        (
            "new hazard patterns",
            [
                *python,
                "skills/development/api-design-method/scripts/scan_hazards.py",
                "src/scirel",
                "--baseline",
                "skills/development/scirel-acceptance/hazard_baseline.json",
            ],
        ),
        (
            "documentation build",
            [*python, "scripts/scirel_docs.py", "build", "--output", str(output / "docs")],
        ),
    ]
    for report in sorted(ROOT.glob("examples/*/REPORT.md")):
        plan.append((f"report {report.parent.name}", [*python, VALIDATE_REPORT, str(report)]))
    if not shutil.which("uv"):
        # uv is the only source of lint, format, lockfile and wheel checks. A missing uv must fail
        # the run: a silently skipped lint is not a green tree.
        return plan, list(NOT_RUN_WITHOUT_UV)
    plan.append(
        ("lint", ["uv", "run", "--frozen", "ruff", "check", ".", "--output-format", "concise"])
    )
    plan.append(("format", ["uv", "run", "--frozen", "ruff", "format", "--check", "."]))
    plan.append(("lockfile", ["uv", "lock", "--check"]))
    wheels = output / "wheel"
    plan.append(("wheel build", ["uv", "build", "--wheel", "--out-dir", str(wheels), "."]))
    plan.append(
        (
            "wheel exposure",
            [
                *python,
                "scripts/check_wheel_exposure.py",
                "--source-root",
                str(ROOT / "src"),
                "--wheel",
                str(wheels / WHEEL),
            ],
        )
    )
    return plan, []


def run_step(command: list[str]) -> subprocess.CompletedProcess:
    """Run one step, and stop it too if this script is stopped, so that no orphan keeps running."""
    process = subprocess.Popen(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    def stop(signum, _frame):
        process.terminate()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    stdout, stderr = process.communicate()
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def main() -> int:
    # Two runs at once slow each other and share build directories, so allow one per checkout.
    lock = open(
        Path(tempfile.gettempdir())
        / f"scirel-check-{hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]}.lock",
        "w",
    )
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another check_all is running on this checkout; wait for it or stop it")
        return 2
    failed = []
    with tempfile.TemporaryDirectory(prefix="scirel-check-") as temporary:
        plan, not_run = steps(Path(temporary))
        for name in not_run:
            print(f"NOT_RUN  {name}  (uv is not on PATH)", flush=True)
            failed.append(name)
        for name, command in plan:
            started = time.perf_counter()
            completed = run_step(command)
            status = "PASS" if completed.returncode == 0 else "FAIL"
            print(f"{status}  {name}  ({time.perf_counter() - started:.0f} s)", flush=True)
            if completed.returncode:
                failed.append(name)
                print((completed.stdout + completed.stderr)[-4000:])
    for leftover in ("build", "src/scirel.egg-info"):
        shutil.rmtree(ROOT / leftover, ignore_errors=True)
    if not_run:
        print("A missing uv fails the run: lint, format, lockfile and wheel checks did not run.")
    print("ALL GREEN" if not failed else f"FAILED: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
