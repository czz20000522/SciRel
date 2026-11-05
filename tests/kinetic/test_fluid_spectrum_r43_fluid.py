"""Source-bounded pole, fluid-matrix, and eigenbranch contracts."""

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_fluid_dispersion_matrix,
    derive_species_equilibrium_scales,
    get_gamma_lpole_coefficients,
    get_z_pole_coefficients,
    solve_fluid_wavevector_eigenproblem,
)


def test_source_poles_and_lpole_ordering():
    z = get_z_pole_coefficients(j_order=8)
    assert z["bzj"][0] == -0.017340112270401 - 0.046306439626294j
    assert z["czj"][0] == 2.237687725134293 - 1.625941024120362j
    np.testing.assert_array_equal(z["bzj"][4:], np.conj(z["bzj"][:4]))
    np.testing.assert_array_equal(z["czj"][4:], -np.conj(z["czj"][:4]))
    l = get_gamma_lpole_coefficients(max_harmonic=7)
    assert l["order_lengths"] == {1: 12, 2: 18, 3: 20, 4: 22, 5: 28, 6: 30, 7: 32, 8: 34}
    assert l["residues"][1][0] == -0.0326560281967822 + 0.0312590495572379j
    with pytest.raises(ValueError):
        get_gamma_lpole_coefficients(max_harmonic=8)


@pytest.mark.parametrize("j_order", [8.5, 12.5, True])
def test_z_pole_order_must_be_an_integer(j_order):
    with pytest.raises(ValueError, match="j_order"):
        get_z_pole_coefficients(j_order=j_order)


@pytest.mark.parametrize("max_harmonic", [6.5, True])
def test_lpole_harmonic_limit_must_be_an_integer(max_harmonic):
    with pytest.raises(ValueError, match="max_harmonic"):
        get_gamma_lpole_coefficients(max_harmonic=max_harmonic)


def test_fluid_matrix_block_and_eigen_selection():
    scales = derive_species_equilibrium_scales(
        ms=[9.1094e-31],
        qs=[-1.60217662e-19],
        ns_unit=[1.0],
        Ts_unit=[1.0],
        B0=1.0,
        n00=6.075e19,
        T00=1000.0,
    )
    l = get_gamma_lpole_coefficients(max_harmonic=6)
    z = get_z_pole_coefficients(j_order=8)
    omega = 0.5 * scales["wn"]
    kz = 0.1 * scales["kn"]
    out = assemble_fluid_dispersion_matrix(
        omega=omega,
        kz=kz,
        c2=scales["c2"],
        epsilon0=scales["epsilon0"],
        wps2=scales["wps2"],
        wcs=scales["wcs"],
        vts=scales["vts"],
        rhocs=scales["rhocs"],
        sgns=scales["sgns"],
        absrhocs=scales["absrhocs"],
        cn_residues=l["residues"],
        cn_poles=l["poles"],
        order_lengths=l["order_lengths"],
        bzj=z["bzj"],
        czj=z["czj"],
        max_harmonic=6,
        n_species=1,
    )
    assert out["matrix_size"] == 3 * sum(l["order_lengths"].values()) + 4
    m = out["M"]
    n = out["n_sl3"]
    assert m[n, n + 3] == omega
    assert m[n + 2, n + 1] == -omega / scales["c2"]
    assert m[0, 0] == l["poles"][1][0] / scales["absrhocs"][0]
    solved = solve_fluid_wavevector_eigenproblem(matrix=m, kn=scales["kn"])
    assert solved["head"].size == 5
    np.testing.assert_array_equal(solved["head"], solved["selected"][:5])
    assert np.all(np.diff(np.abs(solved["selected"].imag)) >= 0)


def test_fluid_matrix_rejects_nonfinite_resonance():
    scales = derive_species_equilibrium_scales(
        ms=[9.1094e-31],
        qs=[-1.60217662e-19],
        ns_unit=[1.0],
        Ts_unit=[1.0],
        B0=1.0,
        n00=6.075e19,
        T00=1000.0,
    )
    l = get_gamma_lpole_coefficients(max_harmonic=0)
    z = get_z_pole_coefficients(j_order=8)
    with pytest.raises(ValueError, match="finite"):
        assemble_fluid_dispersion_matrix(
            omega=abs(scales["wcs"][0]),
            kz=0.0,
            c2=scales["c2"],
            epsilon0=scales["epsilon0"],
            wps2=scales["wps2"],
            wcs=scales["wcs"],
            vts=scales["vts"],
            rhocs=scales["rhocs"],
            sgns=scales["sgns"],
            absrhocs=scales["absrhocs"],
            cn_residues=l["residues"],
            cn_poles=l["poles"],
            order_lengths=l["order_lengths"],
            bzj=z["bzj"],
            czj=z["czj"],
            max_harmonic=0,
            n_species=1,
        )


def test_eigen_floor_rejects_nonpropagating_modes():
    roots = np.array([0.1 + 3j, -1 + 0j, 0.2 + 1j])
    out = solve_fluid_wavevector_eigenproblem(matrix=np.diag(roots), kn=1.0)
    assert out["selected_count"] == 2
    np.testing.assert_array_equal(out["head"], [0.2 + 1j, 0.1 + 3j])


@pytest.mark.parametrize("keep", [1.5, True])
def test_eigen_branch_count_must_be_an_integer(keep):
    with pytest.raises(ValueError, match="keep"):
        solve_fluid_wavevector_eigenproblem(matrix=np.eye(2), kn=1.0, keep=keep)


@pytest.mark.parametrize("change", [{"n_species": 1.5}, {"max_harmonic": 0.5}])
def test_fluid_matrix_rejects_fractional_dimensions(change):
    args = dict(
        omega=1.0,
        kz=1.0,
        c2=1.0,
        epsilon0=1.0,
        wps2=[],
        wcs=[],
        vts=[],
        rhocs=[],
        sgns=[],
        absrhocs=[],
        cn_residues={},
        cn_poles={},
        order_lengths={},
        bzj=[],
        czj=[],
        max_harmonic=0,
        n_species=1,
    )
    args.update(change)
    with pytest.raises(ValueError, match="integer"):
        assemble_fluid_dispersion_matrix(**args)


@pytest.mark.parametrize(
    "change",
    [
        {"order_lengths": {1: 12.5}},
        {"cn_residues": {1.5: np.ones(12, dtype=complex)}},
    ],
)
def test_fluid_matrix_rejects_fractional_coefficient_indices(change):
    scales = derive_species_equilibrium_scales(
        ms=[9.1094e-31],
        qs=[-1.60217662e-19],
        ns_unit=[1.0],
        Ts_unit=[1.0],
        B0=1.0,
        n00=6.075e19,
        T00=1000.0,
    )
    l = get_gamma_lpole_coefficients(max_harmonic=0)
    z = get_z_pole_coefficients(j_order=8)
    args = dict(
        omega=scales["wn"],
        kz=0.1 * scales["kn"],
        c2=scales["c2"],
        epsilon0=scales["epsilon0"],
        wps2=scales["wps2"],
        wcs=scales["wcs"],
        vts=scales["vts"],
        rhocs=scales["rhocs"],
        sgns=scales["sgns"],
        absrhocs=scales["absrhocs"],
        cn_residues=l["residues"],
        cn_poles=l["poles"],
        order_lengths=l["order_lengths"],
        bzj=z["bzj"],
        czj=z["czj"],
        max_harmonic=0,
        n_species=1,
    )
    args.update(change)
    with pytest.raises(ValueError, match="integer"):
        assemble_fluid_dispersion_matrix(**args)
