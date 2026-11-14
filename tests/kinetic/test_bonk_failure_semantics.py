"""Operator errors cannot be published as completed BONK search rows."""

import importlib
from types import SimpleNamespace

import numpy as np
import pytest

from scirel.kinetic.fluid_spectrum import derive_fluid_case, solve_fluid_bonk

MODULE = importlib.import_module("scirel.kinetic.fluid_spectrum")


@pytest.mark.parametrize("position", ("first", "middle", "last", "only"))
def test_genuine_harmonic_pole_is_not_hidden_by_later_success(position):
    state = derive_fluid_case("bonk", 2)
    pole = state["wcn"].item()
    normal = 0.63 * state["wn"].item()
    axes = {
        "first": [pole, normal],
        "middle": [normal, pole, normal],
        "last": [normal, pole],
        "only": [pole],
    }
    with pytest.raises(ValueError, match="pole"):
        solve_fluid_bonk(2, axes[position])


@pytest.mark.parametrize("exception", (ValueError, FloatingPointError, RuntimeError))
def test_search_does_not_swallow_operator_exceptions(monkeypatch, exception):
    state = derive_fluid_case("bonk", 2)
    error = exception("independent operator failure")

    def fail(*args, **kwargs):
        raise error

    # Patching a missing attribute on the lazy proxy would leave a shadowing
    # root attribute when monkeypatch restores it, hiding later backend spies.
    monkeypatch.setattr(MODULE, "optimize", SimpleNamespace(root=fail))
    with pytest.raises(exception, match="independent operator failure") as caught:
        solve_fluid_bonk(2, [0.63 * state["wn"].item()])
    assert caught.value is error, "Return the real cause, not a fabricated terminal failure."


def test_finite_bounded_nonconvergence_retains_real_attempts(monkeypatch):
    state = derive_fluid_case("bonk", 2)
    calls = []

    def terminate(fun, seed, *, method, options):
        assert method == "hybr"
        assert options == {"xtol": 1e-12, "maxfev": 100}
        q = np.asarray(seed, dtype=float)
        assert np.isfinite(fun(q)).all()
        calls.append(q.copy())
        return SimpleNamespace(x=q, status=2, nfev=100)

    monkeypatch.setattr(MODULE, "optimize", SimpleNamespace(root=terminate))
    result = solve_fluid_bonk(2, [0.63 * state["wn"].item()])
    rows = result["solver_attempts"][0, 0]
    assert len(calls) == rows.size == 5
    assert not result["root_valid"].item()
    candidates = np.array([row["candidate"].item() for row in rows.flat])
    expected = np.array([complex(*q) * state["kn"].item() for q in calls])
    np.testing.assert_array_equal(candidates, expected)
    assert np.isfinite(result["nf"]).all()
    assert result["nf"].item() in candidates
    assert all(row["solver_info"].item() == 2 for row in rows.flat)
