"""Independent evidence for the invariant bi-Maxwellian distribution.

Asset: ``scirel.mirror.mirror-invariant-distribution``.

The maintained tests in ``test_mirror_invariant_distribution.py`` check
invariance between two states that were themselves built by inverting the
implementation's own energy/magnetic-moment expressions, plus the loss-cone
occupation branches.  Invariance under a self-consistent pair cannot distinguish
a correct invariant from a consistently wrong one: ``E`` and ``mu`` with the
same wrong factor on both sides still agree.

The evidence here is the closed-form distribution written from the physics
rather than from the implementation's algebra.  For a bi-Maxwellian specified by
parallel thermal energy ``T_parallel`` and reference perpendicular thermal energy
``T_perp,ref`` at reference field ``B_ref``, the invariants are

``mu = m v_perp^2 / (2 B)``,  ``E = m v_parallel^2 / 2 + mu B + q phi``,

and the phase-space density is

``f0 = n_ref (m/(2 pi))^(3/2) / (T_perp,ref sqrt(T_parallel))
        exp[-(E - q phi_ref)/T_parallel - mu B_ref (1/T_perp,ref - 1/T_parallel)]``

multiplied by the loss-cone occupation.  This form uses absolute ``E`` and
``mu``; the implementation evaluates the same function through the coefficient
``C = (B - B_ref)/T_parallel + B_ref/T_perp,ref``.  The two are algebraically
equal but numerically distinct, and the algebra above is expanded independently
of :func:`evaluate_mirror_invariant_distribution`.

Six statements, each of which a wrong implementation cannot pass:

1. **Closed-form density at 50 digits.**  On both an O(1) fixture and the
   hydrogen fixture from the contract example, ``f0`` matches the mpmath
   evaluation of the formula above.  This rejects a dropped ``(m/2pi)^(3/2)``,
   a ``T_perp T_parallel`` instead of ``T_perp sqrt(T_parallel)`` normalisation,
   a sign flip in either exponent term and any additive constant.
2. **Exact invariants.**  On dyadic inputs ``mu`` and ``E`` equal the
   ``Fraction``-exact values bit for bit.  The factor two in ``mu``, the
   ``mu*B`` term in ``E`` and the ``q phi`` charge term are each decided
   exactly, not within a tolerance.
3. **Velocity-sign symmetry.**  ``f0`` is exactly invariant under
   ``v_parallel -> -v_parallel`` and under ``v_perp -> -v_perp``, because both
   enter through squares.  An implementation with a linear velocity factor, or
   one that mixed up the two velocities, changes value here.
4. **Charge-potential antisymmetry.**  With ``phi_ref = 0``,
   ``f0(q, phi) == f0(-q, -phi)``: only the product ``q phi`` enters.  This
   pins the gauge structure and rejects a ``|q|`` or a dropped charge sign.
5. **The loss-cone occupation convention.**  With no plugs the occupation is the
   scalar ``1.0`` and the density is the untruncated one; with plugs a particle
   whose parallel kinetic balance equals the lower barrier exactly receives the
   refill value, because the trapped comparison is declared strict.
6. **Permitted underflow.**  A deeply negative exponent returns ``0.0`` rather
   than raising, which is the declared behaviour and the reason the exponent is
   never clipped.

Budgets, fixed before the comparison was run:

* statements 2, 3, 5 and 6 are exact equalities or exact zeros and carry no
  budget;
* statement 1 uses ``_RELATIVE_BUDGET = 256 eps = 5.68e-14``.  It comes from the
  operation count of the log-space evaluation: at most nine logarithms with
  ``|log| <= 100`` (the hydrogen fixture gives ``log(m/(2 pi)) ~ -62`` and
  ``log(T) ~ -36``), each contributing at most one ulp of its own magnitude, plus
  five additions of terms of magnitude at most 100.  That is
  ``(9 + 5) * 100 * eps ~ 1.6e-13`` before the generous factor is applied to the
  far smaller O(1) fixture; 256 eps is the smaller of the two derived figures and
  was not adjusted after any measurement.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- bool/nonfinite/zero mass and charge, refill outside
  ``[0, 1]``, a one-sided plug pair, nonfinite local arrays, nonpositive
  ``B``/``B_ref``/temperatures, a negative reference density and an
  unmatchable profile all raise ``ValueError``.
* ``runtime_failure`` -- a nonpositive integrability coefficient ``C`` raises
  ``FloatingPointError``, and an f0 that leaves the finite range raises
  ``FloatingPointError`` instead of returning ``inf``.
* ``nonconvergence`` -- declared not applicable; the assertion is that the
  returned mapping has exactly the four declared keys and no status field.
* ``partial_results`` -- every raise above happens before the mapping exists, so
  the ``pytest.raises`` block is the assertion that nothing is returned.
"""

