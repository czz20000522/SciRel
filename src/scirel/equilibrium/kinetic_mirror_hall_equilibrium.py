"""Composition boundary joining a kinetic mirror closure to Hall feedback."""

from __future__ import annotations

__all__ = ["solve_kinetic_mirror_hall_equilibrium"]


def _run_composition(inputs, *, composition_loader):
    """Bind each Hall field iterate into the nested kinetic composition."""
    if not isinstance(inputs, dict) or not isinstance(inputs.get("kinetic_config"), dict):
        raise ValueError("inputs.kinetic_config must be a mapping")
    required = ("r_grid", "z_grid", "psi_vac", "g_psi", "ion_mass_kg", "ion_charge_c")
    missing = [name for name in required if name not in inputs]
    if missing:
        raise ValueError(f"{missing[0]} is required")
    kinetic = composition_loader("scirel.mirror.compositions.grid_mirror_kinetic_closure")
    hall = composition_loader("scirel.equilibrium.compositions.reduced_hall_anisotropic_picard")
    kinetic_config = dict(inputs["kinetic_config"])

    def pressure_closure(B, psi):
        return kinetic(
            {
                **kinetic_config,
                "r_grid": inputs["r_grid"],
                "z_grid": inputs["z_grid"],
                "b_t": B,
                "psi": psi,
            }
        )

    hall_inputs = {key: value for key, value in inputs.items() if key != "kinetic_config"}
    hall_inputs["pressure_closure"] = pressure_closure
    return hall(hall_inputs)


