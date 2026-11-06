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


def _run_composition(inputs, *, asset_loader, composition_loader):
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
    r"""Solve the grid-aware mirror end-loss and quasineutral closure from mapping ports.

    Parameters
    ----------
    inputs : mapping, optional
        Existing input mapping containing the mapping ports documented under Other
        Parameters. The default is None and is merged with named keyword ports by the
        composition boundary. Units: [mapping].
    **kwargs : mapping, optional
        Named mapping ports merged with inputs by the composition boundary. A keyword takes
        precedence over the same key in inputs. Units: [mapping].

    Other Parameters
    ----------------
    r_grid : real array-like converted to float64
        Cylindrical radial mesh coordinate R. Shape: [N_Z,N_R], N_Z,N_R >= 2. Constraints:
        Finite, nonnegative first-row R axis strictly increasing; each row matches that axis
        within np.allclose. Units: [m].
    z_grid : real array-like converted to float64
        Axial mesh coordinate Z. Shape: same [N_Z,N_R] as r_grid. Constraints: Finite
        first-column Z axis strictly increasing; each column matches that axis within
        np.allclose. Units: [m].
    b_t : real array-like converted to float64
        Current local magnetic-field magnitude. Shape: same [N_Z,N_R] grid. Constraints:
        Finite and strictly positive. Units: [T].
    psi : real array-like converted to float64
        Caller-owned flux-profile coordinate on the grid. Shape: same [N_Z,N_R] grid.
        Constraints: Finite; sampled rows need at least two distinct psi coordinates for the
        bound profile operator. The external convention labels psi in Wb; nested Hall
        supplies Wb/rad, so all psi-dependent profiles must follow the supplied coordinate.
        Units: [caller-consistent Wb or Wb/rad].
    mass_kg : real numeric
        Positive-ion particle mass. Shape: scalar. Constraints: Nested ion and endpoint
        operators require finite strictly positive value. Units: [kg].
    charge_c : real numeric
        Positive ion charge. Shape: scalar. Constraints: Nested quasineutral and endpoint
        operators require finite strictly positive charge. Units: [C].
    density_ref_m3 : real numeric or callable yielding float64-convertible arrays
        Ion reference number density, reused at reference row and full grid. Shape: scalar
        or callable(psi) yielding reference-row and full-grid shapes. Constraints: Finite
        nonnegative wherever evaluated; an [N_Z,N_R] fixed array generally cannot broadcast
        to the [N_R] endpoint psi and is not a universally supported form. Units: [m^-3].
    temperature_parallel_j : real numeric or callable yielding float64-convertible arrays
        Ion parallel reference thermal energy. Shape: scalar or callable(psi) yielding
        reference-row and full-grid shapes. Constraints: Finite and strictly positive
        wherever evaluated; fixed 2-D arrays may fail endpoint broadcasting. Units: [J].
    temperature_perpendicular_ref_j : real numeric or callable yielding float64-convertible arrays
        Ion perpendicular reference thermal energy. Shape: scalar or callable(psi) yielding
        reference-row and full-grid shapes. Constraints: Finite and strictly positive
        wherever evaluated; fixed 2-D arrays may fail endpoint broadcasting. Units: [J].
    electron_temperature_j : real numeric or callable yielding float64-convertible arrays
        Prescribed Boltzmann electron thermal energy, also used in endpoint fluxes. Shape:
        scalar or callable(psi) yielding reference-row and full-grid shapes. Constraints:
        Finite and strictly positive wherever evaluated; fixed 2-D arrays may fail endpoint
        broadcasting. Units: [J].
    reference_z : real numeric scalar
        Requested reference plane coordinate, mapped to nearest Z index. Shape: scalar.
        Constraints: Finite and mapped strictly between mapped plug indices. Units: [m].
    plug_left_z : real numeric scalar
        Requested left plug plane coordinate. Shape: scalar. Constraints: Finite; nearest
        index strictly below reference index. Units: [m].
    plug_right_z : real numeric scalar
        Requested right plug plane coordinate. Shape: scalar. Constraints: Finite; nearest
        index strictly above reference index. Units: [m].
    electron_density_ref_m3 : null, real numeric or callable yielding float64-convertible arrays, optional
        Optional electron reference density for both endpoint and nested closures. Shape:
        scalar or callable(psi) yielding reference-row and full-grid shapes. Constraints:
        Omission derives charge-state times ion density; if provided, finite nonnegative and
        same active mask as ion reference density for the nested solve. Default: None.
        Units: [m^-3].
    phi_ref_v : real numeric or callable yielding float64-convertible values, optional
        Reference potential sampled on the reference psi row, then interpolated over the
        full grid. Shape: scalar, [N_R] array or callable(reference-row psi). Constraints:
        Finite and broadcastable to the one-dimensional reference row; a fixed [N_Z,N_R]
        array is not accepted. Default: 0.0. Units: [V].
    phi_plug_left_v : real numeric or callable yielding float64-convertible values, optional
        Prescribed left endpoint potential in prescribed mode. Shape: scalar, [N_R] array or
        callable(reference-row psi). Constraints: Finite and reference-row broadcastable if
        prescribed mode; ignored in ambipolar_end_loss mode. Default: 0.0. Units: [V].
    phi_plug_right_v : real numeric or callable yielding float64-convertible values, optional
        Prescribed right endpoint potential in prescribed mode. Shape: scalar, [N_R] array
        or callable(reference-row psi). Constraints: Finite and reference-row broadcastable
        if prescribed mode; ignored in ambipolar_end_loss mode. Default: 0.0. Units: [V].
    plug_potential_mode : str, optional
        Endpoint potential evaluation or end-current-balance solve. Shape: scalar string.
        Constraints: Only 'prescribed' or 'ambipolar_end_loss'. Default: 'prescribed'.
        Units: [enum].
    loss_cone_refill : real numeric, optional
        Refill fraction passed to the nested mirror moments and used as default
        ion_loss_refill. Shape: scalar. Constraints: Nested moments require finite [0,1];
        ambipolar_end_loss requires a positive ion_loss_refill, supplied separately or
        inherited here. Default: 0.0. Units: [dimensionless].
    quadrature_order : Python or NumPy integer, excluding bool, optional
        Finite pitch quadrature order for nested mirror moments. Shape: scalar. Constraints:
        At least 8; unlike the nested moment leaf, this parent rejects nonintegral values
        before dispatch. Default: 32. Units: [count].
    ion_loss_refill : real numeric, optional
        Ion one-way endpoint-flux refill, overriding the loss_cone_refill default. Shape:
        scalar. Constraints: Finite [0,1]; strictly positive for ambipolar_end_loss mode.
        The endpoint operator itself defaults to 1.0, but this graph always passes the
        parent-derived value. Default: 'loss_cone_refill if supplied, otherwise 0.0'. Units:
        [dimensionless].
    electron_loss_refill : real numeric, optional
        Electron one-way endpoint-flux refill. Shape: scalar. Constraints: Finite in (0,1].
        Default: 1.0. Units: [dimensionless].
    potential_tolerance_v : real numeric, optional
        Absolute endpoint-potential tolerance for end-current solve. Shape: scalar.
        Constraints: Finite and strictly positive; independent of the nested quasineutral
        graph's default tolerance. Default: 1e-06. Units: [V].
    current_tolerance : real numeric, optional
        Endpoint log-current-ratio convergence tolerance. Shape: scalar. Constraints: Finite
        and strictly positive. Default: 1e-10. Units: [dimensionless].
    max_iterations : Python or NumPy integer, excluding bool, optional
        Endpoint ambipolar bisection limit. Shape: scalar. Constraints: At least one; this
        parent passes it only to endpoint solves and does not override the nested graph's
        separate default 100. Default: 100. Units: [iterations].
    initial_bracket_thermal : real numeric, optional
        Initial endpoint-potential bracket half-width in thermal-voltage units. Shape:
        scalar. Constraints: Finite and strictly positive; passed only to endpoint solves.
        Default: 8.0. Units: [dimensionless].
    confine_to_plug_planes : Python or NumPy bool, optional
        Whether selected top-level returned fields are zeroed outside nearest plug rows.
        Shape: scalar. Constraints: A boolean scalar only, not numeric 0/1. It does not mask
        all returned fields. Default: True. Units: [bool].

    Returns
    -------
    p_parallel : float64 ndarray
        Total ion-plus-electron parallel pressure, masked outside plugs by default. Shape:
        [N_Z,N_R]. Constraints: Top-level mask does not alter active rows. Units: [Pa].
    p_perpendicular : float64 ndarray
        Total ion-plus-electron perpendicular pressure, masked outside plugs by default.
        Shape: [N_Z,N_R]. Constraints: Top-level mask does not alter active rows. Units:
        [Pa].
    ion_density : float64 ndarray
        Ion density from nested closure, masked outside plugs by default. Shape: [N_Z,N_R].
        Constraints: May differ from unmasked density_m3 outside plugs. Units: [m^-3].
    electron_density : float64 ndarray
        Boltzmann electron density, masked outside plugs by default. Shape: [N_Z,N_R].
        Constraints: The top-level field is zero outside the inclusive plug interval when
        confinement is enabled. Units: [m^-3].
    electrostatic_potential : float64 ndarray
        Nested local quasineutral potential. Shape: [N_Z,N_R]. Constraints: Never masked by
        confine_to_plug_planes. Units: [V].
    relative_charge_residual : float64 ndarray
        Nested relative ion-charge/electron-density residual, masked outside plugs by
        default. Shape: [N_Z,N_R]. Constraints: Not the endpoint log-current ratio. Units:
        [dimensionless].
    kinetic_moments : dict
        Full nested mirror ion-moment mapping. Shape: mapping of [N_Z,N_R] fields.
        Constraints: Remains full-grid even when selected top-level aliases are masked.
        Units: [mixed; see mirror-constrained-moments asset].
    ion_p_parallel : float64 ndarray
        Ion parallel pressure component, masked outside plugs by default. Shape: [N_Z,N_R].
        Constraints: Original p_parallel_pa remains unmasked. Units: [Pa].
    ion_p_perpendicular : float64 ndarray
        Ion perpendicular pressure component, masked outside plugs by default. Shape:
        [N_Z,N_R]. Constraints: Original p_perpendicular_pa remains unmasked. Units: [Pa].
    electron_pressure : float64 ndarray
        Electron pressure component, masked outside plugs by default. Shape: [N_Z,N_R].
        Constraints: No separate masked copy in kinetic_moments. Units: [Pa].
    density_m3 : float64 ndarray
        Original nested ion density under moment-field name. Shape: [N_Z,N_R]. Constraints:
        Unmasked even when ion_density and density are zeroed outside plugs. Units: [m^-3].
    p_parallel_pa : float64 ndarray
        Original nested ion parallel pressure. Shape: [N_Z,N_R]. Constraints: Unmasked even
        when ion_p_parallel is zeroed outside plugs. Units: [Pa].
    p_perpendicular_pa : float64 ndarray
        Original nested ion perpendicular pressure. Shape: [N_Z,N_R]. Constraints: Unmasked
        even when ion_p_perpendicular is zeroed outside plugs. Units: [Pa].
    temperature_parallel_j : float64 ndarray
        Original nested ion parallel thermal-energy parameter. Shape: [N_Z,N_R].
        Constraints: Unmasked; not pressure over depleted density. Units: [J].
    temperature_perpendicular_local_j : float64 ndarray
        Original nested local perpendicular thermal-energy parameter. Shape: [N_Z,N_R].
        Constraints: Unmasked. Units: [J].
    untruncated_density_m3 : float64 ndarray
        Original nested ion density before loss-cone pitch depletion. Shape: [N_Z,N_R].
        Constraints: Unmasked even when untruncated_density alias is masked. Units: [m^-3].
    density_pitch_integral : float64 ndarray
        Density pitch-occupation integral factor. Shape: [N_Z,N_R]. Constraints: Full-grid
        diagnostic; never masked. Units: [dimensionless].
    parallel_pitch_integral : float64 ndarray
        Parallel-pressure pitch-occupation integral factor. Shape: [N_Z,N_R]. Constraints:
        Full-grid diagnostic; never masked. Units: [dimensionless].
    perpendicular_pitch_integral : float64 ndarray
        Perpendicular-pressure pitch-occupation integral factor. Shape: [N_Z,N_R].
        Constraints: Full-grid diagnostic; never masked. Units: [dimensionless].
    iterations : int
        Nested local quasineutral bisection iteration count. Shape: scalar. Constraints: Not
        the two endpoint iteration counts, which are not exposed by this graph. Units:
        [iterations].
    converged : bool
        Nested local quasineutral convergence flag. Shape: scalar. Constraints: Endpoint
        states must also have returned successfully, but their flags are not exposed. Units:
        [bool].
    end_left_potential_v : float64 ndarray
        Left endpoint potential interpolated from reference-row psi to the full grid. Shape:
        [N_Z,N_R]. Constraints: Full-grid, unmasked. Units: [V].
    end_left_ion_particle_flux_m2_s : float64 ndarray
        Mapped left one-way ion particle flux. Shape: [N_Z,N_R]. Constraints: Interpolated
        in psi, not spatially propagated. Units: [m^-2 s^-1].
    end_left_electron_particle_flux_m2_s : float64 ndarray
        Mapped left one-way electron particle flux. Shape: [N_Z,N_R]. Constraints:
        Interpolated in psi, not spatially propagated. Units: [m^-2 s^-1].
    end_left_log_current_ratio : float64 ndarray
        Mapped left logarithmic ion/electron current ratio. Shape: [N_Z,N_R]. Constraints:
        Endpoint diagnostic, not nested charge residual. Units: [dimensionless].
    end_left_relative_current_residual : float64 ndarray
        Mapped left relative ion/electron current residual. Shape: [N_Z,N_R]. Constraints:
        Endpoint diagnostic, not nested charge residual. Units: [dimensionless].
    end_right_potential_v : float64 ndarray
        Right endpoint potential interpolated from reference-row psi to the full grid.
        Shape: [N_Z,N_R]. Constraints: Full-grid, unmasked. Units: [V].
    end_right_ion_particle_flux_m2_s : float64 ndarray
        Mapped right one-way ion particle flux. Shape: [N_Z,N_R]. Constraints: Interpolated
        in psi, not spatially propagated. Units: [m^-2 s^-1].
    end_right_electron_particle_flux_m2_s : float64 ndarray
        Mapped right one-way electron particle flux. Shape: [N_Z,N_R]. Constraints:
        Interpolated in psi, not spatially propagated. Units: [m^-2 s^-1].
    end_right_log_current_ratio : float64 ndarray
        Mapped right logarithmic ion/electron current ratio. Shape: [N_Z,N_R]. Constraints:
        Endpoint diagnostic, not nested charge residual. Units: [dimensionless].
    end_right_relative_current_residual : float64 ndarray
        Mapped right relative ion/electron current residual. Shape: [N_Z,N_R]. Constraints:
        Endpoint diagnostic, not nested charge residual. Units: [dimensionless].
    density : float64 ndarray
        Ion density alias for downstream Hall closure. Shape: [N_Z,N_R]. Constraints: Alias
        of ion_density before optional masking; selected top-level field is masked by
        default. Units: [m^-3].
    T_parallel_J : float64 ndarray
        Ion parallel thermal-energy alias from kinetic_moments. Shape: [N_Z,N_R].
        Constraints: Unmasked; not recalculated from masked pressure/density. Units: [J].
    T_perpendicular_local_J : float64 ndarray
        Local ion perpendicular thermal-energy alias from kinetic_moments. Shape: [N_Z,N_R].
        Constraints: Unmasked; not recalculated from masked pressure/density. Units: [J].
    untruncated_density : float64 ndarray
        Ion untruncated-density alias, masked outside plugs by default. Shape: [N_Z,N_R].
        Constraints: Original untruncated_density_m3 remains unmasked. Units: [m^-3].
    end_left_current_balance_solved : Python bool
        Whether this endpoint was solved for current balance, separately from local
        quasineutral convergence. Shape: scalar. Constraints: False in prescribed mode; True
        in ambipolar_end_loss mode. Units: [boolean].
    end_right_current_balance_solved : Python bool
        Whether this endpoint was solved for current balance, separately from local
        quasineutral convergence. Shape: scalar. Constraints: False in prescribed mode; True
        in ambipolar_end_loss mode. Units: [boolean].

    Raises
    ------
    ValueError
        If the grids, profiles, plane controls, potential mode, confinement flag,
        quadrature order or bound species contract are invalid.
    RuntimeError
        If an ambipolar_end_loss endpoint does not report both convergence and a solved
        current balance.
    Exception
        Any profile, endpoint or nested composition exception propagates unchanged.

    See Also
    --------
    scirel.closures.solve_mirror_ambipolar_potential
        Evaluate or solve one mirror endpoint potential.
    scirel.closures.solve_mirror_quasineutral_closure
        Evaluate the local quasineutral closure.
    scirel.geometry.evaluate_flux_surface_profile
        Map reference-row profiles over the full grid.

    Notes
    -----
        The public wrapper accepts the existing `inputs` mapping and named `**kwargs`
        mapping ports through the composition boundary. `R` and `Z` use `[Z, R]` array
        order. `psi` is a caller-owned flux coordinate and is not rescaled or converted by
        this composition. The `plug_potential_mode`, optional `electron_density_ref_m3`, and
        `confine_to_plug_planes` controls are consumed by the bound operators with their
        declared semantics. Nested `kinetic_moments` remains an ordinary Python dictionary.
        Local quasineutral and endpoint current-balance flags describe separate
        calculations.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import solve_grid_mirror_kinetic_closure
    >>> e = 1.602176634e-19
    >>> r, z = np.linspace(0.0, 0.2, 5), np.linspace(-1.0, 1.0, 7)
    >>> R, Z = np.meshgrid(r, z)
    >>> state = solve_grid_mirror_kinetic_closure({'r_grid': R, 'z_grid': Z, 'b_t': 1.0 + 3.0*np.abs(Z), 'psi': 0.5*R**2, 'mass_kg': 1.67262192595e-27, 'charge_c': e, 'density_ref_m3': 1.0e18, 'temperature_parallel_j': 1000.0*e, 'temperature_perpendicular_ref_j': 2000.0*e, 'electron_temperature_j': 500.0*e, 'reference_z': 0.0, 'plug_left_z': -1.0, 'plug_right_z': 1.0, 'loss_cone_refill': 0.05, 'quadrature_order': 24, 'plug_potential_mode': 'ambipolar_end_loss'})
    >>> assert state['p_parallel'].shape == R.shape
    >>> assert np.all(state['end_left_potential_v'] < 0.0)
    >>> assert np.max(np.abs(state['relative_charge_residual'])) < 1e-9
    >>> assert state['end_left_current_balance_solved'] and state['end_right_current_balance_solved']
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
        _run_composition,
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
