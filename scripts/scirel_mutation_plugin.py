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

KINDS = ("scale", "negate", "zero", "swap", "constant")


def _numpy():
    try:
        import numpy
    except ImportError:  # pragma: no cover - SciReL always has NumPy
        return None
    return numpy


def mutate(value, kind, record):
    """Return ``value`` with every numeric leaf mutated; call ``record()`` when anything changed."""
    np = _numpy()
    if isinstance(value, bool) or value is None or isinstance(value, (str, bytes)):
        return value
    if isinstance(value, dict):
        result = copy.copy(value)
        for key in list(result):
            result[key] = mutate(result[key], kind, record)
        return result
    if isinstance(value, (list, tuple)):
        items = [mutate(item, kind, record) for item in value]
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
            record()
            return np.ascontiguousarray(swapped)
        factor = {"scale": 10, "negate": -1, "zero": 0}[kind]
        record()
        return (value * factor).astype(value.dtype, copy=False)
    numeric_scalar = isinstance(value, (int, float, complex)) or (
        np is not None and isinstance(value, np.number)
    )
    if numeric_scalar:
        if kind == "swap":
            return value
        factor = {"scale": 10, "negate": -1, "zero": 0}[kind]
        record()
        return type(value)(value * factor)
    return value


def _wrap(function, kind, record):
    if kind == "constant":
        cache = []

        @functools.wraps(function)
        def constant(*args, **kwargs):
            result = function(*args, **kwargs)
            if not cache:
                cache.append(result)
                return result
            record()
            return copy.deepcopy(cache[0])

        return constant

    @functools.wraps(function)
    def mutant(*args, **kwargs):
        return mutate(function(*args, **kwargs), kind, record)

    return mutant


def pytest_configure(config):
    spec = json.loads(os.environ["SCIREL_MUTATION"])
    kind = spec["kind"]
    if kind not in KINDS:
        raise ValueError(f"unknown mutation kind {kind!r}; valid kinds are {', '.join(KINDS)}")
    log_path = os.environ["SCIREL_MUTATION_LOG"]

    def record():
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(kind + "\n")

    module = importlib.import_module(spec["module"])
    original = getattr(module, spec["symbol"])
    wrapped = _wrap(original, kind, record)
    setattr(module, spec["symbol"], wrapped)
    canonical = importlib.import_module(spec["canonical_module"])
    setattr(canonical, spec["canonical_symbol"], wrapped)
