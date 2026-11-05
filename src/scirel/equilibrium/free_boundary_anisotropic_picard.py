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
        Mapping containing the rectilinear ``r_grid``/``z_grid``, vacuum
        ``psi_vac``/``br_vac``/``bz_vac``, dense ``g_psi``, caller ``params``
        and ``pressure_closure`` port, plus ``tol``, ``maxiter`` and
        ``relax``.  Optional inputs provide paired ``g_br``/``g_bz``,
        ``plasma_mask``, wall ``boundary_correction``, explicit ``cell_edges``
        and compatibility/field-floor controls.
    **kwargs
        Composition overrides passed to the public composition boundary.

    Returns
    -------
    dict
        Terminal ``psi``, ``BR``, ``BZ`` and ``B`` fields, pressure-closure
        profiles, toroidal and cell-integrated currents, force diagnostics,
        full fixed-point residual components, iteration history and explicit
        convergence/compatibility/failure fields.  Bounded nonconvergence
        returns the last complete state with ``converged=False``.

    Raises
    ------
    ValueError
        If grids, ports, closure fields, controls, masks or wall configuration
        violate the declared contract, or strict parallel-force compatibility
        fails.
    FloatingPointError
        If an intermediate or terminal field falls below ``minimum_field``.
    Exception
        Caller closure and dependency exceptions propagate unchanged.

    Notes
    -----
    The stopping test uses the unrelaxed terminal flux, field and current
    state, not only the relaxed flux increment.  ``maxiter=0`` returns a
    nonconverged terminal evaluation.  The composition owns iteration and state
    composition; it does not certify the physical wall model or a global
    equilibrium.
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
