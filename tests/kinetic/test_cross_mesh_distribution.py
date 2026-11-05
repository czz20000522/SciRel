"""Direct contract tests for ``scirel.kinetic.interp_distribution_across_mesh``
(the N5 H<->H2 cross-grid distribution interpolation, saved anchor
 as recorded by the saved bundle's provenance).

The retained valid numerical assertions are checked against independent
cylindrical moments. The corrected branch is a scientific successor rather
than a replay of the defective saved AN/BN correction. Input coercions,
undefined axes and correction nonconvergence fail closed under SciRel's
declared contract.

The saved formal operator has no cache or w_new branch: it recomputes the
weight matrix every call, exactly like this stateless port.  The original
the neutral-transport formulation runtime's weight cache lifecycle lives in the source runtime, not
in the saved formal operator, so no cache-state replay is possible here.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import interp_distribution_across_mesh


def _meshes():
    vr_a = np.linspace(0.5, 2.0, 4)
    vx_a = np.linspace(-1.5, 1.5, 6)
    x_a = np.linspace(0.0, 1.0, 5)
    vr_b = np.linspace(0.4, 1.8, 5)
    vx_b = np.linspace(-1.2, 1.2, 7)
    x_b = np.linspace(0.1, 0.9, 4)
    return vr_a, vx_a, x_a, vr_b, vx_b, x_b


def _distribution(vr, vx, nx):
    vr2 = vr[:, None] ** 2 + vx[None, :] ** 2
    return np.exp(-vr2)[:, :, None] * np.ones((vr.size, vx.size, nx))


def _quadrature(vr, vx):
    """Independent cylindrical quadrature for a uniform mesh: the source's
    cell edges are [0, (vr[0]+vr[1])/2, ..., (vr[-2]+vr[-1])/2, vr[-1]+dr/2],
    so the ring areas are pi*(edges[1:]^2 - edges[:-1]^2) -- exactly nvr
    areas for nvr nodes.  Computed analytically here, NOT via the
    implementation's _make_dvr_dvx, so an error in either would surface as
    a mismatch."""
    assert np.all(np.diff(vr) > 0) and vr[0] > 0, "test-only: uniform-mesh assumption"
    dr = vr[1] - vr[0]
    edges = np.concatenate(
        (
            [0.0],
            0.5 * (vr[:-1] + vr[1:]),
            [vr[-1] + dr / 2],
        )
    )
    assert edges.size == vr.size + 1, f"edges {edges.size} != nodes+1 {vr.size + 1}"
    ring_area = np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)
    dx = vx[1] - vx[0]
    dVx = np.full(vx.size, dx)
    return ring_area, dVx


def _density(f, vr, vx, x):
    Vr2pidVr, dVx = _quadrature(vr, vx)
    return np.array([np.sum(Vr2pidVr * (f[:, :, k] @ dVx)) for k in range(f.shape[2])])


def test_output_shape_and_finiteness():
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    fb = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5, correct=1)
    assert fb.shape == (vr_b.size, vx_b.size, x_b.size)
    assert np.all(np.isfinite(fb))


def test_correct_branch_density_matches_interpolated_target():
    """With correct=1 the interpolated distribution's density on mesh_b
    (computed with the saved mesh_b quadrature) must equal the mesh_a
    density profile linearly interpolated onto the mesh_b x nodes, within
    a tight relative tolerance."""
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    na = _density(fa, vr_a, vx_a, x_a)
    na_b = np.array([np.interp(x_b[k], x_a, na) for k in range(x_b.size)])
    fb = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5, correct=1)
    nb = _density(fb, vr_b, vx_b, x_b)
    np.testing.assert_allclose(nb, na_b, rtol=1e-9, atol=0.0)


def test_correct_branch_zero_flow_for_symmetric_input():
    """The input is symmetric in vx (exp(-vr^2-vx^2)), so the corrected
    distribution's axial flow (first vx moment) must be zero on mesh_b."""
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    Vr2pidVr, dVx = _quadrature(vr_b, vx_b)
    fb = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5, correct=1)
    nb = _density(fb, vr_b, vx_b, x_b)
    for k in range(x_b.size):
        Wxb = np.sqrt(1.5) * np.sum(Vr2pidVr * (fb[:, :, k] @ (vx_b * dVx))) / nb[k]
        np.testing.assert_allclose(Wxb, 0.0, atol=1e-12)


