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
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any

from public_api_binding import (
    canonical_binding,
    has_explicit_canonical_binding,
    implementation_module,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "scirel.capability-runtime-closure.v1"
_RESULT_PREFIX = "SCIREL_RUNTIME_RESULT="


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
    if not module.startswith("scirel"):
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
    if _root == "scirel" or _root in _stdlib or _root.startswith("_"):
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
    if probe is not None and (target is not None or asset_id is not None):
        raise ValueError("provide only one of --target, --asset-id, or --probe")
    if probe is None:
        target_info, module, symbol = _resolve_target(root, target=target, asset_id=asset_id)
    else:
        probe = probe.resolve()
        if not probe.is_file():
            raise ValueError(f"probe does not exist: {probe}")
        target_info, module, symbol = {"probe": str(probe)}, None, None

    source = _child_source(
        source_path=root / "src",
        module=module,
        symbol=symbol,
        probe=probe,
    )
    source_path = root / "src"
    if not source_path.is_dir():
        raise ValueError(f"source root has no src directory: {source_path}")
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-I", "-c", source],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    child_result: dict[str, Any] | None = None
    for line in reversed(completed.stderr.splitlines()):
        if line.startswith(_RESULT_PREFIX):
            try:
                child_result = json.loads(line[len(_RESULT_PREFIX) :])
            except json.JSONDecodeError:
                child_result = None
            break
    if child_result is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL",
            "target": target_info,
            "python": {"executable": sys.executable},
            "platform": {"system": platform.system(), "machine": platform.machine()},
            "loaded_module_count": 0,
            "loaded_scirel_modules": [],
            "external_import_roots": [],
            "distributions": [],
            "error": {
                "type": "ChildProcessError",
                "message": "child did not emit a runtime measurement",
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            },
            "duration_ms": duration_ms,
        }
    child_result["target"] = target_info
    child_result["source_root"] = str(root)
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
        result = {
            "schema": SCHEMA,
            "status": "FAIL",
            "target": {"target": args.target, "asset_id": args.asset_id, "probe": str(args.probe) if args.probe else None},
            "error": {"type": type(error).__name__, "message": str(error)},
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
