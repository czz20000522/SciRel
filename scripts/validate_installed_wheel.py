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

Use ``--extra plot`` after installing that extra in the same clean environment
to validate its declared dependency closure and a capability-specific smoke
path. Repeat ``--extra`` to validate more than one optional capability. Core
validation remains the default; undeclared extras fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata as metadata
import json
import os
import pkgutil
from pathlib import Path
import platform
import re
import subprocess
import sys
import sysconfig
from types import ModuleType
from typing import Any
from zipfile import BadZipFile, ZipFile
from pathlib import PurePosixPath

try:
    from public_api_binding import implementation_module
except ModuleNotFoundError:  # imported as ``scripts.validate_installed_wheel`` in tests
    from scripts.public_api_binding import implementation_module


SCHEMA = "scirel.installed-wheel-validation.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
    """Parse ``linux-x86_64-cp314`` style acceptance identifiers.

    The optional ``t`` suffix distinguishes CPython's free-threaded ABI from
    the regular ABI.  Both runtimes report the same major/minor version, so
    the suffix must remain part of the platform identity instead of being
    inferred from the Python line alone.
    """

    parts = value.strip().lower().split("-")
    if len(parts) < 3 or any(not part for part in parts):
        raise ValueError(
            "expected platform id '<os>-<architecture>-<python>', "
            "for example linux-x86_64-cp314"
        )
    python_tag = parts[-1]
    match = re.fullmatch(r"cp(?P<digits>\d{2,3})(?P<free_threaded>t)?", python_tag)
    if not match:
        raise ValueError("platform Python tag must use the cp314 or cp314t form")
    architecture = _normalise_arch("-".join(parts[1:-1]))
    digits = match.group("digits")
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
        "python_abi": f"cpython-{digits}{'t' if match.group('free_threaded') else ''}",
    }


