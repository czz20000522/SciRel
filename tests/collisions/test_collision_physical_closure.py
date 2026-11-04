"""Independent angular integration and physical distribution contracts.

SciPy quadrature is development-only; the selected scientific wheel uses NumPy.
Fit coefficients in existing independent test oracles are retained, rather than
calling the production fit to construct the reference integral.
"""

import gc
import numpy as np
import pytest
from scipy.integrate import quad
from scirel.collisions import (
    assemble_atomic_hydrogen_collision_matrices as atomic_matrices,
    assemble_molecular_hydrogen_collision_matrices as molecular_matrices,
    assemble_atomic_hydrogen_omega_frequencies as atomic_moments,
    assemble_molecular_hydrogen_omega_frequencies as molecular_moments,
)
from test_atomic_hydrogen_collision_matrices import (
    _sigma_cx as acx,
    _sigma_h_h as aa,
    _sigma_h_hh as am,
    _sigma_p_h as ap,
)
from test_molecular_hydrogen_collision_matrices import (
    _sigma_cx as mcx,
    _sigma_h_hh as ma,
    _sigma_p_hh as mp,
    _sigma_hh_hh as mm,
)

CASES = [
    (
        atomic_matrices,
        atomic_moments,
        ["H_P", "H_H2", "H_H"],
        [acx, ap, am, aa],
        "VxH",
        "Wperp_paraH",
    ),
    (
        molecular_matrices,
        molecular_moments,
        ["H2_P", "H2_H", "H2_H2"],
        [mcx, mp, ma, mm],
        "VxH2",
        "Wperp_paraH2",
    ),
]


@pytest.mark.parametrize("make,reduce,names,fits,flow,stress", CASES)
@pytest.mark.parametrize("mu", [1.0, 2.0])
def test_adaptive_angular_oracle_and_weighted_exchange(make, reduce, names, fits, flow, stress, mu):
    vr = np.array([0.35, 0.9])
    vx = np.array([-0.6, 0.8])
    wr = np.array([0.7, 1.2])
    dx = np.array([0.6, 1.1])
    T = 0.15
    w = (wr[:, None] * dx).ravel(order="F")
    coords = [(r, x) for x in vx for r in vr]
    r = make(vr, vx, wr, dx, T, mu, n_theta=4096)
    factor = 1 if make is atomic_matrices else 2
    energy = [factor * T / mu, T / mu, T / mu, factor * T]
    for ci, key in enumerate(["SIG_CX"] + ["SIG_" + n for n in names]):
        expected = np.empty((4, 4))
        for i, (ri, xi) in enumerate(coords):
            for j, (rj, xj) in enumerate(coords):

                def integrand(t):
                    perp = (ri - rj) ** 2 + 4 * ri * rj * np.sin(t / 2) ** 2
                    g2 = perp + (xi - xj) ** 2
                    value = np.sqrt(g2) * float(fits[ci](np.asarray(g2 * energy[ci])))
                    if ci in (1, 2):
                        value *= xi - xj
                    elif ci == 3:
                        value *= (perp - 2 * (xi - xj) ** 2) / 8
                    return value

                expected[i, j] = (
                    w[j]
                    * quad(integrand, 0, np.pi, epsabs=1e-29, epsrel=2e-10, limit=300)[0]
                    / np.pi
                )
        np.testing.assert_allclose(r[key], expected, rtol=1e-6, atol=1e-26)
        weighted = w[:, None] * r[key]
        np.testing.assert_allclose(
            weighted, (-1 if ci in (1, 2) else 1) * weighted.T, rtol=1e-14, atol=1e-32
        )
    assert np.all(r["SIG_CX"] >= 0)
    for key in ["SIG_" + n for n in names]:
        assert np.any(r[key] < 0)
    boosted = make(vr, vx + 8.0, wr, dx, T, mu, n_theta=4096)
    for key in ["SIG_CX"] + ["SIG_" + n for n in names]:
        np.testing.assert_allclose(r[key], boosted[key], rtol=1e-14, atol=1e-32)


def physical_case(make, reduce, names, flow, stress, nr=8, nv=12, drift=0.15):
    lr, lw = np.polynomial.laguerre.laggauss(nr)
    vx, xw = np.polynomial.hermite.hermgauss(nv)
    vr = np.sqrt(lr)
    wr = np.pi * lw * np.exp(lr)
    dx = xw * np.exp(vx * vx)
    weights = wr[:, None] * dx

    # Discrete nonnegative Maxwellians, normalized to the specified density.
    def maxwell(n, u, aniso=1.0):
        f = np.exp(-(vr[:, None] ** 2) - (vx[None, :] - u) ** 2 / aniso)
        return n * f / np.sum(weights * f)

    f = maxwell(2e17, drift, 1.3)
    bg1 = maxwell(3e17, 0)
    bg2 = maxwell(1e17, -0.08)
    matrices = make(vr, vx, wr, dx, 1.0, 2.0, n_theta=24)
    vth = float(np.sqrt(matrices["Vth2"][0]))
    alphas = [
        (matrices["SIG_" + c] @ bg.ravel(order="F")).reshape((nr, nv), order="F")[:, :, None]
        for c, bg in zip(names[:2], [bg1, bg2])
    ]
    bgflows = [np.array([vth * np.sum(weights * b * vx) / np.sum(weights * b)]) for b in [bg1, bg2]]
    args = [
        f[:, :, None],
        np.array([2e17]),
        *alphas,
        matrices["SIG_" + names[2]],
        wr,
        dx,
        vr,
        vx,
        vth,
        *bgflows,
    ]
    return reduce(*args), args, matrices, weights, bg1, bg2


