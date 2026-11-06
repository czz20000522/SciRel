"""Discrete velocity moment compensation for a supplied cylindrical mesh."""

from __future__ import annotations

import warnings

import numpy as np

from .cylindrical_velocity_quadrature import make_cylindrical_velocity_quadrature

__all__ = ["compensate_velocity_slice", "build_compensated_shifted_maxwellian"]


HYDROGEN_MASS = 1.6726231e-27
CHARGE = 1.602177e-19


def _cell_fields(quadrature):
    required = (
        "dvr_vol",
        "dvx",
        "dvr",
        "volume",
        "speed_squared",
        "vx_pos_first_index",
        "vx_pos_last_index",
        "vx_neg_first_index",
        "vx_neg_last_index",
    )
    if isinstance(quadrature, dict):
        radial_measure = quadrature["radial_measure"]
        return {
            "dvr_vol": radial_measure,
            "dvx": quadrature["dvx"],
            "dvr": quadrature["vr_right"] - quadrature["vr_left"],
            "volume": quadrature["volume"],
            "speed_squared": quadrature["speed_squared"],
            "vx_pos_first_index": quadrature["positive_vx_first_index"],
            "vx_pos_last_index": quadrature["positive_vx_last_index"],
            "vx_neg_first_index": quadrature["negative_vx_first_index"],
            "vx_neg_last_index": quadrature["negative_vx_last_index"],
        }
    return {name: getattr(quadrature, name) for name in required}


def _slice_moments(f_slice, fields, vx, vth):
    """Return density, mean vx [m/s] and mean speed squared [m^2/s^2] of one slice."""
    dvr_vol, dvx = fields["dvr_vol"], fields["dvx"]
    density = np.sum(dvr_vol * np.matmul(f_slice, dvx))
    mean_vx = vth * np.sum(dvr_vol * np.matmul(f_slice, vx * dvx)) / density
    mean_energy = (
        vth**2 * np.sum(dvr_vol * np.matmul(fields["speed_squared"] * f_slice, dvx)) / density
    )
    return density, mean_vx, mean_energy


def compensate_velocity_slice(
    f_slice,
    quadrature,
    vr,
    vx,
    vth,
    target_vx,
    target_energy,
    nb=1.0,
    assume_pos=True,
    moment_rtol=0.01,
):
    """Adjust one slice toward target drift and energy moments.

    The caller supplies the output of :func:`make_cylindrical_velocity_quadrature`.
    The four sign combinations and optional signed-distribution cutoff follow
    the bounded source transcription; no iterative convergence claim is made.

    Warns
    -----
    RuntimeWarning
        If the corrected slice misses the targets by more than ``moment_rtol``
        once normalized by its own density, or its density changed by more than
        that. The correction is linear in the targets and does not conserve
        density, so a mesh too small for the distribution can miss badly.

    Notes
    -----
    Errors are relative: the drift to ``sqrt(target_energy)``, the energy and the
    density to the target energy and ``nb``.
    """
    result, scale = _compensate_slice(
        f_slice, quadrature, vr, vx, vth, target_vx, target_energy, nb, assume_pos
    )
    fields = _cell_fields(quadrature)
    density, mean_vx, mean_energy = _slice_moments(result, fields, np.asarray(vx), vth)
    speed = np.sqrt(abs(target_energy))
    errors = (
        abs(density / nb - 1.0),
        abs(mean_vx - target_vx) / speed if speed > 0.0 else 0.0,
        abs(mean_energy / target_energy - 1.0) if target_energy != 0.0 else 0.0,
    )
    if max(errors) > moment_rtol:
        warnings.warn(
            "velocity slice missed its moment targets: relative density, drift and energy errors "
            f"{errors[0]:.3g}, {errors[1]:.3g}, {errors[2]:.3g} exceed {moment_rtol:g}; "
            "the velocity mesh may not represent this distribution",
            RuntimeWarning,
            stacklevel=2,
        )
    return result, scale