def solve_kinetic_mirror_hall_equilibrium(
    inputs=None, *, kinetic_composition=None, hall_composition=None, **kwargs
):
    """Run the nested kinetic and Hall compositions with explicit dependency ports.

    Parameters
    ----------
    inputs : mapping, optional
        Composition input mapping. Its declared keys are listed under Other Parameters.
    kinetic_composition : Python callable or None
        Optional explicit substitute for the bound kinetic TaskGraph [callable] Shape callable(mapping)->mapping or null. Dependency-injection hook, selected by Python truthiness; an override changes the scientific composition and is not the canonical asset.
    hall_composition : Python callable or None
        Optional explicit substitute for the bound Hall TaskGraph [callable] Shape callable(mapping)->mapping or null. Dependency-injection hook, selected by Python truthiness; an override changes the returned mapping and is not the canonical asset.
    kwargs : mapping, optional
        Additional composition inputs merged at the public boundary.

    Other Parameters
    ----------------
    r_grid : finite real array-like
        Cylindrical radius grid passed to both child graphs [m] Shape [N_Z,N_R]. Rectilinear, nonnegative R axis, strictly increasing with at least three columns; same shape as z_grid and psi_vac.
    z_grid : finite real array-like
        Axial grid passed to both child graphs [m] Shape [N_Z,N_R]. Rectilinear, strictly increasing Z axis with at least three rows; same shape as r_grid and psi_vac.
    psi_vac : finite real array-like
        Vacuum psi=R A_phi and initial Hall Picard state [Wb/rad] Shape [N_Z,N_R]. Same grid shape; copied by the Hall graph and passed unconverted as the kinetic flux-profile coordinate.
    g_psi : finite real array-like
        Dense cell-current-to-psi response for the Hall graph [Wb/rad/A] Shape [N_Z*N_R,N_Z*N_R]. Exact finite square shape and Hall Picard C-order cell-current mapping, with no embedded 2*pi or cell-area factor.
    ion_mass_kg : finite real scalar
        Ion mass passed to Hall drift [kg] Shape scalar. Strictly positive in the Hall leaf; independently provide the corresponding kinetic_config.mass_kg.
    ion_charge_c : finite real scalar
        Positive ion charge passed to Hall drift [C] Shape scalar. Strictly positive in the Hall leaf; independently provide the corresponding kinetic_config.charge_c.
    kinetic_config : Python dict
        Fixed inputs for each evaluation of the nested grid mirror kinetic closure [mixed SI; psi-dependent profiles use Wb/rad] Shape mapping. Must be a dict. The bound graph requires mass_kg, charge_c, density_ref_m3, temperature_parallel_j, temperature_perpendicular_ref_j, electron_temperature_j, reference_z, plug_left_z and plug_right_z. Optional kinetic controls, their defaults and validation are defined by scirel.mirror.grid-mirror-kinetic-closure; r_grid, z_grid, b_t and psi are supplied from the current Hall call and override matching entries. Psi-dependent profiles must interpret the Hall psi=R A_phi in Wb/rad. The wrapper does not reconcile kinetic mass/charge with the Hall mass/charge.
    tol : finite real scalar
        Outer Hall relative flux-change stopping threshold Shape scalar. The Hall graph checks finiteness, not positivity; choose a positive value for intended stopping.
    maxiter : integer scalar
        Hall Picard update bound [count] Shape scalar. Integer >= 1; outer nonconvergence returns converged=false if terminal checks pass.
    relax : finite real scalar
        Previous-flux weight in Hall Green update Shape scalar. 0 <= value < 1.
    minimum_field : finite real scalar
        Hall update field floor [T] Shape scalar. Strictly positive; checked during updates and before the terminal kinetic closure.
    minimum_firehose_margin : finite real scalar
        Terminal active-cell firehose threshold Shape scalar. Negative disables the terminal threshold; nonnegative values reject active cells at or below it.
    plasma_mask : boolean array, callable returning boolean array, or None
        Fixed or state-dependent Hall active-cell policy [boolean] Shape [N_Z,N_R], callable(B,psi)->[N_Z,N_R], or null. Null selects all cells; fixed/callable masks must match the grid shape and use true boolean dtype; integer/float masks are rejected without coercion.
    hall_multiplier : finite real scalar
        Hall drift multiplier Shape scalar. Nonnegative.
    include_toroidal_inertia : bool
        Enable the Hall leaf's bounded local inertia correction [boolean] Shape scalar. Actual boolean scalar; not numeric 0/1.
    hall_density_floor_fraction : finite real scalar
        Relative density floor for Hall-active drift support Shape scalar. 0 <= value < 1.
    maximum_inertial_mach : finite real scalar
        Ion-drift Mach cap in Hall leaf Shape scalar. Strictly positive.
    inertia_relax : finite real scalar
        Previous-current weight in Hall local inertia iteration Shape scalar. 0 <= value < 1.
    inertia_tolerance : finite real scalar
        Hall local inertia stopping threshold Shape scalar. Strictly positive.
    inertia_max_iterations : integer scalar
        Hall local inertia iteration bound [count] Shape scalar. Integer >= 1; local nonconvergence raises.
    compatibility_tol : finite real scalar
        Terminal parallel-momentum error threshold Shape scalar. Nonnegative; exceedance raises only with strict_compatibility=true.
    ohm_tolerance : finite real scalar
        Terminal normalized generalized-Ohm error threshold Shape scalar. Strictly positive; exceedance raises only with strict_compatibility=true.
    strict_compatibility : bool
        Reject Hall terminal compatibility threshold exceedance [boolean] Shape scalar. Actual boolean scalar; the separate firehose check remains active.

    Returns
    -------
    psi : float64
        Terminal Hall psi=R A_phi state [Wb/rad] Shape [N_Z,N_R]. Returned unchanged from the Hall graph after one or more updates.
    plasma_cell_currents : float64
        Terminal Hall cell-current grid [A] Shape [N_Z,N_R]. Recomputed by the Hall graph at terminal psi.
    J_phi : float64
        Terminal reduced-Hall toroidal current density [A/m^2] Shape [N_Z,N_R]. Hall active-cell mask applies.
    B_R : float64
        Terminal radial poloidal field [T] Shape [N_Z,N_R]. Derived from terminal psi.
    B_Z : float64
        Terminal axial poloidal field [T] Shape [N_Z,N_R]. Derived from terminal psi.
    B : float64
        Terminal poloidal-field magnitude passed into the last kinetic evaluation [T] Shape [N_Z,N_R]. The Hall graph checks minimum_field before the terminal kinetic closure call.
    p_parallel : float64
        Terminal kinetic parallel pressure after Hall scalar broadcast [Pa] Shape [N_Z,N_R]. Taken from the terminal kinetic closure and shape-coerced by Hall.
    p_perpendicular : float64
        Terminal kinetic perpendicular pressure after Hall scalar broadcast [Pa] Shape [N_Z,N_R]. Taken from the terminal kinetic closure and shape-coerced by Hall.
    parallel_force : float64
        Terminal Hall force along magnetic field [Pa/m] Shape [N_Z,N_R]. Hall diagnostic, not an independent physical validation.
    force_R : float64
        Terminal radial Hall target force [Pa/m] Shape [N_Z,N_R]. May include centrifugal correction.
    force_Z : float64
        Terminal axial Hall target force [Pa/m] Shape [N_Z,N_R]. Returned from Hall state.
    ion_toroidal_velocity : float64
        Terminal Hall ion toroidal drift [m/s] Shape [N_Z,N_R]. Zero outside Hall-active cells.
    electron_toroidal_velocity : float64
        Terminal Hall electron toroidal drift [m/s] Shape [N_Z,N_R]. Zero outside Hall-active cells.
    electric_field_R : float64
        Terminal radial electrostatic field [V/m] Shape [N_Z,N_R]. From kinetic electrostatic_potential through the Hall leaf.
    electric_field_Z : float64
        Terminal axial electrostatic field [V/m] Shape [N_Z,N_R]. From kinetic electrostatic_potential through the Hall leaf.
    hall_state : Python mapping
        Complete terminal reduced-Hall leaf result [mixed SI] Shape mapping. Returned by the child graph without outer modification.
    converged : bool
        Hall outer Picard convergence flag [boolean] Shape scalar. False at maxiter is returned if terminal gates pass.
    iterations : integer
        Executed Hall outer updates [count] Shape scalar. Between one and maxiter inclusive.
    relative_psi_change : float
        Last Hall relative flux change Shape scalar. Uses the bound Hall graph's norm convention.
    parallel_force_error : float
        Terminal Hall parallel-momentum error fraction Shape scalar. Compared with compatibility_tol.
    generalized_ohm_error : float
        Terminal normalized generalized-Ohm residual Shape scalar. Compared with ohm_tolerance.
    closure_state : Python mapping
        Unmodified mapping from the last grid mirror kinetic call [mixed SI] Shape mapping. Includes the kinetic graph's density, pressure, potential and diagnostic fields; may not match Hall-broadcast primary pressure shapes if a custom kinetic override is used.
    firehose_margin : float64
        Terminal Hall firehose/tension margin Shape [N_Z,N_R]. Checked on active cells when minimum_firehose_margin >= 0.
    compatibility_messages : Python list of strings
        Hall terminal compatibility exceedance messages [text] Shape list[string]. Can be nonempty on successful return only when strict_compatibility=false.
    iteration_history : Python list of mappings
        Hall per-update flux/current and Ohm diagnostics [mixed dimensionless diagnostics] Shape [iterations] list[mapping]. Each item records iteration, relative_psi_change, relative_current_change and generalized_ohm_error.

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
    solve_reduced_hall_anisotropic_picard : Run the Hall composition directly.

    Notes
    -----
    Copy kinetic_config, then bind a pressure_closure(B,psi) which calls the grid mirror kinetic TaskGraph with the current Hall B and psi and with the outer r_grid/z_grid overriding any same-named kinetic_config entries. Remove kinetic_config from the Hall payload, replace any supplied pressure_closure with the bound closure, and return the reduced-Hall TaskGraph result unchanged. The outer wrapper performs no magnetic update itself; the nested Hall graph owns its bounded Picard and optional Hall-inertia iterations, checks the terminal field floor before the final kinetic closure, and reevaluates that closure at its terminal state.

    axisymmetric grid mirror end-loss/quasineutral kinetic closure coupled to reduced-Hall anisotropic Picard feedback

    The kinetic_config supplies all remaining required kinetic graph ports and is scientifically compatible with the outer Hall ion properties; every psi-dependent kinetic profile interprets psi=R A_phi in Wb/rad.

    The two nested graphs interpret magnetic field, flux and pressure using compatible conventions; the wrapper does not verify this beyond their existing contracts.

    Dependency-injection hooks can replace the bound nested callables for testing, but such overrides are not evidence for the canonical scientific composition.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.equilibrium import solve_kinetic_mirror_hall_equilibrium
    >>> seen = {}
    >>> def kinetic_composition(payload):
    ...     seen['kinetic'] = payload
    ...     return {'p_parallel': np.array([[2.0]]), 'p_perpendicular': np.array([[3.0]])}
    >>> def hall_composition(payload):
    ...     state = payload['pressure_closure'](np.array([[1.5]]), np.array([[0.25]]))
    ...     return {'converged': True, 'closure_state': state}
    >>> result = solve_kinetic_mirror_hall_equilibrium({'r_grid': np.array([[0.1]]), 'z_grid': np.array([[0.0]]), 'psi_vac': np.array([[0.2]]), 'g_psi': np.zeros((1, 1)), 'ion_mass_kg': 1.0, 'ion_charge_c': 1.0, 'kinetic_config': {'mass_kg': 1.0}}, kinetic_composition=kinetic_composition, hall_composition=hall_composition)
    >>> assert result['converged'] and result['closure_state']['p_parallel'][0, 0] == 2.0
    >>> assert seen['kinetic']['b_t'][0, 0] == 1.5 and seen['kinetic']['psi'][0, 0] == 0.25
    >>> assert np.array_equal(seen['kinetic']['r_grid'], np.array([[0.1]]))
    """
    from scirel._composition import compose
    from scirel.equilibrium.reduced_hall_anisotropic_picard import (
        solve_reduced_hall_anisotropic_picard,
    )
    from scirel.mirror.grid_mirror_kinetic_closure import solve_grid_mirror_kinetic_closure

    return compose(
        _run_composition,
        inputs,
        kwargs,
        {
            "composition_loader": {
                "scirel.mirror.compositions.grid_mirror_kinetic_closure": kinetic_composition
                or solve_grid_mirror_kinetic_closure,
                "scirel.equilibrium.compositions.reduced_hall_anisotropic_picard": hall_composition
                or solve_reduced_hall_anisotropic_picard,
            }
        },
    )
