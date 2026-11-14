#!/usr/bin/env python3
"""Run the complete local acceptance: everything must pass for the tree to be green."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

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


class BindingError(Exception):
    """The candidate or runtime cannot be identified without guessing."""


class StepStartError(Exception):
    """The subprocess was never started."""


class StepInterrupted(Exception):
    """A started subprocess was interrupted; retain its output and stop the plan."""

    def __init__(self, completed: subprocess.CompletedProcess):
        self.completed = completed


def candidate_identity(root: Path) -> dict:
    """Identify HEAD and local edits without recording filenames or file contents."""

    def git(*arguments: str) -> bytes:
        try:
            done = subprocess.run(["git", *arguments], cwd=root, capture_output=True, check=False)
        except OSError as error:
            raise BindingError("git identity command could not start") from error
        if done.returncode:
            raise BindingError("git identity command failed")
        return done.stdout

    if Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip()).resolve() != root.resolve():
        raise BindingError("candidate is not the root of a Git checkout")
    commit = git("rev-parse", "HEAD").decode("ascii").strip()
    tree = git("rev-parse", "HEAD^{tree}").decode("ascii").strip()
    status = git(
        "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"
    )
    digest = hashlib.sha256(status)
    for mode in ([], ["--cached"]):
        digest.update(
            git(
                "diff",
                *mode,
                "--binary",
                "--no-ext-diff",
                "--no-textconv",
                "--ignore-submodules=none",
                "HEAD",
                "--",
            )
        )
    for name in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if not name:
            continue
        path = root / os.fsdecode(name)
        try:
            if path.is_symlink():
                content_hash = hashlib.sha256(os.fsencode(os.readlink(path))).digest()
            else:
                with path.open("rb") as stream:
                    content_hash = hashlib.file_digest(stream, "sha256").digest()
        except OSError as error:
            raise BindingError("cannot hash an untracked candidate file") from error
        digest.update(name + b"\0" + content_hash)
    return {
        "commit": commit,
        "tree": tree,
        "dirty": bool(status),
        "worktree_sha256": digest.hexdigest(),
    }


def dependency_digests(root: Path) -> dict:
    """Hash the candidate's dependency inputs without assuming the caller's interpreter."""
    digests = {}
    for name, field_name in (
        ("uv.lock", "uv_lock_sha256"),
        (".python-version", "python_version_sha256"),
    ):
        try:
            digests[field_name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except OSError as error:
            raise BindingError(f"cannot hash {name}") from error
    return digests


def runtime_environment(root: Path) -> dict:
    """Record only the interpreter, platform, architecture and two dependency inputs."""
    environment = {
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "platform": sys.platform,
        "architecture": platform.machine(),
        **dependency_digests(root),
    }
    if not all(
        (environment["platform"], environment["architecture"], *environment["python"].values())
    ):
        raise BindingError("interpreter, platform or architecture identity is unavailable")
    return environment


@dataclass(frozen=True)
class Step:
    """One acceptance step. Without uv, a step marked ``requires_uv`` is NOT_RUN and fails."""

    name: str
    command: list[str]
    requires_uv: bool = False
    counts: Path | None = None
    env: dict[str, str] = field(default_factory=dict)


def steps(output: Path, *, root: Path = ROOT, executable: str | None = None) -> list[Step]:
    python = [executable or sys.executable, "-B"]
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
                "tests",
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
    for report in sorted(root.glob("examples/*/REPORT.md")):
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
                    str(root / "src"),
                    "--wheel",
                    str(wheels / WHEEL),
                ],
                requires_uv=True,
            ),
        ]
    )
    return plan


def read_counts(path: Path, *, require_execution: bool = True) -> dict:
    """Read the pytest counts report, refusing anything whose numbers do not add up."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CountsError(f"{path.name} was not written") from error
    except (OSError, ValueError) as error:
        raise CountsError(f"{path.name} is not readable JSON: {error}") from error
    if not isinstance(report, dict):
        raise CountsError(f"{path.name} is not a JSON object")
    wrong = [name for name in COUNT_FIELDS if type(report.get(name)) is not int or report[name] < 0]
    if wrong:
        raise CountsError(f"{path.name} lacks integer counts: {wrong}")
    if not isinstance(report.get("skip_reasons"), dict) or any(
        not isinstance(reason, str) or not isinstance(nodes, list)
        for reason, nodes in report["skip_reasons"].items()
    ):
        raise CountsError(f"{path.name} lacks skip reasons")
    if report.get("consistent") is not True:
        raise CountsError(
            f"{path.name} reports inconsistency: {report.get('inconsistency') or 'no reason given'}"
        )
    if require_execution and report["selected"] <= 0:
        raise CountsError(f"{path.name}: no tests executed; rerun the required suite")
    if report["collected"] != report["selected"] + report["deselected"]:
        raise CountsError(
            f"{path.name}: collected {report['collected']} != selected {report['selected']}"
            f" + deselected {report['deselected']}"
        )
    if report["deselected"]:
        raise CountsError(
            f"{path.name}: {report['deselected']} tests were deselected; full acceptance requires"
            " the whole suite, so remove test filters and rerun"
        )
    accounted = sum(
        report[name] for name in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
    )
    if accounted != report["selected"]:
        raise CountsError(
            f"{path.name}: outcomes add up to {accounted} but {report['selected']} were selected"
        )
    if require_execution and not sum(report[name] for name in ("passed", "failed", "xpassed")):
        raise CountsError(
            f"{path.name}: no tests executed with a passed, failed or xpassed outcome"
        )
    return report


