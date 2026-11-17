"""Independent evidence for the complex kinetic perpendicular-wavenumber roots.

Why this file exists
--------------------
``solve_kinetic_wavevector_roots`` returns ``roots`` next to ``residuals`` and
``determinant_scale``, and all three come out of the same ``_reference_fsolve`` call: the residual is
the solver's own final ``fval`` at the root it returned.  A root that is not a zero of the shipped
determinant, and a residual that agrees with it, are the same failure seen twice.  So none of the three
anchors below reads ``residuals`` as the source of truth:

1. **Cross-asset recomputation.**  The returned root is handed to
   ``scirel.kinetic.dielectric-response`` -- a separate delivered asset whose printed entry is
   ``evaluate_dielectric_response`` -- and the recomputed determinant there must be at the roundoff
   floor relative to that tensor's own element scale.  This passes through another asset's public
   port, not through the root finder's bookkeeping.
2. **Displacement separation.**  The same call at ``root*(1 +- 1e-3)`` must raise the relative
   determinant by a factor of at least ``1e3``.  This is the only anchor that says the reported number
   is a *zero of the function* rather than a plateau, a seed, or a mis-scaled candidate: no
   self-report can satisfy it, because it changes the returned value and observes the function.
3. **Conjugate branch.**  Two seeds on the same case reach roots that sum to zero at roundoff.  The
   determinant of this model is even in ``kx`` for ``kz=0``, so both signs are zeros; a sign or
   conjugation error in the returned value breaks the pair identity while leaving ``|root|`` intact.

What this file deliberately does not claim
------------------------------------------
* ``Re(kx)`` **has no asserted analytic value.**  It measures about ``6e-13`` on the example, i.e. it
  is numerically zero; the assertions below never compare it to a formula, only the pair sum to zero.
* **No mode identity is claimed.**  "Branch i is the lower-hybrid / Bernstein / ... mode" is not
  observable from these numbers and is not asserted.
* ``evaluate_kinetic_dispersion_relation`` is **not** used as the cross-asset oracle even though it is
  the natural sibling: its perpendicular port is a *real* ratio (``kx_frac``), so it cannot represent a
  root whose real part is ``~1e-13`` and whose imaginary part is ``~1315``.  Feeding only ``Re(root)``
  there leaves ``abs(det)/max|K|`` at about ``1.6e2`` (measured), i.e. the substitution would be a
  false anchor rather than a weak one.
"""

from __future__ import annotations

import numpy as np


from scirel.kinetic import evaluate_dielectric_response, solve_kinetic_wavevector_roots

# The reviewed example case: one electron species, omega = 1e11 rad/s, kz = 0.
CASE = dict(
    B0=1.0,
    qs=[-1.60217662e-19],
    ms=[9.1094e-31],
    ns0=[6.075e19],
    Ts0=[11604941.036704937],
    omegas=[1e11],
    kz=0.0,
)

# The example's own seed.  0.5*kn (the previous batch's choice) does not converge on this case; the
# seed is a modelling input, not a tuning knob, so the case is pinned where the reference example puts it.
SEED = 8000.0
MIRROR_SEED = 16000.0

FLOOR = 1e-12  # roundoff floor for a recomputed relative determinant
SEPARATION_FLOOR = 1e3  # smallest factor that can be called "not a plateau"
PAIR_TOL = 1e-12  # relative tolerance on the conjugate pair sum


def _relative_determinant(kx):
    """Recompute ``abs(det)/max|K|`` through the dielectric-response asset at one complex ``kx``."""
    out = evaluate_dielectric_response(
        method="ronnmark",
        B0=CASE["B0"],
        qs=CASE["qs"],
        ms=CASE["ms"],
        ns0=CASE["ns0"],
        Ts0=CASE["Ts0"],
        omega=CASE["omegas"][0],
        kz=CASE["kz"],
        kx=kx,
    )
    return abs(out["determinant"]) / float(np.abs(out["K"]).max())


def _solve(seed):
    return solve_kinetic_wavevector_roots(**CASE, kx_start=seed)


