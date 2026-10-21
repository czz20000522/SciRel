"""External PDRF oracle regression for the two-species fluid frequency pencil.

The expected real frequencies are the 14-mode PDRF/Octave oracle values for the
``complex-field-to-pdrf`` case (B0=0.002377416400457883 T, electron/proton
n=8.7e18 m^-3, csz=csp=4.631e5/9.360e3 m/s).  Only real parts are asserted:
the external truth records an imaginary-part roundoff floor of order
1e-5..1e-4 s^-1, which is not a physical growth-rate claim.
"""
import math

import numpy as np
import pytest

from scirel.kinetic.dispersion._fluid_parallel import fluid_frequency_pencil, fluid_state_scales
from scirel.kinetic.dispersion.multifluid import (
    fluid_equilibrium_si,
    fluid_solve_state,
    scan_fluid_corrected,
)
from scirel.kinetic.spectral_evolution import solve_temporal_spectrum


_TRUTH = {
    (0.05, 0.05): np.array([
        166655333249.04752, 166446242952.5425, 166237416231.889,
        1486.2539412705669, 878.8005821820403, 597.6013876329414,
        4.440997289938538e-19, -3.132517573933501e-17,
        -597.6013876329416, -878.8005821820401, -1486.2539412705664,
        -166237416231.88882, -166446242952.54236, -166655333249.04733,
    ]),
    (0.05, 0.15): np.array([
        166655338635.09497, 166446242952.55533, 166237421645.03397,
        2965.9534294648743, 2635.9220343555785, 2009.211002528863,
        4.4403607431133714e-17, 5.924791847562319e-21,
        -2009.2110025288616, -2635.922034355578, -2965.9534294648715,
        -166237421645.03397, -166446242952.55527, -166655338635.09506,
    ]),
    (0.15, 0.05): np.array([
        166655335942.10403, 166446248352.12625, 166237418938.44174,
        3537.6849760122122, 878.8370981420053, 561.3741208598624,
        -9.918466303307448e-17, -1.0112753177030305e-16,
        -561.374120859862, -878.8370981420053, -3537.684976012212,
        -166237418938.44177, -166446248352.12607, -166655335942.10385,
    ]),
    (0.15, 0.15): np.array([
        166655341328.22086, 166446248352.13934, 166237424351.51648,
        4458.944532682346, 2636.502779513612, 1792.6617714870615,
        8.062124357013837e-17, -1.1437396599777925e-16,
        -1792.6617714870608, -2636.5027795136125, -4458.944532682342,
        -166237424351.5167, -166446248352.13947, -166655341328.2211,
    ]),
}


def _state():
    electron = -1.602176634e-19
    proton = 1.602176634e-19
    deck = np.array([
        [electron, 9.1093837e-31, 8.7e18, 0.0, 0.0, 0.0, 4.631e5, 4.631e5, 0.0, 0.0],
        [proton, 1.6726e-27, 8.7e18, 0.0, 0.0, 0.0, 9.360e3, 9.360e3, 0.0, 0.0],
    ], dtype=float)
    return fluid_equilibrium_si(deck, B0=0.002377416400457883)


@pytest.mark.parametrize("kx,kz", list(_TRUTH))
def test_external_pdrf_two_species_spectrum_keeps_all_14_modes(kx, kz):
    """Regression: the identity-inertia pencil must not duplicate or drop modes."""
    result = fluid_solve_state(_state(), kx, kz)
    actual = result["w1"].real
    expected = _TRUTH[(kx, kz)]
    assert actual.shape == (14,)
    np.testing.assert_allclose(actual, expected, rtol=2e-9, atol=1e-9)
    assert np.max(result["componentwise_backward_errors"]) <= 1e-10
    assert result["zero_structure"]["geometric_multiplicity"] == 2
    assert result["zero_structure"]["algebraic_multiplicity"] == 2
    assert not result["zero_structure"]["complete_eigenbasis_not_claimed"]


@pytest.mark.parametrize("kx,kz", list(_TRUTH))
def test_multifluid_scan_point_matches_external_pdrf_truth(kx, kz):
    """The scan wrapper must not alter the per-point external-truth spectrum."""
    state = _state()
    kn = math.hypot(kx, kz)
    theta = math.atan2(kx, kz)
    result = scan_fluid_corrected(dict(
        state=state,
        method=1,
        grid_controls={"wave_number": kn, "angle": theta},
    ))
    np.testing.assert_allclose(
        result["w1"][0, 0].real, _TRUTH[(kx, kz)], rtol=2e-9, atol=1e-9
    )


@pytest.mark.parametrize("kx,kz", list(_TRUTH))
@pytest.mark.parametrize("oldmethod", [1, 2])
def test_spectral_temporal_spectrum_matches_external_pdrf_truth(kx, kz, oldmethod):
    """Both documented temporal-spectrum paths retain the same low-frequency modes."""
    state = _state()
    pencil = fluid_frequency_pencil(state, kx, kz)
    scales = fluid_state_scales(state)
    result = solve_temporal_spectrum(
        pencil["M"], pencil["A"], scales=scales, oldmethod=oldmethod
    )
    np.testing.assert_allclose(
        result["w1"].real, _TRUTH[(kx, kz)], rtol=2e-9, atol=1e-9
    )
