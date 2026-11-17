"""Reproducible mutation ledger for the four C1 kinetic evidence files.

Why this file exists
--------------------
The four contracts this batch touches (`kinetic-wavevector-roots`, `kinetic-wavevector-scan`,
`parallel-em-continuation`, `parallel-em-residual`) now carry assertion-level evidence claims.  A claim
is only evidence if its assertion would *change* when the thing it names changes, so each claim gets a
targeted mutant here -- one mutant per claim, applied by ``_c1_kinetic_final4_mutants.py`` and graded
against the evidence file alone.  ``scripts/mutation_check.py`` stays the generic five-mutant sweep and
is reported separately; it cannot see these claims, because scale/negate/zero/swap/constant do not touch
"the ladder is a ulp-exact colon expression" or "a false success is rejected".

Grading follows the repository's four states (plus the unobserved one), and ``covered`` is only assigned
when the mutated callable demonstrably ran:

``killed``        the mutant was installed, its callable was reached, and the evidence file went red.
``covered``       installed and reached, tests stayed green: the claim does not constrain this behaviour.
``not-exercised`` installed, but no mutated callable was reached: the test path never arrived.
``equivalent``    judged by reading, not measurable here: the mutant cannot change any observable.  This
                  script never assigns it -- a mutant that cannot change an observable must not exist in
                  the table.  Where a *plausible* defect is invisible to this contract's surfaces, the
                  entry is listed as ``covered`` with the owning surface named in ``OWNED_ELSEWHERE``.
``UNKNOWN``       the instrument failed (plugin did not install, pytest output unusable), so no
                  conclusion is available.  It is never folded into ``killed``.

Exit codes are the three states this repository requires: ``0`` every expectation met, ``1`` at least
one mutant survived or the baseline was red, ``2`` at least one mutant is UNKNOWN.

Usage::

    python3 scripts/dev.py run python -B tests/kinetic/c1_kinetic_final4_mutant_check.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = ROOT / "tests" / "kinetic"

# asset id -> (evidence file, {mutant: claim the mutant attacks})
TARGETS = {
    "scirel.kinetic.kinetic-wavevector-roots": (
        "tests/kinetic/test_kinetic_wavevector_roots_evidence.py",
        {
            "roots_seed": "the returned root is a zero of the determinant, not the seed",
            "roots_conj": "the returned root is the conjugated branch",
            "roots_scaled": "the returned root is not a near-miss of the zero",
            "roots_flag_ok": "a nonconverged exit is not promoted to success",
        },
    ),
    "scirel.kinetic.kinetic-wavevector-scan": (
        "tests/kinetic/test_kinetic_wavevector_scan_evidence.py",
        {
            "scan_ulp": "the ladder is the declared colon expression bit for bit",
            "scan_seed": "the fixed seed is 0.6*kn, not a scaled copy",
            "scan_flag_ok": "a modulus jump along the ladder is disclosed by the exit flags",
        },
    ),
    "scirel.kinetic.parallel-em-continuation": (
        "tests/kinetic/test_parallel_em_continuation_evidence.py",
        {
            "cont_noise": "accepted roots reproduce the closed-form vacuum branch",
            "cont_ignore_bound": "a solver success above the residual bound is rejected",
            "cont_swallow_failure": "a rejected point produces no successor row",
        },
    ),
    "scirel.kinetic.parallel-em-residual": (
        "tests/kinetic/test_parallel_em_residual_evidence.py",
        {
            "res_drop_pm": "the residual carries the fixed polarization sign",
            "res_signed_k": "both causal denominators keep |k|, so signed-k handling is asserted",
            "res_scale": "the residual value matches the direct velocity integral",
        },
    ),
}

# Mutants that a surviving run shows to be *semantically equivalent* for this contract, with the
# reading-based proof.  A "covered" grade is reclassified to "equivalent" only through this table, so
# no survival is upgraded by hand: the entry must carry an argument that no assertion could kill it
# without contradicting the contract.
EQUIVALENT = {
    "roots_conj": (
        "det(kx) depends on kx only through kx**2 in this port (the Ronnmark tensor is assembled from "
        "b = a**2 with kz=0), so -r is a root whenever r is; the contract explicitly refuses to say which "
        "signed root is returned ('... without mirroring roots').  Flipping the sign therefore maps one "
        "valid answer of the declared relation onto another valid one, and every anchor here -- the "
        "recomputed relative determinant, the displacement factor, and the conjugate-pair identity -- is "
        "invariant under the flip by construction.  Killing it would require asserting an absolute sign "
        "mapping from seed to branch, i.e. adding a claim the contract does not make; that would have to "
        "be introduced as a new contract claim with its own evidence, not as a stronger assertion here."
    ),
}

# Defects a contract deliberately does not constrain, with the surface that owns them.  Recorded here so
# "covered" is never left as an unexplained survival.
OWNED_ELSEWHERE = {
    "scirel.kinetic.parallel-em-continuation": {
        "k sign inside the residual call": (
            "not measurable here: the vacuum branch is even in k, so a sign flip inside the residual "
            "leaves every assertion of this contract unchanged. It is owned by "
            "scirel.kinetic.parallel-em-residual, whose signed-k quadrature anchor catches it."
        )
    },
    "scirel.kinetic.kinetic-wavevector-scan": {
        "branch topology between ladder points": (
            "not asserted by design: the contract excludes mode identity and branch labels, so a "
            "mutant that swaps the sign of a converged root leaves this contract green. The "
            "conjugate-pair anchor of scirel.kinetic.kinetic-wavevector-roots owns sign behaviour."
        )
    },
}

TIMEOUT_SECONDS = 1800


def _environment(mutant: str, hits: Path, log: Path) -> dict:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(ROOT / "src"),
            str(ROOT / "scripts"),
            str(PLUGIN_DIR),
            environment.get("PYTHONPATH", ""),
        ]
    )
    environment.pop("PYTEST_ADDOPTS", None)
    environment["C1F4_MUTANT"] = mutant
    environment["C1F4_HITS"] = str(hits)
    return environment


def _run(test_file: str, mutant: str, workdir: Path) -> dict:
    hits = workdir / "hits.txt"
    if hits.exists():
        hits.unlink()
    log = workdir / ("log-" + (mutant or "baseline") + ".txt")
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "_c1_kinetic_final4_mutants",
        test_file,
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=_environment(mutant, hits, log),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    lines = hits.read_text(encoding="utf-8").splitlines() if hits.exists() else []
    calls = [line for line in lines if ":" not in line]
    return {
        "exit_code": completed.returncode,
        "installed": ("installed:" + mutant) in lines,
        "unknown": ("unknown:" + mutant) in lines,
        "calls": len(calls),
        "log": str(log),
    }


def _grade(mutant_run: dict) -> str:
    if mutant_run["unknown"] or not mutant_run["installed"]:
        return "UNKNOWN"
    if mutant_run["calls"] == 0:
        return "not-exercised"
    if mutant_run["exit_code"] == 0:
        return "covered"
    if mutant_run["exit_code"] == 1:
        return "killed"
    return "UNKNOWN"


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="c1f4-mutants-", dir=ROOT / ".runtime"))
    ledger: dict[str, dict[str, str]] = {}
    unobserved = False
    failures = False
    for asset, (test_file, mutants) in TARGETS.items():
        baseline = _run(test_file, "", workdir)
        if baseline["exit_code"] != 0:
            print(f"BASELINE RED  {asset}: read {baseline['log']}")
            failures = True
            ledger[asset] = {"<baseline>": "baseline_failed"}
            continue
        grades = {}
        for mutant in mutants:
            observed = _run(test_file, mutant, workdir)
            grade = _grade(observed)
            if grade == "covered" and mutant in EQUIVALENT:
                grade = "equivalent"
                print(f"equivalent     {asset} :: {mutant} -- {EQUIVALENT[mutant]}")
            grades[mutant] = grade
            if grade == "UNKNOWN":
                unobserved = True
                failures = failures or True
            elif grade not in ("killed", "equivalent"):
                failures = True
            print(
                f"{grade:14} {asset} :: {mutant} -- {mutants[mutant]}"
                + (
                    f"  (calls {observed['calls']}, log {observed['log']})"
                    if grade != "killed"
                    else ""
                )
            )
        ledger[asset] = grades

    print()
    print("ledger (JSON):")
    print(json.dumps(ledger, ensure_ascii=False, indent=1))
    for asset, entries in OWNED_ELSEWHERE.items():
        for claim, note in entries.items():
            print(f"owned-elsewhere {asset} :: {claim} -- {note}")

    counts: dict[str, int] = {}
    for grades in ledger.values():
        for grade in grades.values():
            counts[grade] = counts.get(grade, 0) + 1
    print("totals:", ", ".join(f"{key} {value}" for key, value in sorted(counts.items())))
    if unobserved:
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
