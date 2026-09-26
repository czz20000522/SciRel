"""Incoming neutral boundary-flux normalization over the positive-vx half.

One leaf recovered from the saved KN1DPy ``入射中性边界通量归一化`` package
(source anchor ``KN1DPy/kinetic_h.py:600-616`` and ``kinetic_h2.py:715-731``,
as recorded by the saved bundle's own provenance), integrated as
:func:`normalize_incoming_neutral_boundary`:

scale a caller-owned H or H2 boundary shape distribution on the positive
axial-velocity half space to a requested incoming neutral particle flux,
returning the scaled incoming boundary distribution, the applied scalar
scale, and the pre-scale incoming flux integral
``Vth * sum(volume * shape * vx)`` over ``vx > 0``.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (finite two-dimensional boundary shape with the axial axis
as the second dimension, an equal-shape nonnegative cylindrical volume,
positive thermal speed, finite target flux, at least one positive ``vx``
node, and a strictly positive positive-half flux integral) and is reproduced
bit for bit, messages included.  The negative half of the returned
distribution is exactly zero (the source's incoming-boundary semantics), and
the scale is ``abs(target_flux) / incoming_flux`` exactly as saved -- a
negative requested flux produces the same positive scale (flux direction is
carried by the sign convention of the caller's profile, not by the scale).

Evidence ceiling: this module establishes the normalization against
independent recomputation of the flux integral, the fail-closed contracts,
and -- in the environment-gated replay test -- exact agreement with the
saved KN1DPy implementation.  The saved bundle's strict D1 qualification has
been withdrawn; that replay is historical development evidence, not
qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "normalize_incoming_neutral_boundary",
]


def normalize_incoming_neutral_boundary(
    boundary_shape, vx, cylindrical_volume, thermal_speed_m_s, target_flux_m2_s
):
    """Scale the positive-vx source shape to the source desired incoming flux.

    Parameters
    ----------
    boundary_shape
        The caller's boundary shape as a finite nonnegative ``(nvr, nvx)``
        array (axial velocity on the second axis).
    vx
        The axial velocity axis, a finite one-dimensional ``(nvx,)`` array
        containing at least one positive node.
    cylindrical_volume
        The cylindrical quadrature weight, finite, shape ``(nvr, nvx)``.
    thermal_speed_m_s
        The positive thermal speed in ``m/s`` (the :doc:`thermal speed scale
        <thermal_speed_scale>` of the species).
    target_flux_m2_s
        The requested incoming particle flux in ``m^-2 s^-1`` (finite).

    Returns
    -------
    tuple
        ``(incoming_boundary, scale, incoming_flux)``: the scaled boundary
        distribution (zero on the nonpositive-vx half), the applied positive
        scale, and the pre-scale positive-half flux integral.

    Raises
    ------
    ValueError
        If any contract above is violated.
    """
    shape = np.asarray(boundary_shape, dtype=float)
    axial, volume = np.asarray(vx, dtype=float), np.asarray(cylindrical_volume, dtype=float)
    if (
        shape.ndim != 2
        or shape.shape[1] != axial.size
        or volume.shape != shape.shape
        or not np.all(np.isfinite(shape))
        or np.any(shape < 0.0)
        or thermal_speed_m_s <= 0.0
        or not np.isfinite(target_flux_m2_s)
    ):
        raise ValueError(
            "boundary shape, quadrature, thermal speed, or target flux is invalid"
        )
    positive = axial > 0.0
    if not np.any(positive):
        raise ValueError("vx must contain a positive incoming half")
    incoming_flux = thermal_speed_m_s * np.sum(
        volume[:, positive] * shape[:, positive] * axial[None, positive]
    )
    if incoming_flux <= 0.0:
        raise ValueError("positive-vx boundary shape must have positive flux")
    scale = abs(target_flux_m2_s) / incoming_flux
    incoming_boundary = np.zeros_like(shape)
    incoming_boundary[:, positive] = shape[:, positive] * scale
    return incoming_boundary, float(scale), float(incoming_flux)
