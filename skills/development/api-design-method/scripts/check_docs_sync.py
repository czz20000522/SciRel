#!/usr/bin/env python3
"""Check public docstrings against signatures, required sections, unit notation and examples.

Usage: check_docs_sync.py PACKAGE [--src DIR] [--scope FILE] [--sections NAME ...]
                          [--unit-regex REGEX] [--no-doctest] [--list-only]

Checks each public callable, or each dotted name in --scope (one per line), for:
- a docstring with every required numpydoc section;
- a Parameters entry for each signature parameter, and none extra;
- a unit in each Parameters and Returns entry, if --unit-regex is given;
- Examples that run as doctests.
A scope file makes this a ratchet: strict for what is listed, silent about the rest.
"""

from __future__ import annotations

import argparse
import doctest
import importlib
import inspect
import json
from pathlib import Path
import re
import sys

from api_inventory import public_namespaces

ROOT = Path(__file__).resolve().parents[4]
SECTION = re.compile(r"^([A-Z][A-Za-z ]+)\n[ \t]*-{3,}[ \t]*$", re.M)
ENTRY = re.compile(r"^([A-Za-z_*][\w*, ]*?)\s*(?::.*)?$")


def split_sections(doc):
    marks = list(SECTION.finditer(doc))
    return {
        m.group(1): doc[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(doc)]
        for i, m in enumerate(marks)
    }


def entries(body):
    """Return {name: text} for the unindented entry lines of a numpydoc section."""
    result, current = {}, None
    for line in body.splitlines():
        if line and not line[0].isspace():
            found = ENTRY.match(line)
            if found:
                names = [n.strip().lstrip("*") for n in found.group(1).split(",")]
                current = names
                for name in names:
                    result[name] = line
                continue
        if current:
            for name in current:
                result[name] += "\n" + line
    return result


def mapping_signature(obj):
    """Use reviewed mapping ports when a public wrapper exposes a mapping."""
    if any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in inspect.signature(obj).parameters.values()
    ):
        return None
    path = ROOT / "scripts" / "mapping_interface_bindings.json"
    if not path.is_file():
        return None
    actual = f"{obj.__module__}.{obj.__name__}"
    for row in json.loads(path.read_text(encoding="utf-8"))["records"]:
        if row["callable"] != actual:
            continue
        return inspect.Signature(
            [
                inspect.Parameter(
                    port["name"],
                    inspect.Parameter.KEYWORD_ONLY,
                    default=inspect.Parameter.empty if port["required"] else port["default"],
                )
                for port in row["ports"]
            ]
        )
    return None


def check(name, obj, sections, unit_regex, run_doctest):
    problems = []
    doc = inspect.getdoc(obj)
    if not doc:
        return [f"{name}: no docstring"]
    found = split_sections(doc)
    try:
        signature = mapping_signature(obj) or inspect.signature(obj)
        parameters = [p for p in signature.parameters.values() if p.name not in ("self", "cls")]
    except (TypeError, ValueError):
        parameters = None
    for section in sections:
        if section == "Parameters" and parameters == []:
            continue
        if section == "Returns" and inspect.isclass(obj):
            continue
        if section not in found:
            problems.append(f"{name}: missing section {section}")
    if parameters is not None and "Parameters" in found:
        documented = entries(found["Parameters"])
        wanted = {p.name for p in parameters}
        problems += [
            f"{name}: parameter {p} not documented" for p in sorted(wanted - set(documented))
        ]
        problems += [
            f"{name}: documents unknown parameter {p}" for p in sorted(set(documented) - wanted)
        ]
    if unit_regex:
        for section in ("Parameters", "Returns"):
            for entry, text in entries(found.get(section, "")).items():
                if not unit_regex.search(text):
                    problems.append(f"{name}: {section} entry {entry} states no unit")
    if run_doctest and "Examples" in found:
        finder = doctest.DocTestFinder(recurse=False)
        runner = doctest.DocTestRunner(
            verbose=False, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
        )
        globs = dict(vars(sys.modules[obj.__module__]))
        for test in finder.find(obj, name, globs=globs):
            runner.run(test, out=lambda _: None)
        if runner.failures:
            problems.append(f"{name}: Examples fail as doctests")
    return problems


def resolve(dotted):
    module, _, attribute = dotted.rpartition(".")
    return getattr(importlib.import_module(module), attribute)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("package")
    parser.add_argument("--src")
    parser.add_argument("--scope", help="file with one dotted public name per line")
    parser.add_argument(
        "--sections", nargs="*", default=["Parameters", "Returns", "Raises", "See Also", "Examples"]
    )
    parser.add_argument(
        "--unit-regex", help="regular expression that each parameter and return entry must match"
    )
    parser.add_argument("--no-doctest", action="store_true")
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="print the names that would be checked, as a starter scope",
    )
    args = parser.parse_args()
    if args.src:
        sys.path.insert(0, args.src)
    if args.scope:
        names = [
            n.strip()
            for n in Path(args.scope).read_text(encoding="utf-8").splitlines()
            if n.strip() and not n.startswith("#")
        ]
    else:
        package = importlib.import_module(args.package)
        names = [
            f"{ns.__name__}.{n}"
            for ns in public_namespaces(package)
            for n in getattr(ns, "__all__", [])
            if callable(getattr(ns, n))
        ]
    if args.list_only:
        print("\n".join(names))
        return 0
    unit = re.compile(args.unit_regex) if args.unit_regex else None
    problems = []
    for name in names:
        problems += check(name, resolve(name), args.sections, unit, not args.no_doctest)
    for problem in problems:
        print(problem)
    print(f"{len(names)} names checked; {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
