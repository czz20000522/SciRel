"""Independent evidence for the kinetic perpendicular-wavenumber frequency scan.

Why this file exists
--------------------
``scan_kinetic_wavevectors`` is a graph: it derives a frequency ladder and one fixed seed from the
equilibrium controls, then hands both to ``solve_kinetic_wavevector_roots``.  A test that only reads the
scan's own ``roots``/``residuals`` cannot tell "the scan is a faithful driver" from "the scan re-derived
a different ladder, seed or kz and drove the same solver".  The anchors here are chosen so that each one
moves when a different part of that chain is wrong:

1. **Independent ladder recomputation.**  The ladder is rebuilt in this file from exact rational
   arithmetic (``Fraction``) and the seed from ``0.6*kn``, without calling the private
   ``scan_frequencies``/``seed_wavenumber`` helpers, and compared to the returned ``omegas``/
   ``kx_start`` bit for bit.  The scan's own docstring says a one-ulp frequency shift changes which zero
   the solver reaches, so a ulp-level ladder error is not cosmetic here.
2. **Entry identity with the root solver.**  Feed the scan's reported ``omegas``, ``kz``, ``kx_start``
   and derived ``ns0``/``Ts0`` to ``solve_kinetic_wavevector_roots`` and require the whole ladder, not
   just its first point, to reproduce ``roots``/``residuals``/``status`` exactly.  The two entries share
   the mathematics but not the input path, so this catches "the scan computed its endpoint somewhere
   else", which is what an endpoint-only comparison cannot see.
3. **Per-point zero quality through another asset.**  Every converged point's root is re-fed to
   ``scirel.kinetic.dielectric-response``; the recomputed relative determinant must sit at the roundoff
   floor.  A point flagged converged whose root is not a zero fails here.
4. **Jump discipline, both directions.**  Along the ladder the *modulus* of the root is what has to be
   continuous: this model's ``kz=0`` determinant is even in ``kx``, so adjacent points may legitimately
   sit on opposite signs of the same branch.  The discipline is therefore: a converged pair must keep
   the modulus continuous, and any pair that breaks modulus continuity must have at least one endpoint
   flagged nonconverged.  Both halves are counted, so neither can hold vacuously: the measured ladder
   contains converged neighbouring pairs *and* flagged discontinuities.

What this file deliberately does not claim
------------------------------------------
* **The branch topology between ladder points is not claimed.**  Nothing here says the scan follows one
  physical mode, or that a sign flip at adjacent frequencies is physically right; only that a sign flip
  between two converged points leaves the modulus continuous and that a modulus jump is disclosed.
* An adjacent pair may be converged at both ends and still change sign (measured below): that is not a
  nonconvergence, and the contract says so.
* ``scan_kinetic_wavevectors`` can raise ``FloatingPointError`` from the Ronnmark path at some
  frequencies (measured on the ``1.0:0.005:1.2`` ladder); the scan returns no partial result there, so
  that window is out of this file's scope by construction.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np


from scirel.kinetic import (
    evaluate_dielectric_response,
    scan_kinetic_wavevectors,
    solve_kinetic_wavevector_roots,
)

CASE = dict(
    ms=[9.1094e-31],
    qs=[-1.60217662e-19],
    ns_unit=[1.0],
    Ts_unit=[1.0],
    B0=1.0,
    n00=6.075e19,
    T00=1000.0,
    kz=0.0,
)
LADDER = dict(omega_scale=0.66, omega_step=0.005, omega_stop=0.72)
KX_SCALE = 0.6

FLOOR = 1e-12
CONTINUITY = 1e-2


def _scan():
    return scan_kinetic_wavevectors(**CASE, **LADDER)


def _independent_ladder():
    """Rebuild the colon ladder from exact rationals, without the scan's own helpers."""
    start, step, stop = (
        Fraction(LADDER[key]) for key in ("omega_scale", "omega_step", "omega_stop")
    )
    ratio = (stop - start) / step
    count = int(math.floor(ratio + 1e-12 * max(1.0, abs(ratio)))) + 1
    return np.array([float(start + index * step) for index in range(count)], dtype=np.float64)


def _relative_determinant(kx, omega, kz, scales):
    out = evaluate_dielectric_response(
        method="ronnmark",
        B0=CASE["B0"],
        qs=CASE["qs"],
        ms=CASE["ms"],
        ns0=np.asarray(scales["ns0"]),
        Ts0=np.asarray(scales["Ts0"]),
        omega=omega,
        kz=kz,
        kx=kx,
    )
    return abs(out["determinant"]) / float(np.abs(out["K"]).max())


def test_ladder_and_seed_match_an_independent_recomputation():
    # Anchor 1.  Exact rational ladder + seed from the returned kn, compared bit for bit.
    answer = _scan()
    expected = _independent_ladder() * answer["scales"]["wn"]
    assert answer["count"] == expected.size
    np.testing.assert_array_equal(np.asarray(answer["omegas"]), expected)
    assert complex(answer["kx_start"]) == complex(KX_SCALE * answer["scales"]["kn"], 0.0)


def test_scan_reproduces_the_root_solver_over_the_whole_ladder():
    # Anchor 2.  The scan's own derived inputs, replayed through the root solver's entry: every point,
    # not only the endpoint, must come back identical.
    answer = _scan()
    replay = solve_kinetic_wavevector_roots(
        B0=CASE["B0"],
        qs=CASE["qs"],
        ms=CASE["ms"],
        ns0=np.asarray(answer["scales"]["ns0"]),
        Ts0=np.asarray(answer["scales"]["Ts0"]),
        omegas=np.asarray(answer["omegas"]),
        kz=answer["kz"],
        kx_start=complex(answer["kx_start"]),
    )
    np.testing.assert_array_equal(np.asarray(answer["roots"]), np.asarray(replay["roots"]))
    np.testing.assert_array_equal(np.asarray(answer["residuals"]), np.asarray(replay["residuals"]))
    np.testing.assert_array_equal(np.asarray(answer["status"]), np.asarray(replay["status"]))


def test_every_converged_point_is_a_zero_of_the_determinant():
    # Anchor 3.  Converged points are re-checked through the separate dielectric-response asset.
    answer = _scan()
    converged = [index for index, flag in enumerate(np.asarray(answer["status"])) if int(flag) > 0]
    assert len(converged) >= 2, converged
    for index in converged:
        relative = _relative_determinant(
            complex(answer["roots"][index]),
            float(answer["omegas"][index]),
            float(answer["kz"]),
            answer["scales"],
        )
        assert relative <= FLOOR, (index, relative)


def test_modulus_is_continuous_across_converged_pairs_and_jumps_are_flagged():
    # Anchor 4.  Both halves are counted so neither can be vacuous.
    answer = _scan()
    roots = np.asarray(answer["roots"])
    status = np.asarray(answer["status"])

    continuous_converged = 0
    discontinuities = 0
    for index in range(1, roots.size):
        previous, current = roots[index - 1], roots[index]
        scale = max(abs(previous), abs(current))
        assert scale > 0.0
        change = abs(abs(current) - abs(previous)) / scale
        flagged = int(status[index - 1]) <= 0 or int(status[index]) <= 0
        if change <= CONTINUITY:
            if int(status[index - 1]) > 0 and int(status[index]) > 0:
                continuous_converged += 1
        else:
            discontinuities += 1
            # A modulus jump between ladder points must be disclosed by the exit flags.
            assert flagged, (index, change, int(status[index - 1]), int(status[index]))

    # Non-vacuity: the ladder actually contains both shapes this test is about.
    assert continuous_converged >= 2, continuous_converged
    assert discontinuities >= 2, discontinuities
