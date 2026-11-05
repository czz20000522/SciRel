"""Independent finite-assembly regressions for the local cold response.

Extreme coefficients are arithmetic-contract witnesses, not device validation.
"""

import math

import numpy as np
import pytest

from scirel.dielectric import cold_plasma_dielectric_tensor


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_finite_stix_axis_projection_survives_overflowing_difference(axis):
    frequency = 1.0 / (2.0 * math.pi)
    field = np.zeros(3)
    field[axis] = math.sqrt(2.0)
    species = [{"density_m3": 8.8541878128e296, "charge_c": 1.0, "mass_kg": 1.0}]
    tensor = cold_plasma_dielectric_tensor(frequency, field, species)
    assert np.all(np.isfinite(tensor)), (
        "finite Stix coefficients must not become NaN during projector assembly"
    )
    # Stix coefficients are independently formed at omega=1. Their difference
    # overflows although both perpendicular and parallel entries are finite.
    wp2 = species[0]["density_m3"] / 8.8541878128e-12
    denominator = 1.0 - float(np.linalg.norm(field)) ** 2
    s, p = 1.0 - wp2 / denominator, 1.0 - wp2
    assert math.isfinite(s) and math.isfinite(p)
    assert math.isinf(p - s)
    expected_diagonal = np.full(3, s)
    expected_diagonal[axis] = p
    np.testing.assert_allclose(tensor.diagonal().real, expected_diagonal, rtol=1e-15, atol=0)


def _decimal_tensor(frequency, field, species, precision=400):
    """Evaluate the defining equation in Decimal, not production Fraction code."""
    from decimal import Decimal as Q, localcontext

    def dec(x):
        return Q.from_float(float(x))

    def add(a, b):
        return a[0] + b[0], a[1] + b[1]

    def neg(a):
        return -a[0], -a[1]

    def mul(a, b):
        return a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]

    def div(a, b):
        norm = b[0] * b[0] + b[1] * b[1]
        return (a[0] * b[0] + a[1] * b[1]) / norm, (a[1] * b[0] - a[0] * b[1]) / norm

    with localcontext() as context:
        context.prec = precision
        w = dec(2.0 * math.pi * frequency)
        B = [dec(x) for x in field]
        magnitude = sum(x * x for x in B).sqrt()
        b = [x / magnitude if magnitude else Q(0) for x in B]
        S, D, P = (Q(1), Q(0)), (Q(0), Q(0)), (Q(1), Q(0))
        for item in species:
            n, q, m = [dec(item[k]) for k in ("density_m3", "charge_c", "mass_kg")]
            if not n or not q:
                continue
            wp2 = n * q * q / (dec(8.8541878128e-12) * m)
            oc = q * magnitude / m
            shifted = (w, dec(item.get("collision_rate_s_inv", 0.0)))
            den = add(mul(shifted, shifted), (-oc * oc, Q(0)))
            S = add(S, neg(div(mul((wp2, Q(0)), shifted), mul((w, Q(0)), den))))
            D = add(D, div((oc * wp2, Q(0)), mul((w, Q(0)), den)))
            P = add(P, neg(div((wp2, Q(0)), mul((w, Q(0)), shifted))))
        cross = [[Q(0), -b[2], b[1]], [b[2], Q(0), -b[0]], [-b[1], b[0], Q(0)]]
        result = []
        for i in range(3):
            row = []
            for j in range(3):
                entry = mul(S, (Q(int(i == j)), Q(0)))
                entry = add(entry, mul(add(P, neg(S)), (b[i] * b[j], Q(0))))
                row.append(add(entry, mul(D, (Q(0), cross[i][j]))))
            result.append(row)
        return result, (S, D, P)


@pytest.mark.parametrize(
    "field",
    [
        [1.0, 1.0, 0.0],
        [1.0, -1.0, 0.0],
        [0.0, 1.0, 1.0],
        [math.sqrt(2.0 / 3.0)] * 3,
        [math.sqrt(2.0) / 3.0, -2.0 * math.sqrt(2.0) / 3.0, 2.0 * math.sqrt(2.0) / 3.0],
    ],
)
def test_rotated_extreme_tensor_agrees_with_high_precision_projection(field):
    frequency = 1.0 / (2.0 * math.pi)
    species = [{"density_m3": 8.8541878128e296, "charge_c": 1.0, "mass_kg": 1.0}]
    answer = cold_plasma_dielectric_tensor(frequency, field, species)
    reference, _ = _decimal_tensor(frequency, field, species)
    refined, _ = _decimal_tensor(frequency, field, species, 480)
    expected = np.array([[complex(float(x), float(y)) for x, y in row] for row in reference])
    assert np.array_equal(
        expected, np.array([[complex(float(x), float(y)) for x, y in row] for row in refined])
    )
    assert np.all(np.isfinite(answer))
    # Normalize components before differences so the assertion cannot overflow.
    np.testing.assert_allclose(answer.real / 1e308, expected.real / 1e308, rtol=1e-14, atol=1e-14)
    np.testing.assert_allclose(answer.imag / 1e308, expected.imag / 1e308, rtol=1e-14, atol=1e-14)
    assert np.array_equal(answer, answer.conj().T)


OVERFLOW_FIELD = [0.9647867330962587, -0.6478744759656198, -0.3873895185961109]
OVERFLOW_SPECIES = [
    {
        "density_m3": 2.714873042260912e296,
        "charge_c": 1.0,
        "mass_kg": 1.0,
        "collision_rate_s_inv": 0.012978111497335272,
    },
    {
        "density_m3": 1.1248668142145498e297,
        "charge_c": -1.0,
        "mass_kg": 1.0,
        "collision_rate_s_inv": 0.2161050319076752,
    },
]


