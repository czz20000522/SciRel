"""FIDASIM Doppler and Stark--Zeeman line component wavelengths.

Source: the saved package ``多普勒StarkZeeman谱线波长`` (source anchors
``src/fidasim.f90:69-81`` for the constants and the single cm/s -> m/s
velocity conversion, ``:11891-11963`` for the moving electric field, the
Stark--Zeeman level shifts and the fixed component ordering).  For one
emitting neutral hydrogen isotope on one sightline the relation returns
the source-ordered Lyman-alpha (3) or Balmer-alpha (15) component
wavelengths: the nonrelativistic Doppler shift
``lambda_D = lambda0 * (1 + v . p_hat / c)`` is added to the
Stark--Zeeman level-difference displacements evaluated against
``lambda0`` at the moving electric field magnitude
``E' = ||E + v x B||`` and the magnetic magnitude ``B``.

The saved arm is ported verbatim: the velocity is converted once, the
sightline is normalized internally, the y component of the moving
electric field carries the source's sign convention, the combined
Stark--Zeeman frequencies ``q0``/``q1`` add the cyclotron and Stark
terms in quadrature, and the 15 Balmer components follow the fixed
``(lower, upper)`` sublevel table in source order.

Registered hardenings against the saved arm (whose own contract already
promised fail-closed behavior it did not implement): every scalar and
vector input is checked finite, the reference wavelength must be
positive, scalar magnitudes and vector entries reject booleans, and
``component_count`` must be a genuine integer (the saved arm's
``not in (3, 15)`` accepted whole-number floats such as ``3.0``).

r80-v2 repairs (read-only expert review findings on the r80-v1 freeze):
the sightline norm is computed by max-abs scaling so a finite but huge
sightline (e.g. ``(1e308, 1e308, 0)``) keeps its nonzero Doppler shift
instead of collapsing the direction to zero through a ``inf`` norm; the
Stark--Zeeman frequencies and the final component wavelengths are
checked finite, so field magnitudes whose quadrature overflows (e.g.
``B = 1e308``) raise ``ValueError`` instead of returning ``nan``; and
the vector boolean check now runs before the float conversion, where
the r80-v1 placement after ``asarray(..., dtype=float)`` was dead code.
"""
from __future__ import annotations

import math
from math import pi, sqrt

import numpy as np

__all__ = ["doppler_stark_zeeman_wavelengths"]

_C0 = 2.99792458e8
_E0 = 1.60217733e-19
_A0 = 5.29177210903e-11
_H = 6.62607004e-34
_ME = 9.109384e-31

_LYMAN_SHIFTS = ((-1, 0), (0, 0), (1, 0))
_BALMER_SHIFTS = (
    (-1, 2), (0, 2), (-1, 1), (1, 2), (0, 1), (-1, 0), (1, 1), (0, 0),
    (-1, -1), (1, 0), (0, -1), (-1, -2), (1, -1), (0, -2), (1, -2),
)


def _finite_vector(value, *, name: str) -> tuple[float, float, float]:
    # booleans must be inspected before numpy coerces them: a mixed
    # list/tuple such as (True, 0.0, 0.0) becomes float64 at asarray time
    if isinstance(value, (list, tuple)) and any(
        isinstance(item, (bool, np.bool_)) for item in value
    ):
        raise ValueError(f"{name} must not contain boolean entries (registered hardening)")
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if raw.dtype == np.bool_ or (
        raw.dtype == np.object_ and any(isinstance(item, (bool, np.bool_)) for item in raw)
    ):
        raise ValueError(f"{name} must not contain boolean entries (registered hardening)")
    try:
        array = raw.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite 3-vector")
    return (float(array[0]), float(array[1]), float(array[2]))


def _finite_scalar(value, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must not be boolean (registered hardening)")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite scalar") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite scalar")
    return number


