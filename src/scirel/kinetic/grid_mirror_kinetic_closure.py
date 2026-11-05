"""Compose the mirror kinetic closure on a shared grid while preserving explicit dependency and shape contracts."""

from __future__ import annotations
import numpy as np


def _field(value, target, name):
    if callable(value):
        value = value(np.asarray(target, dtype=float))
    try:
        values = np.broadcast_to(np.asarray(value, dtype=float), target.shape)
    except ValueError as exc:
        raise ValueError(f"{name} cannot be broadcast over target") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def _nearest_index(axis, coordinate):
    """Map a caller coordinate to the first nearest declared grid index."""
    return min(range(axis.size), key=lambda index: abs(float(axis[index]) - float(coordinate)))


def _confine_rows(value, left_index, right_index):
    """Zero rows outside the caller-declared plug interval."""
    result = np.array(value, copy=True)
    result[:left_index] = 0.0
    result[right_index:][1:] = 0.0
    return result


def run_composition(inputs, *, asset_loader, composition_loader):
    """Map reference/plug planes into a local nested kinetic closure.

    Endpoint current_balance_solved flags distinguish prescribed evaluation
    from a solved end-current balance. Local converged describes the separately
    verified quasineutral state, not a prescribed endpoint equilibrium.
    """
    required = {
        "r_grid",
        "z_grid",
        "b_t",
        "psi",
        "mass_kg",
        "charge_c",
        "density_ref_m3",
        "temperature_parallel_j",
        "temperature_perpendicular_ref_j",
        "electron_temperature_j",
        "reference_z",
        "plug_left_z",
        "plug_right_z",
    }
    missing = (
        sorted((key for key in required if key not in inputs)) if isinstance(inputs, dict) else []
    )
    if not isinstance(inputs, dict) or missing:
        raise ValueError(f"inputs must be a mapping with {', '.join(missing or [])}")
    r_grid, z_grid, b_t, psi = (
        np.asarray(inputs[name], dtype=float) for name in ("r_grid", "z_grid", "b_t", "psi")
    )
    if (
        r_grid.shape != z_grid.shape
        or b_t.shape != r_grid.shape
        or psi.shape != r_grid.shape
        or (r_grid.ndim != 2)
    ):
        raise ValueError("R, Z, B, psi must be equal-shape 2-D arrays")
    if not all((np.all(np.isfinite(value)) for value in (r_grid, z_grid, b_t, psi))):
        raise ValueError("R, Z, B, psi must be finite")
    r_axis, z_axis = (r_grid[0, :], z_grid[:, 0])
    if (
        not np.allclose(r_grid, r_axis[np.newaxis, :])
        or not np.allclose(z_grid, z_axis[:, np.newaxis])
        or np.any(r_axis < 0.0)
        or (r_axis.size < 2)
        or (z_axis.size < 2)
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or np.any(b_t <= 0.0)
    ):
        raise ValueError(
            "r_grid and z_grid must be rectilinear with strictly increasing axes; b_t must be positive"
        )
    confine_to_plug_planes = inputs.get("confine_to_plug_planes", True)
    if not isinstance(confine_to_plug_planes, (bool, np.bool_)):
        raise ValueError("confine_to_plug_planes must be a boolean scalar")
    confine_to_plug_planes = bool(confine_to_plug_planes)
    plane_coordinates = []
    for name in ("plug_left_z", "reference_z", "plug_right_z"):
        coordinate = np.asarray(inputs[name])
        if (
            coordinate.ndim != 0
            or not np.isrealobj(coordinate)
            or (not bool(np.isfinite(coordinate)))
        ):
            raise ValueError(f"{name} must be a finite scalar")
        plane_coordinates.append(float(coordinate))
    left_index, reference_index, right_index = (
        _nearest_index(z_axis, coordinate) for coordinate in plane_coordinates
    )
    if not left_index < reference_index < right_index:
        raise ValueError("plug planes must bracket the reference plane")
    psi_reference, b_reference = (psi[reference_index], b_t[reference_index])
    profile = asset_loader("scirel.geometry.flux_surface_profile")
    b_left = profile(psi_samples=psi[left_index], values=b_t[left_index], target=psi)["values"]
    b_right = profile(psi_samples=psi[right_index], values=b_t[right_index], target=psi)["values"]
    b_ref = profile(psi_samples=psi_reference, values=b_reference, target=psi)["values"]
    phi_ref = _field(inputs.get("phi_ref_v", 0.0), psi_reference, "phi_ref_v")
    phi_ref_grid = profile(psi_samples=psi_reference, values=phi_ref, target=psi)["values"]
    end_loss = asset_loader("scirel.closures.mirror_ambipolar_potential")
    common = {
        key: inputs[key]
        for key in (
            "ion_mass_kg",
            "ion_charge_c",
            "ion_density_ref_m3",
            "ion_temperature_parallel_j",
            "ion_temperature_perpendicular_j",
            "electron_temperature_j",
        )
        if key in inputs
    }
    common.update(
        {
            "ion_mass_kg": inputs["mass_kg"],
            "ion_charge_c": inputs["charge_c"],
            "ion_density_ref_m3": inputs["density_ref_m3"],
            "ion_temperature_parallel_j": inputs["temperature_parallel_j"],
            "ion_temperature_perpendicular_j": inputs["temperature_perpendicular_ref_j"],
            "electron_temperature_j": inputs["electron_temperature_j"],
            "phi_reference_v": phi_ref,
        }
    )
    for key in (
        "electron_density_ref_m3",
        "ion_loss_refill",
        "electron_loss_refill",
        "potential_tolerance_v",
        "current_tolerance",
        "max_iterations",
        "initial_bracket_thermal",
    ):
        if key in inputs:
            common[key] = inputs[key]
    common.setdefault("ion_loss_refill", inputs.get("loss_cone_refill", 0.0))
    mode = inputs.get("plug_potential_mode", "prescribed")
    if mode not in {"prescribed", "ambipolar_end_loss"}:
        raise ValueError("plug_potential_mode must be prescribed or ambipolar_end_loss")

    def endpoint(b_plug, phi_key):
        if mode == "ambipolar_end_loss":
            return end_loss(b_reference, b_plug[reference_index], psi_reference, **common)
        phi = _field(inputs.get(phi_key, 0.0), psi_reference, phi_key)
        return end_loss(
            b_reference,
            b_plug[reference_index],
            psi_reference,
            **common,
            mode="evaluate",
            phi_plug_v=phi,
        )

    left, right = (endpoint(b_left, "phi_plug_left_v"), endpoint(b_right, "phi_plug_right_v"))
    if mode == "ambipolar_end_loss" and any(
        not x.get("current_balance_solved", False) or not x.get("converged", False)
        for x in (left, right)
    ):
        raise RuntimeError("endpoint current balance has not been solved")
    phi_left = profile(psi_samples=psi_reference, values=left["potential_v"], target=psi)["values"]
    phi_right = profile(psi_samples=psi_reference, values=right["potential_v"], target=psi)[
        "values"
    ]
    ambipolar = composition_loader("scirel.closures.compositions.mirror_quasineutral_closure")
    raw_quadrature_order = inputs.get("quadrature_order", 32)
    if (
        isinstance(raw_quadrature_order, (bool, np.bool_))
        or not isinstance(raw_quadrature_order, (int, np.integer))
        or raw_quadrature_order < 8
    ):
        raise ValueError("quadrature_order must be an integer scalar >= 8")
    quadrature_order = int(raw_quadrature_order)
    state = ambipolar(
        {
            "b_t": b_t,
            "psi": psi,
            "mass_kg": inputs["mass_kg"],
            "charge_c": inputs["charge_c"],
            "density_ref_m3": inputs["density_ref_m3"],
            "temperature_parallel_j": inputs["temperature_parallel_j"],
            "temperature_perpendicular_ref_j": inputs["temperature_perpendicular_ref_j"],
            "b_ref_t": b_ref,
            "phi_ref_v": phi_ref_grid,
            "b_plug_left_t": b_left,
            "b_plug_right_t": b_right,
            "phi_plug_left_v": phi_left,
            "phi_plug_right_v": phi_right,
            "loss_cone_refill": inputs.get("loss_cone_refill", 0.0),
            "quadrature_order": quadrature_order,
            "electron_temperature_j": inputs["electron_temperature_j"],
            **(
                {"electron_density_ref_m3": inputs["electron_density_ref_m3"]}
                if "electron_density_ref_m3" in inputs
                else {}
            ),
        }
    )
    for side, endpoint_state in (("end_left_", left), ("end_right_", right)):
        state[f"{side}current_balance_solved"] = bool(endpoint_state["current_balance_solved"])
        for name in (
            "potential_v",
            "ion_particle_flux_m2_s",
            "electron_particle_flux_m2_s",
            "log_current_ratio",
            "relative_current_residual",
        ):
            state[f"{side}{name}"] = profile(
                psi_samples=psi_reference, values=endpoint_state[name], target=psi
            )["values"]
    moments = state["kinetic_moments"]
    state.update(
        {
            "density": state["ion_density"],
            "T_parallel_J": moments["temperature_parallel_j"],
            "T_perpendicular_local_J": moments["temperature_perpendicular_local_j"],
            "untruncated_density": moments["untruncated_density_m3"],
            "density_pitch_integral": moments["density_pitch_integral"],
            "parallel_pitch_integral": moments["parallel_pitch_integral"],
            "perpendicular_pitch_integral": moments["perpendicular_pitch_integral"],
        }
    )
    if confine_to_plug_planes:
        for name in (
            "density",
            "p_parallel",
            "p_perpendicular",
            "ion_density",
            "ion_p_parallel",
            "ion_p_perpendicular",
            "electron_density",
            "electron_pressure",
            "untruncated_density",
        ):
            state[name] = _confine_rows(state[name], left_index, right_index)
        state["relative_charge_residual"] = _confine_rows(
            state["relative_charge_residual"], left_index, right_index
        )
    return state


