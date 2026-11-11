#!/usr/bin/env python3
"""Check that an asset's own tests catch common output errors.

For each asset ID, the callable named in its contract is replaced, one at a time, by five output
mutants: every numeric output multiplied by 10 (a unit error), negated (a sign error), set to zero,
with its last two axes swapped (or a 1-D array reversed), and replaced by the first returned value
(a hard-coded sample). The tests listed in the contract's ``verification.tests`` must fail for every
mutant.

States per mutant:

- ``killed``: a test observed an actual output change and failed during its call phase.
- ``survived``: the tests passed although the output was changed.
- ``not_exercised``: the tests passed and the mutation never changed a returned value, so the
  tests do not call the function with numeric output through its public name.
- ``inapplicable``: ``swap`` on an output that has no array with more than one element, when the
  other kinds were exercised. Every other kind is always applicable to numeric output; in
  particular ``constant`` needs the tests to call the function at least twice, which the test
  matrix (normal, lower and upper bound) already requires.
- ``error``: pytest could not run (collection or usage error).

``survived``, ``not_exercised``, ``error`` and a failing baseline make the check fail.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from scirel_mutation_plugin import KINDS  # noqa: E402

FAILING_STATES = {"survived", "not_exercised", "error", "baseline_failed"}


def _pytest(root: Path, tests: list[str], spec: dict, output: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(SCRIPTS), env.get("PYTHONPATH", "")]
    )
    env.pop("PYTEST_ADDOPTS", None)
    counts_path = output.with_suffix(".json")
    env.update(
        SCIREL_MUTATION=json.dumps(spec),
        SCIREL_MUTATION_LOG=str(output.with_suffix(".mutations")),
        SCIREL_MUTATION_REPORT=str(counts_path),
    )
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-x",
        "-p",
        "no:cacheprovider",
        "-p",
        "scirel_mutation_plugin",
        *tests,
    ]
    done = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    output.write_text(done.stdout + done.stderr, encoding="utf-8")
    counts = None
    try:
        counts = json.loads(counts_path.read_text(encoding="utf-8"))
        if (
            counts.get("schema") != 1
            or counts.get("exit_code") != done.returncode
            or not isinstance(counts.get("selected"), int)
            or not isinstance(counts.get("executed"), int)
            or not isinstance(counts.get("deselected"), int)
            or not all(
                isinstance(counts.get(key), list)
                for key in ("applied", "applicable", "call_failed", "errors")
            )
            or counts["executed"] > counts["selected"]
        ):
            counts = None
    except (OSError, ValueError, AttributeError):
        counts = None
    return {"exit_code": done.returncode, "counts": counts, "log": str(output)}


def check_asset(root: Path, asset_id: str, *, log_dir: Path | None = None) -> dict:
    path = root / "catalog" / "examples" / f"{asset_id}.json"
    report = {"asset_id": asset_id, "mutants": {}}
    if not path.is_file():
        report["state"] = "error"
        report["detail"] = f"no contract at {path.relative_to(root)}"
        return report
    contract = json.loads(path.read_text(encoding="utf-8"))
    api = contract["public_api"]["python"]
    tests = list(contract["verification"]["tests"])
    report["tests"] = tests
    missing = [t for t in tests if not (root / t).is_file()]
    if not tests or missing:
        report["state"] = "error"
        report["detail"] = f"verification.tests missing or not found: {missing or 'empty'}"
        return report
    spec = {
        "module": api["module"],
        "symbol": api["symbol"],
        "canonical_module": api.get("canonical_module", api["module"]),
        "canonical_symbol": api.get("canonical_symbol", api["symbol"]),
    }
    logs_root = log_dir if log_dir is not None else root / ".runtime" / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    logs = Path(tempfile.mkdtemp(prefix="mutation-", dir=logs_root))
    report["log_dir"] = str(logs)
    report["runs"] = {}
    # The control has the same wrapping as a mutant but returns original outputs.
    # Signature/introspection failures caused by wrapping are not numerical evidence.
    baseline = _pytest(root, tests, {**spec, "kind": "baseline"}, logs / "baseline.log")
    report["runs"]["baseline"] = baseline
    counts = baseline["counts"]
    if (
        baseline["exit_code"] != 0
        or counts is None
        or counts["selected"] <= 0
        or counts["executed"] != counts["selected"]
        or counts["deselected"]
        or counts["errors"]
    ):
        report["state"] = "baseline_failed"
        report["detail"] = (
            f"original-output control failed (exit {baseline['exit_code']}); read {baseline['log']}"
        )
        return report
    for kind in KINDS:
        observed = _pytest(root, tests, {**spec, "kind": kind}, logs / f"{kind}.log")
        report["runs"][kind] = observed
        code, counts = observed["exit_code"], observed["counts"]
        if (
            counts is None
            or counts["selected"] <= 0
            or counts["executed"] <= 0
            or counts["deselected"]
            or counts["errors"]
        ):
            state = "error"
        elif code == 1 and set(counts["applied"]) & set(counts["call_failed"]):
            state = "killed"
        elif not counts["applied"] and code in (0, 1):
            state = "not_exercised"
        elif code == 0 and counts["executed"] == counts["selected"]:
            state = "survived"
        else:
            state = "error"
        report["mutants"][kind] = state
    exercised = [k for k, s in report["mutants"].items() if s in ("killed", "survived")]
    if exercised:
        for kind, state in report["mutants"].items():
            if (
                state == "not_exercised"
                and kind == "swap"
                and not report["runs"][kind]["counts"]["applicable"]
            ):
                report["mutants"][kind] = "inapplicable"
    states = set(report["mutants"].values())
    report["state"] = "failed" if states & FAILING_STATES else "passed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("asset_ids", nargs="+")
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="SciReL tree to test (default: this one)"
    )
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    parser.add_argument("--log-dir", type=Path, help="keep raw output and execution reports here")
    args = parser.parse_args()
    root = args.root.resolve()
    reports = [check_asset(root, asset_id, log_dir=args.log_dir) for asset_id in args.asset_ids]
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    counts: dict[str, int] = {}
    for report in reports:
        mutants = report["mutants"]
        summary = ", ".join(f"{k} {v}" for k, v in mutants.items()) or report.get("detail", "")
        print(f"{report['state'].upper():16} {report['asset_id']}: {summary}")
        if "log_dir" in report:
            baseline = report["runs"]["baseline"]["counts"]
            if baseline is not None:
                print(
                    f"  control selected {baseline['selected']}, executed {baseline['executed']}, deselected {baseline['deselected']}; logs {report['log_dir']}"
                )
        for state in mutants.values():
            counts[state] = counts.get(state, 0) + 1
    failed = sum(r["state"] != "passed" for r in reports)
    tally = ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none run"
    print(
        f"assets {len(reports)}, passed {len(reports) - failed}, failed {failed}; mutants: {tally}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
