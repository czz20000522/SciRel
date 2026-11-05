"""Scientific regressions for the retained D2 successor, not D1 parity claims."""

import copy
import numpy as np
import pytest
from scipy.special import erfcx, iv
from scirel.kinetic.fluid_spectrum import (
    evaluate_fluid_special,
    derive_fluid_case,
    evaluate_fluid_dispersion,
    assemble_fluid_em,
    solve_fluid_bonk,
    solve_fluid_em,
)


def test_large_imaginary_z_and_all_r_removable_boundaries():
    z = evaluate_fluid_special("zfun", 30j)
    np.testing.assert_allclose(z, 1j * np.sqrt(np.pi) * erfcx(30), rtol=3e-13, atol=0)
    for method in ("RTAY", "RASY", "RINT", "RYLA"):
        np.testing.assert_allclose(
            evaluate_fluid_special(method, 2, 0),
            [[2 / 3, 2 / 3], [-10 / 9, -10 / 9]],
            rtol=3e-13,
            atol=0,
        )
        np.testing.assert_array_equal(evaluate_fluid_special(method, 0, 40), np.zeros((2, 2)))
        with pytest.raises(ValueError, match="pole"):
            evaluate_fluid_special(method, 1, 0)


def test_zero_wavenumbers_are_finite_signed_reflection_and_state_isolation():
    state = derive_fluid_case("bonk", 1)
    state["w"] = 0.63 * state["wn"]
    original = copy.deepcopy(state)
    for method in ("fD", "fDR", "fDtensor"):
        state["kz"] = 0
        result = evaluate_fluid_dispersion(0, state, method)
        assert np.isfinite(result["K"]).all()
        np.testing.assert_array_equal(result["K"][[0, 1], 2], [0, 0])
        state["kz"] = 1e-12
        plus = evaluate_fluid_dispersion(0.43 * state["kn"], state, method)
        state["kz"] = -1e-12
        minus = evaluate_fluid_dispersion(0.43 * state["kn"], state, method)
        reflection = np.diag([1, 1, -1])
        np.testing.assert_allclose(
            minus["K"], reflection @ plus["K"] @ reflection, rtol=3e-12, atol=1e-11
        )
        assert minus["state_after"]["kz"].item() == -1e-12
    for key in original:
        if key != "kz":
            np.testing.assert_array_equal(state[key], original[key])


def test_finite_rational_matrix_restores_dropped_polynomial_response():
    # Independent direct constitutive evaluation at a nonpole point. The
    # production four-entry correction is not used to build this oracle.
    s = derive_fluid_case("em", 2)
    w = 0.83 * s["wn"].item()
    r = assemble_fluid_em(s, w, 8, 0)
    M = r["M"]
    p = r["poles"]

    # Independent harmonic dielectric sum, not the implementation's polynomial
    # correction. n=0 Gamma only, but its neighbor identity contributes +/-1.
    def physical_residual(k):
        K = np.eye(3, dtype=complex)
        table = p["cn"].flat[0]
        rl = np.asarray(table["rl"]).ravel()
        pl = np.asarray(table["pl"]).ravel()
        for wc, wp, rho, vt in zip(
            *(np.asarray(s[x]).ravel() for x in ("wcs", "wps2", "rhocs", "vts"))
        ):
            z = k * abs(rho)
            a = k * rho
            b = a * a
            G0 = sum(rl / (z - pl))
            n = np.array([-1, 0, 1])
            G = np.array([0, G0, 0])
            Gp = np.array([G0 / 2, -G0, G0 / 2])
            for bj, cj in zip(np.asarray(p["bzj"]).ravel(), np.asarray(p["czj"]).ravel()):
                Y = (w - s["kz"].item() * vt * cj) / wc
                f = wp / (w * wc) * bj / (Y - n)
                K[0, 0] += sum(f * n * n * G / b)
                K[0, 1] += sum(f * 1j * n * Gp)
                K[1, 0] -= sum(f * 1j * n * Gp)
                K[1, 1] += sum(f * (n * n * G / b - 2 * b * Gp))
                K[0, 2] += sum(f * np.sqrt(2) * cj * n * G / a)
                K[2, 0] += sum(f * np.sqrt(2) * cj * n * G / a)
                K[1, 2] += sum(f * (-1j * np.sqrt(2) * a * cj * Gp))
                K[2, 1] -= sum(f * (-1j * np.sqrt(2) * a * cj * Gp))
                K[2, 2] += sum(f * 2 * cj * cj * G)
        nn = np.sqrt(s["c2"].item()) / w * np.array([k, 0, s["kz"].item()])
        D = K + np.outer(nn, nn) - sum(nn * nn) * np.eye(3)
        return abs(np.linalg.det(D)) / max(1, np.prod(np.linalg.norm(D, axis=1)))

    roots = np.linalg.eigvals(M)
    roots = roots[roots.real > 1e-5 * s["kn"].item()]
    roots = roots[np.argsort(abs(roots.imag))][:5]
    assert len(roots) == 5
    assert max(physical_residual(root) for root in roots) < 2e-6


