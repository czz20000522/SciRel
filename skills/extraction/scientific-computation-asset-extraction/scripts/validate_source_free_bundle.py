from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FORMAL_DIRS = {"operators", "task_graphs"}
PROJECT_DIRS = {"docker"}
PROJECT_FILES = {
    "extraction_ledger.md",
    "extraction_report.md",
    "program_framework_map.md",
}
OPTIONAL_ROOT_DIRS = {"configs"}
OPTIONAL_ROOT_FILES = {"asset_entry.py"}
SOURCE_SUFFIXES = {
    ".f",
    ".for",
    ".f77",
    ".f90",
    ".f95",
    ".f03",
    ".f08",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".inc",
}
CACHE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    ".cache",
}
SOURCE_DIRS = {
    "original",
    "original_source",
    "source",
    "sources",
    "source_snapshot",
    "src",
    "upstream",
    "work",
    "workcopy",
}
EVIDENCE_DIRS = {"validation_harnesses", "validation", "probes", "golden"}
EVIDENCE_NAME_RE = re.compile(
    r"(?:validation|probe|oracle|golden|replay|gate|验证|探针|预言|金标准|重放|门禁)",
    re.IGNORECASE,
)
EVIDENCE_SUFFIXES = {".json", ".log", ".out", ".nc", ".csv"}
ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users|mnt|opt|tmp|var|srv|workspace|workspaces|root|data)/)[^\s`\"'<>]+"
)
QUOTED_PATH_RE = re.compile(r"(?P<quote>[\"'`])(?P<value>[^\"'`\r\n]+)(?P=quote)")
SOURCE_PATH_SUFFIXES = {
    ".f", ".for", ".f77", ".f90", ".f95", ".f03", ".f08",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".inc", ".py",
}
PATH_SCAN_SUFFIXES = {".py", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".yaml", ".yml", ".json", ".toml"}
# Bare absolute paths are meaningful in structured configuration.  In source
# code, scan quoted values below so comments and escaped regexes cannot look
# like host dependencies.
ABSOLUTE_SCAN_SUFFIXES = {".yaml", ".yml", ".json", ".toml"}


def validate_source_free_bundle(
    root: Path,
    *,
    evidence_root: Path | None = None,
    expected_digest: str | None = None,
    require_docker: bool = False,
    standalone_kind: str | None = None,
) -> dict[str, Any]:
    if standalone_kind is not None:
        return _validate_standalone_bundle(
            root,
            kind=standalone_kind,
            evidence_root=evidence_root,
            expected_digest=expected_digest,
        )
    errors: list[str] = []
    if not root.exists():
        return {"valid": False, "errors": [f"root does not exist: {root}"]}
    if not root.is_dir():
        return {"valid": False, "errors": [f"root is not a directory: {root}"]}

    root_entries = {path.name for path in root.iterdir()}
    for required in sorted(FORMAL_DIRS):
        if not (root / required).is_dir():
            errors.append(f"formal bundle requires directory: {required}")
    allowed_root_dirs = FORMAL_DIRS | PROJECT_DIRS | OPTIONAL_ROOT_DIRS
    for entry in sorted(root_entries):
        if entry in allowed_root_dirs or entry in OPTIONAL_ROOT_FILES:
            continue
        if entry in PROJECT_FILES:
            continue
        errors.append(f"unexpected root entry in formal bundle: {entry}")
    for project_file in sorted(PROJECT_FILES):
        if not (root / project_file).is_file():
            errors.append(f"formal bundle requires project sidecar: {project_file}")
    docker_root = root / "docker"
    if require_docker and not docker_root.is_dir():
        errors.append("project bundle requires Docker configuration directory: docker")
    docker_files = (
        sorted(path.relative_to(root).as_posix() for path in docker_root.rglob("*") if path.is_file())
        if docker_root.is_dir()
        else []
    )
    if docker_root.is_dir() and not docker_files:
        errors.append("Docker configuration directory is empty: docker")

    source_files: list[str] = []
    cache_paths: list[str] = []
    source_dirs: list[str] = []
    mixed_evidence: list[str] = []
    external_path_references: list[str] = []
    symlink_paths: list[str] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        parts = {part.casefold() for part in path.relative_to(root).parts}
        if path.is_symlink():
            symlink_paths.append(rel)
            continue
        if path.is_dir():
            if parts.intersection(CACHE_DIRS):
                cache_paths.append(rel)
            if path.name.casefold() in SOURCE_DIRS:
                source_dirs.append(rel)
            if path.name.casefold() in EVIDENCE_DIRS:
                mixed_evidence.append(rel)
            continue
        if (
            path.suffix.casefold() in SOURCE_SUFFIXES
            and not _is_c_profile_asset(path, root=root)
        ):
            source_files.append(rel)
        if path.suffix.casefold() == ".py" and not _is_python_asset(path, root=root):
            source_files.append(rel)
        if path.name.casefold() in CACHE_DIRS:
            cache_paths.append(rel)
        if (
            path.suffix.casefold() in EVIDENCE_SUFFIXES
            and EVIDENCE_NAME_RE.search(path.stem)
            and "docker" not in parts
        ) or "validation_harnesses" in parts:
            mixed_evidence.append(rel)
    for rel in source_files:
        errors.append(f"source-language file inside formal bundle: {rel}")
    for rel in sorted(set(cache_paths)):
        errors.append(f"cache/generated directory inside formal bundle: {rel}")
    for rel in sorted(set(source_dirs)):
        errors.append(f"source/work directory inside formal bundle: {rel}")
    for rel in sorted(set(mixed_evidence)):
        errors.append(f"validation evidence mixed into formal bundle: {rel}")
    external_path_references = _find_external_path_references(root)
    for finding in external_path_references:
        errors.append(f"external path reference inside formal bundle: {finding}")
    for rel in sorted(set(symlink_paths)):
        errors.append(f"symbolic link inside formal bundle: {rel}")

    package_results: dict[str, Any] = {}
    family_count = 0
    for kind in ("operators", "task_graphs"):
        family_root = root / kind
        if not family_root.is_dir():
            continue
        families = sorted(path for path in family_root.iterdir() if path.is_dir())
        family_count += len(families)
        package_results[kind] = {
            "family_count": len(families),
            "families": [family.relative_to(root).as_posix() for family in families],
        }
    if family_count == 0:
        errors.append("formal bundle requires at least one operator or task-graph package")

    evidence_result: dict[str, Any] | None = None
    if evidence_root is not None:
        evidence_result = _validate_evidence_json(evidence_root, errors=errors)

    digest = _bundle_digest(root)
    if expected_digest and digest != expected_digest:
        errors.append(
            f"bundle digest mismatch: expected {expected_digest}, observed {digest}"
        )
    return {
        "valid": not errors,
        "errors": errors,
        "bundle_digest": digest,
        "bundle_file_count": sum(1 for path in root.rglob("*") if path.is_file()),
        "source_language_files": sorted(source_files),
        "cache_paths": sorted(set(cache_paths)),
        "source_dirs": sorted(set(source_dirs)),
        "mixed_evidence": sorted(set(mixed_evidence)),
        "external_path_references": external_path_references,
        "symlink_paths": sorted(set(symlink_paths)),
        "packages": package_results,
        "docker": {"present": docker_root.is_dir(), "files": docker_files},
        "evidence": evidence_result,
    }


def _validate_standalone_bundle(
    root: Path,
    *,
    kind: str,
    evidence_root: Path | None,
    expected_digest: str | None,
) -> dict[str, Any]:
    """Validate one operator/task-graph snapshot used by an Intake review case."""
    errors: list[str] = []
    if kind not in {"operator", "task_graph"}:
        return {
            "valid": False,
            "errors": ["standalone_kind must be operator or task_graph"],
        }
    if not root.exists():
        return {"valid": False, "errors": [f"root does not exist: {root}"]}
    if not root.is_dir():
        return {"valid": False, "errors": [f"root is not a directory: {root}"]}

    required_files = (
        {"operator.md"}
        if kind == "operator"
        else {"task_graph.md", "task_graph.yaml", "graph.py"}
    )
    allowed_dirs = {"adapters", "nodes"} if kind == "task_graph" else set()
    root_entries = list(root.iterdir())
    for required in sorted(required_files):
        if not (root / required).is_file():
            errors.append(f"standalone {kind} requires file: {required}")
    for entry in sorted(root_entries, key=lambda path: path.name):
        if entry.is_dir() and entry.name in allowed_dirs:
            continue
        if entry.is_file() and _is_standalone_asset(entry, root=root, kind=kind):
            continue
        errors.append(f"unexpected standalone {kind} entry: {entry.name}")

    source_files: list[str] = []
    cache_paths: list[str] = []
    source_dirs: list[str] = []
    mixed_evidence: list[str] = []
    external_path_references: list[str] = []
    symlink_paths: list[str] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        parts = {part.casefold() for part in path.relative_to(root).parts}
        if path.is_symlink():
            symlink_paths.append(rel)
            continue
        if path.is_dir():
            if parts.intersection(CACHE_DIRS):
                cache_paths.append(rel)
            if path.name.casefold() in SOURCE_DIRS:
                source_dirs.append(rel)
            if path.name.casefold() in EVIDENCE_DIRS:
                mixed_evidence.append(rel)
            continue
        if (
            path.suffix.casefold() in SOURCE_SUFFIXES
            and not _is_standalone_asset(path, root=root, kind=kind)
        ) or (
            path.suffix.casefold() == ".py"
            and not _is_standalone_asset(path, root=root, kind=kind)
        ):
            source_files.append(rel)
        if path.name.casefold() in CACHE_DIRS:
            cache_paths.append(rel)
        if (
            path.suffix.casefold() in EVIDENCE_SUFFIXES
            and EVIDENCE_NAME_RE.search(path.stem)
        ) or "validation_harnesses" in parts:
            mixed_evidence.append(rel)
    for rel in source_files:
        errors.append(f"source-language file inside standalone bundle: {rel}")
    for rel in sorted(set(cache_paths)):
        errors.append(f"cache/generated directory inside standalone bundle: {rel}")
    for rel in sorted(set(source_dirs)):
        errors.append(f"source/work directory inside standalone bundle: {rel}")
    for rel in sorted(set(mixed_evidence)):
        errors.append(f"validation evidence mixed into standalone bundle: {rel}")
    external_path_references = _find_external_path_references(root)
    for finding in external_path_references:
        errors.append(f"external path reference inside standalone bundle: {finding}")
    for rel in sorted(set(symlink_paths)):
        errors.append(f"symbolic link inside standalone bundle: {rel}")

    evidence_result: dict[str, Any] | None = None
    if evidence_root is not None:
        evidence_result = _validate_evidence_json(evidence_root, errors=errors)
    digest = _bundle_digest(root)
    if expected_digest and digest != expected_digest:
        errors.append(f"bundle digest mismatch: expected {expected_digest}, observed {digest}")
    package_key = "operators" if kind == "operator" else "task_graphs"
    return {
        "valid": not errors,
        "errors": errors,
        "bundle_digest": digest,
        "bundle_file_count": sum(1 for path in root.rglob("*") if path.is_file()),
        "source_language_files": sorted(source_files),
        "cache_paths": sorted(set(cache_paths)),
        "source_dirs": sorted(set(source_dirs)),
        "mixed_evidence": sorted(set(mixed_evidence)),
        "external_path_references": external_path_references,
        "symlink_paths": sorted(set(symlink_paths)),
        "packages": {package_key: {"family_count": 1, "families": ["."]}},
        "docker": {"present": False, "files": []},
        "evidence": evidence_result,
    }


def _find_external_path_references(root: Path) -> list[str]:
    """Find host/source paths that make a supposedly source-free bundle non-portable.

    Relative source anchors in operator/task-graph markdown are provenance and remain
    allowed. Executable/configuration files must not point outside the formal bundle;
    absolute host paths are rejected in every text file.
    """
    findings: list[str] = []
    resolved_root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        if _is_non_executable_documentation(path, root=root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix.casefold() in ABSOLUTE_SCAN_SUFFIXES:
            for match in ABSOLUTE_PATH_RE.finditer(text):
                token = match.group(0).rstrip(".,;:)]}")
                findings.append(f"{rel}: {token}")
        if path.suffix.casefold() not in PATH_SCAN_SUFFIXES:
            continue
        for match in QUOTED_PATH_RE.finditer(text):
            value = match.group("value").strip()
            if not _looks_like_source_path(value):
                continue
            normalized = value.replace("\\", "/")
            candidate = Path(normalized)
            windows_absolute = bool(re.match(r"^[A-Za-z]:/", normalized))
            unc_absolute = value.startswith("\\\\")
            if (
                normalized.startswith("/")
                or windows_absolute
                or unc_absolute
                or candidate.is_absolute()
            ):
                # Generated loaders commonly append a package-local filename to
                # an already validated asset reference (for example,
                # ``asset_ref + "/graph.py"``).  A single-segment suffix is not
                # a host path; nested absolute paths remain rejected.
                if normalized.startswith("/") and normalized.count("/") == 1:
                    continue
                findings.append(f"{rel}: {value}")
                continue
            resolved = (path.parent / candidate).resolve()
            try:
                resolved.relative_to(resolved_root)
            except ValueError:
                findings.append(f"{rel}: {value}")
    return sorted(set(findings))


def _is_non_executable_documentation(path: Path, *, root: Path) -> bool:
    """Exclude provenance and runtime notes from executable dependency scanning."""
    rel_parts = path.relative_to(root).parts
    if path.suffix.casefold() != ".md":
        return False
    if path.name.casefold() in {name.casefold() for name in PROJECT_FILES}:
        return True
    return "docker" in {part.casefold() for part in rel_parts}


def _looks_like_source_path(value: str) -> bool:
    if not ("/" in value or "\\" in value):
        return False
    if value.startswith(("../", "..\\", "./", ".\\")):
        return True
    return Path(value.replace("\\", "/")).suffix.casefold() in SOURCE_PATH_SUFFIXES


def _is_standalone_asset(path: Path, *, root: Path, kind: str) -> bool:
    rel = path.relative_to(root).parts
    name = path.name
    if kind == "operator":
        return len(rel) == 1 and name in {
            "operator.md",
            "scientific_operator.py",
            "test_scientific_operator.py",
            "scientific_operator.c",
            "scientific_operator.h",
            "test_scientific_operator.c",
        }
    return (
        (len(rel) == 1 and name in {"task_graph.md", "task_graph.yaml", "graph.py"})
        or (len(rel) == 1 and name.casefold().startswith("test") and path.suffix.casefold() == ".py")
        or (len(rel) > 1 and rel[0] in {"adapters", "nodes"} and path.suffix.casefold() == ".py")
    )


def _is_c_profile_asset(path: Path, *, root: Path) -> bool:
    rel = path.relative_to(root)
    return (
        len(rel.parts) == 3
        and rel.parts[0] == "operators"
        and path.name
        in {
            "scientific_operator.c",
            "scientific_operator.h",
            "test_scientific_operator.c",
        }
    )


def _is_python_asset(path: Path, *, root: Path) -> bool:
    rel = path.relative_to(root)
    if rel.parts == ("asset_entry.py",):
        return True
    if len(rel.parts) == 3 and rel.parts[0] == "operators":
        return path.name in {"scientific_operator.py", "test_scientific_operator.py"}
    if len(rel.parts) >= 3 and rel.parts[0] == "task_graphs":
        package_tail = rel.parts[2:]
        if package_tail == ("graph.py",) or (
            len(package_tail) == 1
            and path.name.casefold().startswith("test")
            and path.suffix.casefold() == ".py"
        ):
            return True
        return package_tail[0] in {"adapters", "nodes"}
    return False


def _validate_evidence_json(root: Path, *, errors: list[str]) -> dict[str, Any]:
    if not root.is_dir():
        errors.append(f"evidence root is not a directory: {root}")
        return {"root": str(root), "json_files": 0, "invalid_json": []}
    invalid: list[str] = []
    json_files = sorted(root.rglob("*.json"))
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            invalid.append(path.relative_to(root).as_posix())
            errors.append(f"invalid evidence JSON {path.relative_to(root)}: {exc}")
    return {
        "root": str(root),
        "json_files": len(json_files),
        "invalid_json": invalid,
    }


def _bundle_digest(root: Path) -> str:
    """Return the shared digest used by external freeze and grading evidence."""
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and not any(part.casefold() in CACHE_DIRS for part in path.relative_to(root).parts)
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    records = [
        f"{path.relative_to(root).as_posix()}\t{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
        for path in files
    ]
    return hashlib.sha256("".join(records).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check formal scientific-asset bundle hygiene and package shape."
    )
    parser.add_argument("root", type=Path, help="Formal bundle root")
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=None,
        help="Optional external validation-evidence directory; all JSON must parse.",
    )
    parser.add_argument(
        "--expected-digest",
        default=None,
        help="Optional digest to enforce after the tree check.",
    )
    parser.add_argument(
        "--require-docker",
        action="store_true",
        help="Require a non-empty project-level docker/ configuration directory.",
    )
    parser.add_argument(
        "--standalone-kind",
        choices=("operator", "task_graph"),
        default=None,
        help="Validate one operator or task-graph snapshot instead of a project bundle.",
    )
    args = parser.parse_args()
    result = validate_source_free_bundle(
        args.root,
        evidence_root=args.evidence_root,
        expected_digest=args.expected_digest,
        require_docker=args.require_docker,
        standalone_kind=args.standalone_kind,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
