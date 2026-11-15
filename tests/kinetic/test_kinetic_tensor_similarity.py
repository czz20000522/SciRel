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
    pytest.param(method, sign, 10000.0, id=f"{method}-real-{label}-kz")
    for sign, label in ((1, "positive"), (-1, "negative"))
    for method in ("harmonic", "harmonic_weideman", "diagnostic", "ronnmark")
] + [
    pytest.param(method, sign, 10000.0 + 2000.0j, id=f"{method}-complex-{label}-kz")
    for sign, label in ((1, "positive"), (-1, "negative"))
    for method in ("diagnostic", "ronnmark")
]


@pytest.mark.parametrize("method,sign,kx", _PAIRS)
def test_full_tensor_and_determinant_preserve_si_similarity(method, sign, kx):
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
    call = (
        kinetic.evaluate_dielectric_diagnostics
        if method == "diagnostic"
        else kinetic.evaluate_dielectric_response
    )
    options = {} if method == "diagnostic" else {"method": method}
    base = call(
        **{key: value for key, value in inputs.items() if key != "f"},
        omega=2.0 * np.pi * float(inputs["f"]),
        **options,
    )
    scaled = call(
        **{key: value for key, value in scaled_inputs.items() if key != "f"},
        omega=2.0 * np.pi * float(scaled_inputs["f"]),
        **options,
    )
    # Preserve the original Hz-to-omega arithmetic and each method's default order.
    comparisons = {}
    for field in ("K", "D", "determinant"):
        key = (
            ("determinant_raw" if field == "determinant" else f"{field}_raw")
            if method == "diagnostic"
            else field
        )
        reference, actual = np.asarray(base[key]), np.asarray(scaled[key])
        assert reference.shape == actual.shape == ((3, 3) if field != "determinant" else ())
        assert np.isfinite(reference).all() and np.isfinite(actual).all()
        errors = np.abs(actual - reference) / np.maximum(1, np.abs(reference))
        comparisons[field] = float(np.max(errors))
    assert all(error <= 2e-12 for error in comparisons.values()), comparisons
