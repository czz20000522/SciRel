"""Validate the public admission format; PASS never means scientific acceptance.

The schema reader implements only the explicitly supported keywords used by the
live admission schemas. Unknown keywords fail closed; this is not a general
JSON Schema engine. Validation never imports or executes payload code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
FINAL_SCHEMA = ROOT / "contracts/admission/project-final.schema.json"
FILES_SCHEMA = ROOT / "contracts/admission/files.schema.json"
PATH_MAP_SCHEMA = ROOT / "contracts/admission/path-map.schema.json"
BOUND = ("FINAL.json", "FILES.json", "PATH_MAP.json")
ROOT_BINDING = "ROOT.sha256"
CONTROLS = frozenset((*BOUND, ROOT_BINDING))
DERIVED_KEYS = frozenset(("schema", "files", "path_map", "root_binding", "payload_files", "payload_bytes"))
_KEYWORDS = frozenset(("$schema", "$id", "title", "description", "type", "const",
                       "required", "properties", "additionalProperties", "propertyNames",
                       "items", "minItems", "minLength", "minimum", "pattern"))
_TYPES = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
          "string": lambda v: isinstance(v, str),
          "integer": lambda v: (isinstance(v, int) and not isinstance(v, bool))
          or (isinstance(v, float) and v.is_integer())}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"non-JSON numeric constant: {value}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object,
                      parse_constant=_invalid_constant)


def _safe_relative(path: str, errors: list[str], where: str) -> bool:
    if not isinstance(path, str) or not path:
        errors.append(f"{where}: path must be a non-empty string")
        return False
    parts = path.split("/")
    invalid = ("\\" in path or any(c in '<>:"|?*' for c in path) or path.startswith("/")
               or any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in path)
               or any(p in {"", ".", ".."} or p.endswith((".", " ")) for p in parts)
               or any(re.fullmatch(r"(?i:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])", p.split(".")[0]) for p in parts))
    if invalid:
        errors.append(f"{where}: unsafe relative POSIX path: {path!r}")
        return False
    return True


def check_ancestors(path: Path, errors: list[str]) -> None:
    # Inspect lexical ancestors before resolve(), so a junction cannot disappear
    # from the checks by resolving its destination first.
    absolute = path.absolute()
    for current in reversed((absolute, *absolute.parents)):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            errors.append(f"links/reparse points are forbidden: {current}")
            return


def inspect_tree(directory: Path, errors: list[str]) -> tuple[dict[str, Path], set[str]]:
    check_ancestors(directory, errors)
    if errors:
        return {}, set()
    if not directory.is_dir():
        errors.append(f"not a directory: {directory}")
        return {}, set()
    files = {}
    stored = set()
    folded = set()
    for parent, dirs, names in os.walk(directory, followlinks=False, onerror=lambda e: errors.append(str(e))):
        for name in sorted(dirs + names):
            target = Path(parent) / name
            relative = target.relative_to(directory).as_posix()
            info = target.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                errors.append(f"links/reparse points are forbidden: {relative}")
                if name in dirs:
                    dirs.remove(name)
                continue
            if not _safe_relative(relative, errors, "stored member"):
                continue
            if relative.casefold() in folded:
                errors.append(f"portable path collision: {relative}")
            folded.add(relative.casefold())
            stored.add(relative)
            if stat.S_ISREG(info.st_mode):
                if info.st_nlink > 1:
                    errors.append(f"hardlinked member is forbidden: {relative}")
                files[relative] = target
            elif not stat.S_ISDIR(info.st_mode):
                errors.append(f"non-regular member: {relative}")
    return files, stored


def _schema_definition(schema, where: str) -> None:
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ValueError(f"{where}: schema must be an object or boolean")
    unknown = set(schema) - _KEYWORDS
    if unknown:
        raise ValueError(f"{where}: unsupported schema keywords: {sorted(unknown)}")
    if "type" in schema and schema["type"] not in _TYPES:
        raise ValueError(f"{where}: unsupported schema type")
    if "pattern" in schema:
        re.compile(schema["pattern"])
    for key, child in schema.get("properties", {}).items():
        _schema_definition(child, f"{where}.{key}")
    for key in ("additionalProperties", "propertyNames", "items"):
        if key in schema:
            _schema_definition(schema[key], f"{where}.{key}")


def _schema_value(value, schema, errors: list[str], where: str) -> None:
    if schema is True:
        return
    if schema is False:
        errors.append(f"{where}: not permitted by schema")
        return
    if "type" in schema and not _TYPES[schema["type"]](value):
        errors.append(f"{where}: expected {schema['type']}")
        return
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(f"{where}: must equal {schema['const']!r}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing {key}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if "propertyNames" in schema:
                _schema_value(key, schema["propertyNames"], errors, f"{where} key {key!r}")
            if key in properties:
                _schema_value(item, properties[key], errors, f"{where}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{where}: unknown property {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                _schema_value(item, schema["additionalProperties"], errors, f"{where}.{key}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: requires at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(value):
                _schema_value(item, schema["items"], errors, f"{where}[{index}]")
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: string is too short")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{where}: string does not match schema pattern")
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{where}: below minimum {schema['minimum']}")


def check_schema(value, schema_path: Path, errors: list[str], where: str) -> None:
    schema = read_json(schema_path)
    _schema_definition(schema, str(schema_path))
    _schema_value(value, schema, errors, where)


def _check_final(final, errors: list[str]) -> None:
    check_schema(final, FINAL_SCHEMA, errors, "FINAL.json")


def check_references(final: dict, members: set[str], errors: list[str]) -> None:
    for reference in final["license"]["references"]:
        if _safe_relative(reference, errors, "license reference") and reference not in members:
            errors.append(f"FINAL.json: license reference is not a FILES member: {reference}")
    for key, value in final.get("stage_evidence", {}).items():
        if _safe_relative(value, errors, f"stage_evidence.{key}") and value not in members:
            errors.append(f"FINAL.json: stage_evidence.{key} is not a FILES member: {value}")
    for item in final.get("compositions", []):
        _safe_relative(item["directory"], errors, "composition directory")


def check_path_map(mapping, members: set[str], stored: set[str], errors: list[str]) -> None:
    check_schema(mapping, PATH_MAP_SCHEMA, errors, "PATH_MAP.json")
    if not isinstance(mapping, dict):
        return
    aliases = set(mapping)
    occupied = {p.casefold() for p in stored | set(CONTROLS)}
    file_paths = {p.casefold() for p in members | set(CONTROLS)}
    alias_paths = {p.casefold() for p in aliases}
    folded = set()
    for alias, target in mapping.items():
        if not _safe_relative(alias, errors, "PATH_MAP alias"):
            continue
        if not _safe_relative(target, errors, f"PATH_MAP target for {alias}"):
            continue
        if alias.casefold() in occupied or alias.casefold() in folded:
            errors.append(f"PATH_MAP.json: alias collides with a stored member/alias: {alias}")
        folded.add(alias.casefold())
        if any(alias.casefold().startswith(p + "/") for p in file_paths):
            errors.append(f"PATH_MAP.json: alias is nested under a stored file: {alias}")
        if any(alias.casefold().startswith(p + "/") for p in alias_paths):
            errors.append(f"PATH_MAP.json: alias is nested under another file alias: {alias}")
        if alias == target or target in aliases:
            errors.append(f"PATH_MAP.json: identity mapping/alias chain is forbidden: {alias}")
        if target in CONTROLS or target not in members:
            errors.append(f"PATH_MAP.json: target must be a directly stored non-control FILES member: {target}")


def root_bytes(final_dir: Path) -> bytes:
    lines = b"".join(f"{_sha(final_dir / name)}  {name}\n".encode("utf-8") for name in BOUND)
    return f"{hashlib.sha256(lines).hexdigest()}  {ROOT_BINDING}\n".encode("ascii") + lines


def _emit_root(final_dir: Path) -> None:
    errors = []
    files, _ = inspect_tree(final_dir, errors)
    if not all(name in files for name in BOUND):
        errors.append("required controls missing before ROOT emission")
    if errors:
        raise ValueError("; ".join(errors))
    (final_dir / ROOT_BINDING).write_bytes(root_bytes(final_dir))


def validate(final_dir: Path, *, emit_root: bool = False) -> dict:
    final_dir = Path(final_dir)
    report = {"directory": str(final_dir), "status": "FAIL", "errors": [], "warnings": [], "checks": {}}
    errors = report["errors"]
    try:
        check_ancestors(final_dir, errors)
        if errors:
            return report
        if not final_dir.is_dir():
            report["status"] = "NOT_RUN"
            errors.append("FINAL directory does not exist or is not a directory")
            return report
        files, stored = inspect_tree(final_dir, errors)
        if errors:
            return report
        missing = [name for name in BOUND if name not in files]
        if missing:
            report["status"] = "NOT_RUN"
            errors.append(f"required control file(s) missing: {missing}")
            return report
        final, manifest, mapping = [read_json(final_dir / name) for name in BOUND]
        if mapping == {} and (final_dir / "PATH_MAP.json").read_bytes() != b"{}\n":
            errors.append("PATH_MAP.json: empty object must be exactly b'{}\\n'")
        _check_final(final, errors)
        check_schema(manifest, FILES_SCHEMA, errors, "FILES.json")
        if errors:
            return report
        entries = manifest["files"]
        paths = []
        for entry in entries:
            if _safe_relative(entry["path"], errors, "FILES member"):
                paths.append(entry["path"])
        if errors:
            return report  # Never open a manifest path until every path is safe.
        members = set(paths)
        if paths != sorted(paths):
            errors.append("FILES.json: members must be sorted by case-sensitive POSIX path")
        if len(members) != len(paths):
            errors.append("FILES.json: duplicate path")
        if not {"FINAL.json", "PATH_MAP.json"} <= members:
            errors.append("FILES.json: FINAL.json and PATH_MAP.json must be members")
        if members & {"FILES.json", ROOT_BINDING}:
            errors.append("FILES.json: FILES.json/ROOT.sha256 are outer-bound controls, not members")
        actual_members = set(files) - {"FILES.json", ROOT_BINDING}
        if members != actual_members:
            errors.append(f"FILES.json: missing/unlisted members: missing={sorted(members - actual_members)}, unlisted={sorted(actual_members - members)}")
        total = 0
        for entry in entries:
            target = files.get(entry["path"])
            if target is None:
                continue
            size = target.stat().st_size
            total += size
            if size != entry["bytes"]:
                errors.append(f"payload size mismatch: {entry['path']}")
            if _sha(target) != entry["sha256"]:
                errors.append(f"payload digest mismatch: {entry['path']}")
        if final["payload_files"] != len(entries):
            errors.append("FINAL.json: payload_files does not match FILES member count")
        if final["payload_bytes"] != total:
            errors.append("FINAL.json: payload_bytes does not match FILES byte sum")
        check_references(final, members, errors)
        check_path_map(mapping, members, stored, errors)
        if emit_root and not errors:
            _emit_root(final_dir)
            report["checks"]["emit_root"] = "WROTE"
        if ROOT_BINDING not in files and not (emit_root and not errors):
            errors.append("ROOT.sha256: missing")
        elif (final_dir / ROOT_BINDING).read_bytes() != root_bytes(final_dir):
            errors.append("ROOT.sha256: bytes do not match fixed FINAL/FILES/PATH_MAP LF binding")
        report["checks"].update(payload_files=len(entries), payload_bytes=total)
        report["status"] = "FAIL" if errors else "PASS"
    except (OSError, ValueError, TypeError, KeyError, RecursionError, re.error) as exc:
        errors.append(f"cannot validate admission: {type(exc).__name__}: {exc}")
    return report


def exit_code(report: dict) -> int:
    return {"PASS": 0, "FAIL": 1, "NOT_RUN": 2}[report["status"]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("final", type=Path)
    parser.add_argument("--emit-root", action="store_true", help="explicitly produce ROOT after checking safe controls and all members")
    parser.add_argument("--output", type=Path, help="machine report outside the package")
    args = parser.parse_args(argv)
    output_errors = []
    if args.output:
        try:
            check_ancestors(args.output, output_errors)
            if args.output.resolve().is_relative_to(args.final.resolve()):
                output_errors.append("report output must be outside the package")
            if args.output.exists():
                info = args.output.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
                    output_errors.append("report output must be an ordinary unshared file")
        except (OSError, ValueError) as exc:
            output_errors.append(str(exc))
    if output_errors:
        report = {"directory": str(args.final), "status": "FAIL", "errors": output_errors}
    else:
        report = validate(args.final, emit_root=args.emit_root)
        if args.output:
            try:
                args.output.write_bytes(json_bytes(report))
            except (OSError, ValueError) as exc:
                report["status"] = "FAIL"
                report["errors"].append(f"cannot write report: {exc}")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