def doppler_stark_zeeman_wavelengths(
    sightline_to_head,
    ion_velocity_cm_s,
    magnetic_unit_vector,
    magnetic_magnitude_t,
    electric_unit_vector,
    electric_magnitude_v_m,
    reference_wavelength_nm,
    component_count,
):
    """Return source-ordered Lyman-alpha (3) or Balmer-alpha (15) wavelengths."""
    if isinstance(component_count, (bool, np.bool_)) or not isinstance(
        component_count, (int, np.integer)
    ):
        raise ValueError(
            "component_count must be a genuine integer 3 or 15 (registered hardening:"
            " the saved arm accepted whole-number floats)"
        )
    component_count = int(component_count)
    if component_count not in (3, 15):
        raise ValueError("component_count must be 3 or 15")
    direction = _finite_vector(sightline_to_head, name="sightline_to_head")
    scale = max(abs(value) for value in direction)
    if scale == 0.0:
        raise ValueError("sightline_to_head must be nonzero")
    direction = tuple(value / scale for value in direction)
    norm = math.sqrt(sum(value * value for value in direction))
    direction = tuple(value / norm for value in direction)
    velocity = _finite_vector(ion_velocity_cm_s, name="ion_velocity_cm_s")
    velocity = tuple(value * 0.01 for value in velocity)
    magnetic_unit = _finite_vector(magnetic_unit_vector, name="magnetic_unit_vector")
    magnetic_magnitude = _finite_scalar(magnetic_magnitude_t, name="magnetic_magnitude_t")
    electric_unit = _finite_vector(electric_unit_vector, name="electric_unit_vector")
    electric_magnitude = _finite_scalar(electric_magnitude_v_m, name="electric_magnitude_v_m")
    reference_wavelength = _finite_scalar(
        reference_wavelength_nm, name="reference_wavelength_nm"
    )
    if reference_wavelength <= 0.0:
        raise ValueError("reference_wavelength_nm must be positive (registered hardening)")
    bfield = tuple(value * magnetic_magnitude for value in magnetic_unit)
    efield = [value * electric_magnitude for value in electric_unit]
    efield[0] += velocity[1] * bfield[2] - velocity[2] * bfield[1]
    efield[1] -= velocity[0] * bfield[2] - velocity[2] * bfield[0]
    efield[2] += velocity[0] * bfield[1] - velocity[1] * bfield[0]
    electric = math.sqrt(sum(value * value for value in efield))
    magnetic = math.sqrt(sum(value * value for value in bfield))
    wavelength_m = reference_wavelength * 1.0e-9
    doppler_nm = reference_wavelength * (
        1.0 + sum(a * b for a, b in zip(velocity, direction)) / _C0
    )
    q0 = sqrt(
        (_E0 * _H * magnetic / (4.0 * pi * _ME)) ** 2
        + (3.0 * _A0 * _E0 * electric) ** 2
    )
    q1 = sqrt(
        4.0 * (_E0 * _H * magnetic / (4.0 * pi * _ME)) ** 2
        + 9.0 * (3.0 * _A0 * _E0 * electric) ** 2
    )
    if not (math.isfinite(q0) and math.isfinite(q1)):
        raise ValueError(
            "magnetic/electric magnitudes are outside the representable Stark-Zeeman"
            " range (r80-v2 repair: the saved arm returned nan)"
        )
    if component_count == 3:
        shifts = _LYMAN_SHIFTS
        wavelengths_m = tuple(
            _C0 * _H * wavelength_m / (_C0 * _H + q0 * lower * wavelength_m)
            for lower, _ in shifts
        )
    else:
        shifts = _BALMER_SHIFTS
        wavelengths_m = tuple(
            2.0 * _C0 * _H * wavelength_m
            / (2.0 * _C0 * _H + (-2.0 * q0 * lower + q1 * upper) * wavelength_m)
            for lower, upper in shifts
        )
    result = tuple(doppler_nm + (value - wavelength_m) * 1.0e9 for value in wavelengths_m)
    if not all(math.isfinite(value) for value in result):
        raise ValueError(
            "component wavelengths are not finite for the supplied inputs (r80-v2 repair:"
            " the saved arm could return nan/inf)"
        )
    return result
