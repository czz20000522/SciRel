#!/usr/bin/env python3
"""Audit every project's FINAL against SciRel's admission standard.

`validate_final.py` judges one submission. This walks a projects root and reports
the whole corpus, because the useful question on the decomposition side is
"which of my deliveries would be admitted today", not "is torax valid".

It refuses to be the authority. Judgement is delegated to validate_final.py,
which mirrors SciRel @ the commit recorded in the report, so a corpus result
always carries the standard it was measured against.

Usage:
  audit_finals.py <projects root> [--json report.json] [--summary summary.json]
                  [--max-errors N] [--payload]

Exit codes: 0 every FINAL passes; 1 at least one fails; 2 nothing was auditable.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
DEFAULT_MAX_ERRORS = 6

STATUS_LABEL = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "NOT_RUN": "NOT RUN",
}


def _load_validator():
    target = _HERE / "validate_final.py"
    spec = importlib.util.spec_from_file_location("_vf", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_finals(root: Path) -> list[Path]:
    """Return every decomposition/FINAL directory under root, sorted."""
    return sorted(
        path for path in root.glob("*/decomposition/FINAL") if path.is_dir()
    )


def audit_one(final_dir: Path, validator, max_errors: int) -> dict:
    record: dict = {
        "project": final_dir.parent.parent.name,
        "directory": str(final_dir),
    }
    if not final_dir.is_dir():
        record.update(status="NOT_RUN", detail="FINAL directory does not exist")
        return record
    has_final = (final_dir / "FINAL.json").is_file()
    if not has_final:
        members = sum(1 for path in final_dir.rglob("*") if path.is_file())
        record.update(
            status="NOT_RUN",
            detail=(
                "no FINAL.json: the directory has payload bytes "
                f"({members} files) but no authoritative manifest, so there is "
                "nothing to admit and nothing to compare"
            ),
        )
        return record
    try:
        report = validator.validate(final_dir)
    except Exception as exc:  # a validator crash is a corpus finding, not a stop
        record.update(status="ERROR", detail=f"{type(exc).__name__}: {exc}")
        return record
    errors = report.get("errors", [])
    record["status"] = report.get("status", "FAIL")
    record["error_count"] = len(errors)
    record["errors"] = errors[:max_errors]
    if len(errors) > max_errors:
        record["errors_truncated"] = len(errors) - max_errors
    record["payload_files"] = report.get("checks", {}).get("payload_files")
    return record


def build_report(root: Path, *, max_errors: int = DEFAULT_MAX_ERRORS) -> dict:
    validator = _load_validator()
    finals = find_finals(root)
    records = [audit_one(final_dir, validator, max_errors) for final_dir in finals]
    counts = {"finals": len(records), "pass": 0, "fail": 0, "not_run": 0, "error": 0}
    for record in records:
        key = {"PASS": "pass", "FAIL": "fail",
               "NOT_RUN": "not_run"}.get(record["status"], "error")
        counts[key] += 1
    no_manifest = [r["project"] for r in records
                   if r["status"] == "NOT_RUN" and "no FINAL.json" in r.get("detail", "")]
    return {
        "root": str(root),
        "standard": "scirel.project-final",
        "mirrored_upstream_commit": validator.MIRRORED_UPSTREAM_COMMIT,
        "counts": counts,
        "projects_without_final_json": no_manifest,
        "projects": records,
        "note": (
            "A PASS is a structural and byte-level result. It does not mean the "
            "science is accepted, the retained scope is right, or the payload is "
            "the core 10-20%."
        ),
    }


def render(report: dict) -> str:
    counts = report["counts"]
    lines = [
        f"standard: scirel.project-final  (mirror of SciRel @ "
        f"{report['mirrored_upstream_commit']})",
        "",
        f"{'project':<14} {'status':<9} {'files':>7}  detail",
        "-" * 72,
    ]
    for record in report["projects"]:
        files = record.get("payload_files")
        files_text = str(files) if files is not None else "-"
        if record["status"] == "PASS":
            detail = "admissible"
        elif "no FINAL.json" in record.get("detail", ""):
            detail = "no manifest"
        else:
            detail = f"{record.get('error_count', '?')} error(s)"
        lines.append(
            f"{record['project']:<14} {STATUS_LABEL.get(record['status'], record['status']):<9} "
            f"{files_text:>7}  {detail}"
        )
    lines.append("-" * 72)
    lines.append(
        f"{counts['finals']} FINAL dirs | {counts['pass']} pass | "
        f"{counts['fail']} fail | {counts['not_run']} not run | "
        f"{counts['error']} error"
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--max-errors", type=int, default=DEFAULT_MAX_ERRORS)
    args = parser.parse_args(argv)
    report = build_report(args.root, max_errors=args.max_errors)
    print(render(report))
    if args.json:
        args.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if args.summary:
        args.summary.write_text(
            json.dumps({"counts": report["counts"],
                        "mirrored_upstream_commit": report["mirrored_upstream_commit"],
                        "projects_without_final_json": report["projects_without_final_json"]},
                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = report["counts"]
    if counts["finals"] == 0:
        return 2
    return 0 if counts["pass"] == counts["finals"] else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