def _runtime_identity(expected_platform: str | None, expected_python: str) -> tuple[dict[str, Any], list[str]]:
    implementation = platform.python_implementation()
    version_line = f"{sys.version_info.major}.{sys.version_info.minor}"
    prefix = Path(sys.prefix).resolve()
    base_prefix = Path(sys.base_prefix).resolve()
    is_virtualenv = prefix != base_prefix
    external_site_paths = sorted(
        {
            str(path.resolve())
            for raw_path in sys.path
            if raw_path
            for path in [Path(raw_path)]
            if path.name in {"site-packages", "dist-packages"}
            and not _path_is_within(path.resolve(), prefix)
        }
    )
    actual = {
        "implementation": implementation,
        "version": platform.python_version(),
        "version_line": version_line,
        "executable": str(Path(sys.executable).resolve()),
        "prefix": str(prefix),
        "base_prefix": str(base_prefix),
        "is_virtualenv": is_virtualenv,
        "external_site_paths": external_site_paths,
        "os": _normalise_os(platform.system()),
        "architecture": _normalise_arch(platform.machine()),
        "platform": sysconfig.get_platform(),
        "python_abi": getattr(sys.implementation, "cache_tag", None),
    }
    errors: list[str] = []
    if not is_virtualenv:
        errors.append(
            "Python interpreter is not running inside a virtual environment; "
            "create a clean venv with `python -m venv`"
        )
    if external_site_paths:
        errors.append(
            "Python path exposes site-packages outside the virtual environment: "
            + ", ".join(external_site_paths)
        )
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
        if actual["python_abi"] != expected["python_abi"]:
            errors.append(
                f"Python ABI is {actual['python_abi']}, expected {expected['python_abi']} "
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


def _declared_extra_requirements(extra: str, dist_name: str = "scirel") -> list[dict[str, str]]:
    """Return the installed distribution requirements for one named extra."""

    requested = extra.strip().lower()
    if not requested:
        raise ValueError("extra name must not be empty")
    rows: list[dict[str, str]] = []
    marker_pattern = re.compile(r"\bextra\s*==\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
    for raw in metadata.requires(dist_name) or []:
        requirement, _, marker = raw.partition(";")
        match = marker_pattern.search(marker)
        if match is None or match.group(1).strip().lower() != requested:
            continue
        requirement_match = _REQUIREMENT_NAME.match(requirement)
        if not requirement_match:
            raise ValueError(f"cannot parse declared dependency: {raw}")
        rows.append(
            {
                "requirement": raw,
                "name": requirement_match.group(1),
                "extra": requested,
            }
        )
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


def _check_dependencies(requirements: list[dict[str, str]] | None = None) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    prefix = Path(sys.prefix).resolve()
    rows = requirements if requirements is not None else _declared_runtime_requirements()
    for row in rows:
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
            module_file = getattr(module, "__file__", None)
            if module_file:
                module_path = Path(module_file).resolve()
                item["within_sys_prefix"] = _path_is_within(module_path, prefix)
            else:
                item["within_sys_prefix"] = False
            imported = True
            break
        if imported:
            if item["within_sys_prefix"]:
                item["status"] = "PASS"
            else:
                item["error"] = (
                    "imported module is outside the current environment prefix: "
                    f"{item['imported_from']}"
                )
        else:
            item["error"] = "; ".join(import_errors) or f"no import candidate for {name}"
        checks.append(item)
    return checks


def _available_extras(dist: Any | None) -> set[str]:
    if dist is None or not hasattr(dist, "metadata"):
        return set()
    return {
        value.strip().lower()
        for value in (dist.metadata.get_all("Provides-Extra") or [])
        if value.strip()
    }


def _run_plot_extra() -> tuple[dict[str, Any], list[str]]:
    try:
        from matplotlib.patches import Rectangle

        from scirel.geometry.plotting import scale_patches

        patch = Rectangle((0.0, 0.0), 1.0, 1.0)
        scale_patches([patch], 2.0)
        return {
            "status": "PASS",
            "matplotlib_version": metadata.version("matplotlib"),
            "patch_type": type(patch).__name__,
        }, []
    except Exception as exc:
        details = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        return details, [f"plot extra smoke failed: {type(exc).__name__}: {exc}"]


def _run_extra_smoke(extra: str) -> tuple[dict[str, Any], list[str]]:
    if extra == "plot":
        return _run_plot_extra()
    return {"status": "FAIL", "error": f"unsupported extra: {extra}"}, [
        f"unsupported optional extra: {extra}"
    ]


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
    metadata_path = Path(dist._path).resolve()
    source_roots = _source_tree_roots()
    metadata_within_prefix = _path_is_within(metadata_path, prefix)
    within_prefix = _path_is_within(module_path, prefix)
    in_source_tree = any(_path_is_within(module_path, root / "src") for root in source_roots)
    details.update(
        {
            "module_file": str(module_path),
            "metadata_within_sys_prefix": metadata_within_prefix,
            "within_sys_prefix": within_prefix,
            "in_source_tree": in_source_tree,
        }
    )
    if not metadata_within_prefix:
        errors.append(
            "scirel distribution metadata is outside the current environment prefix: "
            f"{metadata_path}"
        )
    if not within_prefix:
        errors.append(f"scirel module is outside the current environment prefix: {module_path}")
    if in_source_tree:
        errors.append(f"scirel module resolves to a source checkout: {module_path}")
    if errors:
        return details, errors, dist
    details["status"] = "PASS"
    return details, errors, dist


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
        "native_source_file_count": 0,
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
                is_native_resource = name.startswith(
                    (
                        "scirel/kinetic/_fluidbw_native/",
                        "scirel/kinetic/_native/",
                        "scirel/kinetic/pdrk/_native/",
                    )
                )
                if is_native_resource:
                    details["native_resource_count"] += 1
                    if name.endswith(".m"):
                        details["native_source_file_count"] += 1

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


def _catalog_wheel_closure(root: Path, wheel: Path) -> tuple[dict[str, Any], list[str]]:
    """Check that every catalog implementation module is present in a wheel."""

    details: dict[str, Any] = {
        "status": "FAIL",
        "document_count": 0,
        "implementation_module_count": 0,
        "missing_modules": [],
    }
    documents = sorted((root / "catalog" / "examples").glob("*.json"))
    if not documents:
        details["status"] = "NOT_RUN"
        return details, []
    try:
        with ZipFile(wheel) as archive:
            members = set(archive.namelist())
    except (BadZipFile, OSError) as exc:
        return details, [f"catalog wheel closure could not read wheel: {exc}"]

    implementations: set[str] = set()
    errors: list[str] = []
    for path in documents:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            api = document["public_api"]["python"]
            implementations.add(implementation_module(root, api["module"], api["symbol"]))
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"catalog binding could not be resolved for {path.name}: {exc}")

    missing = sorted(
        implementation
        for implementation in implementations
        if implementation.replace(".", "/") + ".py" not in members
    )
    details["document_count"] = len(documents)
    details["implementation_module_count"] = len(implementations)
    details["missing_modules"] = missing
    if missing:
        errors.append("catalog implementation modules are absent from wheel: " + ", ".join(missing))
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


def _run_public_surface() -> tuple[dict[str, Any], list[str]]:
    """Resolve every installed domain and symbol advertised by ``__all__``.

    This is a discoverability check, not a numerical acceptance run.  Public
    constants and exception classes are valid exports, so the probe requires
    successful attribute resolution rather than callability.
    """

    details: dict[str, Any] = {
        "status": "FAIL",
        "domain_count": 0,
        "export_count": 0,
        "nested_package_count": 0,
        "nested_module_count": 0,
        "nested_export_count": 0,
        "failures": [],
    }
    failures: list[str] = []
    try:
        root = importlib.import_module("scirel")
    except Exception as exc:
        error = f"cannot import public root: {type(exc).__name__}: {exc}"
        details["failures"] = [error]
        return details, [f"public surface failed: {error}"]

    root_exports = getattr(root, "__all__", None)
    if not isinstance(root_exports, (list, tuple)) or not all(
        isinstance(name, str) and name for name in root_exports
    ):
        error = "scirel.__all__ is missing or contains invalid names"
        details["failures"] = [error]
        return details, [f"public surface failed: {error}"]
    if len(set(root_exports)) != len(root_exports):
        error = "scirel.__all__ contains duplicate names"
        details["failures"] = [error]
        return details, [f"public surface failed: {error}"]

    for domain_name in root_exports:
        try:
            domain = getattr(root, domain_name)
        except Exception as exc:
            failures.append(
                f"domain {domain_name!r} cannot be resolved: {type(exc).__name__}: {exc}"
            )
            continue
        if not isinstance(domain, ModuleType):
            failures.append(f"root export {domain_name!r} is not a module")
            continue
        expected_name = f"scirel.{domain_name}"
        if domain.__name__ != expected_name:
            failures.append(
                f"root export {domain_name!r} resolves to {domain.__name__!r}, expected {expected_name!r}"
            )
            continue
        details["domain_count"] += 1
        exports = getattr(domain, "__all__", None)
        if not isinstance(exports, (list, tuple)) or not all(
            isinstance(name, str) and name for name in exports
        ):
            failures.append(f"domain {expected_name} has invalid __all__")
            continue
        if len(set(exports)) != len(exports):
            failures.append(f"domain {expected_name} has duplicate __all__ names")
            continue
        for export_name in exports:
            details["export_count"] += 1
            try:
                getattr(domain, export_name)
            except Exception as exc:
                failures.append(
                    f"{expected_name}.{export_name} cannot be resolved: {type(exc).__name__}: {exc}"
                )

    # Some public packages are intentionally nested below a domain facade.
    # Discover those packages from the installed namespace instead of keeping
    # a permanent list of capability counts in the validator.
    kinetic = getattr(root, "kinetic", None)
    nested_packages = []
    if isinstance(kinetic, ModuleType) and hasattr(kinetic, "__path__"):
        nested_packages = [
            info.name
            for info in pkgutil.iter_modules(kinetic.__path__, prefix="scirel.kinetic.")
            if info.ispkg and not info.name.rsplit(".", 1)[-1].startswith("_")
        ]
    for package_name in sorted(nested_packages):
        try:
            package = importlib.import_module(package_name)
        except Exception as exc:
            failures.append(
                f"nested package {package_name!r} cannot be resolved: {type(exc).__name__}: {exc}"
            )
            continue
        details["nested_package_count"] += 1
        exports = getattr(package, "__all__", None)
        if not isinstance(exports, (list, tuple)) or not all(
            isinstance(name, str) and name for name in exports
        ):
            failures.append(f"nested package {package_name} has invalid __all__")
            continue
        if len(set(exports)) != len(exports):
            failures.append(f"nested package {package_name} has duplicate __all__ names")
            continue
        for export_name in exports:
            try:
                child = getattr(package, export_name)
            except Exception as exc:
                failures.append(
                    f"{package_name}.{export_name} cannot be resolved: {type(exc).__name__}: {exc}"
                )
                continue
            if not isinstance(child, ModuleType):
                failures.append(f"nested package export {package_name}.{export_name} is not a module")
                continue
            expected_name = f"{package_name}.{export_name}"
            if child.__name__ != expected_name:
                failures.append(
                    f"nested package export {package_name}.{export_name} resolves to {child.__name__!r}, "
                    f"expected {expected_name!r}"
                )
                continue
            details["nested_module_count"] += 1
            child_exports = getattr(child, "__all__", None)
            if not isinstance(child_exports, (list, tuple)) or not all(
                isinstance(name, str) and name for name in child_exports
            ):
                failures.append(f"nested module {expected_name} has invalid __all__")
                continue
            if len(set(child_exports)) != len(child_exports):
                failures.append(f"nested module {expected_name} has duplicate __all__ names")
                continue
            for child_export_name in child_exports:
                details["nested_export_count"] += 1
                try:
                    getattr(child, child_export_name)
                except Exception as exc:
                    failures.append(
                        f"{expected_name}.{child_export_name} cannot be resolved: "
                        f"{type(exc).__name__}: {exc}"
                    )

    details["failures"] = failures
    if not failures:
        details["status"] = "PASS"
        return details, []
    return details, [
        f"public surface has {len(failures)} unresolved export(s): " + "; ".join(failures)
    ]


def validate_installed_wheel(
    *,
    expected_platform: str | None = None,
    expected_python: str = DEFAULT_EXPECTED_PYTHON,
    wheel_path: Path | None = None,
    catalog_root: Path | None = None,
    extras: tuple[str, ...] = (),
) -> dict[str, Any]:
    runtime, errors = _runtime_identity(expected_platform, expected_python)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "FAIL",
        "artifact": {},
        "wheel_payload": {},
        "catalog_wheel_closure": {},
        "runtime": runtime,
        "package": {},
        "dependencies": [],
        "extras": {},
        "pip_check": {},
        "simple_operator": {},
        "cross_domain_task": {},
        "public_surface": {},
        "errors": errors.copy(),
    }
    package, package_errors, distribution = _check_distribution()
    receipt["package"] = package
    receipt["errors"].extend(package_errors)
    if wheel_path is not None:
        artifact, artifact_errors = _wheel_artifact(wheel_path.resolve())
        receipt["artifact"] = artifact
        receipt["errors"].extend(artifact_errors)
        payload, payload_errors = _wheel_payload(wheel_path.resolve())
        receipt["wheel_payload"] = payload
        receipt["errors"].extend(payload_errors)
        if catalog_root is not None:
            closure, closure_errors = _catalog_wheel_closure(
                catalog_root.resolve(), wheel_path.resolve()
            )
            receipt["catalog_wheel_closure"] = closure
            receipt["errors"].extend(closure_errors)
    try:
        receipt["dependencies"] = _check_dependencies()
    except Exception as exc:
        receipt["errors"].append(f"declared dependency inspection failed: {type(exc).__name__}: {exc}")
    for item in receipt["dependencies"]:
        if item.get("status") != "PASS":
            receipt["errors"].append(
                f"declared dependency failed import: {item.get('name', '<unknown>')}"
            )
    seen_extras: set[str] = set()
    available_extras = _available_extras(distribution)
    for raw_extra in extras:
        extra = raw_extra.strip().lower()
        if not extra or extra in seen_extras:
            continue
        seen_extras.add(extra)
        extra_details: dict[str, Any] = {
            "status": "FAIL",
            "dependencies": [],
            "smoke": {},
        }
        receipt["extras"][extra] = extra_details
        if extra not in available_extras:
            error = f"optional extra is not declared by the installed distribution: {extra}"
            extra_details["error"] = error
            receipt["errors"].append(error)
            continue
        try:
            extra_requirements = _declared_extra_requirements(extra)
            extra_details["declared_requirements"] = extra_requirements
            extra_details["dependencies"] = _check_dependencies(extra_requirements)
        except Exception as exc:
            error = f"extra dependency inspection failed for {extra}: {type(exc).__name__}: {exc}"
            extra_details["error"] = error
            receipt["errors"].append(error)
            continue
        dependency_failed = False
        for item in extra_details["dependencies"]:
            if item.get("status") != "PASS":
                dependency_failed = True
                receipt["errors"].append(
                    f"extra dependency failed import ({extra}): {item.get('name', '<unknown>')}"
                )
        smoke, smoke_errors = _run_extra_smoke(extra)
        extra_details["smoke"] = smoke
        receipt["errors"].extend(smoke_errors)
        if not dependency_failed and not smoke_errors:
            extra_details["status"] = "PASS"
        else:
            extra_details["status"] = "FAIL"
    pip_check, pip_errors = _run_pip_check()
    receipt["pip_check"] = pip_check
    receipt["errors"].extend(pip_errors)
    simple, simple_errors = _run_simple_operator()
    receipt["simple_operator"] = simple
    receipt["errors"].extend(simple_errors)
    cross_domain, cross_errors = _run_cross_domain_task()
    receipt["cross_domain_task"] = cross_domain
    receipt["errors"].extend(cross_errors)
    public_surface, public_surface_errors = _run_public_surface()
    receipt["public_surface"] = public_surface
    receipt["errors"].extend(public_surface_errors)
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
    parser.add_argument(
        "--catalog-root",
        type=Path,
        help="source checkout whose catalog implementation modules must be present in --wheel",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        dest="extras",
        metavar="NAME",
        help="validate an installed optional extra; repeat for multiple extras",
    )
    parser.add_argument("--output", type=Path, help="write the JSON receipt to this path")
    args = parser.parse_args()
    try:
        receipt = validate_installed_wheel(
            expected_platform=args.expected_platform,
            expected_python=args.expected_python,
            wheel_path=args.wheel,
            catalog_root=args.catalog_root,
            extras=tuple(args.extras),
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
