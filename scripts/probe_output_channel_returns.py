"""Classify what each baselined single-output contract's example actually returns.

Why this exists
---------------
92 single-output contracts do not state whether the caller receives a value
positionally or a field of a ``Result`` mapping (``tools/docs/output-channel-baseline.json``).
Paying that debt needs to know, per asset, what the example returns -- guessing
would write a sentence that is true for most and false for a few.

What it does
------------
Runs each baselined contract's own example in this interpreter, takes the first
name the example assigns, and classifies the resulting object:

    positional      array / scalar / tuple       -> the return value is the value
    scirel-object   a scirel instance            -> the returned instance is the value
    SimpleNamespace -> attributes live on the object
    list            -> the sequence is the value
    Generator       -> the caller iterates the return value
    mapping-like    a mapping                    -> **real ambiguity**: keys are the value,
                                                     so this belongs with T-2026-1203
    no-candidate    no name could be identified  -> needs a manual read

It writes nothing and judges no contract: the classification is evidence for a
later decision, not the decision.

Usage:
    PYTHONPATH=src python3 -B scripts/probe_output_channel_returns.py [--json PATH]

Exit status is the repository's three states: 0 every entry classified,
2 at least one entry could not be classified (unobserved -- NOT a pass).
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import io
import json
import pathlib
import re
import sys
import warnings

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = pathlib.Path("tools/docs/output-channel-baseline.json")
CATALOG = pathlib.Path("catalog/examples")


def classify(value: object) -> str:
    """Name the kind of object an example produced."""
    if value is None:
        return "no-candidate"
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


def probe(root: pathlib.Path) -> dict[str, dict]:
    baseline = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for entry in baseline["entries"]:
        asset = entry["asset_id"]
        document = json.loads((root / CATALOG / f"{asset}.json").read_text(encoding="utf-8"))
        code = (document.get("example") or {}).get("code") or ""
        dtype = (document.get("outputs") or [{}])[0].get("dtype")
        namespace: dict = {}
        record: dict = {"asset": asset, "dtype": dtype}
        try:
            with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
                warnings.simplefilter("ignore")
                exec(compile(code, asset, "exec"), namespace)  # noqa: S102 - repo-owned example
            assigned = re.findall(r"^\s*([A-Za-z_]\w*)\s*=", code, re.M)
            value = next(
                (
                    namespace[n]
                    for n in assigned
                    if n in namespace and not isinstance(namespace[n], type(sys))
                ),
                None,
            )
            record["kind"] = classify(value)
            record["runtime_type"] = type(value).__name__
        except Exception as error:  # noqa: BLE001 - a probe records, it does not raise
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
