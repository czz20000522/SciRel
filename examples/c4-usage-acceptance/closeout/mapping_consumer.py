"""Replay the three mapping reads with the distribution's isolated Python (-IB)."""

import numpy as np

from scirel.kinetic import solve_relativistic_codrift_spectrum
from scirel.kinetic.dispersion.rational import jpole_evaluate
from scirel.neutrals import sum_elastic_frequency_channels


def main():
    zj = jpole_evaluate([-1], [-1j], 1 + 1j)["ZJ"]
    np.testing.assert_allclose(zj, -0.2 + 0.4j, rtol=1e-14, atol=0)
    print("ZJ:", zj)

    total = sum_elastic_frequency_channels([[1, 2], [0.5, 1], [0.25, 0.5]])[
        "elastic_frequency_m_inv"
    ]
    np.testing.assert_array_equal(total, [1.75, 3.5])
    print("elastic_frequency_m_inv (1/m):", total.tolist())

    # The packaged case specifies empty species and k; it does not name all species fields.
    case = {
        "constants": {"c": 1, "epsilon0": 1, "mu0": 1, "B0": 1},
        "relativistic": False,
        "collision_matrix": "zero",
        "species": [],
        "k": np.empty((0, 3)),
    }
    spectra = solve_relativistic_codrift_spectrum(case)["spectra"]
    assert spectra == []
    print("spectra:", spectra, "(empty k; no nonempty plasma spectrum observed)")


if __name__ == "__main__":
    main()
