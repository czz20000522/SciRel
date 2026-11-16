"""Independent evidence for the one-dimensional scalar cross-mesh handoff.

Asset: ``scirel.neutrals.cross-mesh-scalar-interpolation``.

The relation is a piecewise-linear transfer with a zero-filled exterior, so the
evidence is built from the algebraic properties of linear interpolation plus one
**measured** refinement ratio on a declared grid family - the only place an order
claim is made, and it is made for uniform source meshes only:

1. **Exact reproduction of the affine class.**  Linear interpolation reproduces
   any affine profile exactly, so the observed error is pure rounding; the same
   equality is asserted on an unsorted destination mesh to show that the
   contiguity rule, not the call order, decides.
2. **Node and exterior conventions.**  Values at the source nodes are reproduced
   exactly, and every destination node outside ``[min(xa), max(xa)]`` is exactly
   zero.
3. **Convexity of the interpolant.**  Each interpolated value lies between the
   two bracketing source values, which a sign or weight error cannot satisfy for
   a monotone profile.
4. **Contiguity discriminator.**  A destination mesh whose in-range nodes are not
   one contiguous block must be rejected; a fully out-of-range mesh must be
   rejected too.
5. **Measured second-order ratio, uniform source family only.**  Refining a
   uniform source mesh by two halves the spacing, so the linear-interpolation
   error of a smooth profile at fixed evaluation points must fall by about four.
   The ratio is measured and asserted to lie in ``[3.0, 5.0]``; this is an
   observation on uniform meshes, not a claim about arbitrary meshes.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel.

Budgets, fixed before measurement:

* affine reproduction and node values: ``8 * eps * scale`` (the weights are exact
  for data of this form, so only rounding remains).
* the measured ratio band ``[3.0, 5.0]`` around the exact 4, declared before any
  measurement: the band is wide enough to absorb the pre-asymptotic first level
  but narrow enough that a first-order or third-order implementation is rejected.
* exterior zeros: exact equality.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps


def test_affine_profiles_are_reproduced_to_rounding():
    """Evidence 1: an affine profile is exact, including on an unsorted destination."""
    xa = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    fa = 1.0 + 2.0 * xa
    xb = np.array([0.0, 0.25, 1.1, 2.0, 0.8, 1.6])
    fb = N.interpolate_scalar_across_mesh(fa, xa, xb)
    exact = 1.0 + 2.0 * xb
    assert np.all(np.abs(fb - exact) <= 8 * EPS * float(np.max(np.abs(exact))))


def test_source_nodes_are_reproduced_and_the_exterior_is_exactly_zero():
    """Evidence 2: node values and the zero-filled exterior."""
    xa = np.array([0.0, 0.3, 1.0, 2.5])
    fa = np.array([3.0, -1.0, 2.0, 0.5])
    xb = np.array([-2.0, 0.0, 0.3, 1.0, 2.5, 4.0])
    fb = N.interpolate_scalar_across_mesh(fa, xa, xb)
    assert fb[0] == 0.0 and fb[-1] == 0.0
    assert np.allclose(fb[1:5], fa, rtol=0.0, atol=8 * EPS * 3.0)


def test_interpolated_values_stay_between_the_bracketing_nodes():
    """Evidence 3: convexity of the piecewise-linear interpolant."""
    xa = np.array([0.0, 1.0, 2.0, 4.0])
    fa = np.array([0.0, 10.0, 10.0, -5.0])
    xb = np.array([0.25, 0.75, 1.5, 3.0, 3.75])
    fb = N.interpolate_scalar_across_mesh(fa, xa, xb)
    for value, coordinate in zip(fb, xb):
        right = int(np.searchsorted(xa, coordinate, side="right"))
        right = min(max(right, 1), xa.size - 1)
        left = right - 1
        low, high = min(fa[left], fa[right]), max(fa[left], fa[right])
        assert low - 8 * EPS * 10.0 <= value <= high + 8 * EPS * 10.0


def test_the_in_range_block_must_be_contiguous():
    """Evidence 4: a hole in the in-range set is rejected, as is a fully out-of-range mesh."""
    xa = np.array([0.0, 1.0, 2.0])
    fa = np.array([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="contiguous"):
        N.interpolate_scalar_across_mesh(fa, xa, np.array([0.5, 5.0, 1.5]))
    with pytest.raises(ValueError, match="within range"):
        N.interpolate_scalar_across_mesh(fa, xa, np.array([5.0, 6.0]))


def test_measured_refinement_ratio_on_uniform_source_meshes():
    """Evidence 5: the measured h^-2 ratio, observed on uniform meshes only."""
    probes = np.array([0.137, 0.311, 0.523, 0.789, 0.941])
    errors = []
    for nodes in (8, 16, 32, 64):
        xa = np.linspace(0.0, 1.0, nodes)
        fa = np.sin(np.pi * xa)
        fb = N.interpolate_scalar_across_mesh(fa, xa, probes)
        errors.append(float(np.max(np.abs(fb - np.sin(np.pi * probes)))))
    ratios = [errors[k] / errors[k + 1] for k in range(len(errors) - 1)]
    assert all(error > 0.0 for error in errors)
    assert 3.0 <= ratios[-1] <= 5.0, (errors, ratios)
    # The band is declared in the module docstring before the measurement; the
    # exact second-order value is 4 and the observed ratio is recorded here.
    assert abs(math.log2(ratios[-1]) - 2.0) <= 0.5, (errors, ratios)


def test_scalar_interpolation_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.interpolate_scalar_across_mesh
    xa = np.array([0.0, 1.0, 2.0])
    fa = np.array([0.0, 1.0, 2.0])
    xb = np.array([0.5, 1.5])
    assert call(fa, xa, xb).shape == (2,)
    with pytest.raises(ValueError, match="strictly increasing"):
        call(fa, np.array([0.0, 1.0, 1.0]), xb)
    with pytest.raises(ValueError, match="at least two strictly increasing nodes"):
        call(np.array([1.0]), np.array([0.5]), xb)
    with pytest.raises(ValueError, match="do not agree"):
        call(fa[:2], xa, xb)
    with pytest.raises(ValueError, match="finite real one-dimensional"):
        call(fa, xa, np.array([0.5, np.nan]))
    with pytest.raises(ValueError, match="finite real one-dimensional"):
        call([[True, 1.0, 2.0]], xa, xb)
    with pytest.raises(ValueError, match="do_warn must be an integer"):
        call(fa, xa, xb, do_warn=0.5)
    with pytest.raises(ValueError, match="do_warn must be an integer"):
        call(fa, xa, xb, do_warn=True)
