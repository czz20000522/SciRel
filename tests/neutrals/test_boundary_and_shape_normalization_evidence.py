"""Independent evidence for the two source normalizations.

Assets: ``scirel.neutrals.spatial-source-shape-normalization``,
``scirel.neutrals.incoming-boundary-flux-normalization``.

Both reduce to a declared quadrature and an explicit normalization statement, and
the risk is exactly the one this project has been burned by: turning a numerical
convention into a physics claim.  The evidence therefore does two things - it
recomputes the declared integral exactly, and it **decides the measure** with a
case where the rival measure gives a different answer:

1. **Trapezoid, not rectangle, decided by a discriminator.**  On a non-uniform
   grid with a linear profile the trapezoid and the left-rectangle integrals
   differ by a factor; the reported integral must equal the exact trapezoid value
   and must differ from the rectangle value by more than ``1e6 eps``.
2. **Exact rational integral and shape.**  ``integral = sum 0.5 (s_k + s_{k+1})
   (x_{k+1} - x_k)`` and ``shape = source / integral`` are recomputed with
   :class:`fractions.Fraction`; the returned unit-integral re-check is verified on
   the returned floats as well.
3. **Scale invariance of the shape.**  Doubling the source doubles the reported
   integral and leaves the shape bit-identical, because the normalization is a
   ratio of two exactly scaled quantities.
4. **Flux budget on the actual returned cells.**  The incoming-boundary flux is
   recomputed exactly from the returned floats and must meet the contract's own
   ``64/2**52`` relative budget with zero absolute allowance - the declared
   acceptance criterion, not a fitted tolerance.  The initial flux and the scale
   are separately checked against their exact rational values.
5. **Declared branches.**  A negative target has the same scale and boundary as
   the positive one; a zero target returns an exactly zero boundary and scale
   while still reporting the positive initial flux; the nonpositive axial half is
   exactly zero; a tiny-in-volume case exercises the exact arithmetic path that
   the bounded float interval cannot certify.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset.

Budgets, fixed before measurement:

* exact rational integrals: ``8 * eps`` relative after one rounding.
* the incoming-boundary flux: the contract's ``64 / 2**52`` relative budget with
  zero absolute allowance (its own declared criterion).
* exact equalities: the bit-identical shape under a factor-of-two source, the
  exactly zero half, the exactly zero target branch, and the equality of the two
  target signs.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps
FLUX_RTOL = Fraction(64, 2**52)


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _trapezoid(values, coordinates):
    """Exact rational trapezoid integral."""
    return sum(
        (
            _frac(values[k + 1] + values[k])
            / 2
            * (_frac(coordinates[k + 1]) - _frac(coordinates[k]))
            for k in range(len(values) - 1)
        ),
        Fraction(0),
    )


# --------------------------------------------------------------------------- #
# spatial-source-shape-normalization
# --------------------------------------------------------------------------- #

X = np.array([0.0, 1.0, 3.0])
SOURCE = np.array([0.0, 1.0, 3.0])  # linear in x


def test_the_measure_is_the_trapezoid_not_the_left_rectangle():
    """Evidence 1: the reported integral agrees with the trapezoid and rejects the rival."""
    result = N.normalize_spatial_source_shape(SOURCE, X)
    exact_trapezoid = _trapezoid(SOURCE, X)
    left_rectangle = sum(
        (_frac(SOURCE[k]) * (_frac(X[k + 1]) - _frac(X[k])) for k in range(len(X) - 1)),
        Fraction(0),
    )
    assert float(exact_trapezoid) == 4.5
    assert float(left_rectangle) == 2.0
    assert abs(result["integral_source"] - float(exact_trapezoid)) <= 8 * EPS * 4.5
    # The two measures are far apart, so the assertion above decides between them.
    assert abs(float(exact_trapezoid) - float(left_rectangle)) > 1e6 * EPS * 4.5


def test_shape_matches_the_exact_rational_normalization():
    """Evidence 2: shape = source / integral, and the returned unit integral."""
    result = N.normalize_spatial_source_shape(SOURCE, X)
    exact_integral = _trapezoid(SOURCE, X)
    expected = np.array([float(_frac(value) / exact_integral) for value in SOURCE])
    assert np.all(np.abs(result["shape_m_inv"] - expected) <= 16 * EPS * float(np.max(expected)))
    # The declared re-check, recomputed from the returned floats.
    assert abs(float(_trapezoid(result["shape_m_inv"], X)) - 1.0) <= 1e-12


def test_doubling_the_source_keeps_the_shape_bit_identical():
    """Evidence 3: the normalization is invariant under an exact source scaling."""
    base = N.normalize_spatial_source_shape(SOURCE, X)
    doubled = N.normalize_spatial_source_shape(2.0 * SOURCE, X)
    assert np.array_equal(doubled["shape_m_inv"], base["shape_m_inv"])
    assert doubled["integral_source"] == 2.0 * base["integral_source"]


def test_shape_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.normalize_spatial_source_shape
    with pytest.raises(ValueError, match="positive spatial integral"):
        call(np.zeros(3), X)
    with pytest.raises(ValueError, match="finite one-dimensional profiles"):
        call(np.array([1.0, -1.0, 1.0]), X)
    with pytest.raises(ValueError, match="finite one-dimensional profiles"):
        call(SOURCE, np.array([0.0, 1.0, 1.0]))
    with pytest.raises(ValueError, match="finite one-dimensional profiles"):
        call(SOURCE, np.array([0.0, 1.0]))
    with pytest.raises(ValueError, match="finite one-dimensional profiles"):
        call(SOURCE, np.array([0.0, np.nan, 3.0]))
    with pytest.raises(ValueError, match="real numeric"):
        call(np.array([0.0, "a", 3.0]), X)
    with pytest.raises(ValueError, match="real numeric"):
        call([0.0, True, 3.0], X)


# --------------------------------------------------------------------------- #
# incoming-boundary-flux-normalization
# --------------------------------------------------------------------------- #

VX = np.array([-1.5, -0.5, 0.5, 1.0])
SHAPE = np.array([[1.0, 2.0, 0.5, 1.5], [0.25, 0.0, 3.0, 0.5]])
VOLUME = np.array([[1.0, 2.0, 0.5, 1.0], [0.5, 1.0, 2.0, 0.25]])
SPEED = 2.0


def _exact_incoming(shape, vx, volume, speed):
    """Exact positive-half flux."""
    return sum(
        (
            _frac(speed) * _frac(volume[i, j]) * _frac(shape[i, j]) * _frac(vx[j])
            for j in range(vx.size)
            if vx[j] > 0.0
            for i in range(shape.shape[0])
        ),
        Fraction(0),
    )


def _returned_flux(boundary, vx, volume, speed):
    """Exact positive-half flux of the returned binary64 cells."""
    return _exact_incoming(boundary, vx, volume, speed)


@pytest.mark.parametrize("target", [12.0, -12.0, 0.25, 1e-3])
def test_returned_cells_meet_the_declared_relative_flux_budget(target):
    """Evidence 4: the contract's 64/2**52 budget, recomputed exactly on the output."""
    boundary, scale, initial = N.normalize_incoming_neutral_boundary(
        SHAPE, VX, VOLUME, SPEED, target
    )
    exact_initial = _exact_incoming(SHAPE, VX, VOLUME, SPEED)
    exact_returned = _returned_flux(boundary, VX, VOLUME, SPEED)
    reference = abs(_frac(target))
    assert abs(exact_returned - reference) <= FLUX_RTOL * reference
    assert np.all(boundary[:, VX <= 0.0] == 0.0)
    # The public scalars are separately certified against their exact values.
    assert abs(_frac(initial) / exact_initial - 1) <= FLUX_RTOL
    assert abs(_frac(scale) / (reference / exact_initial) - 1) <= FLUX_RTOL


