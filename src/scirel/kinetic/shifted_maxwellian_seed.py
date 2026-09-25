"""Discrete shifted-Maxwellian seed on an explicit cylindrical velocity mesh.

One leaf recovered from the saved KN1DPy ``create_shifted_maxwellian`` slice
(source anchor ``KN1DPy/create_shifted_maxwellian_include.py:58-76``),
integrated as :func:`build_shifted_maxwellian_seed`: the normalized
exponential distribution on a cylindrical ``(vr, vx)`` mesh **before any
moment compensation**, with one temperature per axial shift, the
molecule-count factor in the exponent, the saved source's strict-interior
``-80`` clamp, and normalization by the caller-supplied cell volumes.

**The construction, exactly as the saved source defines it.**  With ``vth =
sqrt(2 e T_norm / (m amu))`` the raw exponent is
``-(vr^2 + (vx - shift/vth)^2) * molecule_count * T_norm / T_shift`` per shift,
so a shift given in m/s is divided by the thermal speed into mesh units.  The
raw seed is ``exp(argument)`` where ``-80 < argument < 0`` and ``exp(-80)``
everywhere else -- a strict interior clamp: a mesh node that lands exactly on
the shifted peak (``argument == 0``) is floored like the far tail, while the
returned ``exponent`` still reports the raw value.  The distribution is then
normalized per shift by the supplied cell volumes.  ``molecule_count`` is 1
for atomic and 2 for molecular hydrogen, scaling the exponent.

**The cell volumes are the caller's.**  The N1 cylindrical quadrature
(``scirel.kinetic.make_cylindrical_velocity_quadrature``) produces exactly the
volume measure this normalization consumes; the composition is covered by
direct tests, together with the downstream Maxwellian rate average.

Evidence ceiling: the maintained tests compare the distribution and exponent
against an in-file loop-per-shift formulation, assert per-shift volume
normalization, the positive-shift axial moment, the uniform-distribution limit
when every exponent sits below the floor, the exact strict-interior clamp
witness, the molecule-count exponent scaling, and the full input contract
including the composition chain.  The environment-gated replay pins the saved
implementation by SHA-256; the saved bundle sits in the re-review archive
(strict D1 qualification withdrawn), so the replay is bounded historical
development evidence only.  This leaf deliberately excludes the saved source's
downstream moment-compensation loop -- the returned distribution is the seed
before compensation, not a converged distribution.
"""
from __future__ import annotations

import numpy as np

from .._validation import required_finite_scalar

__all__ = ["build_shifted_maxwellian_seed"]

AMU_KG = 1.6726231e-27
ELEMENTARY_CHARGE_C = 1.602177e-19


def build_shifted_maxwellian_seed(
    *,
    vr,
    vx,
    tnorm_ev,
    shifted_vx_m_s,
    temperature_ev,
    mass_amu,
    molecule_count,
    cylindrical_volume,
):
    """Return the normalized exponential seed in ``create_shifted_maxwellian``.

    Parameters
    ----------
    vr, vx
        Finite nonempty one-dimensional normalized radial-speed and
        axial-velocity meshes.
    tnorm_ev
        Positive scalar normalization temperature in eV; fixes the thermal
        speed that converts the shifts into mesh units.
    shifted_vx_m_s
        One-dimensional array of axial shifts in m/s.
    temperature_ev
        One-dimensional array of per-shift temperatures in eV, same length as
        the shifts; every entry finite and positive.
    mass_amu
        Positive scalar mass in amu.
    molecule_count
        Exactly ``1`` (atomic) or ``2`` (molecular hydrogen); scales the
        exponent.
    cylindrical_volume
        Finite strictly positive cell volumes with shape ``(vr.size,
        vx.size)``.

    Returns
    -------
    dict
        ``distribution`` (float64, shape ``(vr.size, vx.size, n_shifts)``,
        normalized per shift), ``thermal_speed_m_s`` (scalar), ``exponent``
        (raw exponent, shape as the distribution).

    Raises
    ------
    ValueError
        If an input leaves the domain stated above or the shapes are
        inconsistent.
    """
    radial = np.asarray(vr, dtype=float)
    axial = np.asarray(vx, dtype=float)
    shifts = np.asarray(shifted_vx_m_s, dtype=float)
    temperatures = np.asarray(temperature_ev, dtype=float)
    volume = np.asarray(cylindrical_volume, dtype=float)
    if (
        radial.ndim != 1
        or axial.ndim != 1
        or shifts.ndim != 1
        or temperatures.shape != shifts.shape
        or not radial.size
        or not axial.size
        or volume.shape != (radial.size, axial.size)
    ):
        raise ValueError("vr/vx/shift/temperature/volume shape contract is invalid")
    if tnorm_ev <= 0.0 or mass_amu <= 0.0 or molecule_count not in (1, 2) or np.any(
        temperatures <= 0.0
    ) or not all(
        np.all(np.isfinite(value))
        for value in (radial, axial, shifts, temperatures, volume)
    ) or np.any(volume <= 0.0):
        raise ValueError("physical inputs must be finite and positive where required")
    tnorm_ev = required_finite_scalar(tnorm_ev, "tnorm_ev", positive=True)
    mass_amu = required_finite_scalar(mass_amu, "mass_amu", positive=True)
    # Extreme-but-finite inputs can overflow the thermal speed or the raw
    # exponent; the overflow warnings are the conditions the explicit
    # representability checks below report as ValueError.
    with np.errstate(over="ignore", invalid="ignore"):
        thermal_speed = np.sqrt(2.0 * ELEMENTARY_CHARGE_C * tnorm_ev / (mass_amu * AMU_KG))
    if not np.isfinite(thermal_speed) or thermal_speed <= 0.0:
        raise ValueError(
            "the thermal speed is not representable for these finite inputs"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        argument = -(
            radial[:, None, None] ** 2
            + (axial[None, :, None] - shifts[None, None, :] / thermal_speed) ** 2
        ) * molecule_count * tnorm_ev / temperatures[None, None, :]
    if not bool(np.all(np.isfinite(argument))):
        raise ValueError(
            "the seed exponent is not representable for these finite inputs"
        )
    seed = np.exp(np.where(np.logical_and(-80.0 < argument, argument < 0.0), argument, -80.0))
    seed /= np.sum(volume[:, :, None] * seed, axis=(0, 1), keepdims=True)
    return {
        "distribution": seed,
        "thermal_speed_m_s": thermal_speed,
        "exponent": argument,
    }
