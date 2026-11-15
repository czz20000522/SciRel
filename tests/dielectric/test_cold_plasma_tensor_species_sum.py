"""Independent momentum-equation checks of collective Stix cancellation.

References solve Cartesian Newton--Lorentz equations at 120 and 200 digits.
No production coefficient or projection supplies an expected value. Each real
and imaginary component has its own rtol=1e-13, atol=0 budget, fixed before
running the implementation; exact structural zeros are checked separately.
"""

import itertools
import math

import numpy as np
import pytest

from scirel.dielectric import (
    ColdPlasmaOverflowError,
    ColdPlasmaResonanceError,
    cold_plasma_dielectric_tensor,
)
from test_cold_plasma_tensor_assembly import _momentum_tensor

EPS0 = 8.8541878128e-12
FREQUENCY = 1 / (2 * math.pi)


def _species(density, charge, mass=1.0, collision=0.0):
    return dict(
        density_m3=density,
        charge_c=charge,
        mass_kg=mass,
        collision_rate_s_inv=collision,
    )


def _reference(frequency, field, species):
    first = _momentum_tensor(frequency, field, species, precision=120)
    second = _momentum_tensor(frequency, field, species, precision=200)
    # With real omega and no contributing collisions, L=-i*omega*I+(q/m)C
    # is anti-Hermitian because C.T=-C. Thus i*L^-1 is Hermitian and its
    # diagonal imaginary parts are exact zeros. Generic complex elimination
    # can leave precision-dependent roundoff there; apply this independent
    # theorem only to reference diagonals, never to a production result or a
    # nonzero Hall/collisional component. All other convergence checks remain.
    if all(
        item["density_m3"] == 0
        or item["charge_c"] == 0
        or item.get("collision_rate_s_inv", 0.0) == 0
        for item in species
    ):
        np.fill_diagonal(first.imag, 0.0)
        np.fill_diagonal(second.imag, 0.0)
    np.testing.assert_array_equal(first, second)
    return second


def _assert_components(actual, expected):
    assert actual.shape == expected.shape
    assert actual.dtype == np.complex128
    assert np.all(np.isfinite(actual))
    for part in ("real", "imag"):
        observed, reference = getattr(actual, part), getattr(expected, part)
        zeros = reference == 0
        np.testing.assert_array_equal(observed[zeros], np.zeros_like(reference[zeros]))
        np.testing.assert_allclose(observed[~zeros], reference[~zeros], rtol=1e-13, atol=0)


@pytest.mark.parametrize("scale", [0.01, 1.0, 100.0])
@pytest.mark.parametrize("field", [[0.0, 0.0, 0.5], [0.3, 0.4, 0.0]])
def test_opposite_large_species_keep_small_hall_in_every_order(scale, field):
    species = [
        _species(EPS0 * 2**54, 1.0),
        _species(EPS0, 1.0),
        _species(EPS0 * 2**54, -1.0),
    ]
    frequency = FREQUENCY * scale
    reference = _reference(frequency, field, species)
    answers = []
    for ordered in itertools.permutations(species):
        answer = cold_plasma_dielectric_tensor(frequency, field, ordered)
        _assert_components(answer, reference)
        answers.append(answer)
    for answer in answers[1:]:
        np.testing.assert_array_equal(answer, answers[0])


@pytest.mark.parametrize("scale", [0.01, 1.0, 100.0])
@pytest.mark.parametrize("field", [[0.0, 0.0, 1.0], [0.0, -1.0, 0.0], [0.48, 0.64, 0.6]])
@pytest.mark.parametrize("collision", [0.0, 0.02])
def test_quasineutral_small_hall_is_checked_on_its_own_scale(scale, field, collision):
    species = [
        _species(1e19, -1.602176634e-19, 9.1093837015e-31, collision),
        _species(1e19, 1.602176634e-19, 1.67262192369e-27, collision),
    ]
    frequency = FREQUENCY * scale
    reference = _reference(frequency, field, species)
    first = cold_plasma_dielectric_tensor(frequency, field, species)
    second = cold_plasma_dielectric_tensor(frequency, field, species[::-1])
    _assert_components(first, reference)
    _assert_components(second, reference)
    np.testing.assert_array_equal(first, second)


@pytest.mark.parametrize("collision", [0.0, math.ulp(0.0)])
def test_underflowed_frequency_square_is_not_a_resonance(collision):
    species = [_species(1e-300, 1.0, collision=collision)]
    reference = _reference(1e-180, [0.0, 0.0, 0.0], species)
    try:
        answer = cold_plasma_dielectric_tensor(1e-180, [0.0, 0.0, 0.0], species)
    except ColdPlasmaOverflowError:
        return  # Explicit arithmetic refusal is permitted; a resonance is not.
    _assert_components(answer, reference)


def test_true_represented_pole_still_rejects_when_both_squares_underflow():
    frequency = 1e-180
    omega = 2 * math.pi * frequency
    with pytest.raises(ColdPlasmaResonanceError):
        cold_plasma_dielectric_tensor(frequency, [0.0, 0.0, 1.0], [_species(1e300, omega)])


def test_inert_entries_do_not_select_a_different_single_species_arithmetic():
    active = _species(EPS0, 1.0)
    inert = _species(0.0, 1.0, mass=math.ulp(0.0), collision=1e308)
    field = [0.0, 0.0, 0.5]
    expected = cold_plasma_dielectric_tensor(FREQUENCY, field, [active])
    for species in ([inert, active], [active, inert]):
        np.testing.assert_array_equal(
            cold_plasma_dielectric_tensor(FREQUENCY, field, species), expected
        )


def test_collective_batch_and_point_calls_agree_without_losing_components():
    species = [
        _species(1e19, -1.602176634e-19, 9.1093837015e-31),
        _species(1e19, 1.602176634e-19, 1.67262192369e-27),
    ]
    fields = np.array([[[0.0, 0.0, 1.0], [0.0, 0.0, 0.0]], [[0.0, -1.0, 0.0], [0.48, 0.64, 0.6]]])
    result = cold_plasma_dielectric_tensor(FREQUENCY, fields, species)
    assert result.shape == (2, 2, 3, 3)
    for index in np.ndindex(2, 2):
        point = cold_plasma_dielectric_tensor(FREQUENCY, fields[index], species)
        np.testing.assert_array_equal(result[index], point)
        _assert_components(point, _reference(FREQUENCY, fields[index], species))
