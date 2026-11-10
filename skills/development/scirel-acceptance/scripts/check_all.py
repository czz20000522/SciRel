#!/usr/bin/env python3
"""Run the complete local acceptance: everything must pass for the tree to be green."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Step:
    """One acceptance step. Without uv, a step marked ``requires_uv`` is NOT_RUN and fails."""

    name: str
    command: list[str]
    requires_uv: bool = False


def steps(output: Path) -> list[Step]:
    python = [sys.executable, "-B"]
    wheels = output / "wheel"
    plan = [
        Step("tests", [*python, "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
        Step(
            "contracts and examples",
            [
                *python,
                "scripts/validate_asset_documents.py",
                "catalog/examples",
                "--check-runtime",
                "--execute-examples",
            ],
        ),
        Step(
            "contract sync",
            [*python, "skills/development/scirel-acceptance/scripts/check_contract_sync.py"],
        ),
        Step(
            "new hazard patterns",
            [
                *python,
                "skills/development/api-design-method/scripts/scan_hazards.py",
                "src/scirel",
                "--baseline",
                "skills/development/scirel-acceptance/hazard_baseline.json",
            ],
        ),
        Step(
            "documentation build",
            [*python, "scripts/scirel_docs.py", "build", "--output", str(output / "docs")],
        ),
    ]
    for report in sorted(ROOT.glob("examples/*/REPORT.md")):
        plan.append(Step(f"report {report.parent.name}", [*python, VALIDATE_REPORT, str(report)]))
    # uv is the only source of lint, format, lockfile and wheel checks. Marking the steps here, in
    # the one list that defines them, keeps the uv and no-uv branches from drifting apart: a new
    # uv-only step is a single entry with requires_uv=True.
    plan.extend(
        [
            Step(
                "lint",
                ["uv", "run", "--frozen", "ruff", "check", ".", "--output-format", "concise"],
                requires_uv=True,
            ),
            Step(
                "format",
                ["uv", "run", "--frozen", "ruff", "format", "--check", "."],
                requires_uv=True,
            ),
            Step("lockfile", ["uv", "lock", "--check"], requires_uv=True),
            Step(
                "wheel build",
                ["uv", "build", "--wheel", "--out-dir", str(wheels), "."],
                requires_uv=True,
            ),
            Step(
                "wheel exposure",
                [
                    *python,
                    "scripts/check_wheel_exposure.py",
                    "--source-root",
                    str(ROOT / "src"),
                    "--wheel",
                    str(wheels / WHEEL),
                ],
                requires_uv=True,
            ),
        ]
    )
    return plan


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
    not_run = []
    with tempfile.TemporaryDirectory(prefix="scirel-check-") as temporary:
        has_uv = shutil.which("uv") is not None
        for step in steps(Path(temporary)):
            if step.requires_uv and not has_uv:
                print(f"NOT_RUN  {step.name}  (uv is not on PATH)", flush=True)
                not_run.append(step.name)
                failed.append(step.name)
                continue
            started = time.perf_counter()
            completed = run_step(step.command)
            status = "PASS" if completed.returncode == 0 else "FAIL"
            print(f"{status}  {step.name}  ({time.perf_counter() - started:.0f} s)", flush=True)
            if completed.returncode:
                failed.append(step.name)
                print((completed.stdout + completed.stderr)[-4000:])
    for leftover in ("build", "src/scirel.egg-info"):
        shutil.rmtree(ROOT / leftover, ignore_errors=True)
    if not_run:
        print("A missing uv fails the run: lint, format, lockfile and wheel checks did not run.")
    print("ALL GREEN" if not failed else f"FAILED: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
