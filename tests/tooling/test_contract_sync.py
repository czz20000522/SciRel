"""Regression tests for docstring/contract synchronization mechanics."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/development/scirel-acceptance/scripts/check_contract_sync.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_contract_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_direct_parameter_is_required_even_when_var_keyword_is_documented():
    module = _load()

    def sampled(inputs=None, **kwargs):
        pass

    parameters = list(inspect.signature(sampled).parameters.values())
    parts = module.sections(
        """Parameters
----------
**kwargs
    Named inputs merged into ``inputs``.
"""
    )
    assert module._missing_direct_parameter_docs(parameters, parts) == ["inputs"]


def test_direct_parameter_is_accepted_when_documented():
    module = _load()

    def sampled(inputs=None, **kwargs):
        pass

    parameters = list(inspect.signature(sampled).parameters.values())
    parts = module.sections(
        """Parameters
----------
inputs : mapping, optional
    Input mapping.
**kwargs
    Named inputs merged into ``inputs``.
"""
    )
    assert module._missing_direct_parameter_docs(parameters, parts) == []


def test_exception_names_include_custom_failure_types():
    module = _load()
    assert module.ERROR.findall("ContinuationFailure") == ["ContinuationFailure"]
