#!/usr/bin/env python3
"""Run the complete local acceptance: everything must pass for the tree to be green."""

from __future__ import annotations

from dataclasses import dataclass, field
import fcntl
import hashlib
import json
import os
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
COUNTS_PLUGIN = "scirel_pytest_counts"
COUNT_FIELDS = (
    "collected",
    "selected",
    "deselected",
    "passed",
    "failed",
    "error",
    "skipped",
    "xfailed",
    "xpassed",
)


class CountsError(Exception):
    """The pytest counts report cannot be trusted, so the tests step cannot be green."""


@dataclass(frozen=True)
class Step:
    """One acceptance step. Without uv, a step marked ``requires_uv`` is NOT_RUN and fails."""

    name: str
    command: list[str]
    requires_uv: bool = False
    counts: Path | None = None
    env: dict[str, str] = field(default_factory=dict)


def steps(output: Path) -> list[Step]:
    python = [sys.executable, "-B"]
    wheels = output / "wheel"
    counts = output / "tests-counts.json"
    # The plugin is loaded by name with ``-p`` from this directory only, never discovered, so a
    # third-party environment cannot inject a module that happens to share the name.
    plugin_dir = str(Path(__file__).resolve().parent)
    plan = [
        Step(
            "tests",
            [
                *python,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-p",
                COUNTS_PLUGIN,
                f"--scirel-counts={counts}",
            ],
            counts=counts,
            env={
                "PYTHONPATH": os.pathsep.join(
                    filter(None, [plugin_dir, os.environ.get("PYTHONPATH")])
                )
            },
        ),
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


def read_counts(path: Path) -> dict:
    """Read the pytest counts report, refusing anything whose numbers do not add up."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CountsError(f"{path.name} was not written") from error
    except (OSError, ValueError) as error:
        raise CountsError(f"{path.name} is not readable JSON: {error}") from error
    if not isinstance(report, dict):
        raise CountsError(f"{path.name} is not a JSON object")
    wrong = [name for name in COUNT_FIELDS if not isinstance(report.get(name), int)]
    if wrong:
        raise CountsError(f"{path.name} lacks integer counts: {wrong}")
    if report.get("consistent") is not True:
        raise CountsError(
            f"{path.name} reports inconsistency: {report.get('inconsistency') or 'no reason given'}"
        )
    if report["collected"] != report["selected"] + report["deselected"]:
        raise CountsError(
            f"{path.name}: collected {report['collected']} != selected {report['selected']}"
            f" + deselected {report['deselected']}"
        )
    accounted = sum(
        report[name] for name in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
    )
    if accounted != report["selected"]:
        raise CountsError(
            f"{path.name}: outcomes add up to {accounted} but {report['selected']} were selected"
        )
    return report


def step_status(step: Step, returncode: int) -> tuple[str, str, dict | None]:
    """Judge one finished step: a green pytest run also needs counts that add up."""
    if returncode != 0:
        return "FAIL", "", None
    if step.counts is None:
        return "PASS", "", None
    try:
        report = read_counts(step.counts)
    except CountsError as error:
        return "FAIL", f"  (test counts unusable: {error})", None
    return "PASS", "", report


def counts_summary(steps_passed: int, steps_total: int, report: dict) -> str:
    reasons = "; ".join(
        f"{reason} ({len(nodeids)})"
        for reason, nodeids in sorted(
            report["skip_reasons"].items(), key=lambda item: (-len(item[1]), item[0])
        )
    )
    return (
        f"steps {steps_passed}/{steps_total} passed; tests collected {report['collected']},"
        f" selected {report['selected']}, deselected {report['deselected']},"
        f" passed {report['passed']}, failed {report['failed']}, error {report['error']},"
        f" skipped {report['skipped']}, xfailed {report['xfailed']},"
        f" xpassed {report['xpassed']} (skip reasons: {reasons or 'none'})"
    )


def skip_lines(report: dict) -> list[str]:
    """One line per skip reason with its count and the first few test IDs."""
    lines = []
    for reason, nodeids in sorted(
        report["skip_reasons"].items(), key=lambda item: (-len(item[1]), item[0])
    ):
        shown = ", ".join(nodeids[:3])
        more = "" if len(nodeids) <= 3 else f", and {len(nodeids) - 3} more"
        lines.append(f"SKIP  {reason}  ({len(nodeids)}): {shown}{more}")
    return lines


def run_step(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run one step, and stop it too if this script is stopped, so that no orphan keeps running."""
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, **env},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
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
    counts_report = None
    plan = []
    with tempfile.TemporaryDirectory(prefix="scirel-check-") as temporary:
        has_uv = shutil.which("uv") is not None
        plan = steps(Path(temporary))
        for step in plan:
            if step.requires_uv and not has_uv:
                print(f"NOT_RUN  {step.name}  (uv is not on PATH)", flush=True)
                not_run.append(step.name)
                failed.append(step.name)
                continue
            started = time.perf_counter()
            completed = run_step(step.command, step.env)
            status, detail, report = step_status(step, completed.returncode)
            if report is not None:
                counts_report = report
            print(
                f"{status}  {step.name}  ({time.perf_counter() - started:.0f} s){detail}",
                flush=True,
            )
            if status == "FAIL":
                failed.append(step.name)
                if completed.returncode:
                    print((completed.stdout + completed.stderr)[-4000:])
    for leftover in ("build", "src/scirel.egg-info"):
        shutil.rmtree(ROOT / leftover, ignore_errors=True)
    if not_run:
        print("A missing uv fails the run: lint, format, lockfile and wheel checks did not run.")
    if counts_report is not None:
        for line in skip_lines(counts_report):
            print(line)
        print(counts_summary(len(plan) - len(failed), len(plan), counts_report))
    print("ALL GREEN" if not failed else f"FAILED: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
