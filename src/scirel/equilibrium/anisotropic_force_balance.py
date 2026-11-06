"""Axisymmetric gyrotropic pressure-tensor force and current closure."""

from __future__ import annotations

import math
import struct
import numpy as np

from scirel._anisotropic_numerics import pressure_divergence, residual_metrics

MU0 = 4.0e-7 * np.pi
__all__ = ["compute_anisotropic_force_balance"]


def _source_hypot(left, right):
    """Evaluate ``hypot`` with the retained source's finite-range behavior."""
    left, right = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    result = []
    for first, second in zip(left.flat, right.flat):
        x, y = abs(float(first)), abs(float(second))
        if math.isinf(x) or math.isinf(y):
            result.append(math.inf)
            continue
        if math.isnan(x) or math.isnan(y):
            result.append(math.nan)
            continue
        if x < y:
            x, y = y, x
        if x == 0.0:
            result.append(0.0)
            continue
        _, exponent = math.frexp(x)
        scaled_x = math.ldexp(x, -exponent)
        scaled_y = math.ldexp(y, -exponent)
        bits = struct.unpack(">Q", struct.pack(">d", scaled_x))[0] & 18446744073575333888
        high = struct.unpack(">d", struct.pack(">Q", bits))[0]
        low = scaled_x - high
        scaled_norm = math.sqrt(high * high - (scaled_y * -scaled_y - low * (scaled_x + high)))
        try:
            result.append(math.ldexp(scaled_norm, exponent))
        except OverflowError:
            result.append(math.inf)
    return np.asarray(result, dtype=float).reshape(left.shape)


