"""T-2026-0001: discrete momentum evidence, not a cross-section oracle.

For equal nuclear masses, the declared exchange source is
Vth * [f_i * (SIG_CX @ f_H) - f_H * (SIG_CX @ f_i)].
SIG includes column quadrature weights and normalized relative speed.
Taking its first moment gives -Vth**2/n_H times the pair integral of
(vx-vx') * g * sigma_CX. The existing elastic reduction gives the same
integral with sigma_mt and a factor 1/2. The exchange source is constructed
here as an explicit assumption; SciRel has no combined transport solver.

The independent constant-cross-section reference integrates relative speed
analytically with a complete elliptic integral. It does not reuse the
assembler's angular grid, flattening, Alpha contraction or reduction.
"""

from __future__ import annotations

import importlib
import math

import numpy as np
import pytest
from scipy.special import ellipe

from scirel.collisions import (
    assemble_atomic_hydrogen_collision_matrices,
    assemble_atomic_hydrogen_omega_frequencies,
)
from scirel.kinetic import contract_atomic_hydrogen_alpha_frequencies


def _distributions(*, reverse=False, equal=False):
    vr = np.array([0.2, 0.85])
    vx = np.array([-1.1, -0.2, 0.7, 1.6])
    wr = np.array([0.35, 1.4])
    dx = np.array([0.4, 0.9, 1.1, 0.6])
    weights = wr[:, None] * dx[None, :]
    neutral = np.array([[4.0, 2.0, 1.0, 0.5], [1.0, 3.0, 2.0, 0.25]])
    ion = np.array([[0.5, 1.0, 2.0, 4.0], [0.25, 2.0, 3.0, 1.0]])
    if reverse:
        neutral, ion = ion, neutral
    if equal:
        ion = neutral.copy()
    nh, ni = 2e17, 3e17
    neutral *= nh / np.sum(weights * neutral)
    ion *= ni / np.sum(weights * ion)
    return vr, vx, wr, dx, weights, neutral, ion, nh, ni


def _budget(state, *, n_theta=64):
    vr, vx, wr, dx, weights, neutral, ion, nh, ni = state
    matrices = assemble_atomic_hydrogen_collision_matrices(
        vr, vx, wr, dx, 3.0, mu=1.0, n_theta=n_theta
    )
    vth = math.sqrt(float(matrices["Vth2"][0]))
    alpha = contract_atomic_hydrogen_alpha_frequencies(
        matrices["SIG_CX"],
        matrices["SIG_H_H"],
        matrices["SIG_H_H2"],
        matrices["SIG_H_P"],
        (ion / ni)[:, :, None],
        np.array([ni]),
        np.zeros((*neutral.shape, 1)),
        neutral[:, :, None],
    )
    flow_i = vth * np.sum(weights * ion * vx[None, :]) / ni
    reduction = assemble_atomic_hydrogen_omega_frequencies(
        neutral[:, :, None],
        np.array([nh]),
        alpha["Alpha_H_P"],
        alpha["Alpha_H_H2"],
        matrices["SIG_H_H"],
        wr,
        dx,
        vr,
        vx,
        vth,
        np.array([flow_i]),
        np.array([flow_i]),
        H_H2_EL=False,
        H_H_EL=False,
    )
    # Evaluate gain and loss separately. Only the loss reuses the public
    # Alpha result; gain contracts the same symmetric kernel with neutrals.
    gain = ion * (matrices["SIG_CX"] @ neutral.ravel(order="F")).reshape(neutral.shape, order="F")
    loss = neutral * alpha["Alpha_CX"][:, :, 0]
    exchange = vth * (gain - loss)
    exchange_acceleration = vth / nh * np.sum(weights * vx[None, :] * exchange)
    return {
        "elastic_acceleration": float(reduction["moment_rate_H_P"][0]),
        "exchange_acceleration": float(exchange_acceleration),
        "exchange_number_rate": float(np.sum(weights * exchange)),
        "exchange_number_scale": float(vth * np.sum(weights * (gain + loss))),
        "vth": vth,
    }


