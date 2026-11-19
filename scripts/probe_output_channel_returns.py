"""Classify what each baselined single-output contract's example actually returns.

Observe direct calls in the example to the callable bound by public_api.python.
Classify a completed return before the example indexes, unpacks or discards it.
An observed None is a return, not a missing observation. A mapping observation
says nothing about which keys a contract should promise.

Usage:
    python3 scripts/dev.py run python -B scripts/probe_output_channel_returns.py [--json PATH]

Exit 0 when every example ran successfully with one consistent observed return
kind and runtime type; exit 2 if a classification could not be established.
"""

from __future__ import annotations

import argparse
import ast
import collections
import contextlib
import importlib
import io
import json
import pathlib
import sys
import warnings

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = pathlib.Path("tools/docs/output-channel-baseline.json")
CATALOG = pathlib.Path("catalog/examples")


def classify(value: object) -> str:
    """Name the kind of object an example produced."""
    if value is None:
        return "none"
    module = type(value).__module__ or ""
    name = type(value).__name__
    if name == "Result" and "scirel" in module:
        return "Result"
    if isinstance(value, dict) or (hasattr(value, "keys") and not hasattr(value, "__array__")):
        return "mapping-like"
    if hasattr(value, "__array__") or isinstance(value, (int, float, complex, bool, tuple)):
        return "positional"
    if name == "SimpleNamespace":
        return "SimpleNamespace"
    if isinstance(value, list):
        return "list"
    if "Generator" in name:
        return "Generator"
    if "scirel" in module:
        return "scirel-object"
    return f"other:{name}"


def _observe(code: str, asset: str, api: dict) -> tuple[str, str]:
    target = getattr(importlib.import_module(api["module"]), api["symbol"])
    returns: set[tuple[str, str]] = set()

    def record(*args, **kwargs):
        value = target(*args, **kwargs)
        returns.add((classify(value), type(value).__name__))
        return value

    # f(...) becomes select(f)(...): aliases work, unrelated calls keep their caller frame.
    def select(callee):
        return record if callee is target else callee

    tree = ast.parse(code, filename=asset)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    for call in calls:
        call.func = ast.Call(ast.Name("__probe_select__", ast.Load()), [call.func], [])
    compiled = compile(ast.fix_missing_locations(tree), asset, "exec")
    exec(compiled, {"__probe_select__": select})  # noqa: S102 - repo-owned example
    if not returns:
        raise ValueError("no completed direct call to the target")
    if len(returns) != 1:
        raise ValueError(f"inconsistent target returns: {sorted(returns)}")
    return returns.pop()


def probe(root: pathlib.Path) -> dict[str, dict]:
    baseline = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for entry in baseline["entries"]:
        asset = entry["asset_id"]
        document = json.loads((root / CATALOG / f"{asset}.json").read_text(encoding="utf-8"))
        code = (document.get("example") or {}).get("code") or ""
        dtype = (document.get("outputs") or [{}])[0].get("dtype")
        record: dict = {"asset": asset, "dtype": dtype}
        try:
            with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
                warnings.simplefilter("ignore")
                record["kind"], record["runtime_type"] = _observe(
                    code, asset, document["public_api"]["python"]
                )
        except (Exception, SystemExit) as error:  # a failed example must not exit the probe
            record["kind"] = "no-candidate"
            record["error"] = f"{type(error).__name__}: {error}"[:140]
        out[asset] = record
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", default=None, help="write the per-asset classification here")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root).resolve()
    try:
        result = probe(root)
    except (OSError, KeyError, json.JSONDecodeError) as error:
        print(f"unobservable: {error}", file=sys.stderr)
        return 2
    counts = collections.Counter(record["kind"].split(":")[0] for record in result.values())
    for kind, number in counts.most_common():
        print(f"{number:3d}  {kind}")
    unobserved = counts.get("no-candidate", 0)
    print(f"{len(result)} baselined contracts; {unobserved} could not be classified")
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    return 2 if unobserved else 0


if __name__ == "__main__":
    raise SystemExit(main())