def _compensate_slice(f_slice, quadrature, vr, vx, vth, target_vx, target_energy, nb, assume_pos):
    """Apply the source-shaped two-coefficient correction once."""
    fields = _cell_fields(quadrature)
    dvr_vol, dvx = fields["dvr_vol"], fields["dvx"]
    dvr, volume = fields["dvr"], fields["volume"]
    speed_squared = fields["speed_squared"]
    vr = np.asarray(vr)
    vx = np.asarray(vx)
    vr_n, vx_n = vr.size, vx.size
    vth_diffs = np.zeros((vr_n, vx_n, 2), dtype=float)
    vrvx_diffs = np.zeros((vr_n, vx_n, 2), dtype=float)
    signs = (1.0, -1.0)
    vx_moment = vth * np.sum(dvr_vol * np.matmul(f_slice, vx * dvx)) / nb
    energy_moment = vth**2 * np.sum(dvr_vol * np.matmul(speed_squared * f_slice, dvx)) / nb
    weighted = np.zeros((vr_n + 2, vx_n + 2), dtype=np.float64)
    rs, xs = slice(1, vr_n + 1), slice(1, vx_n + 1)
    weighted[rs, xs] = f_slice * volume / nb
    allow_neg = False
    if not assume_pos:
        cutoff = 1.0e-6 * np.max(weighted)
        small = np.where((np.abs(weighted) < cutoff) & (np.abs(weighted) > 0))
        if small[0].size:
            weighted[small] = 0.0
        if max(weighted[2, :]) <= 0:
            allow_neg = True
    vx_dist = np.zeros_like(weighted)
    vr_dist = np.zeros_like(weighted)
    vth_dist = np.zeros_like(weighted)
    vx_dist[rs, xs] = weighted[rs, xs] * (vx / dvx)
    vr_dist[rs, xs] = weighted[rs, xs] * (vr[:, None] / dvr[:, None])
    vth_dist[rs, xs] = weighted[rs, xs] / dvx
    rolled = np.roll(vth_dist, 1, axis=1) - vth_dist
    vth_diffs[:, :, 0] = rolled[rs, xs]
    rolled = -np.roll(vth_dist, -1, axis=1) + vth_dist
    vth_diffs[:, :, 1] = rolled[rs, xs]
    ps, pe = fields["vx_pos_first_index"], fields["vx_pos_last_index"]
    ns, ne = fields["vx_neg_first_index"], fields["vx_neg_last_index"]
    vrvx_diffs[:, ps + 1 : pe + 1, 0] = vx_dist[rs, ps + 1 : pe + 1] - vx_dist[rs, ps + 2 : pe + 2]
    vrvx_diffs[:, ps, 0] = -vx_dist[rs, ps + 1]
    vrvx_diffs[:, ne, 0] = vx_dist[rs, ne + 1]
    vrvx_diffs[:, ns:ne, 0] = -vx_dist[rs, ns + 2 : ne + 2] + vx_dist[rs, ns + 1 : ne + 1]
    vrvx_diffs[:, :, 0] += vr_dist[:vr_n, xs] - vr_dist[rs, xs]
    vrvx_diffs[:, ps + 1 : pe + 1, 1] = -vx_dist[rs, ps + 3 : pe + 3] + vx_dist[rs, ps + 2 : pe + 2]
    vrvx_diffs[:, ps, 1] = -vx_dist[rs, ps + 2]
    vrvx_diffs[:, ne, 1] = vx_dist[rs, ne]
    vrvx_diffs[:, ns:ne, 1] = vx_dist[rs, ns:ne] - vx_dist[rs, ns + 1 : ne + 1]
    vrvx_diffs[1:vr_n, :, 1] += vr_dist[2 : vr_n + 1, xs] - vr_dist[3 : vr_n + 2, xs]
    vrvx_diffs[0, :, 1] -= vr_dist[2, xs]
    if allow_neg:
        vrvx_diffs[0, :, 1] -= vr_dist[1, xs]
        vrvx_diffs[1, :, 1] += vr_dist[1, xs]
    weighted = weighted[rs, xs]
    tb1 = np.zeros(2, dtype=float)
    tb2 = np.zeros(2, dtype=float)
    do_break = False
    for ia in range(2):
        ta1 = vth * np.sum(np.matmul(vth_diffs[:, :, ia], vx))
        ta2 = vth**2 * np.sum(speed_squared * vth_diffs[:, :, ia])
        for ib in range(2):
            if tb1[ib] == 0:
                tb1[ib] = vth * np.sum(np.matmul(vrvx_diffs[:, :, ib], vx))
            if tb2[ib] == 0:
                tb2[ib] = vth**2 * np.sum(speed_squared * vrvx_diffs[:, :, ib])
            denom = ta2 * tb1[ib] - ta1 * tb2[ib]
            vrvx_scalar = 0.0
            vth_scalar = 0.0
            if denom != 0 and ta1 != 0:
                vrvx_scalar = (
                    ta2 * (target_vx - vx_moment) - ta1 * (target_energy - energy_moment)
                ) / denom
                vth_scalar = (target_vx - vx_moment - tb1[ib] * vrvx_scalar) / ta1
            do_break = (vth_scalar * signs[ia] > 0) and (vrvx_scalar * signs[ib] > 0)
            if do_break:
                break
        if do_break:
            break
    correction = vth_diffs[:, :, ia] * vth_scalar + vrvx_diffs[:, :, ib] * vrvx_scalar
    scale = 1.0
    if (not assume_pos) and (not allow_neg):
        nz = np.nonzero(weighted)
        if np.size(nz) > 0:
            scale = min(1 / np.max(-correction[nz] / weighted[nz]), 1)
    result = nb * (weighted + scale * correction) / volume
    return result, float(scale)


