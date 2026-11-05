"""Composition contracts for the three fluid-dispersion paths."""

import numpy as np
import pytest

from scirel.kinetic import (
    evaluate_kinetic_dispersion_relation,
    scan_fluid_wavevectors,
    scan_kinetic_wavevectors,
)


CASE = dict(
    ms=[9.1094e-31],
    qs=[-1.60217662e-19],
    ns_unit=[1.0],
    Ts_unit=[1.0],
    B0=1.0,
    n00=6.075e19,
    T00=1000.0,
)
WN = 175881684853.009
KN = 13261.94247879565


def test_kinetic_relation_returns_both_source_paths():
    result = evaluate_kinetic_dispersion_relation(
        **CASE, omega_frac=1.0, kz=1326.1942478795652, kx_frac=1.0
    )
    assert result["omega"] == pytest.approx(WN)
    assert result["kx"] == pytest.approx(KN)
    assert result["determinant_sum_n"] == pytest.approx(
        1184249.3244493124 + 4322451.2861608062j, rel=1e-12
    )
    assert result["determinant_ronnmark"] == pytest.approx(
        1184258.061758124 + 4322544.0839688079j, rel=1e-12
    )


@pytest.mark.parametrize(
    "omega,expected_sum,expected_ronnmark",
    [
        (
            431047494.35601676,
            84156144001125.656 + 29822940983252.656j,
            84154917089965.141 + 29822444270111.691j,
        ),
        (
            718412490.59336126,
            13174325513551.057 + 8828415003972.5879j,
            13173663914380.654 + 8828066693749.1387j,
        ),
    ],
)
def test_two_species_relation_matches_both_frozen_source_paths(
    omega, expected_sum, expected_ronnmark
):
    case = dict(
        ms=[9.1094e-31, 2 * 1.6726219e-27],
        qs=[-1.60217662e-19, 1.60217662e-19],
        ns_unit=[1.0, 1.0],
        Ts_unit=[1.0, 1.0],
        B0=6.0,
        n00=2e20,
        T00=4000.0,
    )
    result = evaluate_kinetic_dispersion_relation(
        **case,
        omega_frac=omega / 287364996.2373445,
        kz=65.65372832698084,
        kx_frac=1.0,
    )
    assert result["determinant_sum_n"] == pytest.approx(expected_sum, rel=1e-12)
    assert result["determinant_ronnmark"] == pytest.approx(expected_ronnmark, rel=1e-12)
    assert len(result["branches"]) == 16


def test_fluid_scan_source_branch_and_internal_axis():
    result = scan_fluid_wavevectors(
        **CASE,
        omega_scale=0.5,
        omega_step=0.05,
        omega_stop=0.5,
        kz_scale=0.1,
        max_harmonic=6,
        j_order=8,
    )
    assert result["count"] == 1
    assert result["omegas"][0] == 0.5 * WN
    assert result["matrix_sizes"][0] == (490, 77092)
    np.testing.assert_allclose(
        result["kx_head"][0],
        [
            905.1790141262235 + 1098.4405252549827j,
            905.3284546850839 - 1099.1401577361607j,
            17460.574000679004 - 3076.8115609398164j,
            17460.57399242396 + 3076.811575501693j,
            17460.769014362882 - 3078.808722147245j,
        ],
        rtol=0,
        atol=1e-4,
    )


def test_kinetic_scan_keeps_absolute_zero_kz_and_fixed_seed():
    result = scan_kinetic_wavevectors(
        **CASE,
        kz=0.0,
        omega_scale=0.11,
        omega_step=0.05,
        omega_stop=0.11,
    )
    assert result["count"] == 1
    assert result["kx_start"] == 0.6 * KN
    assert result["kz"] == 0.0
    assert result["roots"][0] == pytest.approx(
        -0.1724798740276431 - 0.12372615593987332j, rel=1e-9, abs=1e-9
    )