def _constant_reference(state, vth, sigma):
    """Independent scalar pair sum with an analytic azimuthal average."""
    vr, vx, wr, dx, _, neutral, ion, nh, _ = state
    terms = []
    for ir, r in enumerate(vr):
        for ix, x in enumerate(vx):
            for jr, rp in enumerate(vr):
                for jx, xp in enumerate(vx):
                    a_plus_b = (r + rp) ** 2 + (x - xp) ** 2
                    parameter = 4 * r * rp / a_plus_b
                    mean_g = 2 / math.pi * math.sqrt(a_plus_b) * ellipe(parameter)
                    terms.append(
                        wr[ir]
                        * dx[ix]
                        * neutral[ir, ix]
                        * wr[jr]
                        * dx[jx]
                        * ion[jr, jx]
                        * (x - xp)
                        * mean_g
                    )
    return -(vth**2) * sigma * math.fsum(terms) / nh


@pytest.mark.parametrize("reverse", [False, True])
def test_constant_cross_sections_have_the_derived_exchange_and_elastic_moments(
    monkeypatch, reverse
):
    module = importlib.import_module("scirel.collisions.atomic_hydrogen_collision_matrices")
    sigma_cx, sigma_mt = 1.1e-19, 2.3e-19
    monkeypatch.setattr(
        module,
        "evaluate_atomic_hydrogen_charge_exchange_cross_section",
        lambda energy: np.full_like(energy, sigma_cx),
    )
    monkeypatch.setattr(
        module,
        "evaluate_hydrogen_proton_elastic_cross_section",
        lambda energy: np.full_like(energy, sigma_mt),
    )
    state = _distributions(reverse=reverse)
    result = _budget(state)
    # Use the declared Tnorm=3 eV, mu=1 and frozen SI constants rather
    # than the returned Vth: an erroneous common velocity scale must fail.
    expected_vth = math.sqrt(2 * 1.602177e-19 * 3.0 / 1.6726231e-27)
    np.testing.assert_allclose(
        result["vth"],
        expected_vth,
        rtol=2e-15,
        atol=0,
        err_msg="Vth must follow the declared input energy, mass and normalization",
    )
    expected_cx = _constant_reference(state, expected_vth, sigma_cx)
    expected_elastic = 0.5 * _constant_reference(state, expected_vth, sigma_mt)
    # Cross-node axial gaps keep the angular integrand smooth. Diagonal
    # angular cusps multiply exactly zero axial difference. 64 vs 128 nodes
    # is checked separately below; this is numerical, not model tolerance.
    np.testing.assert_allclose(
        result["exchange_acceleration"],
        expected_cx,
        rtol=3e-13,
        atol=0,
        err_msg="CX first moment must match gain-loss exchange with full relative momentum",
    )
    np.testing.assert_allclose(
        result["elastic_acceleration"],
        expected_elastic,
        rtol=3e-13,
        atol=0,
        err_msg="equal-mass elastic first moment must retain its 1/2 mass factor",
    )
    np.testing.assert_allclose(
        result["exchange_acceleration"] / result["elastic_acceleration"],
        2 * sigma_cx / sigma_mt,
        rtol=3e-13,
        err_msg="the constant-cross-section ratio follows from operators, not a backward-angle assumption",
    )
    assert abs(result["exchange_number_rate"]) <= (
        128 * np.finfo(float).eps * result["exchange_number_scale"]
    ), "CX gain and loss must conserve neutral particle number with nonuniform quadrature"


@pytest.mark.parametrize("reverse", [False, True])
def test_current_fits_conserve_number_and_resolve_the_signed_momentum_budget(reverse):
    state = _distributions(reverse=reverse)
    result = _budget(state)
    refined = _budget(state, n_theta=128)
    for key in ("exchange_acceleration", "elastic_acceleration"):
        np.testing.assert_allclose(
            result[key],
            refined[key],
            rtol=3e-13,
            atol=0,
            err_msg="the selected distribution's momentum budget must be angularly resolved",
        )
    direction = -1 if reverse else 1
    assert direction * result["exchange_acceleration"] > 0
    assert direction * result["elastic_acceleration"] > 0
    assert abs(result["exchange_number_rate"]) <= (
        128 * np.finfo(float).eps * result["exchange_number_scale"]
    ), "particle exchange must conserve neutral number before comparing momentum terms"


def test_identical_distributions_have_zero_momentum_transfer_without_a_defined_ratio():
    state = _distributions(equal=True)
    result = _budget(state)
    # The scale is based on gross event rates, not the small cancelling moment.
    vr, vx, _, _, _, _, _, nh, _ = state
    scale = result["vth"] * max(max(abs(vx)), max(vr)) / nh
    bound = 128 * np.finfo(float).eps * result["exchange_number_scale"] * scale
    assert abs(result["exchange_acceleration"]) <= bound
    assert abs(result["elastic_acceleration"]) <= bound
