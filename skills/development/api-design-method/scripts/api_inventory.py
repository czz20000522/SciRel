#!/usr/bin/env python3
"""List a package's public surface and flag interface problems.

Usage: api_inventory.py PACKAGE [--src DIR] [--name-pattern REGEX] [--documented FILE] [--json]

Public means: listed in `__all__` of the package or of one of its public subpackages.
--documented names a text file with one documented public name per line
("pkg.mod.name"); the two lists are compared in both directions.
Exit status is 1 if the documented list disagrees or a public name fails the pattern.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pkgutil
import re
import sys

SECTION = re.compile(r"^([A-Z][A-Za-z ]+)\n[ \t]*-{3,}[ \t]*$", re.M)
MAPPING_NAMES = {"inputs", "params", "parameters", "config", "options", "case", "kwargs"}


def public_namespaces(package):
    yield package
    for info in pkgutil.iter_modules(package.__path__):
        if info.ispkg and not info.name.startswith("_"):
            yield importlib.import_module(f"{package.__name__}.{info.name}")


def describe(namespace, name):
    obj = getattr(namespace, name)
    kind = "class" if inspect.isclass(obj) else "function" if callable(obj) else "module" if inspect.ismodule(obj) else "data"
    row = {"name": f"{namespace.__name__}.{name}", "kind": kind, "signature": None, "sections": [], "flags": []}
    if kind not in ("function", "class"):
        return row
    doc = inspect.getdoc(obj) or ""
    row["sections"] = SECTION.findall(doc)
    if not doc:
        row["flags"].append("no-docstring")
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        row["flags"].append("no-signature")
        return row
    row["signature"] = f"{name}{signature}"
    for parameter in signature.parameters.values():
        if parameter.kind is parameter.VAR_KEYWORD:
            row["flags"].append("var-keyword")
        elif parameter.name in MAPPING_NAMES:
            row["flags"].append(f"mapping-parameter:{parameter.name}")
        if isinstance(parameter.default, (list, dict, set)):
            row["flags"].append(f"mutable-default:{parameter.name}")
        if isinstance(parameter.default, bool) and parameter.kind is parameter.POSITIONAL_OR_KEYWORD:
            row["flags"].append(f"positional-flag:{parameter.name}")
    return row


def inventory(package_name):
    package = importlib.import_module(package_name)
    rows, undeclared = [], []
    for namespace in public_namespaces(package):
        names = getattr(namespace, "__all__", None)
        if names is None:
            undeclared.append(namespace.__name__)
            continue
        rows.extend(describe(namespace, name) for name in names)
    return rows, undeclared


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("package")
    parser.add_argument("--src", help="directory to put first on sys.path")
    parser.add_argument("--name-pattern", help="regular expression that public function names must match")
    parser.add_argument("--documented", help="file listing documented public names, one per line")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.src:
        sys.path.insert(0, args.src)
    rows, undeclared = inventory(args.package)
    problems = []
    counts = {}
    for row in rows:
        counts.setdefault(row["name"].rsplit(".", 1)[1], []).append(row["name"])
    duplicates = {short: names for short, names in counts.items() if len(names) > 1}
    if args.name_pattern:
        pattern = re.compile(args.name_pattern)
        for row in rows:
            short = row["name"].rsplit(".", 1)[1]
            if row["kind"] == "function" and not pattern.fullmatch(short):
                problems.append(f"name outside the pattern: {row['name']}")
    if args.documented:
        with open(args.documented, encoding="utf-8") as stream:
            documented = {line.strip() for line in stream if line.strip()}
        actual = {row["name"] for row in rows}
        problems += [f"public but undocumented: {name}" for name in sorted(actual - documented)]
        problems += [f"documented but not public: {name}" for name in sorted(documented - actual)]
    report = {"public": rows, "namespaces_without_all": undeclared, "same_name_in_several_namespaces": duplicates, "problems": problems}
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        for row in rows:
            flags = f"  !! {','.join(row['flags'])}" if row["flags"] else ""
            print(f"{row['kind']:8} {row['signature'] or row['name']}  [{'/'.join(row['sections'])}]{flags}")
        print(f"\n{len(rows)} public names; {sum(1 for r in rows if r['flags'])} flagged")
        print("namespaces without __all__:", undeclared)
        print("same name in several namespaces:", duplicates)
        for problem in problems:
            print("PROBLEM:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