def step_status(step: Step, returncode: int) -> tuple[str, str, dict | None]:
    """Judge one finished step: a green pytest run also needs counts that add up."""
    if step.counts is None:
        return ("FAIL" if returncode else "PASS"), "", None
    try:
        report = read_counts(step.counts, require_execution=False)
    except CountsError as error:
        return "FAIL", f"  (test counts unusable: {error})", None
    if not sum(report[name] for name in ("passed", "failed", "xpassed")):
        return "FAIL", "  (no tests executed with a passed, failed or xpassed outcome)", report
    return ("FAIL" if returncode or report["failed"] or report["error"] else "PASS"), "", report


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
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env={**os.environ, **env},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as error:
        raise StepStartError("subprocess could not start") from error

    def stop(signum, _frame):
        process.terminate()
        raise SystemExit(128 + signum)

    signals = [signal.SIGTERM] + ([signal.SIGHUP] if hasattr(signal, "SIGHUP") else [])
    handlers = {signum: signal.getsignal(signum) for signum in signals}
    for signum in signals:
        signal.signal(signum, stop)
    try:
        stdout, stderr = process.communicate()
    except (KeyboardInterrupt, SystemExit, OSError) as error:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        code = (
            error.code
            if isinstance(error, SystemExit) and isinstance(error.code, int)
            else (1 if isinstance(error, OSError) else 130)
        )
        raise StepInterrupted(subprocess.CompletedProcess(command, code, stdout, stderr)) from error
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def main(report_path: Path | None = None, *, run_id: str | None = None) -> int:
    # Two runs at once slow each other and share build directories, so allow one per checkout.
    temporary_root = ROOT / ".runtime" / "tmp"
    temporary_root.mkdir(parents=True, exist_ok=True)
    logs_root = ROOT / ".runtime" / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    if report_path is None:
        report_path = Path(tempfile.mkdtemp(prefix="check-", dir=logs_root)) / "result.json"
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ROOT / ".runtime" / "locks" / "check-all.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path.open("a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            lock.write(b"0")
            lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        print("another check_all is running on this checkout; wait for it or stop it")
        return 2
    # Reserve a fresh result before starting anything: an interrupted run cannot leave an old green.
    try:
        result_stream = report_path.open("x", encoding="utf-8")
    except OSError:
        lock.close()
        print("result must be a new writable file; refusing to reuse an earlier result")
        return 2
    run_id = run_id or uuid.uuid4().hex
    binding_errors = []

    def snapshot():
        candidate, environment = None, None
        try:
            candidate = candidate_identity(ROOT)
        except BindingError as error:
            binding_errors.append(str(error))
        try:
            environment = runtime_environment(ROOT)
        except BindingError as error:
            binding_errors.append(str(error))
        return candidate, environment

    before, environment_before = snapshot()
    failed = []
    not_run = []
    counts_report = None
    plan = []
    records = []
    interrupted = False
    with tempfile.TemporaryDirectory(prefix="scirel-check-", dir=temporary_root) as temporary:
        has_uv = shutil.which("uv") is not None
        plan = steps(Path(temporary), root=ROOT)
        for step in plan:
            record = {"name": step.name, "argv": list(step.command), "started": False}
            if interrupted or (step.requires_uv and not has_uv):
                detail = "previous step interrupted" if interrupted else "uv is not on PATH"
                print(f"NOT_RUN  {step.name}  ({detail})", flush=True)
                not_run.append(step.name)
                failed.append(step.name)
                records.append(
                    {
                        **record,
                        "status": "NOT_RUN",
                        "returncode": None,
                        "detail": detail,
                    }
                )
                continue
            started = time.perf_counter()
            try:
                completed = run_step(step.command, step.env)
            except StepStartError:
                detail = "subprocess could not start"
                records.append(
                    {**record, "status": "NOT_RUN", "returncode": None, "detail": detail}
                )
                not_run.append(step.name)
                failed.append(step.name)
                print(f"NOT_RUN  {step.name}  ({detail})", flush=True)
                continue
            except StepInterrupted as error:
                completed = error.completed
                interrupted = True
            record["started"] = True
            status, detail, report = step_status(step, completed.returncode)
            if interrupted:
                status, detail = "FAIL", "interrupted"
            log_path = report_path.parent / f"{report_path.stem}-step-{len(records):02d}.log"
            log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
            records.append(
                {
                    **record,
                    "status": status,
                    "returncode": completed.returncode,
                    "detail": detail,
                    "log": str(log_path),
                }
            )
            if report is not None:
                counts_report = report
            print(
                f"{status}  {step.name}  ({time.perf_counter() - started:.0f} s){detail}",
                flush=True,
            )
            if status == "FAIL":
                failed.append(step.name)
                if completed.returncode:
                    print(f"Full output: {log_path}; excerpt follows:")
                    print((completed.stdout + completed.stderr)[-4000:])
    for leftover in ("build", "src/scirel.egg-info"):
        shutil.rmtree(ROOT / leftover, ignore_errors=True)
    after, environment_after = snapshot()
    if before != after:
        binding_errors.append("candidate identity changed during the check")
    if environment_before != environment_after:
        binding_errors.append("runtime environment changed during the check")
    if not plan:
        binding_errors.append("no acceptance steps executed")
    if counts_report is None:
        binding_errors.append("no usable test counts")
    if not_run:
        print("Unstarted steps fail the run; read each NOT_RUN reason.")
    if counts_report is not None:
        for line in skip_lines(counts_report):
            print(line)
        print(counts_summary(len(plan) - len(failed), len(plan), counts_report))
    for error in binding_errors:
        print(f"BINDING FAIL  {error}")
    invalid = bool(failed or binding_errors)
    evidence = "invalid" if invalid else ("development" if before["dirty"] else "clean_candidate")
    result = {
        "schema": "scirel.acceptance.v1",
        "run_id": run_id,
        "candidate": {"before": before, "after": after},
        "environment": {"before": environment_before, "after": environment_after},
        "binding_errors": binding_errors,
        "evidence": evidence,
        "steps": records,
        "tests": counts_report,
        "exit_code": 1 if invalid else 0,
    }
    with result_stream:
        json.dump(result, result_stream, ensure_ascii=False, indent=2)
        result_stream.write("\n")
    print(f"RESULT  {report_path}")
    if invalid:
        print(f"FAILED: {failed}" + (f"; binding: {binding_errors}" if binding_errors else ""))
    else:
        print("DEVELOPMENT PASS (dirty candidate)" if before["dirty"] else "ALL GREEN")
    lock.close()
    return result["exit_code"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="write the structured result here")
    parser.add_argument("--run-id", help="bind the result to this caller's fresh invocation")
    args = parser.parse_args()
    raise SystemExit(main(args.report, run_id=args.run_id))
