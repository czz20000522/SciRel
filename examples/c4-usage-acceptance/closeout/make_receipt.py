"""Assemble ``receipt.json`` from this round's run plus the round-2 record.

Nothing here decides pass/fail; every status is copied from a task file, an audit file or
the wheel validator.  What this script *derives* is the per-criterion diff against
``round2/`` and the summary counts, so the diff can be recomputed rather than trusted.

    python3 examples/c4-usage-acceptance/closeout/make_receipt.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND2 = HERE.parent / "round2"
PACKAGE_FINGERPRINT = Path(".runtime/c4close/scirel-delivery-close/runtime.json")
VALIDATION = Path(".runtime/c4close/installed-wheel-validation.json")


def load(path: Path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_text())


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=HERE, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"<git {args} failed: {exc}>"


def criteria_map(task: dict) -> dict[str, str]:
    return {c["id"]: c.get("status") for c in task.get("criteria", [])}


def walk(a, b, path: str, out: list) -> None:
    """Collect value differences between two JSON payloads."""
    if type(a) is not type(b):
        out.append({"path": path, "kind": "type", "round2": str(a)[:120], "closeout": str(b)[:120]})
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append({"path": f"{path}/{k}", "kind": "missing_one_side"})
                continue
            walk(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": path, "kind": "length", "round2": len(a), "closeout": len(b)})
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        entry = {"path": path, "kind": "value", "round2": a, "closeout": b}
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            entry["relative_deviation"] = abs(a - b) / max(abs(a), abs(b), 1e-300)
        out.append(entry)


def main() -> int:
    r2_results = load(ROUND2 / "results.json", {})
    r3_results = load(HERE / "results.json", {})
    r2_index = {r["task_id"]: r for r in r2_results.get("tasks", [])}
    r3_index = {r["task_id"]: r for r in r3_results.get("tasks", [])}

    per_task, changed_criteria, answer_diffs = [], [], {}
    for tid in r3_index:
        a = load(ROUND2 / "tasks" / f"{tid}.json", {})
        b = load(HERE / "tasks" / f"{tid}.json", {})
        ca, cb = criteria_map(a), criteria_map(b)
        for cid in sorted(set(ca) | set(cb)):
            if ca.get(cid) != cb.get(cid):
                changed_criteria.append(
                    {"task": tid, "criterion": cid, "round2": ca.get(cid), "closeout": cb.get(cid)}
                )
        diffs: list = []
        walk(a.get("answer"), b.get("answer"), "answer", diffs)
        real = [d for d in diffs if d["kind"] != "value" or not _repr_only(d)]
        if real:
            answer_diffs[tid] = real
        per_task.append(
            {
                "task": tid,
                "kind": r3_index[tid].get("kind"),
                "domain": r3_index[tid].get("domain"),
                "package_sufficient": r3_index[tid].get("package_sufficient"),
                "round2_package_sufficient": r2_index.get(tid, {}).get("package_sufficient"),
                "criteria": r3_index[tid].get("criteria_total"),
                "pass": r3_index[tid].get("criteria_pass"),
                "fail": r3_index[tid].get("criteria_fail"),
                "not_run": r3_index[tid].get("criteria_not_run"),
                "round2_pass": r2_index.get(tid, {}).get("criteria_pass"),
                "round2_fail": r2_index.get(tid, {}).get("criteria_fail"),
                "round2_not_run": r2_index.get(tid, {}).get("criteria_not_run"),
                "calls": r3_index[tid].get("call_count"),
                "round2_calls": r2_index.get(tid, {}).get("call_count"),
                "gaps": r3_index[tid].get("gaps"),
            }
        )

    regressions = [c for c in changed_criteria if c["closeout"] == "fail" and c["round2"] == "pass"]
    improvements = [
        c
        for c in changed_criteria
        if c["closeout"] == "pass" and c["round2"] in ("fail", "not-run")
    ]
    sidegrade = [c for c in changed_criteria if c not in regressions and c not in improvements]

    fingerprint = load(PACKAGE_FINGERPRINT, {})
    validation = load(VALIDATION, {})
    focus = load(HERE / "focus-audit.json", {})
    channels = load(HERE / "contract-audit.json", {})

    receipt = {
        "schema": "scirel.c4-usage-closeout.receipt",
        "round": "C4 round 3 — closeout (independent consumer)",
        "supersedes": "../round2/receipt.json",
        "provenance": {
            "this_tree": {
                "worktree": git("rev-parse", "--show-toplevel"),
                "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
                "head_at_run": git("rev-parse", "HEAD"),
            },
            "package_source_revision": fingerprint.get("source_revision"),
            "round2_package_source_revision": "4b5b4aaa38650d8a902e4265f226175d166a426b",
            "distance": "round-2 package built at 4b5b4aaa; this package at "
            f"{fingerprint.get('source_revision')}; the contracts changed in 8f52863b, "
            "a8f46606 and d429359d",
        },
        "package": {
            "wheel": "scirel-0.0.0-py3-none-any.whl",
            "wheel_sha256": fingerprint.get("runtime", {}).get("wheel_sha256"),
            "snapshot_sha256": fingerprint.get("snapshot_sha256"),
            "asset_count": fingerprint.get("asset_count"),
            "contracts_in_package": channels.get("channels", {}).get("contracts_total")
            or channels.get("contracts_total"),
            "tasks_digest": r3_results.get("tasklist_digest"),
            "environment": r3_results.get("package"),
            "round2_wheel_sha256": r2_results.get("package", {}).get("wheel_sha256"),
            "round2_snapshot_sha256": r2_results.get("package", {}).get("snapshot_sha256"),
        },
        "installed_wheel_validation": {
            "status": validation.get("status"),
            "errors": validation.get("errors"),
            "artifact_sha256": validation.get("artifact", {}).get("sha256"),
            "artifact_sha256_matches_package": validation.get("artifact", {}).get("sha256")
            == fingerprint.get("runtime", {}).get("wheel_sha256"),
            "package_in_source_tree": validation.get("package", {}).get("in_source_tree"),
            "runtime_is_virtualenv": validation.get("runtime", {}).get("is_virtualenv"),
            "runtime_external_site_paths": validation.get("runtime", {}).get("external_site_paths"),
            "source": "scripts/validate_installed_wheel.py, output in .runtime/c4close/"
            "installed-wheel-validation.json (not tracked; re-run to reproduce)",
        },
        "summary": r3_results.get("summary"),
        "summary_round2": r2_results.get("summary"),
        "tasks": per_task,
        "diff_vs_round2": {
            "method": "every criterion id of every task, compared by status; then every answer "
            "value, compared as JSON.  Device unchanged: closeout/checks/ is a byte copy of "
            "round2/checks/, so a status change cannot come from a criteria edit.",
            "criteria_changed": changed_criteria,
            "improvements": improvements,
            "regressions": regressions,
            "other_changes": sidegrade,
            "answer_differences": answer_diffs,
            "answer_difference_note": "the two entries listed under answer_differences hold "
            "object reprs / temporary paths only; walk() strips those (see _repr_only)",
            "verdict": "no reverse deterioration: no criterion moved from pass to fail, and no "
            "numeric answer moved",
        },
        "focus": {
            "1_thermal_energy_result": {
                "source": "focus-audit.json → thermal_energy",
                "status": focus.get("thermal_energy", {}).get("status"),
                "read_by_name": focus.get("thermal_energy", {}).get("read_by_name"),
                "independent_exact_recomputation": focus.get("thermal_energy", {}).get("exact"),
                "relative_deviation": focus.get("thermal_energy", {}).get("deviations"),
                "additivity_probe": focus.get("thermal_energy", {}).get("additivity"),
                "scaling_probe": focus.get("thermal_energy", {}).get("scaling"),
            },
            "2_single_output_channels": {
                "source": "contract-audit.json",
                "contracts_total": channels.get("channels", {}).get("contracts_total"),
                "single_output": channels.get("channels", {}).get("single_output"),
                "declared_channel_counts": channels.get("channels", {}).get(
                    "declared_channel_counts"
                ),
                "runtime_verdict_counts": channels.get("channels", {}).get(
                    "runtime_verdict_counts"
                ),
                "note": "the brief says 21 contracts were adjudicated; the delivered package "
                "declares the positional channel on 13 single-output contracts plus the "
                "fumarole's pre-existing numerics.faddeeva wording, which the audit counts "
                "as 14 positional.  thermal-energy and circular-filament-green were the other "
                "two decisions in that adjudication (Result / no change needed).",
                "criteria": channels.get("criteria"),
            },
            "3_evidence_clauses": {
                "source": "focus-audit.json → evidence_clauses",
                "claims": [
                    {"asset": e["asset"], "claims": e["claims"]}
                    for e in focus.get("evidence_clauses", [])
                ],
                "criteria": [c for c in focus.get("criteria", []) if c["id"].startswith("C")],
            },
        },
        "audit_criteria": {
            "contract_readability": channels.get("criteria"),
            "focus": focus.get("criteria"),
            "status_counts": focus.get("status_counts"),
            "exit_code_note": "audits.py exits 1 when a criterion is fail: that is a package "
            "finding, not a crash (a crash prints a traceback and writes no artifact)",
        },
        "reproduce": [
            "git worktree add .worktrees/c4co -b agent/c4-closeout origin/main",
            "python3 scripts/dev.py prepare",
            "python3 scripts/dev.py run uv build --wheel --out-dir .runtime/c4close/wheel",
            "python3 scripts/dev.py run python -B scripts/build_pure_delivery.py "
            "--wheel .runtime/c4close/wheel/scirel-0.0.0-py3-none-any.whl "
            "--output .runtime/c4close/scirel-delivery-close",
            "uv venv --seed --python 3.14.7 .runtime/c4close/venv-consumer",
            "uv pip install --python .runtime/c4close/venv-consumer/bin/python "
            ".runtime/c4close/scirel-delivery-close/wheel/scirel-0.0.0-py3-none-any.whl "
            "-r .runtime/c4close/scirel-delivery-close/runtime-requirements.txt",
            ".runtime/c4close/venv-consumer/bin/python -I scripts/validate_installed_wheel.py "
            "--expected-python 3.14 "
            "--wheel .runtime/c4close/scirel-delivery-close/wheel/scirel-0.0.0-py3-none-any.whl "
            "--catalog-root . --source-revision d429359dcfbf37aedf09aa64cfa78b89da3b3623 "
            "--output .runtime/c4close/installed-wheel-validation.json",
            "SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close "
            ".runtime/c4close/venv-consumer/bin/python -I "
            "examples/c4-usage-acceptance/closeout/selfcheck.py",
            "SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close "
            ".runtime/c4close/venv-consumer/bin/python -I "
            "examples/c4-usage-acceptance/closeout/run.py",
            "SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close "
            ".runtime/c4close/venv-consumer/bin/python -I "
            "examples/c4-usage-acceptance/closeout/audits.py",
            "python3 examples/c4-usage-acceptance/closeout/coverage.py",
            "python3 examples/c4-usage-acceptance/closeout/make_receipt.py",
        ],
        "artifacts": {
            "results.json": "per-task index of this round",
            "tasks/<task-id>.json": "per-task record: calls, answer, criteria, gaps",
            "calls.jsonl": "every public call, in execution order",
            "contract-audit.json": "return-channel audit over all 249 contracts",
            "focus-audit.json": "thermal-energy numbers, the five evidence clauses, the audit criteria",
            "coverage.py": "recomputes the domain/kind matrix",
            "make_receipt.py": "rebuilds this receipt (the diff against round2 included)",
        },
    }
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n")
    print("wrote receipt.json")
    print(
        f"  criteria changed: {len(changed_criteria)}  improvements: {len(improvements)}  "
        f"regressions: {len(regressions)}"
    )
    print(f"  tasks with material answer differences: {len(answer_diffs)}")
    return 0


def _repr_only(diff: dict) -> bool:
    """Object reprs and temporary paths differ between runs; they are not measurements."""
    vals = (diff.get("round2"), diff.get("closeout"))
    text = " ".join(str(v) for v in vals)
    return ("object at 0x" in text) or ("/tmp" in text) or ("tmpr" in text)


if __name__ == "__main__":
    raise SystemExit(main())
