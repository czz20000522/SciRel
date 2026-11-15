"""Necessary SI similarity, not an absolute tensor-accuracy certification.

For s>0 scale B, f, kx and kz by s and density by s**2, leaving q/m/T
unchanged. Thermal speeds, alpha, a/b, zeta_n, nx/nz and hence full K/D
and det(D) are invariant at fixed harmonic/pole order. Both evaluations
can share an error: this relation does not prove the model or its accuracy.
The 12 pairs/24 calls and componentwise 2e-12 budget are fixed in advance.
"""

import numpy as np
import pytest

import scirel.kinetic as kinetic


_SCALE = 2.0**-52
_PAIRS = [
    pytest.param(name, sign, 10000.0, id=f"{name}-real-{label}-kz")
    for sign, label in ((1, "positive"), (-1, "negative"))
    for name in (
        "evaluate_kinetic_dispersion_sum",
        "evaluate_fluid_kinetic_dispersion_sum",
        "evaluate_kinetic_dielectric_tensor",
        "evaluate_kinetic_dispersion_ronnmark",
    )
] + [
    pytest.param(name, sign, 10000.0 + 2000.0j, id=f"{name}-complex-{label}-kz")
    for sign, label in ((1, "positive"), (-1, "negative"))
    for name in ("evaluate_kinetic_dielectric_tensor", "evaluate_kinetic_dispersion_ronnmark")
]


@pytest.mark.parametrize("name,sign,kx", _PAIRS)
def test_full_tensor_and_determinant_preserve_si_similarity(name, sign, kx):
    inputs = dict(
        B0=1.0,
        qs=[-1.60217662e-19],
        ms=[9.1094e-31],
        ns0=[6.075e19],
        Ts0=[11604691.395316169],
        f=15915494309.189535,
        kz=sign * 1000.0,
        kx=kx,
    )
    scaled_inputs = inputs | {key: inputs[key] * _SCALE for key in ("B0", "f", "kx", "kz")}
    scaled_inputs["ns0"] = [value * _SCALE**2 for value in inputs["ns0"]]
    call = getattr(kinetic, name)
    base = call(**inputs)
    scaled = call(**scaled_inputs)
    # No frequency reconstruction or backend/order override in either call.
    comparisons = {}
    for field in ("K", "D", "determinant"):
        key = "det_D" if field == "determinant" and "det_D" in base else field
        reference, actual = np.asarray(base[key]), np.asarray(scaled[key])
        assert reference.shape == actual.shape == ((3, 3) if field != "determinant" else ())
        assert np.isfinite(reference).all() and np.isfinite(actual).all()
        errors = np.abs(actual - reference) / np.maximum(1, np.abs(reference))
        comparisons[field] = float(np.max(errors))
    assert all(error <= 2e-12 for error in comparisons.values()), comparisons
