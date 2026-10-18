"""Assemble a source-free SciRel distribution tree from admitted integrations."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any


INTEGRATIONS_SCHEMA = "scirel.admitted-integrations.v1"
MANIFEST_SCHEMA = "scirel.admitted-wheel-manifest.v1"
CONTENT_LOCK_SCHEMA = "scirel.distribution-content-lock.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WHEEL_SOURCE_DATE_EPOCH = "315532800"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _string_list(value: Any, field: str, *, required: bool = False) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"pyproject.toml {field} must be a non-empty string list")
    return list(value)


def _read_project_metadata(source_root: Path) -> dict[str, Any]:
    """Read the canonical build and runtime metadata for an admitted build.

    The admitted source closure is historical, but its generated wheel must use
    the same Python and dependency contract as the current project.  Only
    metadata that is self-contained in the staging tree is copied here;
    source-only fields such as ``readme`` and ``license-files`` are deliberately
    left out because the admitted staging tree does not contain those files.
    """

    pyproject_path = source_root / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as stream:
            config = tomllib.load(stream)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"canonical project metadata is missing: {pyproject_path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"invalid canonical project metadata: {pyproject_path}") from error

    build_system = config.get("build-system")
    project = config.get("project")
    if not isinstance(build_system, dict):
        raise ValueError("pyproject.toml has no [build-system] table")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml has no [project] table")

    build_requires = _string_list(build_system.get("requires"), "build-system.requires", required=True)
    build_backend = build_system.get("build-backend")
    if not isinstance(build_backend, str) or not build_backend:
        raise ValueError("pyproject.toml build-system.build-backend must be a non-empty string")

    metadata: dict[str, Any] = {
        "name": project.get("name"),
        "version": project.get("version"),
        "description": project.get("description", ""),
        "requires_python": project.get("requires-python"),
        "dependencies": _string_list(project.get("dependencies"), "project.dependencies"),
        "optional_dependencies": project.get("optional-dependencies", {}),
        "build_requires": build_requires,
        "build_backend": build_backend,
    }
    for field in ("name", "version", "requires_python"):
        if not isinstance(metadata[field], str) or not metadata[field]:
            raise ValueError(f"pyproject.toml project.{field.replace('_', '-')} must be a non-empty string")
    if metadata["name"] != "scirel":
        raise ValueError(
            "admitted distribution staging requires pyproject.toml project.name = 'scirel'"
        )
    if not isinstance(metadata["description"], str):
        raise ValueError("pyproject.toml project.description must be a string")

    optional_dependencies = metadata["optional_dependencies"]
    if not isinstance(optional_dependencies, dict):
        raise ValueError("pyproject.toml project.optional-dependencies must be a table")
    normalized_optional: dict[str, list[str]] = {}
    for extra, requirements in optional_dependencies.items():
        if not isinstance(extra, str) or not extra:
            raise ValueError("pyproject.toml project.optional-dependencies has an invalid extra name")
        normalized_optional[extra] = _string_list(
            requirements, f"project.optional-dependencies.{extra}", required=True
        )
    metadata["optional_dependencies"] = normalized_optional
    return metadata


def _read_version(source_root: Path) -> str:
    """Return the canonical project version (kept for callers of the old helper)."""

    return _read_project_metadata(source_root)["version"]


def _toml_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _render_admitted_pyproject(metadata: dict[str, Any]) -> str:
    """Render the self-contained pyproject used by the admitted staging tree."""

    lines = [
        "[build-system]",
        f"requires = {_toml_value(metadata['build_requires'])}",
        f"build-backend = {_toml_value(metadata['build_backend'])}",
        "",
        "[project]",
        f"name = {_toml_value(metadata['name'])}",
        f"version = {_toml_value(metadata['version'])}",
    ]
    if metadata["description"]:
        lines.append(f"description = {_toml_value(metadata['description'])}")
    lines.extend(
        [
            f"requires-python = {_toml_value(metadata['requires_python'])}",
            f"dependencies = {_toml_value(metadata['dependencies'])}",
        ]
    )
    if metadata["optional_dependencies"]:
        lines.extend(["", "[project.optional-dependencies]"])
        for extra, requirements in sorted(metadata["optional_dependencies"].items()):
            lines.append(f"{_toml_value(extra)} = {_toml_value(requirements)}")
    lines.extend(
        [
            "",
            "[tool.setuptools.packages.find]",
            'where = ["src"]',
            "",
            "[tool.setuptools.package-data]",
            'scirel = ["_admitted_manifest.json"]',
            "",
        ]
    )
    return "\n".join(lines)


def _module_source(source_root: Path, public_callable: str) -> tuple[str, str, Path]:
    parts = public_callable.split(".")
    if len(parts) < 4 or parts[0] != "scirel" or not all(part.isidentifier() for part in parts):
        raise ValueError(f"invalid public callable: {public_callable}")
    module_name = ".".join(parts[:-1])
    source = source_root / "src" / Path(*parts[:-1]).with_suffix(".py")
    if not source.resolve().is_relative_to((source_root / "src" / "scirel").resolve()):
        raise ValueError(f"public callable escapes the SciRel source tree: {public_callable}")
    return module_name, parts[-1], source


def _support_module_source(source_root: Path, module_name: str) -> Path:
    parts = module_name.split(".")
    if (
        len(parts) < 2
        or parts[0] != "scirel"
        or parts[-1] == "__init__"
        or not all(part.isidentifier() for part in parts)
    ):
        raise ValueError(f"invalid support module: {module_name!r}")
    source = source_root / "src" / Path(*parts).with_suffix(".py")
    if not source.resolve().is_relative_to((source_root / "src" / "scirel").resolve()):
        raise ValueError(f"support module escapes the SciRel source tree: {module_name}")
    return source


def _required_reference(admission: dict[str, Any], name: str, module_name: str) -> str:
    value = admission.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing {name} for {module_name}")
    return value


def _relative_import_module(module_name: str, node: ast.ImportFrom) -> str | None:
    package = module_name.split(".")[:-1]
    if node.level > len(package):
        raise ValueError(
            f"{module_name} has a relative import escaping the SciRel source tree"
        )
    base = package[: len(package) - node.level + 1]
    if node.module:
        return ".".join([*base, *node.module.split(".")])
    return None


def _validate_internal_imports(source: Path, module_name: str, admitted_modules: set[str]) -> None:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            internal = [alias.name for alias in node.names if alias.name == "scirel" or alias.name.startswith("scirel.")]
            missing = [name for name in internal if name not in admitted_modules]
            if missing:
                raise ValueError(
                    f"{module_name} has an unbound internal import: {', '.join(missing)}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imported = _relative_import_module(module_name, node)
                if imported is None:
                    base = module_name.split(".")[:-1]
                    for alias in node.names:
                        candidate = ".".join([*base, alias.name])
                        if candidate not in admitted_modules:
                            raise ValueError(
                                f"{module_name} has an unbound internal import: {candidate}"
                            )
                elif imported not in admitted_modules:
                    raise ValueError(
                        f"{module_name} has an unbound internal import: {imported}"
                    )
            else:
                imported = node.module or ""
                if imported == "scirel" or imported.startswith("scirel."):
                    if imported not in admitted_modules:
                        raise ValueError(
                            f"{module_name} has an unbound internal import: {imported}"
                        )


def _write_package_initializers(
    package_root: Path, exports: dict[tuple[str, ...], list[tuple[str, str]]]
) -> None:
    packages: set[tuple[str, ...]] = {("scirel",)}
    for package in exports:
        for length in range(1, len(package) + 1):
            packages.add(package[:length])

    for package in sorted(packages, key=lambda item: (len(item), item)):
        package_dir = package_root.parent / Path(*package)
        package_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        names: list[str] = []

        child_packages = sorted(
            candidate[-1]
            for candidate in packages
            if len(candidate) == len(package) + 1 and candidate[:-1] == package
        )
        if child_packages:
            lines.append("from . import " + ", ".join(child_packages))
            names.extend(child_packages)

        for module, symbol in sorted(exports.get(package, [])):
            lines.append(f"from .{module} import {symbol}")
            names.append(symbol)

        if len(names) != len(set(names)):
            raise ValueError(f"duplicate public export in {'.'.join(package)}")
        if lines:
            lines.append("")
        rendered_names = ", ".join(repr(name) for name in names)
        lines.append(f"__all__ = [{rendered_names}]")
        lines.append("")
        (package_dir / "__init__.py").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def assemble(source_root: Path, staging_dir: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    staging_dir = staging_dir.resolve()
    if staging_dir.exists():
        raise FileExistsError(f"staging directory already exists: {staging_dir}")

    provenance_path = source_root / "provenance" / "admitted-assets.json"
    provenance_bytes = provenance_path.read_bytes()
    records = json.loads(provenance_bytes)
    if records.get("schema") != INTEGRATIONS_SCHEMA:
        raise ValueError("unsupported admitted integration schema")
    integrations = records.get("integrations")
    if not isinstance(integrations, list) or not integrations:
        raise ValueError("admitted integration list is empty")

    parsed: list[tuple[dict[str, Any], str, str, Path]] = []
    selected_modules: set[str] = set()
    public_callables: set[str] = set()
    for entry in integrations:
        public_callable = entry.get("public_callable")
        if not isinstance(public_callable, str) or public_callable in public_callables:
            raise ValueError(f"duplicate or missing public callable: {public_callable!r}")
        public_callables.add(public_callable)
        module_name, symbol, source = _module_source(source_root, public_callable)
        if module_name in selected_modules:
            raise ValueError(f"only one admitted public symbol per module is currently supported: {module_name}")
        selected_modules.add(module_name)
        parsed.append((entry, module_name, symbol, source))

    support_entries = records.get("support_modules", [])
    if not isinstance(support_entries, list):
        raise ValueError("support module list must be a list")
    support_modules: set[str] = set()
    parsed_support: list[tuple[str, Path, bytes]] = []
    for entry in support_entries:
        if not isinstance(entry, dict):
            raise ValueError("support module entry must be an object")
        module_name = entry.get("module")
        if not isinstance(module_name, str) or module_name in support_modules:
            raise ValueError(f"duplicate or missing support module: {module_name!r}")
        if module_name in selected_modules:
            raise ValueError(f"support module is already a public asset module: {module_name}")
        source = _support_module_source(source_root, module_name)
        expected_hash = entry.get("library_source_lf_sha256")
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            raise ValueError(f"invalid source digest for support module: {module_name}")
        if not source.is_file():
            raise FileNotFoundError(f"admitted support source is missing: {source}")
        source_bytes = source.read_bytes()
        normalized_bytes = source_bytes.replace(b"\r\n", b"\n")
        if _sha256(normalized_bytes) != expected_hash:
            raise ValueError(f"support source digest differs from admitted integration: {module_name}")
        support_modules.add(module_name)
        parsed_support.append((module_name, source, normalized_bytes))

    admitted_modules = selected_modules | support_modules

    project_metadata = _read_project_metadata(source_root)
    version = project_metadata["version"]
    target_parent = staging_dir.parent
    target_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{staging_dir.name}-", dir=target_parent) as temporary:
        stage = Path(temporary)
        exports: dict[tuple[str, ...], list[tuple[str, str]]] = {}
        assets: list[dict[str, Any]] = []
        all_admission_refs: set[str] = set()

        for entry, module_name, symbol, source in sorted(parsed, key=lambda item: item[1]):
            if not source.is_file():
                raise FileNotFoundError(f"admitted library source is missing: {source}")
            source_bytes = source.read_bytes()
            normalized_hash = _sha256(source_bytes.replace(b"\r\n", b"\n"))
            expected_hash = entry.get("library_source_lf_sha256")
            if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
                raise ValueError(f"invalid source digest for {module_name}")
            if normalized_hash != expected_hash:
                raise ValueError(f"source digest differs from admitted integration: {module_name}")
            _validate_internal_imports(source, module_name, admitted_modules)

            relative_module = Path("src", *module_name.split(".")).with_suffix(".py")
            destination = stage / relative_module
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_bytes.replace(b"\r\n", b"\n"))

            package = tuple(module_name.split(".")[:-1])
            exports.setdefault(package, []).append((module_name.rsplit(".", 1)[1], symbol))

            admitted_inputs = [entry["admitted_input"]]
            admitted_inputs.extend(
                equivalent["admitted_input"]
                for equivalent in entry.get("equivalent_admitted_inputs", [])
            )
            bindings = []
            for admitted_input in admitted_inputs:
                if admitted_input.get("schema") != "scirel.admitted-asset-export.v1":
                    raise ValueError(f"invalid admitted export for {module_name}")
                admission = admitted_input.get("admission", {})
                admission_ref = _required_reference(admission, "admission_ref", module_name)
                if admission_ref in all_admission_refs:
                    raise ValueError(f"duplicate admission reference: {admission_ref}")
                all_admission_refs.add(admission_ref)
                asset_kind = admission.get("asset_kind")
                if asset_kind not in {"operator", "task_graph"}:
                    raise ValueError(f"invalid asset_kind for {module_name}")
                root_digest = _required_reference(admission, "root_digest", module_name)
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", root_digest):
                    raise ValueError(f"invalid root_digest for {module_name}")
                bindings.append(
                    {
                        "admission_ref": admission_ref,
                        "asset_kind": asset_kind,
                        "case_ref": _required_reference(admission, "case_ref", module_name),
                        "decision_ref": _required_reference(admission, "decision_ref", module_name),
                        "root_digest": root_digest,
                        "version_commit_ref": _required_reference(
                            admission, "version_commit_ref", module_name
                        ),
                    }
                )
            assets.append(
                {
                    "admitted_inputs": bindings,
                    "module_lf_sha256": normalized_hash,
                    "public_callable": entry["public_callable"],
                }
            )

        for module_name, source, source_bytes in sorted(parsed_support):
            _validate_internal_imports(source, module_name, admitted_modules)
            relative_module = Path("src", *module_name.split(".")).with_suffix(".py")
            destination = stage / relative_module
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_bytes)

        package_root = stage / "src" / "scirel"
        _write_package_initializers(package_root, exports)

        manifest: dict[str, Any] = {
            "schema": MANIFEST_SCHEMA,
            "distribution_name": project_metadata["name"],
            "distribution_version": version,
            "source_integrations_schema": records["schema"],
            "source_integrations_sha256": "sha256:" + _sha256(_canonical_json(records)),
            "admission_refs": sorted(all_admission_refs),
            "assets": sorted(assets, key=lambda item: item["public_callable"]),
        }
        manifest["manifest_digest"] = "sha256:" + _sha256(_canonical_json(manifest))
        manifest_path = package_root / "_admitted_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        pyproject = _render_admitted_pyproject(project_metadata)
        (stage / "pyproject.toml").write_text(pyproject, encoding="utf-8", newline="\n")

        locked_files = []
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            locked_files.append(
                {
                    "path": path.relative_to(stage).as_posix(),
                    "sha256": _sha256(path.read_bytes()),
                    "size_bytes": path.stat().st_size,
                }
            )
        content_lock = {
            "schema": CONTENT_LOCK_SCHEMA,
            "distribution_name": project_metadata["name"],
            "distribution_version": version,
            "admitted_manifest_digest": manifest["manifest_digest"],
            "files": locked_files,
        }
        (stage / "scirel-content-lock.json").write_text(
            json.dumps(content_lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        Path(temporary).replace(staging_dir)

    return {
        "staging_dir": str(staging_dir),
        "distribution_version": version,
        "asset_count": len(assets),
        "admission_count": len(all_admission_refs),
        "manifest_digest": manifest["manifest_digest"],
    }


def build_wheel(staging_dir: Path, wheel_dir: Path) -> dict[str, str]:
    staging_dir = staging_dir.resolve()
    wheel_dir = wheel_dir.resolve()
    if wheel_dir.exists():
        raise FileExistsError(f"wheel directory already exists: {wheel_dir}")
    wheel_dir.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = WHEEL_SOURCE_DATE_EPOCH
    environment["PYTHONHASHSEED"] = "0"
    with tempfile.TemporaryDirectory(prefix=f".{wheel_dir.name}-", dir=wheel_dir.parent) as temporary:
        command = [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            temporary,
            str(staging_dir),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, env=environment)
        if completed.returncode:
            raise RuntimeError(
                "wheel build failed:\n" + (completed.stderr or completed.stdout).strip()
            )
        wheels = list(Path(temporary).glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("wheel build did not produce exactly one artifact")
        wheel_name = wheels[0].name
        wheel_hash = _sha256(wheels[0].read_bytes())
        Path(temporary).replace(wheel_dir)
    return {
        "wheel": str(wheel_dir / wheel_name),
        "wheel_sha256": wheel_hash,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble an admitted-only SciRel distribution staging tree"
    )
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.wheel_dir is not None and args.wheel_dir.exists():
            raise FileExistsError(f"wheel directory already exists: {args.wheel_dir.resolve()}")
        result = assemble(args.source_root, args.staging_dir)
        if args.wheel_dir is not None:
            result.update(build_wheel(args.staging_dir, args.wheel_dir))
    except Exception as error:
        print(f"admitted distribution assembly failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