def test_genuinely_unrepresentable_final_component_rejects_whole_call():
    from decimal import Decimal
    from scirel.dielectric import ColdPlasmaOverflowError

    reference, scalars = _decimal_tensor(1 / (2 * math.pi), OVERFLOW_FIELD, OVERFLOW_SPECIES)
    limit = Decimal.from_float(float(np.finfo(float).max))
    assert all(abs(component) < limit for scalar in scalars for component in scalar)
    assert any(
        abs(component) > limit for row in reference for scalar in row for component in scalar
    )
    with pytest.raises(ColdPlasmaOverflowError, match="final tensor assembly"):
        cold_plasma_dielectric_tensor(1 / (2 * math.pi), OVERFLOW_FIELD, OVERFLOW_SPECIES)
    # One invalid point rejects the entire leading-shape call, with no partial tensor.
    with pytest.raises(ColdPlasmaOverflowError, match="final tensor assembly"):
        cold_plasma_dielectric_tensor(
            1 / (2 * math.pi), [np.zeros(3), OVERFLOW_FIELD], OVERFLOW_SPECIES
        )


def _momentum_tensor(frequency, field, species, precision=400):
    """Solve the Cartesian3x3 momentum system by Decimal Gauss-Jordan.

    This oracle never uses Stix scalars or magnetic-direction projectors.
    Binary64 linear solves lose about1e-14 at the electron gyro/drive ratios
    exercised here; high precision fixes that reference error without relaxing
    the production comparison threshold.
    """
    from decimal import Decimal as Q, localcontext

    def dec(x):
        return Q.from_float(float(x))

    def add(a, b):
        return a[0] + b[0], a[1] + b[1]

    def mul(a, b):
        return a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]

    def sub(a, b):
        return a[0] - b[0], a[1] - b[1]

    def div(a, b):
        norm = b[0] * b[0] + b[1] * b[1]
        return (a[0] * b[0] + a[1] * b[1]) / norm, (a[1] * b[0] - a[0] * b[1]) / norm

    with localcontext() as context:
        context.prec = precision
        w = dec(2 * math.pi * frequency)
        x, y, z = [dec(v) for v in field]
        bx = [[Q(0), -z, y], [z, Q(0), -x], [-y, x, Q(0)]]
        sigma = [[(Q(0), Q(0)) for _ in range(3)] for _ in range(3)]
        for item in species:
            n, q, m = [dec(item[k]) for k in ("density_m3", "charge_c", "mass_kg")]
            if not n or not q:
                continue
            nu = dec(item.get("collision_rate_s_inv", 0.0))
            matrix = [
                [(nu * int(i == j) + (q / m) * bx[i][j], -w * int(i == j)) for j in range(3)]
                + [((q / m) * int(i == j), Q(0)) for j in range(3)]
                for i in range(3)
            ]
            for column in range(3):
                pivot = max(
                    range(column, 3), key=lambda row: sum(v * v for v in matrix[row][column])
                )
                matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
                divisor = matrix[column][column]
                matrix[column] = [div(v, divisor) for v in matrix[column]]
                for row in range(3):
                    if row == column:
                        continue
                    factor = matrix[row][column]
                    matrix[row] = [
                        sub(a, mul(factor, b)) for a, b in zip(matrix[row], matrix[column])
                    ]
            for i in range(3):
                for j in range(3):
                    sigma[i][j] = add(sigma[i][j], mul((n * q, Q(0)), matrix[i][j + 3]))
        denominator = dec(8.8541878128e-12) * w
        return np.array(
            [
                [
                    complex(
                        float(Q(int(i == j)) - sigma[i][j][1] / denominator),
                        float(sigma[i][j][0] / denominator),
                    )
                    for j in range(3)
                ]
                for i in range(3)
            ]
        )


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("collision", [0.0, 1e4, 1e6, 1e9])
def test_arbitrary_direction_collisional_response_matches_momentum_system(seed, collision):
    field = np.random.default_rng(31000 + seed).uniform(-0.7, 0.7, 3)
    species = [
        {
            "density_m3": 1e19,
            "charge_c": -1.602176634e-19,
            "mass_kg": 9.1093837015e-31,
            "collision_rate_s_inv": collision,
        },
        {
            "density_m3": 7e18,
            "charge_c": 1.602176634e-19,
            "mass_kg": 1.67262192369e-27,
            "collision_rate_s_inv": collision / 4,
        },
    ]
    answer = cold_plasma_dielectric_tensor(60e6, field, species)
    reference = _momentum_tensor(60e6, field, species)
    assert np.array_equal(reference, _momentum_tensor(60e6, field, species, 480))
    scale = max(float(np.max(np.abs(reference))), 1.0)
    assert np.max(np.abs(answer - reference)) / scale <= 1e-14


def test_leading_shape_mixes_recovered_and_ordinary_points():
    fields = np.array(
        [[[0, 0, math.sqrt(2.0)], [1, 1, 0]], [[0, math.sqrt(2.0), 0], [math.sqrt(2.0), 0, 0]]]
    )
    species = [{"density_m3": 8.8541878128e296, "charge_c": 1.0, "mass_kg": 1.0}]
    answer = cold_plasma_dielectric_tensor(1 / (2 * math.pi), fields, species)
    assert answer.shape == (2, 2, 3, 3)
    assert np.all(np.isfinite(answer))
    for index in np.ndindex(2, 2):
        point = cold_plasma_dielectric_tensor(1 / (2 * math.pi), fields[index], species)
        np.testing.assert_allclose(answer[index] / 1e308, point / 1e308, rtol=1e-14, atol=1e-14)
