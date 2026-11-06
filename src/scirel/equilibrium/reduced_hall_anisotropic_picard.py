"""Source-ordered reduced Hall magnetic feedback over emitted leaf assets."""

from __future__ import annotations
from scirel._validation import (
    finite_scalar as _require_finite_scalar,
    integer_scalar as _require_integer_scalar,
    bool_scalar as _require_bool_scalar,
)
import numpy as np


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


def _active_mask(mask_port, fixed_mask, b, psi):
    """Return the validated active-cell array for one closure evaluation."""
    if not callable(mask_port):
        return fixed_mask
    active = np.asarray(mask_port(b, psi))
    if active.shape != psi.shape or active.dtype != np.dtype(bool):
        raise ValueError(
            "callable plasma_mask must return a boolean array with the same shape as the R-Z grid"
        )
    return active


def _run_composition(inputs, *, asset_loader):
    """Iterate magnetic flux, caller-bound kinetic closure, and Hall current."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    required = {
        "r_grid",
        "z_grid",
        "psi_vac",
        "g_psi",
        "ion_mass_kg",
        "ion_charge_c",
        "pressure_closure",
    }
    missing = sorted((key for key in required if key not in inputs))
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    r_grid, z_grid, psi_vac = (
        np.asarray(inputs["r_grid"], dtype=float),
        np.asarray(inputs["z_grid"], dtype=float),
        np.asarray(inputs["psi_vac"], dtype=float),
    )
    if r_grid.shape != z_grid.shape or psi_vac.shape != r_grid.shape or r_grid.ndim != 2:
        raise ValueError("r_grid, z_grid, psi_vac must be equal-shape 2-D arrays")
    if not all((np.all(np.isfinite(value)) for value in (r_grid, z_grid, psi_vac))):
        raise ValueError("r_grid, z_grid, psi_vac must be finite")
    r, z = (r_grid[0], z_grid[:, 0])
    if (
        r.size < 3
        or z.size < 3
        or (not np.allclose(r_grid, r[np.newaxis, :]))
        or (not np.allclose(z_grid, z[:, np.newaxis]))
        or np.any(np.diff(r) <= 0.0)
        or np.any(np.diff(z) <= 0.0)
    ):
        raise ValueError("Hall Picard requires a strictly increasing rectilinear R-Z grid")
    g_psi = np.asarray(inputs["g_psi"], dtype=float)
    if g_psi.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(g_psi)):
        raise ValueError("g_psi must be finite with shape (grid_size, grid_size)")
    closure = inputs["pressure_closure"]
    if not callable(closure):
        raise TypeError("pressure_closure must be a callable returning a kinetic state mapping")
    tol = _require_finite_scalar(inputs.get("tol"), "tol", 1e-08)
    maxiter = _require_integer_scalar(inputs.get("maxiter"), "maxiter", 200, minimum=1)
    relax = _require_finite_scalar(inputs.get("relax"), "relax", 0.5)
    minimum_field = _require_finite_scalar(inputs.get("minimum_field"), "minimum_field", 1e-08)
    minimum_firehose = _require_finite_scalar(
        inputs.get("minimum_firehose_margin"), "minimum_firehose_margin", 0.0
    )
    ion_mass = _require_finite_scalar(inputs["ion_mass_kg"], "ion_mass_kg", None)
    ion_charge = _require_finite_scalar(inputs["ion_charge_c"], "ion_charge_c", None)
    hall_multiplier = _require_finite_scalar(inputs.get("hall_multiplier"), "hall_multiplier", 1.0)
    include_toroidal_inertia = _require_bool_scalar(
        inputs.get("include_toroidal_inertia"), "include_toroidal_inertia", True
    )
    hall_density_floor_fraction = _require_finite_scalar(
        inputs.get("hall_density_floor_fraction"), "hall_density_floor_fraction", 0.1
    )
    maximum_inertial_mach = _require_finite_scalar(
        inputs.get("maximum_inertial_mach"), "maximum_inertial_mach", 0.5
    )
    inertia_relax = _require_finite_scalar(inputs.get("inertia_relax"), "inertia_relax", 0.5)
    inertia_tolerance = _require_finite_scalar(
        inputs.get("inertia_tolerance"), "inertia_tolerance", 1e-10
    )
    inertia_max_iterations = _require_integer_scalar(
        inputs.get("inertia_max_iterations"), "inertia_max_iterations", 80, minimum=1
    )
    compatibility_tol = _require_finite_scalar(
        inputs.get("compatibility_tol"), "compatibility_tol", 0.05
    )
    ohm_tol = _require_finite_scalar(inputs.get("ohm_tolerance"), "ohm_tolerance", 0.05)
    strict = _require_bool_scalar(inputs.get("strict_compatibility"), "strict_compatibility", True)
    if (
        minimum_field <= 0.0
        or not 0.0 <= relax < 1.0
        or hall_multiplier < 0.0
        or (not 0.0 <= hall_density_floor_fraction < 1.0)
        or (maximum_inertial_mach <= 0.0)
        or (not 0.0 <= inertia_relax < 1.0)
        or (inertia_tolerance <= 0.0)
        or (compatibility_tol < 0.0)
        or (ohm_tol <= 0.0)
    ):
        raise ValueError("Hall Picard controls are invalid")
    mask_port = inputs.get("plasma_mask")
    if mask_port is None:
        fixed_mask = np.ones_like(r_grid, dtype=bool)
    elif callable(mask_port):
        fixed_mask = None
    else:
        fixed_mask = np.asarray(mask_port)
        if fixed_mask.shape != r_grid.shape or fixed_mask.dtype != np.dtype(bool):
            raise ValueError("plasma_mask must be a boolean array with the same shape as r_grid")
    field = asset_loader("scirel.field.poloidal_field_from_flux")
    drift = asset_loader("scirel.closures.reduced_hall_drift")
    flux_update = asset_loader("scirel.equilibrium.axisymmetric_picard_update")
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
            raise FloatingPointError("Hall equilibrium magnetic field vanished")
        state = closure(magnetic["B"], psi)
        if (
            not isinstance(state, dict)
            or "p_parallel" not in state
            or "p_perpendicular" not in state
        ):
            raise ValueError("pressure_closure must return p_parallel and p_perpendicular")
        p_parallel, p_perpendicular = _coerce_pressure(
            state["p_parallel"], state["p_perpendicular"], psi
        )
        if (
            not np.all(np.isfinite(p_parallel))
            or not np.all(np.isfinite(p_perpendicular))
            or np.any(p_parallel < 0.0)
            or np.any(p_perpendicular < 0.0)
        ):
            raise ValueError("pressure_closure returned invalid pressure")
        active = _active_mask(mask_port, fixed_mask, magnetic["B"], psi)
        hall = drift(
            r_grid,
            z_grid,
            magnetic["B_R"],
            magnetic["B_Z"],
            p_parallel,
            p_perpendicular,
            state,
            active,
            ion_mass,
            ion_charge,
            hall_multiplier=hall_multiplier,
            include_toroidal_inertia=include_toroidal_inertia,
            hall_density_floor_fraction=hall_density_floor_fraction,
            maximum_inertial_mach=maximum_inertial_mach,
            inertia_relax=inertia_relax,
            inertia_tolerance=inertia_tolerance,
            inertia_max_iterations=inertia_max_iterations,
        )
        update = flux_update(
            r_grid,
            z_grid,
            hall["J_phi"],
            psi,
            psi_vac,
            g_psi,
            relax,
            old_currents,
            cell_edges=inputs.get("cell_edges"),
        )
        next_psi = update["psi_next"]
        cell_currents = update["plasma_cell_currents"]
        relative_change = update["relative_psi_change"]
        current_change = update["relative_current_change"]
        history.append(
            {
                "iteration": iteration,
                "relative_psi_change": relative_change,
                "relative_current_change": current_change,
                "generalized_ohm_error": hall["generalized_ohm_error"],
            }
        )
        psi, old_currents = (next_psi, cell_currents)
        if update["fixed_point_residual"] <= tol:
            converged = True
            break
    magnetic = field(r_grid, z_grid, psi)
    if np.any(magnetic["B"] < minimum_field):
        raise FloatingPointError("Hall terminal magnetic field vanished")
    state = closure(magnetic["B"], psi)
    p_parallel, p_perpendicular = _coerce_pressure(
        state["p_parallel"], state["p_perpendicular"], psi
    )
    active = _active_mask(mask_port, fixed_mask, magnetic["B"], psi)
    hall = drift(
        r_grid,
        z_grid,
        magnetic["B_R"],
        magnetic["B_Z"],
        p_parallel,
        p_perpendicular,
        state,
        active,
        ion_mass,
        ion_charge,
        hall_multiplier=hall_multiplier,
        include_toroidal_inertia=include_toroidal_inertia,
        hall_density_floor_fraction=hall_density_floor_fraction,
        maximum_inertial_mach=maximum_inertial_mach,
        inertia_relax=inertia_relax,
        inertia_tolerance=inertia_tolerance,
        inertia_max_iterations=inertia_max_iterations,
    )
    final_update = flux_update(
        r_grid,
        z_grid,
        hall["J_phi"],
        psi,
        psi_vac,
        g_psi,
        relax,
        old_currents,
        cell_edges=inputs.get("cell_edges"),
    )
    cell_currents = final_update["plasma_cell_currents"]
    fixed_point_residual = final_update["fixed_point_residual"]
    converged = bool(fixed_point_residual <= tol)
    if minimum_firehose >= 0.0 and np.any(active & (hall["firehose_margin"] <= minimum_firehose)):
        raise FloatingPointError("Hall pressure closure crossed firehose/tension singularity")
    compatibility_tol = compatibility_tol
    messages = []
    if hall["parallel_force_error"] > compatibility_tol:
        messages.append(
            f"parallel momentum error {hall['parallel_force_error']:.3e} exceeds {compatibility_tol:.3e}"
        )
    if hall["generalized_ohm_error"] > ohm_tol:
        messages.append(
            f"generalized Ohm error {hall['generalized_ohm_error']:.3e} exceeds {ohm_tol:.3e}"
        )
    if messages and strict:
        raise ValueError("; ".join(messages))
    return {
        "psi": psi,
        "plasma_cell_currents": cell_currents,
        "J_phi": hall["J_phi"],
        "B_R": magnetic["B_R"],
        "B_Z": magnetic["B_Z"],
        "B": magnetic["B"],
        "p_parallel": p_parallel,
        "p_perpendicular": p_perpendicular,
        "parallel_force": hall["parallel_force"],
        "force_R": hall["force_R"],
        "force_Z": hall["force_Z"],
        "ion_toroidal_velocity": hall["ion_toroidal_velocity"],
        "electron_toroidal_velocity": hall["electron_toroidal_velocity"],
        "electric_field_R": hall["electric_field_R"],
        "electric_field_Z": hall["electric_field_Z"],
        "hall_state": hall,
        "converged": converged,
        "fixed_point_residual": fixed_point_residual,
        "iterations": iteration,
        "relative_psi_change": relative_change,
        "parallel_force_error": hall["parallel_force_error"],
        "generalized_ohm_error": hall["generalized_ohm_error"],
        "closure_state": state,
        "firehose_margin": hall["firehose_margin"],
        "compatibility_messages": messages,
        "iteration_history": history,
    }


def solve_reduced_hall_anisotropic_picard(inputs=None, **kwargs):
    """Run reduced-Hall magnetic feedback with a caller-owned pressure closure.

    Parameters
    ----------
    inputs : mapping, optional
        Composition input mapping. Its declared keys are listed under Other Parameters.
    kwargs : mapping, optional
        Additional composition inputs merged at the public boundary.

    Other Parameters
    ----------------
    r_grid : finite real array-like
        Cylindrical radius mesh [m] Shape [N_Z,N_R]. Same two-dimensional rectilinear shape as z_grid and psi_vac; strictly increasing radial axis, at least three columns. The bound field/Hall leaves additionally require nonnegative R.
    z_grid : finite real array-like
        Axial coordinate mesh [m] Shape [N_Z,N_R]. Strictly increasing rectilinear axial axis, at least three rows; same shape as r_grid and psi_vac.
    psi_vac : finite real array-like
        Vacuum psi=R A_phi and initial evolving state [Wb/rad] Shape [N_Z,N_R]. Same shape as the grid; copied before iteration. Full linked flux requires an explicit 2*pi conversion outside this graph.
    g_psi : finite real array-like
        Dense cell-current-to-psi Green response [Wb/rad/A] Shape [N_Z*N_R,N_Z*N_R]. Finite exact square shape, with the Picard leaf's C-order grid mapping and no embedded 2*pi or cell-area factor.
    pressure_closure : Python callable
        Caller-owned callable returning pressure and Hall species state for each B and psi=R A_phi [output pressure Pa; input B T and psi Wb/rad] Shape callable(B,psi) -> mapping. Must interpret psi in Wb/rad and return p_parallel and p_perpendicular, scalar or exact-grid nonnegative finite Pa values, plus required Hall leaf keys ion_density (m^-3), electron_pressure (Pa) and electrostatic_potential (V); optional species pressures follow the Hall leaf contract.
    ion_mass_kg : finite real scalar
        Positive ion mass passed to the Hall leaf [kg] Shape scalar. Strictly positive in the bound Hall leaf.
    ion_charge_c : finite real scalar
        Positive ion charge magnitude passed to the Hall leaf [C] Shape scalar. Strictly positive in the bound Hall leaf.
    tol : finite real scalar
        Outer relative flux-change stopping threshold Shape scalar. The graph checks finiteness but not positivity; choose a positive value for the intended stopping criterion.
    maxiter : integer scalar
        Maximum outer Picard updates [count] Shape scalar. Integer >= 1; no automatic retry beyond this bound.
    relax : finite real scalar
        Previous-flux retention weight in the Green step Shape scalar. 0 <= value < 1; applied to flux, not raw cell currents.
    minimum_field : finite real scalar
        Minimum acceptable poloidal field magnitude during outer updates [T] Shape scalar. Strictly positive; each iteration and the terminal reevaluation check B before invoking the pressure closure.
    minimum_firehose_margin : finite real scalar
        Terminal active-cell firehose/tension threshold Shape scalar. If nonnegative, terminal active cells with margin <= this threshold cause FloatingPointError; a negative value disables this check.
    plasma_mask : boolean array, callable returning boolean array, or None
        Fixed active cells or caller policy evaluated at each B,psi [boolean] Shape [N_Z,N_R], callable(B,psi)->[N_Z,N_R], or null. Null selects all cells; fixed arrays must have exact grid shape and bool dtype; callable results must have exact grid shape and bool dtype. Integer/float arrays are not silently converted. Hall drift further excludes axis, low-density and unresolved-field cells.
    hall_multiplier : finite real scalar
        Multiplier passed to the reduced Hall leaf Shape scalar. Nonnegative.
    include_toroidal_inertia : bool
        Enable the Hall leaf's local toroidal-inertia correction [boolean] Shape scalar. Actual boolean scalar, not numeric 0/1.
    hall_density_floor_fraction : finite real scalar
        Peak active-density fraction defining Hall drift support Shape scalar. 0 <= value < 1.
    maximum_inertial_mach : finite real scalar
        Local ion-drift Mach cap Shape scalar. Strictly positive.
    inertia_relax : finite real scalar
        Previous-current weight inside the Hall leaf's local iteration Shape scalar. 0 <= value < 1.
    inertia_tolerance : finite real scalar
        Local inertia current-change tolerance Shape scalar. Strictly positive.
    inertia_max_iterations : integer scalar
        Local inertia iteration bound per Hall call [count] Shape scalar. Integer >= 1; local nonconvergence raises rather than returning the outer graph state.
    compatibility_tol : finite real scalar
        Terminal parallel-momentum error threshold Shape scalar. Nonnegative; exceedance adds a message and raises only if strict_compatibility is true.
    ohm_tolerance : finite real scalar
        Terminal normalized generalized-Ohm error threshold Shape scalar. Strictly positive; exceedance adds a message and raises only if strict_compatibility is true.
    strict_compatibility : bool
        Reject terminal compatibility exceedance instead of returning messages [boolean] Shape scalar. Actual boolean scalar, not numeric 0/1; does not disable the separate firehose check.
    cell_edges : pair of finite arrays or None
        Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current [m] Shape (N_R+1, N_Z+1) arrays or None. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Returns
    -------
    psi : float64
        Last psi=R A_phi state after one or more bounded Picard updates [Wb/rad] Shape [N_Z,N_R]. Terminal field, closure and Hall state are recomputed at this psi.
    plasma_cell_currents : float64
        Terminal or step current density integrated with the explicitly declared node/cell-domain weights [A] Shape [N_Z,N_R]. Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.
    J_phi : float64
        Terminal reduced-Hall toroidal current density [A/m^2] Shape [N_Z,N_R]. Hall leaf zeros cells outside plasma_mask.
    B_R : float64
        Terminal radial poloidal magnetic field [T] Shape [N_Z,N_R]. Derived from returned psi.
    B_Z : float64
        Terminal axial poloidal magnetic field [T] Shape [N_Z,N_R]. Derived from returned psi.
    B : float64
        Terminal poloidal-field magnitude [T] Shape [N_Z,N_R]. Terminal field is checked against minimum_field before the terminal closure/Hall reevaluation.
    p_parallel : float64
        Terminal caller-closure parallel pressure after scalar broadcast [Pa] Shape [N_Z,N_R]. Grid-shaped and checked finite by the Hall leaf; the graph-level nonnegative pressure gate is not repeated at terminal evaluation.
    p_perpendicular : float64
        Terminal caller-closure perpendicular pressure after scalar broadcast [Pa] Shape [N_Z,N_R]. Grid-shaped and checked finite by the Hall leaf; the graph-level nonnegative pressure gate is not repeated at terminal evaluation.
    parallel_force : float64
        Terminal Hall target force projected along the field [Pa/m] Shape [N_Z,N_R]. Diagnostic from hall_state.
    force_R : float64
        Terminal radial target force including any centrifugal correction [Pa/m] Shape [N_Z,N_R]. From hall_state, not necessarily the uncorrected pressure force.
    force_Z : float64
        Terminal axial target force [Pa/m] Shape [N_Z,N_R]. From hall_state.
    ion_toroidal_velocity : float64
        Terminal Hall ion toroidal drift [m/s] Shape [N_Z,N_R]. Zero outside Hall-active cells.
    electron_toroidal_velocity : float64
        Terminal Hall electron toroidal drift [m/s] Shape [N_Z,N_R]. Zero outside Hall-active cells.
    electric_field_R : float64
        Terminal radial electrostatic field from the Hall leaf [V/m] Shape [N_Z,N_R]. Negative radial gradient of caller potential.
    electric_field_Z : float64
        Terminal axial electrostatic field from the Hall leaf [V/m] Shape [N_Z,N_R]. Negative axial gradient of caller potential.
    hall_state : Python mapping
        Complete terminal reduced-Hall Operator result including local masks and diagnostics [mixed SI] Shape mapping. Not a separate published asset; follows the bound Hall leaf's output contract.
    converged : bool
        True only when the terminal unrelaxed fixed-point residual passes tol (and free-boundary force compatibility passes) [boolean] Shape scalar. Relaxed stagnation alone does not establish convergence.
    iterations : integer
        Executed outer Picard update count [count] Shape scalar. Between one and maxiter inclusive.
    relative_psi_change : float
        Last outer update's relative flux change Shape scalar. Uses the bound Picard leaf's norm convention.
    parallel_force_error : float
        Terminal Hall parallel-force error fraction Shape scalar. Compared to compatibility_tol for optional strict rejection.
    generalized_ohm_error : float
        Terminal normalized generalized-Ohm residual Shape scalar. Compared to ohm_tolerance for optional strict rejection.
    closure_state : Python mapping
        Unmodified mapping returned by the terminal caller closure [mixed SI] Shape mapping. Primary scalar pressures may remain scalar here even though p_parallel and p_perpendicular output fields were broadcast.
    firehose_margin : float64
        Terminal Hall firehose/tension margin Shape [N_Z,N_R]. Checked on terminal active cells only when minimum_firehose_margin >= 0.
    compatibility_messages : Python list of strings
        Messages for parallel-momentum or generalized-Ohm threshold exceedance [text] Shape list[string]. Can be nonempty on a successful result only when strict_compatibility is false.
    iteration_history : Python list of mappings
        Per-update flux/current changes and generalized-Ohm error [mixed dimensionless diagnostics] Shape [iterations] list[mapping]. Each item has iteration, relative_psi_change, relative_current_change and generalized_ohm_error.
    fixed_point_residual : float
        Unrelaxed flux-map residual recomputed at the returned terminal closure/current state; convergence requires <=tol Shape scalar. Unrelaxed flux-map residual recomputed at the returned terminal closure/current state; convergence requires <=tol.

    Raises
    ------
    FloatingPointError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    RuntimeError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    TypeError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    solve_kinetic_mirror_hall_equilibrium : Nest kinetic closure with Hall feedback.

    Notes
    -----
    Starting from a copy of psi_vac and zero prior cell currents, each outer step derives B from the current psi, checks the step field floor, calls pressure_closure(B,psi), validates and broadcasts the primary pressures, selects active cells, computes reduced-Hall J_phi and drifts, then applies a flux-relaxed Green update. The outer loop stops at relative_psi_change <= tol or maxiter. On the returned psi it derives the field, checks the terminal field floor before invoking the terminal closure, repeats closure, pressure shape coercion, Hall and cell-current evaluation, then applies active-cell firehose and optional strict parallel-force/generalized-Ohm compatibility checks. The terminal path still does not repeat the graph-level pressure nonnegativity gate; the Hall leaf checks pressure finiteness and its optional ion-pressure state. The Hall Operator may run its own bounded local inertia iteration inside each evaluation.

    axisymmetric reduced Hall and gyrotropic-pressure Picard feedback with caller-bound closure

    The caller pressure_closure(B,psi) interprets psi=R A_phi in Wb/rad and supplies a physically compatible state, including ion_density, electron_pressure and electrostatic_potential needed by the Hall leaf.

    The dense Green matrix maps cell currents in A to psi=R A_phi in Wb/rad on the same grid; no 2*pi conversion occurs inside the graph.

    A pressure closure, mask callable and control values must remain meaningful on each iterated and terminal state; this graph does not independently certify their physical model.

    Convergence is a global fixed-point statement for the declared composition
    and its terminal compatibility checks; it is not a proof of a global
    equilibrium or of physical identifiability.

    Default composite-trapezoid weights integrate exactly over the supplied node-domain rectangle; boundary nodes have half-interval weights. Explicit cell_edges=(radial_edges,axial_edges), each with center_count+1 monotone finite entries enclosing its centers, instead define cell-center areas. No 2*pi*R factor multiplies toroidal filament current.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import solve_reduced_hall_anisotropic_picard
    >>> r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.2, 0.2, 5))
    >>> psi_vac = r_grid**2
    >>> def pressure_closure(_b, psi):
    ...     zeros = np.zeros_like(psi)
    ...     return {'p_parallel': 0.0, 'p_perpendicular': 0.0, 'ion_density': np.full_like(psi, 1e18), 'electron_pressure': zeros, 'electrostatic_potential': zeros}
    >>> result = solve_reduced_hall_anisotropic_picard(r_grid=r_grid, z_grid=z_grid, psi_vac=psi_vac, g_psi=np.zeros((25,25)), ion_mass_kg=1.67262192595e-27, ion_charge_c=1.602176634e-19, pressure_closure=pressure_closure, maxiter=2)
    >>> np.testing.assert_allclose(result['psi'], psi_vac)
    >>> np.testing.assert_allclose(result['J_phi'], 0.0)
    >>> assert result['converged'] and result['iterations'] == 1
    """

    from scirel._composition import compose
    from scirel.closures.reduced_hall_drift import close_reduced_hall_drift as _dependency_0
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
                "scirel.closures.reduced_hall_drift": _dependency_0,
                "scirel.equilibrium.axisymmetric_picard_update": _dependency_1,
                "scirel.field.poloidal_field_from_flux": _dependency_2,
            }
        },
    )


__all__ = ["solve_reduced_hall_anisotropic_picard"]
