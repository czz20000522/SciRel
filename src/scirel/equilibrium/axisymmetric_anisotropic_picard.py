"""Standalone orchestration of the current SciRel anisotropic Picard solver."""

from __future__ import annotations

from scirel._validation import (
    finite_scalar as _require_finite_scalar,
    integer_scalar as _require_integer_scalar,
    bool_scalar as _require_bool_scalar,
)
from collections.abc import Mapping
import numpy as np
from ._anisotropic_numerics import cell_areas


def _require_boolean_mask(value, shape, name="plasma_mask"):
    """Require an exact-shape boolean mask; never coerce ints/floats/0-1 values."""
    mask = np.asarray(value)
    if mask.dtype.kind != "b":
        raise ValueError(
            f"{name} must be a boolean array; integer/float/0-1 coercion is not accepted"
        )
    if mask.shape != shape:
        raise ValueError(f"{name} must match the R-Z grid shape {shape}")
    return mask


def _coerce_pressure(parallel, perpendicular, psi):
    """Broadcast scalar Pa values or validate the caller-owned grid shape."""
    result = []
    for value in (parallel, perpendicular):
        values = np.asarray(value, dtype=float)
        if values.ndim == 0:
            values = np.broadcast_to(values, psi.shape)
        elif values.shape != psi.shape:
            raise ValueError("pressure fields must be scalar or match psi shape")
        result.append(values)
    return tuple(result)


def _apply_active_mask(values, active):
    """Apply the caller-owned active-cell selector without changing the field formula."""
    result = np.array(values, copy=True)
    result[~active] = 0.0
    return result


def _require_state(closure, magnetic, psi):
    state = closure(magnetic["B"], psi)
    if not isinstance(state, Mapping):
        raise TypeError("pressure_closure must return a mapping")
    try:
        parallel, perpendicular = _coerce_pressure(
            state["p_parallel"], state["p_perpendicular"], psi
        )
    except KeyError as exc:
        raise KeyError("pressure_closure must return p_parallel and p_perpendicular") from exc
    if (
        not np.all(np.isfinite(parallel))
        or not np.all(np.isfinite(perpendicular))
        or np.any(parallel < 0.0)
        or np.any(perpendicular < 0.0)
    ):
        raise ValueError("pressure_closure returned invalid pressure")
    result = dict(state)
    result["p_parallel"], result["p_perpendicular"] = (parallel, perpendicular)
    return result