from __future__ import annotations

import math
from fractions import Fraction

import mpmath
import numpy as np
import pytest

from scirel.mirror import evaluate_mirror_invariant_distribution

mpmath.mp.dps = 50

# One binary64 rounding is at most half an ulp; the log-space evaluation uses
# several, so the budget is stated as a multiple of eps with its derivation in
# the module docstring.
_EPS = math.ulp(1.0)
_RELATIVE_BUDGET = 256 * _EPS

E_CHARGE = 1.602176634e-19
M_PROTON = 1.67262192595e-27


def _reference_f0(
    *,
    v_parallel,
    v_perpendicular,
    b_t,
    potential,
    mass,
    charge,
    density_ref,
    temperature_parallel,
    temperature_perpendicular_ref,
    b_ref,
    phi_ref,
    occupation=1.0,
):
    """Evaluate the closed-form bi-Maxwellian in 50-digit arithmetic.

    Written from the physics: absolute energy and magnetic moment enter the
    exponent directly, with no intermediate coefficient and no frexp scaling.
    """
    mp = mpmath
    v_parallel = mp.mpf(v_parallel)
    v_perpendicular = mp.mpf(v_perpendicular)
    b_t = mp.mpf(b_t)
    mass = mp.mpf(mass)
    charge = mp.mpf(charge)
    density_ref = mp.mpf(density_ref)
    temperature_parallel = mp.mpf(temperature_parallel)
    temperature_perpendicular_ref = mp.mpf(temperature_perpendicular_ref)
    b_ref = mp.mpf(b_ref)
    mu = mass * v_perpendicular**2 / (2 * b_t)
    energy = mass * v_parallel**2 / 2 + mu * b_t + charge * mp.mpf(potential)
    log_normalisation = (
        mp.log(density_ref)
        + mp.mpf(1.5) * (mp.log(mass) - mp.log(2 * mp.pi))
        - mp.log(temperature_perpendicular_ref)
        - mp.mpf(0.5) * mp.log(temperature_parallel)
    )
    exponent = -(energy - charge * mp.mpf(phi_ref)) / temperature_parallel - mu * b_ref * (
        1 / temperature_perpendicular_ref - 1 / temperature_parallel
    )
    return mp.e ** (log_normalisation + exponent) * mp.mpf(occupation)


