"""Finite-grid arithmetic diagnostic against independent Eq.(8), not physics approval.

The saved Eq.(3) Maxwellian A and rounded-table Eq.(8) B are different
objects. Only product minus B has the pre-frozen 2e-7 diagnostic budget.
No research generator is imported or executed during pytest.
"""

import json
from fractions import Fraction
from pathlib import Path

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_dielectric_response


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "kinetic_tensor"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


INPUTS = _load("inputs.json")
REFERENCE = _load("reference.json")
CASES = {case["id"]: case for case in INPUTS["cases"]}
B = {case["id"]: case for case in REFERENCE["B"]["cases"]}
A = {case["id"]: case for case in REFERENCE["A_original"]["cases"]}
# Select the independently frozen successor only for the new observations.
# The original small-kz value and its REFERENCE_BLOCK remain in A_original.
A["small-kz"] = REFERENCE["A_small_kz_successor"]["case"]


def _complex(pair):
    return complex(float(pair[0]), float(pair[1]))


def _mp(pair):
    return mp.mpc(mp.mpf(pair[0]), mp.mpf(pair[1]))


def _matrix(record, key):
    return np.array([[_complex(value) for value in row] for row in record[key]])


def _kwargs(case):
    species = case["species"]
    return dict(
        B0=case["B"],
        qs=[s["charge"] for s in species],
        ms=[s["mass"] for s in species],
        ns0=[s["density"] for s in species],
        Ts0=[s["temperature"] for s in species],
        omega=case["omega"],
        kz=case["kz"],
        kx=complex(*case["kx"]),
    )


@pytest.mark.parametrize("case_id", CASES)
def test_product_matches_independent_B_16(case_id, record_property):
    actual = evaluate_dielectric_response(method="ronnmark", **_kwargs(CASES[case_id]))
    expected = B[case_id]
    for key in ("K", "D", "determinant"):
        reference = _complex(expected["detD"]) if key == "determinant" else _matrix(expected, key)
        value = np.asarray(actual[key])
        assert value.shape == (() if key == "determinant" else (3, 3))
        assert np.isfinite(value).all()
        # Componentwise complex magnitude; never normalize by a matrix maximum.
        error = np.abs(value - reference) / np.maximum(1.0, np.abs(reference))
        assert np.all(error <= 2e-7), (case_id, key, error)

    # Observations only: B-A has no physical acceptance budget. The manual
    # reproduce.py --observe entry retains re/im/absolute/scaled values too.
    differences = {}
    for key in ("K", "D"):
        physical, numerical = _matrix(A[case_id], key), _matrix(expected, key)
        differences[key] = float(
            np.max(np.abs(numerical - physical) / np.maximum(1.0, np.abs(physical)))
        )
    physical = _complex(A[case_id]["detD"])
    differences["detD"] = abs(_complex(expected["detD"]) - physical) / max(1, abs(physical))
    record_property("B_minus_A_observation_no_acceptance_threshold", json.dumps(differences))


def _fraction(record):
    return Fraction(int(record["numerator"]), int(record["denominator"]))


