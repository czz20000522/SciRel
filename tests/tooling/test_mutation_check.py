"""Output mutants are caught by strong tests and reported for weak ones."""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("mutation_check", ROOT / "scripts/mutation_check.py")
mutation_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mutation_check)
import scirel_mutation_plugin as plugin  # noqa: E402

MODULE = """
import numpy as np

def compute_double(x):
    return {"value": 2.0 * np.asarray(x, dtype=float), "flag": True}
"""
STRONG = """
import numpy as np
from demo_relation import compute_double

def test_values():
    np.testing.assert_allclose(compute_double([1.0, 3.0])["value"], [2.0, 6.0])

def test_second_point():
    np.testing.assert_allclose(compute_double([5.0, 7.0])["value"], [10.0, 14.0])
"""
WEAK = """
from demo_relation import compute_double

def test_runs():
    assert compute_double([1.0, 2.0])["value"] is not None
"""


def _tree(tmp_path, test_source):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/demo_relation.py").write_text(MODULE)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_demo.py").write_text(test_source)
    (tmp_path / "catalog/examples").mkdir(parents=True)
    contract = {
        "public_api": {"python": {"module": "demo_relation", "symbol": "compute_double"}},
        "verification": {"tests": ["tests/test_demo.py"]},
    }
    (tmp_path / "catalog/examples/scirel.demo.double.json").write_text(json.dumps(contract))
    return tmp_path


def test_mutate_changes_every_numeric_leaf_and_keeps_the_rest():
    calls = []
    value = {"a": np.array([[1.0, 2.0], [3.0, 4.0]]), "n": 3, "flag": True, "name": "x"}
    scaled = plugin.mutate(value, "scale", lambda: calls.append(1))
    np.testing.assert_array_equal(scaled["a"], 10 * value["a"])
    assert scaled["n"] == 30 and scaled["flag"] is True and scaled["name"] == "x"
    swapped = plugin.mutate(value, "swap", lambda: calls.append(1))
    np.testing.assert_array_equal(swapped["a"], value["a"].T)
    assert calls


def test_strong_tests_kill_every_mutant(tmp_path):
    report = mutation_check.check_asset(_tree(tmp_path, STRONG), "scirel.demo.double")
    assert report["state"] == "passed", report
    assert set(report["mutants"].values()) == {"killed"}


def test_weak_tests_are_reported(tmp_path):
    report = mutation_check.check_asset(_tree(tmp_path, WEAK), "scirel.demo.double")
    assert report["state"] == "failed", report
    assert report["mutants"]["scale"] == "survived"
    assert report["mutants"]["constant"] == "not_exercised"


def test_missing_contract_is_an_error(tmp_path):
    report = mutation_check.check_asset(_tree(tmp_path, STRONG), "scirel.demo.absent")
    assert report["state"] == "error"
