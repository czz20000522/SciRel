"""Direct consumption and import boundaries for the migrated SVD operator."""

import importlib
import inspect
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
NAME = "compute_truncated_pseudoinverse"


def _run(source):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-B", "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_new_topic_namespace_is_lazy_and_discoverable():
    _run("""
import sys
import scirel.numerics as numerics
assert "compute_truncated_pseudoinverse" in dir(numerics)
assert "compute_truncated_pseudoinverse" in numerics.__all__
assert "linalg" in dir(numerics)
assert "scirel.numerics.linalg" not in sys.modules
from scirel.numerics import linalg
assert "compute_truncated_pseudoinverse" in dir(linalg)
assert linalg.__all__ == ["compute_truncated_pseudoinverse"]
assert "scirel.numerics.linalg.truncated_pseudoinverse" not in sys.modules
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
""")


@pytest.mark.parametrize("first", ["domain", "implementation"])
def test_import_orders_resolve_one_callable_without_scipy(first):
    imports = {
        "domain": "from scirel.numerics import compute_truncated_pseudoinverse as first",
        "implementation": "from scirel.numerics.linalg.truncated_pseudoinverse import compute_truncated_pseudoinverse as first",
    }
    _run(
        imports[first]
        + """
import sys
from scirel.numerics import compute_truncated_pseudoinverse as domain
from scirel.numerics.linalg import compute_truncated_pseudoinverse as topic
from scirel.numerics.linalg.truncated_pseudoinverse import compute_truncated_pseudoinverse as implementation
assert first is domain is topic is implementation
assert topic([[2.0]]).tolist() == [[0.5]]
assert "scipy" not in sys.modules
assert "scirel.geometry" not in sys.modules
"""
    )


def test_old_geometry_entry_and_module_are_absent():
    import scirel.geometry as geometry

    assert "truncated_svd_inverse" not in geometry.__all__
    assert "truncated_svd_inverse" not in dir(geometry)
    assert not hasattr(geometry, "truncated_svd_inverse")
    assert importlib.util.find_spec("scirel.geometry.truncated_svd_inverse") is None
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("scirel.geometry.truncated_svd_inverse")


def test_rcond_is_keyword_only_at_all_public_entrypoints():
    import numpy as np
    import scirel.numerics as numerics
    from scirel.numerics import linalg

    for namespace in (numerics, linalg):
        function = getattr(namespace, NAME)
        assert str(inspect.signature(function)) == "(mat, *, rcond=1e-10)"
        with pytest.raises(TypeError):
            function(np.eye(2), 1.0e-10)
        np.testing.assert_array_equal(function(np.eye(2), rcond=1.0e-10), np.eye(2))
