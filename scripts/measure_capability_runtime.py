"""Measure a single SciRel capability's fresh-process runtime import closure.

This is a development measurement aid.  It does not change the dependency
declaration, build metadata, release state, or scientific capability status.
The measurement runs in a child interpreter so the result is not polluted by
the caller's already-imported modules.  Import mode resolves an exact public
module (and optionally a symbol); probe mode executes a caller-owned probe
script for capabilities whose useful dependencies are only reached by a call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import tomllib
from typing import Any, Iterable

from public_api_binding import (
    canonical_binding,
    has_explicit_canonical_binding,
    implementation_module,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "scirel.capability-runtime-closure"
_RESULT_PREFIX = "SCIREL_RUNTIME_RESULT="
_CHILD_COMMAND = ("-I", "-c")


def _source_binding(root: Path) -> dict[str, Any]:
    """Return the Git and package identity of the measured source tree."""

    revision: str | None = None
    dirty = True
    try:
        revision_run = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if revision_run.returncode == 0:
            candidate = revision_run.stdout.strip()
            if len(candidate) == 40 and all(char in "0123456789abcdef" for char in candidate):
                revision = candidate
        status_run = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        dirty = status_run.returncode != 0 or bool(status_run.stdout.strip())
    except OSError:
        pass

    package_version: str | None = None
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        value = project.get("project", {}).get("version")
        if isinstance(value, str) and value:
            package_version = value
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, AttributeError):
        pass
    if package_version is None:
        try:
            from importlib.metadata import PackageNotFoundError, version

            package_version = version("scirel")
        except PackageNotFoundError:
            package_version = "0+unknown"

    return {
        "root": str(root),
        "revision": revision,
        "dirty": dirty,
        "package_version": package_version,
        "content_sha256": _source_content_sha256(root),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _optional_sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return _sha256(path)
    except OSError:
        return None


def _source_content_sha256(root: Path) -> str | None:
    paths = [root / "pyproject.toml"]
    source_root = root / "src"
    if source_root.is_dir():
        paths.extend(
            path
            for path in source_root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        )
    paths = sorted(
        path
        for path in paths
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        try:
            data = path.read_bytes()
        except OSError:
            return None
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _binding_status(
    source_before: dict[str, Any],
    source_after: dict[str, Any],
    probe_before: str | None,
    probe_after: str | None,
    *,
    extra_reasons: Iterable[str] = (),
) -> tuple[str, list[str]]:
    reasons: list[str] = list(extra_reasons)
    if source_before != source_after:
        reasons.append("source identity changed during measurement")
    if probe_before != probe_after:
        reasons.append("probe identity changed during measurement")
    if source_before.get("revision") is None:
        reasons.append("source revision is unavailable")
    if source_before.get("dirty") is True:
        reasons.append("source tree is dirty")
    if source_before.get("package_version") in {None, "0+unknown"}:
        reasons.append("package version is unavailable")
    reasons = sorted(set(reasons))
    return ("BOUND" if not reasons else "UNBOUND"), reasons


def _load_asset(root: Path, asset_id: str) -> dict[str, Any]:
    catalog = root / "catalog" / "examples"
    direct = catalog / f"{asset_id}.json"
    candidates = [direct] if direct.is_file() else sorted(catalog.glob("*.json"))
    for path in candidates:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if document.get("asset_id") == asset_id:
            return document
    raise ValueError(f"catalog asset not found: {asset_id}")


def _resolve_target(
    root: Path,
    *,
    target: str | None = None,
    asset_id: str | None = None,
) -> tuple[dict[str, str], str, str | None]:
    if (target is None) == (asset_id is None):
        raise ValueError("provide exactly one of --target, --asset-id, or --probe")
    if asset_id is not None:
        document = _load_asset(root, asset_id)
        python_api = document.get("public_api", {}).get("python", {})
        module = python_api.get("module")
        symbol = python_api.get("symbol")
        if not isinstance(module, str) or not module:
            raise ValueError(f"asset has no public Python module: {asset_id}")
        if symbol is not None and (not isinstance(symbol, str) or not symbol):
            raise ValueError(f"asset has an invalid public Python symbol: {asset_id}")
        implementation = implementation_module(root, module, symbol or "")
        if has_explicit_canonical_binding(python_api):
            load_module, load_symbol = canonical_binding(python_api)
        else:
            load_module, load_symbol = implementation, symbol
        return {
            "asset_id": asset_id,
            "module": load_module,
            "symbol": load_symbol or "",
            "implementation": implementation,
        }, load_module, load_symbol

    assert target is not None
    if ":" in target:
        module, symbol = target.split(":", 1)
        if not module or not symbol:
            raise ValueError(f"target must be module or module:symbol: {target!r}")
    else:
        module, symbol = target, None
    if module != "scirel" and not module.startswith("scirel."):
        raise ValueError(f"target must be a SciRel module: {module!r}")
    return {"module": module, "symbol": symbol or ""}, module, symbol


def _child_source(
    *,
    source_path: Path,
    module: str | None,
    symbol: str | None,
    probe: Path | None,
) -> str:
    module_literal = repr(module)
    symbol_literal = repr(symbol)
    probe_literal = repr(str(probe) if probe is not None else None)
    source_literal = repr(str(source_path))
    return f"""