def _run_composition(inputs, *, asset_loader):
    """Run current-declared-order field -> closure -> div(P) -> flux feedback."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    required = {"r_grid", "z_grid", "psi_vac", "g_psi", "pressure_closure"}
    missing = sorted((key for key in required if key not in inputs))
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    closure = inputs["pressure_closure"]
    if not callable(closure):
        raise TypeError("pressure_closure must be callable as pressure_closure(B, psi)")
    r_grid, z_grid, psi_vac = (
        np.asarray(inputs[key], dtype=float) for key in ("r_grid", "z_grid", "psi_vac")
    )
    if r_grid.shape != z_grid.shape or psi_vac.shape != r_grid.shape or r_grid.ndim != 2:
        raise ValueError("r_grid, z_grid, psi_vac must be equal-shape 2-D arrays")
    r, z = (r_grid[0, :], z_grid[:, 0])
    if (
        r.size < 3
        or z.size < 3
        or (not np.allclose(r_grid, r[np.newaxis, :]))
        or (not np.allclose(z_grid, z[:, np.newaxis]))
        or (r[0] < 0.0)
        or np.any(np.diff(r) <= 0.0)
        or np.any(np.diff(z) <= 0.0)
    ):
        raise ValueError(
            "a strictly increasing rectilinear R-Z grid with at least 3 points per axis is required"
        )
    g_psi = np.asarray(inputs["g_psi"], dtype=float)
    if g_psi.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(g_psi)):
        raise ValueError("g_psi must be finite with shape (grid_size, grid_size)")
    tol = _require_finite_scalar(inputs.get("tol"), "tol", 1e-08)
    maxiter = _require_integer_scalar(inputs.get("maxiter"), "maxiter", 200, minimum=1)
    relax = _require_finite_scalar(inputs.get("relax"), "relax", 0.5)
    minimum_field = _require_finite_scalar(inputs.get("minimum_field"), "minimum_field", 1e-08)
    minimum_firehose = _require_finite_scalar(
        inputs.get("minimum_firehose_margin"), "minimum_firehose_margin", 0.0
    )
    compatibility_tol = _require_finite_scalar(
        inputs.get("compatibility_tol"), "compatibility_tol", 0.05
    )
    strict = _require_bool_scalar(inputs.get("strict_compatibility"), "strict_compatibility", True)
    if (
        not np.isfinite(tol)
        or not np.isfinite(relax)
        or (not np.isfinite(minimum_field))
        or (not np.isfinite(minimum_firehose))
        or (not np.isfinite(compatibility_tol))
        or (tol <= 0.0)
        or (maxiter < 1)
        or (not 0.0 <= relax < 1.0)
        or (minimum_field <= 0.0)
        or (compatibility_tol < 0.0)
    ):
        raise ValueError("Picard controls are invalid")
    mask_port = inputs.get("plasma_mask")
    if mask_port is None:
        fixed_mask = np.ones_like(psi_vac, dtype=bool)
    elif callable(mask_port):
        fixed_mask = None
    else:
        fixed_mask = _require_boolean_mask(mask_port, psi_vac.shape)
    field = asset_loader("scirel.field.poloidal_field_from_flux")
    force = asset_loader("scirel.equilibrium.anisotropic_force_balance")
    update = asset_loader("scirel.equilibrium.axisymmetric_picard_update")
    psi, old_currents, relative_change, converged = (
        np.array(psi_vac, copy=True),
        np.zeros_like(psi_vac),
        np.inf,
        False,
    )
    history = []
    for iteration in range(maxiter):
        iteration += 1
        magnetic = field(r_grid, z_grid, psi)
        if np.any(magnetic["B"] < minimum_field):
            raise FloatingPointError(
                "magnetic field fell below minimum_field; the gyrotropic closure is singular"
            )
        state = _require_state(closure, magnetic, psi)
        active = (
            _require_boolean_mask(mask_port(magnetic["B"], psi), psi.shape)
            if callable(mask_port)
            else fixed_mask
        )
        force_state = force(
            r_grid,
            z_grid,
            magnetic["B_R"],
            magnetic["B_Z"],
            state["p_parallel"],
            state["p_perpendicular"],
            active,
        )
        j_phi = _apply_active_mask(force_state["J_phi"], active)
        step = update(
            r_grid,
            z_grid,
            j_phi,
            psi,
            psi_vac,
            g_psi,
            relax,
            old_currents,
            cell_edges=inputs.get("cell_edges"),
        )
        relative_change = step["relative_psi_change"]
        history.append(
            {
                "iteration": iteration,
                "relative_psi_change": relative_change,
                "relative_current_change": step["relative_current_change"],
            }
        )
        psi, old_currents = (step["psi_next"], step["plasma_cell_currents"])
        if step["fixed_point_residual"] <= tol:
            converged = True
            break
    magnetic = field(r_grid, z_grid, psi)
    if np.any(magnetic["B"] < minimum_field):
        raise FloatingPointError(
            "magnetic field fell below minimum_field at the returned terminal state"
        )
    state = _require_state(closure, magnetic, psi)
    active = (
        _require_boolean_mask(mask_port(magnetic["B"], psi), psi.shape)
        if callable(mask_port)
        else fixed_mask
    )
    force_state = force(
        r_grid,
        z_grid,
        magnetic["B_R"],
        magnetic["B_Z"],
        state["p_parallel"],
        state["p_perpendicular"],
        active,
    )
    j_phi = _apply_active_mask(force_state["J_phi"], active)
    terminal_cell_currents = j_phi * cell_areas(r_grid, z_grid, inputs.get("cell_edges"))
    terminal_update = update(
        r_grid,
        z_grid,
        j_phi,
        psi,
        psi_vac,
        g_psi,
        0.0,
        old_currents,
        cell_edges=inputs.get("cell_edges"),
    )
    fixed_point_residual = terminal_update["fixed_point_residual"]
    converged = bool(fixed_point_residual <= tol)
    if np.any(active & (force_state["firehose_margin"] <= minimum_firehose)):
        raise FloatingPointError("pressure closure crossed the firehose/tension singularity")
    if force_state["parallel_force_error"] > compatibility_tol and strict:
        raise ValueError(
            f"p_parallel and p_perpendicular leave an unbalanced parallel div(P) fraction of {force_state['parallel_force_error']:.3e}; required <= {compatibility_tol:.3e}"
        )
    return {
        "psi": psi,
        "plasma_cell_currents": terminal_cell_currents,
        "J_phi": j_phi,
        "B_R": magnetic["B_R"],
        "B_Z": magnetic["B_Z"],
        "B": magnetic["B"],
        "p_parallel": state["p_parallel"],
        "p_perpendicular": state["p_perpendicular"],
        "parallel_force": force_state["parallel_force"],
        "force_R": force_state["force_R"],
        "force_Z": force_state["force_Z"],
        "converged": converged,
        "fixed_point_residual": fixed_point_residual,
        "iterations": iteration,
        "relative_psi_change": relative_change,
        "parallel_force_error": force_state["parallel_force_error"],
        "force_diagnostics": force_state,
        "closure_state": state,
        "firehose_margin": force_state["firehose_margin"],
        "iteration_history": history,
    }


def solve_axisymmetric_anisotropic_picard(inputs=None, **kwargs):
    """Run the axisymmetric anisotropic Picard field/pressure feedback loop.

    Parameters
    ----------
    inputs : mapping, optional
        Composition input mapping. Its declared keys are listed under Other Parameters.
    kwargs : mapping, optional
        Additional composition inputs merged at the public boundary.

    Other Parameters
    ----------------
    r_grid : finite real array-like
        Cylindrical radius mesh [m] Shape [N_Z,N_R]. Nonnegative rectilinear R, strictly increasing radial axis and at least three columns; same shape as z_grid and psi_vac.
    z_grid : finite real array-like
        Axial coordinate mesh [m] Shape [N_Z,N_R]. Rectilinear Z with strictly increasing axial axis and at least three rows; same shape as r_grid and psi_vac.
    psi_vac : real array-like
        Vacuum or externally supplied initial psi=R A_phi [Wb/rad] Shape [N_Z,N_R]. Same shape as grid; the graph copies it and the field Operator validates its finite values.
    g_psi : finite real array-like
        Dense cell-current-to-field-psi Green matrix [Wb/rad/A] Shape [N_Z*N_R,N_Z*N_R]. Rows/columns follow [Z,R] C order; exact square shape and finite values.
    pressure_closure : Python callable
        Caller pressure relation evaluated against each current field and psi=R A_phi [output pressure Pa; input B T and psi Wb/rad] Shape callable(B,psi) -> mapping. Returns nonnegative finite p_parallel and p_perpendicular as scalars or exact grid arrays; other mapping keys are retained in closure_state.
    tol : finite real scalar
        Unrelaxed flux-map residual threshold for step stopping and terminal convergence Shape scalar. Strictly positive; relative_psi_change does not determine convergence.
    maxiter : integer scalar, not bool
        Maximum number of Picard updates [iteration] Shape scalar. At least one update; nonconvergence returns the last state with converged=false.
    relax : finite real scalar
        Previous-flux retention weight passed to the Green update Shape scalar. 0 <= relax < 1; this is flux rather than current relaxation.
    plasma_mask : boolean array-like, callable or None
        Fixed active-cell boolean array or dynamic callable evaluated from each B,psi state [boolean] Shape [N_Z,N_R], callable(B,psi)->[N_Z,N_R], or null. When omitted, all cells are active. A fixed mask must be a boolean array and a callable must return a boolean array of the same shape; integer, float and 0/1 coercions are rejected. False cells have J_phi set to zero before Green feedback.
    minimum_field : finite real scalar
        Required lower bound on the current and returned field magnitude [T] Shape scalar. Strictly positive; field values below it raise FloatingPointError before pressure_closure runs.
    minimum_firehose_margin : finite real scalar
        Lower bound on active-cell firehose/tension margin at the terminal state Shape scalar. Active-cell margins at or below this value raise FloatingPointError at terminal evaluation.
    compatibility_tol : finite real scalar
        Upper bound on the terminal active-domain parallel-force error when strict checking is enabled Shape scalar. Nonnegative.
    strict_compatibility : bool, not 0/1
        Whether terminal parallel-force incompatibility is rejected [boolean] Shape scalar. When false, return the error diagnostic without applying the compatibility_tol failure gate.
    cell_edges : pair of finite arrays or None
        Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current [m] Shape (N_R+1, N_Z+1) arrays or None. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Returns
    -------
    psi : float64
        Last psi=R A_phi state after one or more bounded Picard updates [Wb/rad] Shape [N_Z,N_R]. The terminal field, closure and force outputs are recomputed on this same state.
    plasma_cell_currents : float64
        Terminal or step current density integrated with the explicitly declared node/cell-domain weights [A] Shape [N_Z,N_R]. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.
    J_phi : float64
        Terminal active-cell toroidal current density [A/m^2] Shape [N_Z,N_R]. Zeroed outside the terminal active mask.
    B_R : float64
        Terminal radial poloidal field [T] Shape [N_Z,N_R]. Derived from returned psi by the bound field Operator.
    B_Z : float64
        Terminal axial poloidal field [T] Shape [N_Z,N_R]. Derived from returned psi by the bound field Operator.
    B : float64
        Terminal poloidal field magnitude [T] Shape [N_Z,N_R]. Minimum-field gate is rechecked after terminal recomputation.
    p_parallel : float64
        Terminal closure parallel pressure after scalar broadcast or grid validation [Pa] Shape [N_Z,N_R]. Finite and nonnegative.
    p_perpendicular : float64
        Terminal closure perpendicular pressure after scalar broadcast or grid validation [Pa] Shape [N_Z,N_R]. Finite and nonnegative.
    parallel_force : float64
        Terminal pressure force projected along the field [Pa/m] Shape [N_Z,N_R]. Diagnostic; not used to rewrite psi.
    force_R : float64
        Terminal cylindrical pressure-force radial component [Pa/m] Shape [N_Z,N_R]. From the bound anisotropic force Operator.
    force_Z : float64
        Terminal cylindrical pressure-force axial component [Pa/m] Shape [N_Z,N_R]. From the bound anisotropic force Operator.
    converged : bool
        True exactly when the terminal unrelaxed flux-map fixed_point_residual <=tol after the declared terminal gates [boolean] Shape scalar. Relaxed stagnation alone does not establish convergence.
    iterations : integer
        Number of executed Picard updates [iteration] Shape scalar. Between one and maxiter inclusive.
    relative_psi_change : float
        Last step's relative flux change Shape scalar. Uses the Picard update Operator's norm convention.
    parallel_force_error : float
        Terminal active-domain RMS parallel-force fraction Shape scalar. Compatibility gate uses this value only when strict_compatibility is true.
    closure_state : Python mapping
        Final caller closure mapping with normalized pressure fields [mixed] Shape mapping. Additional caller fields are retained; p_parallel and p_perpendicular are grid arrays.
    firehose_margin : float64
        Terminal gyrotropic firehose/tension margin Shape [N_Z,N_R]. Checked only on terminal active cells against minimum_firehose_margin.
    iteration_history : Python list of mappings
        One mapping of relative psi/current changes for each executed step [mixed dimensionless diagnostics] Shape [iterations] list[mapping]. Each item contains iteration, relative_psi_change and relative_current_change.
    fixed_point_residual : float
        Unrelaxed flux-map residual recomputed at the returned terminal closure/current state; convergence requires <=tol Shape scalar. Unrelaxed flux-map residual recomputed at the returned terminal closure/current state; convergence requires <=tol.
    force_diagnostics : dict
        Complete terminal force result including raw residual and floating-point envelope [mixed SI] Shape mapping. Complete terminal force result including raw residual and floating-point envelope.

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
    solve_reduced_hall_anisotropic_picard : Add reduced-Hall feedback.
    solve_free_boundary_anisotropic_picard : Add the free-boundary wall response.

    Notes
    -----
    Starting at a copy of psi_vac, derive B_R/B_Z/B from psi, gate the iteration field, call pressure_closure(B,psi), broadcast scalar pressures or require exact grid shapes, evaluate cylindrical div(P), mask inactive J_phi, and apply a flux-relaxed Green update. Stop when the step's unrelaxed fixed_point_residual reaches tol or maxiter is exhausted; the relaxed relative_psi_change is diagnostic; then rederive the terminal field, call the closure and force, recompute masked cell currents, and check minimum field, firehose and parallel-force compatibility in that order.

    bounded axisymmetric gyrotropic pressure Picard composition with externally supplied pressure closure

    pressure_closure is a caller-owned scientific callable that interprets each current psi=R A_phi in Wb/rad and returns physically meaningful p_parallel and p_perpendicular in Pa.

    g_psi maps cell currents in A to psi=R A_phi in Wb/rad in the declared order; no 2*pi conversion occurs inside the graph.

    The graph's plasma_mask=True cells are active; inactive current is zeroed before feedback, while the force Operator itself uses the mask only for its error metric.

    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import solve_axisymmetric_anisotropic_picard
    >>> r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.6, 5), np.linspace(-0.2, 0.2, 5))
    >>> pressure = 3.0 + r_grid
    >>> result = solve_axisymmetric_anisotropic_picard(r_grid=r_grid, z_grid=z_grid, psi_vac=r_grid**2, g_psi=np.zeros((25,25)), pressure_closure=lambda _b,_psi: {'p_parallel': pressure, 'p_perpendicular': pressure}, maxiter=1, tol=1e-12, relax=0.0)
    >>> np.testing.assert_allclose(result['psi'], r_grid**2)
    >>> np.testing.assert_allclose(result['J_phi'], 0.5, rtol=2e-13, atol=2e-13)
    >>> assert result['converged'] and result['iterations'] == 1
    """
    from scirel._composition import compose
    from scirel.equilibrium.anisotropic_force_balance import (
        compute_anisotropic_force_balance as _dependency_0,
    )
    from scirel.equilibrium.axisymmetric_picard_update import (
        update_axisymmetric_picard_flux as _dependency_1,
    )
    from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as _dependency_2

    return compose(
        _run_composition,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.equilibrium.anisotropic_force_balance": _dependency_0,
                "scirel.equilibrium.axisymmetric_picard_update": _dependency_1,
                "scirel.field.poloidal_field_from_flux": _dependency_2,
            }
        },
    )


__all__ = ["solve_axisymmetric_anisotropic_picard"]
