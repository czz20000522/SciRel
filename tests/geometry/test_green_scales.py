"""Scale witnesses derived from the loop integral, not the elliptic implementation."""

from decimal import Decimal, localcontext

import numpy as np
import pytest
import mpmath as mp
from scipy.integrate import quad

from scirel.electromagnetism import compute_greens, get_gpsi
from scirel.electromagnetism.greens import _weighted_psi
from scirel.electromagnetism import MagnetRing
from scirel.configurations import BRB

PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286")


@pytest.mark.parametrize("weight", [1e300, -1e300])
@pytest.mark.parametrize("radius,height", [(1e-160, 1.0), (1e-320, 1e-100)])
def test_axis_field_combines_weight_before_final_rounding(weight, radius, height):
    with localcontext() as ctx:
        ctx.prec = 100
        a, h, w = map(Decimal.from_float, (radius, height, weight))
        expected = float(2 * PI * Decimal("1e-7") * w * a * a / (a * a + h * h) ** Decimal("1.5"))
    psi, br, bz = compute_greens(np.array([[radius, 0.0, weight]]), [[0.0, height]])
    np.testing.assert_allclose(bz, [expected], rtol=1e-14, atol=0.0)
    np.testing.assert_array_equal([psi, br], 0.0)


@pytest.mark.parametrize("entry", ["aggregate", "blocked"])
def test_far_flux_preserves_representable_response(entry):
    # Expanding the angular vector-potential integral at a/r<1e-109 gives
    # pi*1e-7*a^2/r with relative remainder <18*a/r<1.8e-108.
    with localcontext() as ctx:
        ctx.prec = 100
        expected = float(PI * Decimal("1e-7") / Decimal.from_float(1e110))
    rows, points = np.array([[1.0, 0.0, 1.0]]), np.array([[1e110, 0.0]])
    actual = (
        compute_greens(rows, points)[0] if entry == "aggregate" else _weighted_psi(rows, points)
    )
    np.testing.assert_allclose(actual, [expected], rtol=1e-14, atol=0.0)


def test_extreme_radius_flux_matrix_preserves_reciprocity():
    matrix = get_gpsi(np.array([[1.0, 1e110]]), np.array([[0.0, 0.0]]))
    assert matrix[0, 1] > 0
    np.testing.assert_allclose(matrix[0, 1], matrix[1, 0], rtol=1e-14, atol=0.0)


@pytest.mark.parametrize("factory", [MagnetRing, BRB])
def test_signed_source_cancellation_retains_the_original_far_flux_budget(factory):
    # Check the returned geometry, not whether an experimental device has
    # these constants. Its bounded geometric cancellation is included in the
    # independent moment; source order and current conventions are untouched.
    source = factory()
    source.mesh = [[1e110, 0.0]]
    rows = source.rzw if isinstance(source, BRB) else [source.rzw]
    currents = source.current if isinstance(source, BRB) else [source.current]
    with localcontext() as ctx:
        ctx.prec = 100
        moment = sum(
            Decimal.from_float(float(current))
            * Decimal.from_float(float(weight))
            * Decimal.from_float(float(radius)) ** 2
            for group, current in zip(rows, currents, strict=True)
            for radius, _z, weight in group
        )
        expected = float(PI * Decimal("1e-7") * moment / Decimal.from_float(1e110))
    np.testing.assert_allclose(source.psi(), [expected], rtol=1e-14, atol=0.0)


def test_near_wire_complement_square_does_not_create_a_false_singularity():
    # The positive separation is real, and all three weighted responses are
    # representable. 400 digits retain 1-m even at h=1e-170.
    with mp.workdps(400):
        a, r, h, w = map(mp.mpf, (1.0, 1.0, 1e-170, 1e-200))
        d = mp.sqrt((a + r) ** 2 + h * h)
        m = 4 * a * r / (d * d)
        k, e = mp.ellipk(m), mp.ellipe(m)
        expected = [
            float(mp.mpf("1e-7") * w * d * ((2 - m) * k - 2 * e)),
            float(
                2 * mp.mpf("1e-7") * w * h / (r * d) * (-k + (a * a + r * r + h * h) / (h * h) * e)
            ),
            float(2 * mp.mpf("1e-7") * w / d * (k - e)),
        ]
    actual = np.asarray(compute_greens(np.array([[1.0, 0.0, 1e-200]]), [[1.0, 1e-170]]))[:, 0]
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=0.0)
    np.testing.assert_allclose(
        _weighted_psi(np.array([[1.0, 0.0, 1e-200]]), [[1.0, 1e-170]]),
        expected[:1],
        rtol=1e-14,
        atol=0.0,
    )


def _angular_reference(a, r, h):
    # Direct Biot-Savart and vector-potential integrals in ordinary geometry.
    def integrand(phi, component):
        c = np.cos(phi)
        d2 = (r - a) ** 2 + 2 * r * a * (1 - c) + h * h
        return (a * r * c / np.sqrt(d2), a * h * c / d2**1.5, a * (a - r * c) / d2**1.5)[component]

    return np.array(
        [
            1e-7 * quad(lambda p: integrand(p, j), 0, 2 * np.pi, epsabs=1e-12, epsrel=1e-12)[0]
            for j in range(3)
        ]
    )


@pytest.mark.parametrize("r,h", [(0.1, 0.3), (0.9, 0.3), (3.0, -1.0)])
@pytest.mark.parametrize("length,weight", [(1e-200, 1e-100), (1e200, 1e-100), (1e-100, 1e200)])
def test_both_branches_obey_length_and_weight_scaling(r, h, length, weight):
    base = _angular_reference(1.0, r, h)
    with localcontext() as ctx:
        ctx.prec = 100
        length_d, weight_d = map(Decimal.from_float, (length, weight))
        expected = [float(Decimal.from_float(float(base[0])) * length_d * weight_d)]
        expected.extend(float(Decimal.from_float(float(x)) * weight_d / length_d) for x in base[1:])
    actual = np.asarray(
        compute_greens(np.array([[length, 0.0, weight]]), [[r * length, h * length]])
    )[:, 0]
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=0.0)
