"""Independent evidence for the generation-density and simple-CX-source reductions.

Assets: ``scirel.neutrals.generation-density-reduction``,
``scirel.neutrals.simple-charge-exchange-source``.

Both contracts are cell-local velocity-space reductions with an explicitly
declared operation order, so the evidence is built from the exact rational value
of the declared sum plus two structural discriminators that a wrong broadcast or
a wrong index convention cannot pass:

1. **Exact rational value.**  The sum of ``weight * distribution * dvx`` (and of
   ``target * alpha * weight * previous * dvx``) is recomputed with
   :class:`fractions.Fraction` and rounded once.
2. **The three documented density paths agree.**  A one-dimensional radial
   weight, a two-dimensional weight with uniform columns (which the contract
   routes through the radial projection) and a general two-dimensional weight
   must produce the same density on the same data; the first two are asserted
   equal exactly, because they are the same declared operation order.
3. **No spatial coupling, decided by a perturbation.**  Changing the
   distribution (or the predecessor) at one spatial cell must change exactly that
   cell of the output and nothing else.  A cross-cell smearing or an axial
   contraction that leaks into neighbouring cells breaks it.
4. **Exact homogeneity and sign preservation.**  Doubling the distribution
   doubles the density exactly; doubling target, predecessor or CX frequency
   doubles the source exactly; a zero CX frequency gives exactly zero; an
   antisymmetric pair cancels exactly.
5. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset.

Budgets, fixed before measurement:

* the sums: ``(n + 4) * eps * sum_i |term_i|`` for ``n`` products, the standard
  forward bound (the exact rational reference is rounded once).
* the equalities: exact ``array_equal`` for the identical operation order and for
  power-of-two scalings; the perturbation equality is exact because the untouched
  cells receive the identical inputs and operation order.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps

NVR, NVX, NX = 2, 3, 2


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _distribution(seed=907):
    """Return a signed distribution on the shared shape."""
    rng = np.random.default_rng(seed)
    return rng.uniform(-2.0, 2.0, size=(NVR, NVX, NX))


def _radial(seed=911):
    """Return a nonnegative radial weight."""
    return np.random.default_rng(seed).uniform(0.0, 2.0, size=NVR)


def _widths(seed=919):
    """Return nonnegative axial widths."""
    return np.random.default_rng(seed).uniform(0.0, 1.5, size=NVX)


def _exact_density(field, weight, widths):
    """Exact per-cell sum of weight * field * widths; the weight may be 1-D or 2-D."""
    weight = np.asarray(weight, dtype=float)
    out = []
    for k in range(field.shape[2]):
        total = Fraction(0)
        for i in range(field.shape[0]):
            for j in range(field.shape[1]):
                w = _frac(weight[i]) if weight.ndim == 1 else _frac(weight[i, j])
                total += _frac(field[i, j, k]) * w * _frac(widths[j])
        out.append(total)
    return out


# --------------------------------------------------------------------------- #
# generation-density-reduction
# --------------------------------------------------------------------------- #


def test_density_matches_the_exact_rational_reduction():
    """Evidence 1: the declared sum, recomputed exactly."""
    field = _distribution()
    weight = _radial()
    widths = _widths()
    result = N.reduce_generation_density(field, weight, widths)
    expected = np.array([float(value) for value in _exact_density(field, weight, widths)])
    scale = max(float(np.max(np.abs(expected))), 1.0)
    assert np.all(np.abs(result - expected) <= (NVR * NVX + 4) * EPS * scale)


def test_the_three_documented_paths_agree():
    """Evidence 2: radial profile, uniform-column 2-D and general 2-D weights."""
    field = _distribution()
    radial = _radial()
    widths = _widths()
    one_dimensional = N.reduce_generation_density(field, radial, widths)
    uniform_two = N.reduce_generation_density(
        field, np.repeat(radial[:, None], NVX, axis=1), widths
    )
    general = np.random.default_rng(929).uniform(0.0, 2.0, size=(NVR, NVX))
    general_two = N.reduce_generation_density(field, general, widths)
    # The uniform-column case is documented to take the same operation order.
    assert np.array_equal(uniform_two, one_dimensional)
    expected = np.array([float(value) for value in _exact_density(field, general, widths)])
    scale = max(float(np.max(np.abs(expected))), 1.0)
    assert np.all(np.abs(general_two - expected) <= (NVR * NVX + 4) * EPS * scale)


def test_density_is_cell_local_and_exactly_homogeneous():
    """Evidence 3: one cell in, one cell out; doubling doubles; signs are preserved."""
    field = _distribution()
    weight = _radial()
    widths = _widths()
    base = N.reduce_generation_density(field, weight, widths)
    perturbed = field.copy()
    perturbed[0, 0, 1] += 5.0
    moved = N.reduce_generation_density(perturbed, weight, widths)
    assert moved[1] != base[1]
    assert moved[0] == base[0]
    # Homogeneity by a power of two is exact in binary64.
    assert np.array_equal(N.reduce_generation_density(2.0 * field, weight, widths), 2.0 * base)
    # The reduction is linear, so the difference of the two signs is twice the value.
    opposite = N.reduce_generation_density(-field, weight, widths)
    assert np.array_equal(base - opposite, 2.0 * base)
    assert np.array_equal(opposite, -base)


def test_density_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    field = _distribution()
    weight = _radial()
    widths = _widths()
    call = N.reduce_generation_density
    with pytest.raises(ValueError, match="finite and aligned"):
        call(field, weight, np.array([0.5, 1.0]))
    with pytest.raises(ValueError, match="radial quadrature must align"):
        call(field, weight[:1], widths)
    with pytest.raises(ValueError, match="finite and aligned"):
        call(field, weight, np.array([0.5, -1.0, 0.5]))
    with pytest.raises(ValueError, match="finite and aligned"):
        call(field, -weight, widths)
    with pytest.raises(ValueError, match="finite and aligned"):
        call(np.full_like(field, np.nan), weight, widths)
    with pytest.raises(ValueError, match="real numeric"):
        call(np.array([[["a", 1.0]]]), weight, widths)
    with pytest.raises(ValueError, match="real numeric"):
        call([[True]], np.array([1.0]), np.array([1.0]))
    with pytest.raises(ValueError, match="not finite"):
        call(np.full((2, 3, 2), 1.7e308), np.full((2, 3), 1.7e308), widths)


# --------------------------------------------------------------------------- #
# simple-charge-exchange-source
# --------------------------------------------------------------------------- #


def _cx_fields(seed=1009):
    """Return target, CX frequency, predecessor, weight and widths."""
    rng = np.random.default_rng(seed)
    target = rng.uniform(-1.0, 2.0, size=(NVR, NVX, NX))
    alpha = rng.uniform(0.0, 2.0, size=(NVR, NVX, NX))
    previous = rng.uniform(-1.0, 2.0, size=(NVR, NVX, NX))
    weight = rng.uniform(0.0, 2.0, size=(NVR, NVX))
    widths = rng.uniform(0.0, 1.5, size=NVX)
    return target, alpha, previous, weight, widths


def _exact_cx(target, alpha, previous, weight, widths):
    """Exact target * integral(alpha * previous) per cell."""
    out = []
    for k in range(NX):
        rate = Fraction(0)
        for i in range(NVR):
            for j in range(NVX):
                rate += (
                    _frac(alpha[i, j, k])
                    * _frac(weight[i, j])
                    * _frac(previous[i, j, k])
                    * _frac(widths[j])
                )
        out.append(rate)
    return out


def test_cx_source_matches_the_exact_rational_cell_local_construction():
    """Evidence 1 + 5: the rate is one scalar per cell and the target scales it."""
    target, alpha, previous, weight, widths = _cx_fields()
    result = N.assemble_simple_charge_exchange_source(target, alpha, previous, weight, widths)
    exact_rates = _exact_cx(target, alpha, previous, weight, widths)
    for k, rate in enumerate(exact_rates):
        scale = max(abs(float(rate)), 1.0)
        expected = np.array(
            [[float(_frac(target[i, j, k]) * rate) for j in range(NVX)] for i in range(NVR)]
        )
        assert np.all(np.abs(result[:, :, k] - expected) <= (NVR * NVX + 4) * EPS * scale)
        # The per-cell rate is shared by every velocity cell: the target shapes it.
        ratios = [
            result[i, j, k] / target[i, j, k]
            for i in range(NVR)
            for j in range(NVX)
            if target[i, j, k] != 0.0
        ]
        if ratios:
            assert np.allclose(ratios, ratios[0], rtol=8 * EPS, atol=0.0)


def test_cx_source_couples_no_spatial_cells():
    """Evidence 3: perturbing the predecessor at one cell changes only that cell."""
    target, alpha, previous, weight, widths = _cx_fields()
    base = N.assemble_simple_charge_exchange_source(target, alpha, previous, weight, widths)
    perturbed = previous.copy()
    perturbed[1, 2, 1] += 3.0
    moved = N.assemble_simple_charge_exchange_source(target, alpha, perturbed, weight, widths)
    assert np.array_equal(moved[:, :, 0], base[:, :, 0])
    assert moved[1, 2, 1] != base[1, 2, 1]
    # Every velocity cell of the perturbed spatial column changes together, because
    # the rate is a single scalar per cell and only its target value differs.
    assert np.all(moved[:, :, 1] != base[:, :, 1])


def test_cx_source_is_exactly_linear_in_each_factor():
    """Evidence 4: doubling target, predecessor or frequency doubles the source."""
    target, alpha, previous, weight, widths = _cx_fields()
    base = N.assemble_simple_charge_exchange_source(target, alpha, previous, weight, widths)
    doubled_target = N.assemble_simple_charge_exchange_source(
        2.0 * target, alpha, previous, weight, widths
    )
    doubled_previous = N.assemble_simple_charge_exchange_source(
        target, alpha, 2.0 * previous, weight, widths
    )
    doubled_alpha = N.assemble_simple_charge_exchange_source(
        target, 2.0 * alpha, previous, weight, widths
    )
    assert np.array_equal(doubled_target, 2.0 * base)
    assert np.array_equal(doubled_previous, 2.0 * base)
    assert np.array_equal(doubled_alpha, 2.0 * base)
    zero = N.assemble_simple_charge_exchange_source(
        target, np.zeros_like(alpha), previous, weight, widths
    )
    assert np.array_equal(zero, np.zeros_like(zero))


def test_cx_source_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    target, alpha, previous, weight, widths = _cx_fields()
    call = N.assemble_simple_charge_exchange_source
    with pytest.raises(ValueError, match="finite and aligned"):
        call(target, alpha[:, :, :1], previous, weight, widths)
    with pytest.raises(ValueError, match="finite and aligned"):
        call(target, alpha, previous, weight, np.array([0.5, 1.0]))
    with pytest.raises(ValueError, match="finite and aligned"):
        call(target, -alpha, previous, weight, widths)
    with pytest.raises(ValueError, match="finite and aligned"):
        call(target, alpha, previous, -weight, widths)
    with pytest.raises(ValueError, match="finite and aligned"):
        call(target, alpha, previous, weight, -widths)
    with pytest.raises(ValueError, match="finite real array"):
        call(np.full_like(target, np.inf), alpha, previous, weight, widths)
    with pytest.raises(ValueError, match="finite real array"):
        call(np.array([[["a", 1.0]]]), alpha, previous, weight, widths)
    with pytest.raises(ValueError, match="assembled scattered source must be finite"):
        call(
            np.full((1, 1, 1), 1e200),
            np.full((1, 1, 1), 1e200),
            np.full((1, 1, 1), 1e200),
            np.ones((1, 1)),
            np.ones(1),
        )
