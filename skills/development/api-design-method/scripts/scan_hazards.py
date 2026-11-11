#!/usr/bin/env python3
"""Find code patterns that often hide silent behaviour. Each hit is a prompt to read, not a verdict.

Usage: scan_hazards.py SOURCE_DIR [--baseline FILE] [--write-baseline FILE] [--json]

A baseline file records accepted hits by file, function and rule, without line numbers,
so that it survives edits. With --baseline only new hits are reported and fail the run.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
import math
from pathlib import Path

RULES = {
    "broad-except": "a broad except can turn a programming error into a result",
    "swallowed-exception": "an except body that does nothing hides the failure",
    "error-state-ignored": "floating-point errors are switched off; check the result is still checked",
    "non-finite-replaced": "non-finite values are replaced with numbers",
    "clip": "values are clamped; confirm this is documented and intended",
    "zeroed-by-condition": "values are overwritten by a condition; confirm it is documented",
    "zeroed-by-position": "the first or last array entry is overwritten by position, not by its value",
    "warning-filter": "warnings are hidden from the caller",
    "mutable-default": "a mutable default is shared between calls",
    "var-keyword": "**kwargs hides what the function accepts",
    "mapping-get-default": "a missing input silently falls back to a default",
    "bare-default-none-or": "`x or default` also replaces valid zero or empty values",
    "unused-parameter": "a parameter that is never used is silently ignored",
}
CLAMP_NAMES = {"clip", "clamp", "minimum", "maximum"}
REPLACE_NAMES = {"nan_to_num"}
NON_FINITE_NAMES = {"inf", "infinity", "infty", "nan", "NAN", "NaN", "NINF", "PINF"}
INPUT_MAPPINGS = {"inputs", "params", "parameters", "config", "options", "case", "kwargs", "settings"}


def call_name(node):
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""


def non_finite_literal(node):
    """Return whether an argument is a literal non-finite number, not a computed value.

    Covers a non-finite float constant, the names and attributes commonly used for
    infinity and NaN, and conversions of such a string, such as ``float("inf")``.
    """
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    if isinstance(node, ast.Constant):
        if isinstance(node.value, float):
            return not math.isfinite(node.value)
        if isinstance(node.value, str):
            try:
                return not math.isfinite(float(node.value))
            except ValueError:
                return False
        return False
    if isinstance(node, ast.Name):
        return node.id in NON_FINITE_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr in NON_FINITE_NAMES
    if isinstance(node, ast.Call):
        return any(non_finite_literal(argument) for argument in node.args)
    return False


class Visitor(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.scope = ["<module>"]
        self.hits = []

    def hit(self, rule, node):
        self.hits.append({"file": self.path, "function": ".".join(self.scope), "rule": rule, "line": node.lineno})

    def visit_FunctionDef(self, node):
        self.scope.append(node.name)
        self.check_function(node)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def check_function(self, node):
        args = node.args
        defaults = [*args.defaults, *[d for d in args.kw_defaults if d is not None]]
        if any(isinstance(d, (ast.List, ast.Dict, ast.Set)) for d in defaults):
            self.hit("mutable-default", node)
        if args.kwarg:
            self.hit("var-keyword", node)
        body = node.body[1:] if ast.get_docstring(node) is not None else node.body
        stub = not body or all(isinstance(s, (ast.Pass, ast.Raise)) for s in body)
        if not stub and not node.name.startswith("_") and not node.decorator_list:
            used = {n.id for s in body for n in ast.walk(s) if isinstance(n, ast.Name)}
            named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            if "locals" not in used and any(a.arg not in used and a.arg not in ("self", "cls") for a in named):
                self.hit("unused-parameter", node)

    def visit_ExceptHandler(self, node):
        broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"))
        reraises = any(isinstance(n, ast.Raise) for s in node.body for n in ast.walk(s))
        if broad and not reraises:
            self.hit("broad-except", node)
        if all(isinstance(s, (ast.Pass, ast.Continue)) for s in node.body):
            self.hit("swallowed-exception", node)
        self.generic_visit(node)

    def visit_Call(self, node):
        name = call_name(node)
        if name == "errstate" and any(
            isinstance(k.value, ast.Constant) and k.value.value == "ignore" for k in node.keywords
        ):
            self.hit("error-state-ignored", node)
        elif name in REPLACE_NAMES:
            self.hit("non-finite-replaced", node)
        elif name == "fill_diagonal":
            # ``fill_diagonal(a, value)`` writes a supplied value onto the diagonal of a
            # matrix under construction, so an ordinary call is assembly rather than a
            # replacement of non-finite entries. Only a literal non-finite fill value
            # matches the rule, in either its positional or its ``val=`` keyword form.
            fill_values = node.args[1:2] + [
                keyword.value for keyword in node.keywords if keyword.arg == "val"
            ]
            if any(non_finite_literal(value) for value in fill_values):
                self.hit("non-finite-replaced", node)
        elif name in CLAMP_NAMES:
            self.hit("clip", node)
        elif name in ("filterwarnings", "simplefilter", "catch_warnings"):
            self.hit("warning-filter", node)
        elif name == "where" and len(node.args) == 3 and any(
            isinstance(a, ast.Constant) and a.value in (0, 0.0) for a in node.args[1:]
        ):
            self.hit("zeroed-by-condition", node)
        elif (name == "get" and len(node.args) == 2 and isinstance(node.func, ast.Attribute)
              and isinstance(node.func.value, ast.Name) and node.func.value.id in INPUT_MAPPINGS):
            self.hit("mapping-get-default", node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if (isinstance(target, ast.Subscript) and isinstance(node.value, ast.Constant)
                    and node.value.value in (0, 0.0)):
                index = target.slice
                if (isinstance(index, ast.Constant) and index.value == 0) or (
                    isinstance(index, ast.UnaryOp) and isinstance(index.op, ast.USub)
                ):
                    self.hit("zeroed-by-position", node)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.Or) and isinstance(node.values[0], ast.Name):
            if isinstance(node.values[-1], ast.Constant) and node.values[-1].value is not None:
                self.hit("bare-default-none-or", node)
        self.generic_visit(node)


def scan(root):
    hits = []
    root = Path(root)
    for path in sorted(root.rglob("*.py")):
        visitor = Visitor(path.relative_to(root).as_posix())
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        hits.extend(visitor.hits)
    return hits


def key(hit):
    return f"{hit['file']}::{hit['function']}::{hit['rule']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source")
    parser.add_argument("--baseline")
    parser.add_argument("--write-baseline")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    hits = scan(args.source)
    if args.write_baseline:
        accepted = Counter(key(h) for h in hits)
        Path(args.write_baseline).write_text(json.dumps(dict(sorted(accepted.items())), indent=0) + "\n", encoding="utf-8")
        print(f"baseline written: {len(hits)} hits")
        return 0
    if args.baseline:
        allowed = Counter(json.loads(Path(args.baseline).read_text(encoding="utf-8")))
        new = []
        for hit in hits:
            if allowed[key(hit)] > 0:
                allowed[key(hit)] -= 1
            else:
                new.append(hit)
        hits = new
    if args.json:
        print(json.dumps(hits, indent=1))
    else:
        for hit in hits:
            print(f"{hit['file']}:{hit['line']} {hit['function']} [{hit['rule']}] {RULES[hit['rule']]}")
        print(Counter(h["rule"] for h in hits).most_common())
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
