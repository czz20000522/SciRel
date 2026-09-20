"""SciRel-owned DD neutron lab energy -- non-relativistic two-body kinematics.

Two deuteron velocity vectors and a detector line-of-sight unit vector map to the
laboratory-frame neutron kinetic energy of D(d,n)3He, in keV:

    v_cm    = (v1 + v2) / 2
    v_rel   = v1 - v2
    E_avail = 0.5 * (m_D / 2) * m_u * |v_rel|^2 * 1e-4 / q_MeV + Q_DD
    E_cm    = m_He3 / (m_n + m_He3) * E_avail
    E_boost = 0.5 * m_n * m_u * |v_cm|^2 * 1e-4 / q_MeV
    c       = v_cm_hat . d_hat
    E_lab   = (sqrt(E_cm) - sqrt(E_boost))^2 + 2 * sqrt(E_cm * E_boost) * (1 + c)

The return value is the energy and nothing else.  The three intermediate
quantities above, the direction cosine, and the mass constants are all
recoverable from this formula and are checked in the tests rather than returned.

**The source's non-positive fallback is removed, and this is a correction.**

The retained source route and the V2 predecessor both guard the result with
``lab_mev if lab_mev > 0.0 else E_cm``, substituting the centre-of-mass energy
whenever the computed lab energy is not strictly positive.  The V2 review
searched for an input reaching that branch, did not find one, and recorded the
branch as algebraically unreachable except at exact equality of ``E_cm`` and
``E_boost``.  That is not correct.  Because the guard is ``not lab_mev > 0.0``,
it fires on *every* non-positive value, including the small negative values that
floating-point rounding produces near exact cancellation of the two-body square
root.  Measured over the 8001 doubles within +-4000 ulp of the speed that makes
``E_boost`` closest to ``E_cm``, the guard fires 6983 times: 5986 where the
computed value is exactly zero and 997 where it is strictly negative, that is,
where the value is a pure rounding artifact.  That census was measured by the
frozen review against the external route; the maintained tests cannot reach it and
do not replay it, and record the finding here as the reason for the removal.  Two
witnesses are pinned in the tests:

===========  ===========================  ====================
speed (cm/s) this asset's ``E_lab`` (keV)  guarded result (keV)
===========  ===========================  ====================
2165199149.095274    ``2.9996e-25``       2450.47589941598
2165199149.0952773   ``2.2132e-25``       2450.47589941598
===========  ===========================  ====================

At both speeds the neutron is emitted backwards at essentially the speed that
brings it to rest in the laboratory, so the lab energy is zero to well below any
physical significance; the guard replaces it with 2450 keV.  The second witness
is not an exact equality: it is one of the 997 ordinary neighbouring doubles
whose computed value rounds to a negative, and the substitution is a 100%
relative error on a quantity whose true value is about ``2e-25`` keV.  A guard
that converts a rounding artifact into a 2.45 MeV value is not protecting the
caller from a non-physical number; it is producing one.

**The evaluated form is non-negative by construction, so no clamp is applied.**

``E_lab`` is algebraically equal to the retained route's
``E_cm + E_boost + 2 * sqrt(E_cm * E_boost) * c``, but it is evaluated in a form
whose two terms are each individually non-negative for every physical input:

* ``(sqrt(E_cm) - sqrt(E_boost))^2`` is a square, so it is never negative;
* ``2 * sqrt(E_cm * E_boost) * (1 + c)`` is a product of non-negative factors,
  because ``E_cm`` and ``E_boost`` are non-negative by construction and the
  direction cosine ``c`` is bounded to ``[-1, 1]``, so ``1 + c >= 0``.

The retained route's ordering adds a large negative term to a large positive one
near backward emission, which is what produced the ``-8.881784197001252e-13`` keV
that the V3 candidate disclosed and what the V4 candidate answered with an
empirical ``max(0.0, value)`` clamp.  This formulation does not need that clamp:
the sum of two non-negative terms cannot round below zero, and the negative
returned by the retained ordering does not arise.  The bound is structural
rather than measured, so no value is ever replaced by zero.

The reformulation is a change of evaluation order and not a change of relation,
so the returned energy is no longer bit-identical to the retained route.  It
agrees with it to the accuracy the relation itself carries: the two forms differ
only in where the roundings fall, so the difference is bounded by a few units in
the last place of ``E_cm + E_boost``.  The tests assert that bound rather than
bit-identity, and they assert that the *result* is non-negative exactly rather
than within a tolerance.  The ordering they compare against is re-derived from the
constants this module publishes, not read from the retained route, which the
maintained tests cannot reach; the frozen review's measurement against that route
is recorded above as a non-contract observation.

**The exact-cancellation configuration returns exactly zero.**

The neutron is at rest in the laboratory when ``E_cm`` and ``E_boost`` are the
same double and the detector is exactly backward.  At that input both terms
above are exactly ``0.0`` -- the first because the two square roots are the same
double, the second because ``c`` is exactly ``-1`` -- so the returned energy is
exactly ``0.0``, not a small positive residue and not a rounding negative.  This
is the one double within +-4000 ulp of the cancellation speed at which
``E_boost`` equals ``E_cm`` exactly; the two V4-pinned speeds are one and three
units in the last place away from it, which is why they return ``2.9996e-25``
and ``2.2132e-25`` keV rather than exactly zero.  Both configurations are pinned
in the tests.  The behaviour of the *removed* guard at those inputs -- the
substitution of the centre-of-mass energy -- was established by the frozen review
against the external route and is not replayed here.

**Arithmetic that is not representable fails closed.**

The input contract accepts any finite velocity, including values for which the
non-relativistic relation cannot be evaluated in double precision.  Two
signatures were measured on the V4 candidate, both with finite inputs:

* two ``1.0e308`` cm/s velocities overflow ``v1 + v2`` and then the
  ``inf / inf`` in the direction cosine, so the sum is ``NaN`` and the empirical
  clamp returned ``0.0`` -- a silent zero for an input whose energy is not zero;
* one ``1.0e150`` cm/s velocity overflows ``|v_cm|^2`` to ``inf`` while
  ``E_cm`` stays finite, so the sum is ``inf`` and the clamp passed the infinity
  through.

Neither is a scientific result.  Every intermediate and the returned value are
therefore checked for finiteness, and a non-finite value raises ``ValueError``
rather than being returned or clamped.  This is a representability check on
finite inputs and not a speed cutoff: no magnitude threshold is introduced, and
a velocity that is large but still evaluable is accepted and answered.  The
non-relativistic applicability precondition remains a scientific statement about
the relation rather than a hard-coded bound on the input.

**No angular weighting is applied.** The source route returned a fixed
``angular_weight`` of 1.0 alongside the energy; that port is dropped here, not
because anisotropy is absent but because a constant 1.0 is not a scientific
output.  Angular weighting is a separate capability that this leaf does not
provide, does not import and does not compose: a caller that needs the
Brown--Jarmie angular distribution must apply it outside this asset, and no
public SciRel callable for it exists at this development baseline.

**The detector vector must be a unit vector.** The precondition is the retained
route's, not one introduced here: the vector is used directly as a direction, so
a non-unit vector scales the direction cosine.  It is rejected with an absolute
tolerance of 1e-12 rather than normalised, because normalising would hide a
caller error.  The tolerance is what makes the cosine bound necessary rather
than redundant.

Evidence ceiling: this module establishes the two-body lab-energy relation, its
input contract, the behaviour of the removed guard at two pinned witnesses, the
non-negativity of the returned value, the exactness of the zero at the
cancellation configuration, and the failure of non-representable arithmetic.
It does **not** establish the accuracy of the non-relativistic approximation at
any energy, and it does **not** establish the mass constants against any
independent measurement; the retained route cites no reference and states no
licence for them.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "ATOMIC_MASS_KG",
    "DD_Q_VALUE_MEV",
    "DEUTERON_MASS_AMU",
    "DETECTOR_NORM_ATOL",
    "HELIUM3_MASS_AMU",
    "NEUTRON_MASS_AMU",
    "calculate_dd_neutron_lab_energy_kev",
]

# Masses and the Q value as the retained route states them.  Unverified against
# any independent measurement; see the evidence ceiling above.
DEUTERON_MASS_AMU = 2.013553212745
NEUTRON_MASS_AMU = 1.008665
HELIUM3_MASS_AMU = 3.01603
ATOMIC_MASS_KG = 1.660539040e-27
MEV_J = 1.60218e-13
DD_Q_VALUE_MEV = 3.27

# Absolute tolerance on the detector vector's Euclidean norm.  Because it is a
# tolerance and not an exact test, an accepted detector can have a norm on either
# side of one, which is why the direction cosine is bounded below.
DETECTOR_NORM_ATOL = 1e-12

# Raised when a finite input produces arithmetic that double precision cannot
# represent.  Distinct from the input-contract ValueError by message, and not by
# a magnitude threshold: see the module docstring.
NON_REPRESENTABLE_MESSAGE = (
    "the DD neutron lab energy is not representable for these finite inputs"
)


def _require_representable(value, quantity):
    """Fail closed when a finite input has produced a non-finite value."""
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{NON_REPRESENTABLE_MESSAGE}: {quantity} is not finite")


def calculate_dd_neutron_lab_energy_kev(
    *,
    reactant1_velocity_cm_s,
    reactant2_velocity_cm_s,
    detector_unit_vector,
):
    """Return the laboratory-frame DD neutron energy, in keV.

    Parameters
    ----------
    reactant1_velocity_cm_s, reactant2_velocity_cm_s
        Finite shape-``(3,)`` deuteron velocity vectors in cm/s.
    detector_unit_vector
        Finite shape-``(3,)`` line-of-sight vector from the reaction point to the
        detector, of unit Euclidean norm within an absolute tolerance of
        ``DETECTOR_NORM_ATOL``.

    Returns
    -------
    float
        ``E_lab`` in keV, always finite and always non-negative.  ``E_lab`` is
        evaluated as the sum of the two non-negative terms
        ``(sqrt(E_cm) - sqrt(E_boost))^2`` and
        ``2 * sqrt(E_cm * E_boost) * (1 + c)``, which is algebraically the same
        relation the retained route evaluates as
        ``E_cm + E_boost + 2 * sqrt(E_cm * E_boost) * c`` but cannot round below
        zero.  The direction cosine is bounded to ``[-1, 1]`` before use, because
        the detector norm is accepted within a tolerance and can therefore exceed
        one.  At the exact-cancellation configuration, where ``E_cm`` and
        ``E_boost`` are the same double and the detector is exactly backward,
        both terms are exactly zero and the result is exactly ``0.0``.

    Raises
    ------
    ValueError
        If a vector is not a finite shape-``(3,)`` vector, if the detector vector
        is not a unit vector, or if the relation's arithmetic is not representable
        for the supplied finite velocities.

    Notes
    -----
    The relation is the retained route's, with its non-positive fallback removed
    and its evaluation order reformulated so that the result cannot round
    negative.  See the module docstring for the two witnesses that justify the
    removal, for the exact-cancellation configuration, and for the measured
    non-representable inputs.
    """
    v1 = np.asarray(reactant1_velocity_cm_s, dtype=float)
    v2 = np.asarray(reactant2_velocity_cm_s, dtype=float)
    detector = np.asarray(detector_unit_vector, dtype=float)
    if (
        v1.shape != (3,)
        or v2.shape != (3,)
        or detector.shape != (3,)
        or not all(np.all(np.isfinite(v)) for v in (v1, v2, detector))
    ):
        raise ValueError(
            "velocity vectors and detector_unit_vector must be finite shape-(3,) vectors"
        )
    if not np.isclose(
        np.linalg.norm(detector), 1.0, rtol=0.0, atol=DETECTOR_NORM_ATOL
    ):
        raise ValueError("detector_unit_vector must have unit norm")

    # The overflow and invalid-operation warnings NumPy would raise below are the
    # conditions `_require_representable` detects explicitly and reports as a
    # ValueError, so they are suppressed here rather than reported twice.
    with np.errstate(over="ignore", invalid="ignore"):
        v_centre_of_mass = 0.5 * (v1 + v2)
        v_relative = v1 - v2
        _require_representable(v_centre_of_mass, "the centre-of-mass velocity")
        _require_representable(v_relative, "the relative velocity")
        available_mev = (
            0.5 * (DEUTERON_MASS_AMU / 2.0) * ATOMIC_MASS_KG
            * float(np.dot(v_relative, v_relative)) * 1.0e-4 / MEV_J
            + DD_Q_VALUE_MEV
        )
        centre_of_mass_mev = (
            HELIUM3_MASS_AMU / (NEUTRON_MASS_AMU + HELIUM3_MASS_AMU) * available_mev
        )
        boost_mev = (
            0.5 * NEUTRON_MASS_AMU * ATOMIC_MASS_KG
            * float(np.dot(v_centre_of_mass, v_centre_of_mass)) * 1.0e-4 / MEV_J
        )
        _require_representable(available_mev, "the available energy")
        _require_representable(centre_of_mass_mev, "the centre-of-mass energy")
        _require_representable(boost_mev, "the boost energy")
        centre_of_mass_norm = float(np.linalg.norm(v_centre_of_mass))
        if centre_of_mass_norm > 0.0:
            cos_theta_lab = float(
                np.dot(v_centre_of_mass / centre_of_mass_norm, detector)
            )
        else:
            cos_theta_lab = 0.0
        # The detector is accepted within a norm tolerance, so an accepted caller
        # can hand in a vector whose dot product with a unit v_cm_hat leaves
        # [-1, 1].  A direction cosine cannot, so bound it rather than let it
        # inflate the energy.
        cos_theta_lab = min(1.0, max(-1.0, cos_theta_lab))
        _require_representable(cos_theta_lab, "the direction cosine")
        # Algebraically E_cm + E_boost + 2*sqrt(E_cm*E_boost)*c, regrouped so
        # that both terms are individually non-negative: a square, and a product
        # of non-negative factors because c is bounded to [-1, 1].  No clamp is
        # needed and none is applied; see the module docstring.
        lab_mev = (
            (math.sqrt(centre_of_mass_mev) - math.sqrt(boost_mev)) ** 2
            + 2.0 * math.sqrt(centre_of_mass_mev * boost_mev) * (1.0 + cos_theta_lab)
        )
        _require_representable(lab_mev, "the laboratory-frame energy")
        lab_kev = float(lab_mev * 1000.0)
        _require_representable(lab_kev, "the laboratory-frame energy in keV")
    return lab_kev