def test_status_and_complete_finite_spectrum_are_explicit():
    s = derive_fluid_case("bonk", 2)
    r = solve_fluid_bonk(2, [0.63 * s["wn"].item()])
    assert r["nf"].shape == (1, 1)
    assert r["root_valid"].item()
    assert r["residual"].item() <= 1e-8
    np.testing.assert_allclose(
        r["nf"].item() / s["kn"].item(), 0.0983444810802785j, atol=3e-12, rtol=3e-12
    )
    e = derive_fluid_case("em", 2)
    r = solve_fluid_em(2, 8, 0, [0.83 * e["wn"].item()])
    assert r["d"].shape == (40, 1)
    assert r["kxx"].shape == (1, 5)
    assert r["eigen_diagnostics"]["complete_finite_matrix_spectrum"].item()
    assert not r["eigen_diagnostics"]["complete_physical_modes"].item()


@pytest.mark.parametrize("J,N", [(4, 0), (8, -1), (8, 8), (12, 1.5)])
def test_undefined_tables_fail_closed(J, N):
    s = derive_fluid_case("em", 2)
    with pytest.raises(ValueError):
        assemble_fluid_em(s, 0.83 * s["wn"].item(), J, N)


def test_explicit_controls_cannot_be_overridden_by_state_fields():
    s = derive_fluid_case("em", 2)
    w = 0.83 * s["wn"].item()
    expected = assemble_fluid_em(s, w, 8, 0)["M"]
    s.update(w=0, N=7, J=12, L=np.zeros(8), cn="invalid", sgns=np.nan, absrhocs=np.nan)
    actual = assemble_fluid_em(s, w, 8, 0)["M"]
    np.testing.assert_array_equal(actual, expected)


def test_physical_state_and_zero_weight_harmonic_boundary():
    s = derive_fluid_case("bonk", 2)
    s["w"] = 2 * abs(s["wcs"].item())
    for method in ("fD", "fDtensor"):
        r = evaluate_fluid_dispersion(0, s, method)
        assert np.isfinite(r["K"]).all()
    s["rhocs"] = s["rhocs"] * 1.01
    with pytest.raises(ValueError, match="rho"):
        evaluate_fluid_dispersion(0, s, "fD")
    with pytest.raises(ValueError, match="65536"):
        evaluate_fluid_special("RYLA", 1e6 + 0.1j, 1)


def test_multifrequency_em_preserves_each_nested_diagnostic_array():
    s = derive_fluid_case("em", 2)
    result = solve_fluid_em(2, 8, 0, np.array([0.37, 0.83, 1.43]) * s["wn"].item())
    assert result["kxx"].shape == (3, 5)
    assert np.isfinite(result["kxx"]).all()
    # Each frequency owns a full finite spectrum, not a flattened MAT cell.
    assert result["spectra"].shape == (1, 3)
    assert all(row.shape == (40, 1) for row in result["spectra"].flat)
    assert result["diagnostic_rows"].shape == (1, 3)
    assert all(
        row["complete_finite_matrix_spectrum"].item() for row in result["diagnostic_rows"].flat
    )
    diagnostics = result["eigen_diagnostics"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["complete_finite_matrix_spectrum"].item()


def test_gamma_order_and_argument_broadcast_contract():
    n = np.arange(8)[:, None]
    b = np.array([0, 0.217, 0.731, 2.717])
    expected = np.exp(-b) * iv(n, b)
    derivative = np.exp(-b) * ((iv(n - 1, b) + iv(n + 1, b)) / 2 - iv(n, b))
    np.testing.assert_allclose(
        evaluate_fluid_special("Gamman", n, b), expected, rtol=3e-13, atol=3e-15
    )
    np.testing.assert_allclose(
        evaluate_fluid_special("Gammapn", n, b), derivative, rtol=3e-13, atol=3e-15
    )