def test_correct_zero_branch_differs_from_correct_one():
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    fb0 = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5, correct=0)
    fb1 = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5, correct=1)
    assert not np.array_equal(fb0, fb1)


def test_stateless_port_is_deterministic_across_calls():
    """The port has no cache or hidden state; repeated calls must produce
    bit-identical results.  This is a precondition for the replay test to
    be meaningful (the saved formal operator also has no cache branch, so
    both arms execute the same code path on every call)."""
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    fb1 = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5)
    fb2 = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5)
    np.testing.assert_array_equal(fb1, fb2)


def test_domain_edges_fail_closed():
    """Declared fail-closed domain: the axes need at least two nodes (the
    saved arm raises a raw IndexError on a single-node vx; this asset now
    fail-closes with a named ValueError), and both velocity-space and
    x-space overlaps are required."""
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    # single-node vx_a: the saved arm raises a raw IndexError; this asset
    # fail-closes with a named ValueError instead (declared divergence).
    with pytest.raises(ValueError, match="vx_a must have at least two nodes"):
        interp_distribution_across_mesh(
            np.ones((vr_a.size, 1, x_a.size)),
            vr_a,
            np.array([0.0]),
            x_a,
            2.0,
            vr_b,
            vx_b,
            x_b,
            1.5,
        )
    # no x overlap: rejected by the source's own exception path
    with pytest.raises(ValueError, match="within range"):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, np.array([5.0, 6.0]), 1.5
        )
    # no velocity overlap: rejected by the source's own exception path
    with pytest.raises(ValueError, match="within range"):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 2.0, np.array([5.0, 6.0, 7.0, 8.0]), vx_b, x_b, 1.5
        )
    # Tnorm NaN/inf: the exact document requires finite positive; the saved
    # arm only checks Tnorm <= 0 which passes for NaN
    with pytest.raises(ValueError, match="Tnorm_a and Tnorm_b must be positive and finite"):
        interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, float("nan"), vr_b, vx_b, x_b, 1.5)
    with pytest.raises(ValueError, match="Tnorm_a and Tnorm_b must be positive and finite"):
        interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, float("inf"), vr_b, vx_b, x_b, 1.5)


def test_disjoint_velocity_cells_are_zero_and_overlapping_cells_are_preserved():
    vr_a = np.array([0.5, 1.0, 2.0])
    vx_a = np.array([-1.5, -0.5, 0.5, 1.5])
    x_a = np.array([0.0, 1.0])
    vr_b = np.array([0.1, 0.5, 1.0, 2.0, 3.0])
    vx_b = np.array([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5])
    x_b = np.array([0.0, 1.0])
    fa = np.ones((vr_a.size, vx_a.size, x_a.size))

    fb = interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 1.0, vr_b, vx_b, x_b, 1.0, correct=0)

    np.testing.assert_array_equal(fb[4, :, :], 0.0)
    np.testing.assert_array_equal(fb[:, [0, 5], :], 0.0)
    np.testing.assert_allclose(fb[:4, 1:5, :], 1.0, rtol=0.0, atol=0.0)


