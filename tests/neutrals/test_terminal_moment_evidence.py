"""Independent evidence for the five terminal moment reductions.

Assets: ``scirel.neutrals.terminal-flux-velocity-reduction``,
``scirel.neutrals.terminal-pressure-temperature-reduction``,
``scirel.neutrals.terminal-heat-flux-reduction``,
``scirel.neutrals.terminal-energy-transfer-reduction``,
``scirel.neutrals.terminal-ion-state-reduction``.

These contracts are the terminal closure of the neutral transport equation: a
discrete velocity-space integral of a caller-owned distribution (and, for the
transfer, of a signed collision RHS) into density, flux, pressure, temperature,
heat flux and transfer rates.  A normal example against the same formula proves
nothing, so the evidence is built from moment identities that must hold for any
correct reduction plus exact rational recomputation of the declared sums:

1. **Exact rational reduction oracle.**  Every integral is recomputed from the
   exact binary64 inputs with :class:`fractions.Fraction` and rounded once.  That
   separates the declared measure (``weight * (slice @ widths)`` followed by the
   radial sum), the per-cell formulas and the unit factors from floating-point
   accumulation.
2. **Physical moment identities, asserted as equalities where binary64 allows.**
   A distribution symmetric in the axial velocity carries exactly zero mean
   velocity and exactly zero heat flux; a distribution with all mass at one axial
   node carries mean velocity ``vth * vx``; doubling the thermal speed quadruples
   the pressure and temperature; axial velocity reversal flips the heat flux.
3. **Second-moment temperature closure.**  ``T`` is the second moment
   ``(1/3) m <v_rand^2> / q``; a hand-built anisotropic shell with a known mean
   square random speed fixes it independently of the reduction's own expression
   tree, and ``P = n T`` is required to hold.
4. **Removed bulk energy.**  For a loss proportional to the distribution itself,
   the centered momentum vanishes exactly and the total transfer exceeds the
   thermal transfer by exactly ``0.5 m U^2 J`` of bulk kinetic energy.  That is a
   physical statement about what a particle sink carries away, not a rearrangement
   of the implementation's expression.
5. **Steady-state ionization balance and the rate-table index convention.**  The
   ion-state reduction is checked against production = loss at the returned
   state, against the complementarity ``T_ion/T_i + nu_den/(nu_ex + nu_den) = 1``,
   and against a discriminator that changes the first seven rate-table columns
   (which the contract says are unread) and the four columns it says are read.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset.

Budgets, fixed before measurement:

* sums of ``n`` terms: ``(n + 4) * eps * sum_i |term_i|``.  A top-down reduction
  of ``n`` terms performs ``O(n)`` roundings bounded by ``eps`` times the running
  magnitude, which is at most the sum of absolute terms; ``n + 4`` leaves room for
  the per-cell products and divisions without turning the check into a rubber
  stamp.
* ``P = n T`` and the balance identities below: ``8 * eps * scale`` (one product,
  one division and the accumulation slack).
* exact-equality claims: only for power-of-two scalings and for sums whose terms
  cancel pairwise exactly, where binary64 arithmetic is exact.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps
M_H = 1.6726231e-27
Q = 1.602177e-19

VR = np.array([1.0, 2.0])
VX = np.array([-1.0, 0.0, 2.0])
WEIGHT = np.array([1.0, 2.0])
WIDTHS = np.array([0.5, 0.25, 0.25])
DISTRIBUTION = np.array(
    [
        [[1.0, 2.0], [0.5, 0.0], [3.0, 1.0]],
        [[0.0, 1.0], [2.0, 1.0], [0.5, 2.0]],
    ]
)
VTH = 5000.0
MASS_RATIO = 1.0


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _integral(field, weight, widths):
    """Exact per-slice integral of a (nvr, nvx, nx) field over weight * widths."""
    nvr, nvx, nx = field.shape
    out = []
    for k in range(nx):
        total = Fraction(0)
        for i in range(nvr):
            for j in range(nvx):
                total += _frac(field[i, j, k]) * _frac(weight[i]) * _frac(widths[j])
        out.append(total)
    return out


def _scale(*arrays):
    """sum of elementwise absolute magnitudes, broadcast over the same shape."""
    total = 0.0
    for array in arrays:
        total += float(np.max(np.abs(array)))
    return total


def _budget(terms, scale, extra=4):
    """(terms + extra) * eps * scale."""
    return (terms + extra) * EPS * max(scale, 1.0)


# --------------------------------------------------------------------------- #
# terminal-flux-velocity-reduction
# --------------------------------------------------------------------------- #


def test_flux_velocity_matches_the_exact_rational_reduction():
    """Evidence 1: density, flux and the flux/density mean velocity."""
    result = N.reduce_terminal_molecular_flux_velocity(VX, VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    density = _integral(DISTRIBUTION, WEIGHT, WIDTHS)
    flux = _integral(DISTRIBUTION * VX[None, :, None], WEIGHT, WIDTHS)
    expected_density = np.array([float(value) for value in density])
    expected_flux = np.array([float(_frac(VTH) * value) for value in flux])
    scale = _scale(DISTRIBUTION) * float(np.sum(WEIGHT) * np.sum(WIDTHS))
    assert np.allclose(
        result["flux_profile_m2_s"], expected_flux, rtol=0.0, atol=_budget(6, scale * VTH)
    )
    assert np.all(result["mean_velocity_profile_m_s"] > 0.0)
    # The mean velocity is the flux divided by the density of the same integral.
    independent_mean = expected_flux / expected_density
    assert np.all(
        np.abs(result["mean_velocity_profile_m_s"] - independent_mean)
        <= _budget(8, float(np.max(np.abs(independent_mean))))
    )


def test_flux_velocity_zero_flow_and_galilean_shift():
    """Evidence 2: a symmetric distribution has zero mean flow; shifting moves it."""
    vx = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    widths = np.full(5, 0.5)
    symmetric = np.ones((2, 5, 1))
    zero = N.reduce_terminal_molecular_flux_velocity(vx, VTH, symmetric, WEIGHT, widths)
    # Pairwise-exact cancellation: the axial first moment is exactly zero.
    assert zero["flux_profile_m2_s"][0] == 0.0
    assert zero["mean_velocity_profile_m_s"][0] == 0.0
    # Shifting every axial node by +1 shifts the mean velocity by exactly vth.
    shifted = N.reduce_terminal_molecular_flux_velocity(vx + 1.0, VTH, symmetric, WEIGHT, widths)
    assert shifted["mean_velocity_profile_m_s"][0] == VTH


def test_flux_velocity_is_exactly_homogeneous_in_the_distribution():
    """Evidence 2: doubling the distribution doubles flux and leaves U unchanged."""
    base = N.reduce_terminal_molecular_flux_velocity(VX, VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    doubled = N.reduce_terminal_molecular_flux_velocity(VX, VTH, 2.0 * DISTRIBUTION, WEIGHT, WIDTHS)
    assert np.array_equal(doubled["flux_profile_m2_s"], 2.0 * base["flux_profile_m2_s"])
    assert np.allclose(
        doubled["mean_velocity_profile_m_s"], base["mean_velocity_profile_m_s"], rtol=0.0, atol=0.0
    )


def test_flux_velocity_allows_zero_cells_but_requires_positive_density():
    """Evidence 6: degenerate cells are accepted only where density stays positive."""
    zero_width = WIDTHS.copy()
    zero_width[1] = 0.0
    result = N.reduce_terminal_molecular_flux_velocity(VX, VTH, DISTRIBUTION, WEIGHT, zero_width)
    assert all(np.isfinite(value).all() for value in result.values())
    with pytest.raises(ValueError, match="strictly positive density"):
        N.reduce_terminal_molecular_flux_velocity(
            VX, VTH, np.zeros_like(DISTRIBUTION), WEIGHT, WIDTHS
        )


def test_flux_velocity_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.reduce_terminal_molecular_flux_velocity
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VX, 0.0, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VX, float("nan"), DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VX[:2], VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VX, VTH, DISTRIBUTION, -WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VX, VTH, np.full_like(DISTRIBUTION, -1.0), WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VX, VTH, DISTRIBUTION, WEIGHT, np.array([np.inf, 0.0, 0.0]))
    with pytest.raises(ValueError, match="real numeric"):
        call(VX, VTH, [[[True, 1.0]]], WEIGHT, WIDTHS)


# --------------------------------------------------------------------------- #
# terminal-pressure-temperature-reduction
# --------------------------------------------------------------------------- #


def _pressure_temperature(distribution=DISTRIBUTION, vth=VTH, mass_ratio=MASS_RATIO):
    """Call the pressure/temperature reduction with the shared fixtures."""
    return N.reduce_terminal_molecular_pressure_temperature(
        VR, VX, mass_ratio, vth, distribution, WEIGHT, WIDTHS
    )


def _second_moment(distribution, axial_mean_normalized):
    """Exact <vr^2 + (vx - U/vth)^2> and density for the shared mesh."""
    density = _integral(distribution, WEIGHT, WIDTHS)
    second = []
    for k in range(distribution.shape[2]):
        total = Fraction(0)
        for i in range(VR.size):
            for j in range(VX.size):
                random_squared = (
                    _frac(VR[i]) ** 2 + (_frac(VX[j]) - _frac(axial_mean_normalized[k])) ** 2
                )
                total += (
                    _frac(distribution[i, j, k])
                    * random_squared
                    * _frac(WEIGHT[i])
                    * _frac(WIDTHS[j])
                )
        second.append(total)
    return density, second


def test_pressure_and_temperature_are_the_second_moment_closure():
    """Evidence 3: T = (1/3) m <v_rand^2> / q, with P = n T."""
    result = _pressure_temperature()
    density = _integral(DISTRIBUTION, WEIGHT, WIDTHS)
    flux = _integral(DISTRIBUTION * VX[None, :, None], WEIGHT, WIDTHS)
    # U/vth is the axial first moment divided by the density; recover it exactly.
    normalized_mean = [f / n for f, n in zip(flux, density)]
    exact_density, second = _second_moment(DISTRIBUTION, normalized_mean)
    molecule_mass = 2 * _frac(MASS_RATIO) * _frac(M_H)
    expected_pressure = [
        float(molecule_mass * _frac(VTH) ** 2 * value / (3 * _frac(Q))) for value in second
    ]
    expected_temperature = [
        float(expect / density_value)
        for expect, density_value in zip(expected_pressure, exact_density)
    ]
    scale = float(np.max(np.abs(expected_pressure)))
    assert np.all(
        np.abs(result["pressure_profile_ev_m3"] - np.array(expected_pressure)) <= _budget(10, scale)
    )
    assert np.all(
        np.abs(result["temperature_profile_ev"] - np.array(expected_temperature))
        <= _budget(10, float(np.max(np.abs(expected_temperature))))
    )
    # P = n T on the returned values.
    assert np.allclose(
        result["pressure_profile_ev_m3"],
        result["temperature_profile_ev"] * np.array([float(v) for v in exact_density]),
        rtol=0.0,
        atol=_budget(8, scale),
    )


def test_pressure_and_temperature_scale_exactly_with_vth_squared_and_mass():
    """Evidence 3: doubling vth quadruples P and T; doubling the mass factor doubles them."""
    base = _pressure_temperature()
    faster = _pressure_temperature(vth=2.0 * VTH)
    heavier = _pressure_temperature(mass_ratio=2.0 * MASS_RATIO)
    assert np.array_equal(faster["pressure_profile_ev_m3"], 4.0 * base["pressure_profile_ev_m3"])
    assert np.array_equal(faster["temperature_profile_ev"], 4.0 * base["temperature_profile_ev"])
    assert np.array_equal(heavier["pressure_profile_ev_m3"], 2.0 * base["pressure_profile_ev_m3"])
    assert np.array_equal(heavier["temperature_profile_ev"], 2.0 * base["temperature_profile_ev"])


def test_pressure_of_an_anisotropic_shell_is_a_closed_form():
    """Evidence 3: a distribution living on one radial shell has a known T."""
    shell = np.zeros((2, 3, 1))
    shell[1, 1, 0] = 1.0  # vr = 2, vx = 0
    result = _pressure_temperature(distribution=shell)
    # <v_rand^2> = 4 at that node, and the discrete moment carries the radial
    # weight and the axial width: 1 * 4 * 2 * 0.25 = 2.
    expected_pressure = float(
        2 * _frac(MASS_RATIO) * _frac(M_H) * _frac(VTH) ** 2 * 2 / (3 * _frac(Q))
    )
    expected_density = 2.0 * 0.25
    assert abs(result["pressure_profile_ev_m3"][0] - expected_pressure) <= _budget(
        6, expected_pressure
    )
    assert result["temperature_profile_ev"][0] == pytest.approx(
        expected_pressure / expected_density, rel=8 * EPS
    )


def test_pressure_temperature_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.reduce_terminal_molecular_pressure_temperature
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR - 3.0, VX, MASS_RATIO, VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, 0.0, VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, -VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, VTH, DISTRIBUTION, WEIGHT, WIDTHS[:2])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, VTH, np.full_like(DISTRIBUTION, np.inf), WEIGHT, WIDTHS)
    poisoned = np.array(DISTRIBUTION, dtype=object)
    poisoned[0, 0, 0] = "a"
    with pytest.raises(ValueError, match="real numeric"):
        call(VR, VX, MASS_RATIO, VTH, poisoned, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="strictly positive density"):
        call(VR, VX, MASS_RATIO, VTH, np.zeros_like(DISTRIBUTION), WEIGHT, WIDTHS)


# --------------------------------------------------------------------------- #
# terminal-heat-flux-reduction
# --------------------------------------------------------------------------- #


def _heat_flux(distribution=DISTRIBUTION, vth=VTH, mass_ratio=MASS_RATIO):
    """Call the heat-flux reduction with the shared fixtures."""
    return N.reduce_terminal_molecular_heat_flux(
        VR, VX, mass_ratio, vth, distribution, WEIGHT, WIDTHS
    )


def test_heat_flux_matches_the_exact_rational_random_flux():
    """Evidence 1: 0.5 m vth^3 * integral of f * v_rand^2 * (vx - U/vth)."""
    result = _heat_flux()
    density = _integral(DISTRIBUTION, WEIGHT, WIDTHS)
    flux = _integral(DISTRIBUTION * VX[None, :, None], WEIGHT, WIDTHS)
    normalized_mean = [f / n for f, n in zip(flux, density)]
    expected = []
    for k in range(DISTRIBUTION.shape[2]):
        total = Fraction(0)
        for i in range(VR.size):
            for j in range(VX.size):
                random_squared = _frac(VR[i]) ** 2 + (_frac(VX[j]) - normalized_mean[k]) ** 2
                total += (
                    _frac(DISTRIBUTION[i, j, k])
                    * random_squared
                    * (_frac(VX[j]) - normalized_mean[k])
                    * _frac(WEIGHT[i])
                    * _frac(WIDTHS[j])
                )
        expected.append(0.5 * 2 * _frac(MASS_RATIO) * _frac(M_H) * _frac(VTH) ** 3 * total)
    expected = np.array([float(value) for value in expected])
    scale = float(np.max(np.abs(expected))) * 4
    assert np.all(np.abs(result["random_heat_flux_profile_w_m2"] - expected) <= _budget(12, scale))


def test_heat_flux_of_a_symmetric_distribution_at_rest_is_exactly_zero():
    """Evidence 2: no heat flux without flow and without skewness."""
    vx = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    widths = np.full(5, 0.5)
    symmetric = np.ones((2, 5, 2))
    result = N.reduce_terminal_molecular_heat_flux(
        VR, vx, MASS_RATIO, VTH, symmetric, WEIGHT, widths
    )
    assert np.array_equal(result["random_heat_flux_profile_w_m2"], np.zeros(2))
    assert np.array_equal(result["total_heat_flux_profile_w_m2"], np.zeros(2))


def test_heat_flux_reverses_sign_under_axial_velocity_reversal():
    """Evidence 2: q(vx) = -q(-vx) for a fixed distribution shape."""
    vx = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    widths = np.full(5, 0.25)
    rng = np.random.default_rng(503)
    distribution = rng.uniform(0.0, 2.0, size=(2, 5, 2))
    forward = N.reduce_terminal_molecular_heat_flux(
        VR, vx, MASS_RATIO, VTH, distribution, WEIGHT, widths
    )["random_heat_flux_profile_w_m2"]
    reversed_ = N.reduce_terminal_molecular_heat_flux(
        VR, vx, MASS_RATIO, VTH, distribution[:, ::-1, :], WEIGHT, widths
    )["random_heat_flux_profile_w_m2"]
    scale = float(np.max(np.abs(forward)))
    assert np.all(np.abs(reversed_ + forward) <= _budget(14, scale))
    # The reversal is not a no-op: the flux is actually nonzero here.
    assert scale > 0.0


def test_heat_flux_scales_with_the_cube_of_the_thermal_speed():
    """Evidence 2: doubling vth multiplies both heat-flux profiles by exactly 8."""
    base = _heat_flux()
    doubled = _heat_flux(vth=2.0 * VTH)
    assert np.array_equal(
        doubled["random_heat_flux_profile_w_m2"], 8.0 * base["random_heat_flux_profile_w_m2"]
    )
    assert np.array_equal(
        doubled["total_heat_flux_profile_w_m2"], 8.0 * base["total_heat_flux_profile_w_m2"]
    )


def test_total_heat_flux_of_a_beam_obeys_the_enthalpy_closed_form():
    """Evidence 2: a mono-axial beam has sigma = -P, so q_total = (m U^2/2 + 3 T/2) n U."""
    vx = np.array([0.5])
    widths = np.array([0.25])
    beam = np.ones((2, 1, 1))
    result = N.reduce_terminal_molecular_heat_flux(VR, vx, MASS_RATIO, VTH, beam, WEIGHT, widths)
    raw = N.reduce_terminal_molecular_heat_flux(VR, vx, MASS_RATIO, 2.0 * VTH, beam, WEIGHT, widths)
    assert np.array_equal(
        raw["total_heat_flux_profile_w_m2"], 8.0 * result["total_heat_flux_profile_w_m2"]
    )
    assert result["random_heat_flux_profile_w_m2"][0] == 0.0
    pressure = N.reduce_terminal_molecular_pressure_temperature(
        VR, vx, MASS_RATIO, VTH, beam, WEIGHT, widths
    )["pressure_profile_ev_m3"][0]
    density = float(np.sum(WEIGHT) * 0.25)
    mean_velocity = 0.5 * VTH
    expected = (
        0.5 * density * 2.0 * MASS_RATIO * M_H * mean_velocity**2 + 1.5 * Q * pressure
    ) * mean_velocity
    assert abs(result["total_heat_flux_profile_w_m2"][0] - expected) <= _budget(16, abs(expected))


def test_heat_flux_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    call = N.reduce_terminal_molecular_heat_flux
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(-VR, VX, MASS_RATIO, VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, 0.0, VTH, DISTRIBUTION, WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, VTH, DISTRIBUTION, WEIGHT, WIDTHS[:2])
    with pytest.raises(ValueError, match="real numeric"):
        call(VR, VX, MASS_RATIO, VTH, [[[1j, 1.0]]], WEIGHT, WIDTHS)
    with pytest.raises(ValueError, match="strictly positive density"):
        call(VR, VX, MASS_RATIO, VTH, np.zeros_like(DISTRIBUTION), WEIGHT, WIDTHS)


# --------------------------------------------------------------------------- #
# terminal-energy-transfer-reduction
# --------------------------------------------------------------------------- #


def _energy_transfer(
    distribution=DISTRIBUTION, rhs_scale=0.0, external=0.0, vth=VTH, mass_ratio=MASS_RATIO
):
    """Call the transfer reduction; the default RHS is proportional to f."""
    rhs = rhs_scale * distribution
    external_profile = np.full(distribution.shape[2], float(external))
    return N.reduce_terminal_molecular_energy_transfer(
        VR,
        VX,
        mass_ratio,
        vth,
        distribution,
        rhs,
        WEIGHT,
        WIDTHS,
        external_profile,
    )


def test_pure_loss_transfer_carries_the_thermal_energy_and_the_bulk_energy():
    """Evidence 4: momentum vanishes and the total exceeds thermal by 0.5 m U^2 J."""
    scale_rate = 0.5
    result = _energy_transfer(rhs_scale=scale_rate)
    density = _integral(DISTRIBUTION, WEIGHT, WIDTHS)
    flux = _integral(DISTRIBUTION * VX[None, :, None], WEIGHT, WIDTHS)
    normalized_mean = [f / n for f, n in zip(flux, density)]
    exact_density, second = _second_moment(DISTRIBUTION, normalized_mean)
    molecule_mass = 2 * _frac(MASS_RATIO) * _frac(M_H)
    # thermal transfer = lambda * (1/2 m vth^2 * sum f v_rand^2) = lambda * (3/2) n T
    thermal = np.array(
        [0.5 * float(molecule_mass) * VTH**2 * float(scale_rate) * float(value) for value in second]
    )
    # J = lambda * n, U = vth * normalized mean.
    integral = np.array([float(_frac(scale_rate) * value) for value in exact_density])
    mean_velocity = np.array([float(_frac(VTH) * value) for value in normalized_mean])
    bulk = 0.5 * float(molecule_mass) * integral * mean_velocity**2
    total = thermal + bulk
    assert np.allclose(
        result["thermal_energy_transfer_rate_profile_w_m3"],
        thermal,
        rtol=0.0,
        atol=_budget(12, float(np.max(np.abs(thermal)))),
    )
    # A loss proportional to the distribution removes the mean flow itself, so the
    # centered momentum transfer cancels exactly.
    assert np.all(
        np.abs(result["momentum_transfer_rate_profile_n_m3"])
        <= _budget(12, float(np.max(np.abs(thermal))) / VTH * 8)
    )
    assert np.allclose(
        result["total_energy_transfer_rate_profile_w_m3"],
        total,
        rtol=0.0,
        atol=_budget(14, float(np.max(np.abs(total)))),
    )


def test_transfer_loss_rate_is_external_source_minus_the_rhs_integral():
    """Evidence 1: loss = -J + S_ext with J the exact weighted RHS integral."""
    result = _energy_transfer(rhs_scale=0.25, external=3.0)
    density = _integral(DISTRIBUTION, WEIGHT, WIDTHS)
    integral = np.array([float(_frac(0.25) * value) for value in density])
    expected = -integral + 3.0
    assert np.allclose(
        result["loss_rate_profile_m3_s"],
        expected,
        rtol=0.0,
        atol=_budget(10, float(np.max(np.abs(expected)))),
    )
    # Doubling J doubles only the RHS part of the loss.
    doubled = _energy_transfer(rhs_scale=0.5, external=3.0)
    assert np.allclose(
        doubled["loss_rate_profile_m3_s"],
        -2.0 * integral + 3.0,
        rtol=0.0,
        atol=_budget(10, float(np.max(np.abs(expected)))),
    )


def test_transfer_total_is_independent_of_the_external_source():
    """Evidence 4: the total-energy reconstruction never subtracts the source."""
    base = _energy_transfer(rhs_scale=0.25, external=0.0)
    sourced = _energy_transfer(rhs_scale=0.25, external=7.5)
    assert np.array_equal(
        base["total_energy_transfer_rate_profile_w_m3"],
        sourced["total_energy_transfer_rate_profile_w_m3"],
    )
    assert np.array_equal(
        base["thermal_energy_transfer_rate_profile_w_m3"],
        sourced["thermal_energy_transfer_rate_profile_w_m3"],
    )


def test_transfer_scales_with_the_declared_powers_of_the_thermal_speed():
    """Evidence 4: thermal transfer is quadratic and momentum transfer linear in vth."""
    base = _energy_transfer(rhs_scale=0.25)
    doubled = _energy_transfer(rhs_scale=0.25, vth=2.0 * VTH)
    assert np.array_equal(
        doubled["thermal_energy_transfer_rate_profile_w_m3"],
        4.0 * base["thermal_energy_transfer_rate_profile_w_m3"],
    )
    assert np.array_equal(
        doubled["momentum_transfer_rate_profile_n_m3"],
        2.0 * base["momentum_transfer_rate_profile_n_m3"],
    )


def test_transfer_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    external = np.zeros(DISTRIBUTION.shape[2])
    call = N.reduce_terminal_molecular_energy_transfer
    good = (
        VR,
        VX,
        MASS_RATIO,
        VTH,
        DISTRIBUTION,
        np.zeros_like(DISTRIBUTION),
        WEIGHT,
        WIDTHS,
        external,
    )
    assert call(*good)["loss_rate_profile_m3_s"].shape == (DISTRIBUTION.shape[2],)
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(-VR, *good[1:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, 0.0, *good[3:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, VTH, DISTRIBUTION, np.ones((1, 1, 1)), *good[6:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, VTH, -DISTRIBUTION, *good[5:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(VR, VX, MASS_RATIO, VTH, DISTRIBUTION, np.full_like(DISTRIBUTION, np.inf), *good[6:])
    poisoned = np.array(DISTRIBUTION, dtype=object)
    poisoned[0, 0, 0] = "a"
    with pytest.raises(ValueError, match="real numeric"):
        call(VR, VX, MASS_RATIO, VTH, DISTRIBUTION, poisoned, *good[6:])


# --------------------------------------------------------------------------- #
# terminal-ion-state-reduction
# --------------------------------------------------------------------------- #

ION_DENSITY = np.array([4.0e17, 5.0e17])
ELECTRON_DENSITY = np.array([1.0e18, 2.0e18])
ION_TEMPERATURE = np.array([2.0, 3.0])


def _rate_table():
    """Build the eleven-column rate table, with columns 0..6 deliberately populated."""
    table = np.arange(1.0, 23.0).reshape(2, 11) * 1e-20
    table[:, 7:11] = np.array([1e-18, 2e-18, 3e-18, 4e-18])
    return table


def _ion_state(table=None, electron_density=ELECTRON_DENSITY, mass_ratio=2.0, loss=1.0):
    """Call the ion-state reduction with the shared fixtures."""
    rates = _rate_table() if table is None else table
    return N.reduce_terminal_molecular_ion_state(
        ION_DENSITY,
        electron_density,
        ION_TEMPERATURE,
        mass_ratio,
        np.array([4.0, 5.0]),
        rates,
        np.full(2, float(loss)),
    )


def test_ion_state_satisfies_the_steady_ionization_balance():
    """Evidence 5: production equals (electron + external) loss at the returned state."""
    result = _ion_state()
    loss_frequency = result["electron_loss_frequency_s_inv"] + 1.0
    production = ION_DENSITY * ELECTRON_DENSITY * np.array([4.0, 5.0])
    assert np.allclose(
        production,
        result["molecular_ion_density_m3"] * loss_frequency,
        rtol=0.0,
        atol=_budget(10, float(np.max(np.abs(production)))),
    )


def test_ion_state_reads_only_the_declared_rate_table_columns():
    """Evidence 5: columns 0..6 are unread; columns 7..10 drive the loss frequency."""
    base = _ion_state()
    perturbed = _rate_table()
    perturbed[:, 0:7] += 1e-6
    unchanged = _ion_state(table=perturbed)
    for name in base:
        assert np.array_equal(base[name], unchanged[name]), name
    # Each of the four read columns contributes: ... sum of 7:11 is e_density times
    # the four values, so the loss frequency is exactly that sum.
    expected_loss = ELECTRON_DENSITY * float(np.sum(np.array([1e-18, 2e-18, 3e-18, 4e-18])))
    assert np.allclose(
        base["electron_loss_frequency_s_inv"],
        expected_loss,
        rtol=0.0,
        atol=_budget(8, float(np.max(expected_loss))),
    )


def test_ion_state_temperature_is_a_complementary_blend():
    """Evidence 5: T_ion/T_i + nu_den/(nu_ex + nu_den) = 1, and T_ion < T_i."""
    result = _ion_state()
    exchange = result["energy_exchange_frequency_s_inv"]
    denominator = result["electron_loss_frequency_s_inv"] + 1.0
    ratio = result["molecular_ion_temperature_ev"] / ION_TEMPERATURE
    complement = denominator / (exchange + denominator)
    assert np.allclose(ratio + complement, 1.0, rtol=0.0, atol=8 * EPS)
    assert np.all(result["molecular_ion_temperature_ev"] < ION_TEMPERATURE)


def test_ion_state_branches_scale_with_the_declared_inputs():
    """Evidence 5: nu_ex is linear in n_e, inverse in sqrt(m), and T^-3/2."""
    base = _ion_state()
    denser = _ion_state(electron_density=2.0 * ELECTRON_DENSITY)
    assert np.array_equal(
        denser["energy_exchange_frequency_s_inv"], 2.0 * base["energy_exchange_frequency_s_inv"]
    )
    # mass 2 -> 8 multiplies sqrt(m) by exactly 2.
    heavier = _ion_state(mass_ratio=8.0)
    assert np.array_equal(
        heavier["energy_exchange_frequency_s_inv"], 0.5 * base["energy_exchange_frequency_s_inv"]
    )
    # T -> 4T multiplies T**1.5 by exactly 8.
    hotter = N.reduce_terminal_molecular_ion_state(
        ION_DENSITY,
        ELECTRON_DENSITY,
        4.0 * ION_TEMPERATURE,
        2.0,
        np.array([4.0, 5.0]),
        _rate_table(),
        np.ones(2),
    )
    assert np.array_equal(
        hotter["energy_exchange_frequency_s_inv"],
        base["energy_exchange_frequency_s_inv"] / 8.0,
    )


def test_ion_state_temperature_approaches_the_ion_temperature():
    """Evidence 5: a dominant exchange frequency drives T_ion to T_i."""
    faint_table = np.zeros((2, 11))
    faint_table[:, 7:11] = 1e-30
    dominant = N.reduce_terminal_molecular_ion_state(
        ION_DENSITY,
        ELECTRON_DENSITY,
        ION_TEMPERATURE,
        2.0,
        np.array([4.0, 5.0]),
        faint_table,
        np.full(2, 1e-30),
    )
    # nu_ex / nu_den is ~5e16 here, so the blend sits at T_i to well below 1e-12.
    assert np.allclose(
        dominant["molecular_ion_temperature_ev"], ION_TEMPERATURE, rtol=1e-12, atol=0.0
    )
    # A larger loss frequency cools the molecular ions further.
    weak = N.reduce_terminal_molecular_ion_state(
        ION_DENSITY,
        ELECTRON_DENSITY,
        ION_TEMPERATURE,
        2.0,
        np.array([4.0, 5.0]),
        _rate_table(),
        np.full(2, 1e14),
    )
    assert np.all(
        weak["molecular_ion_temperature_ev"] < _ion_state()["molecular_ion_temperature_ev"]
    )


def test_ion_state_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    rates = _rate_table()
    call = N.reduce_terminal_molecular_ion_state
    good = (
        ION_DENSITY,
        ELECTRON_DENSITY,
        ION_TEMPERATURE,
        2.0,
        np.array([4.0, 5.0]),
        rates,
        np.ones(2),
    )
    assert set(call(*good)) == {
        "molecular_ion_density_m3",
        "molecular_ion_temperature_ev",
        "electron_loss_frequency_s_inv",
        "energy_exchange_frequency_s_inv",
    }
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(ION_DENSITY, ELECTRON_DENSITY, np.array([0.0, 3.0]), *good[3:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(ION_DENSITY, ELECTRON_DENSITY, ION_TEMPERATURE, 0.0, *good[4:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(
            ION_DENSITY,
            ELECTRON_DENSITY,
            ION_TEMPERATURE,
            2.0,
            np.array([4.0, 5.0]),
            rates[:, :10],
            np.ones(2),
        )
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(-ION_DENSITY, *good[1:])
    with pytest.raises(ValueError, match="finite, shape-compatible"):
        call(
            ION_DENSITY,
            ELECTRON_DENSITY,
            ION_TEMPERATURE,
            2.0,
            np.array([4.0, 5.0]),
            -rates,
            np.ones(2),
        )
    with pytest.raises(ValueError, match="real numeric"):
        call(
            ION_DENSITY,
            ELECTRON_DENSITY,
            ION_TEMPERATURE,
            2.0,
            np.array([4.0, 5.0]),
            [[True]],
            np.ones(2),
        )
    # A zero denominator is rejected rather than silently producing a zero density.
    with pytest.raises(ValueError, match="strictly positive"):
        call(
            ION_DENSITY,
            np.zeros(2),
            ION_TEMPERATURE,
            2.0,
            np.array([4.0, 5.0]),
            np.zeros((2, 11)),
            np.zeros(2),
        )
