"""Coverage matrix for one round-2 run.

Reads ``results.json`` (written by ``run.py``) plus the frozen task list and prints, per
domain, how many tasks were executed, how many the package alone could complete and how
many criteria passed / failed / were not evaluated.  Also prints the cross-domain and
failure-path blocks, which are the two coverage axes #249 names explicitly.

    python -I examples/c4-usage-acceptance/round2/coverage.py [--json]
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKLIST = json.loads((HERE.parent / "tasklist.json").read_text())


def build() -> dict:
    results = json.loads((HERE / "results.json").read_text())
    rows = {r["task_id"]: r for r in results["tasks"]}
    tasks = TASKLIST["tasks"]
    by_domain = defaultdict(
        lambda: {
            "nominal": 0,
            "failure": 0,
            "inapplicable": 0,
            "cross": 0,
            "ran": 0,
            "sufficient": 0,
            "criteria": 0,
            "pass": 0,
            "fail": 0,
            "not_run": 0,
            "tasks": [],
        }
    )
    for t in tasks:
        d = by_domain[t["domain"]]
        d[t["kind"]] += 1
        r = rows.get(t["id"], {})
        if r.get("status") == "missing" or not r:
            d["tasks"].append({"task": t["id"], "ran": False})
            continue
        d["ran"] += 1
        d["sufficient"] += 1 if r.get("package_sufficient") else 0
        d["criteria"] += r.get("criteria_total", 0)
        d["pass"] += r.get("criteria_pass", 0)
        d["fail"] += r.get("criteria_fail", 0)
        d["not_run"] += r.get("criteria_not_run", 0)
        d["tasks"].append(
            {
                "task": t["id"],
                "kind": t["kind"],
                "ran": True,
                "package_sufficient": r.get("package_sufficient"),
                "criteria": [r.get("criteria_pass"), r.get("criteria_total")],
            }
        )
    kinds = defaultdict(lambda: {"ran": 0, "sufficient": 0})
    for t in tasks:
        r = rows.get(t["id"], {})
        kinds[t["kind"]]["ran"] += 1 if r and r.get("status") != "missing" else 0
        kinds[t["kind"]]["sufficient"] += 1 if r and r.get("package_sufficient") else 0
    return {
        "schema": "scirel.c4-usage-round2.coverage",
        "domains": {k: by_domain[k] for k in sorted(by_domain)},
        "kinds": dict(kinds),
        "totals": results["summary"],
        "package": results["package"],
        "child_failures": results.get("child_failures", []),
    }


def render(cov: dict) -> str:
    lines = ["domain            tasks  ran  sufficient  criteria(pass/total)  fail  not-run"]
    for dom, d in cov["domains"].items():
        lines.append(
            f"{dom:<17} {d['nominal'] + d['failure'] + d['inapplicable'] + d['cross']:>4} "
            f"{d['ran']:>4} {d['sufficient']:>10} "
            f"{d['pass']:>10}/{d['criteria']:<10} {d['fail']:>5} {d['not_run']:>7}"
        )
    lines.append("")
    lines.append("kind            ran  sufficient")
    for kind, k in cov["kinds"].items():
        lines.append(f"{kind:<14} {k['ran']:>4} {k['sufficient']:>11}")
    t = cov["totals"]
    lines.append("")
    lines.append(
        f"TOTAL tasks={t['tasks']} sufficient={t['package_sufficient']} "
        f"insufficient={t['package_insufficient']} criteria={t['criteria_total']} "
        f"pass={t['criteria_pass']} fail={t['criteria_fail']} not-run={t['criteria_not_run']}"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    cov = build()
    if "--json" in sys.argv:
        print(json.dumps(cov, indent=1, ensure_ascii=False))
    else:
        print(render(cov))
