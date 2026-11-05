"""Evaluate a fixed empirical fast-ion increment to beam stopping, in m^2.

The model fixes pitch diffusion at y=0.6. Its use of a supplied birth-pitch
cosine does not reconstruct geometry or equate magnetic-axis, toroidal and
local-field conventions. No calibrated interval or physical error bound is
established. Required attribution and terms are retained in
licenses/fast-ion-stopping-increment/.
"""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_fast_ion_stopping_increment"]

_ENERGY_COEFFICIENTS = (0.57658, 1.6432, -4.8886, 5.3932, -2.9226, 0.77156, -0.079095)
_PITCH_COEFFICIENTS = (0.30812, 11.992, -68.971, 165.94, -177.33, 69.833)
# The fitted expression retains this historical conversion, not the current SI value.
_ENERGY_CONVERSION_J_PER_EV = 1.602176462e-19


def _shaped_real(value):
    if np.iscomplexobj(value):
        raise TypeError("Input arguments must be real; complex inputs are unsupported")
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(1, array.size)
    return array


def _expand(operation, left, right):
    """Align the leading axes, extending a lower rank on its right."""
    left, right = np.asarray(left), np.asarray(right)
    rank = max(left.ndim, right.ndim)
    return operation(
        left.reshape(left.shape + (1,) * (rank - left.ndim)),
        right.reshape(right.shape + (1,) * (rank - right.ndim)),
    )


def _polynomial(variable, coefficients, first_power):
    """Accumulate explicit powers in ascending order, preserving cancellation."""
    result = (
        coefficients[0] if first_power == 0 else _expand(np.multiply, coefficients[0], variable)
    )
    for exponent, coefficient in enumerate(coefficients[1:], first_power + 1):
        term = _expand(np.multiply, abs(coefficient), np.power(variable, exponent))
        result = _expand(np.subtract if coefficient < 0 else np.add, result, term)
    return np.asarray(result)


def evaluate_fast_ion_stopping_increment(
    beam_mass_number,
    beam_energy_ev,
    birth_pitch_cosine,
    electron_density_m3,
    electron_temperature_ev,
    power_density_w_m3,
    electron_slowing_time_s,
):
    """Return the specified empirical additive stopping increment in m^2.

    Parameters
    ----------
    beam_mass_number : real scalar or array-like
        Dimensionless beam isotope mass number used in the energy normalization.
    beam_energy_ev : real scalar or array-like
        Beam-particle injection energy in eV.
    birth_pitch_cosine : real scalar or array-like
        Caller-supplied cosine of the birth direction relative to the magnetic
        axis, not an angle. The expression uses min(1, abs(cosine)); it does not
        establish equivalence to a toroidal or full-local-field pitch.
    electron_density_m3 : real scalar or array-like
        Electron density in m^-3.
    electron_temperature_ev : real scalar or array-like
        Electron temperature in eV.
    power_density_w_m3 : real scalar or array-like
        Local volumetric neutral-beam deposition power in W/m^3. Total injected
        power is not accepted as an equivalent quantity; no volume is inferred.
    electron_slowing_time_s : real scalar or array-like
        Caller-supplied electron slowing time in seconds; no time is estimated.

    Returns
    -------
    numpy.ndarray
        The increment only. Scalars become (1, 1), vectors become rows, and
        explicit array axes expand by appending singleton axes on the right.
        Arithmetic uses float64, or complex128 when a negative temperature
        enters the fractional power. Inputs are not mutated.

    Notes
    -----
    This evaluates a fixed empirical expression, not a calibrated prediction
    over an established physical domain. Fixed coefficients, y=0.6 and the
    historical energy conversion are retained. The energy polynomial is
    overwritten with zero only for epsilon > pi; equality is not cut off.
    NaN pitch maps to the capped value one. Other negative/nonfinite values
    and extreme magnitudes retain arithmetic warnings and NaN/Inf/complex
    outcomes. In particular zero power does not bypass division by energy.
    Such probes are not supported physical plasma states. There is no total
    stopping, attenuation, deposition, geometry calculation or time evolution.

    Raises
    ------
    TypeError
        For complex inputs or values that cannot be converted to real float64.
    ValueError
        For incompatible axes or values that cannot be converted to float64.
    """
    mass, energy, cosine, density, temperature, power, slowing_time = (
        _shaped_real(value)
        for value in (
            beam_mass_number,
            beam_energy_ev,
            birth_pitch_cosine,
            electron_density_m3,
            electron_temperature_ev,
            power_density_w_m3,
            electron_slowing_time_s,
        )
    )
    with np.errstate(all="warn"):
        source_rate = _expand(
            np.divide,
            power,
            _expand(np.multiply, energy, _ENERGY_CONVERSION_J_PER_EV),
        )
        scaled_energy = _expand(np.divide, _expand(np.divide, energy, mass), 1e6)
        scaled_temperature = _expand(np.divide, _expand(np.divide, temperature, 1e3), 10)
        ratio = _expand(np.divide, scaled_energy, scaled_temperature)
        energy_response = _polynomial(ratio, _ENERGY_COEFFICIENTS, 0).copy()
        energy_response[ratio > np.pi] = 0.0
        pitch_response = _polynomial(np.fmin(1.0, np.abs(cosine)), _PITCH_COEFFICIENTS, 1)
        thermal_response = np.lib.scimath.power(scaled_temperature, -0.9027)
        area_response = _expand(np.multiply, thermal_response, energy_response)
        area_response = _expand(np.multiply, area_response, pitch_response)
        area_response = _expand(np.multiply, area_response, 1e-19)
        population_ratio = _expand(np.multiply, source_rate, slowing_time)
        population_ratio = _expand(np.divide, population_ratio, density)
        return _expand(np.multiply, population_ratio, area_response)