def test_closed_form_density_matches_50_digit_evaluation():
    # O(1) fixture: every log term is small, so the budget is dominated by the
    # hydrogen case below rather than by this one.
    cases = [
        dict(v_parallel=0.3, v_perpendicular=0.4, b_t=1.0, potential=0.05),
        dict(v_parallel=-0.7, v_perpendicular=0.25, b_t=1.4, potential=-0.02),
        dict(v_parallel=0.0, v_perpendicular=0.0, b_t=2.0, potential=0.0),
        dict(v_parallel=1.25, v_perpendicular=0.9, b_t=0.6, potential=0.4),
    ]
    common = dict(
        mass=2.0,
        charge=1.0,
        density_ref=3.0,
        temperature_parallel=0.5,
        temperature_perpendicular_ref=0.25,
        b_ref=0.8,
        phi_ref=0.02,
    )
    for case in cases:
        returned = evaluate_mirror_invariant_distribution(
            case["v_parallel"],
            case["v_perpendicular"],
            case["b_t"],
            0.0,
            case["potential"],
            common["mass"],
            common["charge"],
            common["density_ref"],
            common["temperature_parallel"],
            common["temperature_perpendicular_ref"],
            common["b_ref"],
            common["phi_ref"],
        )["f0_s3_m6"]
        exact = _reference_f0(**case, **common)
        assert float(exact) > 0.0
        assert abs(mpmath.mpf(float(returned)) - exact) <= _RELATIVE_BUDGET * abs(exact), (
            case,
            float(returned),
            float(exact),
        )


def test_hydrogen_fixture_matches_50_digit_evaluation():
    cases = [
        (0.0, 0.0, 1.0, 0.0),
        (2.0e5, 1.0e5, 1.0, 0.0),
        (5.0e5, 3.0e5, 2.5, 250.0),
        (-5.0e5, 3.0e5, 1.6, -250.0),
    ]
    for v_parallel, v_perpendicular, b_t, potential in cases:
        returned = evaluate_mirror_invariant_distribution(
            v_parallel,
            v_perpendicular,
            b_t,
            0.0,
            potential,
            M_PROTON,
            E_CHARGE,
            2.0e18,
            1200.0 * E_CHARGE,
            2400.0 * E_CHARGE,
            1.0,
        )["f0_s3_m6"]
        exact = _reference_f0(
            v_parallel=v_parallel,
            v_perpendicular=v_perpendicular,
            b_t=b_t,
            potential=potential,
            mass=M_PROTON,
            charge=E_CHARGE,
            density_ref=2.0e18,
            temperature_parallel=1200.0 * E_CHARGE,
            temperature_perpendicular_ref=2400.0 * E_CHARGE,
            b_ref=1.0,
            phi_ref=0.0,
        )
        assert abs(mpmath.mpf(float(returned)) - exact) <= _RELATIVE_BUDGET * abs(exact)


def test_magnetic_moment_and_energy_are_exact_rational_identities():
    # Dyadic inputs: mu = m vperp^2/(2B) and E = m vpar^2/2 + mu B + q phi are
    # exactly representable, so the comparison is bitwise.
    mass, charge = 2.0, 0.5
    for v_parallel, v_perpendicular, b_t, potential in (
        (0.5, 0.25, 2.0, 0.125),
        (-1.5, 0.75, 0.5, -0.25),
        (0.0, 1.0, 1.0, 0.5),
    ):
        returned = evaluate_mirror_invariant_distribution(
            v_parallel,
            v_perpendicular,
            b_t,
            0.0,
            potential,
            mass,
            charge,
            1.0,
            1.0,
            0.5,
            1.0,
        )
        mu_exact = Fraction(mass) * Fraction(v_perpendicular) ** 2 / (2 * Fraction(b_t))
        energy_exact = (
            Fraction(mass) * Fraction(v_parallel) ** 2 / 2
            + mu_exact * Fraction(b_t)
            + Fraction(charge) * Fraction(potential)
        )
        assert float(returned["magnetic_moment_j_t"]) == float(mu_exact)
        assert float(returned["energy_j"]) == float(energy_exact)