def test_axis_monotonicity_and_node_count_fail_closed():
    """Pre-review regressions: the saved arm does not validate monotonicity
    of x_a/x_b/vx_a/vx_b or minimum node counts, so non-monotone axes or
    single-node axes can enter _locate/_make_dvr_dvx with undefined
    semantics or raw IndexError.  The exact document requires strictly
    increasing axes and at least two nodes per axis; this asset now
    enforces both."""
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    # non-monotone x_a
    with pytest.raises(ValueError, match="x_a must be strictly increasing"):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, np.array([0.0, 0.5, 0.3, 1.0, 1.0]), 2.0, vr_b, vx_b, x_b, 1.5
        )
    # non-monotone x_b
    with pytest.raises(ValueError, match="x_b must be strictly increasing"):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, np.array([0.9, 0.5, 0.3, 0.1]), 1.5
        )
    # non-monotone vx_a
    with pytest.raises(ValueError, match="vx_a must be strictly increasing"):
        interp_distribution_across_mesh(
            fa, vr_a, np.array([-1.5, 1.5, -0.5, 0.5, 1.0, 1.5]), x_a, 2.0, vr_b, vx_b, x_b, 1.5
        )
    # non-monotone vx_b
    with pytest.raises(ValueError, match="vx_b must be strictly increasing"):
        interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            2.0,
            vr_b,
            np.array([1.2, -1.2, -0.8, 0.0, 0.4, 0.8, 1.2]),
            x_b,
            1.5,
        )
    # single-node x_a
    with pytest.raises(ValueError, match="x_a must have at least two nodes"):
        interp_distribution_across_mesh(
            np.ones((vr_a.size, vx_a.size, 1)),
            vr_a,
            vx_a,
            np.array([0.5]),
            2.0,
            vr_b,
            vx_b,
            x_b,
            1.5,
        )
    # single-node vr_b
    with pytest.raises(ValueError, match="vr_b must have at least two nodes"):
        interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, np.array([1.0]), vx_b, x_b, 1.5)


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("fa", np.ones((4, 6, 5), dtype=bool)),
        ("vr_a", [0.5, 1.0, 1.5, "2.0"]),
        ("vx_a", np.array([-1.5, -0.9, -0.3, 0.3, 0.9, 1.5], dtype=complex)),
        ("x_b", [0.1, 0.3, 0.5, True]),
        ("Tnorm_a", "2.0"),
        ("Tnorm_b", True),
    ],
)
def test_nonreal_coercions_fail_by_parameter_name(parameter, value):
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    inputs = dict(
        fa=_distribution(vr_a, vx_a, x_a.size),
        vr_a=vr_a,
        vx_a=vx_a,
        x_a=x_a,
        Tnorm_a=2.0,
        vr_b=vr_b,
        vx_b=vx_b,
        x_b=x_b,
        Tnorm_b=1.5,
    )
    inputs[parameter] = value
    with pytest.raises(ValueError, match=parameter):
        interp_distribution_across_mesh(**inputs)


@pytest.mark.parametrize("correct", [True, 1.0, "1", 2, np.inf, [1]])
def test_correct_is_binary_integer_selector(correct):
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    with pytest.raises(ValueError, match="correct"):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5, correct=correct
        )


@pytest.mark.parametrize("do_warn", [True, 0.5, "1", np.nan, [1]])
def test_warning_threshold_must_be_an_integer_scalar_or_none(do_warn):
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    with pytest.raises(ValueError, match="do_warn"):
        interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            2.0,
            vr_b,
            vx_b,
            x_b,
            1.5,
            correct=0,
            do_warn=do_warn,
        )


def test_cylindrical_axes_need_nonnegative_radial_and_both_axial_signs():
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    with pytest.raises(ValueError, match="vr_b"):
        interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            2.0,
            np.linspace(-0.4, 1.8, vr_b.size),
            vx_b,
            x_b,
            1.5,
        )
    with pytest.raises(ValueError, match="vx_b"):
        interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            2.0,
            vr_b,
            np.linspace(0.1, 1.2, vx_b.size),
            x_b,
            1.5,
        )


@pytest.mark.parametrize("limit", [0, True, 1.0, "2", -1])
def test_iteration_limit_must_be_positive_integer(limit):
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = _distribution(vr_a, vx_a, x_a.size)
    with pytest.raises(ValueError, match="max_correction_iterations"):
        interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            2.0,
            vr_b,
            vx_b,
            x_b,
            1.5,
            max_correction_iterations=limit,
        )


def test_correction_limit_exhaustion_returns_no_partial_distribution():
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = np.exp(np.random.default_rng(0).normal(size=(vr_a.size, vx_a.size, x_a.size)))
    # The original narrow grid cannot represent the requested energy; a
    # feasible wider grid isolates bounded iteration exhaustion.
    vr_b = np.linspace(0.1, 2.8, 8)
    vx_b = np.linspace(-2.7, 2.7, 11)
    original = fa.copy()
    with pytest.raises(ValueError, match="did not converge within 1 iterations at x_b index 0"):
        interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            2.0,
            vr_b,
            vx_b,
            x_b,
            1.5,
            max_correction_iterations=1,
        )
    np.testing.assert_array_equal(fa, original)


def test_original_negative_output_witness_now_fails_as_infeasible():
    # Historical assertion of negative output is frozen with the original
    # failure receipt. It is not a physical correctness requirement.
    from scirel.kinetic.cross_mesh_distribution_interpolation import InfeasibleMomentsError

    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _meshes()
    fa = np.exp(np.random.default_rng(0).normal(size=(vr_a.size, vx_a.size, x_a.size)))
    assert np.all(fa > 0)
    with pytest.raises(InfeasibleMomentsError, match="convex hull"):
        interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, x_b, 1.5)
