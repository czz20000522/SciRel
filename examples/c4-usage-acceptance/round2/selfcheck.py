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
    criteria_helpers()
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
