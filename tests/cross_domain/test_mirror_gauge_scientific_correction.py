"""Unchanged-physics regressions for resolved electrostatic gauge differences."""

from fractions import Fraction
import numpy as np
import pytest
from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state as boltz
from scirel.mirror.mirror_invariant_distribution import (
    evaluate_mirror_invariant_distribution as invariant,
)
from scirel.mirror.mirror_constrained_moments import evaluate_mirror_constrained_moments as moments
from scirel.mirror._mirror_numerics import _mirror_flux

Q = 1.602176634e-19


@pytest.mark.parametrize("shift", [1e20, -1e20])
@pytest.mark.parametrize("direction", [-1.0, 1.0])
def test_resolved_potential_difference_before_charge_product(shift, direction):
    phi = np.nextafter(shift, direction * np.inf)
    delta = phi - shift
    t = Q * abs(delta)
    state = boltz(phi, t, 1.0, shift, 1.0, 1.0)
    exponent = float(Fraction(Q) * (Fraction(float(phi)) - Fraction(shift)) / Fraction(t))
    np.testing.assert_allclose(state["electron_density_m3"], np.exp(exponent), rtol=3e-13, atol=0.0)


@pytest.mark.parametrize("shift", [1e20, -1e20, 1e100, -1e100])
def test_distribution_and_trapping_ignore_constant_gauge(shift):
    args = (0.2, 1.0, 1.0, 0.0)
    reference = invariant(
        *args, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, b_plug_left_t=2.0, b_plug_right_t=3.0
    )
    state = invariant(
        *args,
        shift,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        phi_ref_v=shift,
        b_plug_left_t=2.0,
        b_plug_right_t=3.0,
        phi_plug_left_v=shift,
        phi_plug_right_v=shift,
    )
    assert state["occupation"] == reference["occupation"] == 1.0
    np.testing.assert_allclose(state["f0_s3_m6"], reference["f0_s3_m6"], rtol=3e-13, atol=0.0)
    assert state["energy_j"] == shift  # absolute output legitimately loses sub-ULP kinetic energy


@pytest.mark.parametrize("charge", [Q, -Q])
def test_physical_charge_gauge_retains_resolvable_thermal_distribution(charge):
    t = Q * 16384.0
    vp = np.sqrt(t)
    base = invariant(vp, 0.0, 1.0, 0.0, 0.0, 1.0, charge, 1.0, t, t, 1.0)
    shifted = invariant(vp, 0.0, 1.0, 0.0, 1e20, 1.0, charge, 1.0, t, t, 1.0, phi_ref_v=1e20)
    np.testing.assert_allclose(shifted["f0_s3_m6"], base["f0_s3_m6"], rtol=3e-13, atol=0.0)


@pytest.mark.parametrize(
    "phi,ref,temp,nref",
    [(1e308, -1e308, 1e308, 1e-308), (-1e308, 1e308, 1e308, 1e-308), (1e-300, 0.0, 1e-319, 1.0)],
)
def test_scaled_potential_difference_avoids_intermediate_range_loss(phi, ref, temp, nref):
    exponent = float(Fraction(Q) * (Fraction(phi) - Fraction(ref)) / Fraction(temp))
    out = boltz(phi, temp, nref, ref, 1.0, 1.0)
    np.testing.assert_allclose(
        out["electron_density_m3"], np.exp(np.log(nref) + exponent), rtol=3e-13, atol=0.0
    )


@pytest.mark.parametrize("charge", [1e-308, -1e-308])
def test_moments_and_end_flux_scaled_overflowing_potential_difference(charge):
    # Delta phi=2e308 is not binary64, but q*delta/T=+/-2 is finite.
    exponent = float(Fraction(charge) * (Fraction(1e308) - Fraction(-1e308)))
    out = moments(1.0, 0.0, 1e308, 1.0, charge, 1.0, 1.0, 1.0, 1.0, phi_ref_v=-1e308)
    np.testing.assert_allclose(out["density_m3"], np.exp(-exponent), rtol=3e-13, atol=0.0)
    flux = _mirror_flux(1.0, 1.0, charge, 1.0, 1.0, 1.0, 1.0, -1e308, 1e308, 1.0)
    np.testing.assert_allclose(
        flux, np.exp(-max(exponent, 0.0)) / np.sqrt(2 * np.pi), rtol=3e-13, atol=0.0
    )


def test_refill_boundary_and_even_velocity_preserved_under_gauge():
    for vp in [0.2, 1.0, 2.0]:
        for sign in [-1.0, 1.0]:
            kwargs = dict(
                mass_kg=1.0,
                charge_c=1.0,
                density_ref_m3=1.0,
                temperature_parallel_j=1.0,
                temperature_perpendicular_ref_j=1.0,
                b_ref_t=1.0,
                b_plug_left_t=2.0,
                b_plug_right_t=2.0,
                loss_cone_refill=0.2,
            )
            a = invariant(sign * vp, 1.0, 1.0, 0.0, 0.0, **kwargs)
            b = invariant(
                sign * vp,
                1.0,
                1.0,
                0.0,
                -1e20,
                phi_ref_v=-1e20,
                phi_plug_left_v=-1e20,
                phi_plug_right_v=-1e20,
                **kwargs,
            )
            assert b["occupation"] == a["occupation"]
            np.testing.assert_allclose(b["f0_s3_m6"], a["f0_s3_m6"], rtol=3e-13, atol=0.0)


@pytest.mark.parametrize("shift", [1e20, -1e20, 1e308, -1e308])
def test_local_quasineutral_midpoint_preserves_large_representable_root(shift):
    from scirel.mirror.mirror_quasineutral_closure import solve_mirror_quasineutral_closure

    x = solve_mirror_quasineutral_closure(
        b_t=1.0,
        psi=np.array([0.0]),
        mass_kg=1.0,
        charge_c=Q,
        density_ref_m3=1.0,
        temperature_parallel_j=Q * 16384.0,
        temperature_perpendicular_ref_j=Q * 16384.0,
        b_ref_t=1.0,
        phi_ref_v=shift,
        electron_temperature_j=Q * 16384.0,
    )
    assert x["converged"] and x["electrostatic_potential"][0] == shift
    np.testing.assert_allclose(x["ion_density"], 1.0, rtol=3e-13, atol=0.0)
    np.testing.assert_allclose(x["relative_charge_residual"], 0.0, rtol=0.0, atol=1e-13)


@pytest.mark.parametrize("shift", [1e20, -1e20, 1e308, -1e308])
def test_end_loss_midpoint_preserves_large_representable_balanced_root(shift):
    from scirel.mirror.mirror_ambipolar_potential import solve_mirror_ambipolar_potential

    x = solve_mirror_ambipolar_potential(
        1.0,
        1.0,
        0.0,
        9.1093837139e-31,
        Q,
        1.0,
        Q * 16384.0,
        Q * 16384.0,
        Q * 16384.0,
        phi_reference_v=shift,
    )
    assert x["current_balance_solved"] and x["potential_v"] == shift
    np.testing.assert_allclose(x["relative_current_residual"], 0.0, rtol=0.0, atol=1e-13)
