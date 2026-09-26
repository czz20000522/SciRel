"""Axisymmetric neutral velocity-space moment reduction.

One leaf recovered from the saved KN1DPy ``轴对称中性分布矩归约`` package
(source anchors ``KN1DPy/kinetic_h.py:1443-1605`` and
``kinetic_h2.py:1612-1801``, as recorded by the saved bundle's own
provenance), integrated as :func:`reduce_axisymmetric_neutral_moments`:

from an H or H2 one-dimensional-space, two-dimensional-axisymmetric velocity
distribution ``(nvr, nvx, nx)`` with the cylindrical cell-volume weight,
recover the density, axial flux and flow speed, pressure, temperature,
diagonal stresses and random heat flux of the saved source's moment
reduction, with the frozen constants ``m_H = 1.6726231e-27`` kg and
``e = 1.602177e-19`` J/eV and the thermal-speed normalization
``Vth = sqrt(2 e T_norm / (m_amu m_H))``.

**Two saved behaviors are preserved exactly and called out as open expert
questions.**

1. ``stress_zz_ev_m3`` is an alias copy of the ``y`` stress (the source's
   cylindrical symmetry identification ``sigma_zz = sigma_yy``), returned as
   an independent array copy.
2. The empty-slice policy: ``"reject"`` (this integration's default) raises
   when any spatial slice has nonpositive density; ``"source_default"``
   keeps the source-compatible zero-density semantics (flow speed
   ``0 m/s``, temperature ``1 eV``).  The saved formal implementation
   documents both branches; the default matches the saved test evidence,
   and the source-default branch is preserved verbatim for the caller who
   needs the source's initial-iteration behavior.

**Declared r60 pre-review tightenings are recorded.**  The saved arm does
not check the velocity axes', volume's, normalization-temperature's or
mass's finiteness (a NaN in any of them propagates NaN into the returned
moments), and it does not gate the outputs' finiteness.  This asset
fail-closes on non-finite axes, volume, temperature and mass scalars, and
on any non-finite returned field, per its exact document's finite-inputs
and finite-outputs contracts.  Each divergence is pinned by a regression
test and the saved-arm behavior is preserved as evidence.

**No repair is claimed otherwise.**  The saved validation contract (3-D
distribution aligned to the axes and volume, positive volume, positive
normalization temperature and mass, molecularity in {1, 2}, the explicit
quadrature reconstruction check ``volume == radial_weight x axial_weight``,
and the fail-closed policy enum) is reproduced bit for bit, messages
included.

Evidence ceiling: this module establishes the moment reduction against
independent recomputation and an independent Maxwellian-moment witness, the
quadrature reconstruction contract, and -- in the environment-gated replay
test -- exact agreement with the saved KN1DPy implementation.  The saved
bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "reduce_axisymmetric_neutral_moments",
]

_AMU_KG = 1.6726231e-27
_ELEMENTARY_CHARGE_C = 1.602177e-19


def reduce_axisymmetric_neutral_moments(
    distribution,
    vx,
    vr,
    cylindrical_volume,
    normalization_temperature_ev,
    isotope_mass_amu,
    molecularity,
    *,
    axial_quadrature=None,
    radial_quadrature=None,
    empty_slice_policy="reject",
):
    """Return the saved neutral moment diagnostics for one distribution.

    Parameters
    ----------
    distribution
        The velocity distribution as a finite ``(nvr, nvx, nx)`` array.
    vx, vr
        The axial and radial velocity-grid axes, finite one-dimensional
        arrays of lengths ``(nvx,)`` and ``(nvr,)``.
    cylindrical_volume
        The finite positive cylindrical cell volumes, shape ``(nvr, nvx)``.
    normalization_temperature_ev
        The positive normalization temperature in eV (scalar).
    isotope_mass_amu
        The positive isotope mass in amu (scalar).
    molecularity
        ``1`` for H or ``2`` for H2.
    axial_quadrature, radial_quadrature
        Optional one-dimensional positive weights aligned to the axes; when
        both are provided they must reconstruct ``cylindrical_volume``
        exactly and the saved source-order per-slice summation is used.
    empty_slice_policy
        ``"reject"`` (default) fails closed on any nonpositive-density
        spatial slice; ``"source_default"`` keeps the source-compatible
        zero-density semantics (flow ``0 m/s``, temperature ``1 eV``).

    Returns
    -------
    dict
        ``density_m3``, ``axial_flux_m2_s``, ``axial_velocity_m_s``,
        ``pressure_ev_m3``, ``temperature_ev``, ``stress_xx_ev_m3``,
        ``stress_yy_ev_m3``, ``stress_zz_ev_m3`` (an independent copy of the
        y stress, the source's cylindrical identification) and
        ``random_heat_flux_w_m2``, each with shape ``(nx,)``.

    Raises
    ------
    ValueError
        If any contract above is violated.
    """
    f = np.asarray(distribution, dtype=float)
    axial, radial, volume = (
        np.asarray(vx, dtype=float),
        np.asarray(vr, dtype=float),
        np.asarray(cylindrical_volume, dtype=float),
    )
    if (
        f.ndim != 3
        or f.shape[:2] != (radial.size, axial.size)
        or volume.shape != f.shape[:2]
        or not np.all(np.isfinite(f))
        or not np.all(np.isfinite(axial))
        or not np.all(np.isfinite(radial))
        or not np.all(np.isfinite(volume))
        or np.any(volume <= 0.0)
        or not np.isfinite(normalization_temperature_ev)
        or normalization_temperature_ev <= 0.0
        or not np.isfinite(isotope_mass_amu)
        or isotope_mass_amu <= 0.0
        or molecularity not in (1, 2)
        or empty_slice_policy not in ("reject", "source_default")
    ):
        raise ValueError("distribution, quadrature, and species contract is invalid")
    thermal_speed = np.sqrt(
        2.0 * _ELEMENTARY_CHARGE_C * normalization_temperature_ev / (isotope_mass_amu * _AMU_KG)
    )
    if (axial_quadrature is None) != (radial_quadrature is None):
        raise ValueError("axial_quadrature and radial_quadrature must be provided together")
    if axial_quadrature is None:
        density = np.sum(volume[:, :, None] * f, axis=(0, 1))
        axial_flux = thermal_speed * np.sum(
            volume[:, :, None] * axial[None, :, None] * f, axis=(0, 1)
        )
    else:
        axial_weight = np.asarray(axial_quadrature, dtype=float)
        radial_weight = np.asarray(radial_quadrature, dtype=float)
        if (
            axial_weight.ndim != 1
            or radial_weight.ndim != 1
            or axial_weight.size != axial.size
            or radial_weight.size != radial.size
            or not np.all(np.isfinite(axial_weight))
            or not np.all(np.isfinite(radial_weight))
            or np.any(axial_weight <= 0.0)
            or np.any(radial_weight <= 0.0)
            or not np.array_equal(volume, radial_weight[:, None] * axial_weight[None, :])
        ):
            raise ValueError("explicit quadrature must match cylindrical_volume")
        density = np.empty(f.shape[2], dtype=float)
        axial_flux = np.empty(f.shape[2], dtype=float)
        for k in range(f.shape[2]):
            density[k] = np.sum(radial_weight * (f[:, :, k] @ axial_weight))
            axial_flux[k] = thermal_speed * np.sum(
                radial_weight * (f[:, :, k] @ (axial * axial_weight))
            )
    valid_density = density > 0.0
    if np.any(~valid_density) and empty_slice_policy == "reject":
        raise ValueError("each spatial distribution slice must have positive density")
    axial_velocity = np.zeros_like(density)
    np.divide(axial_flux, density, out=axial_velocity, where=valid_density)
    normalized_flow = axial_velocity / thermal_speed
    random_speed_squared = radial[:, None, None] ** 2 + (
        axial[None, :, None] - normalized_flow[None, None, :]
    ) ** 2
    mass_kg = molecularity * isotope_mass_amu * _AMU_KG
    if axial_quadrature is None:
        pressure_ev_m3 = (
            mass_kg
            * thermal_speed**2
            * np.sum(volume[:, :, None] * random_speed_squared * f, axis=(0, 1))
            / (3.0 * _ELEMENTARY_CHARGE_C)
        )
        stress_xx_ev_m3 = (
            mass_kg
            * thermal_speed**2
            * np.sum(
                volume[:, :, None]
                * (axial[None, :, None] - normalized_flow[None, None, :]) ** 2
                * f,
                axis=(0, 1),
            )
            / _ELEMENTARY_CHARGE_C
            - pressure_ev_m3
        )
        stress_yy_ev_m3 = (
            mass_kg
            * thermal_speed**2
            * 0.5
            * np.sum(volume[:, :, None] * radial[:, None, None] ** 2 * f, axis=(0, 1))
            / _ELEMENTARY_CHARGE_C
            - pressure_ev_m3
        )
        heat_flux_w_m2 = 0.5 * mass_kg * thermal_speed**3 * np.sum(
            volume[:, :, None]
            * random_speed_squared
            * f
            * (axial[None, :, None] - normalized_flow[None, None, :]),
            axis=(0, 1),
        )
    else:
        pressure_ev_m3 = np.empty(f.shape[2], dtype=float)
        stress_xx_ev_m3 = np.empty(f.shape[2], dtype=float)
        stress_yy_ev_m3 = np.empty(f.shape[2], dtype=float)
        heat_flux_w_m2 = np.empty(f.shape[2], dtype=float)
        for k in range(f.shape[2]):
            pressure_ev_m3[k] = (
                mass_kg
                * thermal_speed**2
                * np.sum(
                    radial_weight
                    * ((random_speed_squared[:, :, k] * f[:, :, k]) @ axial_weight)
                )
                / (3.0 * _ELEMENTARY_CHARGE_C)
            )
            centered_axial = axial - normalized_flow[k]
            stress_xx_ev_m3[k] = (
                mass_kg
                * thermal_speed**2
                * np.sum(
                    radial_weight
                    * (f[:, :, k] @ (axial_weight * centered_axial**2))
                )
                / _ELEMENTARY_CHARGE_C
            )
            stress_yy_ev_m3[k] = (
                mass_kg
                * thermal_speed**2
                * 0.5
                * np.sum((radial_weight * radial**2) * (f[:, :, k] @ axial_weight))
                / _ELEMENTARY_CHARGE_C
            )
            heat_flux_w_m2[k] = (
                0.5
                * mass_kg
                * thermal_speed**3
                * np.sum(
                    radial_weight
                    * (
                        (random_speed_squared[:, :, k] * f[:, :, k])
                        @ (axial_weight * centered_axial)
                    )
                )
            )
    temperature_ev = (
        np.ones_like(density)
        if empty_slice_policy == "source_default"
        else np.empty_like(density)
    )
    np.divide(pressure_ev_m3, density, out=temperature_ev, where=valid_density)
    if axial_quadrature is not None:
        stress_xx_ev_m3 = stress_xx_ev_m3 - pressure_ev_m3
        stress_yy_ev_m3 = stress_yy_ev_m3 - pressure_ev_m3
    result = {
        "density_m3": density,
        "axial_flux_m2_s": axial_flux,
        "axial_velocity_m_s": axial_velocity,
        "pressure_ev_m3": pressure_ev_m3,
        "temperature_ev": temperature_ev,
        "stress_xx_ev_m3": stress_xx_ev_m3,
        "stress_yy_ev_m3": stress_yy_ev_m3,
        "stress_zz_ev_m3": stress_yy_ev_m3.copy(),
        "random_heat_flux_w_m2": heat_flux_w_m2,
    }
    # Declared r60 pre-review tightening: the saved arm's scalar gate misses
    # NaN normalization temperature / mass / volume, and a non-finite input
    # propagates NaN into the returned moments.  This asset fail-closes on
    # any non-finite returned field, per the exact document's finite-outputs
    # contract.
    if not all(np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("moment reduction produced a non-finite output")
    return result
