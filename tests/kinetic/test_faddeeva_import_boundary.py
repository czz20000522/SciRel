"""Fresh-process import boundary for the retained Faddeeva variants."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _run(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_faddeeva_variants_defer_scipy_until_axis_stabilization() -> None:
    result = _run(
        """
import sys
from scirel.numerics import evaluate_faddeeva
from scirel.numerics.special import evaluate_faddeeva as direct

assert evaluate_faddeeva is direct
assert "scipy" not in sys.modules
try:
    evaluate_faddeeva([])
except ValueError as error:
    assert "z" in str(error) and "scirel.numerics.faddeeva" in str(error)
else:
    raise AssertionError("empty Faddeeva input unexpectedly succeeded")
assert "scipy" not in sys.modules
try:
    evaluate_faddeeva(1j, order=0)
except TypeError as error:
    assert "order" in str(error) and "scirel.numerics.faddeeva" in str(error)
else:
    raise AssertionError("invalid Faddeeva order unexpectedly succeeded")
assert "scipy" not in sys.modules
result = evaluate_faddeeva(0.3 + 0.2j)
assert result.shape == ()
assert "scipy" not in sys.modules
result = evaluate_faddeeva(1j)
assert result.shape == ()
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_two_questions_reject_bad_inputs_and_controls_without_scipy() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel import kinetic, numerics
assert 'scipy' not in sys.modules
assert 'scirel.numerics.special' not in sys.modules
assert 'scirel.kinetic.plasma_dispersion' not in sys.modules
f = numerics.evaluate_faddeeva
z = kinetic.evaluate_plasma_dispersion
assert 'scipy' not in sys.modules
for bad, error_type in ((True, TypeError), ([1, False], TypeError), ('1', TypeError),
                        (np.ma.array([1j], mask=[False]), TypeError),
                        ([], ValueError), ([np.inf], ValueError), ([[1], [1, 2]], ValueError)):
    for method in ('scipy', 'rational', 'weideman', 'jpole'):
        try:
            z(bad, method=method)
        except error_type as error:
            assert 'z' in str(error) and 'scirel.kinetic.plasma-dispersion-function' in str(error)
        else:
            raise AssertionError('invalid family input succeeded')
    try:
        f(bad)
    except error_type as error:
        assert 'z' in str(error) and 'scirel.numerics.faddeeva' in str(error)
    else:
        raise AssertionError('invalid math input succeeded')
    assert 'scipy' not in sys.modules
for method, order in (('scipy', 32), ('weideman', 64), ('jpole', 10), ('rational', False), ('unknown', None)):
    try:
        z(1j, method=method, order=order)
    except TypeError:
        pass
    else:
        raise AssertionError('invalid numerical control succeeded')
    assert 'scipy' not in sys.modules
assert z(0.3+0.2j, method='rational')['w'].shape == ()
assert z(0.3+0.2j, method='jpole')['Z'].shape == ()
assert 'scipy' not in sys.modules
assert f(1j).shape == ()
assert 'scipy' in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
