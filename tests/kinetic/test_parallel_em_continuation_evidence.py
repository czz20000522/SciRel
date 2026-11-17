"""Independent evidence for the seeded parallel EM root continuation.

Why this file exists
--------------------
``continue_em1d`` is glue: it drives a fixed ``scipy.optimize.root(method="hybr")`` call on the
normalized residual, certifies each point, and feeds only certified roots forward.  Two failure modes
matter and neither is visible from a successful return:

* the certification could accept a point the solver did *not* resolve (a false success), and
* a failed point could still seed the next grid point, so the continuation silently becomes something
  else while returning plausible numbers.

The anchors below are:

1. **Analytic vacuum branch.**  With ``wps2 == 0`` the residual is exactly ``omega^2 - c2*k^2``, whose
   accepted branch is ``omega = +-sqrt(c2)*abs(k)``.  This is a closed-form solution, so the check does
   not depend on any solver behaviour beyond the values it returns.
2. **Success is equivalent to the residual bound, in both directions.**  Forward: every accepted record
   satisfies ``solver_success`` and ``scaled_residual <= residual_tolerance``.  Reverse: the *same*
   admissible point, driven with a tighter tolerance, must raise ``ContinuationFailure`` even though the
   solver reports success -- and the same call at the declared default tolerance must accept it.  Without
   the reverse direction a "success implies small residual" test cannot see a false success at all.
3. **A rejected point produces no successor row.**  Two independent constructions are used: a natural
   evaluation failure at the second grid point, and an exhausted evaluation budget at the first.  The
   failure record must name the failed point, carry the accepted prefix only as diagnostics, and the grid
   points after it must never be reached -- which is observable because one of them is shown to be
   acceptable on its own.

What this file does not claim
-----------------------------
* **No physical mode identity across the grid.**  Nothing here says the continued root is the same
  physical branch at every ``k``; the contract excludes that, and the analytic anchor exists only in the
  zero-density limit where the branch is unique.
* Non-vacuum *accuracy* is not claimed: the non-vacuum state is used only for the certification and
  seed-propagation properties, never as a physical reference.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.kinetic.dispersion.parallel import continue_em1d
from scirel.kinetic.dispersion.parallel_continuation import ContinuationFailure

VACUUM = dict(wps2=[0.0], vds=[0.0], vtzs=[1.0], wcs=[0.0], c2=4.0)
VACUUM_GRID = [0.2, 0.21, 0.3, -0.15]

# Three species, drifting, non-unit c2: used for certification and seed propagation only.
STATE = dict(
    wps2=np.array([1.0, 2.0, 0.4]),
    vds=np.array([0.2, -0.1, 0.3]),
    vtzs=np.array([0.7, 1.1, 0.5]),
    wcs=np.array([0.4, -0.7, 0.2]),
    c2=9.0,
    cwp=1.0,
    wcs1=1.0,
)


def test_vacuum_continuation_reproduces_the_closed_form_branch():
    # Anchor 1.  omega^2 = c2 * k^2 with zero scaled residual at every point, both signs of k.  The
    # branch is also pinned: the vacuum root is real, and the accepted run must keep the sign of the
    # caller's seed (0.4) instead of crossing to the mirror root -- an assertion that ``abs(omega)``
    # alone cannot make, since both roots share the same modulus.
    result = continue_em1d(dict(state=VACUUM, k_grid=VACUUM_GRID, initial_guess=0.4 + 0j))
    omega = np.asarray(result["omega"])
    grid = np.asarray(VACUUM_GRID)
    assert np.all(np.abs(omega.imag) == 0.0), omega
    assert np.all(omega.real > 0.0), omega
    np.testing.assert_allclose(np.abs(omega), math.sqrt(VACUUM["c2"]) * np.abs(grid), rtol=1e-15)
    for record, root, k in zip(result["records"], omega, grid):
        assert record["scaled_residual"] == 0.0, (record["k"], record["scaled_residual"])
        assert record["solver_success"] is True
        assert abs(complex(root).real ** 2 - VACUUM["c2"] * float(k) ** 2) <= (
            1e-15 * VACUUM["c2"] * float(k) ** 2
        )


def test_a_solver_success_above_the_residual_bound_is_rejected():
    # Anchor 2, reverse direction, without monkeypatching the solver: this point is accepted at the
    # declared default tolerance and rejected -- while the solver still reports success -- at a tighter
    # one.  Both halves are asserted so the rejection is about the bound, not about an unresolvable point.
    accepted = continue_em1d(dict(state=STATE, k_grid=[0.01]))
    assert len(accepted["records"]) == 1
    record = accepted["records"][0]
    assert record["solver_success"] is True
    assert record["scaled_residual"] <= 1e-10

    for tolerance in (1e-20, 1e-25, 1e-30):
        with pytest.raises(ContinuationFailure) as caught:
            continue_em1d(dict(state=STATE, k_grid=[0.01], residual_tolerance=tolerance))
        failure = caught.value.record
        assert failure["k"] == pytest.approx(0.01)
        assert failure["solver_success"] is True, tolerance
        assert failure["scaled_residual"] > tolerance, (tolerance, failure["scaled_residual"])
        assert failure["accepted_prefix"] == (), tolerance


def test_forward_direction_every_accepted_point_meets_the_bound():
    # Anchor 2, forward direction, on a grid where every point is accepted.
    result = continue_em1d(dict(state=STATE, k_grid=[0.01, 0.02], residual_tolerance=1e-10))
    assert len(result["records"]) == 2
    for record in result["records"]:
        assert record["solver_success"] is True
        assert record["scaled_residual"] <= 1e-10


def test_rejected_second_point_produces_no_successor_row():
    # Anchor 3a.  Point 2 fails naturally (the residual raises inside the solver objective).  The run must
    # stop there: the failure names k=0.5, the accepted prefix is exactly the first point, and the third
    # grid point (0.01) -- shown acceptable by a separate two-point run -- is never reached.
    control = continue_em1d(dict(state=STATE, k_grid=[0.01, 0.01]))
    assert len(control["records"]) == 2

    with pytest.raises(ContinuationFailure) as caught:
        continue_em1d(dict(state=STATE, k_grid=[0.01, 0.5, 0.01]))
    failure = caught.value.record
    assert failure["k"] == pytest.approx(0.5)
    assert len(failure["accepted_prefix"]) == 1, failure["accepted_prefix"]
    assert "evaluation_error" in failure
    # No completed continuation is returned: nothing carries a third row.
    assert getattr(caught.value, "result", None) is None


def test_exhausted_budget_at_the_first_point_propagates_nothing():
    # Anchor 3b.  A solver failure (not an exception) at point 1: the record must carry the solver's own
    # verdict and an empty accepted prefix, so no unaccepted candidate is ever used as a seed.
    with pytest.raises(ContinuationFailure) as caught:
        continue_em1d(dict(state=STATE, k_grid=[0.05, 0.6, 0.05], solver_options={"maxfev": 8}))
    failure = caught.value.record
    assert failure["k"] == pytest.approx(0.05)
    assert failure["solver_success"] is False
    assert failure["accepted_prefix"] == ()
    assert np.isfinite(complex(failure["attempted"]))
