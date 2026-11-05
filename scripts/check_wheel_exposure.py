"""Inspect the exact SciRel wheel supplied for private integration.

This is a static artifact check. It does not build, install or import the wheel,
and it does not establish scientific correctness or target-platform acceptance.
"""

from __future__ import annotations

import argparse
import ast
import base64
from collections import Counter
import csv
from email import policy
from email.parser import BytesParser
from fnmatch import fnmatchcase
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "scirel.wheel-exposure-proof"


def _safe_member(name: str) -> bool:
    parts = name.removesuffix("/").split("/")
    return (
        bool(name)
        and not name.startswith("/")
        and "\\" not in name
        and "\x00" not in name
        and all(part not in {"", ".", ".."} and ":" not in part for part in parts)
    )


def _normalise_requirement(value: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", value)
    if not match:
        return value
    name = re.sub(r"[-_.]+", "-", match[1]).lower()
    return name + re.sub(r"\s+", "", value[match.end() :])


def _requirement_name(value: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", value)
    return re.sub(r"[-_.]+", "-", match[1]).lower() if match else ""


def _catalog_bindings(directory: Path) -> list[dict[str, str]]:
    if not directory.is_dir():
        raise ValueError(f"catalog directory does not exist: {directory}")
    bindings = []
    for path in sorted(directory.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        api = doc["public_api"]["python"]
        pairs = {(api["module"], api["symbol"])}
        if "canonical_module" in api or "canonical_symbol" in api:
            pairs.add((api["canonical_module"], api["canonical_symbol"]))
        for module, symbol in sorted(pairs):
            bindings.append({"asset_id": doc["asset_id"], "module": module, "symbol": symbol})
    return bindings


def _module_member(module: str, members: dict[str, bytes]) -> str | None:
    path = module.replace(".", "/")
    return next((name for name in (path + ".py", path + "/__init__.py") if name in members), None)


def _supported_lazy_forwarding(tree: ast.Module) -> bool:
    """Recognize SciRel's explicit loader shape, rather than trusting a table."""
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    getter = functions.get("__getattr__")
    if getter is None or [arg.arg for arg in getter.args.args] != ["name"] or not getter.body:
        return False
    branch = getter.body[0]
    condition = ast.parse("name in _LAZY_EXPORTS", mode="eval").body
    if (
        not isinstance(branch, ast.If)
        or ast.dump(branch.test) != ast.dump(condition)
        or branch.orelse
    ):
        return False
    loader = ast.parse(
        "module_name, attribute_name = _LAZY_EXPORTS[name]\n"
        'module = _import_module(f".{module_name}", __name__)\n'
        "value = getattr(module, attribute_name)\n"
        "globals()[name] = value\nreturn value\n"
    ).body
    dump = lambda nodes: [ast.dump(node) for node in nodes]
    if dump(branch.body) == dump(ast.parse("return _load_export(name)").body):
        helper = functions.get("_load_export")
        if (
            helper is None
            or [arg.arg for arg in helper.args.args] != ["name"]
            or dump(helper.body) != dump(loader)
        ):
            return False
    elif dump(branch.body) != dump(loader):
        return False
    return any(
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "importlib"
        and any(
            alias.name == "import_module" and alias.asname == "_import_module"
            for alias in node.names
        )
        for node in tree.body
    )


def _lazy_target(tree: ast.Module, symbol: str) -> tuple[str, str] | None:
    """Read the package's explicit lazy-export table without evaluating code."""
    if not _supported_lazy_forwarding(tree):
        return None
    values = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                values[target.id] = node.value
    table = values.get("_LAZY_EXPORTS")
    if isinstance(table, ast.Dict):
        for key, value in zip(table.keys, table.values):
            if isinstance(key, ast.Constant) and key.value == symbol:
                try:
                    child, exported = ast.literal_eval(value)
                except (ValueError, TypeError, SyntaxError):
                    return None
                if isinstance(child, str) and isinstance(exported, str):
                    return child, exported
    elif isinstance(table, ast.DictComp) and isinstance(table.key, ast.Name):
        # Some facades map all literal __all__ entries to one child module.
        try:
            exported_names = ast.literal_eval(values.get("__all__"))
        except (ValueError, TypeError, SyntaxError):
            return None
        if not isinstance(exported_names, (list, tuple, set)) or not all(
            isinstance(item, str) for item in exported_names
        ):
            return None
        value = table.value
        if (
            symbol in exported_names
            and isinstance(value, ast.Tuple)
            and len(value.elts) == 2
            and isinstance(value.elts[0], ast.Constant)
            and isinstance(value.elts[0].value, str)
            and isinstance(value.elts[1], ast.Name)
            and value.elts[1].id == table.key.id
            and len(table.generators) == 1
            and isinstance(table.generators[0].target, ast.Name)
            and table.generators[0].target.id == table.key.id
            and isinstance(table.generators[0].iter, ast.Name)
            and table.generators[0].iter.id == "__all__"
            and not table.generators[0].ifs
        ):
            return value.elts[0].value, symbol
    return None


def _static_symbol(
    module: str,
    symbol: str,
    members: dict[str, bytes],
    trees: dict[str, ast.Module],
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> bool:
    if (module, symbol) in seen:
        return False
    member = _module_member(module, members)
    if member is None or member not in trees:
        return False
    tree = trees[member]
    seen = seen | {(module, symbol)}
    package = module if member.endswith("/__init__.py") else module.rpartition(".")[0]
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == symbol
        ):
            return True
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if (alias.asname or alias.name) != symbol:
                    continue
                try:
                    target = importlib.util.resolve_name("." * node.level + node.module, package)
                except (ImportError, ValueError):
                    return False
                return _static_symbol(target, alias.name, members, trees, seen)
    lazy = _lazy_target(tree, symbol)
    if lazy:
        child, exported = lazy
        try:
            target = importlib.util.resolve_name(
                child if child.startswith(".") else "." + child, package
            )
        except (ImportError, ValueError):
            return False
        return _static_symbol(target, exported, members, trees, seen)
    return False


def _record_proof(members: dict[str, bytes], errors: list[str]) -> dict:
    records = sorted(name for name in members if name.endswith(".dist-info/RECORD"))
    proof = {
        "status": "FAIL",
        "path": records[0] if len(records) == 1 else None,
        "entries": 0,
        "verified_files": 0,
        "errors": [],
    }
    failures = proof["errors"]
    if len(records) != 1:
        failures.append("expected exactly one dist-info/RECORD")
    else:
        record = records[0]
        try:
            rows = list(csv.reader(io.StringIO(members[record].decode("utf-8"))))
        except (UnicodeError, csv.Error) as exc:
            rows = []
            failures.append(f"invalid RECORD: {exc}")
        proof["entries"] = len(rows)
        paths = []
        for row in rows:
            if len(row) != 3:
                failures.append(f"RECORD row must contain three columns: {row!r}")
                continue
            name, digest, size = row
            paths.append(name)
            if not _safe_member(name) or name not in members:
                failures.append(f"RECORD member is unsafe or absent: {name}")
                continue
            if name == record:
                if digest or size:
                    failures.append("RECORD must leave its own hash and size empty")
                continue
            try:
                algorithm, encoded = digest.split("=", 1)
                if algorithm not in {"sha256", "sha384", "sha512"}:
                    raise ValueError("hash must use sha256 or stronger")
                actual = (
                    base64.urlsafe_b64encode(hashlib.new(algorithm, members[name]).digest())
                    .rstrip(b"=")
                    .decode("ascii")
                )
                if encoded != actual:
                    raise ValueError("hash mismatch")
                if not re.fullmatch(r"0|[1-9][0-9]*", size) or int(size) != len(members[name]):
                    raise ValueError("size mismatch")
            except ValueError as exc:
                failures.append(f"RECORD {name}: {exc}")
            else:
                proof["verified_files"] += 1
        duplicates = sorted(name for name, count in Counter(paths).items() if count > 1)
        if duplicates:
            failures.append(f"duplicate RECORD paths: {duplicates}")
        missing = sorted(set(members) - set(paths))
        if missing:
            failures.append(f"members missing from RECORD: {missing}")
    proof["status"] = "FAIL" if failures else "PASS"
    errors.extend(f"record: {failure}" for failure in failures)
    return proof


def _metadata_proof(members: dict[str, bytes], project: dict, errors: list[str]) -> dict:
    paths = sorted(name for name in members if name.endswith(".dist-info/METADATA"))
    proof = {"status": "FAIL", "path": paths[0] if len(paths) == 1 else None, "errors": []}
    failures = proof["errors"]
    if len(paths) != 1:
        failures.append("expected exactly one dist-info/METADATA")
    else:
        metadata = BytesParser(policy=policy.default).parsebytes(members[paths[0]])
        for field in ("Name", "Version", "Requires-Python"):
            if len(metadata.get_all(field, [])) != 1:
                failures.append(f"expected exactly one {field} field")
        actual = {
            "name": metadata.get("Name"),
            "version": metadata.get("Version"),
            "requires_python": metadata.get("Requires-Python"),
            "requires_dist": metadata.get_all("Requires-Dist", []),
        }
        proof.update(actual)
        proof["dependency_names"] = sorted(
            _requirement_name(req) for req in actual["requires_dist"]
        )
        expected = {
            "name": project["name"],
            "version": project["version"],
            "requires_python": project["requires-python"],
            "requires_dist": project.get("dependencies", []),
        }
        proof["expected"] = expected
        for key in ("name", "version"):
            if actual[key] != expected[key]:
                failures.append(f"{key} differs from project metadata")
        python_constraints = lambda value: sorted(part.strip() for part in (value or "").split(","))
        if python_constraints(actual["requires_python"]) != python_constraints(
            expected["requires_python"]
        ):
            failures.append("Requires-Python differs from project metadata")
        if sorted(map(_normalise_requirement, actual["requires_dist"])) != sorted(
            map(_normalise_requirement, expected["requires_dist"])
        ):
            failures.append("Requires-Dist differs from project dependencies")
        if paths[0].rsplit("/", 1)[0] + "/RECORD" not in members:
            failures.append("METADATA and RECORD are in different dist-info directories")
    proof["status"] = "FAIL" if failures else "PASS"
    errors.extend(f"metadata: {failure}" for failure in failures)
    return proof


def _pure_wheel_proof(members: dict[str, bytes], errors: list[str]) -> dict:
    paths = sorted(name for name in members if name.endswith(".dist-info/WHEEL"))
    proof = {
        "status": "FAIL",
        "path": paths[0] if len(paths) == 1 else None,
        "relocated_package_members": sorted(
            name
            for name in members
            if any(
                parts[index].endswith(".data") and parts[index + 1] in {"purelib", "platlib"}
                for parts in [PurePosixPath(name).parts]
                for index in range(len(parts) - 1)
            )
        ),
        "non_source_code_members": sorted(
            name
            for name in members
            if name.lower().endswith((".so", ".pyd", ".dll", ".dylib", ".pyc", ".pyo"))
        ),
        "errors": [],
    }
    failures = proof["errors"]
    if len(paths) != 1:
        failures.append("expected exactly one dist-info/WHEEL")
    else:
        metadata = BytesParser(policy=policy.default).parsebytes(members[paths[0]])
        proof["root_is_purelib"] = metadata.get("Root-Is-Purelib")
        proof["tags"] = metadata.get_all("Tag", [])
        if metadata.get_all("Root-Is-Purelib", []) != ["true"]:
            failures.append("Root-Is-Purelib must be true")
        if proof["tags"] != ["py3-none-any"]:
            failures.append("expected the platform-independent py3-none-any tag")
        if paths[0].rsplit("/", 1)[0] + "/RECORD" not in members:
            failures.append("WHEEL and RECORD are in different dist-info directories")
    if proof["non_source_code_members"]:
        failures.append("binary or compiled Python code cannot be statically inspected")
    if proof["relocated_package_members"]:
        failures.append(
            "SciRel package members must use canonical wheel paths; purelib/platlib relocation is unsupported"
        )
    proof["status"] = "FAIL" if failures else "PASS"
    errors.extend(f"pure wheel: {failure}" for failure in failures)
    return proof


def _source_proof(
    members: dict[str, bytes], source_root: Path, config: dict, errors: list[str]
) -> dict:
    """Bind all packaged Python and explicitly declared data to source bytes."""
    source_root = Path(source_root).resolve()
    if not (source_root / "scirel").is_dir():
        raise ValueError("source_root must contain the scirel package")
    setuptools = config.get("tool", {}).get("setuptools", {})
    finder = setuptools.get("packages", {}).get("find", {})
    includes, excludes = finder.get("include", ["*"]), finder.get("exclude", [])

    def admitted(package):
        return any(fnmatchcase(package, pattern) for pattern in includes) and not any(
            fnmatchcase(package, pattern) for pattern in excludes
        )

    expected = {}
    packages = set()
    for path in sorted((source_root / "scirel").rglob("*.py")):
        relative = path.relative_to(source_root)
        package = ".".join(relative.parent.parts)
        if admitted(package):
            packages.add(package)
            expected[relative.as_posix()] = path
    for selector, patterns in setuptools.get("package-data", {}).items():
        for package in sorted(packages):
            if selector not in {"", "*"} and not fnmatchcase(package, selector):
                continue
            for pattern in patterns:
                for path in (source_root / Path(*package.split("."))).glob(pattern):
                    if path.is_file():
                        expected[path.relative_to(source_root).as_posix()] = path
    source_members = {}
    for name, path in sorted(expected.items()):
        if path.is_symlink() or not path.resolve().is_relative_to(source_root):
            raise ValueError("source package member uses a symlink or escapes source_root: " + name)
        source_members[name] = path.read_bytes()
    wheel_members = {name: data for name, data in members.items() if name.startswith("scirel/")}

    def inventory_digest(values):
        inventory = {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
            for name, data in sorted(values.items())
        }
        return hashlib.sha256(
            json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    missing = sorted(set(source_members) - set(wheel_members))
    extra = sorted(set(wheel_members) - set(source_members))
    changed = sorted(
        name
        for name in source_members.keys() & wheel_members.keys()
        if source_members[name] != wheel_members[name]
    )
    failed = bool(missing or extra or changed)
    if failed:
        errors.append("wheel package bytes differ from the selected source tree")
    return {
        "status": "FAIL" if failed else "PASS",
        "expected_files": len(source_members),
        "wheel_files": len(wheel_members),
        "missing_members": missing,
        "extra_members": extra,
        "changed_members": changed,
        "source_content_sha256": inventory_digest(source_members),
        "wheel_content_sha256": inventory_digest(wheel_members),
        "scope": "all included package Python files and explicit setuptools package-data",
        "digest_format": "SHA-256 of sorted compact JSON mapping member to sha256 and size_bytes",
    }


def inspect_wheel(
    wheel: Path,
    *,
    public_catalog: Path = ROOT / "catalog" / "examples",
    held_catalog: Path = ROOT / "catalog" / "review" / "examples",
    project_file: Path = ROOT / "pyproject.toml",
    source_root: Path | None = None,
) -> dict:
    """Return an auditable, static PASS/FAIL report for these exact wheel bytes."""
    wheel = Path(wheel)
    data = wheel.read_bytes()
    public = _catalog_bindings(Path(public_catalog))
    if not public:
        raise ValueError("public catalog contains no asset documents")
    held = _catalog_bindings(Path(held_catalog))
    config = tomllib.loads(Path(project_file).read_text(encoding="utf-8"))
    project = config["project"]
    errors: list[str] = []
    report = {
        "schema": SCHEMA,
        "wheel": wheel.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "status": "FAIL",
        "errors": errors,
        "verification": "static artifact inspection; no wheel code imported",
        "runtime_status": "NOT_RUN",
        "scientific_validation_status": "NOT_RUN",
    }
    members = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            # ZipInfo.filename sanitizes separators on Windows and truncates
            # NULs. Audit the original archive names before that information
            # is lost, retaining those same names for RECORD comparisons.
            names = [info.orig_filename for info in infos]
            duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
            unsafe = sorted(name for name in names if not _safe_member(name))
            symlinks = sorted(
                info.orig_filename for info in infos if stat.S_ISLNK(info.external_attr >> 16)
            )
            report["archive"] = {
                "files": sum(not info.is_dir() for info in infos),
                "duplicate_members": duplicates,
                "unsafe_members": unsafe,
                "symlink_members": symlinks,
            }
            for label, findings in (
                ("duplicate members", duplicates),
                ("unsafe members", unsafe),
                ("symlink members", symlinks),
            ):
                if findings:
                    errors.append(f"archive {label}: {findings}")
            members = {
                info.orig_filename: archive.read(info) for info in infos if not info.is_dir()
            }
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as exc:
        errors.append(f"cannot read wheel archive: {exc}")
        return report
    report["record"] = _record_proof(members, errors)
    report["metadata"] = _metadata_proof(members, project, errors)
    report["pure_wheel"] = _pure_wheel_proof(members, errors)
    report["source_binding"] = (
        _source_proof(members, source_root, config, errors)
        if source_root is not None
        else {"status": "NOT_RUN", "reason": "source_root was not supplied"}
    )
    trees = {}
    for name, source in members.items():
        if name.endswith(".py"):
            try:
                trees[name] = ast.parse(source, filename=name)
            except (SyntaxError, UnicodeError, ValueError) as exc:
                errors.append(f"cannot statically parse {name}: {exc}")
    missing_modules = sorted(
        {item["module"] for item in public if _module_member(item["module"], members) is None}
    )
    unresolved = []
    for item in public:
        member = _module_member(item["module"], members)
        if (
            member
            and member in trees
            and not _static_symbol(item["module"], item["symbol"], members, trees)
        ):
            unresolved.append(item)
    report["public_api"] = {
        "asset_count": len({item["asset_id"] for item in public}),
        "bindings_checked": len(public),
        "missing_modules": missing_modules,
        "unresolved_symbols": unresolved,
        "method": "static definitions, reexports and supported lazy-forwarding syntax; runtime not tested",
    }
    if missing_modules or unresolved:
        errors.append("one or more public API bindings are absent or statically unresolved")
    public_modules = {item["module"] for item in public}
    held_modules = {item["module"] for item in held} - public_modules
    report["held_asset_count"] = len({item["asset_id"] for item in held})
    report["held_modules_present"] = sorted(
        module for module in held_modules if _module_member(module, members)
    )
    report["shared_modules_with_held_symbols_present"] = sorted(
        {item["module"] for item in held} & public_modules
    )
    held_symbols = {item["symbol"] for item in held}
    symbol_hits = {}
    for name, tree in trees.items():
        for node in ast.walk(tree):
            value = (
                node.name
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                else (
                    node.id
                    if isinstance(node, ast.Name)
                    else node.value
                    if isinstance(node, ast.Constant)
                    else None
                )
            )
            if isinstance(node, ast.alias):
                values = {node.name, node.asname}
            else:
                values = {value} if isinstance(value, str) else set()
            for symbol in held_symbols & values:
                symbol_hits.setdefault(symbol, set()).add(name)
    report["held_symbol_references_present"] = {
        symbol: sorted(hits) for symbol, hits in sorted(symbol_hits.items())
    }
    report["candidate_paths_present"] = sorted(
        name
        for name in members
        if any(
            "candidate" in part.lower() or part.lower() == "catalog"
            for part in PurePosixPath(name).parts
        )
    )
    if report["held_modules_present"] or symbol_hits or report["candidate_paths_present"]:
        errors.append("held API or candidate/catalog material is present in the wheel")
    report["licenses"] = [
        {"path": name, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)}
        for name, content in sorted(members.items())
        if ".dist-info/licenses/" in name
    ]
    report["status"] = "FAIL" if errors else "PASS"
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel", type=Path, required=True, help="exact final distribution wheel to inspect"
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        help="optionally bind package bytes to this explicit source directory",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = inspect_wheel(args.wheel, source_root=args.source_root)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
