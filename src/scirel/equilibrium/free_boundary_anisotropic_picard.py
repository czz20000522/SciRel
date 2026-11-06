"""Standalone orchestration of the anisotropic free-boundary Picard state loop."""

from __future__ import annotations
from scirel._validation import (
    finite_scalar as _require_finite_scalar,
    integer_scalar as _require_integer_scalar,
    bool_scalar as _require_bool_scalar,
)
from collections.abc import Mapping
import numpy as np
from ._anisotropic_numerics import cell_areas, flux_field_increment


def _require_mapping(value, name):
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _require_ports(inputs):
    for name in (
        "r_grid",
        "z_grid",
        "psi_vac",
        "br_vac",
        "bz_vac",
        "g_psi",
        "params",
        "tol",
        "maxiter",
        "relax",
    ):
        if name not in inputs:
            raise ValueError(f"{name} is required by composition.yaml")
    closure = inputs.get("pressure_closure")
    if not callable(closure):
        raise ValueError("pressure_closure must be a callable N4 closure port")
    return closure


def _profiles(closure, psi, magnetic_field, params):
    profiles = closure({"psi": psi, "B": magnetic_field, "params": params})
    profiles = _require_mapping(profiles, "pressure_closure output")
    for field in ("p_parallel", "p_perp", "density", "electron_temperature"):
        if field not in profiles:
            raise ValueError(f"pressure_closure output missing {field}")
    shape = np.asarray(psi).shape
    for field in ("p_parallel", "p_perp"):
        try:
            value = np.asarray(profiles[field], dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"pressure_closure output {field} must be a finite nonnegative array with shape {shape}"
            ) from exc
        if value.shape != shape or not np.all(np.isfinite(value)) or np.any(value < 0.0):
            raise ValueError(
                f"pressure_closure output {field} must be a finite nonnegative array with shape {shape}"
            )
        profiles[field] = value
    for field in ("density", "electron_temperature"):
        if profiles[field] is None:
            continue
        try:
            value = np.asarray(profiles[field], dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"pressure_closure output {field} must be None or a finite nonnegative array with shape {shape}"
            ) from exc
        if value.shape != shape or not np.all(np.isfinite(value)) or np.any(value < 0.0):
            raise ValueError(
                f"pressure_closure output {field} must be None or a finite nonnegative array with shape {shape}"
            )
        profiles[field] = value
    return profiles


def _boundary_config(value):
    if value is None:
        return None
    value = _require_mapping(value, "boundary_correction")
    required = ("boundary_sample_matrix", "green_boundary_to_boundary", "green_boundary_to_field")
    missing = [key for key in required if key not in value]
    if missing:
        raise ValueError(f"boundary_correction missing keys: {missing}")
    return value


