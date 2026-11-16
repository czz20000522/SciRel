#!/usr/bin/env python3
"""Run the local acceptance for one stage; everything in that stage must pass.

Two stages share one plan. The release stage is the plan this repository has always run and is
the only evidence for merging or for any outward delivery claim: every step, every test, zero
deselections. The development stage drops the steps that only a built artifact can fail
(documentation build, wheel build, wheel exposure, example execution) and deselects the
release-only tests listed in ``release_only_tests.txt``; it says nothing about packaging.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

from scirel_pytest_counts import validate_execution_records

ROOT = Path(__file__).resolve().parents[4]
VALIDATE_REPORT = "skills/development/usage/scirel-solving/scripts/validate_report.py"
WHEEL = "scirel-0.0.0-py3-none-any.whl"
COUNTS_PLUGIN = "scirel_pytest_counts"
# Kept in step with scripts/dev.py: the marker is exported only while that process
# holds the clone's exclusive lock, and the record names the retired credential.
EXCLUSIVE_MARKER = "SCIREL_EXCLUSIVE_TOKEN"
EXCLUSIVE_RECORD = "acceptance-exclusive"
RESULT_SCHEMA = "scirel.acceptance.v2"
LEGACY_RESULT_SCHEMA = "scirel.acceptance.v1"
SIDECAR_SUFFIX = ".sha256"

# The release stage is what merging and any outward delivery claim needs; the development stage
# is the same plan minus the steps and tests that only a packaged or published product can fail.
STAGES = ("release", "dev")
DEFAULT_STAGE = "release"
RELEASE_ONLY_TESTS = "skills/development/scirel-acceptance/release_only_tests.txt"
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
class ReleaseOnly:
    """One test entry the development stage deselects, with the reason it is release-only."""

    target: str
    why: str


def release_only_tests(path: Path | None = None) -> list[ReleaseOnly]:
    """Read the release-only manifest: one ``<path or nodeid> | <reason>`` line per entry.

    The manifest is the only definition of which tests the development stage may skip, so a
    malformed line, a non-``tests/`` target or a missing reason is an error rather than a
    silently shorter exclusion list.
    """
    manifest = path or ROOT / RELEASE_ONLY_TESTS
    entries = []
    for number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        target, separator, why = line.partition(" | ")
        target, why = target.strip(), why.strip()
        if not separator or not target.startswith("tests/") or not why:
            raise ValueError(
                f"{manifest.name}:{number}: expected '<tests/... | nodeid> | <reason>'"
            )
        entries.append(ReleaseOnly(target, why))
    if not entries:
        raise ValueError(f"{manifest.name}: the release-only list is empty")
    targets = [entry.target for entry in entries]
    if len(targets) != len(set(targets)):
        raise ValueError(f"{manifest.name}: a release-only test is listed twice")
    return entries


@dataclass(frozen=True)
class Step:
    """One acceptance step. Without uv, a step marked ``requires_uv`` is NOT_RUN and fails."""

    name: str
    command: list[str]
    requires_uv: bool = False
    counts: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    stages: tuple[str, ...] = STAGES
    # Release-only targets this step must have deselected, or nothing in the release stage.
    deselected: tuple[str, ...] = ()


def steps(
    output: Path,
    *,
    root: Path = ROOT,
    executable: str | None = None,
    stage: str = DEFAULT_STAGE,
) -> list[Step]:
    """The one step table, filtered by stage.

    A step that only the release stage runs carries ``stages=("release",)``. The steps both
    stages share keep one definition; only the arguments that differ are chosen by ``stage``,
    so the release plan stays the plan the repository already had.
    """
    if stage not in STAGES:
        raise ValueError(f"unknown acceptance stage: {stage}")
    python = [executable or sys.executable, "-B"]
    wheels = output / "wheel"
    counts = output / "tests-counts.json"
    # The release stage runs every test and refuses to have deselected any, so it never reads the
    # manifest: its plan stays the plan this repository already had. The development stage
    # deselects exactly the manifest and passes those targets down so the counts can prove it.
    if stage == "dev":
        try:
            deselected = tuple(
                entry.target for entry in release_only_tests(root / RELEASE_ONLY_TESTS)
            )
        except FileNotFoundError as error:
            raise ValueError(
                f"{RELEASE_ONLY_TESTS} is missing, so the development stage cannot say what it"
                " is allowed to skip"
            ) from error
    else:
        deselected = ()
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
                *(f"--deselect={target}" for target in deselected),
            ],
            counts=counts,
            env={
                "PYTHONPATH": os.pathsep.join(
                    filter(None, [plugin_dir, os.environ.get("PYTHONPATH")])
                )
            },
            deselected=deselected,
        ),
        Step(
            "contracts and examples" if stage == "release" else "contracts",
            [
                *python,
                "scripts/validate_asset_documents.py",
                "catalog/examples",
                "--check-runtime",
                # Executing the 249 documented examples is release evidence: it proves the
                # published examples run, not that this change is correct.
                *(["--execute-examples"] if stage == "release" else []),
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
            stages=("release",),
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
                stages=("release",),
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
                stages=("release",),
            ),
        ]
    )
    return [step for step in plan if stage in step.stages]


def read_counts(
    path: Path, *, require_execution: bool = True, release_only: tuple[str, ...] = ()
) -> dict:
    """Read the pytest counts report, refusing anything whose numbers do not add up.

    ``release_only`` is empty for the release stage, which must deselect nothing. The development
    stage passes the manifest targets it handed to pytest: every deselected nodeid must belong to
    one of them, and every target must have deselected something, so an exclusion cannot be
    widened silently nor survive a renamed test.
    """
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
        if not release_only:
            raise CountsError(
                f"{path.name}: {report['deselected']} tests were deselected; full acceptance"
                " requires the whole suite, so remove test filters and rerun"
            )
        deselected_nodes = report.get("deselected_nodeids")
        if (
            not isinstance(deselected_nodes, list)
            or any(not isinstance(node, str) or not node for node in deselected_nodes)
            or len(set(deselected_nodes)) != len(deselected_nodes)
            or len(deselected_nodes) != report["deselected"]
        ):
            raise CountsError(f"{path.name}: the deselected nodeids are missing or do not add up")
        outside = [
            node
            for node in deselected_nodes
            if not any(node.startswith(target) for target in release_only)
        ]
        if outside:
            raise CountsError(
                f"{path.name}: {len(outside)} tests were deselected outside the release-only list,"
                f" so the development stage skipped more than it may: {outside[:3]}"
            )
        stale = [
            target
            for target in release_only
            if not any(node.startswith(target) for node in deselected_nodes)
        ]
        if stale:
            raise CountsError(
                f"{path.name}: release-only entries deselected no test, so the list has drifted"
                f" away from the suite: {stale[:3]}"
            )
    accounted = sum(
        report[name] for name in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
    )
    if accounted != report["selected"]:
        raise CountsError(
            f"{path.name}: outcomes add up to {accounted} but {report['selected']} were selected"
        )
    try:
        validate_execution_records(report)
    except ValueError as error:
        raise CountsError(f"{path.name}: {error}") from error
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
        report = read_counts(step.counts, require_execution=False, release_only=step.deselected)
    except CountsError as error:
        return "FAIL", f"  (test counts unusable: {error})", None
    if report["pytest_exitstatus"] != returncode:
        return "FAIL", "  (pytest exit status disagrees with subprocess return code)", report
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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_provenance(
    result: dict,
    *,
    report_path: Path,
    check_all_path: Path,
    allow_legacy_receipts: bool = False,
    token: str | None = None,
) -> str:
    """Check what a result claims about the run that produced it, never its science.

    A v2 result binds the file to the run that wrote it: every retained step log has a
    recorded digest, and a sidecar holds the digest of the result file, so editing the
    result alone, or the log alone, is visible.

    The credential digest is a binding **only when the caller holds the live token**. Pass
    ``token`` (the verified credential of this very run, as ``run_full_check`` does) and the
    recorded digest must equal its sha256; a mismatch is refused. With ``token=None`` this
    function cannot check that link and only validates the shape — a format-valid digest
    from an unrelated run passes. Shape validation is not binding.

    **This is still not a signature.** Whoever can rewrite the result, every log and the
    sidecar together can fabricate a self-consistent bundle; what they cannot do is make the
    recorded digest match a live token held by the verifier. What the checks stop is a hand
    edit of one file, and — with a live token — a bundle from another run.

    A digest over the scripts means any change to ``check_all.py`` or
    ``scirel_pytest_counts.py`` makes every earlier v2 receipt disagree; an edited script
    needs a new run, not a repaired receipt.

    This function does not compare step count or step names against a plan: the caller
    that knows the plan owns that comparison.

    ``steps[].seconds`` is a wall-clock observation, recorded so the maintainer can see
    where a long run goes before deciding to split or parallelize a step. It is not
    compared here on purpose: duration is not a verdict, and a slow machine must not turn
    a green run red.

    A ``scirel.acceptance.v1`` receipt predates all of this and is refused by default,
    because a fresh forgery and a genuine historical receipt are indistinguishable. Pass
    ``allow_legacy_receipts=True`` to read one for archaeology, never as evidence.
    """
    schema = result.get("schema")
    if schema == LEGACY_RESULT_SCHEMA:
        if not allow_legacy_receipts:
            raise ValueError(
                "a v1 receipt cannot serve as new evidence; historical receipts are for"
                " archaeology only (pass --allow-legacy-receipts to read one)"
            )
        return "legacy_unprovenanced"
    if schema != RESULT_SCHEMA:
        raise ValueError(f"unknown result schema: {schema!r}")
    exclusive = result.get("exclusive")
    token_digest = exclusive.get("token_sha256") if isinstance(exclusive, dict) else None
    if (
        not isinstance(exclusive, dict)
        or exclusive.get("present") is not True
        or not isinstance(token_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", token_digest) is None
    ):
        raise ValueError("result claims no exclusive lock credential for the run")
    if token is not None:
        expected = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
        if token_digest != expected:
            raise ValueError(
                "recorded credential digest does not match this run's live token:"
                " the result was not produced by the lock holder now verifying it"
            )
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("result lacks the producer script digests")
    try:
        expected_check_all = _digest(Path(check_all_path))
        expected_plugin = _digest(Path(check_all_path).with_name(f"{COUNTS_PLUGIN}.py"))
    except OSError as error:
        raise ValueError(f"cannot read the acceptance scripts: {error}") from error
    if provenance.get("check_all_sha256") != expected_check_all:
        raise ValueError("check_all_sha256 disagrees with the script on disk")
    if provenance.get("counts_plugin_sha256") != expected_plugin:
        raise ValueError("counts_plugin_sha256 disagrees with the script on disk")
    records = result.get("steps")
    if not isinstance(records, list):
        raise ValueError("result lacks the step records")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("result has a malformed step record")
        name = record.get("name", "?")
        log, recorded = record.get("log"), record.get("log_sha256")
        if not isinstance(log, str) or not isinstance(recorded, str):
            raise ValueError(f"{name}: step log digest is missing")
        try:
            actual = _digest(Path(log))
        except OSError as error:
            raise ValueError(f"{name}: step log is missing: {error}") from error
        if actual != recorded:
            raise ValueError(f"{name}: log_sha256 disagrees with the retained log")
    report_path = Path(report_path)
    sidecar = report_path.with_name(report_path.name + SIDECAR_SUFFIX)
    try:
        recorded_sidecar = sidecar.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ValueError(f"result has no sidecar digest: {error}") from error
    if recorded_sidecar != _digest(report_path):
        raise ValueError("sidecar digest disagrees with the result file")
    return "verified_v2"


def main(
    report_path: Path | None = None, *, run_id: str | None = None, stage: str = DEFAULT_STAGE
) -> int:
    if stage not in STAGES:
        print(f"unknown acceptance stage: {stage}; choose one of {STAGES}", file=sys.stderr)
        return 2
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
    # Only the credential digest is recorded: the token itself retires before the lock
    # is released and must never be copied into an artifact that outlives the run.
    marker = os.environ.get(EXCLUSIVE_MARKER, "")
    exclusive = {
        "token_sha256": hashlib.sha256(marker.encode("utf-8")).hexdigest() if marker else "",
        "record": str(ROOT / ".runtime" / "locks" / EXCLUSIVE_RECORD),
        "present": bool(marker),
    }
    if not marker:
        print(f"NOTE  no {EXCLUSIVE_MARKER}: this result is not acceptable evidence")
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
    rejected_counts = None
    plan = []
    records = []
    interrupted = False
    with tempfile.TemporaryDirectory(prefix="scirel-check-", dir=temporary_root) as temporary:
        has_uv = shutil.which("uv") is not None
        try:
            plan = steps(Path(temporary), root=ROOT, stage=stage)
        except (OSError, ValueError) as error:
            # A plan that cannot be built is a pre-flight failure: leave no reserved result that
            # a later reader could mistake for a run.
            result_stream.close()
            report_path.unlink(missing_ok=True)
            lock.close()
            print(f"ERROR: cannot build the {stage} acceptance plan: {error}", file=sys.stderr)
            return 2
        print(
            f"STAGE  {stage}  ({len(plan)} steps; release-only tests"
            f" {'deselected' if stage == 'dev' else 'all run'})",
            flush=True,
        )
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
            elapsed = time.perf_counter() - started
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
                    "log_sha256": _digest(log_path),
                    # Wall-clock observation, not a verdict: it tells the maintainer where
                    # a long run goes, so splitting or parallelizing can be decided on data.
                    "seconds": round(elapsed, 1),
                }
            )
            if report is not None:
                counts_report = report
            elif step.counts is not None:
                # Preserve readable observations from failed collection/interruption or a broken
                # record without ever using those unvalidated fields for a summary or verdict.
                try:
                    rejected_counts = json.loads(step.counts.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass
            print(
                f"{status}  {step.name}  ({elapsed:.0f} s){detail}",
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
        "schema": RESULT_SCHEMA,
        "stage": stage,
        "run_id": run_id,
        "exclusive": exclusive,
        "provenance": {
            "check_all_sha256": _digest(Path(__file__)),
            "counts_plugin_sha256": _digest(Path(__file__).with_name(f"{COUNTS_PLUGIN}.py")),
        },
        "candidate": {"before": before, "after": after},
        "environment": {"before": environment_before, "after": environment_after},
        "binding_errors": binding_errors,
        "evidence": evidence,
        "steps": records,
        "tests": counts_report if counts_report is not None else rejected_counts,
        "exit_code": 1 if invalid else 0,
    }
    with result_stream:
        json.dump(result, result_stream, ensure_ascii=False, indent=2)
        result_stream.write("\n")
    # The digest cannot live inside the file it describes; the sidecar names it.
    result_digest = _digest(report_path)
    report_path.with_name(report_path.name + SIDECAR_SUFFIX).write_text(
        result_digest + "\n", encoding="utf-8"
    )
    print(f"RESULT SHA256 {result_digest}")
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
    parser.add_argument(
        "--stage",
        choices=STAGES,
        default=DEFAULT_STAGE,
        help=(
            "release runs every step and every test and is the only admission evidence;"
            " dev skips the artifact steps and the release-only tests listed in the manifest"
        ),
    )
    args = parser.parse_args()
    raise SystemExit(main(args.report, run_id=args.run_id, stage=args.stage))