import importlib
import importlib.metadata
import json
import platform
import runpy
import sys
import traceback

sys.path.insert(0, {source_literal})
_packages = importlib.metadata.packages_distributions()
_before = set(sys.modules)
_status = "PASS"
_error = None
try:
    _probe = {probe_literal}
    if _probe is not None:
        runpy.run_path(_probe, run_name="__main__")
    else:
        _module = importlib.import_module({module_literal})
        _symbol = {symbol_literal}
        if _symbol:
            getattr(_module, _symbol)
except BaseException as _exc:
    _status = "FAIL"
    _error = {{
        "type": type(_exc).__name__,
        "message": str(_exc),
        "traceback": traceback.format_exc(),
    }}

_stdlib = set(getattr(sys, "stdlib_module_names", ()))
_loaded = {{name for name, value in sys.modules.items() if value is not None}}
_new_loaded = _loaded - _before
_roots = set()
for _name in _new_loaded:
    _root = _name.split(".", 1)[0]
    if _root == "scirel" or _root in _stdlib:
        continue
    _roots.add(_root)

_distributions = []
for _root in sorted(_roots):
    _names = sorted(set(_packages.get(_root, ())))
    _versions = []
    for _name in _names:
        try:
            _versions.append({{"name": _name, "version": importlib.metadata.version(_name)}})
        except importlib.metadata.PackageNotFoundError:
            _versions.append({{"name": _name, "version": None}})
    _representative = sys.modules.get(_root)
    _file = getattr(_representative, "__file__", None)
    _distributions.append({{
        "import_root": _root,
        "distributions": _versions,
        "module_file": _file,
    }})

_result = {{
    "schema": "{SCHEMA}",
    "status": _status,
    "child_isolated": bool(getattr(sys.flags, "isolated", 0)),
    "python": {{
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "executable": sys.executable,
    }},
    "platform": {{"system": platform.system(), "machine": platform.machine()}},
    "loaded_module_count": len(_new_loaded),
    "loaded_scirel_modules": sorted(_name for _name in _new_loaded if _name == "scirel" or _name.startswith("scirel.")),
    "external_import_roots": sorted(_roots),
    "distributions": _distributions,
    "error": _error,
}}
print("{_RESULT_PREFIX}" + json.dumps(_result, ensure_ascii=False, sort_keys=True), file=sys.stderr)
if _status != "PASS":
    sys.exit(1)
