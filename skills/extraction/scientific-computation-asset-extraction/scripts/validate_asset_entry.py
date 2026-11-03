from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path


def validate(root: Path, expected_operators: int, expected_task_graphs: int) -> None:
    if os.environ.get("CODEFUSION_ASSET_SANDBOX") != "1":
        raise RuntimeError(
            "validate_asset_entry.py executes asset_entry.py and must run in the fixed sandbox"
        )
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    entry = root / "asset_entry.py"
    spec = importlib.util.spec_from_file_location("scientific_asset_entry", entry)
    if spec is None or spec.loader is None:
        raise ImportError(entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    bundle = module.load_asset_bundle(root)
    assets = bundle.list_assets()
    if not assets:
        raise AssertionError("asset entry must expose at least one scientific asset")
    operators = [asset for asset in assets if asset["kind"] == "operator"]
    graphs = [asset for asset in assets if asset["kind"] == "task_graph"]
    if len(operators) != expected_operators:
        raise AssertionError((len(operators), expected_operators))
    if len(graphs) != expected_task_graphs:
        raise AssertionError((len(graphs), expected_task_graphs))

    for asset in assets:
        description = bundle.describe_asset(asset["kind"], asset["name"])
        if description["name"] != asset["name"] or not description["contract"].strip():
            raise AssertionError(asset)

    for kind_assets in (operators, graphs):
        if not kind_assets:
            continue
        for asset in (kind_assets[0], kind_assets[-1]):
            if not bundle.find_assets(query=asset["name"], kind=asset["kind"]):
                raise AssertionError(asset)

    try:
        bundle.describe_asset("operator", "../escape")
    except ValueError:
        pass
    else:
        raise AssertionError("asset_entry must reject path traversal")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a bundle's discovery-only asset entry.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--operators", type=int, required=True)
    parser.add_argument("--task-graphs", type=int, required=True)
    args = parser.parse_args()
    validate(args.root, args.operators, args.task_graphs)
    print(
        f"asset-entry=ok operators={args.operators} "
        f"task_graphs={args.task_graphs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
