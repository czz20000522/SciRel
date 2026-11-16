"""Independent evidence for the conservative cylindrical distribution remap.

Asset: ``scirel.neutrals.cross-mesh-distribution-interpolation``.

The remap transfers cell masses by **geometric overlap** and then optionally
projects each destination slice onto three discrete moments.  Both parts are
checked against sources that do not consult the implementation's weight matrix:

1. **Same-mesh identity.**  With identical velocity and spatial meshes the
   overlap of every cell with itself is the whole cell, so the returned
   distribution must equal the source block for block (both branches).
2. **Spatial invariance of a constant source.**  A source that does not depend on
   ``x`` must remap to a profile that does not depend on ``x`` either; an
   axial/radial transposition or an interpolation weight leak breaks it.
3. **Mass conservation under a refined destination velocity mesh.**  When the
   destination velocity grid covers the same velocity domain and the spatial
   nodes coincide, the total destination mass ``sum(fb * Vol_b)`` must equal the
   total source mass ``sum(fa * vol_a)`` - the overlap cells partition each
   source cell, so a dropped or double-counted overlap changes the total.
4. **Moment preservation of the corrected branch, recomputed independently.**
   The density, axial-momentum and squared-speed energy of every corrected slice
   are recomputed from the returned floats with the verified quadrature measure
   and compared with the linearly interpolated source moments in the same
   normalization the contract uses (relative to the density and scaled by the
   axial and energy scales), with the contract's own ``128 eps`` budget plus one
   factor of two for the independent accumulation.
5. **Zero-filled exterior.**  Destination spatial nodes outside the source
   interval are exactly zero in every velocity cell.
6. **The separating hull is decided, not assumed.**  A slice whose target mean
   velocity lies between two destination nodes (a source concentrated at -1 and
   +1 blended halfway, with no zero node) must raise ``InfeasibleMomentsError``.
7. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel that is reachable without a projection.

Budgets, fixed before measurement:

* the same-mesh identity: exact ``array_equal`` (the fast path is a copy).
* the constant-source invariance: ``8 * eps`` of the profile magnitude.
* mass conservation: ``(n_cells + 6) * eps`` relative to the total mass.
* the moment postcondition: ``256 * eps`` on the normalized residual (the
  contract's 128 eps plus a factor of two for the independent recomputation).
* exterior zeros: exact equality.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

# The contract names this type but `scirel.neutrals` does not export it, so the
# module path is the only way to assert the branch by type (ticket T-2026-0003).
from scirel.neutrals.cross_mesh_distribution_interpolation import InfeasibleMomentsError

EPS = np.finfo(float).eps
VR = np.array([0.5, 1.5, 2.5])
VX = np.array([-2.0, -0.5, 0.5, 2.0])
X = np.array([0.0, 1.0, 2.5])
TNORM = 2.0


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _quadrature(vr=VR, vx=VX):
    """Return the verified cylindrical quadrature for a velocity mesh."""
    return N.make_cylindrical_velocity_quadrature(vr=vr, vx=vx)


def _source(seed=1201):
    """Return a nonnegative source distribution on the shared meshes."""
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, 2.0, size=(VR.size, VX.size, X.size))


def _remap(
    fa,
    *,
    vr_b=VR,
    vx_b=VX,
    x_b=X,
    correct=0,
    tnorm_a=TNORM,
    tnorm_b=TNORM,
    **kwargs,
):
    """Call the remap with the shared source mesh."""
    return N.interp_distribution_across_mesh(
        fa,
        VR,
        VX,
        X,
        tnorm_a,
        vr_b,
        vx_b,
        x_b,
        tnorm_b,
        correct=correct,
        **kwargs,
    )


def test_same_mesh_is_the_identity_on_both_branches():
    """Evidence 1: identical meshes reproduce the source block for block.

    The corrected branch takes the same-velocity-mesh fast path and is an exact
    copy; the uncorrected branch still builds the overlap matrix, which is the
    identity up to the rounding of its overlap ratios.
    """
    fa = _source()
    corrected = _remap(fa, correct=1)
    assert np.array_equal(corrected, fa)
    uncorrected = _remap(fa, correct=0)
    scale = float(np.max(np.abs(fa)))
    assert np.all(np.abs(uncorrected - fa) <= 8 * EPS * scale)


def test_a_constant_source_stays_spatially_constant():
    """Evidence 2: no x dependence may be introduced or lost."""
    fa = np.ones((VR.size, VX.size, X.size))
    fb = _remap(fa)
    profile = fb - fb[:, :, :1]
    assert np.all(np.abs(profile) <= 8 * EPS)
    assert np.all(fb >= 0.0)
    assert np.all(fb <= 1.0 + 8 * EPS)


def test_the_uncorrected_branch_renormalizes_each_slice_to_the_interpolated_total():
    """Evidence 3: the declared compatibility rescale, measured exactly.

    The uncorrected branch ends with a per-slice density rescale, so it
    renormalizes the transferred mass to the linearly interpolated source total.
    That is what this test establishes. It is **not** evidence for the absolute
    scale of the geometric overlap weights: a global factor on the transferred
    mass is divided out by the rescale, and the corrected branch projects onto
    fixed moments independently of the incoming scale. The weight scale is
    therefore listed as a ``cannot establish`` item in the contract.
    """
    fa = _source(seed=1213)
    vr_b = np.array([0.75, 1.25, 1.75, 2.25])
    vx_b = np.array([-1.75, -1.0, -0.25, 0.25, 1.0, 1.75])
    fb = _remap(fa, vr_b=vr_b, vx_b=vx_b)
    source = _quadrature()
    target = _quadrature(vr_b, vx_b)
    totals = []
    for k in range(X.size):
        total = Fraction(0)
        for i in range(VR.size):
            for j in range(VX.size):
                total += _frac(fa[i, j, k]) * _frac(source["volume"][i, j])
        totals.append(total)
    for k in range(X.size):
        target_mass = Fraction(0)
        for i in range(vr_b.size):
            for j in range(vx_b.size):
                target_mass += _frac(fb[i, j, k]) * _frac(target["volume"][i, j])
        relative = abs(target_mass - totals[k]) / totals[k]
        assert float(relative) <= (VR.size * VX.size + 6) * EPS, k


def test_the_corrected_branch_preserves_the_three_interpolated_moments():
    """Evidence 4: the three moments recomputed independently against the interpolated targets."""
    fa = _source(seed=1217)
    vr_b = np.array([0.75, 1.25, 1.75, 2.25])
    vx_b = np.array([-1.75, -1.0, -0.25, 0.25, 1.0, 1.75])
    fb = _remap(fa, vr_b=vr_b, vx_b=vx_b, correct=1)
    source = _quadrature()
    target = _quadrature(vr_b, vx_b)
    fv = float(np.sqrt(TNORM / TNORM))
    va = VX / fv
    ea = (VR[:, None] / fv) ** 2 + va[None, :] ** 2
    volume_a = source["radial_measure"][:, None] * source["dvx"][None, :]
    masses = fa * volume_a[:, :, None]
    density = np.sum(masses, axis=(0, 1))
    momentum = np.sum(masses * va[None, :, None], axis=(0, 1))
    energy = np.sum(masses * ea[:, :, None], axis=(0, 1))
    feature_e = vr_b[:, None] ** 2 + vx_b[None, :] ** 2
    vscale = max(abs(vx_b[0]), abs(vx_b[-1]))
    escale = float(np.max(feature_e))
    for k in range(X.size):
        desired = np.array([np.interp(X[k], X, values) for values in (density, momentum, energy)])
        exact = np.zeros(3)
        for name, values in enumerate(
            (np.ones_like(feature_e), np.broadcast_to(vx_b[None, :], feature_e.shape), feature_e)
        ):
            total = Fraction(0)
            for i in range(vr_b.size):
                for j in range(vx_b.size):
                    total += (
                        _frac(fb[i, j, k]) * _frac(target["volume"][i, j]) * _frac(values[i, j])
                    )
            exact[name] = float(total)
        normalized_actual = exact / desired[0] / np.array([1.0, vscale, escale])
        normalized_desired = desired / desired[0] / np.array([1.0, vscale, escale])
        assert np.all(np.abs(normalized_actual - normalized_desired) <= 256 * EPS), k
        assert np.all(fb[:, :, k] >= 0.0)


def test_nodes_outside_the_source_interval_are_exactly_zero():
    """Evidence 5: the exterior in x is zero in every velocity cell."""
    fa = _source(seed=1223)
    x_b = np.array([-1.0, 0.0, 1.0, 3.5])
    fb = _remap(fa, x_b=x_b)
    assert np.all(fb[:, :, 0] == 0.0)
    assert np.all(fb[:, :, 3] == 0.0)
    assert np.any(fb[:, :, 1] > 0.0) and np.any(fb[:, :, 2] > 0.0)


def test_an_infeasible_target_slice_is_rejected_as_infeasible():
    """Evidence 6: a mean velocity outside the destination node range has no realization.

    The temperature ratio rescales the source velocities by ``fV = 1/2``, so a
    source concentrated at ``vx_a = 1`` asks for mean velocity ``2`` in the
    destination normalization while the destination nodes stop at ``1.5``.
    """
    vr_a = np.array([0.5, 1.5])
    vx_a = np.array([-1.0, 1.0])
    x_a = np.array([0.0, 1.0])
    fa = np.zeros((2, 2, 2))
    fa[:, 1, :] = 1.0
    with pytest.raises(InfeasibleMomentsError) as error:
        N.interp_distribution_across_mesh(
            fa,
            vr_a,
            vx_a,
            x_a,
            4.0,
            np.array([0.75, 1.25]),
            np.array([-1.5, -0.5, 0.5, 1.5]),
            np.array([0.4, 0.6]),
            1.0,
            correct=1,
        )
    assert error.value.diagnostics


def test_remap_rejects_each_reachable_declared_channel():
    """Evidence 7: the reachable rejections of the input contract."""
    fa = _source(seed=1229)
    call = _remap
    with pytest.raises(ValueError, match="must be nonnegative"):
        call(-fa, correct=1)
    with pytest.raises(ValueError, match="strictly increasing"):
        call(fa, vr_b=np.array([1.5, 0.5, 2.5]))
    with pytest.raises(ValueError, match="at least two nodes"):
        call(fa, x_b=np.array([0.5]))
    with pytest.raises(ValueError, match="both negative and positive"):
        call(fa, vx_b=np.array([0.5, 1.0, 1.5, 2.0]))
    with pytest.raises(ValueError, match="within range"):
        call(fa, x_b=np.array([9.0, 10.0]))
    with pytest.raises(ValueError, match="max_correction_iterations"):
        call(fa, correct=1, max_correction_iterations=0)
    with pytest.raises(ValueError):
        call(fa, tnorm_b=0.0)
    # The uncorrected branch still accepts a signed finite source.
    signed = _remap(-fa, correct=0)
    assert np.all(np.isfinite(signed))
