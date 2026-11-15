"""F09 equivalence evidence on a bounded common domain, not a physics oracle.

The three harmonic implementations use the same Maxwellian tensor. Their
agreement does not independently validate that model. Use identical cutoffs
and compare the matrices, rather than relative determinants near a root.
The R-function test separately checks a convergent harmonic representation.
"""

import numpy as np
import pytest
from scipy.special import ive

from scirel.kinetic import (
    evaluate_dielectric_response,
    evaluate_dielectric_diagnostics,
    evaluate_ronnmark_r,
)

Q = 1.60217662e-19
M = 9.1094e-31
KB = 1.38064852e-23
TEMPERATURE = 1000.0 * 1.6022e-19 / KB
WC = Q / M
VT = np.sqrt(2 * KB * TEMPERATURE / M)
RHO = VT / (np.sqrt(2) * WC)


def _case(b, frequency, parallel, pair=False):
    return dict(
        B0=1.0,
        qs=[-Q, Q] if pair else [-Q],
        ms=[M, 1.6726219e-27] if pair else [M],
        ns0=[6.075e19] * (2 if pair else 1),
        Ts0=[TEMPERATURE] * (2 if pair else 1),
        f=frequency * WC / (2 * np.pi),
        kx=np.sqrt(b) / RHO,
        kz=parallel * WC / VT,
    )


def _scaled_error(actual, reference):
    return np.max(np.abs(actual - reference)) / max(1.0, np.max(np.abs(reference)))


@pytest.mark.parametrize("order", [5, 15, 30, 80])
@pytest.mark.parametrize(
    "b,frequency,parallel,pair",
    [
        (0.2, 0.7, 0.3, False),
        (1.0, 1.0, 0.2, False),
        (4.0, 2.3, 0.5, False),
        (8.0, 1.4, -0.4, False),
        (0.2, 0.7, 0.3, True),
    ],
)
def test_three_harmonic_paths_have_the_same_tensor_at_the_same_cutoff(
    b, frequency, parallel, pair, order
):
    arguments = _case(b, frequency, parallel, pair)
    inputs = {key: value for key, value in arguments.items() if key != "f"}
    inputs["omega"] = 2.0 * np.pi * float(arguments["f"])
    reference = evaluate_dielectric_response(**inputs, method="harmonic", harmonics=order)
    for method in ("harmonic_weideman", "diagnostic"):
        actual = (
            evaluate_dielectric_diagnostics(**inputs, harmonics=order)
            if method == "diagnostic"
            else evaluate_dielectric_response(**inputs, method=method, harmonics=order)
        )
        assert actual["diagnostics"]["harmonics"] == order, (
            "every harmonic path must actually use the supplied cutoff"
        )
        for key in ("K", "D"):
            assert (
                _scaled_error(
                    actual[f"{key}_raw"] if method == "diagnostic" else actual[key], reference[key]
                )
                < 2e-12
            ), (
                f"{method}: {key} disagrees on the common real-input domain; "
                "compare conventions and algorithms before declaring a new model"
            )


@pytest.mark.parametrize(
    "method",
    [
        "harmonic",
        "harmonic_weideman",
        "diagnostic",
    ],
)
def test_harmonic_cutoff_is_a_convergence_control_for_all_three_paths(method):
    arguments = _case(8.0, 1.4, 0.4)
    inputs = {key: value for key, value in arguments.items() if key != "f"}
    inputs["omega"] = 2.0 * np.pi * float(arguments["f"])
    call = (
        evaluate_dielectric_diagnostics if method == "diagnostic" else evaluate_dielectric_response
    )
    options = {} if method == "diagnostic" else {"method": method}
    key = "K_raw" if method == "diagnostic" else "K"
    reference = call(**inputs, harmonics=80, **options)[key]
    errors = [
        _scaled_error(call(**inputs, harmonics=order, **options)[key], reference)
        for order in (5, 15, 30)
    ]
    assert errors[0] > 1e-2, "this case must exercise a visibly insufficient harmonic cutoff"
    assert errors[2] < errors[1] < errors[0], "increasing the cutoff must converge for this case"
    assert errors[2] < 2e-12, "the selected finite-harmonic reference must be converged"


@pytest.mark.parametrize("b", [0.2, 1.0, 4.0, 8.0])
@pytest.mark.parametrize("x", [0.7 + 0.4j, 2.3 + 1.2j, -1.7 + 0.8j])
def test_ronnmark_r_matches_its_independent_harmonic_representation(b, x):
    # R(x,b) = sum_n n^2 Gamma_n(b)/(b*(x-n)); its reported derivative
    # is d(b*R)/db, not dR/db. Imaginary x avoids harmonic poles. At
    # b <= 8 the 80/160 comparison checks truncation independently.
    def harmonic(order):
        n = np.arange(-order, order + 1)
        gamma = ive(n, b)
        derivative = (ive(n - 1, b) + ive(n + 1, b)) / 2 - gamma
        return np.array(
            [
                np.sum(n**2 * gamma / (b * (x - n))),
                np.sum(n**2 * derivative / (x - n)),
            ]
        )

    reference = harmonic(160)
    np.testing.assert_allclose(harmonic(80), reference, rtol=0, atol=1e-14)
    actual = evaluate_ronnmark_r(x, b)
    # The R routine stops its series at a relative 1e-8 term criterion.
    # This bound concerns these R samples, not the full J=8 tensor's accuracy.
    np.testing.assert_allclose(
        [actual["R"], actual["H"]],
        reference,
        rtol=1e-7,
        atol=1e-9,
        err_msg="Ronnmark response must represent the same harmonic response, including d(bR)/db",
    )
