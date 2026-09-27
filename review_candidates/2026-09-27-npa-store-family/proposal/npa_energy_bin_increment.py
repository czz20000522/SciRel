"""FIDASIM NPA energy-bin and spectral-flux increment record.

Source: the saved package ``NPA能量通道通量增量`` (source anchor
``src/fidasim.f90:10600-10724``, the scalar part of ``store_npa``):
the stateless numerical slice that turns one neutral-particle hit into
the record the caller accumulates into its own ``(energy, detector,
class)`` flux storage.  The relation is
``energy = beam_mass * v2_to_E_per_amu * dot(v, v)``,
``dE = energy_grid(2) - energy_grid(1)``, the Fortran
``minloc(abs(energy_grid - energy))`` nearest-bin selection with the
first channel winning ties, the orbit class capped by
``min(orbit_class, nclass)``, and the non-accumulated
``flux / dE`` increment.  The caller owns the accumulator, the
active/passive grid choice, coordinates, hit production and the whole
NPA Monte Carlo; this leaf reads and mutates nothing.

The saved implementation is ported verbatim, including the source's
first-adjacent-center ``dE`` convention (not the local cell width).
Registered hardenings against the saved arm: the velocity vector
rejects boolean container entries and non-numeric items, the energy
centers reject boolean entries in container, bool dtype and object
form, ``detector_index_one_based``,
``orbit_class_one_based`` and ``class_count`` must be genuine integers
accepting ``np.integer`` while rejecting booleans (the saved arm's
bare ``isinstance(value, int)`` also rejected whole-number floats and
np.integer; float rejection is continuity, the np.integer acceptance
is the hardening), the first adjacent center spacing ``dE`` must be a
positive finite float and the resulting ``flux/dE`` increment
nonnegative finite (the saved arm returned
an ``inf`` increment for a subnormal spacing and a silent ``0.0``
increment when the spacing overflowed to ``inf``), and the computed
energy must stay finite (an overflow ceiling on huge velocities,
declared fail closed rather than silently binned through ``inf``).

The saved bundle's ledger *claims* a native source microprobe for this
relation (``npa_store_flux_audit`` against frozen source
``9019e945...``): three real ``store_npa`` calls replayed
``ACTIVE_1`` (the 50 keV first-of-tie ``minloc``), ``ACTIVE_2`` (the
73 keV nearest bin) and ``PASSIVE_1`` (passive storage and the class
cap) with ``max_abs = 0``. That evidence directory lies outside the
frozen saved input and could not be re-verified, so the review ceiling
is the package-level equation/boundary oracle plus the historical
ledger claim -- not re-verified Fortran runtime parity.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["select_npa_energy_bin_increment"]


def _genuine_positive_integer(value, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(
            f"{name} must be a genuine positive integer (registered hardening:"
            " the saved arm's isinstance(value, int) accepted bools while"
            " rejecting whole-number floats and np.integer)"
        )
    number = int(value)
    if number < 1:
        raise ValueError(f"{name} must be a positive integer")
    return number


def _contains_boolean(value) -> bool:
    """Detect boolean entries before numpy coerces them to floats.

    Covers plain containers element-wise (a mixed list such as
    ``[True, 2.0]`` becomes float64 at ``asarray`` time), bool dtype
    arrays, object arrays, and 0-d/2-d shapes alike; numpy arrays whose
    dtype is already float are accepted as-is because their booleans,
    if any, were lost at construction time and are not recoverable.
    """
    if isinstance(value, np.ndarray):
        if value.dtype == np.bool_:
            return True
        if value.dtype == np.object_:
            return any(isinstance(item, (bool, np.bool_)) for item in value.flat)
        return False
    if isinstance(value, (list, tuple)):
        return any(
            isinstance(item, (bool, np.bool_)) or _contains_boolean(item) for item in value
        )
    return isinstance(value, (bool, np.bool_))


def select_npa_energy_bin_increment(
    velocity_cm_s,
    beam_mass_amu,
    velocity_squared_to_energy_per_amu_kev_s2_cm_minus2,
    energy_centers_kev,
    detector_index_one_based,
    orbit_class_one_based,
    class_count,
    flux_neutrals_per_s,
):
    """Return the source nearest-bin, class-cap and ``flux/dE`` record."""
    # booleans must be inspected before numpy coerces them: a mixed list
    # or object array such as [True, 2.0] becomes float64 at asarray time
    if _contains_boolean(velocity_cm_s):
        raise ValueError(
            "velocity_cm_s must not contain boolean entries (registered hardening)"
        )
    try:
        velocity_array = np.asarray(velocity_cm_s, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("velocity_cm_s must be a finite 3-vector") from exc
    if velocity_array.shape != (3,) or not np.all(np.isfinite(velocity_array)):
        raise ValueError("velocity_cm_s must be a finite 3-vector")
    velocity = (float(velocity_array[0]), float(velocity_array[1]), float(velocity_array[2]))
    if _contains_boolean(energy_centers_kev):
        raise ValueError(
            "energy_centers_kev must not contain boolean entries (registered hardening)"
        )
    try:
        centers_raw = np.asarray(energy_centers_kev)
    except (TypeError, ValueError) as exc:
        raise ValueError("energy_centers_kev must be finite and strictly increasing") from exc
    if centers_raw.dtype == np.bool_ or (
        centers_raw.dtype == np.object_ and any(isinstance(item, (bool, np.bool_)) for item in centers_raw)
    ):
        raise ValueError(
            "energy_centers_kev must not contain boolean entries (registered hardening)"
        )
    try:
        centers_array = centers_raw.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError("energy_centers_kev must be finite and strictly increasing") from exc
    if centers_array.ndim != 1 or centers_array.size < 2 or not np.all(np.isfinite(centers_array)):
        raise ValueError("energy_centers_kev must be finite with length at least two")
    centers = tuple(float(value) for value in centers_array)
    scalars = (beam_mass_amu, velocity_squared_to_energy_per_amu_kev_s2_cm_minus2, flux_neutrals_per_s)
    if any(isinstance(value, (bool, np.bool_)) for value in scalars) or not all(
        math.isfinite(float(value)) for value in scalars
    ):
        raise ValueError(
            "beam_mass_amu, the conversion constant and the flux must be finite scalars"
            " (registered hardening: booleans rejected)"
        )
    beam_mass_amu = float(beam_mass_amu)
    conversion = float(velocity_squared_to_energy_per_amu_kev_s2_cm_minus2)
    flux = float(flux_neutrals_per_s)
    if beam_mass_amu <= 0.0 or conversion <= 0.0 or flux < 0.0:
        raise ValueError("mass and conversion must be positive; flux must be nonnegative")
    if any(b <= a for a, b in zip(centers, centers[1:])):
        raise ValueError("energy_centers_kev must be strictly increasing")
    detector = _genuine_positive_integer(detector_index_one_based, name="detector_index_one_based")
    orbit_class = _genuine_positive_integer(orbit_class_one_based, name="orbit_class_one_based")
    class_count = _genuine_positive_integer(class_count, name="class_count")
    energy_kev = beam_mass_amu * conversion * sum(value * value for value in velocity)
    if not math.isfinite(energy_kev):
        raise ValueError(
            "the computed particle energy is not finite for the supplied velocity and"
            " mass (registered hardening: an overflowing velocity must not be binned"
            " through inf)"
        )
    bin_index = min(range(len(centers)), key=lambda index: abs(centers[index] - energy_kev))
    bin_width_kev = centers[1] - centers[0]
    if not (math.isfinite(bin_width_kev) and bin_width_kev > 0.0):
        raise ValueError(
            "the first adjacent center spacing dE must be a positive finite float"
            " (r81 repair: the saved arm returned an inf increment for a subnormal"
            " spacing and a silent 0.0 increment when the spacing overflowed to inf)"
        )
    increment = flux / bin_width_kev
    if not math.isfinite(increment):
        raise ValueError(
            "the spectral flux increment flux/dE is not finite for the supplied flux and"
            " grid (r81 repair: the exact document declares the increment finite"
            " nonnegative)"
        )
    return {
        "energy_kev": energy_kev,
        "energy_bin_one_based": bin_index + 1,
        "detector_index_one_based": detector,
        "class_index_one_based": min(orbit_class, class_count),
        "spectral_flux_increment_per_kev": increment,
    }
