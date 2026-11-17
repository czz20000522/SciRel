"""C4 round-2 runner: executes the frozen task list against the delivered package.

Usage (from a checkout, with the *delivered venv* interpreter):

    SCIREL_PACKAGE_ROOT=<package dir> python -I examples/c4-usage-acceptance/round2/run.py
    SCIREL_PACKAGE_ROOT=<package dir> python -I examples/c4-usage-acceptance/round2/run.py --task <id>

Every task runs in its own interpreter process: a task that leaves library state in an
unusual shape cannot alter the result of another task, and the per-task log is the only
thing that crosses the boundary.  No file of this repository outside
``examples/c4-usage-acceptance/`` is read.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent
HOME = Path.home()


def scrub(text: str) -> str:
    """Keep machine-local paths out of the tracked record."""
    if not isinstance(text, str):
        return text
    for prefix, token in ((str(REPO_ROOT) + "/", "<repo>/"),
                          (str(REPO_ROOT), "<repo>"),
                          (str(HOME), "<home>")):
        text = text.replace(prefix, token)
    return text
sys.path.insert(0, str(HERE))

import harness as H  # noqa: E402

TASKLIST = HERE.parent / "tasklist.json"
OUT_DIR = HERE / "tasks"


def tasklist() -> dict:
    return json.loads(TASKLIST.read_text())


def task_by_id(tid: str) -> dict:
    for t in tasklist()["tasks"]:
        if t["id"] == tid:
            return t
    raise KeyError(tid)


def environment() -> dict:
    import numpy, scipy, mpmath  # noqa: E401
    rt = H.runtime_json()
    return {
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "mpmath": mpmath.__version__,
        "wheel_sha256": rt["runtime"]["wheel_sha256"],
        "snapshot_sha256": rt["snapshot_sha256"],
        "source_revision": rt.get("source_revision"),
        "asset_count": rt.get("asset_count"),
        "runtime": rt.get("runtime"),
    }


def _result_block(value) -> dict:
    """Answer block: value + unit + a plain statement of what was computed."""
    return {"value": H.plain(value)}


# ------------------------------------------------------------------ one task


def run_task(tid: str) -> dict:
    from checks import CHECKS  # noqa: E402  (imported lazily so --list works without it)

    task = task_by_id(tid)
    ctx = H.Ctx(task)
    record = {
        "task_id": tid,
        "kind": task["kind"],
        "domain": task["domain"],
        "subdomain": task["subdomain"],
        "question": task["question"],
        "assets_declared": task["assets"],
        "min_calls": task["min_calls"],
        "package": environment(),
        "assets_used": [],
        "calls": [],
        "answer": None,
        "independent_check": None,
        "criteria": [],
        "package_sufficient": False,
        "sufficient_reason": "",
        "gaps": [],
    }

    fn = CHECKS.get(tid)
    if fn is None:
        record["gaps"].append(H.gap(
            "process",
            "no consumer check implemented for this task id; low-level criteria (contract "
            "fields, parameters) were still evaluated from the delivered contracts",
        ))
        body = _generic_body(ctx, task)
    else:
        body = fn(ctx, task)

    record["assets_used"] = sorted({c["asset"] for c in ctx.calls})
    record["calls"] = [_strip(c) for c in ctx.calls]
    record["answer"] = body.get("answer")
    record["independent_check"] = body.get("independent_check")
    record["gaps"] = record["gaps"] + body.get("gaps", [])
    record["package_sufficient"] = bool(body.get("package_sufficient", False))
    record["sufficient_reason"] = body.get("sufficient_reason", "")
    record["criteria"] = body.get("criteria", [])
    record["bindings"] = {
        asset: {"symbol": b["symbol"], "args": H.plain(b["named"]),
                "example_error": b["example_error"]}
        for asset, b in ctx.bindings.items()
    }
    if len(ctx.calls) < task["min_calls"]:
        record["gaps"].append(H.gap(
            "process",
            f"task declares min_calls={task['min_calls']} but only {len(ctx.calls)} "
            "public call(s) were made",
        ))
    return record


def _strip(call: dict) -> dict:
    return {k: v for k, v in call.items() if not k.startswith("_")}


def _generic_body(ctx: H.Ctx, task: dict) -> dict:
    criteria = []
    answers = {}
    for asset in task["assets"]:
        call = ctx.call(asset, ctx.named(asset), label=f"contract example of {asset}")
        criteria.append({"id": f"fields@{asset}", "kind": "contract_fields",
                         "status": H.check_fields(ctx, call, asset)["status"],
                         "detail": H.check_fields(ctx, call, asset)["detail"]})
        param = H.check_parameters(ctx.named(asset), asset, [])
        criteria.append({"id": f"params@{asset}", "kind": "parameters",
                         "status": param["status"], "detail": param["detail"]})
        if "_value" in call:
            answers[asset] = H.plain(call["_value"])
    return {
        "criteria": criteria,
        "answer": {"value": answers, "unit": "as declared"},
        "independent_check": {"method": "none", "verdict": "not-run"},
        "package_sufficient": False,
        "sufficient_reason": "no task-specific check was run",
        "gaps": [H.gap("process", "task-specific criteria were not evaluated")],
    }


# ------------------------------------------------------------------ readback


def readback(tid: str) -> dict:
    """Re-open the written task record and confirm the stored product is what was claimed."""
    path = OUT_DIR / f"{tid}.json"
    data = json.loads(path.read_text())
    problems = []
    no_call_by_design = any(c["id"] == "nocall" and c["status"] == "pass"
                            for c in data.get("criteria", []))
    if not data.get("calls") and not no_call_by_design:
        problems.append("no calls stored")
    for c in data["calls"]:
        if c["status"] == "returned" and not c.get("returned_fields") \
                and c.get("returned_type") in ("Result", "dict", "OrderedDict"):
            problems.append(f"call {c['seq']} returned a mapping but stored no field names")
        if c["status"] == "returned" and not c.get("returned_type"):
            problems.append(f"call {c['seq']} stored no returned type")
        if c["status"] == "raised" and not c.get("exception"):
            problems.append(f"call {c['seq']} raised but stored no exception")
    if data.get("answer") is None:
        problems.append("no answer stored")
    if not data.get("independent_check"):
        problems.append("no independent check stored")
    return {"status": "pass" if not problems else "fail",
            "detail": {"reopened": str(path.name), "problems": problems,
                       "stored_call_count": len(data.get("calls", []))}}


def write_task(record: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{record['task_id']}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")


def run_one(tid: str) -> int:
    try:
        record = run_task(tid)
    except BaseException as exc:  # noqa: BLE001 - a crashed task is recorded, not hidden
        record = {
            "task_id": tid,
            "kind": task_by_id(tid)["kind"],
            "domain": task_by_id(tid)["domain"],
            "crashed": True,
            "package_sufficient": False,
            "sufficient_reason": "consumer check raised",
            "gaps": [H.gap("blocking",
                          f"the consumer harness raised {type(exc).__name__}: {exc}")],
            "traceback": scrub(traceback.format_exc()),
            "calls": [],
            "criteria": [],
            "answer": None,
            "independent_check": None,
        }
    write_task(record)
    rb = readback(tid)
    record = json.loads((OUT_DIR / f"{tid}.json").read_text())
    record["criteria"] = [c for c in record.get("criteria", [])
                          if c["id"] != "readback"] + [{
        "id": "readback", "kind": "readback",
        "status": rb["status"], "detail": rb["detail"]}]
    write_task(record)
    return 0 if rb["status"] == "pass" else 1


def run_all() -> int:
    ids = [t["id"] for t in tasklist()["tasks"]]
    env = dict(os.environ)
    env.setdefault("SCIREL_PACKAGE_ROOT", os.environ.get("SCIREL_PACKAGE_ROOT", ""))
    failures = []
    for i, tid in enumerate(ids, 1):
        proc = subprocess.run(
            [sys.executable, "-I", str(HERE / "run.py"), "--task", tid],
            cwd=str(HERE.parent.parent.parent), env=env,
            capture_output=True, text=True,
        )
        status = "ok" if proc.returncode == 0 else "CHECK"
        print(f"[{i:02d}/{len(ids)}] {status} {tid}", flush=True)
        if proc.returncode != 0:
            failures.append({"task": tid, "returncode": proc.returncode,
                             "stderr": scrub(proc.stderr[-3000:])})
    build_index(failures)
    return 0 if not failures else 1


def build_index(failures: list) -> None:
    tasks = {t["id"]: t for t in tasklist()["tasks"]}
    rows = []
    for tid in tasks:
        path = OUT_DIR / f"{tid}.json"
        if not path.is_file():
            rows.append({"task_id": tid, "kind": tasks[tid]["kind"],
                         "domain": tasks[tid]["domain"], "status": "missing"})
            continue
        d = json.loads(path.read_text())
        crit = d.get("criteria", [])
        rows.append({
            "task_id": tid,
            "kind": d.get("kind"),
            "domain": d.get("domain"),
            "subdomain": d.get("subdomain"),
            "package_sufficient": d.get("package_sufficient"),
            "call_count": len(d.get("calls", [])),
            "criteria_total": len(crit),
            "criteria_pass": sum(1 for c in crit if c.get("status") == "pass"),
            "criteria_fail": sum(1 for c in crit if c.get("status") == "fail"),
            "criteria_not_run": sum(1 for c in crit if c.get("status") == "not-run"),
            "gaps": [g["text"] for g in d.get("gaps", [])],
        })
    index = {
        "schema": "scirel.c4-usage-round2.index",
        "tasklist_digest": tasklist()["tasks_digest"],
        "package": environment(),
        "tasks": rows,
        "summary": {
            "tasks": len(rows),
            "package_sufficient": sum(1 for r in rows if r.get("package_sufficient")),
            "package_insufficient": sum(1 for r in rows if r.get("package_sufficient") is False),
            "criteria_total": sum(r.get("criteria_total", 0) for r in rows),
            "criteria_pass": sum(r.get("criteria_pass", 0) for r in rows),
            "criteria_fail": sum(r.get("criteria_fail", 0) for r in rows),
            "criteria_not_run": sum(r.get("criteria_not_run", 0) for r in rows),
        },
        "child_failures": failures,
    }
    (HERE / "results.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    with (HERE / "calls.jsonl").open("w") as fh:
        for tid in tasks:
            path = OUT_DIR / f"{tid}.json"
            if not path.is_file():
                continue
            for call in json.loads(path.read_text()).get("calls", []):
                fh.write(json.dumps({"task_id": tid, **call}, ensure_ascii=False) + "\n")


def main(argv: list[str]) -> int:
    if "--task" in argv:
        return run_one(argv[argv.index("--task") + 1])
    if "--list" in argv:
        for t in tasklist()["tasks"]:
            print(t["id"], t["kind"], t["domain"])
        return 0
    return run_all()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
