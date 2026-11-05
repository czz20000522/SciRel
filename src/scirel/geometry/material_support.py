"""Classify closed-flux material support on a Cartesian solver grid."""

from __future__ import annotations

import math

import numpy as np

__all__ = ["ALLOWED_CLOSED_FLUX_SIDES", "classify_material_support"]
ALLOWED_CLOSED_FLUX_SIDES = ("less_than", "greater_than")


def _coordinate_array(value, name, shape):
    result = np.asarray(value, dtype=float)
    if result.shape != shape:
        raise ValueError(f"{name} must match the poloidal flux shape {shape}")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def _positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive integer cell count")
    try:
        integer = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a positive integer cell count") from None
    if integer != value:
        raise ValueError(f"{name} must be a positive integer cell count")
    if integer < 1:
        raise ValueError(
            "pml_cells must be a positive integer; a zero frame thickness is not a "
            "defined exclusion and the retained slice form silently excluded the "
            "whole solver box"
        )
    return integer


def classify_material_support(
    poloidal_flux_wb_per_rad,
    covered_mask,
    radii_m,
    axial_coordinate_m,
    *,
    separatrix_flux_wb_per_rad,
    closed_flux_side,
    xpoint_half_length_m,
    pml_cells,
    pec_mask,
):
    """Closed-flux and magnetic-axis material support classification

    Parameters
    ----------
    poloidal_flux_wb_per_rad : real array-like
        Poloidal flux per radian sampled on the solver grid. [Wb/rad] Shape: ``[N_x, N_y,
        N_z]``. Finite and three-dimensional. Non-finite flux is rejected, because a
        non-finite sample cannot be compared against the separatrix flux.

    covered_mask : bool array-like
        Points for which the flux sampling is defined. [dimensionless] Shape: ``[N_x, N_y,
        N_z]``. Must match the flux shape. Support is never granted outside this mask.

    radii_m : real array-like
        Cylindrical radius of every grid point. [m] Shape: ``[N_x, N_y, N_z]``. Finite,
        non-negative, and matching the flux shape. The grid's minimum value locates the
        innermost radius.

    axial_coordinate_m : real array-like
        Axial coordinate of every grid point. [m] Shape: ``[N_x, N_y, N_z]``. Finite and
        matching the flux shape. Its absolute value is compared against the poloidal half
        length.

    separatrix_flux_wb_per_rad : real
        Poloidal flux per radian of the separatrix. [Wb/rad] Shape: ``scalar``. Finite. Not
        required to lie inside the sampled flux range; a separatrix outside the range simply
        makes the selected side empty, which then fails the non-empty support requirement.

    closed_flux_side : string
        Which side of the separatrix flux is confined. [dimensionless] Shape: ``scalar``.
        Exactly 'less_than' or 'greater_than'. Any other value is rejected rather than
        defaulted.

    xpoint_half_length_m : real
        Poloidal half length around the midplane within which the innermost-radius segment
        counts as support. [m] Shape: ``scalar``. Finite and strictly positive.

    pml_cells : int
        Thickness of the perfectly matched layer frame, in grid cells, excluded on all six
        faces of the solver box. [dimensionless] Shape: ``scalar``. A positive integer. A
        zero thickness is rejected: the exclusion is expressed as slice assignments, and a
        zero thickness would make every slice cover the whole box.

    pec_mask : bool array-like
        Caller-owned perfect-electric-conductor mask. [dimensionless] Shape: ``[N_x, N_y,
        N_z]``. Must match the flux shape. PEC points are removed from the support after the
        flux-surface classification.

    Returns
    -------
    material_support_mask : bool
        Grid points carrying cold-plasma material support. [dimensionless] Shape: ``[N_x,
        N_y, N_z]``. Guaranteed non-empty: an empty mask raises instead of being returned,
        because a solve with no cold-plasma material is not a result of this relation.
    closed_flux_mask : bool
        Covered grid points on the selected side of the separatrix flux, before the PML
        frame and the PEC mask are applied. [dimensionless] Shape: ``[N_x, N_y, N_z]``. A
        subset of covered_mask. Returned so that a caller can attribute an empty or
        surprising support mask to the flux-surface choice rather than to the frame or the
        conductor mask.
    axis_segment_mask : bool
        Covered grid points at the grid's innermost radius within the poloidal half length,
        before the PML frame and the PEC mask are applied. [dimensionless] Shape: ``[N_x,
        N_y, N_z]``. A subset of covered_mask. Because this term is intersected with the
        coverage mask, it is empty whenever the sampled field's radial axis begins
        above the grid's minimum radius.

    Raises
    ------
    ValueError
        Raises ValueError when the flux is not a finite 3D array, when covered_mask, radii_m, axial_coordinate_m, or pec_mask does not match the flux shape, when radii_m is negative or non-finite, when the coordinate arrays are non-finite, when the separatrix flux is non-finite, when closed_flux_side is not one of the two allowed values, when the poloidal half length is non-finite or not strictly positive, or when pml_cells is not a positive integer. Raises ValueError when the classified support mask is empty.

    See Also
    --------
    scirel.geometry : Geometry namespace.
    face_to_cell : Face-to-cell reduction for geometry consumers.

    Notes
    -----
    Forms the closed-flux mask as the covered points on the selected side of the separatrix
    flux, forms the innermost-radius segment as the covered points at the grid's minimum
    radius within the poloidal half length, excludes the PML frame on all six faces of the
    solver box, excludes the caller's PEC mask, and requires the result to be non-empty.

    **Coordinates.** cylindrical radius and axial coordinate of the sampling grid, together
    with the discrete index position of each point in the solver box

    **Boundary.** the PML frame is the set of points within pml_cells of any of the six
    faces of the solver box; the frame thickness must be a positive integer, so a zero
    thickness is rejected rather than treated as an empty frame

    **Preconditions.**

    * The poloidal flux has already been sampled on the solver grid, and the coverage mask
      states where that sampling is defined.
    * The caller has decided which side of the separatrix flux is confined and the poloidal
      half length of interest.
    * The solver box has a genuine PML frame of at least one cell.

    **Limits.**

    * Reconstruction of the flux field; the flux must already be sampled.
    * Inferring which side of the separatrix is confined.
    * Identifying the magnetic axis from the flux field; the innermost-radius segment is a
      geometric proxy only.
    * Any plasma, collisionality, or wave model.
    * Solver grids with no PML frame, which are rejected rather than treated as having an
      empty frame.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import classify_material_support
    >>> x_m = np.linspace(-0.5, 0.5, 9)
    >>> y_m = np.linspace(-0.5, 0.5, 9)
    >>> z_m = np.linspace(-0.4, 0.4, 7)
    >>> xx, yy, zz = np.meshgrid(x_m, y_m, z_m, indexing='ij')
    >>> radii = np.hypot(xx, yy)
    >>> flux = 0.9 * radii + 0.1 * np.sin(2.0 * np.pi * zz)
    >>> covered = (radii >= 0.05) & (radii <= 1.0) & (zz >= -0.5) & (zz <= 0.5)
    >>> pec = np.zeros((9, 9, 7), dtype=bool)
    >>> pec[5, 5, 3] = True
    >>> result = classify_material_support(
    ...     flux,
    ...     covered,
    ...     radii,
    ...     zz,
    ...     separatrix_flux_wb_per_rad=0.4,
    ...     closed_flux_side='less_than',
    ...     xpoint_half_length_m=0.2,
    ...     pml_cells=1,
    ...     pec_mask=pec,
    ... )
    >>> support = result['material_support_mask']
    >>> assert support.dtype == bool and support.shape == (9, 9, 7)
    >>> assert support.sum() > 0
    >>> assert not support[0, :, :].any() and not support[-1, :, :].any()
    >>> assert not support[:, 0, :].any() and not support[:, -1, :].any()
    >>> assert not support[:, :, 0].any() and not support[:, :, -1].any()
    >>> assert not support[5, 5, 3]
    >>> assert not result['axis_segment_mask'].any()
    >>> assert result['closed_flux_mask'].sum() >= support.sum()
    """
    flux = np.asarray(poloidal_flux_wb_per_rad, dtype=float)
    if flux.ndim != 3:
        raise ValueError("poloidal_flux_wb_per_rad must be a 3D array")
    shape = flux.shape
    if not np.isfinite(flux).all():
        raise ValueError("poloidal_flux_wb_per_rad must be finite")
    covered = np.asarray(covered_mask, dtype=bool)
    if covered.shape != shape:
        raise ValueError(f"covered_mask must match the poloidal flux shape {shape}")
    radius = _coordinate_array(radii_m, "radii_m", shape)
    if np.any(radius < 0.0):
        raise ValueError("radii_m must be non-negative")
    axial = _coordinate_array(axial_coordinate_m, "axial_coordinate_m", shape)
    separatrix = float(separatrix_flux_wb_per_rad)
    if not math.isfinite(separatrix):
        raise ValueError("separatrix_flux_wb_per_rad must be finite")
    side = str(closed_flux_side)
    if side not in ALLOWED_CLOSED_FLUX_SIDES:
        raise ValueError("closed_flux_side must be less_than or greater_than")
    half_length = float(xpoint_half_length_m)
    if not math.isfinite(half_length) or half_length <= 0.0:
        raise ValueError("xpoint_half_length_m must be finite and strictly positive")
    thickness = _positive_integer(pml_cells, "pml_cells")
    pec = np.asarray(pec_mask, dtype=bool)
    if pec.shape != shape:
        raise ValueError(f"pec_mask must match the solver grid shape {shape}")

    if side == "less_than":
        closed = covered & (flux < separatrix)
    else:
        closed = covered & (flux > separatrix)
    axis = covered & np.isclose(radius, np.min(radius), rtol=0.0, atol=1.0e-15)
    axis &= np.abs(axial) < half_length

    interior = np.ones(shape, dtype=bool)
    interior[:thickness] = False
    interior[-thickness:] = False
    interior[:, :thickness] = False
    interior[:, -thickness:] = False
    interior[:, :, :thickness] = False
    interior[:, :, -thickness:] = False
    support = (closed | axis) & interior & ~pec
    if not np.any(support):
        raise ValueError(
            "material support classification is empty: the selected closed-flux side, "
            "the innermost-radius segment, the PML frame, and the PEC mask leave no "
            "grid point with cold-plasma support"
        )
    return {
        "material_support_mask": support,
        "closed_flux_mask": closed,
        "axis_segment_mask": axis,
    }