def test_target_sign_only_changes_the_reported_magnitude():
    """Evidence 5: +target and -target give the same boundary and scale."""
    positive = N.normalize_incoming_neutral_boundary(SHAPE, VX, VOLUME, SPEED, 12.0)
    negative = N.normalize_incoming_neutral_boundary(SHAPE, VX, VOLUME, SPEED, -12.0)
    assert np.array_equal(positive[0], negative[0])
    assert positive[1] == negative[1]
    assert positive[2] == negative[2]


def test_zero_target_returns_the_zero_branch_and_keeps_the_initial_flux():
    """Evidence 5: a zero target is the declared zero branch."""
    boundary, scale, initial = N.normalize_incoming_neutral_boundary(SHAPE, VX, VOLUME, SPEED, 0.0)
    assert np.array_equal(boundary, np.zeros_like(boundary))
    assert scale == 0.0
    assert abs(_frac(initial) / _exact_incoming(SHAPE, VX, VOLUME, SPEED) - 1) <= FLUX_RTOL


def test_tiny_volume_uses_the_exact_path_and_still_meets_the_budget():
    """Evidence 5: factors below 2^-128 leave the bounded float interval for exact arithmetic."""
    tiny = np.array([[1e-200, 1e-200, 1e-200, 1e-200]])
    boundary, scale, initial = N.normalize_incoming_neutral_boundary(
        np.ones_like(tiny), VX, tiny, 1.0, 2.0
    )
    exact_initial = _exact_incoming(np.ones_like(tiny), VX, tiny, 1.0)
    assert abs(_frac(initial) / exact_initial - 1) <= FLUX_RTOL
    exact_returned = _returned_flux(boundary, VX, tiny, 1.0)
    assert abs(exact_returned - 2) <= FLUX_RTOL * 2
    assert scale > 0.0


def test_boundary_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.normalize_incoming_neutral_boundary
    with pytest.raises(ValueError, match="positive incoming half"):
        call(SHAPE, np.array([-1.5, -0.5, -0.25, 0.0]), VOLUME, SPEED, 12.0)
    with pytest.raises(ValueError, match="positive flux"):
        call(np.zeros_like(SHAPE), VX, VOLUME, SPEED, 12.0)
    with pytest.raises(ValueError, match="is invalid"):
        call(-SHAPE, VX, VOLUME, SPEED, 12.0)
    with pytest.raises(ValueError, match="is invalid"):
        call(SHAPE, VX, -VOLUME, SPEED, 12.0)
    with pytest.raises(ValueError, match="is invalid"):
        call(SHAPE, VX, VOLUME, 0.0, 12.0)
    with pytest.raises(ValueError, match="is invalid"):
        call(SHAPE, VX, VOLUME, SPEED, np.nan)
    with pytest.raises(ValueError, match="is invalid"):
        call(SHAPE[:1], VX, VOLUME, SPEED, 12.0)
    with pytest.raises(ValueError, match="real numeric"):
        call(SHAPE, VX, VOLUME, "2.0", 12.0)
    with pytest.raises(ValueError, match="real numeric"):
        call(SHAPE, VX, VOLUME, True, 12.0)
    with pytest.raises(ValueError, match="real numeric"):
        call(SHAPE, VX, VOLUME, SPEED, np.array([12.0]))
