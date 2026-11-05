#!/usr/bin/env python3
"""Check that code docstrings and JSON contracts agree, for the assets in a scope list.

Source of truth: the code signature and its numpydoc docstring own parameter
names, order, defaults, units, return entries, raised exceptions and the
example. The JSON contract keeps the agent-only material (model, scope,
applicability, failure semantics, evidence, limitations); its fields that
overlap the docstring are derived and must agree. This script checks, per asset:

- ``public_api.signature`` equals the live signature;
- contract inputs match the signature's parameter names, order, required
  flags and defaults (skipped for ``**kwargs`` mapping callables, which the
  mapping binding checks);
- the docstring has Parameters (when there are inputs), Returns (for
  functions), Raises, See Also and Examples sections;
- every contract input and output has a docstring entry, and every
  dimensional unit appears in that entry as ``[unit]`` exactly as written in
  the contract; contract inputs supplied through ``**kwargs`` may be described
  in ``Other Parameters``;
- every exception named in ``failure_semantics`` is listed under Raises;
- the docstring Examples run as doctests and are the same code as the
  contract example;
- the Chinese reader record is bound to the current contract bytes;
- no phrase listed as stale for the asset appears in the contract, the
  reader record or the docstring.

Usage: check_contract_sync.py [--scope FILE] [asset_id ...]
"""

from __future__ import annotations

import argparse
import ast
import doctest
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
SCOPE = Path(__file__).with_name("contract_sync_scope.json")
DIMENSIONLESS = {"", "1", "dimensionless", "none", "-", "n/a"}
SECTION = re.compile(r"^([A-Z][A-Za-z ]+)\n-{3,}[ \t]*$", re.M)
ERROR = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Exception|Warning))\b")

sys.path.insert(0, str(ROOT / "scripts"))
from code_digest import source_digest  # noqa: E402


def sections(doc: str) -> dict[str, str]:
    marks = list(SECTION.finditer(doc))
    return {
        m.group(1).strip(): doc[
            m.end() : (marks[i + 1].start() if i + 1 < len(marks) else len(doc))
        ]
        for i, m in enumerate(marks)
    }


def entries(body: str) -> dict[str, str]:
    """Split a numpydoc Parameters/Returns body into ``name -> text`` (names may be comma-joined)."""
    out: dict[str, str] = {}
    current: list[str] = []
    for line in body.splitlines():
        if line and not line[0].isspace():
            head = line.split(" : ")[0].strip()
            current = [name.strip().lstrip("*") for name in head.split(",")]
            for name in current:
                out[name] = line + "\n"
        elif current:
            for name in current:
                out[name] += line + "\n"
    return out


def _json_value(value):
    return json.loads(json.dumps(value, default=repr))


def _code_ast(code: str) -> str:
    return ast.dump(ast.parse(code))


def _missing_direct_parameter_docs(params, parts: dict[str, str]) -> list[str]:
    """Return direct signature parameters missing from the Parameters section."""
    documented = entries(parts.get("Parameters", ""))
    return [
        parameter.name
        for parameter in params
        if parameter.kind not in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL)
        and parameter.name not in documented
    ]


def _mapping_signature(document: dict, obj) -> inspect.Signature | None:
    """Resolve a reviewed mapping wrapper to its declared scientific ports."""
    path = ROOT / "scripts" / "mapping_interface_bindings.json"
    if not path.is_file():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))["records"]
    binding = next((row for row in rows if row["asset_id"] == document["asset_id"]), None)
    if binding is None:
        return None
    actual = f"{obj.__module__}.{obj.__name__}"
    if binding["callable"] != actual:
        raise ValueError(f"mapping binding callable differs: {binding['callable']} != {actual}")
    for module_name, expected in binding["modules"].items():
        module = importlib.import_module(module_name)
        if source_digest(module.__file__) != expected:
            raise ValueError(f"mapping source binding differs: {module_name}")
    actual_ports = [
        {key: port[key] for key in ("name", "required", "default") if key in port}
        for port in document["inputs"]
    ]
    if actual_ports != binding["ports"]:
        raise ValueError("mapping scientific ports/defaults differ")
    return inspect.Signature(
        [
            inspect.Parameter(
                port["name"],
                inspect.Parameter.KEYWORD_ONLY,
                default=inspect.Parameter.empty if port["required"] else port["default"],
            )
            for port in binding["ports"]
        ]
    )