def solve_grid_mirror_kinetic_closure(inputs=None, **kwargs):
    """Run the grid-aware mirror end-loss and quasineutral closure.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping with required ``r_grid``, ``z_grid``, ``b_t``, ``psi``,
        ``mass_kg``, ``charge_c``, reference density and temperature profiles,
        ``electron_temperature_j``, ``reference_z``, ``plug_left_z`` and
        ``plug_right_z``.  Profiles may be scalars or callables evaluated on
        the caller-owned flux coordinate.  Optional controls include
        ``electron_density_ref_m3``, ``phi_ref_v``, prescribed plug
        potentials, ``plug_potential_mode``, refill fractions,
        ``quadrature_order``, endpoint tolerances and ``max_iterations``.
    **kwargs
        Composition overrides passed to the public composition boundary.

    Returns
    -------
    dict
        Full-grid pressure, density, potential and charge-residual fields;
        nested ``kinetic_moments``; endpoint potential, particle-flux and
        current diagnostics; and legacy density, temperature and pressure
        aliases.  With ``confine_to_plug_planes=True`` (the default), only the
        selected top-level density, pressure and relative-residual aliases are
        zeroed outside the nearest inclusive plug rows; potentials, endpoint
        diagnostics and original moment fields remain full-grid.

    Raises
    ------
    ValueError
        If the grids are unequal, non-rectilinear, nonfinite, too small or
        have nonpositive field; plane coordinates are invalid or unordered;
        the mode or confinement flag is invalid; or quadrature order is not an
        integer of at least 8.  Bound profile and species contracts may raise
        the same error during dispatch.
    RuntimeError
        If an ``ambipolar_end_loss`` endpoint does not return both a converged
        state and ``current_balance_solved``.
    Exception
        Profile, endpoint and nested composition exceptions propagate unchanged.

    Notes
    -----
    ``R`` and ``Z`` use ``[Z, R]`` array order.  ``psi`` is a caller-owned flux
    coordinate and is not rescaled or converted by this composition.  The local
    quasineutral convergence flag and the two endpoint current-balance flags
    describe separate calculations; neither establishes a self-consistent
    magnetic equilibrium.
    """

    from scirel._composition import compose
    from scirel.closures.mirror_ambipolar_potential import (
        solve_mirror_ambipolar_potential as _dependency_0,
    )
    from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile as _dependency_1
    from scirel.closures.mirror_quasineutral_closure import (
        solve_mirror_quasineutral_closure as _dependency_2,
    )

    return compose(
        run_composition,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.closures.mirror_ambipolar_potential": _dependency_0,
                "scirel.geometry.flux_surface_profile": _dependency_1,
            },
            "composition_loader": {
                "scirel.closures.compositions.mirror_quasineutral_closure": _dependency_2
            },
        },
    )


__all__ = ["solve_grid_mirror_kinetic_closure"]