def _require_moments(f_slice, cells, vx, vth, drift, temperature_eV, mass, rtol):
    """Raise unless a normalized slice has its Maxwellian's drift and temperature."""
    _, mean_vx, mean_energy = _slice_moments(f_slice, _cell_fields(cells), vx, vth)
    temperature = (mean_energy - mean_vx**2) * mass / (3 * CHARGE)
    thermal = np.sqrt(3 * CHARGE * temperature_eV / mass)
    wrong_drift = abs(mean_vx - drift) > rtol * max(abs(drift), thermal)
    wrong_temperature = abs(temperature - temperature_eV) > rtol * temperature_eV
    negative = np.min(f_slice) < -rtol * np.max(f_slice)
    if wrong_drift or wrong_temperature or negative:
        raise ValueError(
            f"velocity mesh cannot represent T={temperature_eV:g} eV with drift {drift:g} m/s: "
            f"got T={temperature:.4g} eV, drift {mean_vx:.4g} m/s, min/max f={np.min(f_slice) / np.max(f_slice):.3g}; "
            "use a larger velocity mesh"
        )


def build_compensated_shifted_maxwellian(
    *, vr, vx, temperatures_eV, shifts_ms, mu, molecularity, tnorm_eV, moment_rtol=0.01
):
    """Build and moment-compensate shifted Maxwellian slices.

    Parameters
    ----------
    vr : real array_like, shape [nvr]
        Finite nonempty one-dimensional normalized radial-speed mesh [v/vth].
        Passed to the cylindrical velocity quadrature.
    vx : real array_like, shape [nvx]
        Finite nonempty one-dimensional normalized axial-velocity mesh [v/vth].
        Passed to the cylindrical velocity quadrature.
    temperatures_eV : real array_like, shape [nshift]
        Temperature per shift [eV]. Nonpositive entries return exactly zero
        slices; entries must otherwise be finite and positive.
    shifts_ms : real array_like, shape [nshift]
        Physical axial shifts [m/s], with the same shape as
        ``temperatures_eV``.
    mu : real scalar
        Species mass multiplier [dimensionless] used in the thermal speed and
        target energy.
    molecularity : real scalar
        Molecule-count exponent multiplier [dimensionless] used in the
        exponent and target energy.
    tnorm_eV : real scalar
        Normalization temperature [eV] used to construct the thermal speed.
    moment_rtol : float, optional
        Largest accepted relative error of each returned slice
        [dimensionless]. Must be positive; the default is ``0.01``.

    Returns
    -------
    distribution : ndarray of float64, shape [nvr,nvx,nshift]
        Moment-compensated shifted-Maxwellian slices [normalized density per
        cylindrical velocity volume]. Positive-temperature slices are
        renormalized on the generated quadrature; zero and negative
        temperature branches are zero.

    Raises
    ------
    ValueError
        If a returned slice misses its temperature by more than ``moment_rtol``
        relative to the temperature, misses its drift by more than that relative
        to the larger of the drift and the thermal speed, or goes negative below
        ``-moment_rtol`` times its peak. This happens when the mesh is too small
        for the temperature, typically ``vmax`` under about twice the thermal
        speed. The correction then changes the density, and normalizing afterwards
        can give any drift or temperature, including a negative one. Use a larger
        velocity mesh.

    See Also
    --------
    make_cylindrical_velocity_quadrature : Build the mesh weights and cell measures.
    compensate_velocity_slice : Apply the one-slice bounded correction primitive.

    Notes
    -----
    A Maxwellian with drift ``U`` and temperature ``T`` has mean ``vx = U`` and
    mean speed squared ``U**2 + 3 T / m``. These exact moments are the targets
    and the acceptance test. The correction follows LaBombard's shifted-Maxwellian
    construction, which compensates for velocity-mesh discretization error; it
    is not meant to represent a distribution the mesh cannot hold.

    References
    ----------
    B. LaBombard, "KN1D: A 1-D Space, Kinetic Transport Algorithm for Atomic and
    Molecular Hydrogen in an Ionizing Plasma", MIT PSFC report RR-01-3 (2001).

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import build_compensated_shifted_maxwellian
    >>> vr=np.array([.25,.75,1.5]); vx=np.array([-2.5,-1.5,-.5,.5,1.5,2.5]); out=build_compensated_shifted_maxwellian(vr=vr,vx=vx,temperatures_eV=np.array([5.,0.,-1.]),shifts_ms=np.array([0.,100.,-100.]),mu=1,molecularity=1,tnorm_eV=5., moment_rtol=0.1); assert out.shape==(3,6,3) and np.all(out[:,:,1:]==0)
    """
    vr, vx = np.asarray(vr), np.asarray(vx)
    temperatures_eV, shifts_ms = np.asarray(temperatures_eV), np.asarray(shifts_ms)
    out = np.zeros((vr.size, vx.size, shifts_ms.size), dtype=float)
    thermal_speed = np.sqrt(2 * CHARGE * tnorm_eV / (mu * HYDROGEN_MASS))
    cells = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    for k in range(shifts_ms.size):
        if temperatures_eV[k] <= 0:
            continue
        argument = (
            -(vr[:, None] ** 2 + (vx - shifts_ms[k] / thermal_speed) ** 2)
            * molecularity
            * tnorm_eV
            / temperatures_eV[k]
        )
        argument = np.where((argument > -80) & (argument < 0.0), argument, -80)
        out[:, :, k] = np.exp(argument)
        integral = np.sum(cells["radial_measure"] * np.matmul(out[:, :, k], cells["dvx"]))
        out[:, :, k] /= np.nansum(integral)
        target_energy = shifts_ms[k] ** 2 + 3 * CHARGE * temperatures_eV[k] / (
            molecularity * mu * HYDROGEN_MASS
        )
        out[:, :, k], _ = _compensate_slice(
            out[:, :, k], cells, vr, vx, thermal_speed, shifts_ms[k], target_energy, 1.0, True
        )
        out[:, :, k] /= np.sum(cells["radial_measure"] * np.matmul(out[:, :, k], cells["dvx"]))
        _require_moments(
            out[:, :, k],
            cells,
            vx,
            thermal_speed,
            shifts_ms[k],
            temperatures_eV[k],
            molecularity * mu * HYDROGEN_MASS,
            moment_rtol,
        )
    return out