def _run_composition(inputs, *, asset_loader):
    """Iterate pressure/current/Green feedback until its full state closes.

    State comprises psi, BR, BZ and relaxed cell currents. Every iteration
    recomputes pressure and current from the predecessor fields, then applies
    current relaxation, Green feedback and the same wall correction to flux
    and its magnetic derivatives. The unrelaxed target, including wall fields,
    controls termination; relaxed flux change remains a diagnostic only.
    Returned pressure/current and force compatibility use the returned fields.
    ``plasma_mask`` is a declared domain selector: True cells retain the
    computed feedback and terminal current, False cells are zeroed before
    feedback and in terminal ``j_phi``, and None treats all cells as active.
    Invalid masks fail before iteration; these zeros do not hide numerical
    failures.
    压力闭合对给定状态须确定且不修改输入；每次求值前检查B下界。
    全状态残差比较未松弛目标与当前态：各场分量的L2分母为目标、
    当前及真空范数的最大值，电流分母为目标和当前范数的最大值；
    全零状态记零。返回最大残差及磁通、场和电流三个分项。
    A full state residual above tol at maxiter is nonconvergence, even when
    relaxation suppresses delta-psi. This corrects predecessor early stopping
    and flux-only fixed-point qualification without changing gyrotropic physics.
    """
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    r_grid = np.asarray(inputs["r_grid"], dtype=float)
    z_grid = np.asarray(inputs["z_grid"], dtype=float)
    if (
        r_grid.ndim != 2
        or z_grid.shape != r_grid.shape
        or r_grid.shape[0] < 3
        or (r_grid.shape[1] < 3)
    ):
        raise ValueError(
            "r_grid and z_grid must be equal-shape 2-D grids with at least 3 points per axis"
        )
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)):
        raise ValueError("r_grid and z_grid must be finite")
    r_axis, z_axis = (r_grid[0, :], z_grid[:, 0])
    if (
        not np.allclose(r_grid, r_axis[np.newaxis, :])
        or not np.allclose(z_grid, z_axis[:, np.newaxis])
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or r_axis[0] < 0.0
    ):
        raise ValueError(
            "r_grid and z_grid must be finite, strictly increasing tensor-product grids with nonnegative R"
        )
    plasma_mask = None
    if inputs.get("plasma_mask") is not None:
        plasma_mask = np.asarray(inputs["plasma_mask"])
        if plasma_mask.shape != r_grid.shape or plasma_mask.dtype != np.dtype(bool):
            raise ValueError("plasma_mask must be a boolean array with the same shape as r_grid")
    pressure_closure = _require_ports(inputs)
    params = dict(_require_mapping(inputs["params"], "params"))
    magnitude = asset_loader("scirel.field.poloidal_field_magnitude")
    current = asset_loader("scirel.equilibrium.anisotropic_toroidal_current")
    feedback = asset_loader("scirel.equilibrium.anisotropic_picard_feedback")
    residual_operator = asset_loader("scirel.diagnostics.picard_flux_residual")
    boundary_operator = asset_loader("scirel.field.ideal_conductor_boundary")
    psi, br, bz = (inputs["psi_vac"], inputs["br_vac"], inputs["bz_vac"])
    initial_field = magnitude(br, bz)
    if "B0" not in params:
        b0 = _require_finite_scalar(inputs.get("b0"), "b0", initial_field["B0_default"])
        if b0 <= 0.0:
            raise ValueError("b0 must be a finite positive scalar")
        params["B0"] = b0
    tol = _require_finite_scalar(inputs["tol"], "tol", None)
    maxiter = _require_integer_scalar(inputs["maxiter"], "maxiter", None, minimum=0)
    relax = _require_finite_scalar(inputs["relax"], "relax", None)
    if tol <= 0.0 or not 0.0 <= relax <= 1.0:
        raise ValueError("tol, maxiter, and relax violate the declared Picard bounds")
    boundary = _boundary_config(inputs.get("boundary_correction"))
    compatibility_tol = _require_finite_scalar(
        inputs.get("compatibility_tol"), "compatibility_tol", 0.05
    )
    strict = _require_bool_scalar(inputs.get("strict_compatibility"), "strict_compatibility", True)
    minimum_field = _require_finite_scalar(inputs.get("minimum_field"), "minimum_field", 1e-8)
    if compatibility_tol < 0.0 or minimum_field <= 0.0:
        raise ValueError("compatibility_tol and minimum_field are invalid")

    def apply_boundary(state):
        if boundary is None:
            return state, None
        wall = boundary_operator(
            state["psi"].ravel(),
            boundary["boundary_sample_matrix"],
            boundary["green_boundary_to_boundary"],
            boundary["green_boundary_to_field"],
            rcond=boundary.get("rcond", 1e-10),
        )
        corrected = dict(state)
        corrected["psi"] = wall["corrected_field_flux"].reshape(r_grid.shape)
        delta = flux_field_increment(
            r_grid, z_grid, wall["field_flux_correction"].reshape(r_grid.shape)
        )
        corrected["BR"] = state["BR"] + delta["B_R"]
        corrected["BZ"] = state["BZ"] + delta["B_Z"]
        return corrected, wall

    def target_state(parts):
        target = feedback(
            parts["j_phi"],
            r_grid,
            z_grid,
            plasma_mask,
            None,
            0.0,
            inputs["g_psi"],
            inputs.get("g_br"),
            inputs.get("g_bz"),
            inputs["psi_vac"],
            inputs["br_vac"],
            inputs["bz_vac"],
            cell_edges=inputs.get("cell_edges"),
        )
        return apply_boundary(target)[0]

    def state_residuals(target, psi_state, br_state, bz_state, current_state):
        # A small relaxed step cannot establish a fixed point. All fields and
        # currents consumed by the next pressure/current evaluation must close.
        # Scaling before subtraction/norm avoids overflow of finite states.
        def relative(candidate, state, reference):
            arrays = [np.asarray(x, dtype=float) for x in (candidate, state, reference)]
            scale = max(float(np.max(np.abs(x), initial=0.0)) for x in arrays)
            if scale == 0.0:
                return 0.0
            a, b, c = (x / scale for x in arrays)
            denominator = max(float(np.linalg.norm(x)) for x in (a, b, c))
            return float(np.linalg.norm(a - b)) / denominator

        flux_error = relative(target["psi"], psi_state, inputs["psi_vac"])
        field_error = max(
            relative(target["BR"], br_state, inputs["br_vac"]),
            relative(target["BZ"], bz_state, inputs["bz_vac"]),
        )
        old = np.zeros(r_grid.size) if current_state is None else current_state
        current_error = relative(target["picard_current_state"], old, np.zeros(r_grid.size))
        return flux_error, field_error, current_error

    currents_old = None
    residual = float("inf")
    residual_history = []
    iterations = 0
    profiles = None
    current_parts = None
    boundary_result = None
    boundary_flux_correction = None
    while iterations < maxiter:
        field = magnitude(br, bz)
        if np.any(field["B"] < minimum_field):
            raise FloatingPointError(
                "free-boundary intermediate magnetic field fell below minimum_field"
            )
        profiles = _profiles(pressure_closure, psi, field["B"], params)
        current_parts = current(
            inputs["r_grid"], inputs["z_grid"], br, bz, profiles["p_parallel"], profiles["p_perp"]
        )
        target = target_state(current_parts)
        if iterations > 0 and max(state_residuals(target, psi, br, bz, currents_old)) <= tol:
            break
        psi_previous = psi
        step = feedback(
            current_parts["j_phi"],
            inputs["r_grid"],
            inputs["z_grid"],
            plasma_mask,
            currents_old,
            relax,
            inputs["g_psi"],
            inputs.get("g_br"),
            inputs.get("g_bz"),
            inputs["psi_vac"],
            inputs["br_vac"],
            inputs["bz_vac"],
            cell_edges=inputs.get("cell_edges"),
        )
        step, boundary_result = apply_boundary(step)
        psi, br, bz = (step["psi"], step["BR"], step["BZ"])
        if boundary_result is not None:
            boundary_flux_correction = boundary_result["field_flux_correction"].reshape(
                r_grid.shape
            )
        residual = residual_operator(psi_previous, psi)["residual"]
        residual_history.append(residual)
        currents_old = step["picard_current_state"]
        iterations += 1
    field = magnitude(br, bz)
    if np.any(field["B"] < minimum_field):
        raise FloatingPointError("free-boundary terminal magnetic field fell below minimum_field")
    profiles = _profiles(pressure_closure, psi, field["B"], params)
    current_parts = current(
        inputs["r_grid"], inputs["z_grid"], br, bz, profiles["p_parallel"], profiles["p_perp"]
    )
    terminal_j_phi = np.asarray(current_parts["j_phi"], dtype=float)
    if plasma_mask is not None:
        terminal_j_phi = np.where(plasma_mask, terminal_j_phi, 0.0)
    if currents_old is None:
        step = feedback(
            current_parts["j_phi"],
            inputs["r_grid"],
            inputs["z_grid"],
            plasma_mask,
            None,
            relax,
            inputs["g_psi"],
            inputs.get("g_br"),
            inputs.get("g_bz"),
            inputs["psi_vac"],
            inputs["br_vac"],
            inputs["bz_vac"],
            cell_edges=inputs.get("cell_edges"),
        )
        currents_old = step["initial_picard_current_state"]
    terminal_cell_currents = terminal_j_phi * cell_areas(r_grid, z_grid, inputs.get("cell_edges"))
    target = target_state(current_parts)
    flux_fixed_point_residual, field_fixed_point_residual, current_fixed_point_residual = (
        state_residuals(target, psi, br, bz, currents_old)
    )
    fixed_point_residual = max(
        flux_fixed_point_residual, field_fixed_point_residual, current_fixed_point_residual
    )
    force_diagnostics = current_parts["force_diagnostics"]
    active = np.ones_like(r_grid, dtype=bool) if plasma_mask is None else plasma_mask
    from ._anisotropic_numerics import residual_metrics

    compatibility = residual_metrics(
        force_diagnostics["parallel_force"],
        np.hypot(force_diagnostics["force_R"], force_diagnostics["force_Z"]),
        force_diagnostics["parallel_force_roundoff"],
        active,
    )
    compatible = compatibility["error"] <= compatibility_tol
    if strict and not compatible:
        raise ValueError("free-boundary parallel pressure force exceeds compatibility_tol")
    return {
        "psi": psi,
        "BR": br,
        "BZ": bz,
        "B": field["B"],
        "profiles": {
            key: profiles[key]
            for key in ("p_parallel", "p_perp", "density", "electron_temperature")
        },
        "j_phi": terminal_j_phi,
        "plasma_currents": terminal_cell_currents,
        "picard_current_state": currents_old,
        "gradp_term": current_parts["gradp_term"],
        "anisotropy_curvature_term": current_parts["anisotropy_curvature_term"],
        "converged": bool(fixed_point_residual <= tol and compatible and iterations > 0),
        "fixed_point_residual": fixed_point_residual,
        "flux_fixed_point_residual": flux_fixed_point_residual,
        "field_fixed_point_residual": field_fixed_point_residual,
        "current_fixed_point_residual": current_fixed_point_residual,
        "flux_converged": bool(residual <= tol),
        "equilibrium_compatible": compatible,
        "force_diagnostics": force_diagnostics,
        "parallel_force_diagnostics": compatibility,
        "iterations": iterations,
        "residual": residual,
        "residual_history": np.asarray(residual_history, dtype=float),
        "parameters": params,
        "boundary_currents": None
        if boundary_result is None
        else boundary_result["boundary_currents"],
        "boundary_flux_correction": boundary_flux_correction,
        "boundary_residual_norm": None
        if boundary_result is None
        else boundary_result["residual_norm"],
        "failure_reason": "parallel_force_incompatible"
        if not compatible
        else None
        if fixed_point_residual <= tol and iterations > 0
        else "maxiter_reached",
    }