@pytest.mark.parametrize("make,reduce,names,fits,flow,stress", CASES)
def test_real_generated_channels_and_momentum_exchange(make, reduce, names, fits, flow, stress):
    r, a, mat, w, b1, b2 = physical_case(make, reduce, names, flow, stress)
    for i, c in enumerate(names):
        assert r["defined_" + c].all()
        assert np.isfinite(r["nu_" + c]).all()
        # Independent double sum from actual SIG and physical distributions.
        f = a[0][:, :, 0]
        b = [b1, b2, f][i]
        W = w.ravel(order="F")
        raw = (
            np.sum(
                W[:, None]
                * f.ravel(order="F")[:, None]
                * mat["SIG_" + c]
                * b.ravel(order="F")[None, :]
            )
            / a[1][0]
        )
        np.testing.assert_allclose(r["moment_" + c][0], raw, rtol=1e-14, atol=0)
    # Reverse H <-> H2 uses the same H-on-H2 laboratory-energy fit. With
    # momentum mass factors 2/3 and 1/3, actual force densities cancel.
    other = molecular_matrices if make is atomic_matrices else atomic_matrices
    revname = "H2_H" if make is atomic_matrices else "H_H2"
    reverse = other(a[7], a[8], a[5], a[6], 1.0, 2.0, n_theta=24)["SIG_" + revname]
    fw = a[0][:, :, 0].ravel(order="F")
    bw = b2.ravel(order="F")
    W = w.ravel(order="F")
    forward = np.dot(W * fw, mat["SIG_" + names[1]] @ bw)
    backward = np.dot(W * bw, reverse @ fw)
    np.testing.assert_allclose(forward, -backward, rtol=1e-14, atol=0)
    del mat
    gc.collect()


@pytest.mark.parametrize("make,reduce,names,fits,flow,stress", CASES)
def test_equilibrium_momentum_and_weak_drift_no_floor(make, reduce, names, fits, flow, stress):
    # Identical equilibrium populations have zero mixed momentum by pair
    # antisymmetry. A self target f gives exact zero stress denominator;
    # discretization residuals are exposed, never converted to a fake rate.
    r, a, mat, w, b1, b2 = physical_case(make, reduce, names, flow, stress, nr=6, nv=10, drift=0)
    f = a[0][:, :, 0]
    flat = f.ravel(order="F")
    a[2] = (mat["SIG_" + names[0]] @ flat).reshape(f.shape, order="F")[:, :, None]
    a[10] = r[flow].copy()
    q = reduce(*a, moment_state="target", target_distribution=a[0])
    scale = np.sum(np.abs(w * f * a[2][:, :, 0])) / a[1][0]
    assert abs(q["moment_" + names[0]][0]) <= 1e-14 * scale
    assert not q["defined_" + names[0]][0] and not q["defined_" + names[2]][0]
    assert not q["defined_EL"][0] and np.isnan(q["nu_EL"][0])
    values = []
    # A fixed family of weak shifted physical Maxwellians, both sides of zero.
    for drift in [-0.002, -0.001, 0.001, 0.002]:
        f = np.exp(-(a[7][:, None] ** 2) - (a[8][None, :] - drift) ** 2)
        f *= a[1][0] / np.sum(w * f)
        a[0] = f[:, :, None]
        bg = np.exp(-(a[7][:, None] ** 2) - a[8][None, :] ** 2)
        bg *= 3e17 / np.sum(w * bg)
        a[2] = (mat["SIG_" + names[0]] @ bg.ravel(order="F")).reshape(f.shape, order="F")[
            :, :, None
        ]
        a[10] = np.array([a[9] * np.sum(w * bg * a[8]) / 3e17])
        t = reduce(*a)
        values.append(float(t["nu_" + names[0]][0]))
        assert values[-1] > 0
    np.testing.assert_allclose(values[0], values[3], rtol=1e-11, atol=0)
    np.testing.assert_allclose(values[1], values[2], rtol=1e-11, atol=0)
    assert abs(values[1] / values[0] - 1) < 2e-5
