"""Validate a SciRel installation from a clean virtual environment.

The command deliberately validates the installed distribution rather than the
checkout.  It records the interpreter identity, imports every declared runtime
dependency, runs ``pip check``, and executes one small Operator plus one
cross-domain diagnostics TaskGraph.  A failed check returns a non-zero status
and the JSON receipt retains the exact failure rather than treating a partial
run as a pass.

Typical Linux amd64 acceptance invocation::

    python -I scripts/validate_installed_wheel.py \
        --expected-platform linux-x86_64-cp314 \
    --wheel dist/scirel-<project.version>-py3-none-any.whl \
        --output installed-wheel-validation.json

The optional ``--wheel`` argument records the exact artifact digest and byte
size, so the receipt can be bound to the release tuple. The script does not
build wheels, modify release records, or update the platform matrix. It is
safe to run against a historical wheel while a later candidate is being
prepared.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import sysconfig
from typing import Any
from zipfile import BadZipFile, ZipFile
from pathlib import PurePosixPath


SCHEMA = "scirel.installed-wheel-validation.v1"
DEFAULT_EXPECTED_PYTHON = "3.14"
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")


def _normalise_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _normalise_os(value: str) -> str:
    token = value.strip().lower()
    return {"darwin": "macos", "mac": "macos", "win32": "windows"}.get(
        token, token
    )


def _normalise_arch(value: str) -> str:
    token = value.strip().lower().replace("-", "_")
    return {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "x8664": "x86_64",
        "x86": "x86",
        "arm64": "aarch64",
        "aarch64": "aarch64",
        "armv8": "aarch64",
    }.get(token, token)


def _parse_platform_id(value: str) -> dict[str, str]:
    """Parse ``linux-x86_64-cp314`` style acceptance identifiers."""

    parts = value.strip().lower().split("-")
    if len(parts) < 3 or any(not part for part in parts):
        raise ValueError(
            "expected platform id '<os>-<architecture>-<python>', "
            "for example linux-x86_64-cp314"
        )
    python_tag = parts[-1]
    if not re.fullmatch(r"cp\d+", python_tag):
        raise ValueError("platform Python tag must use the cp314 form")
    architecture = _normalise_arch("-".join(parts[1:-1]))
    digits = python_tag[2:]
    if len(digits) == 2:
        python_line = f"{int(digits[0])}.{int(digits[1])}"
    elif len(digits) == 3:
        python_line = f"{int(digits[0])}.{int(digits[1:])}"
    else:
        raise ValueError("platform Python tag must identify a CPython 3.x line")
    return {
        "os": _normalise_os(parts[0]),
        "architecture": architecture,
        "python_tag": python_tag,
        "python_line": python_line,
    }


def _runtime_identity(expected_platform: str | None, expected_python: str) -> tuple[dict[str, Any], list[str]]:
    implementation = platform.python_implementation()
    version_line = f"{sys.version_info.major}.{sys.version_info.minor}"
    actual = {
        "implementation": implementation,
        "version": platform.python_version(),
        "version_line": version_line,
        "executable": str(Path(sys.executable).resolve()),
        "prefix": str(Path(sys.prefix).resolve()),
        "base_prefix": str(Path(sys.base_prefix).resolve()),
        "os": _normalise_os(platform.system()),
        "architecture": _normalise_arch(platform.machine()),
        "platform": sysconfig.get_platform(),
        "python_abi": getattr(sys.implementation, "cache_tag", None),
    }
    errors: list[str] = []
    if implementation != "CPython":
        errors.append(f"Python implementation is {implementation}, expected CPython")
    if version_line != expected_python:
        errors.append(f"Python version line is {version_line}, expected {expected_python}")
    if expected_platform:
        expected = _parse_platform_id(expected_platform)
        actual["expected_platform"] = expected_platform
        for key, label in (("os", "OS"), ("architecture", "architecture"), ("python_line", "Python line")):
            actual_key = "version_line" if key == "python_line" else key
            if actual[actual_key] != expected[key]:
                errors.append(
                    f"{label} is {actual[actual_key]}, expected {expected[key]} "
                    f"for {expected_platform}"
                )
    return actual, errors


def _declared_runtime_requirements(dist_name: str = "scirel") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in metadata.requires(dist_name) or []:
        requirement, _, marker = raw.partition(";")
        # Extras are development/optional paths.  The core acceptance receipt
        # must report the package's unconditional runtime closure only.
        if "extra" in marker.lower():
            continue
        match = _REQUIREMENT_NAME.match(requirement)
        if not match:
            raise ValueError(f"cannot parse declared dependency: {raw}")
        rows.append({"requirement": raw, "name": match.group(1)})
    return rows


def _dependency_import_candidates(name: str) -> list[str]:
    target = _normalise_distribution(name)
    mapping = metadata.packages_distributions()
    candidates = [
        module
        for module, distributions in mapping.items()
        if any(_normalise_distribution(dist) == target for dist in distributions)
    ]
    # Keep the conventional top-level spelling first when a distribution
    # publishes more than one module (for example matplotlib toolkits).
    candidates.sort(key=lambda value: (0 if _normalise_distribution(value) == target else 1, value))
    if not candidates:
        candidates = [name.replace("-", "_")]
    return candidates


def _check_dependencies() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for row in _declared_runtime_requirements():
        name = row["name"]
        item: dict[str, Any] = {**row, "status": "FAIL", "import_candidates": _dependency_import_candidates(name)}
        try:
            item["installed_version"] = metadata.version(name)
        except metadata.PackageNotFoundError as exc:
            item["error"] = f"distribution is not installed: {name}"
            checks.append(item)
            continue
        imported = False
        import_errors: list[str] = []
        for module_name in item["import_candidates"]:
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # pragma: no cover - dependency-owned import failures
                import_errors.append(f"{module_name}: {type(exc).__name__}: {exc}")
                continue
            item["imported_module"] = module_name
            item["imported_from"] = str(getattr(module, "__file__", ""))
            imported = True
            break
        if imported:
            item["status"] = "PASS"
        else:
            item["error"] = "; ".join(import_errors) or f"no import candidate for {name}"
        checks.append(item)
    return checks


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _source_tree_roots() -> list[Path]:
    roots: list[Path] = []
    script_root = Path(__file__).resolve().parents[1]
    if (script_root / "src" / "scirel").is_dir():
        roots.append(script_root.resolve())
    cwd = Path.cwd().resolve()
    if (cwd / "src" / "scirel").is_dir() and cwd not in roots:
        roots.append(cwd)
    return roots


def _check_distribution() -> tuple[dict[str, Any], list[str], Any | None]:
    details: dict[str, Any] = {"status": "FAIL"}
    errors: list[str] = []
    try:
        dist = metadata.distribution("scirel")
    except metadata.PackageNotFoundError:
        return {"status": "FAIL", "error": "scirel distribution is not installed"}, [
            "scirel distribution is not installed"
        ], None
    details.update(
        {
            "version": dist.version,
            "requires_python": dist.metadata.get("Requires-Python"),
            "metadata_path": str(Path(dist._path).resolve()),
        }
    )
    try:
        module = importlib.import_module("scirel")
    except Exception as exc:
        details["error"] = f"cannot import scirel: {type(exc).__name__}: {exc}"
        return details, [details["error"]], None
    module_path = Path(getattr(module, "__file__", "")).resolve()
    prefix = Path(sys.prefix).resolve()
    source_roots = _source_tree_roots()
    within_prefix = _path_is_within(module_path, prefix)
    in_source_tree = any(_path_is_within(module_path, root / "src") for root in source_roots)
    details.update(
        {
            "module_file": str(module_path),
            "within_sys_prefix": within_prefix,
            "in_source_tree": in_source_tree,
        }
    )
    if not within_prefix:
        errors.append(f"scirel module is outside the current environment prefix: {module_path}")
    if in_source_tree:
        errors.append(f"scirel module resolves to a source checkout: {module_path}")
    if errors:
        return details, errors, module
    details["status"] = "PASS"
    return details, errors, module


def _wheel_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Return a stable identity for the exact wheel used for installation."""

    artifact: dict[str, Any] = {"path": path.name}
    if not path.is_file():
        return artifact, [f"wheel artifact does not exist: {path}"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    artifact.update({"sha256": digest, "bytes": path.stat().st_size})
    return artifact, []


def _wheel_payload(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Inspect the archive payload that was passed to the installer.

    A clean-environment receipt should also prove that the wheel itself is a
    scientific runtime artifact.  In particular, development trees and
    interpreter caches must not be smuggled into an otherwise successful
    installation.  This check is deliberately independent of package import
    behaviour and does not infer scientific capability from file names.
    """

    details: dict[str, Any] = {
        "status": "FAIL",
        "path": path.name,
        "file_count": 0,
        "package_file_count": 0,
        "dist_info_file_count": 0,
        "native_resource_count": 0,
        "uncompressed_bytes": 0,
        "forbidden_files": [],
    }
    if not path.is_file():
        return details, [f"wheel payload does not exist: {path}"]

    errors: list[str] = []
    try:
        with ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            details["file_count"] = len(names)
            details["uncompressed_bytes"] = sum(info.file_size for info in infos)
            duplicate_names = sorted({name for name in names if names.count(name) > 1})
            if duplicate_names:
                errors.append(f"wheel contains duplicate archive members: {duplicate_names}")

            top_levels: set[str] = set()
            dist_info_roots: set[str] = set()
            metadata_name: str | None = None
            metadata_version: str | None = None
            for info in infos:
                name = info.filename
                if not name or name.endswith("/"):
                    errors.append(f"wheel contains an empty or directory archive member: {name!r}")
                    continue
                if "\\" in name:
                    errors.append(f"wheel member uses a backslash path: {name!r}")
                    continue
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts:
                    errors.append(f"wheel member escapes its archive root: {name!r}")
                    continue
                top = relative.parts[0]
                top_levels.add(top)
                if top == "scirel":
                    details["package_file_count"] += 1
                elif top.endswith(".dist-info"):
                    dist_info_roots.add(top)
                    details["dist_info_file_count"] += 1
                else:
                    details["forbidden_files"].append(name)
                    errors.append(f"wheel contains a non-package top-level member: {name}")
                if name.endswith(".pyc") or name.endswith(".pyo") or "__pycache__" in relative.parts:
                    details["forbidden_files"].append(name)
                    errors.append(f"wheel contains an interpreter cache: {name}")
                if relative.parts[-1].lower() in {"tests", "provenance", "scripts"}:
                    details["forbidden_files"].append(name)
                    errors.append(f"wheel contains a development asset: {name}")
                if name.endswith(".m"):
                    details["native_resource_count"] += 1

            if len(dist_info_roots) != 1:
                errors.append(
                    "wheel must contain exactly one dist-info root; "
                    f"found {sorted(dist_info_roots)}"
                )
            else:
                dist_info = next(iter(dist_info_roots))
                metadata_path = f"{dist_info}/METADATA"
                try:
                    metadata_text = archive.read(metadata_path).decode("utf-8")
                except (KeyError, UnicodeDecodeError) as exc:
                    errors.append(f"wheel metadata is unreadable: {exc}")
                else:
                    for line in metadata_text.splitlines():
                        if line.startswith("Name: "):
                            metadata_name = line[6:].strip()
                        elif line.startswith("Version: "):
                            metadata_version = line[9:].strip()
                    if metadata_name is None or metadata_version is None:
                        errors.append("wheel metadata lacks Name or Version")
                    else:
                        details["metadata_name"] = metadata_name
                        details["metadata_version"] = metadata_version
            details["top_level_roots"] = sorted(top_levels)
    except (BadZipFile, OSError) as exc:
        errors.append(f"wheel payload is not a readable ZIP archive: {type(exc).__name__}: {exc}")

    if not errors:
        details["status"] = "PASS"
    return details, errors


def _run_pip_check() -> tuple[dict[str, Any], list[str]]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            check=False,
            capture_output=True,
            text=True,
            env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        )
    except OSError as exc:
        return {"status": "FAIL", "error": str(exc)}, [f"pip check could not run: {exc}"]
    details = {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "returncode": result.returncode,
        "stdout": result.stdout.strip()[-4000:],
        "stderr": result.stderr.strip()[-4000:],
    }
    if result.returncode:
        return details, [f"pip check failed with exit code {result.returncode}"]
    return details, []


def _array_summary(value: Any, expected_shape: tuple[int, ...] | None = None) -> dict[str, Any]:
    import numpy as np

    array = np.asarray(value)
    summary: dict[str, Any] = {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "finite": bool(np.all(np.isfinite(array))),
    }
    if array.size:
        summary["min"] = float(np.min(array))
        summary["max"] = float(np.max(array))
    if expected_shape is not None:
        summary["expected_shape"] = list(expected_shape)
        summary["shape_match"] = tuple(array.shape) == expected_shape
    return summary


def _run_simple_operator() -> tuple[dict[str, Any], list[str]]:
    try:
        import numpy as np

        from scirel.field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field

        r_axis = np.array([0.5, 1.5], dtype=float)
        z_axis = np.array([-0.3, 0.3], dtype=float)
        r_grid, z_grid = np.meshgrid(r_axis, z_axis)
        result = solve_multi_coil_vacuum_field(
            {
                "r_grid": r_grid,
                "z_grid": z_grid,
                "rectangular_coils": [
                    {
                        "r0_m": 1.0,
                        "z0_m": 0.0,
                        "nr": 1,
                        "nz": 1,
                        "dr_m": 0.04,
                        "dz_m": 0.05,
                        "current_a": 1000.0,
                    }
                ],
            }
        )
        expected_shape = tuple(r_grid.shape)
        details = {
            "status": "PASS",
            "outputs": {
                name: _array_summary(result[name], expected_shape)
                for name in ("psi_vac", "b_r_vac", "b_z_vac")
            },
            "filaments": _array_summary(result["filaments"], (1, 3)),
        }
        errors = []
        for name, summary in details["outputs"].items():
            if not summary["finite"] or not summary["shape_match"]:
                errors.append(f"simple Operator output {name} is not finite or has the wrong shape")
        if not details["filaments"]["finite"] or not details["filaments"]["shape_match"]:
            errors.append("simple Operator filament output is not finite or has the wrong shape")
        if errors:
            details["status"] = "FAIL"
        return details, errors
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }, [f"simple Operator failed: {type(exc).__name__}: {exc}"]


def _run_cross_domain_task() -> tuple[dict[str, Any], list[str]]:
    """Run the diagnostics graph, which binds a geometry sampler dependency."""

    try:
        import numpy as np

        from scirel.diagnostics.equilibrium_synthesis_diagnostics import (
            synthesize_equilibrium_diagnostics,
        )

        r_grid, z_grid = np.meshgrid(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
        result = synthesize_equilibrium_diagnostics(
            {
                "R": r_grid,
                "Z": z_grid,
                "equilibrium": {
                    "psi": r_grid + 2.0 * z_grid,
                    "psi_unit": "Wb/rad",
                },
                "observations": {
                    "flux_loops": {
                        "points": np.array([[0.5, 0.5]]),
                        "quantity": "raw_psi",
                        "unit": "Wb/rad",
                    }
                },
            }
        )
        summary = _array_summary(result["flux_loops"], (1,))
        details = {
            "status": "PASS" if summary["finite"] and summary["shape_match"] else "FAIL",
            "outputs": {"flux_loops": summary},
            "units": result.get("units"),
            "expected_value": 1.5,
            "value": float(np.asarray(result["flux_loops"])[0]),
        }
        errors: list[str] = []
        if not summary["finite"] or not summary["shape_match"]:
            errors.append("cross-domain TaskGraph output is not finite or has the wrong shape")
        if details["units"].get("flux_loops") != "Wb/rad":
            errors.append("cross-domain TaskGraph returned an unexpected flux-loop unit")
        if not np.isclose(details["value"], details["expected_value"], rtol=0.0, atol=1e-12):
            errors.append("cross-domain TaskGraph returned an unexpected interpolated value")
        if errors:
            details["status"] = "FAIL"
        return details, errors
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }, [f"cross-domain TaskGraph failed: {type(exc).__name__}: {exc}"]


def validate_installed_wheel(
    *,
    expected_platform: str | None = None,
    expected_python: str = DEFAULT_EXPECTED_PYTHON,
    wheel_path: Path | None = None,
) -> dict[str, Any]:
    runtime, errors = _runtime_identity(expected_platform, expected_python)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "FAIL",
        "artifact": {},
        "wheel_payload": {},
        "runtime": runtime,
        "package": {},
        "dependencies": [],
        "pip_check": {},
        "simple_operator": {},
        "cross_domain_task": {},
        "errors": errors.copy(),
    }
    package, package_errors, _ = _check_distribution()
    receipt["package"] = package
    receipt["errors"].extend(package_errors)
    if wheel_path is not None:
        artifact, artifact_errors = _wheel_artifact(wheel_path.resolve())
        receipt["artifact"] = artifact
        receipt["errors"].extend(artifact_errors)
        payload, payload_errors = _wheel_payload(wheel_path.resolve())
        receipt["wheel_payload"] = payload
        receipt["errors"].extend(payload_errors)
    try:
        receipt["dependencies"] = _check_dependencies()
    except Exception as exc:
        receipt["errors"].append(f"declared dependency inspection failed: {type(exc).__name__}: {exc}")
    for item in receipt["dependencies"]:
        if item.get("status") != "PASS":
            receipt["errors"].append(
                f"declared dependency failed import: {item.get('name', '<unknown>')}"
            )
    pip_check, pip_errors = _run_pip_check()
    receipt["pip_check"] = pip_check
    receipt["errors"].extend(pip_errors)
    simple, simple_errors = _run_simple_operator()
    receipt["simple_operator"] = simple
    receipt["errors"].extend(simple_errors)
    cross_domain, cross_errors = _run_cross_domain_task()
    receipt["cross_domain_task"] = cross_domain
    receipt["errors"].extend(cross_errors)
    receipt["status"] = "PASS" if not receipt["errors"] else "FAIL"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-platform",
        help="optional acceptance id such as linux-x86_64-cp314",
    )
    parser.add_argument(
        "--expected-python",
        default=DEFAULT_EXPECTED_PYTHON,
        help=f"expected CPython major.minor line (default: {DEFAULT_EXPECTED_PYTHON})",
    )
    parser.add_argument(
        "--wheel",
        type=Path,
        help="exact wheel file installed into the clean environment; records its SHA-256 and size",
    )
    parser.add_argument("--output", type=Path, help="write the JSON receipt to this path")
    args = parser.parse_args()
    try:
        receipt = validate_installed_wheel(
            expected_platform=args.expected_platform,
            expected_python=args.expected_python,
            wheel_path=args.wheel,
        )
    except Exception as exc:  # keep command failures machine-readable
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"validation setup failed: {type(exc).__name__}: {exc}"],
        }
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if receipt.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
