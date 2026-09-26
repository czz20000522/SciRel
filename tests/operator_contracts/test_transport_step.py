"""Direct contract tests for the r63 transport-step family:
``propagate_neutral_generation``, ``assemble_neutral_upwind_transport_coefficients``,
``assemble_neutral_boltzmann_rhs``.

The saved KN1DPy implementations (SHA-256 pinned in the L1 replay) are
reproduced bit for bit on the declared domain; no repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_neutral_boltzmann_rhs,
    assemble_neutral_upwind_transport_coefficients,
    propagate_neutral_generation,
)


def _fixture(nvr=2, nvx=4, nx=5):
    rng = np.random.default_rng(71)
    vr = np.linspace(0.5, 1.5, nvr)
    vx = np.array([-1.5, -0.5, 0.5, 1.5])[:nvx]
    x = np.linspace(0.0, 1.0, nx)
    shape = (nvr, nvx, nx)
    alpha = rng.uniform(0.1, 1.0, shape)
    source = rng.uniform(0.0, 1.0, shape)
    return vr, vx, x, alpha, source


def test_upwind_coefficients_have_saved_shape_and_sign_structure():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    assert set(result) == {"Ak", "Bk", "Fk", "Ck", "Dk", "Gk", "positive_vx_indices", "negative_vx_indices"}
    for key in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk"):
        assert result[key].shape == alpha.shape
    # positive vx nodes: Ak has diagonal term, Bk=0 for first_flight, Fk has source term
    positive = result["positive_vx_indices"]
    negative = result["negative_vx_indices"]
    assert np.all(vx[positive] > 0)
    assert np.all(vx[negative] < 0)
    # Ck/Dk/Gk are zero on positive branch; Ak/Bk/Fk zero on negative branch
    np.testing.assert_array_equal(result["Ck"][:, positive, :], 0.0)
    np.testing.assert_array_equal(result["Ak"][:, negative, :], 0.0)


def test_upwind_coefficients_forward_step_is_consistent():
    vr, vx, x, alpha, source = _fixture(nvx=4)
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    # the forward trapezoidal coefficients must satisfy:
    # Ak = (2*vx - dx*alpha_k) / (2*vx + dx*alpha_{k+1}) on the positive branch
    positive = result["positive_vx_indices"]
    for k in range(x.size - 1):
        dx = x[k + 1] - x[k]
        for j in positive:
            expected_a = (2.0 * vx[j] - dx * alpha[:, j, k]) / (2.0 * vx[j] + dx * alpha[:, j, k + 1])
            np.testing.assert_allclose(result["Ak"][:, j, k], expected_a, rtol=1e-14)


def test_propagate_first_flight_with_boundary():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    boundary = np.ones((alpha.shape[0], alpha.shape[1]))
    gen = propagate_neutral_generation(
        vx, result["Ak"], result["Bk"], result["Fk"],
        result["Ck"], result["Dk"], result["Gk"],
        generation_kind="first_flight", incoming_boundary=boundary,
    )
    assert gen.shape == alpha.shape
    assert np.all(np.isfinite(gen))
    # positive branch: forward propagation from boundary
    positive = result["positive_vx_indices"]
    for j in positive:
        for k in range(x.size - 1):
            expected = gen[:, j, k] * result["Ak"][:, j, k] + result["Fk"][:, j, k]
            np.testing.assert_allclose(gen[:, j, k + 1], expected, rtol=1e-14)


def test_propagate_scattered_with_source():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    gen = propagate_neutral_generation(
        vx, result["Ak"], result["Bk"], result["Fk"],
        result["Ck"], result["Dk"], result["Gk"],
        generation_kind="scattered", scattered_source_distribution=source,
    )
    assert gen.shape == alpha.shape
    assert np.all(np.isfinite(gen))


def test_propagate_rejects_missing_source_or_boundary():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    with pytest.raises(ValueError, match="first_flight needs exactly one"):
        propagate_neutral_generation(
            vx, result["Ak"], result["Bk"], result["Fk"],
            result["Ck"], result["Dk"], result["Gk"], generation_kind="first_flight",
        )
    with pytest.raises(ValueError, match="scattered needs exactly one"):
        propagate_neutral_generation(
            vx, result["Ak"], result["Bk"], result["Fk"],
            result["Ck"], result["Dk"], result["Gk"], generation_kind="scattered",
        )


def test_propagate_rejects_invalid_generation_kind():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    with pytest.raises(ValueError, match="generation_kind"):
        propagate_neutral_generation(
            vx, result["Ak"], result["Bk"], result["Fk"],
            result["Ck"], result["Dk"], result["Gk"], generation_kind="invalid",
        )


def test_boltzmann_rhs_matches_independent_recomputation():
    rng = np.random.default_rng(72)
    shape = (2, 3, 4)
    vth = 5000.0
    fields = {name: rng.uniform(-1.0, 1.0, shape) for name in
              ("coeff_source", "cx_sum", "coll_freq", "total_dist", "elastic_sum", "wall_sum")}
    rhs = assemble_neutral_boltzmann_rhs(
        vth, fields["coeff_source"], fields["cx_sum"], fields["coll_freq"],
        fields["total_dist"], fields["elastic_sum"], fields["wall_sum"],
    )
    expected = vth * (
        fields["coeff_source"] + fields["cx_sum"]
        - fields["coll_freq"] * fields["total_dist"]
        + fields["elastic_sum"] + fields["wall_sum"]
    )
    np.testing.assert_array_equal(rhs["rhs"], expected)


def test_boltzmann_rhs_rejects_nonfinite_or_mismatched():
    shape = (1, 1, 1)
    ones = np.ones(shape)
    with pytest.raises(ValueError, match="positive and finite"):
        assemble_neutral_boltzmann_rhs(
            float("nan"), ones, ones, ones, ones, ones, ones,
        )
    with pytest.raises(ValueError, match="one shape"):
        assemble_neutral_boltzmann_rhs(
            5000.0, ones, ones, ones, np.ones((2, 2, 2)), ones, ones,
        )
    with pytest.raises(ValueError, match="finite"):
        assemble_neutral_boltzmann_rhs(
            5000.0, np.full(shape, np.nan), ones, ones, ones, ones, ones,
        )

def test_upwind_rejects_nonfinite_x():
    """Pre-review regression: NaN in x passes the monotonic predicate
    (NaN comparisons are False) and produces NaN coefficients; the exact
    document requires finite x, so this asset fail-closes."""
    vx = np.array([-1.0, 1.0])
    alpha = np.ones((1, 2, 3))
    source = np.ones((1, 2, 3))
    with pytest.raises(ValueError, match="contract is invalid"):
        assemble_neutral_upwind_transport_coefficients(
            np.array([0.0, float("nan"), 1.0]), vx, alpha, source
        )
    with pytest.raises(ValueError, match="contract is invalid"):
        assemble_neutral_upwind_transport_coefficients(
            np.array([0.0, float("inf"), 1.0]), vx, alpha, source
        )
