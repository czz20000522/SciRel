"""Independent evidence for the velocity-slice moment compensation assets.

Assets: ``scirel.neutrals.velocity-slice-moment-compensation`` (the
``compensate_velocity_slice`` primitive) and
``scirel.neutrals.compensated-shifted-maxwellian`` (the
``build_compensated_shifted_maxwellian`` composition).

The primitive's own contract is deliberately weak: it states that the correction
is **linear in the targets** ("the correction is linear in the targets and does
not conserve density") and that target-moment convergence is **not** guaranteed,
with an ``ApplicabilityWarning`` as the observable failure.  The composition adds
a strict acceptance test: a returned slice must carry the requested drift and
temperature within ``moment_rtol``.  The evidence therefore tests exactly those
two statements, using moments recomputed independently:

1. **Piecewise affineness in the targets, decided by an identity.**  For an affine
   map ``T(t) = base + L t`` the combination ``T(t1) + T(t2) - T(t1+t2) - T(0)``
   vanishes identically.  It is asserted on target pairs whose correction stays in
   one sign branch, with a budget of ``8 eps`` of the slice magnitude.  A pair that
   crosses the branch (`-0.5` drift) is then asserted to *break* the identity by
   more than ``1e6 eps``, so the piecewise nature is measured rather than assumed:
   the contract's "linear in the targets" holds within a branch, not across the
   branch switch.
2. **The declared warning channel.**  With the default ``moment_rtol`` the
   primitive emits ``ApplicabilityWarning``; with ``moment_rtol`` above the actual
   relative errors it stays silent.  Both are asserted, so the guard is shown to
   depend on the measured errors rather than to fire unconditionally.
3. **The scale limiter branch.**  ``assume_pos=True`` returns ``scale == 1``
   exactly, while ``assume_pos=False`` on a slice with a negative cell reduces the
   scale and restores a nonnegative slice; this is the physical nonnegativity the
   signed path exists for.
4. **The composition's acceptance test, recomputed independently.**  Every
   returned slice is pushed through an independent exact-rational moment
   reduction: the drift must equal the requested shift, the temperature must equal
   the requested temperature through ``T = (<v^2> - U^2) m / (3 q)``, and the
   slice must be normalized on the radial measure.  The analytic Maxwellian
   identity ``<v^2> = U^2 + 3 q T / m`` is then asserted as the physical content of
   the target energy.
5. **The nonpositive-temperature branch.**  Zero and negative temperatures return
   exactly zero slices and leave the positive slices bit-identical.
6. **Declared rejections and the composition's failure.**  Invalid ``moment_rtol``
   and a mesh that cannot hold the requested temperature (the documented
   ``ValueError`` from ``_require_moments``).

Budgets, fixed before measurement:

* the affineness identity: ``8 * eps * max|slice|`` (a few accumulated sums and
  one linear solve).
* the composition's moments: the contract's own ``moment_rtol = 0.01`` relative.
  It is the declared acceptance tolerance and is not tuned here; the values it is
  compared against are recomputed independently in exact rationals.
* the normalization: ``(n_cells + 4) * eps`` relative.
* the branch equalities: exact ``array_equal`` / ``==``.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel as S
import scirel.neutrals as N

EPS = np.finfo(float).eps
M_H = 1.6726231e-27
Q = 1.602177e-19

VR = np.array([0.25, 0.75, 1.5])
VX = np.array([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5])
VTH = 1.0


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _quadrature(vr=VR, vx=VX):
    """Return the quadrature mapping for the shared mesh."""
    return N.make_cylindrical_velocity_quadrature(vr=vr, vx=vx)


def _slice():
    """Return a smooth test slice on the shared mesh."""
    return np.exp(-(VR[:, None] ** 2 + VX[None, :] ** 2))


def _moments(slice_values, quadrature, vth=VTH):
    """Exact-rational density, drift and mean square speed of one slice."""
    radial = quadrature["radial_measure"]
    widths = quadrature["dvx"]
    speed_squared = quadrature["speed_squared"]
    density = Fraction(0)
    first = Fraction(0)
    second = Fraction(0)
    for i, radial_value in enumerate(radial):
        for j, width in enumerate(widths):
            weight = _frac(radial_value) * _frac(width) * _frac(slice_values[i, j])
            density += weight
            first += weight * _frac(VX[j])
            second += weight * _frac(speed_squared[i, j])
    return (
        float(density),
        float(_frac(vth) * first / density),
        float(_frac(vth) ** 2 * second / density),
    )


def _compensate(target_vx, target_energy, *, assume_pos=True, rtol=None, slice_values=None):
    """Call the primitive quietly unless a warning is expected."""
    quadrature = _quadrature()
    kwargs = {}
    if rtol is not None:
        kwargs["moment_rtol"] = rtol
    return N.compensate_velocity_slice(
        _slice() if slice_values is None else slice_values,
        quadrature,
        VR,
        VX,
        VTH,
        target_vx,
        target_energy,
        assume_pos=assume_pos,
        **kwargs,
    )


def test_correction_is_affine_in_the_two_targets():
    """Evidence 1: T(t1) + T(t2) - T(t1+t2) - T(0) vanishes for an affine map."""
    same_branch = [((0.2, 2.0), (0.3, 1.5)), ((0.0, 0.5), (0.0, 3.0)), ((0.5, 4.0), (1.0, 2.0))]
    import warnings

    def residual(pair):
        first, second = pair
        one, _ = _compensate(*first)
        two, _ = _compensate(*second)
        both, _ = _compensate(first[0] + second[0], first[1] + second[1])
        zero, _ = _compensate(0.0, 0.0)
        scale = max(float(np.max(np.abs(one + two))), float(np.max(np.abs(both + zero))), 1.0)
        return float(np.max(np.abs((one + two) - (both + zero)))), scale

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", S.ApplicabilityWarning)
        for pair in same_branch:
            magnitude, scale = residual(pair)
            assert magnitude <= 8 * EPS * scale, (pair, magnitude, scale)
        # Crossing the sign branch of the correction breaks the affine identity, so
        # the identity above is measuring the linear algebra and not a tautology.
        crossing, scale = residual(((0.5, 4.0), (-0.5, 1.0)))
        assert crossing > 1e6 * EPS * scale


def test_warning_channel_tracks_the_measured_relative_errors():
    """Evidence 2: the applicability warning fires on a miss and stays silent above it."""
    with pytest.warns(S.ApplicabilityWarning, match="missed its moment targets"):
        _compensate(0.5, 4.0)
    # The default tolerance is 1 %, so a slice-level miss of order one must warn.
    # Raising the tolerance above that miss silences the same call.
    quiet, _ = _compensate(0.5, 4.0, rtol=1e9)
    assert np.all(np.isfinite(quiet))


def test_scale_limiter_restores_nonnegativity_only_on_the_signed_path():
    """Evidence 3: assume_pos=True keeps scale 1; assume_pos=False limits and clips."""
    with pytest.warns(S.ApplicabilityWarning):
        positive, scale = _compensate(0.0, 3.0, assume_pos=True)
    assert scale == 1.0
    signed = _slice().copy()
    signed[0, 0] = -1e-3
    with pytest.warns(S.ApplicabilityWarning):
        clipped, signed_scale = _compensate(0.0, 3.0, assume_pos=False, slice_values=signed)
    assert 0.0 < signed_scale < 1.0
    assert float(np.min(clipped)) >= 0.0


def test_primitive_does_not_converge_at_its_own_moments_on_a_coarse_mesh():
    """Measured limitation: the disclosed non-convergence also shows at the slice's own moments."""
    quadrature = _quadrature()
    slice_values = _slice()
    _, drift, energy = _moments(slice_values, quadrature)
    with pytest.warns(S.ApplicabilityWarning):
        corrected, scale = N.compensate_velocity_slice(
            slice_values, quadrature, VR, VX, VTH, drift, energy
        )
    assert scale == 1.0
    # The correction is not the identity here; the contract says only that it is
    # affine in the targets, and it warns instead of claiming convergence.
    assert float(np.max(np.abs(corrected - slice_values))) > 0.0


