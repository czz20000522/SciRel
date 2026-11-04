"""The self-collision frequency matches the Boltzmann stress relaxation rate.

For equal masses a collision of relative velocity g, scattering angle chi, changes
Q(v) = v_perp^2 - 2 v_x^2, averaged over the pair and the azimuth, by

    (1/4) (P2(cos chi) - 1) Q(g) = -(3/8) sin^2(chi) Q(g),

so d<Q>/dt = -(3/8) n <<g sigma_vis Q(g)>> with sigma_vis = Integral sin^2(chi) dsigma.
A BGK operator gives d<Q>/dt = -nu <Q>, which fixes nu. Hard spheres of diameter d have
sigma_vis = (2/3) pi d^2, and nu must equal p/mu of the first Chapman-Enskog approximation,
(16/5) sqrt(pi) n d^2 sqrt(kT/m) (Chapman and Cowling; cited from memory, and the formula
below follows from the known mu = (5/16) sqrt(pi m k T)/(pi d^2)).
"""

import math

import numpy as np
import pytest

from scirel.collisions import atomic_hydrogen_collision_matrices as module
from scirel.collisions.atomic_hydrogen_omega_frequencies import (
    assemble_atomic_hydrogen_omega_frequencies,
)

MASS, CHARGE = 1.6726231e-27, 1.602177e-19
DIAMETER = 1.0e-10


def test_hard_sphere_frequency_is_p_over_mu(monkeypatch):
    sigma = 2.0 / 3.0 * math.pi * DIAMETER**2
    monkeypatch.setattr(
        module,
        "evaluate_atomic_hydrogen_elastic_cross_section",
        lambda energy, viscosity=False: np.full_like(energy, sigma),
    )
    edges_r = np.linspace(0.0, 3.5, 15)
    edges_x = np.linspace(-3.5, 3.5, 25)
    vr = 0.5 * (edges_r[:-1] + edges_r[1:])
    vx = 0.5 * (edges_x[:-1] + edges_x[1:])
    radial = math.pi * np.diff(edges_r**2)
    dvx = np.diff(edges_x)
    tnorm, density = 10.0, 1.0e19
    matrices = module.assemble_atomic_hydrogen_collision_matrices(
        vr, vx, radial, dvx, tnorm, mu=1.0
    )
    vth = math.sqrt(matrices["Vth2"][0])
    # A slightly anisotropic Maxwellian at T = Tnorm, the first Sonine perturbation shape.
    f = np.exp(-(vr[:, None] ** 2 * (1 - 0.01) + vx[None, :] ** 2 * (1 + 0.02)))
    f *= density / np.sum(radial[:, None] * dvx[None, :] * f)
    result = assemble_atomic_hydrogen_omega_frequencies(
        f[..., None],
        np.array([density]),
        np.zeros(f.shape + (1,)),
        np.zeros(f.shape + (1,)),
        matrices["SIG_H_H"],
        radial,
        dvx,
        vr,
        vx,
        vth,
        np.zeros(1),
        np.zeros(1),
        H_P_EL=False,
        H_H2_EL=False,
    )
    expected = (
        16.0 / 5.0 * math.sqrt(math.pi) * density * DIAMETER**2 * math.sqrt(CHARGE * tnorm / MASS)
    )
    assert result["nu_H_H"][0] == pytest.approx(expected, rel=0.05)