def test_root_is_a_zero_of_the_determinant_recomputed_through_another_asset():
    # Anchor 1.  The root finder's own ``residuals`` is not consulted: the determinant is rebuilt here
    # from the contract's declared inputs at the returned root, through the separate dielectric-response
    # asset, so a root that only zeroes the solver's cached ``fval`` cannot pass.
    answer = _solve(SEED)
    assert answer["success"].tolist() == [True]
    root = complex(answer["roots"][0])
    relative = _relative_determinant(root)
    assert relative <= FLOOR, relative


def test_displaced_root_raises_the_determinant_by_at_least_three_orders():
    # Anchor 2.  A relative displacement of 1e-3 in the *returned number* must move the recomputed
    # determinant up by >= 1e3.  A plateau, an unmodified seed, or a root reported for the wrong
    # frequency all keep the determinant flat and fail here; the assertion is a lower bound on the
    # separation factor, not a pinned multiplier.
    answer = _solve(SEED)
    root = complex(answer["roots"][0])
    baseline = _relative_determinant(root)
    for offset in (1e-3, -1e-3):
        displaced = _relative_determinant(root * (1.0 + offset))
        ratio = displaced / baseline
        assert ratio >= SEPARATION_FLOOR, (offset, ratio)


def test_two_seeds_reach_the_conjugate_branch():
    # Anchor 3.  ``det`` is even in ``kx`` at ``kz=0``, so +root and -root are both zeros of the same
    # function.  Two seeds that reach opposite signs must therefore sum to zero at roundoff.  This is a
    # statement about the *pair*: it constrains the sign/conjugation of what is returned without
    # claiming an analytic value for the (numerically zero) real part.
    lower = _solve(SEED)
    upper = _solve(MIRROR_SEED)
    assert lower["success"].tolist() == [True]
    assert upper["success"].tolist() == [True]
    first = complex(lower["roots"][0])
    second = complex(upper["roots"][0])
    scale = max(abs(first), abs(second))
    assert scale > 0.0
    assert abs(first + second) / scale <= PAIR_TOL, (first, second)
    # The pair identity is only meaningful if the two roots actually differ in sign.
    assert np.sign(first.imag) == -np.sign(second.imag), (first.imag, second.imag)


def test_nonconverged_seeds_are_disclosed_and_reported_residuals_are_honest():
    # The seed is a modelling input and the contract says which seeds converge on this case.  Three
    # properties are asserted together, which is what makes the disclosure load-bearing:
    #   * a nonconverged seed reports ``status <= 0`` and ``success is False`` and a message that says
    #     so, i.e. no exit flag is promoted to success;
    #   * the reported ``residuals``/``determinant_scale`` agree with a fresh recomputation at the
    #     returned candidate, so the numbers next to a failure are not decorative;
    #   * a status-0 candidate is not a zero, while a status=-3 candidate *can* be one.  The second
    #     half is measured, not assumed: seed 4000 exits -3 and its candidate sits at the roundoff
    #     floor, so "nonconverged" must not be read as "not a root" in either direction.
    seeds = (8000.0, 16000.0, 4000.0, 1e5, 1e6, 1e7, 1.25e11)
    observed = {}
    for seed in seeds:
        answer = _solve(seed)
        candidate = complex(answer["roots"][0])
        recomputed = _relative_determinant(candidate)
        reported = abs(complex(answer["residuals"][0])) / float(answer["determinant_scale"][0])
        assert abs(reported - recomputed) <= 1e-12 * max(1.0, recomputed), (
            seed,
            reported,
            recomputed,
        )
        status = int(answer["status"][0])
        assert bool(answer["success"][0]) is (status > 0), (seed, status)
        if status > 0:
            assert recomputed <= FLOOR, (seed, recomputed)
        else:
            assert "not converged" in answer["message"][0], (seed, answer["message"][0])
        observed[seed] = (status, recomputed)

    assert observed[8000.0][0] > 0 and observed[16000.0][0] > 0
    for seed in (1e5, 1e6, 1e7, 1.25e11):
        status, recomputed = observed[seed]
        assert status == 0, (seed, status)
        assert recomputed > 1e-6, (seed, recomputed)
    # Measured asymmetry: the collapsed-trust-region exit carries a genuine zero here.
    status, recomputed = observed[4000.0]
    assert status == -3, status
    assert recomputed <= FLOOR, recomputed
