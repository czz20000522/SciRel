"""Ordered composition for a collection of rectangular vacuum coils."""

from __future__ import annotations

import numpy as np

from scirel._result import Result

CURRENT_KEYS = ("current_a", "ampere_turns_a")


def _attach_coil_current(points, current, weights):
    """Attach dimensionless filament weights while keeping drive current scalar."""
    return np.column_stack((points, weights)), current


def _concatenate_filament_blocks(blocks):
    """Join per-coil source blocks in caller order."""
    return np.concatenate(blocks, axis=0)


def _target_points(r_grid, z_grid):
    """Pack matching grid arrays into the Green target table."""
    return np.column_stack((r_grid.ravel(), z_grid.ravel()))


def _stack_response_columns(responses):
    """Turn one target-ordered response mapping per coil into source columns."""
    return {
        name: np.column_stack([item[name] for item in responses]) for name in ("gpsi", "gBR", "gBZ")
    }


def _run_composition(inputs, *, asset_loader):
    """Expand coil records, evaluate local Green blocks, then contract currents."""
    if not isinstance(inputs, dict):
        raise ValueError("r_grid, z_grid, and rectangular_coils are required")
    required_inputs = ("r_grid", "z_grid", "rectangular_coils")
    missing = [name for name in required_inputs if name not in inputs]
    if missing:
        raise ValueError("r_grid, z_grid, and rectangular_coils are required")
    r_grid, z_grid = (
        np.asarray(inputs["r_grid"], dtype=float),
        np.asarray(inputs["z_grid"], dtype=float),
    )
    if (
        r_grid.ndim != 2
        or z_grid.shape != r_grid.shape
        or not np.all(np.isfinite(r_grid))
        or not np.all(np.isfinite(z_grid))
    ):
        raise ValueError("r_grid and z_grid must be equal-shape finite 2-D arrays")
    if not r_grid.size:
        raise ValueError("r_grid and z_grid must be nonempty 2-D arrays")
    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (
        np.any(r_axis < 0.0)
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
    ):
        raise ValueError("r_grid and z_grid must define a strictly increasing rectilinear R-Z grid")
    coils = inputs["rectangular_coils"]
    if not isinstance(coils, (list, tuple)) or not coils:
        raise ValueError("rectangular_coils must be a nonempty list of configuration mappings")

    target_r = set(r_axis.tolist())
    target_z = set(z_axis.tolist())
    geometry = asset_loader("scirel.field.rectangular_coil_filaments")
    source_blocks, currents = [], []
    required_coil = {"r0_m", "z0_m", "nr", "nz", "dr_m", "dz_m"}
    for index, coil in enumerate(coils):
        missing = (
            sorted(required_coil.difference(coil))
            if isinstance(coil, dict)
            else sorted(required_coil)
        )
        if not isinstance(coil, dict) or missing:
            raise ValueError(f"rectangular_coils[{index}] misses {', '.join(missing)}")
        given = [key for key in CURRENT_KEYS if key in coil]
        if len(given) != 1:
            raise ValueError(
                f"rectangular_coils[{index}] needs exactly one of current_a (current in each filament) "
                f"or ampere_turns_a (total current of the coil, split over its filaments); got {given or 'neither'}"
            )
        points = geometry(
            coil["r0_m"],
            coil["z0_m"],
            coil["nr"],
            coil["nz"],
            coil["dr_m"],
            coil["dz_m"],
            coil.get("angle_deg", 0.0),
        )
        value = float(coil[given[0]])
        if not np.isfinite(value):
            raise ValueError(f"rectangular_coils[{index}].{given[0]} must be finite")
        weights = np.asarray(coil.get("weights", np.ones(len(points))), dtype=float)
        if weights.shape != (len(points),) or not np.all(np.isfinite(weights)):
            raise ValueError(
                f"rectangular_coils[{index}].weights must be finite with one value per filament"
            )
        if given[0] == "current_a":
            current = value
        else:
            total_weight = float(np.sum(weights))
            if total_weight == 0.0 or not np.isfinite(total_weight):
                raise ValueError(
                    f"rectangular_coils[{index}].ampere_turns_a needs filament weights with a nonzero finite sum"
                )
            current = value / total_weight
        block, drive = _attach_coil_current(points, current, weights)
        if current != 0.0:
            active = (block[:, 0] > 0.0) & (block[:, 2] != 0.0)
            coincident = any(
                float(radius) in target_r and float(height) in target_z
                for radius, height in block[active, :2]
            )
            if coincident:
                raise ValueError(
                    f"rectangular_coils[{index}] has an active filament coincident with a target grid node"
                )
        source_blocks.append(block)
        currents.append(drive)

    target_points = _target_points(r_grid, z_grid)
    green = asset_loader("scirel.field.circular_filament_green")
    responses = [green(block, target_points) for block in source_blocks]
    stacked = _stack_response_columns(responses)
    superpose = asset_loader("scirel.field.current_green_superposition")
    combined = superpose(np.asarray(currents), stacked["gpsi"], stacked["gBR"], stacked["gBZ"])
    return {
        "psi_vac": combined["psi"].reshape(r_grid.shape),
        "b_r_vac": combined["BR"].reshape(r_grid.shape),
        "b_z_vac": combined["BZ"].reshape(r_grid.shape),
        "filaments": _concatenate_filament_blocks(source_blocks),
    }


