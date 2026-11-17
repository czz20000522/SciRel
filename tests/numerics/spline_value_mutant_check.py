"""Are the spline evidence tests load-bearing on the value the spline returns?

Why this file exists
--------------------
``scripts/mutation_check.py`` answers "would these tests notice a wrong output?" with five
output mutants — ``scale``, ``negate``, ``zero``, ``swap`` and ``constant``.  Those mutants
change **numeric leaves** of a returned value.  ``ClampedCubicSpline`` and
``NaturalCubicSpline`` return a *callable object*, which has no such leaf, so all five report
``not_exercised`` for both contracts.  That reading has two possible causes and the mutation
ledger alone cannot separate them:

* the tests never constrain the returned values (a real gap), or
* the instrument cannot reach the value (an instrument limit).

This script separates them by moving the mutation one level down, onto the evaluator, and
re-running the same test file.  It is a **diagnostic for the tests**, not for the
implementation: a green verdict means "these tests would go red if the spline returned
something wrong", which is what makes the ``not_exercised`` line in each contract's
verification block an *attributable* blind spot rather than an unexplained blank.

Usage::

    python3 scripts/dev.py run python -B tests/numerics/spline_value_mutant_check.py

Exit codes are the three states this repository requires, never two:

``0``  every expectation met (baseline green, every mutant red at or above the floor).
``1``  an expectation failed — the numbers below say which.
``2``  not observed: pytest output could not be parsed or the mutant never loaded, so no
       conclusion is available.  This is *not* a pass.

Expectations, fixed before measurement:

* the baseline run of the evidence file is green and collects at least one test;
* the plugin wrote its load marker for each mutant (positive control: a mutant that never
  installed would otherwise look like "tests survived");
* with the evaluator returning zeros, and again with it returning ten times its value, at
  least 80% of the collected tests fail.

The floor is a share of the collected count rather than the literal 21/20 of one revision, so
adding a test to the evidence file does not require editing this script; the measured numbers
are printed either way.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "tests" / "numerics" / "test_spline_boundary_evidence.py"
RED_FLOOR = 0.80
TIMEOUT_SECONDS = 600
MUTANTS = ("zero", "scale")

PLUGIN_SOURCE = '''"""Ad-hoc mutant: patch the spline evaluator, not the returned object."""

import os

import numpy as np

import scirel.numerics.basis as basis


def pytest_configure(config):
    mutant = os.environ.get("SPLINE_MUTANT", "")
    marker = os.environ.get("SPLINE_MUTANT_MARKER", "")
    if marker:
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(mutant + "\\n")
    if mutant not in ("zero", "scale"):
        return
    original = basis.CubicSpline._interpolate

    def patched(self, x_value, deriv=0):
        values = np.asarray(original(self, x_value, deriv))
        if mutant == "zero":
            return np.zeros_like(values)
        return values * 10.0

    basis.CubicSpline._interpolate = patched
'''

COUNT_FAILED = re.compile(r"(\d+) failed")
COUNT_PASSED = re.compile(r"(\d+) passed")


def _plugin(directory: Path) -> Path:
    path = directory / "spline_value_mutant.py"
    path.write_text(PLUGIN_SOURCE, encoding="utf-8")
    return directory


def _run(mutant: str, plugin_dir: Path, marker: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(plugin_dir), str(ROOT / "src"), env.get("PYTHONPATH", "")]
    )
    env.pop("PYTEST_ADDOPTS", None)
    env["SPLINE_MUTANT"] = mutant
    env["SPLINE_MUTANT_MARKER"] = str(marker)
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "--tb=no",
        "-p",
        "no:cacheprovider",
        "-p",
        "spline_value_mutant",
        str(EVIDENCE),
    ]
    done = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    output = done.stdout + done.stderr
    failed = COUNT_FAILED.search(output)
    passed = COUNT_PASSED.search(output)
    counts = None
    if passed is not None:
        counts = {
            "failed": int(failed.group(1)) if failed else 0,
            "passed": int(passed.group(1)),
        }
    return {
        "mutant": mutant,
        "returncode": done.returncode,
        "counts": counts,
        "output": output,
        "marker": marker.is_file(),
    }


def main() -> int:
    if not EVIDENCE.is_file():
        print(f"NOT OBSERVED  the evidence file is missing: {EVIDENCE.relative_to(ROOT)}")
        return 2
    problems: list[str] = []
    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="spline-mutant-") as temporary:
        directory = Path(temporary)
        plugin_dir = _plugin(directory)
        for index, mutant in enumerate(("baseline", *MUTANTS)):
            marker = directory / f"loaded-{index}.marker"
            result = _run(mutant, plugin_dir, marker)
            rows.append(result)
            print(
                f"{mutant:9s} exit {result['returncode']}  "
                f"counts {result['counts']}  marker {result['marker']}"
            )
            if result["counts"] is None:
                problems.append(f"{mutant}: pytest output could not be parsed (not observed)")
                print("  full output:", result["output"][-2000:].replace("\n", "\n  "))
            elif mutant != "baseline" and not result["marker"]:
                problems.append(f"{mutant}: the mutant never loaded, so its run proves nothing")

    baseline_row = rows[0]
    baseline = baseline_row["counts"]
    if baseline is None:
        return 2
    collected = baseline["failed"] + baseline["passed"]
    if baseline_row["returncode"] != 0 or baseline["failed"] != 0 or baseline["passed"] == 0:
        problems.append(
            f"baseline is not green: exit {baseline_row['returncode']}, counts {baseline}"
        )
    for result in rows[1:]:
        counts = result["counts"]
        if counts is None:
            continue
        floor = math.ceil(RED_FLOOR * collected)
        if counts["failed"] < floor:
            problems.append(
                f"{result['mutant']}: {counts['failed']} of {collected} tests failed, "
                f"below the {floor}-test floor"
            )
        if result["returncode"] == 0:
            problems.append(f"{result['mutant']}: pytest exited 0, so no test caught the mutant")

    print(
        f"\ncollected {collected}; "
        + "; ".join(
            f"{row['mutant']} red {(row['counts'] or {}).get('failed', 'n/a')}" for row in rows
        )
    )
    if problems:
        for problem in problems:
            print("FAIL          " + problem)
        return 1
    print("PASS          the evidence file is load-bearing on the returned spline values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
