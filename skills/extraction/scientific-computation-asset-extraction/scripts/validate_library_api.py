"""Check the minimum library-ready entry protocol for one asset bundle."""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from pathlib import Path


REQUIRED_METHODS = {
    "list_assets",
    "describe_asset",
    "find_assets",
    "operator_callable",
    "task_graph_callable",
    "asset_callable",
}


def validate(root: Path) -> None:
    if os.environ.get("CODEFUSION_ASSET_SANDBOX") != "1":
        raise RuntimeError("validate_library_api.py must run in the fixed asset sandbox")
    entry = root / "asset_entry.py"
    spec = importlib.util.spec_from_file_location("library_asset_entry", entry)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {entry}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(root))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    bundle = module.load_asset_bundle(root)
    missing = sorted(name for name in REQUIRED_METHODS if not callable(getattr(bundle, name, None)))
    if missing:
        raise AssertionError(f"missing AssetBundle methods: {missing}")
    for name in ("load_asset_bundle", "load_operator", "load_task_graph"):
        if not callable(getattr(module, name, None)):
            raise AssertionError(f"missing root loader: {name}")
    operator = next((item for item in bundle.list_assets("operator")), None)
    graph = next((item for item in bundle.list_assets("task_graph")), None)
    if operator is None or graph is None:
        raise AssertionError("library-ready bundle must expose at least one operator and task graph")
    operator_callable = bundle.operator_callable(f"operators/{operator['name']}")
    graph_callable = bundle.task_graph_callable(f"task_graphs/{graph['name']}")
    if not callable(operator_callable) or not callable(graph_callable):
        raise AssertionError("canonical asset resolvers must return callables")
    signatures = {
        "operator_callable": inspect.signature(bundle.operator_callable),
        "task_graph_callable": inspect.signature(bundle.task_graph_callable),
        "asset_callable": inspect.signature(bundle.asset_callable),
    }
    if signatures["task_graph_callable"].parameters["callable_name"].default != "run_graph":
        raise AssertionError("task_graph_callable default must be run_graph")


if __name__ == "__main__":
    validate(Path(sys.argv[1]).resolve())
    print("library API gate: ok")