def solve_multi_coil_vacuum_field(inputs=None, **kwargs):
    """Compute vacuum fields from coil records as a named result.

    Each coil mapping gives ``r0_m, z0_m, nr, nz, dr_m, dz_m`` (an ``nr`` x ``nz``
    array of thin circular filaments centred on ``(r0_m, z0_m)`` with centre
    spacings ``dr_m, dz_m``), optional ``angle_deg`` and ``weights`` (one per
    filament, default 1), and exactly one current:

    * ``current_a``: the current in each filament, in amperes. Filament ``j``
      carries ``current_a * weights[j]``, so the coil's total ampere-turns are
      ``current_a * sum(weights)`` (``nr * nz * current_a`` for unit weights).
    * ``ampere_turns_a``: the total current of the whole coil block, in
      amperes. It is split over the filaments in proportion to ``weights``
      (equally for unit weights).

    Giving both, or neither, raises ``ValueError``; passing a coil's total
    ampere-turns as ``current_a`` would multiply its field by ``nr * nz``.

    The returned ``psi_vac`` is Wb/rad (``R * A_phi``) and ``b_r_vac``/``b_z_vac``
    are tesla; all arrays have the shape of the supplied ``r_grid`` and ``z_grid``.
    An active nonzero-current filament exactly coincident with a target grid
    node raises ``ValueError`` instead of dropping that singular source. Raises
    ``ValueError`` for missing or malformed grid and coil records.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing ``r_grid``, ``z_grid`` and ``rectangular_coils``.
        The default None is allowed only when those entries are supplied as
        keywords.
    **kwargs
        Named entries merged into ``inputs`` by the composition boundary; a
        keyword takes precedence over the same key in the mapping.
    r_grid : real array-like, shape [N_Z,N_R]
        Target cylindrical radius grid [m]. Finite nonempty rectilinear 2-D
        grid; radial axis is strictly increasing and nonnegative. N_R and N_Z
        are each at least one.
    z_grid : real array-like, shape [N_Z,N_R]
        Target axial coordinate grid [m]. Finite, nonempty, same shape as
        r_grid, and axial axis strictly increasing; singleton axes are
        permitted.
    rectangular_coils : Python sequence of mappings, shape list[mapping]
        Coil mappings with r0_m,z0_m,nr,nz,dr_m,dz_m, exactly one of current_a
        or ampere_turns_a, and optional angle_deg/weights. current_a is the
        current in EACH filament (filament j carries current_a*weights[j];
        weights default to 1, so a coil's total ampere-turns are
        nr*nz*current_a). ampere_turns_a is the total current of the whole coil
        block, split over its filaments in proportion to weights. Passing a
        coil's total ampere-turns as current_a makes its field nr*nz times too
        large [mixed SI]. Nonempty; each coil gives exactly one finite current_a
        or ampere_turns_a (both or neither raise ValueError) and optionally one
        finite weight per generated filament; ampere_turns_a needs weights with
        a nonzero sum. A nonzero-current, nonzero-weight filament must not be
        exactly coincident with a target grid node.

    Returns
    -------
    psi_vac : float64, shape [N_Z,N_R]
        Field ``psi_vac`` of the returned ``scirel._result.Result`` mapping:
        vacuum poloidal flux on the target grid [Wb/rad]. Same grid shape and
        C-order point mapping as inputs.
    b_r_vac : float64, shape [N_Z,N_R]
        Field ``b_r_vac`` of the returned result mapping: vacuum radial
        magnetic field on the target grid [T]. Same grid shape and C-order
        point mapping as inputs.
    b_z_vac : float64, shape [N_Z,N_R]
        Field ``b_z_vac`` of the returned result mapping: vacuum axial magnetic
        field on the target grid [T]. Same grid shape and C-order point mapping
        as inputs.
    filaments : float64, shape [N_filament,3]
        Field ``filaments`` of the returned result mapping: concatenated
        [R_m,Z_m,weight] rows in caller coil order [m,m,dimensionless].
        Preserves each coil's filament order and the outer caller coil order.

    Raises
    ------
    FloatingPointError
        Dependency ValueError/FloatingPointError propagates before any field is
        returned, including a nonrepresentable current-weighted Green
        contraction; no fallback or retry is performed.
    ValueError
        ValueError is raised for missing, empty or malformed grids,
        empty/nonmapping coils, invalid geometry, weights, currents, or an
        active filament exactly coincident with a target grid node. Dependency
        ValueError/FloatingPointError propagates before any field is returned,
        including a nonrepresentable current-weighted Green contraction; no
        fallback or retry is performed.

    See Also
    --------
    scirel.electromagnetism.compute_greens : Circular-filament Green functions.
    scirel.configurations.WHAM : Fixed WHAM coil geometry preset.

    Notes
    -----
    The four fields are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import solve_multi_coil_vacuum_field
    >>> r_grid, z_grid = np.meshgrid([0.0, 0.2], [-0.1, 0.1])
    >>> result = solve_multi_coil_vacuum_field(
    ...     r_grid=r_grid,
    ...     z_grid=z_grid,
    ...     rectangular_coils=[{
    ...         'r0_m': 0.45, 'z0_m': 0.0, 'nr': 2, 'nz': 2,
    ...         'dr_m': 0.04, 'dz_m': 0.05, 'current_a': 1000.0,
    ...     }],
    ... )
    >>> assert isinstance(result, Result)
    >>> assert list(result) == [
    ...     'psi_vac', 'b_r_vac', 'b_z_vac', 'filaments'
    ... ]
    >>> assert result.psi_vac is result['psi_vac']
    >>> assert result['psi_vac'].shape == r_grid.shape
    >>> assert result['filaments'].shape == (4, 3)
    >>> assert np.isfinite(result['b_z_vac']).all()
    """
    from scirel._composition import compose
    from scirel.field.circular_filament_green import circular_filament_green_response
    from scirel.field.current_green_superposition import superpose_current_green_field
    from scirel.field.rectangular_coil_filaments import discretize_rectangular_coil

    return Result(
        compose(
            _run_composition,
            inputs,
            kwargs,
            {
                "asset_loader": {
                    "scirel.field.circular_filament_green": circular_filament_green_response,
                    "scirel.field.current_green_superposition": superpose_current_green_field,
                    "scirel.field.rectangular_coil_filaments": discretize_rectangular_coil,
                }
            },
        )
    )


__all__ = ["solve_multi_coil_vacuum_field"]