def compute_anisotropic_force_balance(
    r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular, active_mask=None
):
    """Compute ``div(P)``, toroidal current, and closure diagnostics.

    Parameters
    ----------
    r_grid : finite real array-like
        Cylindrical radius mesh [m] Shape [N_Z,N_R]. Rectilinear, nonnegative R, strictly increasing radial axis, at least three columns; same shape as other arrays.
    z_grid : finite real array-like
        Axial coordinate mesh [m] Shape [N_Z,N_R]. Rectilinear, strictly increasing axial axis, at least three rows; same shape as other arrays.
    b_r : finite real array-like
        Radial component of the poloidal magnetic field [T] Shape [N_Z,N_R]. Same grid shape; no nonzero-field precondition is enforced by this Operator.
    b_z : finite real array-like
        Axial component of the poloidal magnetic field [T] Shape [N_Z,N_R]. Same grid shape; combined with b_r for field magnitude and direction.
    p_parallel : finite real array-like
        Pressure parallel to the local poloidal magnetic field [Pa] Shape [N_Z,N_R]. Same grid shape and nonnegative; scalar broadcasting is not performed here.
    p_perpendicular : finite real array-like
        Pressure perpendicular to the local poloidal magnetic field [Pa] Shape [N_Z,N_R]. Same grid shape and nonnegative; scalar broadcasting is not performed here.
    active_mask : boolean array-like or None
        Cells included in the RMS parallel-force compatibility metric [boolean] Shape [N_Z,N_R] or null. If omitted, all cells are active; same shape when supplied. It does not suppress the returned force or current arrays.

    Returns
    -------
    force_R : float64
        Radial component of cylindrical div(P) [Pa/m] Shape [N_Z,N_R]. Axis column is set to zero when the first radius is exactly zero.
    force_Z : float64
        Axial component of cylindrical div(P) [Pa/m] Shape [N_Z,N_R]. Includes the off-axis P_RZ/R term.
    parallel_force : float64
        Pressure force projected along the poloidal field [Pa/m] Shape [N_Z,N_R]. Observational compatibility residual, not subtracted from the current relation.
    J_phi : float64
        Toroidal current-density projection of pressure force [A/m^2] Shape [N_Z,N_R]. Zero at the axis and where |B|^2 is at or below the numeric tiny threshold; active_mask does not zero it.
    B : float64
        Magnitude of the supplied poloidal field [T] Shape [N_Z,N_R]. Computed from B_R and B_Z using the maintained source-compatible hypot path.
    parallel_force_error : float
        Resolved RMS parallel-force after subtracting its dimensioned floating-point evaluation envelope, normalized by the larger of total-force RMS and envelope Shape scalar. Denominator also floored at numeric tiny; raw absolute, raw relative and envelope diagnostics remain available; returns 0.0 when no cell is active.
    firehose_margin : float64
        Local 1 - mu0*(p_parallel-p_perpendicular)/max(|B|^2,tiny) Shape [N_Z,N_R]. Diagnostic only; this Operator does not reject nonpositive margin.
    force_roundoff_R : real array
        Local floating-point evaluation envelope, not a truncation error [N/m^3] Shape [N_Z,N_R]. Local floating-point evaluation envelope, not a truncation error.
    force_roundoff_Z : real array
        Local floating-point evaluation envelope, not a truncation error [N/m^3] Shape [N_Z,N_R]. Local floating-point evaluation envelope, not a truncation error.
    parallel_force_roundoff : real array
        Local floating-point evaluation envelope, not a truncation error [N/m^3] Shape [N_Z,N_R]. Local floating-point evaluation envelope, not a truncation error.
    parallel_force_absolute : float
        Active-mask RMS raw force or its rounding envelope [N/m^3] Shape scalar. Active-mask RMS raw force or its rounding envelope.
    parallel_force_roundoff_rms : float
        Active-mask RMS raw force or its rounding envelope [N/m^3] Shape scalar. Active-mask RMS raw force or its rounding envelope.
    parallel_force_error_raw : float
        Unmodified RMS parallel force divided by RMS total force Shape scalar. Unmodified RMS parallel force divided by RMS total force.
    parallel_force_roundoff_consistent : bool
        Whether raw RMS parallel force is no larger than its rounding envelope [boolean] Shape scalar. Whether raw RMS parallel force is no larger than its rounding envelope.

    Raises
    ------
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    compute_anisotropic_toroidal_current : Split the toroidal current into isotropic and curvature terms.

    Notes
    -----
    P=p_perpendicular I+(p_parallel-p_perpendicular)bb. Evaluate the cylindrical tensor divergence using difference-form quadratic stencils. At R=0, smooth odd P_RZ contributes a second d_R P_RZ term to force_Z; regular force_R=J_phi=0. Off axis, J_phi=(B_Z force_R-B_R force_Z)/B².

    axisymmetric gyrotropic pressure tensor and perpendicular force-balance current projection

    The supplied B_R and B_Z are components of the same poloidal field as the pressure arrays.

    Both pressure components are nonnegative Pa values at grid nodes.

    The optional active_mask selects cells for the parallel-force error metric only; this Operator does not zero J_phi outside it.

    For an axis-containing mesh the physical field and tensor must have smooth axisymmetric parity: BR and PRZ odd, BZ and diagonal pressures even.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import compute_anisotropic_force_balance
    >>> r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.3, 0.3, 5))
    >>> result = compute_anisotropic_force_balance(r_grid, z_grid, np.zeros_like(r_grid), np.ones_like(r_grid), np.full_like(r_grid, 2.0), np.full_like(r_grid, 2.0))
    >>> np.testing.assert_allclose(result['force_R'], 0.0, atol=1e-12)
    >>> np.testing.assert_allclose(result['J_phi'], 0.0, atol=1e-12)
    >>> np.testing.assert_allclose(result['firehose_margin'], 1.0)
    """
    arrays = [
        np.asarray(value, dtype=float)
        for value in (r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)
    ]
    shape = arrays[0].shape
    if any(
        value.ndim != 2 or value.shape != shape or not np.all(np.isfinite(value))
        for value in arrays
    ):
        raise ValueError("R, Z, field, and pressure inputs must be finite same-shape [Z,R] arrays")
    r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular = arrays
    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (
        r_axis.size < 3
        or z_axis.size < 3
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
    ):
        raise ValueError("a rectilinear R-Z grid with at least 3 points per axis is required")
    if (
        r_axis[0] < 0.0
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or np.any(p_parallel < 0.0)
        or np.any(p_perpendicular < 0.0)
    ):
        raise ValueError("grid axes and pressures are invalid")
    mask = (
        np.ones(shape, dtype=bool) if active_mask is None else np.asarray(active_mask, dtype=bool)
    )
    if mask.shape != shape:
        raise ValueError("active_mask must match the R-Z grid")

    result = pressure_divergence(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)
    force_norm = np.hypot(result["force_R"], result["force_Z"])
    diagnostics = residual_metrics(
        result["parallel_force"], force_norm, result["parallel_force_roundoff"], mask
    )
    result.update(
        {
            "parallel_force_error": diagnostics["error"],
            "parallel_force_absolute": diagnostics["absolute"],
            "parallel_force_error_raw": diagnostics["raw_relative"],
            "parallel_force_roundoff_rms": diagnostics["roundoff"],
            "parallel_force_roundoff_consistent": diagnostics["roundoff_consistent"],
            "firehose_margin": 1.0
            - MU0
            * (p_parallel - p_perpendicular)
            / np.maximum(result["B"] ** 2, np.finfo(float).tiny),
        }
    )
    return result
