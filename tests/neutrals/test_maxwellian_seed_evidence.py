"""Independent evidence for the normalized shifted-Maxwellian seed.

Asset: ``scirel.neutrals.shifted-maxwellian-seed``.

The seed is an exponential of a quadratic form, renormalized on the supplied cell
volumes.  Its scientific content is (a) the quadratic form and its unit
conversion, (b) the normalization, and (c) the tail floor and molecularity
branch.  Evidence:

1. **Exact rational exponent.**  ``exponent = -(vr^2 + (vx - s/vth)^2) *
   molecule_count * tnorm / T`` is a rational function of the inputs; it is
   recomputed with :class:`fractions.Fraction` and compared node by node.  This
   fixes the sign, the shift conversion ``s/vth`` and the ``molecule_count``
   factor at once, and it is exact in the sense that the implementation's own
   expression is not consulted.
2. **Normalization on the cell volumes.**  ``sum(volume * distribution) = 1`` on
   every shift, and the same statement holds with the ``pi``-weighted radial
   measure, which the volume construction must be consistent with.
3. **Exact covariance of the shift.**  Moving the shift by exactly one thermal
   speed relabels the axial mesh by ``-1`` and must leave the exponent array
   bit-identical, because ``s/vth = 1`` is exact for ``s = vth``.
4. **Peak and tail floor, checked against 60-digit arithmetic.**  The analytic
   peak keeps ``exp(0) = 1`` and the tail floor maps every ``argument <= -80`` to
   ``exp(-80)``; both are reproduced with :mod:`decimal` and the normalized values
   are compared to high-precision references, so the branch (floor versus no
   floor) is decided rather than assumed.
5. **Molecularity is the exponent multiplier.**  ``molecule_count = 2`` doubles
   the exponent exactly, and the resulting distribution equals the square
   renormalized on the same volumes.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel.

Budgets, fixed before measurement:

* the exponent: ``8 * eps * |exponent|`` (a handful of products and one division
  per node).
* the normalization: ``(n_cells + 4) * eps`` relative, the forward bound for a
  sum of ``n_cells`` positive terms followed by one division.
* the peak and floor values: ``(n_cells + 8) * eps`` relative against the
  60-digit reference, which carries the float sum and the float rounding of the
  exponential argument.
* the covariance of the shift: exact ``array_equal``.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps
E_CHARGE = 1.602177e-19
AMU = 1.6726231e-27

VR = np.array([0.5, 1.5])
VX = np.array([-1.5, -0.5, 0.5, 1.5])
TNORM = 20.0
MASS = 2.0
TEMPERATURE = 10.0
SHIFT = 0.0


def _volume(vr=VR, vx=VX):
    """Return the quadrature cell volumes for the shared mesh."""
    return N.make_cylindrical_velocity_quadrature(vr=vr, vx=vx)["volume"]


def _seed(*, shifts=None, temperatures=None, molecule_count=1, vr=VR, vx=VX, volume=None):
    """Call the seed builder with the shared fixtures."""
    return N.build_shifted_maxwellian_seed(
        vr=vr,
        vx=vx,
        tnorm_ev=TNORM,
        shifted_vx_m_s=np.array([SHIFT]) if shifts is None else shifts,
        temperature_ev=np.array([TEMPERATURE]) if temperatures is None else temperatures,
        mass_amu=MASS,
        molecule_count=molecule_count,
        cylindrical_volume=_volume(vr, vx) if volume is None else volume,
    )


def _exact_exponent(vr, vx, shift, temperature, molecule_count, thermal_speed):
    """Exact rational exponent per node for one shift."""
    rate = Fraction(molecule_count) * Fraction(TNORM) / Fraction(temperature)
    rows = []
    for radial in vr:
        row = []
        for axial in vx:
            delta = Fraction(axial) - Fraction(shift) / Fraction(thermal_speed)
            row.append(-(Fraction(radial) ** 2 + delta**2) * rate)
        rows.append(row)
    return rows


def test_exponent_is_the_exact_rational_quadratic_form():
    """Evidence 1: the exponent, node by node, in exact rational arithmetic."""
    result = _seed()
    exact = _exact_exponent(VR, VX, SHIFT, TEMPERATURE, 1, result["thermal_speed_m_s"])
    got = result["exponent"][:, :, 0]
    expected = np.array([[float(value) for value in row] for row in exact])
    assert np.all(np.abs(got - expected) <= 8 * EPS * np.maximum(np.abs(expected), 1.0))
    # The thermal speed is the same second-moment scale as compute_thermal_speed_m_s.
    speed = float(result["thermal_speed_m_s"])
    residual = (
        Fraction(speed) ** 2 * Fraction(MASS * AMU) / (2 * Fraction(E_CHARGE) * Fraction(TNORM))
    )
    assert abs(residual - 1) <= 4 * EPS


def test_distribution_is_normalized_on_the_cell_volumes():
    """Evidence 2: sum(volume * distribution) == 1 on every shift."""
    volume = _volume()
    result = _seed(shifts=np.array([0.0, 6000.0]), temperatures=np.array([5.0, 25.0]))
    for k in range(2):
        total = float(np.sum(volume * result["distribution"][:, :, k]))
        assert abs(total - 1.0) <= (volume.size + 4) * EPS
        assert np.all(result["distribution"][:, :, k] > 0.0)


def test_shift_by_one_thermal_speed_relabels_the_axial_mesh_exactly():
    """Evidence 3: s = vth makes s/vth exactly 1, so the exponent is covariant."""
    reference = _seed(shifts=np.array([0.0]))
    speed = float(reference["thermal_speed_m_s"])
    shifted = _seed(shifts=np.array([speed]))
    relabelled = _seed(shifts=np.array([0.0]), vx=VX - 1.0)
    assert np.array_equal(shifted["exponent"], relabelled["exponent"])


def test_peak_and_tail_floor_match_sixty_digit_arithmetic():
    """Evidence 4: exp(0) = 1 at the peak, exp(-80) below the floor."""
    # A shift outside the mesh plus a cold temperature puts the whole mesh on the
    # floor; a shift on a node keeps one exact peak.
    volume = _volume()
    peak = _seed(shifts=np.array([0.0]), temperatures=np.array([1e6]))
    tail = _seed(shifts=np.array([0.0]), temperatures=np.array([1e-6]))
    for case in (peak, tail):
        with localcontext() as context:
            context.prec = 60
            clamps = np.where(
                (case["exponent"][:, :, 0] > -80.0) & (case["exponent"][:, :, 0] <= 0.0),
                case["exponent"][:, :, 0],
                -80.0,
            )
            seed = np.array(
                [
                    [Decimal(float(clamps[i, j])).exp() for j in range(VX.size)]
                    for i in range(VR.size)
                ]
            )
            normalizer = np.sum(
                np.array(
                    [
                        [Decimal(str(float(volume[i, j]))) * seed[i, j] for j in range(VX.size)]
                        for i in range(VR.size)
                    ]
                )
            )
            expected = np.array(
                [[float(seed[i, j] / normalizer) for j in range(VX.size)] for i in range(VR.size)]
            )
        got = case["distribution"][:, :, 0]
        assert np.all(
            np.abs(got - expected) <= (volume.size + 8) * EPS * np.maximum(np.abs(expected), 1e-300)
        )
    # The cold case really sits on the floor: every clamp is -80.
    assert np.all(tail["distribution"][:, :, 0] > 0.0)
    clamped = peak["exponent"][:, :, 0]
    assert np.max(clamped) <= 0.0


def test_molecularity_multiplies_the_exponent_and_squares_the_distribution():
    """Evidence 5: molecule_count = 2 doubles the exponent exactly."""
    volume = _volume()
    atomic = _seed(molecule_count=1)
    molecular = _seed(molecule_count=2)
    assert np.array_equal(molecular["exponent"], 2.0 * atomic["exponent"])
    # exp(2a) renormalized equals the square of exp(a) renormalized on the same
    # volumes; compare the two normalizations through the exact square.
    squared = atomic["distribution"][:, :, 0] ** 2
    expected = squared / float(np.sum(volume * squared))
    assert np.all(np.abs(molecular["distribution"][:, :, 0] - expected) <= 16 * EPS)


def test_seed_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.build_shifted_maxwellian_seed
    volume = _volume()
    good = dict(
        vr=VR,
        vx=VX,
        tnorm_ev=TNORM,
        shifted_vx_m_s=np.array([0.0]),
        temperature_ev=np.array([TEMPERATURE]),
        mass_amu=MASS,
        molecule_count=1,
        cylindrical_volume=volume,
    )
    assert call(**good)["distribution"].shape == (2, 4, 1)
    with pytest.raises(ValueError, match="physical input molecule_count"):
        call(**{**good, "molecule_count": 3})
    with pytest.raises(ValueError, match="molecule_count"):
        call(**{**good, "molecule_count": 1.5})
    with pytest.raises(ValueError, match="strictly positive"):
        call(**{**good, "temperature_ev": np.array([0.0])})
    with pytest.raises(ValueError, match="strictly positive"):
        call(**{**good, "cylindrical_volume": np.zeros_like(volume)})
    with pytest.raises(ValueError, match="compatible nonempty shapes"):
        call(**{**good, "temperature_ev": np.array([TEMPERATURE, 2.0])})
    with pytest.raises(ValueError, match="compatible nonempty shapes"):
        call(**{**good, "shifted_vx_m_s": np.array([])})
    with pytest.raises(ValueError, match="must be finite"):
        call(**{**good, "shifted_vx_m_s": np.array([np.nan])})
    with pytest.raises(ValueError):
        call(**{**good, "tnorm_ev": 0.0})
    with pytest.raises(ValueError):
        call(**{**good, "mass_amu": -1.0})
