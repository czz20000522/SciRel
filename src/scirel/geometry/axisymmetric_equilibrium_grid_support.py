"""Compose axisymmetric equilibrium mapping with material classification."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from .axisymmetric_grid_mapping import map_axisymmetric_equilibrium_to_cartesian_grid
from .material_support import classify_material_support

__all__ = ["solve_axisymmetric_equilibrium_grid_mapping"]
_REQUIRED_INPUTS = (
    "equilibrium",
    "x_m",
    "y_m",
    "z_m",
    "xpoint_half_length_m",
    "pml_cells",
    "pec_mask",
)


def _cylindrical_coordinates(x_m, y_m, z_m):
    """Return broadcast views of radius and axial coordinates for a grid."""
    axes = []
    for name, values in (("x_m", x_m), ("y_m", y_m), ("z_m", z_m)):
        axis = np.asarray(values, dtype=float)
        if axis.ndim != 1 or axis.size < 2:
            raise ValueError(f"grid axis {name} must be a 1D array of at least two points")
        axes.append(axis)
    radius_xy = np.hypot(axes[0][:, None], axes[1][None, :])
    shape = (axes[0].size, axes[1].size, axes[2].size)
    radius = np.broadcast_to(radius_xy[..., None], shape)
    axial = np.broadcast_to(axes[2][None, None, :], shape)
    return radius, axial


def _classification_parameters(equilibrium):
    try:
        return equilibrium["separatrix_flux_wb_per_rad"], equilibrium["closed_flux_side"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            "equilibrium requires separatrix_flux_wb_per_rad and closed_flux_side "
            "for the material-support classification"
        ) from exc


def _run_composition(
    inputs,
    *,
    equilibrium_grid_mapping=map_axisymmetric_equilibrium_to_cartesian_grid,
    material_support_classification=classify_material_support,
):
    """Run mapping followed by material-support classification."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    missing = sorted(set(_REQUIRED_INPUTS).difference(inputs))
    if missing:
        raise ValueError(f"missing required composition inputs: {missing}")
    equilibrium = inputs["equilibrium"]
    if not isinstance(equilibrium, Mapping):
        raise ValueError("equilibrium must be a mapping of caller-owned arrays")

    mapped = equilibrium_grid_mapping(equilibrium, inputs["x_m"], inputs["y_m"], inputs["z_m"])
    radius, axial = _cylindrical_coordinates(inputs["x_m"], inputs["y_m"], inputs["z_m"])
    separatrix, side = _classification_parameters(equilibrium)
    classified = material_support_classification(
        mapped["poloidal_flux_wb_per_rad"],
        mapped["covered_mask"],
        radius,
        axial,
        separatrix_flux_wb_per_rad=separatrix,
        closed_flux_side=side,
        xpoint_half_length_m=inputs["xpoint_half_length_m"],
        pml_cells=inputs["pml_cells"],
        pec_mask=inputs["pec_mask"],
    )
    return {
        "magnetic_flux_density_t": mapped["magnetic_flux_density_t"],
        "poloidal_flux_wb_per_rad": mapped["poloidal_flux_wb_per_rad"],
        "material_support_mask": classified["material_support_mask"],
        "covered_mask": mapped["covered_mask"],
        "radially_clamped_point_count": mapped["radially_clamped_point_count"],
        "axially_clamped_point_count": mapped["axially_clamped_point_count"],
        "closed_flux_mask": classified["closed_flux_mask"],
        "axis_segment_mask": classified["axis_segment_mask"],
    }


