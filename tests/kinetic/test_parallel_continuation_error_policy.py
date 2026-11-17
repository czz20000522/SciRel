"""A bug in the residual must not be reported as a physics evaluation failure.

`_continue_em1d` used to catch `Exception` and wrap whatever came out into a
`ContinuationFailure` record with `evaluation_error=repr(cause)`. That made a
`TypeError` or `NameError` inside the residual indistinguishable from a legitimate
numerical failure at that `k`: the caller would see a physics status and stop, instead
of the bug surfacing. The code-style rule forbids exactly this shape
("must not turn a programming error into a physics status").

The handler is now narrow -- `(ArithmeticError, ValueError, np.linalg.LinAlgError)` --
so these two tests pin both directions.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic.dispersion import parallel_continuation as module
from scirel.kinetic.dispersion._fluid_parallel import ContinuationFailure

STATE = {"cwp": 1.0, "wcs1": 1.0}


def test_a_programming_error_propagates_unchanged(monkeypatch):
    def broken(*args, **kwargs):
        raise TypeError("residual got the wrong number of arguments")

    monkeypatch.setattr(module, "em1d_parallel_residual", broken)
    with pytest.raises(TypeError):
        module._continue_em1d(STATE, k_grid=[0.1, 0.2])


def test_a_genuine_evaluation_failure_still_becomes_a_record(monkeypatch):
    """A ValueError ends in a record rather than a crash -- but not through our handler.

    Measured here: ``scipy.optimize.root`` swallows a ``ValueError`` raised inside the
    residual and returns ``success=False`` instead of propagating, so the failure is
    reported by the post-solve check ("root not accepted"), not by the ``except``.
    ``TypeError`` and ``LinAlgError`` do propagate, which is what the other two tests
    pin. This one asserts the outcome, not the route, because the route belongs to
    SciPy and would change under us.
    """

    def failing(*args, **kwargs):
        raise ValueError("scaled residual left the declared domain")

    monkeypatch.setattr(module, "em1d_parallel_residual", failing)
    with pytest.raises(ContinuationFailure):
        module._continue_em1d(STATE, k_grid=[0.1])


def test_a_linear_algebra_failure_is_an_evaluation_failure(monkeypatch):
    def singular(*args, **kwargs):
        raise np.linalg.LinAlgError("singular Jacobian")

    monkeypatch.setattr(module, "em1d_parallel_residual", singular)
    with pytest.raises(ContinuationFailure):
        module._continue_em1d(STATE, k_grid=[0.1])
