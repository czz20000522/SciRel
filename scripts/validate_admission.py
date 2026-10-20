"""Validate one FINAL submission against SciRel's admission standard.

The admission standard is the only external interaction surface: a submission
is a decomposition/FINAL directory whose control files bind each other and
whose payload bytes match the manifest. This validator does not judge science,
does not read D0-D3 packages and does not record overlap or merge decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FINAL_SCHEMA = ROOT / "contracts" / "admission" / "project-final.schema.json"
FILES_SCHEMA = ROOT / "contracts" / "admission" / "files.schema.json"
BOUND = ("FINAL.json", "FILES.json", "PATH_MAP.json")
ROOT_BINDING = "ROOT.sha256"
FINAL_KEYS = {
    "schema", "project_id", "decomposition_scope", "limitations",
    "claim_ceiling", "files", "path_map", "root_binding", "payload_files",
    "payload_bytes", "evidence_policy", "custody_note", "license",
    "identity", "stage_evidence", "capabilities", "functions", "compositions",
    "platform_boundaries",
}
_REQUIRED = (
    "schema", "project_id", "decomposition_scope", "limitations",
    "claim_ceiling", "files", "path_map", "root_binding", "payload_files",
    "payload_bytes", "evidence_policy", "custody_note", "license",
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(path: str, errors: list[str], where: str) -> bool:
    if not isinstance(path, str) or not path:
        errors.append(f"{where}: path must be a non-empty string")
        return False
    if "\\" in path or path.startswith("/") or path.startswith("./"):
        errors.append(f"{where}: path must be a relative POSIX path: {path!r}")
        return False
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        errors.append(f"{where}: path contains an empty/dot/.. segment: {path!r}")
        return False
    return True


def _check_final(final: dict, errors: list[str]) -> None:
    if not isinstance(final, dict):
        errors.append("FINAL.json: expected an object")
        return
    unknown = sorted(set(final) - FINAL_KEYS)
    if unknown:
        errors.append(f"FINAL.json: unknown properties {unknown}")
    if "schema_version" in final:
        errors.append("FINAL.json: schema_version is not allowed; the contract has no version suffix")
    for key in _REQUIRED:
        if key not in final:
            errors.append(f"FINAL.json: missing {key}")
    if final.get("schema") != "scirel.project-final":
        errors.append("FINAL.json: schema must be scirel.project-final")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(final.get("project_id", ""))):
        errors.append("FINAL.json: project_id must be lowercase kebab-case")
    for key in ("decomposition_scope", "claim_ceiling", "evidence_policy", "custody_note"):
        if not isinstance(final.get(key), str) or not final.get(key):
            errors.append(f"FINAL.json: {key} must be a non-empty string")
    limitations = final.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(
            isinstance(item, str) and item for item in limitations):
        errors.append("FINAL.json: limitations must be a non-empty list of strings")
    if final.get("files") != "FILES.json":
        errors.append("FINAL.json: files must be FILES.json")
    if final.get("path_map") != "PATH_MAP.json":
        errors.append("FINAL.json: path_map must be PATH_MAP.json")
    if final.get("root_binding") != ROOT_BINDING:
        errors.append(f"FINAL.json: root_binding must be {ROOT_BINDING}")
    for key in ("payload_files", "payload_bytes"):
        value = final.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"FINAL.json: {key} must be a positive integer")
    license_ = final.get("license")
    if not isinstance(license_, dict):
        errors.append("FINAL.json: license must be an object")
    else:
        if set(license_) != {"spdx", "references"}:
            errors.append("FINAL.json: license must contain exactly spdx and references")
        if not isinstance(license_.get("spdx"), str) or not license_.get("spdx"):
            errors.append("FINAL.json: license.spdx must be a non-empty string")
        refs = license_.get("references")
        if not isinstance(refs, list) or not refs or not all(
                isinstance(item, str) and item for item in refs):
            errors.append("FINAL.json: license.references must be a non-empty string list")
    for key in ("identity", "stage_evidence"):
        if key in final and not isinstance(final[key], dict):
            errors.append(f"FINAL.json: {key} must be an object of strings")
    for key in ("capabilities", "functions", "platform_boundaries"):
        if key in final and (not isinstance(final[key], list)
                             or not all(isinstance(item, str) and item for item in final[key])):
            errors.append(f"FINAL.json: {key} must be a list of strings")
    compositions = final.get("compositions")
    if compositions is not None:
        if not isinstance(compositions, list):
            errors.append("FINAL.json: compositions must be a list")
        else:
            for item in compositions:
                if not isinstance(item, dict) or set(item) != {"directory", "name"}:
                    errors.append("FINAL.json: compositions entries need exactly directory and name")
                elif not all(isinstance(item[key], str) and item[key] for key in item):
                    errors.append("FINAL.json: compositions entries need non-empty strings")


def _check_files(manifest: dict, final_dir: Path, errors: list[str]) -> list[dict]:
    if not isinstance(manifest, dict):
        errors.append("FILES.json: expected an object")
        return []
    if manifest.get("schema") != "scirel.final-files":
        errors.append("FILES.json: schema must be scirel.final-files")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        errors.append("FILES.json: files must be a non-empty array")
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"FILES.json: files[{index}] must be an object")
            continue
        if set(entry) != {"path", "bytes", "sha256"}:
            errors.append(f"FILES.json: files[{index}] must contain exactly path/bytes/sha256")
            continue
        path = entry["path"]
        if not _safe_relative(path, errors, f"FILES.json: files[{index}]"):
            continue
        if path in seen:
            errors.append(f"FILES.json: duplicate path {path}")
        seen.add(path)
        ordered.append(path)
        size = entry["bytes"]
        digest = entry["sha256"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append(f"FILES.json: {path}: bytes must be a non-negative integer")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"FILES.json: {path}: sha256 must be 64 lowercase hex characters")
    if ordered != sorted(ordered):
        errors.append("FILES.json: members must be sorted by case-sensitive POSIX path")
    if "FINAL.json" not in seen:
        errors.append("FILES.json: FINAL.json must be a member")
    if "PATH_MAP.json" not in seen:
        errors.append("FILES.json: PATH_MAP.json must be a member")
    for forbidden in ("FILES.json", ROOT_BINDING):
        if forbidden in seen:
            errors.append(f"FILES.json: {forbidden} is bound by ROOT.sha256, not a member")
    return entries


def _check_payload(entries: list[dict], final_dir: Path, errors: list[str]) -> int:
    total = 0
    for entry in entries:
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            continue
        target = final_dir / path
        if not target.is_file():
            errors.append(f"payload missing: {path}")
            continue
        actual_bytes = target.stat().st_size
        if actual_bytes != entry.get("bytes"):
            errors.append(f"payload size mismatch: {path}: {actual_bytes} != {entry.get('bytes')}")
        actual_sha = _sha(target)
        if actual_sha != entry.get("sha256"):
            errors.append(f"payload digest mismatch: {path}")
        total += actual_bytes
    return total


def _check_root(final_dir: Path, errors: list[str]) -> None:
    root = final_dir / ROOT_BINDING
    if not root.is_file():
        errors.append("ROOT.sha256: missing")
        return
    lines = root.read_text(encoding="utf-8").splitlines()
    if not lines:
        errors.append("ROOT.sha256: empty")
        return
    expected = [f"{_sha(final_dir / name)}  {name}" for name in BOUND]
    if lines[0] != f"{hashlib.sha256((''.join(line + '\n' for line in expected)).encode()).hexdigest()}  {ROOT_BINDING}":
        errors.append("ROOT.sha256: root digest does not match the bound files")
    if lines[1:] != expected:
        errors.append("ROOT.sha256: bound lines do not match the three control files")
    if not root.read_text(encoding="utf-8").endswith("\n"):
        errors.append("ROOT.sha256: must end with a newline")


def _emit_root(final_dir: Path) -> None:
    lines = [f"{_sha(final_dir / name)}  {name}" for name in BOUND]
    digest = hashlib.sha256(("".join(line + "\n" for line in lines)).encode()).hexdigest()
    (final_dir / ROOT_BINDING).write_text(
        f"{digest}  {ROOT_BINDING}\n" + "".join(line + "\n" for line in lines),
        encoding="utf-8")


def validate(final_dir: Path, *, emit_root: bool = False) -> dict:
    report = {"directory": str(final_dir), "status": "PASS", "errors": [], "warnings": [],
              "checks": {}}
    if not final_dir.is_dir():
        report["status"] = "NOT_RUN"
        report["errors"].append("FINAL directory does not exist")
        return report
    if emit_root:
        _emit_root(final_dir)
        report["checks"]["emit_root"] = "WROTE"
    missing = [name for name in ("FINAL.json", "FILES.json", "PATH_MAP.json") if not (final_dir / name).is_file()]
    if missing:
        report["status"] = "NOT_RUN"
        report["errors"].append(f"required control file(s) missing: {missing}")
        return report
    try:
        final = json.loads((final_dir / "FINAL.json").read_text(encoding="utf-8"))
        manifest = json.loads((final_dir / "FILES.json").read_text(encoding="utf-8"))
        path_map = json.loads((final_dir / "PATH_MAP.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        report["status"] = "FAIL"
        report["errors"].append(f"cannot parse control files: {exc}")
        return report
    errors: list[str] = []
    _check_final(final, errors)
    entries = _check_files(manifest, final_dir, errors)
    paths = {entry.get("path") for entry in entries if isinstance(entry, dict)}
    if isinstance(final, dict):
        if final.get("payload_files") != len(entries):
            errors.append(f"FINAL.json: payload_files={final.get('payload_files')} but FILES.json has {len(entries)}")
        total = _check_payload(entries, final_dir, errors)
        if final.get("payload_bytes") != total:
            errors.append(f"FINAL.json: payload_bytes={final.get('payload_bytes')} but payload sums to {total}")
        license_ = final.get("license")
        if isinstance(license_, dict):
            for reference in license_.get("references", []):
                if reference not in paths:
                    errors.append(f"FINAL.json: license reference is not a FILES member: {reference}")
        for key, value in (final.get("stage_evidence") or {}).items():
            if value not in paths:
                errors.append(f"FINAL.json: stage_evidence.{key} is not a FILES member: {value}")
    if not isinstance(path_map, dict):
        errors.append("PATH_MAP.json: expected an object")
    _check_root(final_dir, errors)
    report["errors"].extend(errors)
    report["checks"]["payload_files"] = len(entries)
    report["status"] = "PASS" if not errors else "FAIL"
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("final", type=Path)
    parser.add_argument("--emit-root", action="store_true",
                        help="write ROOT.sha256 from the current control files, then validate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = validate(args.final, emit_root=args.emit_root)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["status"] == "PASS" else (2 if report["status"] == "NOT_RUN" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