def solve_free_boundary_anisotropic_picard(inputs=None, **kwargs):
    """Run the free-boundary anisotropic Picard state loop.

    Parameters
    ----------
    inputs : mapping, optional
        Composition input mapping. Its declared keys are listed under Other Parameters.
    kwargs : mapping, optional
        Additional composition inputs merged at the public boundary.

    Other Parameters
    ----------------
    r_grid : finite real array-like
        Cylindrical radius tensor grid [m] Shape [N_Z,N_R]. At least three samples per axis; strictly increasing, strictly monotone tensor axis; same shape as z_grid.
    z_grid : finite real array-like
        Axial coordinate tensor grid [m] Shape [N_Z,N_R]. Same shape as r_grid; strictly increasing, strictly monotone axial axis.
    psi_vac : finite real array-like
        Vacuum/external psi=R A_phi and initial Picard flux state [Wb/rad] Shape [N_Z,N_R]. Exact grid shape; validated by the feedback dependency during iteration or the zero-step terminal branch.
    br_vac : finite real array-like
        Vacuum radial poloidal field and initial BR [T] Shape [N_Z,N_R]. Exact grid shape; field-magnitude dependency validates finiteness before closure.
    bz_vac : finite real array-like
        Vacuum axial poloidal field and initial BZ [T] Shape [N_Z,N_R]. Exact grid shape and co-located with br_vac.
    g_psi : finite real array-like
        Dense source-cell-current to psi=R A_phi Green matrix [Wb/rad/A] Shape [N_Z*N_R,N_Z*N_R]. Exact square grid-point size, with C-order source columns and field rows.
    g_br : finite real array-like or None
        Optional source-current to radial-field Green matrix [T/A] Shape [N_Z*N_R,N_Z*N_R] or null. Must be supplied together with g_bz; when both are omitted, derive the BR increment from -(∂psi/∂Z)/R of the newly added plasma psi, then add br_vac and the optional wall increment.
    g_bz : finite real array-like or None
        Optional source-current to axial-field Green matrix [T/A] Shape [N_Z*N_R,N_Z*N_R] or null. Must be supplied together with g_br; when both are omitted, derive the BZ increment from (∂psi/∂R)/R of the newly added plasma psi (regular limit on the axis), then add bz_vac and the optional wall increment.
    params : Python mapping
        Caller-owned pressure-closure parameter mapping [mixed] Shape mapping. Shallow-copied before use; if B0 is absent, the graph inserts positive b0 or the initial field-magnitude median. Other keys are passed through without physical validation by this graph.
    pressure_closure : Python callable
        Caller-provided pressure closure evaluated at current state [psi Wb/rad, B T; pressure output Pa] Shape callable({psi,B,params})->mapping. Returns p_parallel, p_perp, density and electron_temperature; pressures must be finite nonnegative exact-grid arrays; latter two may be None or finite nonnegative exact-grid arrays. The relation for a given state must be deterministic and must not rewrite inputs, and multiple evaluations are allowed; a field below minimum_field is rejected before the callback.
    tol : finite real scalar
        Upper bound on the unrelaxed relative residual of every feedback state Shape scalar. Finite strictly positive; compare max(flux_fixed_point_residual,field_fixed_point_residual,current_fixed_point_residual), and do not substitute the relaxed flux step.
    maxiter : integer scalar, not bool
        Maximum number of Picard updates [iteration] Shape scalar. Nonnegative; zero skips the update loop but still runs terminal closure/current evaluation.
    relax : finite real scalar
        Retention weight of previous relaxed cell currents Shape scalar. 0 <= relax <= 1; this is current-state, not flux-state, relaxation.
    b0 : finite real scalar or None
        Positive reference field inserted into params.B0 only if that key is absent [T] Shape scalar or null. When needed, None uses the median initial field magnitude; an explicit value must be positive. An existing params.B0 is not replaced.
    plasma_mask : boolean array or None
        Active-cell selector for feedback and terminal current [boolean] Shape [N_Z,N_R] or null. Exact grid shape and bool dtype when supplied; True cells retain computed feedback and terminal current, while False cells are zeroed in both.
    boundary_correction : Python mapping or None
        Optional ideal-conductor wall-flux correction configuration [mixed] Shape mapping or null. When supplied, requires dimensionless boundary_sample_matrix [N_b,N_f] and Wb/rad/A green_boundary_to_boundary [N_b,N_w] and green_boundary_to_field [N_f,N_w]; optional rcond defaults to 1e-10. Matrix validation belongs to the wall Operator.
    cell_edges : pair of finite arrays or None
        Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current [m] Shape (N_R+1, N_Z+1) arrays or None. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.
    compatibility_tol : float
        Maximum resolved parallel-force fraction Shape scalar. Maximum resolved parallel-force fraction.
    minimum_field : float
        Positive terminal field floor in T [T] Shape scalar. Finite strictly positive; require all B>=minimum_field before every pressure-closure/current evaluation, including the initial state, intermediate feedback states and the returned state.
    strict_compatibility : bool
        Raise on incompatible parallel pressure force; false retains explicit failed compatibility Shape scalar. Raise on incompatible parallel pressure force; false retains explicit failed compatibility.

    Returns
    -------
    psi : float64
        Last wall-corrected or directly projected psi=R A_phi state [Wb/rad] Shape [N_Z,N_R]. At maxiter=0 equals psi_vac after terminal evaluation; optional wall correction changes psi and adds its consistent discrete magnetic-field increment.
    BR : float64
        Last radial field state including plasma and optional wall-flux increments [T] Shape [N_Z,N_R]. The supplied br_vac plus the g_br plasma response when field Green matrices are supplied, or the discrete radial field from the plasma flux increment otherwise; a completed wall correction adds its discrete radial field increment.
    BZ : float64
        Last axial field state including plasma and optional wall-flux increments [T] Shape [N_Z,N_R]. The supplied bz_vac plus the g_bz plasma response when field Green matrices are supplied, or the discrete axial field from the plasma flux increment otherwise; a completed wall correction adds its discrete axial field increment.
    B : float64
        Terminal poloidal magnitude from returned BR/BZ [T] Shape [N_Z,N_R]. Reevaluated from the returned BR/BZ after bounded iteration, including the discrete wall-flux field increment when present. Coherence of the supplied vacuum and Green responses remains a caller precondition.
    profiles : Python mapping
        Terminal pressure closure fields [p_parallel/p_perp Pa; density m^-3 or caller units; electron_temperature caller units] Shape mapping. Contains exactly p_parallel, p_perp, density and electron_temperature from the terminal callback, after array validation.
    j_phi : float64
        Terminal toroidal current density after optional mask [A/m^2] Shape [N_Z,N_R]. Reevaluated at final psi and B; True cells retain the computed value and False cells are zero.
    plasma_currents : float64
        Terminal or step current density integrated with the explicitly declared node/cell-domain weights [A] Shape [N_Z,N_R]. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.
    picard_current_state : float64
        Last relaxed flattened cell-current feedback state [A] Shape [N_Z*N_R]. At maxiter=0, the dependency's zero initial state is returned.
    gradp_term : float64
        Terminal isotropic-comparison current contribution [A/m^2] Shape [N_Z,N_R]. From unmasked terminal current decomposition; may be nonzero outside plasma_mask.
    anisotropy_curvature_term : float64
        Terminal current remainder after isotropic comparison [A/m^2] Shape [N_Z,N_R]. From unmasked current decomposition; may be nonzero outside plasma_mask.
    converged : bool
        True when every unrelaxed state closes, parallel pressure force is compatible, and at least one iteration has executed [boolean] Shape scalar. fixed_point_residual<=tol and equilibrium_compatible and iterations>0; a small flux step caused by relaxation is not sufficient to prove convergence.
    iterations : integer
        Number of performed feedback updates [iteration] Shape scalar. 0 <= iterations <= maxiter.
    residual : float
        Last relative flux-state change Shape scalar. Initially infinity for maxiter=0; finite after a successful update.
    residual_history : float64 array
        Relative flux change after each completed update Shape [iterations]. Empty when maxiter=0; otherwise one value per update.
    parameters : Python dict
        Shallow-copied input parameters with inserted B0 if absent [mixed] Shape mapping. Other caller keys are not normalized by the graph.
    boundary_currents : float64 array or None
        Last ideal-conductor source-current coefficients [A] Shape [N_wall] or null. None without a completed wall correction; from the last update if enabled.
    boundary_flux_correction : float64 array or None
        Last wall response at field flux points [Wb/rad] Shape [N_Z,N_R] or null. None without a completed wall correction; its discrete flux derivatives are added to BR and BZ during that update.
    boundary_residual_norm : float or None
        Last sampled boundary-flux residual norm [Wb/rad] Shape scalar or null. None without a completed wall correction; a nonzero value is allowed.
    failure_reason : str or None
        Explicit bounded nonconvergence marker Shape string or null. parallel_force_incompatible when compatibility fails and strict_compatibility=false; otherwise None when an update executed and the full fixed point passes, or maxiter_reached when it does not pass or when the step count is zero.
    fixed_point_residual : float
        Full unrelaxed fixed-point residual of the returned state Shape scalar. max(flux_fixed_point_residual,field_fixed_point_residual,current_fixed_point_residual); all candidates use the same plasma/wall projection, and convergence requires this value<=tol.
    force_diagnostics : dict
        Full terminal force mapping [mixed SI] Shape mapping. Full terminal force mapping.
    parallel_force_diagnostics : dict
        Compatibility reports the residual above a dimensioned 64-epsilon tensor/stencil rounding envelope, retaining raw absolute and relative residuals and the envelope. This is a floating-point resolution diagnostic, not a truncation-error bound or evidence that a sub-resolution physical force is exactly zero [mixed SI] Shape mapping. Compatibility reports the residual above a dimensioned 64-epsilon tensor/stencil rounding envelope, retaining raw absolute and relative residuals and the envelope. This is a floating-point resolution diagnostic, not a truncation-error bound or evidence that a sub-resolution physical force is exactly zero.
    flux_converged : bool
        Whether the last relaxed flux step stagnated within tol [boolean] Shape scalar. Whether the last relaxed flux step stagnated within tol.
    equilibrium_compatible : bool
        Whether the resolved parallel-force compatibility gate passes [boolean] Shape scalar. Whether the resolved parallel-force compatibility gate passes.
    flux_fixed_point_residual : float
        Unrelaxed target-to-current-state L2 difference for psi; denominator=max(||psi_target||,||psi_state||,||psi_vac||), and the residual is zero when all three are zero Shape scalar. Nonnegative dimensionless diagnostic; binary floating-point scaling avoids norm overflow for finite states.
    field_fixed_point_residual : float
        Maximum of the relative L2 differences for BR and BZ; each component denominator=max(||B_target||,||B_state||,||B_vac||), and that component is zero when all three are zero Shape scalar. Nonnegative dimensionless diagnostic; binary floating-point scaling avoids norm overflow for finite states.
    current_fixed_point_residual : float
        Unrelaxed target L2 difference between the current relaxed cell current and the returned-state pressure current; denominator=max(||I_target||,||I_state||), and the residual is zero when both are zero Shape scalar. Nonnegative dimensionless diagnostic; binary floating-point scaling avoids norm overflow for finite states.

    Raises
    ------
    FloatingPointError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    TypeError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    solve_axisymmetric_anisotropic_picard : Run the no-wall Picard composition.

    Notes
    -----
    Recompute the deterministic pressure closure and toroidal current on the current psi, BR and BZ; integrate current with nodal trapezoidal weights or explicit cell boundaries, mix the old current by relax, and project the Green field. When paired field Green matrices are absent, derive the field from the newly added plasma flux. The wall branch adds both wall flux and its discrete magnetic-field derivative. Before stopping, construct the unrelaxed target from the current pressure/current and require psi, BR, BZ and current all to close. The returned state recomputes the closure, current and parallel-force compatibility; maxiter=0 performs no update and does not claim convergence.

    axisymmetric gyrotropic-pressure Picard composition with caller-owned N4 pressure closure and optional linear ideal-conductor wall correction

    The pressure_closure callback returns scientifically justified nonnegative co-located pressure arrays and optional density/temperature arrays for each state, interpreting psi as R A_phi in Wb/rad.

    All flux and field Green matrices share the declared current basis and appropriate Wb/rad/A or T/A units.

    No supplied pressure-closure parameter is interpreted by the graph except inserting B0 when absent; the caller owns its physical model.

    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    pressure_closure is a deterministic scientific relation for a given {psi,B,params}; it does not modify input arrays or depend on the call count, and the graph re-evaluates it at stopping and at the terminal state. B>=minimum_field is required before every closure and current evaluation.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import solve_free_boundary_anisotropic_picard
    >>> r, z = np.meshgrid([0.2, 0.4, 0.6], [-0.1, 0.0, 0.1])
    >>> shape, size = r.shape, r.size
    >>> def closure(state):
    ...     p = np.full(shape, 2.0)
    ...     return {'p_parallel': p, 'p_perp': p, 'density': None, 'electron_temperature': None}
    >>> result = solve_free_boundary_anisotropic_picard(r_grid=r, z_grid=z, psi_vac=r**2/2, br_vac=np.zeros(shape), bz_vac=np.ones(shape), g_psi=np.zeros((size, size)), params={}, pressure_closure=closure, tol=1e-12, maxiter=1, relax=0.0)
    >>> np.testing.assert_allclose(result['psi'], r**2/2)
    >>> np.testing.assert_allclose(result['j_phi'], 0.0, atol=1e-12)
    >>> assert result['converged'] and result['iterations'] == 1 and result['failure_reason'] is None
    """

    from scirel._composition import compose
    from scirel.diagnostics.picard_flux_residual import (
        compute_picard_flux_residual as _dependency_0,
    )
    from scirel.equilibrium.anisotropic_picard_feedback import (
        update_anisotropic_picard_flux as _dependency_1,
    )
    from scirel.equilibrium.anisotropic_toroidal_current import (
        compute_anisotropic_toroidal_current as _dependency_2,
    )
    from scirel.field.ideal_conductor_boundary import (
        correct_ideal_conductor_boundary_flux as _dependency_3,
    )
    from scirel.field.poloidal_field_magnitude import (
        compute_poloidal_field_magnitude as _dependency_4,
    )

    return compose(
        _run_composition,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.diagnostics.picard_flux_residual": _dependency_0,
                "scirel.equilibrium.anisotropic_picard_feedback": _dependency_1,
                "scirel.equilibrium.anisotropic_toroidal_current": _dependency_2,
                "scirel.field.ideal_conductor_boundary": _dependency_3,
                "scirel.field.poloidal_field_magnitude": _dependency_4,
            }
        },
    )


__all__ = ["solve_free_boundary_anisotropic_picard"]
