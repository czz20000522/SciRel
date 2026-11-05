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
    """Evaluate the empirical fast-ion stopping cross-section increment.

    Parameters
    ----------
    beam_mass_number : real scalar or array-like
        Beam isotope mass number used in the ``E/A`` normalization.
        [dimensionless] Shape: ``() | (N,) | (d0,d1,...)``. No positivity or
        finiteness check is applied.
    beam_energy_ev : real scalar or array-like
        Beam-particle injection energy. [eV] Shape: ``() | (N,) | (d0,d1,...)``.
        No positivity or finiteness check is applied.
    birth_pitch_cosine : real scalar or array-like
        Cosine of the birth direction relative to the magnetic axis, not an angle.
        [dimensionless] Shape: ``() | (N,) | (d0,d1,...)``. The arithmetic uses
        ``min(1, abs(value))``; magnitudes above one and infinities cap at one, and
        NaN maps to one.
    electron_density_m3 : real scalar or array-like
        Electron density. [m^-3] Shape: ``() | (N,) | (d0,d1,...)``. No positivity,
        finiteness or density-threshold check is applied.
    electron_temperature_ev : real scalar or array-like
        Electron temperature. [eV] Shape: ``() | (N,) | (d0,d1,...)``. A negative
        scaled temperature follows the complex fractional-power branch.
    power_density_w_m3 : real scalar or array-like
        Local volumetric neutral-beam deposition power density. [W/m^3] Shape:
        ``() | (N,) | (d0,d1,...)``. Total injected power is not interchangeable.
    electron_slowing_time_s : real scalar or array-like
        Caller-supplied electron slowing time. [s] Shape:
        ``() | (N,) | (d0,d1,...)``. No slowing-time model is inferred.

    Returns
    -------
    stopping_increment_m2 : numpy.ndarray
        Additive stopping cross-section increment. [m^2] Shape: scalar inputs
        become ``(1, 1)``, one-dimensional inputs become ``(1, N)``, and explicit
        array axes expand with singleton axes on the right. Returned values may be
        signed, complex, NaN or infinite according to the retained arithmetic.

    Raises
    ------
    TypeError
        If an input is complex-valued.
    ValueError
        If expanded input axes are incompatible, or if ``float64`` conversion of
        a scalar value raises ``ValueError``. Other conversion errors propagate
        unchanged with their original exception type.
    OverflowError
        If ``float64`` conversion overflows, such as for an oversized integer;
        the converter error propagates unchanged.
    RuntimeWarning
        If the retained direct arithmetic encounters invalid, divide-by-zero,
        overflow or complex fractional-power conditions. These outcomes are not
        replaced with a fallback.

    See Also
    --------
    average_cross_section_over_maxwellian : A different Maxwellian velocity-space
        average; it does not reproduce this empirical increment.
    evaluate_atomic_hydrogen_elastic_cross_section : A fitted elastic cross
        section, not the final beam-stopping increment.

    Notes
    -----
    This is a fixed empirical expression, not a calibrated prediction over a
    quantified physical domain. It uses energy and pitch polynomials, a fractional
    temperature power, the fixed pitch-diffusion parameter ``y=0.6`` and the
    historical conversion ``1.602176462e-19`` J/eV. The energy polynomial is
    overwritten with zero only for ``energy_ratio > pi``; equality is not cut off.
    The input power is local volumetric deposition power, the slowing time is
    caller-supplied, and the pitch is a magnetic-axis cosine. No beam path,
    magnetic geometry, calibrated error bound or general species coverage is
    established.

    References
    ----------
    K. Okano et al. (2001), ECA 25A, P2.088, pp. 809-812; birth-pitch definition
    on p. 810 and area scale/normalization in Eq. (6), p. 811.
    https://info.fusion.ciemat.es/OCS/EPS2001/pdfs/P2.088.pdf

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_fast_ion_stopping_increment
    >>> increment = evaluate_fast_ion_stopping_increment(1.0, 100000.0, 0.5, 1e18, 10000.0, 1e6, 1.0)
    >>> assert increment.shape == (1, 1)
    >>> np.testing.assert_allclose(increment, [[1.9645775636530587e-18]], rtol=5e-12, atol=1e-300)
    >>> print(increment.shape)
    (1, 1)
    >>> print(increment.dtype)
    float64
    >>> print(f'{increment[0, 0]:.17g} m^2')
    1.9645775636530587e-18 m^2
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
