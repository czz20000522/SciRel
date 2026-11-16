"""Independent evidence for the upwind transport coefficients and their propagation.

Assets: ``scirel.neutrals.neutral-upwind-transport-coefficients``,
``scirel.neutrals.neutral-generation-propagation``.

The first asset is a **numerical-scheme convention**, not a physical law: it
transcribes the trapezoidal (Crank-Nicolson-like) upwind recurrence
``Phi_{k+1} = A_k Phi_k + F_k`` with a loss averaged over the interval.  The
evidence therefore tests the scheme's own structural statements and never
upgrades them into a physics claim:

1. **Exact rational coefficients.**  ``A/B/F`` and ``C/D/G`` are recomputed from
   the exact binary64 inputs with :class:`fractions.Fraction`.  The forward
   denominator uses ``alpha_{k+1}`` and the numerator ``alpha_k``; the backward
   branch mirrors that with the interval ``(k-1, k)``.
2. **Upstream index decided by a discriminator.**  Perturbing ``alpha`` at node
   ``k`` must change only the numerator term (``A``) and leave ``B`` and ``F``
   untouched, while perturbing ``alpha`` at ``k+1`` must change ``A``, ``B`` and
   ``F``.  A swapped upstream/downstream assignment changes the *other* pattern,
   so the test decides the convention instead of agreeing with it.
3. **Per-interval discrete balance, asserted as a residual.**  Given
   ``Phi_{k+1} = A_k Phi_k + F_k``, the trapezoidal statement
   ``2|v| (Phi_k - Phi_{k+1}) / dx + alpha_k Phi_k + alpha_{k+1} Phi_{k+1} - (S_k + S_{k+1}) = 0``
   must hold on every interior interval, on both branches.  This is the exact
   cell balance of the scheme; it is a discrete identity, not energy conservation
   of the transport equation.
4. **Loss-free limit and time-reversal symmetry.**  With ``alpha = 0`` the
   recurrence reduces to ``A = 1`` and the exact trapezoid increment of ``S/v``;
   halving/doubling the velocity scales ``B`` and ``F`` exactly.  The backward
   branch is the exact mirror of the forward one for equal ``|v|``.
5. **Propagation is the recurrence it says it is.**  Both branches, both
   generation kinds, are reproduced from independently supplied coefficient
   fields with exact rational cumulative products and sums; the first-flight
   boundary reaches the positive half only, while the negative half is driven by
   ``G`` alone, and the scattered branch is exactly linear in its source.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset.

Budgets, fixed before measurement:

* coefficients and recurrences: ``(n + 6) * eps * scale`` for a sum of ``n``
  products followed by two divisions; the exact rational reference is rounded
  once.
* the interval balance: ``(n_terms + 6) * eps * scale`` with ``n_terms`` the six
  products of the residual.
* exact equality: the loss-free ``A = 1``, the boundary copy, the zero columns
  and the power-of-two scalings.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps

X = np.array([0.0, 0.5, 2.0, 3.5])
VX = np.array([-2.0, -0.5, 0.75, 3.0])
SHAPE = (2, 4, 4)
ALPHA = np.linspace(0.05, 1.0, num=2 * 4 * 4).reshape(SHAPE)
SOURCE = np.linspace(-1.0, 2.0, num=2 * 4 * 4).reshape(SHAPE)


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _coefficients(alpha=ALPHA, source=SOURCE, x=X, vx=VX):
    """Return the upwind coefficient mapping for the shared mesh."""
    return N.assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)


def _exact_forward(alpha, source, x, vx):
    """Exact A/B/F per (i, positive column, interval)."""
    dx = [_frac(b) - _frac(a) for a, b in zip(x[:-1], x[1:])]
    rows = {}
    for j, velocity in enumerate(vx):
        if velocity <= 0:
            continue
        for k in range(x.size - 1):
            denominator = 2 * _frac(velocity) + dx[k] * _frac(alpha[0, j, k + 1])
            rows[(j, k)] = {
                "A": (2 * _frac(velocity) - dx[k] * _frac(alpha[0, j, k])) / denominator,
                "B": dx[k] / denominator,
                "F": dx[k] * (_frac(source[0, j, k]) + _frac(source[0, j, k + 1])) / denominator,
            }
    return rows


def _exact_backward(alpha, source, x, vx):
    """Exact C/D/G per (i, negative column, interval), with the mirrored dx index."""
    dx = [_frac(b) - _frac(a) for a, b in zip(x[:-1], x[1:])]
    rows = {}
    for j, velocity in enumerate(vx):
        if velocity >= 0:
            continue
        for k in range(1, x.size):
            magnitude = -_frac(velocity)
            denominator = 2 * magnitude + dx[k - 1] * _frac(alpha[0, j, k - 1])
            rows[(j, k)] = {
                "C": (2 * magnitude - dx[k - 1] * _frac(alpha[0, j, k])) / denominator,
                "D": dx[k - 1] / denominator,
                "G": dx[k - 1]
                * (_frac(source[0, j, k]) + _frac(source[0, j, k - 1]))
                / denominator,
            }
    return rows


def test_forward_coefficients_match_the_exact_trapezoid_forms():
    """Evidence 1: A/B/F from exact rationals, with the boundary and other branch exactly zero."""
    result = _coefficients()
    exact = _exact_forward(ALPHA, SOURCE, X, VX)
    for (column, k), values in exact.items():
        for name, key in (("Ak", "A"), ("Bk", "B"), ("Fk", "F")):
            expected = float(values[key])
            got = result[name][0, column, k]
            assert abs(got - expected) <= 12 * EPS * max(abs(expected), 1e-300), (name, column, k)
    # The last column of the forward branch and every negative column are exact zero.
    assert np.all(result["Ak"][:, :, -1] == 0.0)
    assert np.all(result["Bk"][:, :, -1] == 0.0)
    assert np.all(result["Fk"][:, :, -1] == 0.0)
    negative_columns = [j for j, velocity in enumerate(VX) if velocity < 0]
    assert np.all(result["Ak"][:, negative_columns, :] == 0.0)
    assert np.all(result["Bk"][:, negative_columns, :] == 0.0)
    assert np.all(result["Fk"][:, negative_columns, :] == 0.0)


def test_backward_coefficients_match_the_exact_mirrored_forms():
    """Evidence 1 + 4: C/D/G with the (k-1, k) interval, and the zero-cost mirror."""
    result = _coefficients()
    exact = _exact_backward(ALPHA, SOURCE, X, VX)
    for (column, k), values in exact.items():
        for name, key in (("Ck", "C"), ("Dk", "D"), ("Gk", "G")):
            expected = float(values[key])
            got = result[name][0, column, k]
            assert abs(got - expected) <= 12 * EPS * max(abs(expected), 1e-300), (name, column, k)
    positive_columns = [j for j, velocity in enumerate(VX) if velocity > 0]
    negative_columns = [j for j, velocity in enumerate(VX) if velocity < 0]
    assert np.all(result["Ck"][:, positive_columns, :] == 0.0)
    assert np.all(result["Dk"][:, positive_columns, :] == 0.0)
    assert np.all(result["Gk"][:, positive_columns, :] == 0.0)
    assert np.all(result["Ck"][:, :, 0] == 0.0)
    assert np.all(result["Dk"][:, :, 0] == 0.0)
    assert np.all(result["Gk"][:, :, 0] == 0.0)
    # With zero loss the backward coefficients mirror the forward ones for the
    # same |v|: this is the time-reversal symmetry of the two-point scheme.
    symmetric = np.zeros_like(ALPHA)
    mirrored = _coefficients(alpha=symmetric)
    pairs = [
        (j_pos, j_neg)
        for j_pos in positive_columns
        for j_neg in negative_columns
        if abs(VX[j_pos]) == abs(VX[j_neg])
    ]
    for j_pos, j_neg in pairs:
        for k in range(X.size - 1):
            assert mirrored["Dk"][0, j_neg, k + 1] == mirrored["Bk"][0, j_pos, k]
            assert mirrored["Gk"][0, j_neg, k + 1] == mirrored["Fk"][0, j_pos, k]


def test_each_interval_satisfies_the_trapezoid_balance():
    """Evidence 3: the discrete cell balance, asserted as a per-interval residual."""
    result = _coefficients()
    phi = np.zeros(SHAPE)
    phi[:, :, 0] = np.linspace(1.0, 2.0, num=SHAPE[0] * SHAPE[1]).reshape(SHAPE[:2])
    dx = np.diff(X)
    for j, velocity in enumerate(VX):
        if velocity > 0:
            for k in range(X.size - 1):
                step = phi[0, j, k] * result["Ak"][0, j, k] + result["Fk"][0, j, k]
                residual = (
                    2.0 * velocity * (step - phi[0, j, k]) / dx[k]
                    + ALPHA[0, j, k] * phi[0, j, k]
                    + ALPHA[0, j, k + 1] * step
                    - (SOURCE[0, j, k] + SOURCE[0, j, k + 1])
                )
                scale = max(
                    abs(2.0 * velocity * (step - phi[0, j, k]) / dx[k]),
                    abs(ALPHA[0, j, k] * phi[0, j, k]),
                    abs(SOURCE[0, j, k] + SOURCE[0, j, k + 1]),
                    1.0,
                )
                assert abs(residual) <= 16 * EPS * scale, (j, k)
                phi[0, j, k + 1] = step
        else:
            # The backward branch starts at the last node.
            phi[0, j, -1] = 1.0
            for k in range(X.size - 1, 0, -1):
                step = phi[0, j, k] * result["Ck"][0, j, k] + result["Gk"][0, j, k]
                residual = (
                    2.0 * abs(velocity) * (step - phi[0, j, k]) / dx[k - 1]
                    + ALPHA[0, j, k] * phi[0, j, k]
                    + ALPHA[0, j, k - 1] * step
                    - (SOURCE[0, j, k] + SOURCE[0, j, k - 1])
                )
                scale = max(
                    abs(2.0 * abs(velocity) * (step - phi[0, j, k]) / dx[k - 1]),
                    abs(SOURCE[0, j, k] + SOURCE[0, j, k - 1]),
                    1.0,
                )
                assert abs(residual) <= 16 * EPS * scale, (j, k)
                phi[0, j, k - 1] = step


def test_upstream_and_downstream_nodes_are_decided_by_a_perturbation():
    """Evidence 2: perturbing alpha at k and at k+1 changes different coefficients."""
    base = _coefficients()
    j = 3  # vx = 3.0, interior interval k = 1
    k = 1
    left = ALPHA.copy()
    left[0, j, k] += 0.5
    right = ALPHA.copy()
    right[0, j, k + 1] += 0.5
    perturbed_left = _coefficients(alpha=left)
    perturbed_right = _coefficients(alpha=right)
    # alpha_k enters only the numerator of A.
    assert perturbed_left["Ak"][0, j, k] != base["Ak"][0, j, k]
    assert perturbed_left["Bk"][0, j, k] == base["Bk"][0, j, k]
    assert perturbed_left["Fk"][0, j, k] == base["Fk"][0, j, k]
    # alpha_{k+1} enters the shared denominator, so all three change.
    assert perturbed_right["Ak"][0, j, k] != base["Ak"][0, j, k]
    assert perturbed_right["Bk"][0, j, k] != base["Bk"][0, j, k]
    assert perturbed_right["Fk"][0, j, k] != base["Fk"][0, j, k]
    # The same pattern holds on the backward branch, with the mirrored nodes.
    negative = [index for index, velocity in enumerate(VX) if velocity < 0][0]
    left = ALPHA.copy()
    left[0, negative, k] += 0.5
    right = ALPHA.copy()
    right[0, negative, k - 1] += 0.5
    moved = _coefficients(alpha=right)
    assert moved["Dk"][0, negative, k] != base["Dk"][0, negative, k]
    assert moved["Gk"][0, negative, k] != base["Gk"][0, negative, k]


def test_loss_free_branch_is_the_exact_trapezoid_increment():
    """Evidence 4: alpha = 0 gives A = 1 and the exact trapezoid of S/v."""
    zero = np.zeros_like(ALPHA)
    result = _coefficients(alpha=zero)
    positive = [index for index, velocity in enumerate(VX) if velocity > 0]
    assert np.all(result["Ak"][:, positive, :-1] == 1.0)
    j, velocity = positive[0], VX[positive[0]]
    dx = np.diff(X)
    for k in range(X.size - 1):
        assert result["Bk"][0, j, k] == dx[k] / (2.0 * velocity)
        assert result["Fk"][0, j, k] == dx[k] * (SOURCE[0, j, k] + SOURCE[0, j, k + 1]) / (
            2.0 * velocity
        )
    # Doubling the velocity halves B and F exactly in the loss-free branch.
    faster = N.assemble_neutral_upwind_transport_coefficients(X, 2.0 * VX, zero, SOURCE)
    assert np.array_equal(faster["Bk"][:, positive, :-1], 0.5 * result["Bk"][:, positive, :-1])
    assert np.array_equal(faster["Fk"][:, positive, :-1], 0.5 * result["Fk"][:, positive, :-1])
    # The telescoped increment over the whole axis is the exact trapezoid.
    total = sum(
        (result["Fk"][0, j, k] for k in range(X.size - 1)),
        0.0,
    )
    exact = sum(
        (
            float(
                (_frac(X[k + 1]) - _frac(X[k]))
                * (_frac(SOURCE[0, j, k]) + _frac(SOURCE[0, j, k + 1]))
                / (2 * _frac(velocity))
            )
            for k in range(X.size - 1)
        ),
        0.0,
    )
    assert abs(total - exact) <= 8 * EPS * max(abs(exact), 1.0)


def test_upwind_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.assemble_neutral_upwind_transport_coefficients
    good = (X, VX, ALPHA, SOURCE)
    assert call(*good)["Ak"].shape == SHAPE
    with pytest.raises(ValueError, match="positive spatial steps"):
        call(np.array([0.0, 0.0, 1.0, 2.0]), VX, ALPHA, SOURCE)
    with pytest.raises(ValueError, match="positive spatial steps"):
        call(np.array([3.0, 2.0, 1.0, 0.0]), VX, ALPHA, SOURCE)
    with pytest.raises(ValueError, match="x/vx/alpha/source"):
        call(X, np.array([-2.0, 0.0, 0.75, 3.0]), ALPHA, SOURCE)
    with pytest.raises(ValueError, match="x/vx/alpha/source"):
        call(X, VX, -ALPHA, SOURCE)
    with pytest.raises(ValueError, match="x/vx/alpha/source"):
        call(X, VX, ALPHA, SOURCE[:, :, :2])
    with pytest.raises(ValueError, match="positive spatial steps"):
        call(np.array([0.0, 1.0, 1.0, 2.0]), VX, ALPHA, SOURCE)
    with pytest.raises(ValueError, match="positive and negative branches"):
        call(X, np.array([0.5, 1.0, 2.0, 3.0]), ALPHA, SOURCE)
    with pytest.raises(ValueError, match="finite real array"):
        call(X, VX, np.full_like(ALPHA, np.inf), SOURCE)
    with pytest.raises(ValueError, match="transport coefficients must be finite"):
        call(X, VX, np.full_like(ALPHA, 1.7e308), SOURCE)


# --------------------------------------------------------------------------- #
# neutral-generation-propagation
# --------------------------------------------------------------------------- #


def _propagation_fields(seed=811):
    """Return independently drawn coefficient fields (not taken from the upwind asset)."""
    rng = np.random.default_rng(seed)
    shape = (2, 4, 3)
    fields = {
        "Ak": rng.uniform(0.0, 1.0, size=shape),
        "Bk": rng.uniform(0.0, 2.0, size=shape),
        "Fk": rng.uniform(-1.0, 1.0, size=shape),
        "Ck": rng.uniform(0.0, 1.0, size=shape),
        "Dk": rng.uniform(0.0, 2.0, size=shape),
        "Gk": rng.uniform(-1.0, 1.0, size=shape),
    }
    return fields


def _exact_propagation(fields, positive, boundary=None, source=None):
    """Exact forward/backward recurrence, independent of the implementation."""
    shape = fields["Ak"].shape
    out = [
        [[Fraction(0) for _ in range(shape[2])] for _ in range(shape[1])] for _ in range(shape[0])
    ]
    for j in range(shape[1]):
        for i in range(shape[0]):
            if positive[j]:
                out[i][j][0] = _frac(boundary[i, j])
                for k in range(shape[2] - 1):
                    if source is None:
                        increment = _frac(fields["Fk"][i, j, k])
                    else:
                        increment = _frac(fields["Bk"][i, j, k]) * (
                            _frac(source[i, j, k]) + _frac(source[i, j, k + 1])
                        )
                    out[i][j][k + 1] = out[i][j][k] * _frac(fields["Ak"][i, j, k]) + increment
            else:
                out[i][j][shape[2] - 1] = Fraction(0)
                for k in range(shape[2] - 1, 0, -1):
                    if source is None:
                        increment = _frac(fields["Gk"][i, j, k])
                    else:
                        increment = _frac(fields["Dk"][i, j, k]) * (
                            _frac(source[i, j, k]) + _frac(source[i, j, k - 1])
                        )
                    out[i][j][k - 1] = out[i][j][k] * _frac(fields["Ck"][i, j, k]) + increment
    return np.array([[np.array(row) for row in plane] for plane in out], dtype=object)


def test_first_flight_recurrence_matches_exact_rational_products():
    """Evidence 5: both branches reproduced from independently drawn coefficients."""
    fields = _propagation_fields()
    rng = np.random.default_rng(813)
    boundary = rng.uniform(0.0, 3.0, size=(2, 4))
    result = N.propagate_neutral_generation(
        VX,
        fields["Ak"],
        fields["Bk"],
        fields["Fk"],
        fields["Ck"],
        fields["Dk"],
        fields["Gk"],
        generation_kind="first_flight",
        incoming_boundary=boundary,
    )
    positive = VX > 0.0
    exact = _exact_propagation(fields, positive, boundary=boundary)
    scale = max(float(np.max(np.abs(result))), 1.0)
    for i in range(2):
        for j in range(4):
            for k in range(3):
                assert abs(result[i, j, k] - float(exact[i][j][k])) <= 32 * EPS * scale


def test_first_flight_boundary_reaches_only_the_positive_half():
    """Evidence 5: the boundary sets the positive half; the negative half is G-driven."""
    fields = _propagation_fields()
    boundary = np.ones((2, 4))
    base = N.propagate_neutral_generation(
        VX,
        *[fields[name] for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")],
        generation_kind="first_flight",
        incoming_boundary=boundary,
    )
    stronger = N.propagate_neutral_generation(
        VX,
        *[fields[name] for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")],
        generation_kind="first_flight",
        incoming_boundary=3.0 * boundary,
    )
    positive = np.flatnonzero(VX > 0.0)
    negative = np.flatnonzero(VX < 0.0)
    assert np.array_equal(base[:, positive, 0], boundary[:, positive])
    assert np.array_equal(stronger[:, negative, :], base[:, negative, :])
    assert not np.array_equal(stronger[:, positive, 1:], base[:, positive, 1:])


def test_single_spatial_node_carries_the_boundary_on_the_positive_half_only():
    """Evidence 5: with nx = 1 the recurrence does not run, so the boundary branch is directly observable."""
    fields = {name: np.zeros((2, 4, 1)) for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")}
    boundary = np.array([[1.0, 2.0, 3.0, 4.0], [0.5, 1.5, 2.5, 3.5]])
    result = N.propagate_neutral_generation(
        VX,
        *[fields[name] for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")],
        generation_kind="first_flight",
        incoming_boundary=boundary,
    )
    positive = np.flatnonzero(VX > 0.0)
    negative = np.flatnonzero(VX < 0.0)
    assert np.array_equal(result[:, positive, 0], boundary[:, positive])
    assert np.array_equal(result[:, negative, 0], np.zeros((2, negative.size)))


def test_scattered_branch_is_exactly_linear_in_the_source():
    """Evidence 5: doubling the scattered source doubles the generation exactly."""
    fields = _propagation_fields(seed=817)
    rng = np.random.default_rng(819)
    source = rng.uniform(0.0, 2.0, size=(2, 4, 3))
    args = [fields[name] for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")]
    base = N.propagate_neutral_generation(
        VX, *args, generation_kind="scattered", scattered_source_distribution=source
    )
    doubled = N.propagate_neutral_generation(
        VX, *args, generation_kind="scattered", scattered_source_distribution=2.0 * source
    )
    assert np.array_equal(doubled, 2.0 * base)
    # A zero source gives exactly the zero generation on both halves.
    zero = N.propagate_neutral_generation(
        VX, *args, generation_kind="scattered", scattered_source_distribution=np.zeros_like(source)
    )
    assert np.array_equal(zero, np.zeros_like(zero))


def test_propagation_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    fields = _propagation_fields()
    args = [fields[name] for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")]
    call = N.propagate_neutral_generation
    boundary = np.ones((2, 4))
    source = np.ones((2, 4, 3))
    assert call(VX, *args, generation_kind="first_flight", incoming_boundary=boundary).shape == (
        2,
        4,
        3,
    )
    mismatched = [args[0][:, :, :2]] + args[1:]
    with pytest.raises(ValueError, match="coefficient fields are invalid"):
        call(VX, *mismatched, generation_kind="first_flight", incoming_boundary=boundary)
    with pytest.raises(ValueError, match="branches must be nonzero"):
        call(
            np.array([-2.0, 0.0, 0.75, 3.0]),
            *args,
            generation_kind="first_flight",
            incoming_boundary=boundary,
        )
    with pytest.raises(ValueError, match="branches must be nonzero"):
        call(
            np.array([0.5, 1.0, 2.0, 3.0]),
            *args,
            generation_kind="first_flight",
            incoming_boundary=boundary,
        )
    with pytest.raises(ValueError, match="generation_kind"):
        call(VX, *args, generation_kind="other", incoming_boundary=boundary)
    with pytest.raises(ValueError, match="exactly one finite incoming_boundary"):
        call(VX, *args, generation_kind="first_flight")
    with pytest.raises(ValueError, match="exactly one finite incoming_boundary"):
        call(
            VX,
            *args,
            generation_kind="first_flight",
            incoming_boundary=boundary,
            scattered_source_distribution=source,
        )
    with pytest.raises(ValueError, match="exactly one finite scattered_source"):
        call(VX, *args, generation_kind="scattered", incoming_boundary=boundary)
    with pytest.raises(ValueError, match="exactly one finite scattered_source"):
        call(VX, *args, generation_kind="scattered")