def test_velocity_sign_reflection_leaves_the_density_unchanged():
    base = (3.0e5, 2.0e5, 1.7, 0.0, 140.0)
    reference = evaluate_mirror_invariant_distribution(
        base[0], base[1], base[2], 0.0, base[4], M_PROTON, E_CHARGE, 1.0e18, 900.0, 1500.0, 1.0
    )
    flipped_parallel = evaluate_mirror_invariant_distribution(
        -base[0], base[1], base[2], 0.0, base[4], M_PROTON, E_CHARGE, 1.0e18, 900.0, 1500.0, 1.0
    )
    flipped_perpendicular = evaluate_mirror_invariant_distribution(
        base[0], -base[1], base[2], 0.0, base[4], M_PROTON, E_CHARGE, 1.0e18, 900.0, 1500.0, 1.0
    )
    # v^2 removes the sign exactly, and the energy expression is the only place
    # the velocity enters, so these are equalities rather than tolerances.
    assert float(flipped_parallel["f0_s3_m6"]) == float(reference["f0_s3_m6"])
    assert float(flipped_parallel["energy_j"]) == float(reference["energy_j"])
    assert float(flipped_perpendicular["f0_s3_m6"]) == float(reference["f0_s3_m6"])
    assert float(flipped_perpendicular["magnetic_moment_j_t"]) == float(
        reference["magnetic_moment_j_t"]
    )


def test_only_the_charge_potential_product_enters_the_density():
    arguments = dict(
        v_parallel_m_s=2.5e5,
        v_perpendicular_m_s=1.5e5,
        b_t=1.3,
        psi=0.0,
        mass_kg=M_PROTON,
        density_ref_m3=1.0e18,
        # Energy units on the eV scale: 120 V against 1200 eV is a 0.1 exponent
        # shift, which binary64 resolves, unlike 120 V against 900 J.
        temperature_parallel_j=1200.0 * E_CHARGE,
        temperature_perpendicular_ref_j=2400.0 * E_CHARGE,
        b_ref_t=1.0,
        phi_ref_v=0.0,
    )
    positive = evaluate_mirror_invariant_distribution(
        potential_v=120.0, charge_c=E_CHARGE, **arguments
    )
    negative = evaluate_mirror_invariant_distribution(
        potential_v=-120.0, charge_c=-E_CHARGE, **arguments
    )
    ratio = float(positive["f0_s3_m6"]) / float(negative["f0_s3_m6"])
    assert abs(ratio - 1.0) <= _RELATIVE_BUDGET
    # The same product q*phi also fixes the absolute energy, so that output is
    # equal as well; this separates "only the product enters" from "the charge
    # sign is ignored".
    assert float(positive["energy_j"]) == float(negative["energy_j"])

    # Reversing the charge alone must change the density: the sign is not
    # dropped by taking an absolute value.
    reversed_charge = evaluate_mirror_invariant_distribution(
        potential_v=120.0, charge_c=-E_CHARGE, **arguments
    )
    assert float(reversed_charge["f0_s3_m6"]) != float(positive["f0_s3_m6"])


def test_occupation_is_scalar_one_without_plugs_and_strict_with_plugs():
    without = evaluate_mirror_invariant_distribution(
        1.0e5, 1.0e5, 1.0, 0.0, 0.0, M_PROTON, E_CHARGE, 1.0e18, 900.0, 1500.0, 1.0
    )
    assert without["occupation"] == 1.0
    assert isinstance(without["occupation"], float)

    # With plugs supplied, an identical plug field at the local point makes both
    # barriers zero; the strict comparison then puts the particle in the
    # depleted branch and the occupation is exactly the refill fraction.
    for refill in (0.0, 0.25, 1.0):
        plugged = evaluate_mirror_invariant_distribution(
            1.0e5,
            1.0e5,
            1.0,
            0.0,
            0.0,
            M_PROTON,
            E_CHARGE,
            1.0e18,
            900.0,
            1500.0,
            1.0,
            0.0,
            1.0,
            1.0,
            0.0,
            0.0,
            refill,
        )
        assert float(plugged["occupation"]) == refill


def test_a_deeply_negative_exponent_underflows_to_zero_without_raising():
    # mass=1 kg, v_parallel=1e6 m/s, T_parallel=1 J: the exponent is -5e11, so
    # the exponential is below the smallest subnormal and the contract permits
    # the density to round to zero instead of raising.
    returned = evaluate_mirror_invariant_distribution(
        1.0e6,
        0.0,
        1.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
    )
    assert returned["f0_s3_m6"] == 0.0