def _multiply(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def test_current_binary64_table_retains_its_actual_moments():
    model = _load("poles.json")
    actual = evaluate_dielectric_response(method="ronnmark", **_kwargs(CASES["ordinary"]))
    beta, poles = [], []
    for j, row in enumerate(model["full8_binary64_identities"]):
        for component, identity in zip(
            (
                actual["diagnostics"]["bzj"][j].real,
                actual["diagnostics"]["bzj"][j].imag,
                actual["diagnostics"]["czj"][j].real,
                actual["diagnostics"]["czj"][j].imag,
            ),
            row,
            strict=True,
        ):
            assert float(component).hex() == identity["hex"]
            assert Fraction(float(component)) == _fraction(identity)
        beta.append(tuple(_fraction(v) for v in row[:2]))
        poles.append(tuple(_fraction(v) for v in row[2:]))
    moments = []
    for order, saved in enumerate(model["exact_rational_moments_M0_M1_M2_M3"]):
        moment = (Fraction(0), Fraction(0))
        for weight, pole in zip(beta, poles, strict=True):
            term = weight
            for _ in range(order):
                term = _multiply(term, pole)
            moment = tuple(a + b for a, b in zip(moment, term, strict=True))
        assert moment == (_fraction(saved["re"]), _fraction(saved["im"]))
        moments.append(moment)
    assert moments[0] != (-1, 0)
    assert moments[1] != (0, 0)
    assert moments[2] != (Fraction(-1, 2), 0)


def test_zero_kz_B_keeps_moment_cross_residuals():
    model = _load("poles.json")
    with mp.workdps(100):
        moments = [
            mp.mpc(
                *(
                    mp.mpf(int(v["numerator"])) / int(v["denominator"])
                    for v in (row["re"], row["im"])
                )
            )
            for row in model["exact_rational_moments_M0_M1_M2_M3"]
        ]
        M0, M1, M2 = moments[:3]
        for endpoint in _load("zero_kz_responses.json"):
            expected = mp.eye(3)
            for species in endpoint["species"]:
                a, b, P = (_mp(species["derived"][k]) for k in ("a", "b", "P"))
                x, R, H = (_mp(species[k]) for k in ("x", "R", "H"))
                xx, xy = P * M0 * R, mp.j * P * M0 * H / x
                yy = P * M0 * (R - 2 * b * H / x**2)
                xz = P * mp.sqrt(2) * a * M1 * R / x
                yz = -mp.j * P * mp.sqrt(2) * a * M1 * H / x**2
                zz = 2 * P * M2 * (x + b * R) / x**2
                expected += mp.matrix([[xx, xy, xz], [-xy, yy, yz], [xz, -yz, zz]])
            reference = B[endpoint["id"]]
            for i in range(3):
                for j in range(3):
                    value = _mp(reference["K"][i][j])
                    assert abs(value - expected[i, j]) / max(1, abs(value)) <= mp.mpf("1e-70")
            if endpoint["id"] != "both-zero":
                assert _mp(reference["K"][0][2]) != 0
                assert _mp(reference["K"][1][2]) != 0
                assert _mp(A[endpoint["id"]]["K"][0][2]) == 0
                assert _mp(A[endpoint["id"]]["K"][1][2]) == 0


def test_A_cold_Hall_sign_and_complex_square():
    with mp.workdps(100):
        case = CASES["both-zero"]
        sp = case["species"][0]
        omega = mp.mpf(case["omega"])
        Omega = mp.mpf(sp["charge"]) * mp.mpf(case["B"]) / mp.mpf(sp["mass"])
        wp2 = (
            mp.mpf(sp["density"])
            * mp.mpf(sp["charge"]) ** 2
            / (mp.mpf(INPUTS["constants"]["eps0"]) * mp.mpf(sp["mass"]))
        )
        # Cold Lorentz equation with exp(-i omega t), independent of the pole table.
        hall = -mp.j * wp2 * Omega / (omega * (omega**2 - Omega**2))
        saved = _mp(A["both-zero"]["K"][0][1])
        assert abs(saved - hall) / max(1, abs(hall)) <= mp.mpf("1e-70")
        assert saved.imag < 0  # Electron, positive B and 0 < omega < |Omega|.
        record = A["complex-kx"]
        a, b = (_mp(record["parameters"][0][k]) for k in ("a", "b"))
        assert abs(b - a * a) <= mp.mpf("1e-70")
        assert b.imag != 0 and b != abs(a) ** 2
        nx = _mp(record["nx"])
        expected = _mp(record["K"][2][2]) - nx**2
        assert abs(_mp(record["D"][2][2]) - expected) <= mp.mpf("1e-70")


def test_original_A_block_and_successor_have_separate_identities():
    convergence = _load("convergence.json")
    old = convergence["A_original"]
    assert old["status"] == "REFERENCE_BLOCK"
    assert (old["convergence_passed"], old["case_count"]) == (15, 16)
    small = next(c for c in old["comparisons"] if c["case_id"] == "small-kz")
    assert small["status"] == "REFERENCE_BLOCK"
    with mp.workdps(100):
        assert any(mp.mpf(c["max_scaled_diff"]) > mp.mpf("1e-70") for c in small["comparisons"])
    successor = convergence["A_small_kz_successor"]
    assert successor["original_evaluation_exit"] == 2
    assert successor["successful_calculations"] == successor["expected_calculations"] == 4
    assert successor["other_case_reruns"] == 0
    assert all(c["status"] == "PASS" for c in successor["gate_comparisons"])
    assert A["small-kz"]["dps"] == 280 and A["small-kz"]["N"] == 128
    assert len(CASES) == len(B) == len(A) == 16
