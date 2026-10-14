"""GSEQ axisymmetric filament-coil Green response after elliptic evaluation.

Source: GSEQ ``second_paper/Fig5/gui/fun_Bfield.m:10-27`` (``imethod==1``):
per coil, the closed-form Green formulas give the poloidal flux
``psi = R A_phi`` (``Wb/rad`` convention), the radial field ``B_r`` and the
axial field ``B_z`` responses, summed linearly over coils.  Current and turns
enter only through the combined factor ``2e-7 * turns * current``; the
modulus and ``K, E`` pairings are per-coil by index.  The operator consumes
the *already regularized* observation radius (the source's ``r0 + 1e-8``
offset applied once by the geometry operator) and does not offset again.

This is the GSEQ variant of the same circular-filament physics as the
baseline ``scirel.field.circular-filament-green`` asset: the baseline
evaluates ``scipy.special.ellipk/ellipe`` at arbitrary (R, Z) point arrays
with per-point moduli, while this operator takes the source's own
polynomial-logarithmic ``K, E`` approximation supplied per coil and scalar
observation coordinates.  The implementations are intentionally kept
separate; the approximation-accuracy gap is quantified in the companion
elliptic-integral operator's documentation.

Failure-closed: non-singular inputs only.  Two singular boundaries are
handled by explicit rejection instead of the source's silent numeric
behavior: (i) geometrically singular coil configurations where the
observation point lies on a filament ring (``separation == 0``, i.e.
``modulus == 1`` -- for such inputs the source's own elliptic approximation
emits its finite sentinel ``K = 1e300`` or ``K = +Inf, E = NaN``, and the
closed form then produces ``0 * Inf = NaN`` responses which the saved
implementation returns silently) raise ``ValueError`` here; (ii) the
input-level validations below reject non-positive radii, out-of-range
moduli and misaligned pairings.  The companion elliptic-integral operator
now evaluates its mathematical endpoint as K(1)=+Inf and E(1)=1
pointwise. This downstream field operator still rejects coincident filament
geometry; a mathematically correct elliptic limit does not remove the physical
line-current field singularity.
"""
from __future__ import annotations

import numpy as np

__all__ = ["evaluate_filament_coil_green_field"]

MU0_OVER_2PI = 2.0e-7


def evaluate_filament_coil_green_field(regularized_radius_m, observation_z_m, coil_radius_m, coil_z_m, current_a, turns, modulus_squared, complete_k, complete_e):
    """Sum source imethod==1 filament-coil flux, Br, and Bz contributions."""
    radius = float(regularized_radius_m)
    arrays = [np.asarray(value, dtype=float) for value in (coil_radius_m, coil_z_m, current_a, turns, modulus_squared, complete_k, complete_e)]
    coil_radius, coil_z, current, winding, modulus, k, e = arrays
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError("regularized observation coordinates must be finite and positive in radius")
    if any(value.ndim != 1 or value.shape != coil_radius.shape for value in arrays) or not all(np.all(np.isfinite(value)) for value in (coil_radius, coil_z, current, winding, modulus)) or np.any(coil_radius <= 0.0) or np.any(modulus <= 0.0) or np.any(modulus > 1.0) or np.any(~np.isfinite(e)) or np.any(~np.isfinite(k) & (modulus != 1.0)):
        raise ValueError("coil inputs and elliptic values must be same-shape vectors with valid geometry")
    dz = observation_z_m - coil_z
    distance = np.sqrt((radius + coil_radius) ** 2 + dz**2)
    separation2 = (radius - coil_radius) ** 2 + dz**2
    if np.any(separation2 <= 0.0) or np.any(modulus >= 1.0):
        # Registered hardening: the source returns NaN responses (via its
        # K/E sentinel and 0*Inf terms) when the observation point lies on a
        # filament ring; this port rejects the configuration instead.
        raise ValueError(
            "singular coil geometry: observation point on a filament ring "
            "(zero separation, modulus == 1); the source's NaN response is "
            "rejected rather than returned")
    factor = MU0_OVER_2PI * winding * current
    flux = np.sum(factor / np.sqrt(modulus) * np.sqrt(radius * coil_radius) * ((2.0 - modulus) * k - 2.0 * e))
    br = np.sum(factor * dz / radius / distance * ((radius**2 + coil_radius**2 + dz**2) / separation2 * e - k))
    bz = np.sum(factor / distance * ((coil_radius**2 - radius**2 - dz**2) / separation2 * e + k))
    # Registered hardening: finite extreme inputs (e.g. current = turns =
    # 1e308) can overflow the combined factor and the responses; the saved
    # implementation would return them silently, this port fails closed.
    for name, value in (("flux_weber", flux), ("radial_field_t", br), ("axial_field_t", bz)):
        if not np.isfinite(value):
            raise ValueError(
                f"{name} overflowed to a non-finite value; finite but extreme "
                "input magnitudes are rejected (registered hardening)")
    return float(flux), float(br), float(bz)
