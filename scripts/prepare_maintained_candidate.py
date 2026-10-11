"""Stage an exact bounded development candidate without admitting other code.

This engineering selector does not establish scientific qualification or review.
The owner supplies source hashes and explicit initializer bodies after comparison.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def module_name(path: str) -> str:
    parts = Path(path).parts
    if len(parts) < 3 or parts[:2] != ("src", "scirel") or not path.endswith(".py"):
        raise ValueError(f"not a scientific Python source: {path}")
    return path[4:-3].replace("/", ".").removesuffix(".__init__")


def inspect_closure(bodies: dict[str, bytes], external_roots: set[str]) -> dict:
    """Fail closed on omitted imports; AST here checks packaging, not science."""
    modules = {module_name(path): path for path in bodies}
    edges: dict[str, list[str]] = {}
    external: dict[str, list[str]] = {}
    for path, body in bodies.items():
        current = module_name(path)
        package = current if path.endswith("/__init__.py") else current.rpartition(".")[0]
        needed = set()
        imported = set()
        for node in ast.walk(ast.parse(body, filename=path)):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
                if name in {"__import__", "import_module", "exec", "eval"}:
                    raise ValueError(f"unbound dynamic executable/import closure: {path}:{node.lineno}")
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = importlib.util.resolve_name("." * node.level + base, package)
                names = [base]
                # `from package import submodule` must bind that submodule when
                # present. Exported symbols are covered by the package body.
                names.extend(base + "." + alias.name for alias in node.names if base + "." + alias.name in modules)
            else:
                continue
            for name in names:
                if name == "scirel" or name.startswith("scirel."):
                    if name not in modules:
                        raise ValueError(f"runtime dependency is outside selected files: {path} -> {name}")
                    needed.add(name)
                elif name:
                    root = name.partition(".")[0]
                    if root not in sys.stdlib_module_names and root not in external_roots:
                        raise ValueError(f"undeclared external import: {path} -> {name}")
                    if root not in sys.stdlib_module_names:
                        imported.add(root)
        edges[current] = sorted(needed)
        external[current] = sorted(imported)
    return {"internal_imports": edges, "external_import_roots": external}


def stage(source_root: Path, profile_path: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"fresh staging required: {output}")
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    if profile.get("schema") != "scirel.maintained-development-selection.v1":
        raise ValueError("invalid development selection schema")
    if profile.get("human_approval") is not False or profile.get("release_approval") is not False:
        raise ValueError("development selector cannot assert approval")
    source_root = source_root.resolve()
    bodies = {}
    records = []
    for record in profile["files"]:
        relative = record["path"]
        name = Path(relative)
        module_name(relative)
        if name.is_absolute() or ".." in name.parts or relative in bodies:
            raise ValueError(f"unsafe or repeated selected path: {relative}")
        actual = (source_root / relative).resolve(strict=True)
        if not actual.is_relative_to(source_root):
            raise ValueError(f"selected symlink escapes source: {relative}")
        data = actual.read_bytes()
        if digest(data) != record["sha256"]:
            raise ValueError(f"source hash drift: {relative}")
        bodies[relative] = data
        records.append({"path": relative, "source_sha256": digest(data), "staged_sha256": digest(data)})
    for relative, text in profile["initializers"].items():
        module_name(relative)
        if not relative.endswith("/__init__.py") or relative in bodies:
            raise ValueError(f"invalid/repeated explicit initializer: {relative}")
        bodies[relative] = text.encode("utf-8")
        original = source_root / relative
        records.append({"path": relative, "source_sha256": digest(original.read_bytes()) if original.exists() else None,
                        "staged_sha256": digest(bodies[relative]), "initializer_projection": True})
    for relative in bodies:
        for parent in Path(relative).parents:
            if parent == Path("src") or parent == Path("."):
                break
            if (parent / "__init__.py").as_posix() not in bodies:
                raise ValueError(f"selected module has no explicit package initializer: {relative}")
    closure = inspect_closure(bodies, set(profile["external_import_roots"]))
    license_path = Path(profile["license_path"])
    if license_path.is_absolute() or ".." in license_path.parts:
        raise ValueError("license path escapes source")
    license_bytes = (source_root / license_path).read_bytes()
    if digest(license_bytes) != profile["license_sha256"]:
        raise ValueError("license drift")
    # All validation precedes mutation. A failed copy leaves a reviewable
    # partial fresh stage; no old output is deleted or overwritten.
    output.mkdir(parents=True)
    for relative, data in bodies.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output / license_path).parent.mkdir(parents=True, exist_ok=True)
    (output / license_path).write_bytes(license_bytes)
    project = f'''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "scirel"
version = {json.dumps(profile["version"])}
description = "SciRel bounded maintained development candidate"
requires-python = ">=3.10"
dependencies = {json.dumps(profile["dependencies"])}

[tool.setuptools]
license-files = [{json.dumps(license_path.as_posix())}]

[tool.setuptools.packages.find]
where = ["src"]
include = ["scirel", "scirel.*"]
'''
    (output / "pyproject.toml").write_text(project)
    excluded = sorted(path.relative_to(source_root).as_posix() for path in (source_root / "src/scirel").rglob("*.py")
                      if path.relative_to(source_root).as_posix() not in bodies)
    receipt = {"schema": "scirel.maintained-development-stage.v1", "profile_sha256": digest(profile_bytes),
               "candidate_source_commit": profile["candidate_source_commit"], "candidate_source_tree": profile["candidate_source_tree"],
               "selected_files": sorted(records, key=lambda record: record["path"]), "excluded_python_paths": excluded,
               "closure": closure, "human_approval": False, "release_approval": False}
    (output / "selection-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.source_root, args.profile, args.staging_dir), indent=2))
