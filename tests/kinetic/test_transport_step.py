"""Direct contract tests for the r63 transport-step family:
``propagate_neutral_generation``, ``assemble_neutral_upwind_transport_coefficients``,
``assemble_neutral_boltzmann_rhs``.

The saved the neutral-transport formulation implementations (SHA-256 pinned in the L1 replay) are
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
    assert set(result) == {
        "Ak",
        "Bk",
        "Fk",
        "Ck",
        "Dk",
        "Gk",
        "positive_vx_indices",
        "negative_vx_indices",
    }
    for key in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk"):
        assert result[key].shape == alpha.shape
    # The coefficient arrays separate the positive and negative velocity branches.
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
            expected_a = (2.0 * vx[j] - dx * alpha[:, j, k]) / (
                2.0 * vx[j] + dx * alpha[:, j, k + 1]
            )
            np.testing.assert_allclose(result["Ak"][:, j, k], expected_a, rtol=1e-14)


def test_propagate_first_flight_with_boundary():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    boundary = np.ones((alpha.shape[0], alpha.shape[1]))
    gen = propagate_neutral_generation(
        vx,
        result["Ak"],
        result["Bk"],
        result["Fk"],
        result["Ck"],
        result["Dk"],
        result["Gk"],
        generation_kind="first_flight",
        incoming_boundary=boundary,
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
        vx,
        result["Ak"],
        result["Bk"],
        result["Fk"],
        result["Ck"],
        result["Dk"],
        result["Gk"],
        generation_kind="scattered",
        scattered_source_distribution=source,
    )
    assert gen.shape == alpha.shape
    assert np.all(np.isfinite(gen))


def test_propagate_rejects_missing_source_or_boundary():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    with pytest.raises(ValueError, match="first_flight needs exactly one"):
        propagate_neutral_generation(
            vx,
            result["Ak"],
            result["Bk"],
            result["Fk"],
            result["Ck"],
            result["Dk"],
            result["Gk"],
            generation_kind="first_flight",
        )
    with pytest.raises(ValueError, match="scattered needs exactly one"):
        propagate_neutral_generation(
            vx,
            result["Ak"],
            result["Bk"],
            result["Fk"],
            result["Ck"],
            result["Dk"],
            result["Gk"],
            generation_kind="scattered",
        )


def test_propagate_rejects_invalid_generation_kind():
    vr, vx, x, alpha, source = _fixture()
    result = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    with pytest.raises(ValueError, match="generation_kind"):
        propagate_neutral_generation(
            vx,
            result["Ak"],
            result["Bk"],
            result["Fk"],
            result["Ck"],
            result["Dk"],
            result["Gk"],
            generation_kind="invalid",
        )


def test_boltzmann_rhs_matches_independent_recomputation():
    rng = np.random.default_rng(72)
    shape = (2, 3, 4)
    vth = 5000.0
    fields = {
        name: rng.uniform(-1.0, 1.0, shape)
        for name in ("coeff_source", "cx_sum", "coll_freq", "total_dist", "elastic_sum", "wall_sum")
    }
    rhs = assemble_neutral_boltzmann_rhs(
        vth,
        fields["coeff_source"],
        fields["cx_sum"],
        fields["coll_freq"],
        fields["total_dist"],
        fields["elastic_sum"],
        fields["wall_sum"],
    )
    expected = vth * (
        fields["coeff_source"]
        + fields["cx_sum"]
        - fields["coll_freq"] * fields["total_dist"]
        + fields["elastic_sum"]
        + fields["wall_sum"]
    )
    np.testing.assert_array_equal(rhs["rhs"], expected)


def test_boltzmann_rhs_rejects_nonfinite_or_mismatched():
    shape = (1, 1, 1)
    ones = np.ones(shape)
    with pytest.raises(ValueError, match="positive and finite"):
        assemble_neutral_boltzmann_rhs(
            float("nan"),
            ones,
            ones,
            ones,
            ones,
            ones,
            ones,
        )
    with pytest.raises(ValueError, match="one shape"):
        assemble_neutral_boltzmann_rhs(
            5000.0,
            ones,
            ones,
            ones,
            np.ones((2, 2, 2)),
            ones,
            ones,
        )
    with pytest.raises(ValueError, match="finite"):
        assemble_neutral_boltzmann_rhs(
            5000.0,
            np.full(shape, np.nan),
            ones,
            ones,
            ones,
            ones,
            ones,
        )


def test_upwind_rejects_nonfinite_x():
    """Pre-review regression: NaN in x passes the monotonic predicate
    (NaN comparisons are False) and produces NaN coefficients; the exact
    document requires finite x, so this asset fail-closes."""
    vx = np.array([-1.0, 1.0])
    alpha = np.ones((1, 2, 3))
    source = np.ones((1, 2, 3))
    with pytest.raises(ValueError, match="x_m"):
        assemble_neutral_upwind_transport_coefficients(
            np.array([0.0, float("nan"), 1.0]), vx, alpha, source
        )
    with pytest.raises(ValueError, match="x_m"):
        assemble_neutral_upwind_transport_coefficients(
            np.array([0.0, float("inf"), 1.0]), vx, alpha, source
        )


def test_propagate_rejects_nonfinite_vx():
    """Pre-review regression: the saved arm accepts a NaN vx node and
    silently leaves the corresponding generation slice zero; the exact
    document requires finite vx, so this asset fail-closes."""
    vx = np.array([-1.0, float("nan"), 1.0])
    Ak = np.ones((1, 3, 3))
    Bk = np.ones((1, 3, 3))
    Fk = np.ones((1, 3, 3))
    Ck = np.ones((1, 3, 3))
    Dk = np.ones((1, 3, 3))
    Gk = np.ones((1, 3, 3))
    with pytest.raises(ValueError, match="vx"):
        propagate_neutral_generation(
            vx,
            Ak,
            Bk,
            Fk,
            Ck,
            Dk,
            Gk,
            generation_kind="first_flight",
            incoming_boundary=np.ones((1, 3)),
        )


def test_first_flight_uses_fk_not_bk():
    """Pre-review regression: first_flight uses Fk as the forward source
    term, not Bk; scattered uses Bk (positive) and Dk (negative).  This
    distinguishes the two generation kinds by their coefficient usage."""
    nvr, nvx, nx = 1, 2, 3
    vx = np.array([-1.0, 1.0])
    Ak = np.zeros((nvr, nvx, nx))
    Bk = np.ones((nvr, nvx, nx)) * 10.0
    Fk = np.ones((nvr, nvx, nx)) * 5.0
    Ck = np.zeros((nvr, nvx, nx))
    Dk = np.ones((nvr, nvx, nx)) * 20.0
    Gk = np.ones((nvr, nvx, nx)) * 7.0
    boundary = np.ones((nvr, nvx))
    src = np.ones((nvr, nvx, nx))
    gen_ff = propagate_neutral_generation(
        vx,
        Ak,
        Bk,
        Fk,
        Ck,
        Dk,
        Gk,
        generation_kind="first_flight",
        incoming_boundary=boundary,
    )
    gen_sc = propagate_neutral_generation(
        vx,
        Ak,
        Bk,
        Fk,
        Ck,
        Dk,
        Gk,
        generation_kind="scattered",
        scattered_source_distribution=src,
    )
    # first_flight positive branch uses Fk (5), not Bk (10)
    np.testing.assert_allclose(gen_ff[0, 1, 1], 5.0)
    # scattered positive branch uses Bk (10)
    np.testing.assert_allclose(gen_sc[0, 1, 1], 20.0)


def test_propagate_nx_zero_fail_closed():
    """Pre-review regression: nx=0 raises a raw IndexError on the saved arm
    (generation[:, positive, 0] with empty axis); this asset fail-closes
    with a named ValueError instead."""
    vx = np.array([-1.0, 1.0])
    Ak = np.ones((1, 2, 0))
    Bk = np.ones((1, 2, 0))
    Fk = np.ones((1, 2, 0))
    Ck = np.ones((1, 2, 0))
    Dk = np.ones((1, 2, 0))
    Gk = np.ones((1, 2, 0))
    with pytest.raises(ValueError, match="nx must be at least one"):
        propagate_neutral_generation(
            vx,
            Ak,
            Bk,
            Fk,
            Ck,
            Dk,
            Gk,
            generation_kind="first_flight",
            incoming_boundary=np.ones((1, 2)),
        )


def test_transport_inputs_reject_real_value_coercion():
    x = np.array([0.0, 1.0])
    vx = np.array([-1.0, 1.0])
    field = np.ones((1, 2, 2))
    for invalid in ([True, False], ["-1", "1"], [-1j, 1j]):
        with pytest.raises(ValueError, match="vx"):
            assemble_neutral_upwind_transport_coefficients(x, invalid, field, field)
    with pytest.raises(ValueError, match="collision_frequency_m_inv"):
        assemble_neutral_upwind_transport_coefficients(x, vx, field.astype(complex), field)
    with pytest.raises(ValueError, match="Ak"):
        propagate_neutral_generation(
            vx,
            field.astype(complex),
            field,
            field,
            field,
            field,
            field,
            "first_flight",
            incoming_boundary=np.ones((1, 2)),
        )
    with pytest.raises(ValueError, match="total_distribution"):
        assemble_neutral_boltzmann_rhs(
            1.0,
            field,
            field,
            field,
            field.astype(complex),
            field,
            field,
        )


def test_transport_fails_closed_when_finite_inputs_overflow_output():
    x = np.array([0.0, 1.0])
    vx = np.array([-1.0, 1.0])
    field = np.ones((1, 2, 2))
    with pytest.raises(ValueError, match="finite"):
        assemble_neutral_upwind_transport_coefficients(x, vx, field, field * 1e308)
    with pytest.raises(ValueError, match="finite"):
        propagate_neutral_generation(
            vx,
            field * 1e308,
            field,
            field,
            field,
            field,
            field,
            "first_flight",
            incoming_boundary=np.full((1, 2), 1e308),
        )
    with pytest.raises(ValueError, match="finite"):
        assemble_neutral_boltzmann_rhs(1e308, field, field, field, field, field, field)


def test_first_flight_negative_boundary_is_zero_and_backward_term_is_gk():
    vx = np.array([-1.0, 1.0])
    zeros = np.zeros((1, 2, 3))
    g = np.full((1, 2, 3), 7.0)
    boundary = np.array([[99.0, 3.0]])
    result = propagate_neutral_generation(
        vx,
        zeros,
        zeros,
        zeros,
        zeros,
        zeros,
        g,
        "first_flight",
        incoming_boundary=boundary,
    )
    np.testing.assert_array_equal(result[0, 0, :], [7.0, 7.0, 0.0])
    np.testing.assert_array_equal(result[0, 1, :], [3.0, 0.0, 0.0])


def test_first_flight_preserves_signed_positive_incoming_cells():
    vx = np.array([-1.0, 1.0])
    zeros = np.zeros((1, 2, 2))
    result = propagate_neutral_generation(
        vx,
        zeros,
        zeros,
        zeros,
        zeros,
        zeros,
        zeros,
        "first_flight",
        incoming_boundary=np.array([[0.4, -0.2]]),
    )
    assert result[0, 1, 0] == -0.2
    assert result[0, 0, 1] == 0.0


def test_scattered_negative_branch_uses_dk():
    vx = np.array([-1.0, 1.0])
    zeros = np.zeros((1, 2, 3))
    b = np.full((1, 2, 3), 10.0)
    d = np.full((1, 2, 3), 20.0)
    result = propagate_neutral_generation(
        vx,
        zeros,
        b,
        zeros,
        zeros,
        d,
        zeros,
        "scattered",
        scattered_source_distribution=np.ones((1, 2, 3)),
    )
    np.testing.assert_array_equal(result[0, 0, :], [40.0, 40.0, 0.0])
    np.testing.assert_array_equal(result[0, 1, :], [0.0, 20.0, 20.0])


def test_upwind_rejects_unrepresentable_spatial_step():
    vx = np.array([-1.0, 1.0])
    field = np.ones((1, 2, 2))
    with pytest.raises(ValueError, match="x_m.*finite positive spatial steps"):
        assemble_neutral_upwind_transport_coefficients(
            np.array([-1e308, 1e308]),
            vx,
            field,
            field,
        )