def solve_axisymmetric_equilibrium_grid_mapping(inputs=None, **kwargs):
    """Axisymmetric equilibrium to solver-grid material support

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing the seven scientific inputs documented below. A missing or
        non-mapping value is rejected.

    equilibrium : Python mapping
        Caller-owned equilibrium mapping carrying the map arrays r_m, z_m, psi_wb_per_rad,
        br_t, bz_t and the classification parameters separatrix_flux_wb_per_rad and
        closed_flux_side. [mixed SI] Shape: ``mapping of arrays and scalars``. Must be a
        mapping. The map arrays must satisfy the mapping relation's contract; the two
        classification parameters must satisfy the material-support relation's contract.

    x_m : real array-like
        Cartesian solver grid x axis. [m] Shape: ``[N_x]``. Finite, one-dimensional, at
        least two points, strictly increasing.

    y_m : real array-like
        Cartesian solver grid y axis. [m] Shape: ``[N_y]``. Finite, one-dimensional, at
        least two points, strictly increasing.

    z_m : real array-like
        Cartesian solver grid axial axis. [m] Shape: ``[N_z]``. Finite, one-dimensional, at
        least two points, strictly increasing.

    xpoint_half_length_m : real
        Poloidal half length passed to the material-support relation. [m] Shape: ``scalar``.
        Finite and strictly positive.

    pml_cells : int
        PML frame thickness passed to the material-support relation. [dimensionless] Shape:
        ``scalar``. A positive integer.

    pec_mask : bool array-like
        Caller-owned PEC mask passed to the material-support relation. [dimensionless]
        Shape: ``[N_x, N_y, N_z]``. Must match the solver grid shape.

    **kwargs : keyword arguments, optional
        Optional composition-node overrides named ``equilibrium_grid_mapping`` and
        ``material_support_classification``.

    Returns
    -------
    magnetic_flux_density_t : float64
        Static magnetic field on the solver grid. [T] Shape: ``[N_x, N_y, N_z, 3]``. Finite
        everywhere; the transverse pair is exactly zero on the grid axis.
    poloidal_flux_wb_per_rad : float64
        Poloidal flux per radian interpolated onto the solver grid. [Wb/rad] Shape: ``[N_x,
        N_y, N_z]``. Finite everywhere, evaluated at the clamped query coordinates.
    material_support_mask : bool
        Grid points carrying cold-plasma material support. [dimensionless] Shape: ``[N_x,
        N_y, N_z]``. Guaranteed non-empty; an empty classification fails the call.
    covered_mask : bool
        Grid points that lay inside the closed box spanned by the map axes. [dimensionless]
        Shape: ``[N_x, N_y, N_z]``. Produced by the mapping relation and passed through
        unchanged.
    radially_clamped_point_count : int
        Grid points whose radius exceeded the outer map radius. [dimensionless] Shape:
        ``scalar``. Produced by the mapping relation and passed through unchanged.
    axially_clamped_point_count : int
        Grid points clamped onto an axial map face. [dimensionless] Shape: ``scalar``.
        Produced by the mapping relation and passed through unchanged.
    closed_flux_mask : bool
        Covered grid points on the selected side of the separatrix flux, before the frame
        and conductor exclusions. [dimensionless] Shape: ``[N_x, N_y, N_z]``. An added
        diagnostic output; it is a subset of covered_mask and is what lets a caller
        attribute an empty support mask to the flux-surface choice.
    axis_segment_mask : bool
        Covered grid points at the grid's innermost radius within the poloidal half length,
        before the frame and conductor exclusions. [dimensionless] Shape: ``[N_x, N_y,
        N_z]``. An added diagnostic output; it is empty whenever the equilibrium map's
        radial axis begins above the grid's minimum radius.

    Raises
    ------
    ValueError
        Raises ValueError when inputs is not a mapping, when any of the seven required inputs is missing, when equilibrium is not a mapping, or when the equilibrium mapping does not carry the two classification parameters.

    See Also
    --------
    map_axisymmetric_equilibrium_to_cartesian_grid : Axisymmetric equilibrium map to Cartesian solver grid.
    classify_material_support : Closed-flux and magnetic-axis material support classification.

    Notes
    -----
    Reconstructs the static field and the poloidal flux on the solver grid, builds the
    cylindrical coordinates of that grid, reads the separatrix flux and the selected
    flux-surface side off the caller's equilibrium mapping, and classifies material support
    from the reconstructed flux and those parameters.

    **Coordinates.** cylindrical for the map, Cartesian for the grid, with the axial
    coordinate shared between them

    **Boundary.** the composition's boundary is the union of its two dependency boundaries:
    query points outside the map box are clamped and reported, and the support mask must be
    non-empty or the call fails

    **Preconditions.**

    * The caller's equilibrium mapping carries both the map arrays and the two flux-surface
      classification parameters, as this operator expects.
    * Both bound relations' preconditions hold for the supplied arrays.
    * The solver box has a genuine PML frame of at least one cell.

    **Limits.**

    * Field solves, wave propagation, and plasma response.
    * Non-axisymmetric equilibria.
    * Solver grids without a PML frame.
    * Any graph-level iteration, feedback, or state; this composition is a single ordered
      pass.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import solve_axisymmetric_equilibrium_grid_mapping
    >>> r_axis = np.linspace(0.05, 1.0, 21)
    >>> z_axis = np.linspace(-0.5, 0.5, 21)
    >>> rr, zz = np.meshgrid(r_axis, z_axis, indexing='ij')
    >>> equilibrium = {
    ...     'r_m': r_axis,
    ...     'z_m': z_axis,
    ...     'psi_wb_per_rad': 0.9 * rr + 0.1 * np.sin(2.0 * np.pi * zz),
    ...     'br_t': 0.3 * rr - 0.1 * zz ** 2,
    ...     'bz_t': 1.0 - 0.4 * rr ** 2,
    ...     'separatrix_flux_wb_per_rad': 0.4,
    ...     'closed_flux_side': 'less_than',
    ... }
    >>> result = solve_axisymmetric_equilibrium_grid_mapping(inputs={
    ...     'equilibrium': equilibrium,
    ...     'x_m': np.linspace(-0.5, 0.5, 9),
    ...     'y_m': np.linspace(-0.5, 0.5, 9),
    ...     'z_m': np.linspace(-0.4, 0.4, 7),
    ...     'xpoint_half_length_m': 0.2,
    ...     'pml_cells': 1,
    ...     'pec_mask': np.zeros((9, 9, 7), dtype=bool),
    ... })
    >>> assert result['magnetic_flux_density_t'].shape == (9, 9, 7, 3)
    >>> assert result['poloidal_flux_wb_per_rad'].shape == (9, 9, 7)
    >>> assert result['covered_mask'].sum() == 560
    >>> assert result['material_support_mask'].sum() > 0
    >>> assert result['closed_flux_mask'].sum() >= result['material_support_mask'].sum()
    >>> assert result['axis_segment_mask'].sum() == 0
    >>> assert result['radially_clamped_point_count'] == 0
    >>> assert result['axially_clamped_point_count'] == 0
    >>> assert not result['material_support_mask'][0, :, :].any()
    >>> assert not result['material_support_mask'][:, :, -1].any()
    """
    mapping = kwargs.pop("equilibrium_grid_mapping", map_axisymmetric_equilibrium_to_cartesian_grid)
    classification = kwargs.pop("material_support_classification", classify_material_support)
    if kwargs:
        raise ValueError(f"unexpected composition keyword arguments: {sorted(kwargs)}")
    return _run_composition(
        inputs, equilibrium_grid_mapping=mapping, material_support_classification=classification
    )
