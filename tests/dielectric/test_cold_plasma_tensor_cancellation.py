"""Final projection accuracy, separate from upstream near-pole conditioning."""

import math

import numpy as np
import pytest

from scirel.dielectric import cold_plasma_dielectric_tensor

EPSILON0 = 8.8541878128e-12
FREQUENCY = 1 / (2 * math.pi)


@pytest.mark.parametrize("axis", range(3))
def test_near_resonance_retains_small_parallel_component(axis):
    field = np.zeros(3)
    field[axis] = np.nextafter(1.0, 2.0)
    density = EPSILON0 * 0.8
    answer = cold_plasma_dielectric_tensor(
        FREQUENCY, field, [dict(density_m3=density, charge_c=1.0, mass_kg=1.0)]
    )
    expected = 1.0 - density / EPSILON0
    assert abs(answer[axis, axis] - expected) <= 1e-14 * abs(expected)


def _represented_stix(frequency, field, species):
    """Retained binary64 coefficients: this is not an upstream accuracy oracle.

    The near-pole tests isolate final projection from the separately retained
    conditioning of the Stix evaluation. Physical equation agreement is checked
    by the independent momentum oracle below at ordinary frequency ratios.
    """
    omega = 2 * math.pi * frequency
    magnitude = np.linalg.norm(np.asarray(field, dtype=float), axis=-1)
    s, d, p = (np.ones((), complex), np.zeros((), complex), np.ones((), complex))
    for item in species:
        n, q, m = (item[k] for k in ("density_m3", "charge_c", "mass_kg"))
        wp2 = n * q * q / (EPSILON0 * m)
        cyclotron = q * magnitude / m
        shifted = omega + 1j * item.get("collision_rate_s_inv", 0.0)
        denominator = shifted * shifted - cyclotron * cyclotron
        s -= wp2 * shifted / (omega * denominator)
        d += cyclotron * wp2 / (omega * denominator)
        p -= wp2 / (omega * shifted)
    return complex(s), complex(d), complex(p)


def _rotation_reference(field, coefficients, precision=400):
    """Rotate an orthonormal field-frame response with Decimal Gram-Schmidt.

    This reference does not use production Fraction projectors, rationalized
    scalar sums or the binary64-normalized magnetic direction.
    """
    from decimal import Decimal as Q, localcontext

    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

    with localcontext() as context:
        context.prec = precision
        B = [Q.from_float(float(x)) for x in field]
        norm = sum(x * x for x in B).sqrt()
        b = [x / norm for x in B]
        axis = min(range(3), key=lambda i: abs(b[i]))
        seed = [Q(int(i == axis)) for i in range(3)]
        first = cross(b, seed)
        length = sum(x * x for x in first).sqrt()
        first = [x / length for x in first]
        second = cross(b, first)
        s, d, p = coefficients
        sr, si, dr, di, pr, pi = [
            Q.from_float(x) for x in (s.real, s.imag, d.real, d.imag, p.real, p.imag)
        ]
        rows = []
        for i in range(3):
            row = []
            for j in range(3):
                perpendicular = first[i] * first[j] + second[i] * second[j]
                parallel = b[i] * b[j]
                rotation = second[i] * first[j] - first[i] * second[j]
                row.append(
                    complex(
                        float(sr * perpendicular + pr * parallel - di * rotation),
                        float(si * perpendicular + pi * parallel + dr * rotation),
                    )
                )
            rows.append(row)
        return np.array(rows)


@pytest.mark.parametrize("axis", range(3))
@pytest.mark.parametrize("transverse", [0.0, 1e-12, 1e-9, 1e-4])
@pytest.mark.parametrize("collision", [0.0, 1e-20, 1e-12, 0.01])
@pytest.mark.parametrize("plasma_factor", [0.8, 0.999999])
def test_near_axis_small_diagonal_matches_independent_rotation(
    axis, transverse, collision, plasma_factor
):
    field = np.zeros(3)
    field[axis] = np.nextafter(1.0, 2.0)
    field[(axis + 1) % 3] = transverse
    field[(axis + 2) % 3] = -transverse / 3
    species = [
        dict(
            density_m3=EPSILON0 * plasma_factor,
            charge_c=1.0,
            mass_kg=1.0,
            collision_rate_s_inv=collision,
        )
    ]
    coefficients = _represented_stix(FREQUENCY, field, species)
    expected = _rotation_reference(field, coefficients)
    assert np.array_equal(expected, _rotation_reference(field, coefficients, 480))
    answer = cold_plasma_dielectric_tensor(FREQUENCY, field, species)
    # The small parallel-like component must pass on its own scale, not be
    # hidden by a norm dominated by the near-resonant transverse response.
    assert abs(answer[axis, axis] - expected[axis, axis]) <= 1e-14 * abs(expected[axis, axis])
    scale = max(float(np.max(np.abs(expected))), 1.0)
    assert np.max(np.abs(answer - expected)) / scale <= 1e-14