def check(asset: dict, root: Path = ROOT) -> list[str]:
    asset_id = asset["asset_id"]
    document = json.loads(
        (root / "catalog/examples" / f"{asset_id}.json").read_text(encoding="utf-8")
    )
    api = document["public_api"]["python"]
    obj = getattr(importlib.import_module(api["module"]), api["symbol"])
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(f"{asset_id}: {message}")

    live_signature = inspect.signature(obj)
    signature = live_signature
    if "inputs" in signature.parameters and not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        try:
            signature = _mapping_signature(document, obj) or signature
        except (ImportError, KeyError, OSError, ValueError) as error:
            fail(str(error))
    if api["signature"] != f"{api['symbol']}{live_signature}":
        fail(f"public_api.signature {api['signature']!r} != live {api['symbol']}{live_signature}")
    params = [p for p in signature.parameters.values()]
    direct_params = [p for p in params if p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)]
    inputs = document["inputs"]
    if not any(p.kind in (p.VAR_KEYWORD, p.VAR_POSITIONAL) for p in params):
        if [p.name for p in params] != [port["name"] for port in inputs]:
            fail(
                f"input names {[q['name'] for q in inputs]} != signature {[p.name for p in params]}"
            )
        else:
            for p, port in zip(params, inputs):
                required = p.default is inspect.Parameter.empty
                if port.get("required") != required:
                    fail(
                        f"input {p.name}: contract required={port.get('required')} but signature says {required}"
                    )
                if (
                    not required
                    and "default" in port
                    and _json_value(port["default"]) != _json_value(p.default)
                ):
                    fail(
                        f"input {p.name}: contract default {port['default']!r} != signature {p.default!r}"
                    )

    doc = inspect.getdoc(obj) or ""
    parts = sections(doc)
    needed = ["Raises", "See Also", "Examples"]
    if inputs or direct_params:
        needed.insert(0, "Parameters")
    if not inspect.isclass(obj):
        needed.insert(1 if inputs or direct_params else 0, "Returns")
    for name in needed:
        if name not in parts:
            fail(f"docstring has no {name} section")
    for name in _missing_direct_parameter_docs(params, parts):
        fail(f"Parameters has no entry for direct signature parameter {name!r}")
    for side, section in (("inputs", "Parameters"), ("outputs", "Returns")):
        if section not in parts:
            continue
        found = entries(parts[section])
        has_var_keyword = any(p.kind is p.VAR_KEYWORD for p in params)
        signature_names = {p.name for p in params}
        other = entries(parts.get("Other Parameters", "")) if side == "inputs" else {}
        for port in document[side]:
            text = found.get(port["name"])
            if text is None and has_var_keyword and port["name"] not in signature_names:
                text = other.get(port["name"])
            if text is None:
                where = "Parameters/Other Parameters" if side == "inputs" else section
                fail(f"{where} has no entry for {side[:-1]} {port['name']!r}")
            elif str(
                port.get("units", "")
            ).strip() not in DIMENSIONLESS and f"[{port['units']}]" not in " ".join(text.split()):
                fail(
                    f"{section} entry {port['name']!r} does not state the contract unit [{port['units']}]"
                )
    if "Raises" in parts:
        listed = set(ERROR.findall(parts["Raises"]))
        named = set(ERROR.findall(json.dumps(document["failure_semantics"])))
        for name in sorted(named - listed):
            fail(f"failure_semantics names {name} but Raises does not")

    if "Examples" in parts:
        tests = doctest.DocTestFinder(recurse=False).find(obj, api["symbol"], globs={})
        examples = [example for test in tests for example in test.examples]
        if not examples:
            fail("Examples section has no doctest")
        else:
            runner = doctest.DocTestRunner(
                optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
            )
            for test in tests:
                runner.run(test, out=lambda text: None)
            if runner.failures:
                fail(f"{runner.failures} docstring example(s) failed as doctests")
            source = "".join(example.source for example in examples)
            try:
                same = _code_ast(source) == _code_ast(document["example"]["code"])
            except SyntaxError as error:
                same = False
                fail(f"example does not parse: {error}")
            if not same:
                fail("contract example.code differs from the docstring Examples")

    zh_text = ""
    for path in sorted((root / "tools/docs/zh").glob("*.json")):
        for record in json.loads(path.read_text(encoding="utf-8"))["records"]:
            if record["asset_id"] == asset_id:
                zh_text = json.dumps(record, ensure_ascii=False)
                digest = hashlib.sha256(
                    (root / "catalog/examples" / f"{asset_id}.json").read_bytes()
                ).hexdigest()
                if record.get("source_sha256") != digest:
                    fail(f"{path.name} reader record is bound to an older contract")
    if not zh_text:
        fail("no Chinese reader record")
    contract_text = json.dumps(document, ensure_ascii=False)
    for phrase in asset.get("forbidden_phrases", []):
        for where, text in (
            ("contract", contract_text),
            ("reader record", zh_text),
            ("docstring", doc),
        ):
            if phrase.lower() in text.lower():
                fail(f"stale phrase {phrase!r} in the {where}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--scope", type=Path, default=SCOPE)
    parser.add_argument("asset_ids", nargs="*")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT / "src"))
    assets = json.loads(args.scope.read_text(encoding="utf-8"))["assets"]
    if args.asset_ids:
        assets = [a for a in assets if a["asset_id"] in args.asset_ids]
    errors = [error for asset in assets for error in check(asset)]
    for error in errors:
        print("ERROR:", error)
    print(f"contract sync: {len(assets)} assets, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
