"""Self-checks for the consumer harness itself.

Two failure classes in this directory were invisible to a green task run:

* **never-executed code** — ``review.py`` called an undefined ``_val`` and a whole
  ``check_fields`` branch returned ``None``; both compiled and imported fine, and only
  crashed on the one path no run had taken.
* **lint rot** — unused imports/variables accumulated because nothing looked at them.

``selfcheck.py`` exercises every branch of the criteria helpers against synthetic calls
and tasks (no library calls needed for most of them), then runs ``ruff`` when it is
available.  Exit codes follow the repository convention: 0 pass, 1 fail, 75 not-run
(ruff unavailable) — "not observed" is never folded into "pass".

    SCIREL_PACKAGE_ROOT=<package> .runtime/.../python -I round2/selfcheck.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness as H  # noqa: E402

TASKLIST = json.loads((HERE.parent / "tasklist.json").read_text())
RESULTS: list[tuple[str, bool, dict]] = []


def check(name: str, ok: bool, detail: dict) -> None:
    RESULTS.append((name, ok, detail))


def call(**kw) -> dict:
    base = {
        "status": "returned",
        "returned_type": "Result",
        "returned_fields": None,
        "exception": None,
        "arguments": {},
        "asset": "?",
        "entrypoint": "?",
        "seq": 1,
        "label": "",
        "warnings": [],
    }
    base.update(kw)
    return base


def criteria_helpers() -> None:
    green = "scirel.field.circular-filament-green"  # 3 declared outputs, Result
    volume = "scirel.geometry.masked-toroidal-volume"  # 1 declared output, float scalar
    polar = "scirel.geometry.meridional-polar-forward"  # 1 declared output, tuple
    thermo = "scirel.physics.thermal-energy"  # 3 declared outputs, tuple

    r = H.check_fields(None, call(returned_fields=["gBR", "gBZ", "gpsi"]), green)
    check("mapping/equal -> pass", r["status"] == "pass", r)

    r = H.check_fields(None, call(returned_fields=["gBR"]), green)
    check("mapping/subset -> fail", r["status"] == "fail", r)

    r = H.check_fields(None, call(returned_type="float", returned_fields=None), volume)
    check(
        "bare single/compatible -> pass + channel",
        r["status"] == "pass"
        and r["detail"].get("channel") == "single declared output returned positionally",
        r,
    )

    r = H.check_fields(None, call(returned_type="tuple", returned_fields=None), polar)
    check("bare single/tuple dtype -> pass", r["status"] == "pass", r)

    r = H.check_fields(None, call(returned_type="tuple", returned_fields=None), volume)
    check("bare single/scalar shape vs tuple -> fail", r["status"] == "fail", r)

    r = H.check_fields(None, call(returned_type="tuple", returned_fields=None), thermo)
    check("bare MULTI -> fail (multi-output not loosened)", r["status"] == "fail", r)

    r = H.check_fields(
        None, call(status="raised", returned_fields=None, exception={"type": "ValueError"}), green
    )
    check("raised -> fail", r["status"] == "fail", r)

    # _args_for must pass parameters before *fields positionally (the TypeError class)
    named = H.discover("scirel.geometry.regular-grid")["named"]
    args, kwargs = H._args_for("scirel.geometry.regular-grid", named)
    check(
        "_args_for with *fields keeps xx/yy positional",
        "xx" not in kwargs and "yy" not in kwargs and len(args) >= 3,
        {"args": len(args), "kwargs": sorted(kwargs)[:6]},
    )


def review_module_runs() -> None:
    """Exercise the review checks end to end (they are the ones that kept crashing)."""
    from checks import CHECKS  # noqa: E402

    ctx = H.Ctx({"id": "selfcheck"})
    for task_id in ("electromagnetism-rejects-missing-mesh", "diagnostics-rejects-shape-mismatch"):
        task = next(t for t in TASKLIST["tasks"] if t["id"] == task_id)
        try:
            body = CHECKS[task_id](ctx, task)
        except BaseException as exc:  # noqa: BLE001
            check(
                f"review check runs: {task_id}",
                False,
                {"exception": f"{type(exc).__name__}: {exc}"},
            )
            continue
        check(
            f"review check runs: {task_id}",
            bool(body.get("criteria")),
            {
                "criteria": len(body.get("criteria", [])),
                "sufficient": body.get("package_sufficient"),
            },
        )


def audit_helpers() -> None:
    """Exercise the closeout audits' own decision points.

    ``audits.py`` decides things the task run never touches: which contracts declare a
    return channel, and what ``1.5*sum(p*vpr*drho)`` is.  Both are oracles, so both get a
    sensitivity case: a wrong input must move the verdict, not only a right input keep it.
    """
    import audits as A  # noqa: E402

    positional = (
        "Elastic cross section, one value per energy. Returned directly as the callable's "
        "single positional value (N,); it is not a field of a mapping."
    )
    field_of_result = "Field of the returned scirel._result.Result mapping: W_el integrated."
    silent = "W_el integrated thermal energy."

    check("audit channel/positional", A.channel_of(positional) == "positional", {})
    check("audit channel/result-field", A.channel_of(field_of_result) == "result-field", {})
    check("audit channel/undeclared", A.channel_of(silent) == "undeclared", {})

    # exact oracle: the 3/2 factor and the weight order both matter
    ok = A.exact_energy([2, 2], [2.0, 3.0], [0.4, 0.6])
    check("audit exact_energy/3-2 weighted sum", ok == 7.8, {"got": ok})
    doubled = A.exact_energy([2, 2], [4.0, 6.0], [0.4, 0.6])
    check(
        "audit exact_energy reacts to a doubled weight",
        abs(doubled - 2 * ok) <= 0 and doubled != ok,
        {"doubled": doubled},
    )
    check(
        "audit exact_energy reacts to a dropped 3/2",
        abs(A.exact_energy([2, 2], [2.0, 3.0], [0.4, 0.6]) - 5.2) > 1e-9,
        {"unweighted": 5.2},
    )


def eqdsk_replay() -> None:
    from unittest.mock import patch

    from checks.batch2 import _compare_eqdsk, io_eqdsk_roundtrip

    task = next(t for t in TASKLIST["tasks"] if t["id"] == "io-eqdsk-roundtrip")
    ctx = H.Ctx(task)
    nominal = io_eqdsk_roundtrip(ctx, task)
    check("roundtrip exercises both reads", nominal["independent_check"]["verdict"] == "pass", {})
    tolerance = {"rel": 1e-9, "abs": 0}
    damaged = _compare_eqdsk({"a": [0.0], "b": 2, "c": [[1]]}, {"a": [1e-16], "c": [1]}, tolerance)
    check(
        "zero, lost key and shape change rejected",
        damaged["missing"] == ["b"] and damaged["mismatches"] == ["a", "c"],
        damaged,
    )

    def partial_writer(data, filename):
        Path(filename).write_text("residual output")
        raise OSError("injected failure after write")

    module, symbol, _ = H.resolve("scirel.io.write-eqdsk")
    ctx = H.Ctx(task)
    with patch.object(module, symbol, partial_writer):
        failed = io_eqdsk_roundtrip(ctx, task)
    check(
        "residual after exception is not read back",
        not failed["package_sufficient"]
        and failed["independent_check"]["verdict"] == "not-run"
        and sum(c["asset"] == "scirel.io.read-eqdsk" for c in ctx.calls) == 1
        and any(c["status"] == "raised" for c in ctx.calls),
        {},
    )


def registry() -> None:
    from checks import CHECKS  # noqa: E402  (import here so harness checks run first)

    missing = [t["id"] for t in TASKLIST["tasks"] if t["id"] not in CHECKS]
    check("every task id has a check", not missing, {"missing": missing})
    # every check module must be importable and expose CHECKS
    modules = sorted(p.stem for p in (HERE / "checks").glob("*.py") if not p.stem.startswith("_"))
    broken = []
    for name in modules:
        mod = __import__(f"checks.{name}", fromlist=["CHECKS"])
        if name != "__init__" and not hasattr(mod, "CHECKS"):
            broken.append(name)
    check("check modules expose CHECKS", not broken, {"modules": modules, "broken": broken})


def ruff() -> int:
    """Run ruff if present. 75 = not observed, never silently pass."""
    exe = None
    for cand in (HERE.parents[2] / ".runtime" / "venv" / "bin" / "ruff",):
        if cand.is_file():
            exe = str(cand)
            break
    exe = exe or shutil.which("ruff")
    if not exe:
        print("ruff: NOT-RUN (binary not found) -> exit 75")
        return 75
    proc = subprocess.run([exe, "check", str(HERE)], capture_output=True, text=True)
    ok = proc.returncode == 0
    print(f"ruff: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(proc.stdout[-3000:] or proc.stderr[-3000:])
    RESULTS.append(("ruff clean", ok, {"findings": proc.stdout.count("\n")}))
    return 0 if ok else 1


def main() -> int:
    H.installed_wheel_origin()
    criteria_helpers()
    eqdsk_replay()
    audit_helpers()
    registry()
    review_module_runs()
    rc = ruff()
    width = max(len(n) for n, _, _ in RESULTS)
    for name, ok, detail in RESULTS:
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {json.dumps(detail)[:120]}")
    failed = [n for n, ok, _ in RESULTS if not ok]
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    if rc == 75:
        print("\npartial: criteria and registry passed; ruff NOT-RUN (exit 75)")
        return 75
    print(f"\nPASS: {len(RESULTS)} self-checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