"""


def _failure_result(
    *,
    mode: str,
    target: dict[str, str],
    source_before: dict[str, Any],
    source_after: dict[str, Any],
    probe_before: str | None,
    probe_after: str | None,
    binding_status: str,
    binding_reasons: list[str],
    error: dict[str, Any],
    child_returncode: int,
    duration_ms: float,
    isolated: bool = False,
    executed: bool = False,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL",
        "binding_status": binding_status,
        "binding_reasons": binding_reasons,
        "mode": mode,
        "target": target,
        "source": source_before,
        "source_after": source_after,
        "probe_sha256": probe_before,
        "probe_sha256_after": probe_after,
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "child": {
            "argv": [sys.executable, *_CHILD_COMMAND],
            "isolated": isolated,
            "executed": executed,
        },
        "child_returncode": child_returncode,
        "loaded_module_count": 0,
        "loaded_scirel_modules": [],
        "external_import_roots": [],
        "distributions": [],
        "error": error,
        "duration_ms": duration_ms,
    }


def measure(
    root: Path = ROOT,
    *,
    target: str | None = None,
    asset_id: str | None = None,
    probe: Path | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Measure one capability in a fresh child interpreter.

    ``target`` is ``scirel.module`` or ``scirel.module:symbol``.  ``asset_id``
    resolves the module and symbol from the exact catalog document.  ``probe``
    is a trusted Python script that performs the capability call; use it when
    import-only evidence does not reach the relevant lazy backend.
    """

    root = root.resolve()
    mode = "probe" if probe is not None else "import"
    if probe is not None and (target is not None or asset_id is not None):
        raise ValueError("provide only one of --target, --asset-id, or --probe")
    if probe is None:
        target_info, module, symbol = _resolve_target(root, target=target, asset_id=asset_id)
    else:
        probe = probe.resolve()
        if not probe.is_file():
            raise ValueError(f"probe does not exist: {probe}")
        target_info, module, symbol = {"probe": str(probe)}, None, None

    source_path = root / "src"
    if not source_path.is_dir():
        raise ValueError(f"source root has no src directory: {source_path}")
    source_before = _source_binding(root)
    probe_before = _optional_sha256(probe)
    source = _child_source(
        source_path=source_path,
        module=module,
        symbol=symbol,
        probe=probe,
    )
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, *_CHILD_COMMAND, source],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        child_error: dict[str, Any] | None = None
    except subprocess.TimeoutExpired as error:
        completed = None
        child_error = {"type": type(error).__name__, "message": str(error)}
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    source_after = _source_binding(root)
    probe_after = _optional_sha256(probe)
    binding_status, binding_reasons = _binding_status(
        source_before, source_after, probe_before, probe_after
    )
    child_result: dict[str, Any] | None = None
    if completed is not None:
        for line in reversed(completed.stderr.splitlines()):
            if line.startswith(_RESULT_PREFIX):
                try:
                    child_result = json.loads(line[len(_RESULT_PREFIX) :])
                except json.JSONDecodeError:
                    child_result = None
                break
    if child_result is None:
        binding_status = "UNBOUND"
        binding_reasons = sorted(
            set(binding_reasons) | {"child did not emit a runtime measurement"}
        )
        return _failure_result(
            mode=mode,
            target=target_info,
            source_before=source_before,
            source_after=source_after,
            probe_before=probe_before,
            probe_after=probe_after,
            binding_status=binding_status,
            binding_reasons=binding_reasons,
            error=child_error
            or {
                "type": "ChildProcessError",
                "message": "child did not emit a runtime measurement",
                "returncode": completed.returncode if completed is not None else -1,
                "stdout": completed.stdout[-4000:] if completed is not None else "",
                "stderr": completed.stderr[-4000:] if completed is not None else "",
            },
            child_returncode=completed.returncode if completed is not None else -1,
            duration_ms=duration_ms,
            executed=completed is not None,
        )
    child_isolated = bool(child_result.pop("child_isolated", False))
    if not child_isolated:
        binding_status = "UNBOUND"
        binding_reasons = sorted(
            set(binding_reasons) | {"child process was not isolated"}
        )
    child_result["target"] = target_info
    child_result["mode"] = mode
    child_result["binding_status"] = binding_status
    child_result["binding_reasons"] = binding_reasons
    child_result["source"] = source_before
    child_result["source_after"] = source_after
    child_result["probe_sha256"] = probe_before
    child_result["probe_sha256_after"] = probe_after
    child_result["child"] = {"argv": [sys.executable, *_CHILD_COMMAND], "isolated": child_isolated}
    child_result["child"]["executed"] = True
    child_result["child_returncode"] = completed.returncode
    child_result["duration_ms"] = duration_ms
    if completed.returncode != 0 and child_result.get("status") == "PASS":
        child_result["status"] = "FAIL"
    return child_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target", help="SciRel module or module:symbol")
    group.add_argument("--asset-id", help="catalog asset_id to resolve")
    group.add_argument("--probe", type=Path, help="trusted probe script")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output", type=Path, help="write the JSON result to this path")
    args = parser.parse_args(argv)
    try:
        result = measure(
            args.root,
            target=args.target,
            asset_id=args.asset_id,
            probe=args.probe,
            timeout=args.timeout,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        failure_root = args.root.resolve()
        source_before = _source_binding(failure_root)
        source_after = _source_binding(failure_root)
        probe_path = args.probe.resolve() if args.probe else None
        probe_before = _optional_sha256(probe_path)
        extra_reasons = ["measurement preflight failed"]
        if args.probe and probe_before is None:
            extra_reasons.append("probe input unavailable")
        binding_status, binding_reasons = _binding_status(
            source_before,
            source_after,
            probe_before,
            probe_before,
            extra_reasons=extra_reasons,
        )
        result = _failure_result(
            mode="probe" if args.probe else "import",
            target={
                "target": args.target or "",
                "asset_id": args.asset_id or "",
                "probe": str(probe_path) if probe_path is not None else "",
            },
            source_before=source_before,
            source_after=source_after,
            probe_before=probe_before,
            probe_after=probe_before,
            binding_status=binding_status,
            binding_reasons=binding_reasons,
            error={"type": type(error).__name__, "message": str(error)},
            child_returncode=-1,
            duration_ms=0.0,
        )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
