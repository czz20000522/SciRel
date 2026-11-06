"""Axisymmetric neutral velocity-space moment reduction.

One leaf recovered from the saved the neutral-transport formulation ``轴对称中性分布矩归约`` package, integrated as :func:`reduce_axisymmetric_neutral_moments`:

from an H or H2 one-dimensional-space, two-dimensional-axisymmetric velocity
distribution ``(nvr, nvx, nx)`` with the cylindrical cell-volume weight,
recover the density, axial flux and flow speed, pressure, temperature,
diagonal stresses and random heat flux of the saved source's moment
reduction, with the frozen constants ``m_H = 1.6726231e-27`` kg and
``e = 1.602177e-19`` J/eV and the thermal-speed normalization
``Vth = sqrt(2 e T_norm / (m_amu m_H))``.  The historical
``isotope_mass_amu`` name denotes a factor of this saved hydrogen mass,
not the standard atomic mass unit.

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

This integration also rejects boolean, numeric-string and complex array
coercions, nonnumeric scalar inputs and noninteger molecularity before
arithmetic.  The saved finite real-valued calculation and its summation order
remain unchanged.

Evidence ceiling: this module establishes the moment reduction against
independent recomputation and an independent Maxwellian-moment witness, the
quadrature reconstruction contract, and bounded read-only comparisons with
the saved the neutral-transport formulation implementation.  The saved bundle's strict D1 qualification
has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "reduce_axisymmetric_neutral_moments",
]

_HYDROGEN_MASS_KG = 1.6726231e-27
_ELEMENTARY_CHARGE_C = 1.602177e-19


def _real_array(name, value):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real-valued numeric values") from exc


def _numeric_scalar(name, value):
    raw = _real_array(name, value)
    if raw.ndim != 0:
        raise ValueError(f"{name} must be a real numeric scalar")
    return float(raw)


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
    """Reduce an H or H2 axisymmetric neutral distribution to nine moment profiles.

    Parameters
    ----------
    distribution : array_like, shape (nvr, nvx, nx)
        Finite real velocity distribution aligned with ``vr`` and ``vx``;
        boolean, string and complex coercions are rejected. [source-normalized]
    vx : array_like, shape (nvx,)
        Finite axial velocity axis. [source-normalized]
    vr : array_like, shape (nvr,)
        Finite radial velocity axis. [source-normalized]
    cylindrical_volume : array_like, shape (nvr, nvx)
        Finite strictly positive cylindrical cell-volume weights aligned with the
        velocity axes. [source-normalized measure]
    normalization_temperature_ev : float
        Positive finite normalization temperature. [eV]
    isotope_mass_amu : float
        Positive finite mass factor relative to the saved hydrogen mass
        ``1.6726231e-27`` kg; the historical name does not mean the standard
        atomic mass unit. [multiples of saved hydrogen mass (1.6726231e-27 kg)]
    molecularity : int
        Exactly ``1`` for H or ``2`` for H2. [dimensionless enum]
    axial_quadrature : array_like, shape (nvx,), optional
        Positive explicit axial weights. It must be supplied together with
        ``radial_quadrature``; their outer product must equal
        ``cylindrical_volume`` exactly. The default is ``None``. [source-normalized measure]
    radial_quadrature : array_like, shape (nvr,), optional
        Positive explicit radial weights. It must be supplied together with
        ``axial_quadrature``. The default is ``None``. [source-normalized measure]
    empty_slice_policy : {'reject', 'source_default'}, optional
        Policy for spatial slices with nonpositive density. ``'reject'`` (the
        default) raises; ``'source_default'`` preserves zero flow and temperature
        ``1 eV``. [dimensionless enum]

    Returns
    -------
    moments : mapping
        A mapping with exactly ``density_m3``, ``axial_flux_m2_s``,
        ``axial_velocity_m_s``, ``pressure_ev_m3``, ``temperature_ev``,
        ``stress_xx_ev_m3``, ``stress_yy_ev_m3``, ``stress_zz_ev_m3`` and
        ``random_heat_flux_w_m2``. Each value is a finite ``float64`` array with
        shape ``(nx,)``. ``stress_zz_ev_m3`` is an independent copy of
        ``stress_yy_ev_m3``. [mixed (see constraints)]

    Raises
    ------
    ValueError
        If the distribution, axes, volume, quadrature, species controls or policy
        are invalid, a ``reject`` slice has nonpositive density, or a returned
        moment is non-finite.

    See Also
    --------
    compute_thermal_speed_m_s : Computes the thermal speed used by this reduction.
    reduce_generation_density : Reduces a generation distribution to cell density.
    reduce_terminal_molecular_flux_velocity : Terminal flux and flow diagnostic.

    Notes
    -----
    With ``weighted = cylindrical_volume * distribution``, density is the sum of
    ``weighted`` over both velocity axes and axial flux is ``Vth`` times the sum
    of ``vx * weighted``. Flow is flux divided by positive density. The pressure
    is the one-third trace of the centered second moment in eV m^-3; the diagonal
    stresses and random heat flux use the same centered velocity field. The
    terminal stress identification is exactly ``stress_zz_ev_m3 =
    stress_yy_ev_m3`` as an independent copy; this records the saved cylindrical
    convention and is not a stand-alone proof that the stress model is physically
    complete. Explicit quadrature switches to the documented per-slice summation
    order and must reconstruct the supplied volume.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import compute_thermal_speed_m_s, reduce_axisymmetric_neutral_moments
    >>> vr = (np.arange(160) + 0.5) * (4.0 / 160)
    >>> vx = -4.0 + (np.arange(200) + 0.5) * (10.0 / 200)
    >>> volume = np.outer(vr * (4.0 / 160), np.full(200, 10.0 / 200))
    >>> vth = compute_thermal_speed_m_s(2.0, 1.0)['thermal_speed_m_s']
    >>> vr_grid, vx_grid = np.meshgrid(vr, vx, indexing='ij')
    >>> shift = 3.0e3 / vth
    >>> f = np.exp(-(vr_grid[:, :, None] ** 2 + (vx_grid[:, :, None] - shift) ** 2))
    >>> f = np.broadcast_to(f, (160, 200, 1)).copy()
    >>> result = reduce_axisymmetric_neutral_moments(f, vx, vr, volume, normalization_temperature_ev=2.0, isotope_mass_amu=1.0, molecularity=1)
    >>> assert abs(result['axial_velocity_m_s'][0] - 3.0e3) < 0.02 * 3.0e3
    >>> assert abs(result['temperature_ev'][0] - 2.0) < 0.05 * 2.0
    >>> assert np.array_equal(result['stress_zz_ev_m3'], result['stress_yy_ev_m3'])
    >>> zero = np.zeros_like(f)
    >>> try:
    ...     reduce_axisymmetric_neutral_moments(zero, vx, vr, volume, normalization_temperature_ev=2.0, isotope_mass_amu=1.0, molecularity=1)
    ... except ValueError as error:
    ...     assert 'positive density' in str(error)
    ... else:
    ...     raise AssertionError('a zero-density slice must be rejected under the default policy')

    """
    f = _real_array("distribution", distribution)
    axial = _real_array("vx", vx)
    radial = _real_array("vr", vr)
    volume = _real_array("cylindrical_volume", cylindrical_volume)
    if axial.ndim != 1:
        raise ValueError("vx must be a one-dimensional array")
    if radial.ndim != 1:
        raise ValueError("vr must be a one-dimensional array")
    normalization_temperature_ev = _numeric_scalar(
        "normalization_temperature_ev", normalization_temperature_ev
    )
    isotope_mass_amu = _numeric_scalar("isotope_mass_amu", isotope_mass_amu)
    if isinstance(molecularity, (bool, np.bool_)) or not isinstance(
        molecularity, (int, np.integer)
    ):
        raise ValueError("molecularity must be an integer scalar")
    if (
        f.ndim != 3
        or axial.ndim != 1
        or radial.ndim != 1
        or volume.ndim != 2
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
    normalization_mass_kg = isotope_mass_amu * _HYDROGEN_MASS_KG
    if not np.isfinite(normalization_mass_kg) or normalization_mass_kg <= 0.0:
        raise ValueError("thermal speed must be finite and positive")
    with np.errstate(over="ignore", divide="ignore", invalid="ignore", under="ignore"):
        thermal_speed = np.sqrt(
            2.0 * _ELEMENTARY_CHARGE_C * normalization_temperature_ev / normalization_mass_kg
        )
    if not np.isfinite(thermal_speed) or thermal_speed <= 0.0:
        raise ValueError("thermal speed must be finite and positive")
    if (axial_quadrature is None) != (radial_quadrature is None):
        raise ValueError("axial_quadrature and radial_quadrature must be provided together")
    if axial_quadrature is None:
        weighted_distribution = volume[:, :, None] * f
        density = np.sum(weighted_distribution, axis=(0, 1))
        axial_flux = thermal_speed * np.sum(
            axial[None, :, None] * weighted_distribution, axis=(0, 1)
        )
    else:
        axial_weight = _real_array("axial_quadrature", axial_quadrature)
        radial_weight = _real_array("radial_quadrature", radial_quadrature)
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
        axial_integrals = np.empty((radial.size, f.shape[2]), dtype=float)
        axial_weighted = axial * axial_weight
        for k in range(f.shape[2]):
            axial_integral = f[:, :, k] @ axial_weight
            axial_integrals[:, k] = axial_integral
            density[k] = np.sum(radial_weight * axial_integral)
            axial_flux[k] = thermal_speed * np.sum(radial_weight * (f[:, :, k] @ axial_weighted))
    valid_density = density > 0.0
    if np.any(~valid_density) and empty_slice_policy == "reject":
        raise ValueError("each spatial distribution slice must have positive density")
    axial_velocity = np.zeros_like(density)
    np.divide(axial_flux, density, out=axial_velocity, where=valid_density)
    normalized_flow = axial_velocity / thermal_speed
    random_speed_squared = (
        radial[:, None, None] ** 2 + (axial[None, :, None] - normalized_flow[None, None, :]) ** 2
    )
    mass_kg = molecularity * isotope_mass_amu * _HYDROGEN_MASS_KG
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
        heat_flux_w_m2 = (
            0.5
            * mass_kg
            * thermal_speed**3
            * np.sum(
                volume[:, :, None]
                * random_speed_squared
                * f
                * (axial[None, :, None] - normalized_flow[None, None, :]),
                axis=(0, 1),
            )
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
                    radial_weight * ((random_speed_squared[:, :, k] * f[:, :, k]) @ axial_weight)
                )
                / (3.0 * _ELEMENTARY_CHARGE_C)
            )
            centered_axial = axial - normalized_flow[k]
            stress_xx_ev_m3[k] = (
                mass_kg
                * thermal_speed**2
                * np.sum(radial_weight * (f[:, :, k] @ (axial_weight * centered_axial**2)))
                / _ELEMENTARY_CHARGE_C
            )
            stress_yy_ev_m3[k] = (
                mass_kg
                * thermal_speed**2
                * 0.5
                * np.sum((radial_weight * radial**2) * axial_integrals[:, k])
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
        np.ones_like(density) if empty_slice_policy == "source_default" else np.empty_like(density)
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