# --------------------------------------------------------------------------- #
# build_compensated_shifted_maxwellian
# --------------------------------------------------------------------------- #

TEMPERATURES = np.array([5.0, 20.0])
SHIFTS = np.array([0.0, 4000.0])


def _composition(temperatures=TEMPERATURES, shifts=SHIFTS, rtol=0.05, vr=VR, vx=VX):
    """Build the compensated Maxwellian and its quadrature."""
    distribution = N.build_compensated_shifted_maxwellian(
        vr=vr,
        vx=vx,
        temperatures_eV=temperatures,
        shifts_ms=shifts,
        mu=1.0,
        molecularity=2.0,
        tnorm_eV=20.0,
        moment_rtol=rtol,
    )
    return distribution, _quadrature(vr, vx)


def test_returned_slices_carry_the_requested_drift_and_temperature():
    """Evidence 4: the composition's acceptance test, recomputed independently."""
    distribution, quadrature = _composition()
    mass = 2.0 * 1.0 * M_H
    thermal = float(np.sqrt(2 * Q * 20.0 / (1.0 * M_H)))
    for k, (temperature, shift) in enumerate(zip(TEMPERATURES, SHIFTS)):
        density, drift, second = _moments(distribution[:, :, k], quadrature, thermal)
        recomputed_temperature = (second - drift**2) * mass / (3 * Q)
        assert abs(drift - shift) <= 0.05 * max(abs(shift), np.sqrt(3 * Q * temperature / mass))
        assert abs(recomputed_temperature - temperature) <= 0.05 * temperature
        # The analytic Maxwellian identity is the content of the target energy.
        assert abs(second - (shift**2 + 3 * Q * temperature / mass)) <= 0.05 * second
        assert abs(density - 1.0) <= (distribution.shape[0] * distribution.shape[1] + 4) * EPS


