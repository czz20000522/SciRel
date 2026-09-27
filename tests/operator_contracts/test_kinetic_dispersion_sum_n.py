"""Scientific contract for the Maxwellian harmonic-sum dispersion tensor."""

import numpy as np
import pytest

from scirel.kinetic import evaluate_kinetic_dispersion_sum


KB = 1.38064852e-23
QE = 1.60217662e-19
ME = 9.1094e-31
MP = 1.6726219e-27

CASE_SINGLE = dict(
    B0=1.0,
    qs=np.array([-QE]),
    ms=np.array([ME]),
    ns0=np.array([6.075e19]),
    Ts0=np.array([1e3 * 1.6022e-19 / KB]),
    kz=1326.1942478795652,
)
CASE_PAIR = dict(
    B0=6.0,
    qs=np.array([-QE, QE]),
    ms=np.array([ME, 2 * MP]),
    ns0=np.array([2e20, 2e20]),
    Ts0=np.array([4e3 * 1.6022e-19 / KB] * 2),
    kz=65.65372832698084,
)


@pytest.mark.parametrize(
    "case,omega,kx,expected",
    [
        (CASE_SINGLE, 175881684853.009, 13261.94247879565, 1184249.3244493124 + 4322451.2861608062j),
        (CASE_PAIR, 718412490.59336126, 656.53728326980831, 13174325513551.057 + 8828415003972.5879j),
    ],
)
def test_saved_fluidbw_source_determinants(case, omega, kx, expected):
    """Two source-oracle points cover one and two species at lmx=5."""
    out = evaluate_kinetic_dispersion_sum(**case, f=omega / (2 * np.pi), kx=kx)
    assert abs(out["determinant"] - expected) <= 1e-13 * abs(expected)
    assert out["lmx"] == 5
    assert out["omega"] == pytest.approx(omega, rel=1e-15)


def test_saved_fluidbw_tensor_and_maxwell_terms():
    out = evaluate_kinetic_dispersion_sum(
        **CASE_SINGLE, f=175881684853.009 / (2 * np.pi), kx=13261.94247879565, lmx=15
    )
    expected = np.array([
        [1.323438756569723 + 16.286340462141965j, 3.9118767638180003 - 1.4240037188940751j, 12.966828375111902 + 1.3366116200711915e-15j],
        [-3.9118767638180003 + 1.4240037188940751j, -2.1714461943578733 + 8.4625869345059641j, 1.35575390846217e-16 + 3.234387565697225j],
        [12.966828375111902 + 1.3366116200711915e-15j, -1.35575390846217e-16 - 3.234387565697225j, -2.426333691743821 - 2.4019273601539881e-14j],
    ])
    np.testing.assert_allclose(out["K"], expected, rtol=0, atol=1e-13 * np.max(np.abs(expected)))
    k, d = out["K"], out["D"]
    nx, nz = out["nx"], out["nz"]
    assert k[1, 0] == pytest.approx(-k[0, 1], rel=1e-15)
    assert k[2, 1] == pytest.approx(-k[1, 2], rel=1e-15)
    assert k[2, 0] == pytest.approx(k[0, 2], rel=1e-15)
    assert d[0, 0] == pytest.approx(k[0, 0] - nz**2, rel=1e-15)
    assert d[1, 1] == pytest.approx(k[1, 1] - nx**2 - nz**2, rel=1e-15)
    assert d[2, 2] == pytest.approx(k[2, 2] - nx**2, rel=1e-15)
    assert d[0, 2] == pytest.approx(k[0, 2] + nx * nz, rel=1e-15)
    assert out["determinant"] == pytest.approx(np.linalg.det(d), rel=1e-15)


@pytest.mark.parametrize(
    "change",
    [
        {"B0": 0.0}, {"B0": np.inf}, {"f": 0.0}, {"f": np.nan},
        {"kz": 0.0}, {"kx": 0.0}, {"kx": np.inf}, {"lmx": -1},
        {"lmx": 1.5}, {"lmx": True}, {"qs": [0.0]},
        {"ms": [-1.0]}, {"ns0": [0.0]}, {"Ts0": [np.nan]}, {"qs": [True]},
    ],
)
def test_invalid_inputs_fail_closed(change):
    args = dict(CASE_SINGLE, f=175881684853.009 / (2 * np.pi), kx=13261.94247879565)
    args.update(change)
    with pytest.raises(ValueError):
        evaluate_kinetic_dispersion_sum(**args)


def test_underflowed_plasma_frequency_is_rejected():
    args = dict(CASE_SINGLE, ns0=[1e-320], f=175881684853.009 / (2 * np.pi), kx=13261.94247879565)
    with pytest.raises(ValueError, match="derived kinetic scales"):
        evaluate_kinetic_dispersion_sum(**args)
