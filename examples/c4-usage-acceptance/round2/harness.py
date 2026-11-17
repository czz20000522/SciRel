"""Blind-consumer harness for the C4 usage task list (round 2).

Everything here reads only the delivered package directory named by
``SCIREL_PACKAGE_ROOT``: ``catalog/contracts/*.json``, ``catalog/capability-index.json``,
``runtime.json`` and the installed wheel.  No file of this repository outside
``examples/c4-usage-acceptance/`` is read, and ``src/`` is never opened.

Public surface used per task:
  * ``contract(asset)``            -> the delivered asset document
  * ``discover(asset)``            -> the call arguments the contract's own example block uses
  * ``Ctx.call(...)``              -> one recorded public call (returned or raised)

Recorded per call: entrypoint, arguments, status, exception type/message, warnings and
returned field names.  Values are normalised to plain JSON (complex -> {real, imag}).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import math
import os
import warnings
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------- package access

PACKAGE_ROOT = Path(os.environ.get("SCIREL_PACKAGE_ROOT", "")).resolve()
if not (PACKAGE_ROOT / "catalog" / "contracts").is_dir():
    raise SystemExit(
        "SCIREL_PACKAGE_ROOT must point at a delivered package (catalog/contracts missing): "
        f"{PACKAGE_ROOT}"
    )


def runtime_json() -> dict:
    return json.loads((PACKAGE_ROOT / "runtime.json").read_text())


def capability_index() -> dict:
    return json.loads((PACKAGE_ROOT / "catalog" / "capability-index.json").read_text())


_CONTRACTS: dict[str, dict] = {}


def contract(asset: str) -> dict:
    if asset not in _CONTRACTS:
        path = PACKAGE_ROOT / "catalog" / "contracts" / f"{asset}.json"
        if not path.is_file():
            raise KeyError(f"asset not delivered: {asset}")
        _CONTRACTS[asset] = json.loads(path.read_text())
    return _CONTRACTS[asset]


def _api(asset: str) -> dict:
    return contract(asset)["public_api"]["python"]


def resolve(asset: str):
    api = _api(asset)
    module = importlib.import_module(api["module"])
    return module, api["symbol"], getattr(module, api["symbol"])


def signature(asset: str) -> inspect.Signature:
    _, _, fn = resolve(asset)
    return inspect.signature(fn)


def input_names(asset: str) -> list[str]:
    return [i["name"] for i in contract(asset)["inputs"]]


def output_names(asset: str) -> list[str]:
    return [o["name"] for o in contract(asset)["outputs"]]


# ---------------------------------------------------------------- JSON values


def plain(value, depth: int = 0):
    """Normalise a returned value to plain JSON."""
    if depth > 6:
        return "<depth-limit>"
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return {"nonfinite": repr(value)}
        return value
    if isinstance(value, complex):
        return {"real": plain(value.real), "imag": plain(value.imag)}
    if isinstance(value, np.generic):
        return plain(value.item(), depth + 1)
    if isinstance(value, np.ndarray):
        if np.iscomplexobj(value):
            return {
                "dtype": str(value.dtype),
                "shape": list(value.shape),
                "real": plain(value.real.tolist(), depth + 1),
                "imag": plain(value.imag.tolist(), depth + 1),
            }
        if value.dtype.kind == "U" or value.dtype.kind == "O":
            return {
                "dtype": str(value.dtype),
                "shape": list(value.shape),
                "values": [plain(v, depth + 1) for v in value.tolist()],
            }
        return {
            "dtype": str(value.dtype),
            "shape": list(value.shape),
            "values": plain(value.tolist(), depth + 1),
        }
    if isinstance(value, dict):
        return {str(k): plain(v, depth + 1) for k, v in value.items()}
    if hasattr(value, "keys") and hasattr(value, "__getitem__"):
        try:
            return {str(k): plain(value[k], depth + 1) for k in value.keys()}
        except Exception:  # pragma: no cover - defensive
            return repr(value)
    if isinstance(value, (list, tuple)):
        return [plain(v, depth + 1) for v in value]
    if isinstance(value, (set, frozenset)):
        return [plain(v, depth + 1) for v in sorted(value, key=repr)]
    if hasattr(value, "tolist"):
        try:
            return plain(value.tolist(), depth + 1)
        except Exception:  # pragma: no cover
            return repr(value)
    return repr(value)


def as_float(value) -> float:
    """Best-effort numeric reduction used by invariant checks."""
    if isinstance(value, complex):
        return float(abs(value))
    if isinstance(value, np.generic):
        return as_float(value.item())
    if isinstance(value, np.ndarray):
        arr = np.asarray(value)
        arr = arr[np.isfinite(arr)] if arr.size else arr
        return float(np.max(np.abs(arr))) if arr.size else 0.0
    return float(abs(value))


def rel_dev(a, b) -> float:
    """Componentwise max relative deviation between two numeric payloads."""

    def arr(x):
        if isinstance(x, dict) and {"real", "imag"} <= set(x):
            return np.asarray(x["real"], dtype=complex_like(x)) + 1j * np.asarray(x["imag"])
        if isinstance(x, dict) and "values" in x:
            return np.asarray(x["values"])
        if isinstance(x, np.ndarray):
            return x
        return np.asarray(x)

    aa, bb = arr(a), arr(b)
    if aa.shape != bb.shape:
        return float("inf")
    scale = np.maximum(np.abs(aa), np.abs(bb))
    diff = np.abs(aa - bb)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(scale > 0, diff / scale, diff)
    if np.iscomplexobj(ratio):
        ratio = np.abs(ratio)
    return float(np.nanmax(ratio)) if ratio.size else 0.0


def complex_like(x):
    return complex if (isinstance(x.get("imag"), (list, float, int))) else float


# ---------------------------------------------------------------- call recording


class CallRecord(dict):
    pass


class Ctx:
    """Per-task recorder."""

    def __init__(self, task: dict):
        self.task = task
        self.calls: list[dict] = []
        self.bindings: dict[str, dict] = {}
        self.notes: list[str] = []

    # -- argument discovery -------------------------------------------------
    def discover(self, asset: str) -> dict:
        if asset in self.bindings:
            return self.bindings[asset]
        binding = discover(asset)
        self.bindings[asset] = binding
        return binding

    def named(self, asset: str, index: int = 0) -> dict:
        """The contract example's first declared call.

        Examples sometimes end with a rejection probe; the first declared call is the
        documented nominal one.  Checks that need another declared variant ask for it by
        matching parameters through :meth:`pick`.
        """
        return dict(self.discover(asset)["variants"][index]["named"])

    def pick(self, asset: str, **match) -> dict:
        """Select the contract-example call whose named args match ``match``."""
        variants = self.discover(asset)["variants"]
        for variant in variants:
            if all(variant["named"].get(k) == v for k, v in match.items()):
                return dict(variant["named"])
        raise LookupError(
            f"no contract-example call of {asset} matches {match}; "
            f"variants={[sorted(v['named']) for v in variants]}"
        )

    # -- public calls -------------------------------------------------------
    def call(
        self, asset: str, named: dict | None = None, *, args=(), kwargs=None, label: str = ""
    ) -> dict:
        kwargs = dict(kwargs or {})
        if named is not None:
            args, kwargs = _args_for(asset, named)
        _, symbol, fn = resolve(asset)
        record = {
            "seq": len(self.calls) + 1,
            "label": label,
            "asset": asset,
            "entrypoint": f"{_api(asset)['module']}:{symbol}",
            "arguments": plain({"args": list(args), "kwargs": kwargs}),
            "status": None,
            "returned_fields": None,
            "exception": None,
            "warnings": [],
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                value = fn(*args, **kwargs)
            except BaseException as exc:  # noqa: BLE001 - the trace must keep the real type
                record["status"] = "raised"
                record["exception"] = {
                    "type": type(exc).__name__,
                    "module": type(exc).__module__,
                    "message": str(exc),
                    "qualname": f"{type(exc).__module__}.{type(exc).__qualname__}",
                }
                record["warnings"] = [f"{w.category.__name__}: {w.message}" for w in caught]
                self.calls.append(record)
                return record
            record["status"] = "returned"
            record["returned_type"] = type(value).__name__
            if hasattr(value, "keys"):
                record["returned_fields"] = sorted(str(k) for k in value.keys())
            record["warnings"] = [f"{w.category.__name__}: {w.message}" for w in caught]
            record["_value"] = value
            self.calls.append(record)
            return record

    def values(self) -> list:
        return [c["_value"] for c in self.calls if "_value" in c]


def _args_for(asset: str, named: dict):
    """Rebuild a positional/keyword call from a parameter-name mapping.

    A signature with ``*fields`` requires every parameter before the star to be passed
    positionally: passing it by keyword as well raises "got multiple values for argument".
    """
    sig = signature(asset)
    params = sig.parameters
    has_varargs = any(p.kind is p.VAR_POSITIONAL for p in params.values())
    args, kwargs = [], {}
    for pname, p in params.items():
        if pname not in named:
            continue
        if p.kind is p.POSITIONAL_ONLY:
            args.append(named[pname])
        elif p.kind is p.VAR_POSITIONAL:
            args.extend(named[pname])
        elif p.kind is p.VAR_KEYWORD:
            kwargs.update(named[pname])
        elif has_varargs and p.kind is p.POSITIONAL_OR_KEYWORD:
            args.append(named[pname])
        else:
            kwargs[pname] = named[pname]
    return tuple(args), kwargs


# ---------------------------------------------------------------- discovery

_DISCOVERY_CACHE: dict[str, dict] = {}


class _Recorder(ast.NodeTransformer):
    """Rewrites calls to the example's own alias of the entry into ``__c4_rec__(...)``.

    The example may import the entry under a local alias (``from m import long_name as
    short``) or reach it as an attribute of an imported module.  The local names that are
    *identical objects* to the delivered entry are found by executing the example's import
    statements first, and only calls through those names are rewritten.  No module of the
    delivered package is patched.
    """

    def __init__(self, names: set[str], attrs: set[str]):
        self.names = names
        self.attrs = attrs
        self.hits = 0

    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        hit = False
        if isinstance(node.func, ast.Name) and node.func.id in self.names:
            hit = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr in self.attrs:
            hit = True
        if hit:
            self.hits += 1
            node.func = ast.Name(id="__c4_rec__", ctx=ast.Load())
        return node


def discover(asset: str) -> dict:
    """Run the contract's own example block, capturing the arguments it passes.

    The example code is contract-supplied and travels inside the delivered package, so
    these arguments are frozen at freeze time and are not chosen by this consumer.
    Captured execution is *input discovery*, not a task call: it is recorded under
    ``bindings`` and never counted towards a task's call trace.
    """
    if asset in _DISCOVERY_CACHE:
        return _DISCOVERY_CACHE[asset]
    api = _api(asset)
    code = contract(asset)["example"]["code"]
    captured: list[tuple[tuple, dict]] = []
    real = resolve(asset)[2]

    def recorder(*a, **kw):
        captured.append((a, kw))
        return real(*a, **kw)

    tree = ast.parse(code, filename=f"<contract-example:{asset}>")
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    ns: dict = {"__name__": "__c4_contract_example__"}
    for node in imports:
        exec(
            compile(
                ast.Module(body=[node], type_ignores=[]),
                f"<contract-example-import:{asset}>",
                "exec",
            ),
            ns,
        )
    names = {name for name, value in ns.items() if value is real}
    attrs = {api["symbol"]}
    canon = api.get("canonical_symbol")
    if canon:
        attrs.add(canon)
    transform = _Recorder(names, attrs)
    tree = transform.visit(tree)
    ast.fix_missing_locations(tree)
    if transform.hits == 0:
        raise RuntimeError(
            f"contract example for {asset} never calls {api['symbol']}; names bound to it: "
            f"{sorted(names)}; example code:\n{code}"
        )
    ns["__c4_rec__"] = recorder
    error = None
    try:
        exec(compile(tree, f"<contract-example:{asset}>", "exec"), ns)
    except BaseException as exc:  # noqa: BLE001 - recorded, not swallowed silently
        error = {"type": type(exc).__name__, "message": str(exc)}
    if not captured:
        raise RuntimeError(
            f"contract example for {asset} did not reach {api['symbol']}; "
            f"error={error}; example code:\n{code}"
        )
    variants = []
    for args, kwargs in captured:
        bound = signature(asset).bind(*args, **kwargs)
        bound.apply_defaults()
        variants.append(
            {"named": dict(bound.arguments), "positional_count": len(args), "kwargs": kwargs}
        )
    result = {
        "asset": asset,
        "symbol": api["symbol"],
        "source": "contract.example",
        "named": variants[0]["named"],
        "positional_count": variants[0]["positional_count"],
        "kwargs": variants[0]["kwargs"],
        "variants": variants,
        "example_error": error,
    }
    _DISCOVERY_CACHE[asset] = result
    return result


def _copy(value):
    """Deep-ish copy so a scaled call cannot mutate the frozen binding."""
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, (list, tuple)):
        return [_copy(v) for v in value]
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    return value


def _scale_value(value, factor):
    arr = np.asarray(value, dtype=float) * factor
    return arr.tolist() if isinstance(value, list) else (arr.item() if arr.ndim == 0 else arr)


def scaled(named: dict, factors: dict) -> dict:
    """Return a copy of ``named`` with per-parameter power-of-two factors applied."""
    out = {k: _copy(v) for k, v in named.items()}
    for key, factor in factors.items():
        if key not in out:
            raise KeyError(f"parameter {key!r} not in binding: {sorted(out)}")
        out[key] = _scale_value(out[key], factor)
    return out


def mapping(value, asset: str) -> dict:
    """Normalise a returned value to a name->value mapping.

    Some published entries return a single array or a float instead of a recorded mapping;
    in that case the value is bound to the single declared output name of the contract.
    """
    if hasattr(value, "keys"):
        return {str(k): value[k] for k in value.keys()}
    names = output_names(asset)
    if len(names) == 1:
        return {names[0]: value}
    return {"value": value}


def arg(named: dict, asset: str, index: int):
    """Return the argument at positional ``index`` of the declared signature."""
    order = list(signature(asset).parameters)
    return named[order[index]]


def argnames(asset: str) -> list[str]:
    return list(signature(asset).parameters)


# ---------------------------------------------------------------- criteria


def check_fields(ctx: Ctx, call: dict, asset: str) -> dict:
    declared = sorted(output_names(asset))
    got = call.get("returned_fields")
    if got is None:
        if call.get("status") == "raised":
            return {
                "status": "fail",
                "detail": {
                    "declared": declared,
                    "returned": "raised",
                    "exception": call.get("exception"),
                },
            }
        return {
            "status": "fail",
            "detail": {
                "declared": declared,
                "returned": f"a {call.get('returned_type')} value, not a mapping",
                "note": "the contract declares named outputs; this return carries no "
                "field names, so the declared output set cannot be observed",
            },
        }
    return {
        "status": "pass" if got == declared else "fail",
        "detail": {"declared": declared, "returned": got},
    }


def check_parameters(named: dict, asset: str, expected: list[str]) -> dict:
    declared = input_names(asset)
    used = sorted(named)
    missing = [n for n in expected if n not in used]
    undeclared = [n for n in used if n not in declared]
    status = "pass" if not missing and not undeclared else "fail"
    return {
        "status": status,
        "detail": {
            "contract_inputs": declared,
            "args_used": used,
            "criteria_names_present": missing,
            "undeclared_args": undeclared,
        },
    }


def check_exception(ctx: Ctx, call: dict, asset: str, failure_key: str, expected: str) -> dict:
    quote = contract(asset)["failure_semantics"].get(failure_key)
    actual = call.get("exception")
    if quote is None:
        return {"status": "fail", "detail": f"contract has no failure_semantics[{failure_key!r}]"}
    declared_phrase = expected in quote
    met = False
    if actual:
        if actual["type"] == expected:
            met = True
        else:
            # a contract that names a base class is satisfied by any subclass of it
            try:
                raised = eval(actual["qualname"], {"builtins": __import__("builtins")})  # noqa: S307
                want = eval(expected, {"builtins": __import__("builtins")})  # noqa: S307
                met = isinstance(raised, want)
            except Exception:  # noqa: BLE001
                met = False
    return {
        "status": "pass" if (met and declared_phrase) else "fail",
        "detail": {
            "expected_exception": expected,
            "expected_appears_in_contract_quote": declared_phrase,
            "type_matches_exactly_or_by_subclass": met,
            "contract_quote": quote,
            "actual": actual,
        },
    }


def check_tolerance(
    observed: float, rel: float, abs_: float = 0.0, quantity: str = "", unit: str = ""
) -> dict:
    rel if observed == observed else math.inf
    ok = observed <= rel or observed <= abs_
    return {
        "status": "pass" if ok else "fail",
        "detail": {
            "quantity": quantity,
            "unit": unit,
            "observed_relative_deviation": observed,
            "declared_tolerance": {"rel": rel, "abs": abs_},
        },
    }


def gap(level: str, text: str) -> dict:
    return {"level": level, "text": text}