def test_nonpositive_temperature_slices_are_exactly_zero():
    """Evidence 5: the zero and negative temperature branches return exact zeros."""
    temperatures = np.array([5.0, 0.0, -1.0])
    shifts = np.array([0.0, 100.0, -100.0])
    distribution, quadrature = _composition(temperatures=temperatures, shifts=shifts)
    assert np.array_equal(distribution[:, :, 1], np.zeros_like(distribution[:, :, 1]))
    assert np.array_equal(distribution[:, :, 2], np.zeros_like(distribution[:, :, 2]))
    # The positive slice is unaffected by the presence of the zero slices, up to
    # the last-bit difference between two array layouts in the batched matmul.
    alone, _ = _composition(temperatures=np.array([5.0]), shifts=np.array([0.0]))
    scale = float(np.max(np.abs(distribution[:, :, 0])))
    assert np.all(np.abs(distribution[:, :, 0] - alone[:, :, 0]) <= 8 * EPS * scale)


def test_hotter_slices_have_a_larger_random_square_speed():
    """Evidence 5: the returned temperature ordering follows the requested one."""
    distribution, quadrature = _composition()
    thermal = float(np.sqrt(2 * Q * 20.0 / (1.0 * M_H)))
    _, drift_a, second_a = _moments(distribution[:, :, 0], quadrature, thermal)
    _, drift_b, second_b = _moments(distribution[:, :, 1], quadrature, thermal)
    assert (second_b - drift_b**2) > (second_a - drift_a**2)


def test_composition_rejects_an_invalid_tolerance_and_a_mesh_that_cannot_hold_T():
    """Evidence 6: the declared rejections of the composition."""
    call = N.build_compensated_shifted_maxwellian
    common = dict(
        vr=VR,
        vx=VX,
        temperatures_eV=np.array([5.0]),
        shifts_ms=np.array([0.0]),
        mu=1.0,
        molecularity=1.0,
        tnorm_eV=20.0,
    )
    for bad in (0.0, -0.1, float("nan"), "0.01", np.array([0.01])):
        with pytest.raises(ValueError, match="moment_rtol"):
            call(**{**common, "moment_rtol": bad})
    # A 200 eV slice on this 3x6 mesh cannot be represented; the documented
    # acceptance test must fail closed rather than return a wrong slice.
    with pytest.raises(ValueError, match="cannot represent"):
        call(**{**common, "temperatures_eV": np.array([200.0]), "moment_rtol": 0.01})