@pytest.mark.parametrize("collision", [0.03, 0.3, 3.0])
@pytest.mark.parametrize("charge", [1.0, -1.0])
def test_rotated_collisional_symmetric_and_hall_cancellation(collision, charge):
    species = [
        dict(
            density_m3=EPSILON0 * 0.8, charge_c=charge, mass_kg=1.0, collision_rate_s_inv=collision
        )
    ]
    s, d, p = _represented_stix(FREQUENCY, [0.0, 0.0, 1.2], species)
    a = (p.real - s.real) / 2
    roots = [(d.imag + sign * math.sqrt(d.imag * d.imag + 4 * a * a)) / (2 * a) for sign in (-1, 1)]
    z = next(root for root in roots if abs(root) < 1)
    x = math.sqrt((1 - z * z) / 2)
    field = 1.2 * np.array([x, x, z])
    coefficients = _represented_stix(FREQUENCY, field, species)
    expected = _rotation_reference(field, coefficients)
    assert np.array_equal(expected, _rotation_reference(field, coefficients, 480))
    answer = cold_plasma_dielectric_tensor(FREQUENCY, field, species)
    assert abs(expected[0, 1].real) < 1e-14
    # Resolve the tiny real cancellation residual componentwise, even though
    # the same complex entry has an ordinary-sized imaginary component.
    assert abs(answer[0, 1].real - expected[0, 1].real) <= 1e-14 * abs(expected[0, 1].real)
    np.testing.assert_allclose(answer, expected, rtol=1e-14, atol=1e-14)


@pytest.mark.parametrize("omega", [1e-3, 1.0, 1e3])
@pytest.mark.parametrize("gyro_ratio", [0.1, 0.8, 1.1, 50.0])
@pytest.mark.parametrize("collision_ratio", [0.0, 0.2, 100.0])
def test_mixed_scales_against_cartesian_momentum_equations(omega, gyro_ratio, collision_ratio):
    from test_cold_plasma_tensor_assembly import _momentum_tensor

    field = omega * gyro_ratio * np.array([2.0, -3.0, 6.0]) / 7.0
    species = [
        dict(
            density_m3=EPSILON0 * omega**2 * 0.3,
            charge_c=1.0,
            mass_kg=1.0,
            collision_rate_s_inv=omega * collision_ratio,
        ),
        dict(
            density_m3=EPSILON0 * omega**2 * 0.1,
            charge_c=-1.0,
            mass_kg=4.0,
            collision_rate_s_inv=omega * collision_ratio / 3,
        ),
    ]
    frequency = omega / (2 * math.pi)
    expected = _momentum_tensor(frequency, field, species, 400)
    assert np.array_equal(expected, _momentum_tensor(frequency, field, species, 480))
    answer = cold_plasma_dielectric_tensor(frequency, field, species)
    scale = max(float(np.max(np.abs(expected))), 1.0)
    assert np.max(np.abs(answer - expected)) / scale <= 1e-14


def test_mixed_batch_keeps_small_parallel_response_and_overflow_recovery():
    fields = np.array(
        [
            [[0.0, 0.0, np.nextafter(1.0, 2.0)], [1e-9, 0.0, np.nextafter(1.0, 2.0)]],
            [[0.0, 0.0, math.sqrt(2.0)], [0.2, 0.3, 0.4]],
        ]
    )
    species = [dict(density_m3=EPSILON0 * 0.8, charge_c=1.0, mass_kg=1.0)]
    answer = cold_plasma_dielectric_tensor(FREQUENCY, fields, species)
    for index in np.ndindex(2, 2):
        point = cold_plasma_dielectric_tensor(FREQUENCY, fields[index], species)
        np.testing.assert_array_equal(answer[index], point)
    assert abs(answer[0, 0, 2, 2] - 0.19999999999999996) <= 1e-14 * 0.19999999999999996


def test_projection_does_not_inherit_callers_decimal_context():
    from decimal import Inexact, ROUND_FLOOR, localcontext

    field = [0.2, -0.3, 0.4]
    species = [dict(density_m3=EPSILON0 * 0.8, charge_c=1.0, mass_kg=1.0, collision_rate_s_inv=0.3)]
    expected = cold_plasma_dielectric_tensor(FREQUENCY, field, species)
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_FLOOR
        context.Emax = 5
        context.Emin = -5
        context.traps[Inexact] = True
        np.testing.assert_array_equal(
            cold_plasma_dielectric_tensor(FREQUENCY, field, species), expected
        )
