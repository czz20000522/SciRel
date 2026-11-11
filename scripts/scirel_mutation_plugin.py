"""Pytest plugin that replaces one public SciReL callable with an output mutant.

Loaded by ``scripts/mutation_check.py`` with ``-p scirel_mutation_plugin``. The mutant is described
by the ``SCIREL_MUTATION`` environment variable (JSON with module, symbol, canonical_module,
canonical_symbol and kind). Each time the mutation changes a returned value, the kind is appended
to the file named by ``SCIREL_MUTATION_LOG`` so the driver can tell "tests caught it" from "tests
never exercised it".
"""

from __future__ import annotations

import copy
import functools
import importlib
import json
import os
from pathlib import Path

KINDS = ("scale", "negate", "zero", "swap", "constant")


def _numpy():
    try:
        import numpy
    except ImportError:  # pragma: no cover - SciReL always has NumPy
        return None
    return numpy


def _changed_numeric(before, after):
    """Compare exact returned values; changing zero to zero is not an exercised mutant."""
    np = _numpy()
    if isinstance(before, dict) and isinstance(after, dict):
        return any(_changed_numeric(before[k], after[k]) for k in before if k in after)
    if isinstance(before, (list, tuple)) and isinstance(after, (list, tuple)):
        return any(_changed_numeric(a, b) for a, b in zip(before, after))
    if isinstance(before, bool):
        return False
    if np is not None and isinstance(before, (int, float, complex, np.ndarray, np.number)):
        array = np.asarray(before)
        return array.dtype.kind in "iufc" and not np.array_equal(array, after, equal_nan=True)
    return False


def mutate(value, kind, record, applicable=lambda: None):
    """Return ``value`` with every numeric leaf mutated; call ``record()`` when anything changed."""
    np = _numpy()
    if isinstance(value, bool) or value is None or isinstance(value, (str, bytes)):
        return value
    if isinstance(value, dict):
        result = copy.copy(value)
        for key in list(result):
            result[key] = mutate(result[key], kind, record, applicable)
        return result
    if isinstance(value, (list, tuple)):
        items = [mutate(item, kind, record, applicable) for item in value]
        return type(value)(items) if not hasattr(value, "_fields") else type(value)(*items)
    if np is not None and isinstance(value, np.ndarray):
        if value.dtype.kind not in "iufc" or value.size == 0:
            return value
        if kind == "swap":
            if value.ndim >= 2:
                swapped = np.swapaxes(value, -1, -2)
            elif value.size > 1:
                swapped = value[::-1]
            else:
                return value
            applicable()
            if _changed_numeric(value, swapped):
                record()
            return np.ascontiguousarray(swapped)
        factor = {"scale": 10, "negate": -1, "zero": 0}[kind]
        result = (value * factor).astype(value.dtype, copy=False)
        if _changed_numeric(value, result):
            record()
        return result
    numeric_scalar = isinstance(value, (int, float, complex)) or (
        np is not None and isinstance(value, np.number)
    )
    if numeric_scalar:
        if kind == "swap":
            return value
        factor = {"scale": 10, "negate": -1, "zero": 0}[kind]
        result = type(value)(value * factor)
        if _changed_numeric(value, result):
            record()
        return result
    return value


def _wrap(function, kind, record, applicable=lambda: None):
    cache = []

    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        result = function(*args, **kwargs)
        if kind == "baseline":
            return result
        if kind == "constant":
            if not cache:
                cache.append(copy.deepcopy(result))
                return result
            if _changed_numeric(result, cache[0]):
                record()
            return copy.deepcopy(cache[0])
        return mutate(result, kind, record, applicable)

    return wrapped


class MutationEvidence:
    """Observe execution and output changes without changing pytest outcomes."""

    def __init__(self):
        self.selected = 0
        self.deselected = 0
        self.active = None
        self.completed = set()
        self.applied = set()
        self.applicable = set()
        self.call_failed = set()
        self.errors = []

    def pytest_collection_finish(self, session):
        self.selected = len(session.items)

    def pytest_deselected(self, items):
        self.deselected += len(items)

    def pytest_runtest_logstart(self, nodeid, location):
        self.active = nodeid

    def pytest_runtest_logfinish(self, nodeid, location):
        self.active = None

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.failed or report.skipped:
            self.completed.add(report.nodeid)
        if report.failed:
            if report.when == "call":
                self.call_failed.add(report.nodeid)
            else:
                self.errors.append(f"{report.nodeid} ({report.when})")


def pytest_configure(config):
    spec = json.loads(os.environ["SCIREL_MUTATION"])
    kind = spec["kind"]
    if kind not in (*KINDS, "baseline"):
        raise ValueError(f"unknown mutation kind {kind!r}; valid kinds are {', '.join(KINDS)}")
    log_path = os.environ["SCIREL_MUTATION_LOG"]
    evidence = MutationEvidence()
    config.pluginmanager.register(evidence, "scirel_mutation_evidence")

    def record():
        if evidence.active is not None:
            evidence.applied.add(evidence.active)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(kind + "\n")

    def applicable():
        if evidence.active is not None:
            evidence.applicable.add(evidence.active)

    module = importlib.import_module(spec["module"])
    original = getattr(module, spec["symbol"])
    wrapped = _wrap(original, kind, record, applicable)
    setattr(module, spec["symbol"], wrapped)
    canonical = importlib.import_module(spec["canonical_module"])
    setattr(canonical, spec["canonical_symbol"], wrapped)


def pytest_sessionfinish(session, exitstatus):
    evidence = session.config.pluginmanager.get_plugin("scirel_mutation_evidence")
    report = {
        "schema": 1,
        "exit_code": int(exitstatus),
        "selected": evidence.selected,
        "deselected": evidence.deselected,
        "executed": len(evidence.completed),
        "applied": sorted(evidence.applied),
        "applicable": sorted(evidence.applicable),
        "call_failed": sorted(evidence.call_failed),
        "errors": evidence.errors,
    }
    Path(os.environ["SCIREL_MUTATION_REPORT"]).write_text(json.dumps(report), encoding="utf-8")
