"""Explicit scalar thermal-speed scale for neutral species.

One leaf recovered from the saved the neutral-transport formulation ``热速度标度换算`` package, integrated as :func:`compute_thermal_speed_m_s`:

the explicit second-moment thermal speed scale
``sqrt(2 e T_ev / (m_amu * m_H))`` with the source's frozen constants
(``m_H = 1.6726231e-27`` kg, ``e = 1.602177e-19`` J/eV).  This is the same
``Vth`` the already-integrated r59 sibling
``scirel.kinetic.hydrogen-saha-equilibrium-population`` does not consume and
that the axisymmetric moment reduction and boundary-flux normalization
relations below use internally.

For representable finite positive real scalars, the source formula and
operation order are retained. Dangerous intermediate overflow/underflow uses
the same defining relation with exact binary64 inputs at 100 decimal digits,
then rounds once to the returned float. Only a nonpositive or non-finite
final result is rejected; losing a representable value in mass-to-kg
conversion is not a scientific failure.

Evidence ceiling: maintained tests establish the scalar relation against an
independent recomputation with the frozen constants and mass monotonicity.
Integration replay found exact agreement with the saved implementation at
three finite positive points. The saved bundle's strict D1 qualification has
been withdrawn; that replay is historical development evidence, not
qualified-L1 provenance.
"""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
import sys

import numpy as np

__all__ = [
    "compute_thermal_speed_m_s",
]

_HYDROGEN_MASS_KG = 1.6726231e-27
_ELECTRON_VOLT_J = 1.602177e-19


def _real_scalar(value, name):
    try:
        raw = np.asarray(value)
        if raw.ndim != 0 or raw.dtype.kind not in "iuf":
            raise ValueError
        return float(raw)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric scalar") from error


def _thermal_speed_ratio(temperature, mass):
    """Build the SI second-moment ratio from the frozen SciRel constants."""
    denominator = mass * _HYDROGEN_MASS_KG
    return (2.0 * _ELECTRON_VOLT_J * temperature) / denominator if denominator else math.inf


def compute_thermal_speed_m_s(temperature_ev, mass_amu):
    r"""The explicit second-moment thermal speed sqrt(2 e T / m) of a neutral species from its temperature in eV and a mass factor relative to the hydrogen mass, using frozen constants (hydrogen mass 1.6726231e-27 kg, elementary charge 1.602177e-19 J/eV).

    Parameters
    ----------
    temperature_ev : real scalar, shape scalar
        Temperature of the species. [eV].
        Constraints: A finite strictly positive real numeric scalar; booleans, strings, complex values and nonscalars are rejected.
    mass_amu : real scalar, shape scalar
        Particle mass factor relative to the hydrogen mass constant, despite the historical parameter name. [multiples of 1.6726231e-27 kg].
        Constraints: A finite strictly positive real numeric scalar; booleans, strings, complex values and nonscalars are rejected.

    Returns
    -------
    result : mapping with one float64 scalar, shape mapping
        The thermal-speed mapping. [m/s].
        Constraints: Carries exactly one field thermal_speed_m_s; finite and strictly positive.

    Raises
    ------
    ValueError
        Raises ValueError for boolean, string, complex or nonscalar inputs, or when temperature_ev or mass_amu is non-finite or nonpositive. Raises ValueError only if the final speed is non-finite or nonpositive. Dangerous intermediate range uses 100-digit Decimal evaluation of the defining relation with exact binary64 inputs before final float rounding. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.create_adaptive_neutral_velocity_mesh : Related neutral-transport operation.

    Notes
    -----
        v = sqrt(2 * 1.602177e-19 * T_ev / (m_amu * 1.6726231e-27)); the same Vth normalization the moment-reduction and boundary-flux relations consume
    Both input scalars are finite and strictly positive; the final thermal speed must be finite and positive. Intermediate conversion underflow does not exclude a representable result.

    Examples
    --------
    >>> import math
    >>> from scirel.kinetic import compute_thermal_speed_m_s
    >>> result = compute_thermal_speed_m_s(1.0, 2.0)
    >>> assert result['thermal_speed_m_s'] == math.sqrt(2.0 * 1.602177e-19 / (2.0 * 1.6726231e-27))
    >>> assert compute_thermal_speed_m_s(4.0, 2.0)['thermal_speed_m_s'] == 2.0 * result['thermal_speed_m_s']
    >>> try:
    ...     compute_thermal_speed_m_s(0.0, 1.0)
    ... except ValueError as error:
    ...     assert 'temperature_ev' in str(error)
    ... else:
    ...     raise AssertionError('a nonpositive temperature must be rejected')
    """
    temperature = _real_scalar(temperature_ev, "temperature_ev")
    mass = _real_scalar(mass_amu, "mass_amu")
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature_ev must be finite and positive")
    if not math.isfinite(mass) or mass <= 0.0:
        raise ValueError("mass_amu must be finite and positive")
    mass_kg = mass * _HYDROGEN_MASS_KG
    numerator = 2.0 * _ELECTRON_VOLT_J * temperature
    ratio = _thermal_speed_ratio(temperature, mass)
    if not math.isfinite(ratio) or min(mass_kg, numerator, ratio) < sys.float_info.min:
        with localcontext() as context:
            context.prec = 100
            exact = (
                Decimal(2)
                * Decimal.from_float(_ELECTRON_VOLT_J)
                * Decimal.from_float(temperature)
                / (Decimal.from_float(mass) * Decimal.from_float(_HYDROGEN_MASS_KG))
            )
            value = float(exact.sqrt())
    else:
        value = math.sqrt(ratio)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("thermal speed must be finite and positive")
    return {"thermal_speed_m_s": value}
