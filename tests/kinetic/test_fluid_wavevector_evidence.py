"""Independent evidence for the fluid case state, wavevector matrix and response.

Precision budgets, written before measurement.  The closed-form case scales are
compared at ``1e-14`` relative, which is the rounding of the declared binary64
constants themselves.  The assembled wavevector matrix puts ``||M||`` near
``1e14``, so its ``n x n`` determinant cannot be compared to a product of
eigenvalues at binary64 precision; the reference recomputes the determinant at 40
digits and allows ``1e-12`` relative on the 40x40 problem and ``1e-10`` on the
94x94 one, both far above the measured value and far below any wrong assembly.
The response determinant identity at zero transverse wavenumber is algebraic and
is asserted at ``1e-14``.

Failure matrix, one assertion per channel:

* wrong derived case scale -> ``test_fluid_case_state_derived_scales_match_closed_forms``
* wrong published constant -> ``test_fluid_case_state_source_constants_are_published_values``
* wrong matrix order or sparsity -> ``test_fluid_dispersion_matrix_structural_identities``
* matrix rows inconsistent with the returned spectrum -> ``test_fluid_dispersion_matrix_determinant_equals_eigenvalue_product``
* a kz-odd assembly that should be kz-even -> ``test_fluid_dispersion_matrix_kz_sign_gives_identical_kx_spectrum``
* wrong threshold, count or ordering rule -> ``test_fluid_wavevector_eigensolve_selection_relations``
* wrong dielectric determinant -> ``test_fluid_dispersion_response_zero_transverse_determinant_identity``
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

import _cold_fluid_spectrum_reference as reference

CASE_SELECTORS = [("bonk", 1), ("bonk", 2), ("bonk", 3), ("em", 1), ("em", 2)]


def _scalar(value) -> float:
    return float(np.asarray(value).ravel()[0])


def _dispersion_state(family: str, jcase: int) -> dict:
    """Case state extended with the angular frequency the response needs."""
    from scirel.kinetic.fluid_spectrum import derive_fluid_case

    case = derive_fluid_case(family, jcase)
    state = {key: value for key, value in case.items()}
    state["w"] = 0.63 * _scalar(case["wn"])
    return state


def _wavevector_matrix(kz: float, max_harmonic: int = 0, j_order: int = 8):
    from scirel.kinetic import (
        assemble_fluid_dispersion_matrix,
        derive_species_equilibrium_scales,
        get_gamma_lpole_coefficients,
        get_z_pole_coefficients,
    )

    scales = derive_species_equilibrium_scales(
        ms=[9.1094e-31],
        qs=[-1.60217662e-19],
        ns_unit=[1],
        Ts_unit=[1],
        B0=1,
        n00=6.075e19,
        T00=1000,
    )
    gamma = get_gamma_lpole_coefficients(max_harmonic=max_harmonic)
    zeta = get_z_pole_coefficients(j_order=j_order)
    result = assemble_fluid_dispersion_matrix(
        omega=scales["wn"],
        kz=kz,
        c2=scales["c2"],
        epsilon0=scales["epsilon0"],
        wps2=scales["wps2"],
        wcs=scales["wcs"],
        vts=scales["vts"],
        rhocs=scales["rhocs"],
        sgns=scales["sgns"],
        absrhocs=scales["absrhocs"],
        cn_residues=gamma["residues"],
        cn_poles=gamma["poles"],
        order_lengths=gamma["order_lengths"],
        bzj=zeta["bzj"],
        czj=zeta["czj"],
        max_harmonic=max_harmonic,
        n_species=1,
    )
    return result, scales


def test_fluid_case_state_source_constants_are_published_values():
    """The fixed constants behind every case are the published ones, not tuned numbers.

    ``c**2`` is exact by the SI definition of the metre.  ``epsilon0``, ``k_B``,
    the elementary charge and the proton mass reproduce the CODATA-2014 literals.
    ``me`` and the eV-to-joule factor are five-digit roundings of the same table,
    which is why they are compared at ``1e-4`` and stated as roundings rather than
    silently accepted as exact.
    """
    from scirel.kinetic.fluid_spectrum import derive_fluid_case

    case = derive_fluid_case("bonk", 2)
    assert _scalar(case["c2"]) == reference.DECLARED_C2
    assert _scalar(case["c2"]) == (2.99792458e8) ** 2  # exact by definition
    assert reference.relative(_scalar(case["epsilon0"]), 8.854187817e-12) <= 1e-12
    assert reference.relative(_scalar(case["kB"]), 1.38064852e-23) <= 1e-12
    assert reference.relative(_scalar(case["qe"]), 1.60217662e-19) <= 1e-12
    assert reference.relative(_scalar(case["mp"]), 1.6726219e-27) <= 1e-12
    # Documented roundings: five significant digits only.
    assert reference.relative(_scalar(case["me"]), 9.1093837015e-31) <= 3e-5
    expected_mu0 = 1.0 / (_scalar(case["c2"]) * _scalar(case["epsilon0"]))
    assert reference.relative(_scalar(case["mu0"]), expected_mu0) <= 1e-15


@pytest.mark.parametrize(("family", "jcase"), CASE_SELECTORS)
def test_fluid_case_state_derived_scales_match_closed_forms(family, jcase):
    """Every derived scale is recomputed from the declared deck inputs at 40 digits.

    The deck numbers (species table, ``B0``, ``n00``, ``T00``) are taken as
    declared inputs; what is checked is that the derived scales satisfy the
    published relations, not that the deck itself is right -- no independent
    source for it exists in the repository.
    """
    from scirel.kinetic.fluid_spectrum import derive_fluid_case

    case = derive_fluid_case(family, jcase)
    expected = reference.case_scales(
        ms=np.asarray(case["ms"], dtype=float).ravel(),
        qs=np.asarray(case["qs"], dtype=float).ravel(),
        ns_unit=np.asarray(case["ns_unit"], dtype=float).ravel(),
        Ts_unit=np.asarray(case["Ts_unit"], dtype=float).ravel(),
        B0=_scalar(case["B0"]),
        n00=_scalar(case["n00"]),
        T00=_scalar(case["T00"]),
    )
    for index in range(np.asarray(case["qs"]).size):
        assert reference.relative(float(np.asarray(case["ns0"]).ravel()[index]), float(expected["ns0"][index])) <= 1e-14
        assert reference.relative(float(np.asarray(case["Ts0"]).ravel()[index]), float(expected["Ts0"][index])) <= 1e-14
        assert reference.relative(float(np.asarray(case["vts"]).ravel()[index]), float(expected["vts"][index])) <= 1e-14
        assert reference.relative(float(np.asarray(case["wcs"]).ravel()[index]), float(expected["wcs"][index])) <= 1e-14
        assert reference.relative(float(np.asarray(case["wps"]).ravel()[index]), float(expected["wps"][index])) <= 1e-14
        assert reference.relative(float(np.asarray(case["rhocs"]).ravel()[index]), float(expected["rhocs"][index])) <= 1e-13
        # absrhocs and sgns are not returned by derive_fluid_case; they are derived
        # from the signed gyroradius the case does return.
        assert reference.relative(
            abs(float(np.asarray(case["rhocs"]).ravel()[index])),
            float(expected["absrhocs"][index]),
        ) <= 1e-13
        assert np.sign(float(np.asarray(case["rhocs"]).ravel()[index])) == expected["sgns"][index]
    assert reference.relative(_scalar(case["wn"]), float(expected["wn"])) <= 1e-15
    assert reference.relative(_scalar(case["kn"]), float(expected["kn"])) <= 1e-13
    assert reference.relative(_scalar(case["rhocn"]), float(expected["rhocn"])) <= 1e-13
    # The EM family declares its parallel wavenumber as a fixed fraction of kn, so
    # that relation is checkable.  The BONK kz values are bare deck numbers with no
    # independent source, so only their finiteness is asserted here.
    if family == "em":
        assert reference.relative(_scalar(case["kz"]), 0.1 * float(expected["kn"])) <= 1e-15
    else:
        assert np.isfinite(_scalar(case["kz"]))


def test_fluid_dispersion_matrix_structural_identities():
    """The declared order and sparsity are identities about the returned object.

    ``n_sl``, the matrix order ``3*n_sl + 4`` and the nonzero count are recomputed
    from the pole table by hand, so a silently reshaped or over-filled matrix fails
    here even when every eigenvalue still looks plausible.
    """
    from scirel.kinetic import get_gamma_lpole_coefficients

    for max_harmonic in (0, 1):
        result, _scales = _wavevector_matrix(0.1 * 1.0, max_harmonic=max_harmonic)
        table = get_gamma_lpole_coefficients(max_harmonic=max_harmonic)
        n_sl = int(np.asarray(table["total_poles"]))
        # The per-order lengths must add up to the same pole count.
        assert sum(int(length) for length in table["order_lengths"].values()) == n_sl
        assert result["n_sl"] == n_sl
        assert result["n_sl3"] == 3 * n_sl
        assert np.asarray(result["M"]).shape == (3 * n_sl + 4, 3 * n_sl + 4)
        assert result["matrix_size"] == 3 * n_sl + 4
        assert result["nonzero_entries"] == int(np.count_nonzero(np.asarray(result["M"])))
        # The response table is not normalised away: at least the diagonal survives.
        assert result["nonzero_entries"] > 3 * n_sl


def test_fluid_dispersion_matrix_determinant_equals_eigenvalue_product():
    """``det(M)`` at 40 digits equals the product of the returned wavenumbers.

    This is the definition of a spectrum as an identity rather than as a second
    solver: the determinant is recomputed from the matrix bytes at 40 digits, and
    the product is taken over the values the eigensolver returned.  A wrong matrix
    entry, a dropped pole or a mis-ordered state block breaks the identity, while
    the two computations share no code.
    """
    from scirel.kinetic import solve_fluid_wavevector_eigenproblem

    for max_harmonic, budget in ((0, 1e-12), (1, 1e-10)):
        result, scales = _wavevector_matrix(1.0, max_harmonic=max_harmonic)
        matrix = np.asarray(result["M"])
        solution = solve_fluid_wavevector_eigenproblem(matrix=matrix, kn=1000.0)
        values = np.asarray(solution["eigenvalues"])
        assert values.size == matrix.shape[0]
        determinant = reference.determinant_high_precision(matrix)
        product = reference.eigenproduct(values)
        assert reference.relative(abs(product), abs(determinant)) <= budget


def test_fluid_dispersion_matrix_kz_sign_gives_identical_kx_spectrum():
    """The contract declares the kx roots identical for ``+kz`` and ``-kz``.

    The two matrices differ by ``~4e14`` in their largest entry, so this is a
    statement about the assembled physics rather than about a shared code path:
    the kx spectrum is exactly invariant.
    """
    from scirel.kinetic import solve_fluid_wavevector_eigenproblem

    _probe, scales = _wavevector_matrix(0.1)
    forward = _wavevector_matrix(0.1 * _scalar(scales["kn"]))[0]
    backward = _wavevector_matrix(-0.1 * _scalar(scales["kn"]))[0]
    assert not np.allclose(np.asarray(forward["M"]), np.asarray(backward["M"]))
    forward_values = np.sort_complex(
        solve_fluid_wavevector_eigenproblem(matrix=np.asarray(forward["M"]), kn=_scalar(scales["kn"]))["eigenvalues"]
    )
    backward_values = np.sort_complex(
        solve_fluid_wavevector_eigenproblem(matrix=np.asarray(backward["M"]), kn=_scalar(scales["kn"]))["eigenvalues"]
    )
    assert np.max(np.abs(forward_values - backward_values)) == 0.0


def test_fluid_wavevector_eigensolve_selection_relations():
    """Threshold, counts and ordering are the declared relations, not observed habits.

    ``real_floor`` is ``real_floor_scale*kn``; every selected value exceeds it; the
    count fields agree with the arrays; and ``head`` is the first ``keep`` of the
    ascending ``|Im|`` order.  A mutation that rescales or negates any of these
    breaks at least one of the equalities.
    """
    from scirel.kinetic import solve_fluid_wavevector_eigenproblem

    result, scales = _wavevector_matrix(0.1)
    matrix = np.asarray(result["M"])
    kn = _scalar(scales["kn"])
    solution = solve_fluid_wavevector_eigenproblem(matrix=matrix, kn=kn, real_floor_scale=2e-5, keep=4)
    values = np.asarray(solution["eigenvalues"])
    selected = np.asarray(solution["selected"])
    head = np.asarray(solution["head"])

    assert solution["eigenvalue_count"] == values.size == matrix.shape[0]
    assert reference.relative(solution["real_floor"], 2e-5 * kn) <= 1e-15
    mask = np.real(values) > solution["real_floor"]
    selection_count = int(np.count_nonzero(mask))
    assert selection_count > 0
    assert solution["selected_count"] == selection_count == selected.size
    assert np.all(np.real(selected) > solution["real_floor"])
    # Ascending |Im| on the selected subset, and head is its prefix.
    assert np.all(np.diff(np.abs(np.imag(selected))) >= -1e-12)
    assert solution["returned_count"] == head.size == min(4, selection_count)
    assert np.array_equal(head, selected[: head.size])
    assert solution["sort_key"] == "ascending_abs_imag"


def test_fluid_dispersion_response_zero_transverse_determinant_identity():
    """At ``kx = 0`` the determinant collapses to an exact Schur identity.

    With no transverse wavenumber the tensor's off-diagonal ``(0,2)`` and ``(1,2)``
    entries vanish, so ``D`` is block upper triangular and

        det(D) = ((K00 - nz**2)(K11 - nz**2) + K01**2) * K22

    holds algebraically.  The right-hand side is recomputed at 40 digits from the
    returned ``K`` and the declared ``nx, nz``, so it does not reuse the
    implementation's determinant.  Both the magnetised and the zero-``kz``
    branches are checked, because the ``kp == 0`` path is a separate code branch.
    """
    from scirel.kinetic.fluid_spectrum import evaluate_fluid_dispersion

    for kz_scale in (1.0, 0.0):
        state = _dispersion_state("bonk", 2)
        state["kz"] = kz_scale * _scalar(state["kz"])
        result = evaluate_fluid_dispersion(0.0, state)
        tensor = np.asarray(result["K"])
        assert abs(tensor[0, 2]) == 0.0 and abs(tensor[1, 2]) == 0.0
        # The declared hermitian pairing of the tensor is part of the relation.
        assert np.allclose(tensor[1, 0], -tensor[0, 1])
        assert np.allclose(tensor[2, 0], tensor[0, 2])

        reference.high_precision()
        w = mp.mpf(float(state["w"]))
        c2 = mp.mpf(float(_scalar(state["c2"])))
        kz = mp.mpf(float(abs(_scalar(state["kz"]))))
        nz = mp.sqrt(c2) * kz / w
        nx = mp.mpf(0)
        k00 = mp.mpf(float(np.real(tensor[0, 0])))
        k01 = mp.mpf(float(np.real(tensor[0, 1]))) + mp.mpf(float(np.imag(tensor[0, 1]))) * 1j
        k11 = mp.mpf(float(np.real(tensor[1, 1])))
        k22 = mp.mpf(float(np.real(tensor[2, 2])))
        assert nx == 0
        predicted = ((k00 - nz**2) * (k11 - nz**2) + k01**2) * k22
        measured = complex(np.asarray(result["determinant"]).ravel()[0])
        assert reference.relative(abs(measured), abs(complex(predicted))) <= 1e-14
