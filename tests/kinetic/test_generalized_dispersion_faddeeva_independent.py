"""Independent arbitrary-precision equation oracle, not captured source answers."""

import mpmath as mp
import numpy as np
from scirel.kinetic import evaluate_plasma_dispersion
from scirel.numerics import evaluate_faddeeva


def test_high_precision_equation_grid():
    mp.mp.dps = 80
    points = [
        complex(x, y) for x in (-12, -3, -0.1, 0, 0.1, 3, 12) for y in (-2, -0.1, 0, 0.1, 2, 40)
    ]
    expected = np.array(
        [complex(mp.exp(-(mp.mpc(z) ** 2)) * mp.erfc(-1j * mp.mpc(z))) for z in points]
    )
    for order, atol, rtol in [
        (32, 5e-13, 5e-13),
        (16, 4e-7, 3e-6),
    ]:
        np.testing.assert_allclose(
            evaluate_faddeeva(points, order=order), expected, atol=atol, rtol=rtol
        )


def test_jpole_gaussian_cauchy_integral():
    mp.mp.dps = 70
    points = [0.2 + 0.1j, 1 + 1j, 5 + 2j, -3 + 0.5j]
    expected = [
        complex(
            mp.quad(lambda v: mp.exp(-v * v) / (v - z), [-mp.inf, -4, -1, 0, 1, 4, mp.inf])
            / mp.sqrt(mp.pi)
        )
        for z in points
    ]
    for order in (8, 12, 16, 24):
        result = evaluate_plasma_dispersion(points, method="jpole", order=order)
        np.testing.assert_allclose(result["Z"], expected, rtol=5e-5, atol=5e-6)
        np.testing.assert_allclose(
            result["w"],
            np.asarray(expected) / (1j * np.sqrt(np.pi)),
            rtol=5e-5,
            atol=5e-6 / np.sqrt(np.pi),
        )
