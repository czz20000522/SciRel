"""Build a normalized shifted-Maxwellian seed on an explicit cylindrical velocity mesh."""
from __future__ import annotations

import numpy as np

from .._validation import required_finite_scalar, required_integer_scalar

__all__ = ["build_shifted_maxwellian_seed"]

AMU_KG = 1.6726231e-27
ELEMENTARY_CHARGE_C = 1.602177e-19


def _real_array(name, value):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def _positive_scalar(name, value):
    return required_finite_scalar(_real_array(name, value), name, positive=True)


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
        Nonempty one-dimensional array of axial shifts in m/s.
    temperature_ev
        One-dimensional array of per-shift temperatures in eV, same length as
        the shifts; every entry finite and positive.
    mass_amu
        Positive scalar factor relative to the saved hydrogen mass
        (1.6726231e-27 kg), despite the historical parameter name.
    molecule_count
        Integer scalar: exactly ``1`` (atomic) or ``2`` (molecular hydrogen);
        scales the exponent.
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
        If an input leaves the domain stated above, including empty shift
        arrays, or the shapes are inconsistent.
    """
    radial = _real_array("vr", vr)
    axial = _real_array("vx", vx)
    shifts = _real_array("shifted_vx_m_s", shifted_vx_m_s)
    temperatures = _real_array("temperature_ev", temperature_ev)
    volume = _real_array("cylindrical_volume", cylindrical_volume)
    if (
        radial.ndim != 1
        or axial.ndim != 1
        or shifts.ndim != 1
        or temperatures.shape != shifts.shape
        or not radial.size
        or not axial.size
        or not shifts.size
        or volume.shape != (radial.size, axial.size)
    ):
        raise ValueError(
            "vr, vx, shifted_vx_m_s, temperature_ev and cylindrical_volume "
            "must have compatible nonempty shapes"
        )
    for name, array in (
        ("vr", radial), ("vx", axial), ("shifted_vx_m_s", shifts),
        ("temperature_ev", temperatures), ("cylindrical_volume", volume),
    ):
        if not bool(np.all(np.isfinite(array))):
            raise ValueError(f"{name} must be finite")
    if bool(np.any(temperatures <= 0.0)):
        raise ValueError("temperature_ev must be strictly positive")
    if bool(np.any(volume <= 0.0)):
        raise ValueError("cylindrical_volume must be strictly positive")
    tnorm_ev = _positive_scalar("tnorm_ev", tnorm_ev)
    mass_amu = _positive_scalar("mass_amu", mass_amu)
    molecule_count = required_integer_scalar(molecule_count, "molecule_count", minimum=1)
    if molecule_count > 2:
        raise ValueError("physical input molecule_count must be 1 or 2")
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
    with np.errstate(over="ignore", invalid="ignore"):
        seed = np.exp(np.where(np.logical_and(-80.0 < argument, argument < 0.0), argument, -80.0))
        seed /= np.sum(volume[:, :, None] * seed, axis=(0, 1), keepdims=True)
    # Extreme-but-finite volumes can make the normalization denominator
    # underflow (the divided distribution overflows to infinity) or overflow
    # (the divided distribution collapses to exact zeros); either way the
    # finite, strictly-positive contract is violated and the call fails closed.
    if not bool(np.all(np.isfinite(seed))) or not bool(np.all(seed > 0.0)):
        raise ValueError(
            "the normalized seed distribution is not representable for these finite inputs"
        )
    return {
        "distribution": seed,
        "thermal_speed_m_s": thermal_speed,
        "exponent": argument,
    }