def test_returned_mapping_has_exactly_the_declared_keys():
    returned = evaluate_mirror_invariant_distribution(
        1.0e5, 1.0e5, 1.0, 0.0, 0.0, M_PROTON, E_CHARGE, 1.0e18, 900.0, 1500.0, 1.0
    )
    assert set(returned) == {
        "f0_s3_m6",
        "energy_j",
        "magnetic_moment_j_t",
        "occupation",
    }


def test_invalid_input_channel_raises_value_error():
    arguments = dict(
        v_parallel_m_s=1.0e5,
        v_perpendicular_m_s=1.0e5,
        b_t=1.0,
        psi=0.0,
        potential_v=0.0,
        mass_kg=M_PROTON,
        charge_c=E_CHARGE,
        density_ref_m3=1.0e18,
        temperature_parallel_j=900.0,
        temperature_perpendicular_ref_j=1500.0,
        b_ref_t=1.0,
    )
    for name, replacement in (
        ("mass_kg", True),
        ("mass_kg", 0.0),
        ("mass_kg", np.inf),
        ("charge_c", 0.0),
        ("charge_c", False),
    ):
        broken = dict(arguments)
        broken[name] = replacement
        with pytest.raises(ValueError, match="must be"):
            evaluate_mirror_invariant_distribution(**broken)

    for refill in (-0.1, 1.5, np.nan):
        with pytest.raises(ValueError, match="loss_cone_refill"):
            evaluate_mirror_invariant_distribution(loss_cone_refill=refill, **arguments)

    one_sided = dict(arguments)
    one_sided["b_plug_left_t"] = 2.0
    with pytest.raises(ValueError, match="both plug fields are required together"):
        evaluate_mirror_invariant_distribution(**one_sided)

    for name, replacement in (
        ("v_parallel_m_s", np.nan),
        ("v_perpendicular_m_s", np.inf),
        ("b_t", np.nan),
        ("psi", np.inf),
        ("potential_v", np.nan),
    ):
        broken = dict(arguments)
        broken[name] = replacement
        with pytest.raises(ValueError, match="must be finite"):
            evaluate_mirror_invariant_distribution(**broken)

    for name, replacement in (
        ("b_t", 0.0),
        ("density_ref_m3", -1.0),
        ("temperature_parallel_j", 0.0),
        ("temperature_perpendicular_ref_j", -1.0),
        ("b_ref_t", 0.0),
    ):
        broken = dict(arguments)
        broken[name] = replacement
        with pytest.raises(ValueError, match="field, reference density, or temperatures"):
            evaluate_mirror_invariant_distribution(**broken)

    unbroadcastable = dict(arguments)
    unbroadcastable["density_ref_m3"] = np.ones(3)
    with pytest.raises(ValueError, match="cannot be broadcast"):
        evaluate_mirror_invariant_distribution(**unbroadcastable)


def test_runtime_failure_channel_raises_floating_point_error():
    # C = (B - B_ref)/T_parallel + B_ref/T_perp,ref turns negative when the local
    # field is well below the reference and the reference term is negligible.
    with pytest.raises(FloatingPointError, match="not integrable"):
        evaluate_mirror_invariant_distribution(
            1.0e5,
            1.0e5,
            0.1,
            0.0,
            0.0,
            M_PROTON,
            E_CHARGE,
            1.0e18,
            1.0,
            100.0,
            1.0,
        )

    # A finite exponent whose exponential leaves the binary64 range is a
    # runtime failure, not a silently infinite density.  B equals B_ref so the
    # integrability coefficient stays finite; only the normalisation overflows.
    with pytest.raises(FloatingPointError, match="exceeds the finite output range"):
        evaluate_mirror_invariant_distribution(
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            1.0,
            1.0,
            1.0e300,
            1.0e-300,
            1.0e-300,
            1.0,
        )
