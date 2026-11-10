"""Sequential ambipolar closure composed from a kinetic-moment evaluator."""

from __future__ import annotations
from scirel._validation import (
    finite_scalar as _require_finite_scalar,
    integer_scalar as _require_integer_scalar,
)
import numpy as np

from scirel._result import Result


def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    values = np.asarray(value, dtype=float)
    if values.ndim == 0:
        values = np.full(psi.shape, values, dtype=float)
    elif values.shape != psi.shape:
        raise ValueError(f"{name} must be scalar or match psi shape")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def _broadcast_state(b_t, psi):
    """Controlled same-grid shape embedding for the two caller-owned fields."""
    psi_values = np.asarray(psi, dtype=float)
    b_values = np.asarray(b_t, dtype=float)
    if b_values.ndim == 0:
        b_values = np.full(psi_values.shape, b_values, dtype=float)
    elif b_values.shape != psi_values.shape:
        raise ValueError("b_t must be scalar or match psi shape")
    return (b_values, psi_values)


def _charge_state(charge_c):
    """Controlled scalar unit conversion from ion charge to charge state."""
    value = float(charge_c) / 1.602176634e-19
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("charge_c must produce a finite positive ion charge state")
    return value


def _run_composition(inputs, *, asset_loader):
    """Solve local quasineutrality by repeated calls to the emitted moment leaf."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    required = {
        "b_t",
        "psi",
        "mass_kg",
        "charge_c",
        "density_ref_m3",
        "temperature_parallel_j",
        "temperature_perpendicular_ref_j",
        "b_ref_t",
        "electron_temperature_j",
    }
    missing = sorted((key for key in required if key not in inputs))
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    if inputs["mass_kg"] <= 0.0 or inputs["charge_c"] <= 0.0:
        raise ValueError("this closure requires one positive ion species")
    tolerance = _require_finite_scalar(
        inputs.get("potential_tolerance_v"), "potential_tolerance_v", 1e-08
    )
    residual_tolerance = _require_finite_scalar(
        inputs.get("quasineutral_tolerance"), "quasineutral_tolerance", 1e-10
    )
    max_iterations = _require_integer_scalar(
        inputs.get("max_iterations"), "max_iterations", 100, minimum=1
    )
    bracket_thermal = _require_finite_scalar(
        inputs.get("initial_bracket_thermal"), "initial_bracket_thermal", 8.0
    )
    if (
        tolerance <= 0.0
        or residual_tolerance <= 0.0
        or max_iterations < 1
        or (bracket_thermal <= 0.0)
    ):
        raise ValueError("invalid quasineutral solver controls")
    b_t, psi = _broadcast_state(inputs["b_t"], inputs["psi"])
    moment_inputs = {
        key: inputs[key]
        for key in (
            "mass_kg",
            "charge_c",
            "density_ref_m3",
            "temperature_parallel_j",
            "temperature_perpendicular_ref_j",
            "b_ref_t",
            "phi_ref_v",
            "b_plug_left_t",
            "b_plug_right_t",
            "phi_plug_left_v",
            "phi_plug_right_v",
            "loss_cone_refill",
            "quadrature_order",
        )
        if key in inputs
    }
    temperature_parallel = _field(inputs["temperature_parallel_j"], psi, "temperature_parallel_j")
    if np.any(temperature_parallel <= 0.0):
        raise ValueError("temperature_parallel_j must be positive")
    moment_inputs["temperature_parallel_j"] = temperature_parallel
    phi_ion_ref = _field(inputs.get("phi_ref_v", 0.0), psi, "phi_ref_v")
    t_e = _field(inputs["electron_temperature_j"], psi, "electron_temperature_j")
    if np.any(t_e <= 0.0):
        raise ValueError("electron_temperature_j must be positive")
    z_i = _charge_state(inputs["charge_c"])
    n_i_ref = _field(inputs["density_ref_m3"], psi, "density_ref_m3")
    reference_density = asset_loader("scirel.closures.quasineutral_reference_density")
    if inputs.get("electron_density_ref_m3") is None:
        n_e_ref = _field(
            reference_density(n_i_ref, z_i)["electron_density_ref_m3"],
            psi,
            "electron_density_ref_m3",
        )
    else:
        n_e_ref = _field(inputs["electron_density_ref_m3"], psi, "electron_density_ref_m3")
    phi_e_ref = _field(inputs.get("electron_phi_ref_v", phi_ion_ref), psi, "electron_phi_ref_v")
    if np.any(n_i_ref < 0.0) or np.any(n_e_ref < 0.0):
        raise ValueError("reference densities cannot be negative")
    if np.any((n_i_ref > 0.0) != (n_e_ref > 0.0)):
        raise ValueError(
            "ion and electron reference densities must be both positive or both zero on each surface for quasineutral solve"
        )
    active = (n_i_ref > 0.0) & (n_e_ref > 0.0)
    moment = asset_loader("scirel.mirror.mirror_constrained_moments")
    electron_response = asset_loader("scirel.closures.boltzmann_quasineutrality")
    potential_solver = asset_loader("scirel.closures.quasineutral_potential")
    pressure_assembly = asset_loader("scirel.mirror.mirror_total_pressure")

    def state_at(potential):
        return moment(b_t=b_t, psi=psi, potential_v=potential, **moment_inputs)

    def electron_state(potential, ion_density):
        return electron_response(
            potential_v=potential,
            electron_temperature_j=t_e,
            electron_density_ref_m3=n_e_ref,
            electron_phi_ref_v=phi_e_ref,
            ion_density_m3=ion_density,
            ion_charge_state=z_i,
        )

    def residual(potential):
        ion = state_at(potential)["density_m3"]
        return electron_state(potential, ion)

    solved = potential_solver(
        phi_ion_ref,
        temperature_parallel,
        t_e,
        inputs["charge_c"],
        active,
        residual,
        potential_tolerance_v=tolerance,
        quasineutral_tolerance=residual_tolerance,
        max_iterations=max_iterations,
        initial_bracket_thermal=bracket_thermal,
    )
    if not solved.get("converged", False):
        raise RuntimeError("terminal quasineutral solve did not converge")
    potential = solved["potential_v"]
    ion = state_at(potential)
    electrons = electron_state(potential, ion["density_m3"])
    terminal_residual = np.asarray(electrons["logarithmic_charge_residual"], dtype=float)
    if not np.all(np.isfinite(terminal_residual)) or np.any(
        np.abs(terminal_residual[active]) > residual_tolerance
    ):
        raise RuntimeError(
            "terminal quasineutral state does not meet the declared residual tolerance"
        )
    state = pressure_assembly(ion, electrons)
    state.update(
        {
            "electrostatic_potential": potential,
            "iterations": solved["iterations"],
            "converged": solved["converged"],
        }
    )
    return state


def solve_mirror_quasineutral_closure(inputs=None, **kwargs):
    """Solve a bounded mirror quasineutral closure with Boltzmann electrons.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing the required ``b_t``, ``psi``, ``mass_kg``,
        ``charge_c``, ``density_ref_m3``, ``temperature_parallel_j``,
        ``temperature_perpendicular_ref_j``, ``b_ref_t`` and
        ``electron_temperature_j`` fields. Profile fields may be scalars,
        psi-shaped arrays or callables of ``psi``. Optional plug, reference
        density, potential-solver tolerance and iteration controls follow the
        catalog contract; keyword arguments are merged at the composition
        boundary. [not applicable]
    **kwargs
        Named inputs merged with ``inputs`` by the composition boundary.
        [not applicable]

    Other Parameters
    ----------------
    b_t : real array-like
        Local mirror magnetic-field magnitude. [T] Shape: scalar or exactly
        ``psi``-shaped array. Must be finite and positive for the ion-moment
        operator.
    psi : real array-like
        Caller flux-profile label and output-shape carrier. [Wb (historical source label, not runtime-enforced)]
        Shape: scalar or array. Must be finite; no axis or unit conversion is
        performed.
    mass_kg : real scalar
        Positive-ion mass passed to the mirror moment operator. [kg] Shape:
        scalar. Must be finite and strictly positive.
    charge_c : real scalar
        Positive-ion charge. [C] Shape: scalar. Must be finite and strictly
        positive; its electron-charge-state ratio must also be finite and
        positive.
    density_ref_m3 : real array-like or callable
        Ion reference number density. [m^-3] Shape: scalar, exactly
        ``psi``-shaped array, or callable of ``psi``. Must be finite and
        nonnegative, with positivity matching the electron reference density.
    temperature_parallel_j : real array-like or callable
        Ion parallel reference thermal energy. [J] Shape: scalar, exactly
        ``psi``-shaped array, or callable of ``psi``. Must be finite and
        strictly positive.
    temperature_perpendicular_ref_j : real array-like or callable
        Ion perpendicular reference thermal energy. [J] Shape: scalar,
        ``psi``-compatible array, or callable of ``psi``. Must be finite and
        strictly positive.
    b_ref_t : real array-like or callable
        Ion reference magnetic-field magnitude. [T] Shape: scalar,
        ``psi``-compatible array, or callable of ``psi``. Must be finite and
        strictly positive.
    electron_temperature_j : real array-like or callable
        Prescribed Boltzmann electron thermal energy. [J] Shape: scalar,
        exactly ``psi``-shaped array, or callable of ``psi``. Must be finite
        and strictly positive.
    phi_ref_v : real array-like or callable, optional
        Ion reference potential, also returned where both reference densities
        are zero. [V] Shape: scalar, exactly ``psi``-shaped array, or callable
        of ``psi``. Default: 0.
    b_plug_left_t : real array-like or callable or None, optional
        Left mirror-plug field for loss-cone moments. [T or not applicable]
        Shape: None, scalar, ``psi``-compatible array, or callable of ``psi``.
        Default: None. Supply with ``b_plug_right_t`` and positive finite
        values when plug integration is active.
    b_plug_right_t : real array-like or callable or None, optional
        Right mirror-plug field for loss-cone moments. [T or not applicable]
        Shape: None, scalar, ``psi``-compatible array, or callable of ``psi``.
        Default: None. Supply with ``b_plug_left_t`` and positive finite values
        when plug integration is active.
    phi_plug_left_v : real array-like or callable, optional
        Left plug electrostatic potential. [V] Shape: scalar,
        ``psi``-compatible array, or callable of ``psi``. Default: 0.
    phi_plug_right_v : real array-like or callable, optional
        Right plug electrostatic potential. [V] Shape: scalar,
        ``psi``-compatible array, or callable of ``psi``. Default: 0.
    loss_cone_refill : real scalar, optional
        Fraction restoring full bi-Maxwellian pitch occupation.
        [dimensionless] Shape: scalar. Default: 0. Must be finite within
        ``[0, 1]``; one bypasses plug integration.
    quadrature_order : int, optional
        Legendre order for active plug pitch integration. [count] Shape:
        scalar. Default: 32. The ion-moment leaf requires at least eight.
    electron_density_ref_m3 : real array-like or callable or None, optional
        Explicit electron reference density. [m^-3] Shape: scalar, exactly
        ``psi``-shaped array, callable of ``psi``, or None. Default: None,
        which uses ``ion_charge_state * density_ref_m3``.
    electron_phi_ref_v : real array-like or callable or None, optional
        Electron reference potential. [V] Shape: scalar, ``psi``-compatible
        array, callable of ``psi``, or None. Default: None, which follows the
        ion reference potential.
    potential_tolerance_v : real scalar, optional
        Active potential-bracket width tolerance. [V] Shape: scalar. Default:
        1e-8. Must be finite and strictly positive.
    quasineutral_tolerance : real scalar, optional
        Maximum absolute logarithmic charge residual. [dimensionless] Shape:
        scalar. Default: 1e-10. Must be finite and strictly positive.
    max_iterations : int, optional
        Maximum potential-solver midpoint evaluations. [iterations] Shape:
        scalar. Default: 100. Must be an integer of at least two after
        preliminary graph validation.
    initial_bracket_thermal : real scalar, optional
        Initial bracket half-width in combined thermal-voltage units.
        [dimensionless] Shape: scalar. Default: 8. Must be finite and strictly
        positive.

    Returns
    -------
    The top-level value is a ``scirel._result.Result`` mapping; non-colliding
    fields are available by key and attribute access. The nested
    ``kinetic_moments`` field remains a plain dict.
    Fields preserve the baseline key order and ``psi`` sample shape.
    p_parallel : NumPy float64 array [Pa]
        Final ion parallel pressure plus isotropic electron pressure.
    p_perpendicular : NumPy float64 array [Pa]
        Final ion perpendicular pressure plus isotropic electron pressure.
    ion_density : NumPy float64 array [m^-3]
        Mirror-constrained ion number density at the returned potential.
    electron_density : NumPy float64 array [m^-3]
        Boltzmann electron number density at the returned potential.
    electrostatic_potential : NumPy float64 array [V]
        Converged electrostatic potential on active samples and reference potential on zero-density samples.
    relative_charge_residual : NumPy float64 array [dimensionless]
        Final (Z_i*n_i-n_e)/max(Z_i*n_i+n_e,tiny) from the Boltzmann response.
    kinetic_moments : Python dict of NumPy arrays [mixed; see bound ion-moment asset]
        Complete final mirror ion-moment mapping including density, pressures, local temperatures
        and pitch integrals.
    ion_p_parallel : NumPy float64 array [Pa]
        Final ion parallel pressure component before electron pressure is added.
    ion_p_perpendicular : NumPy float64 array [Pa]
        Final ion perpendicular pressure component before electron pressure is added.
    electron_pressure : NumPy float64 array [Pa]
        Boltzmann electron pressure added to each ion pressure component.
    density_m3 : NumPy float64 array [m^-3]
        Final ion density retained as the original ion-moment field, alongside ion_density.
    p_parallel_pa : NumPy float64 array [Pa]
        Final ion parallel pressure retained under its original moment-field name.
    p_perpendicular_pa : NumPy float64 array [Pa]
        Final ion perpendicular pressure retained under its original moment-field name.
    temperature_parallel_j : NumPy float64 array [J]
        Evaluated ion parallel thermal-energy parameter retained from final moments.
    temperature_perpendicular_local_j : NumPy float64 array [J]
        Untruncated local perpendicular thermal-energy parameter retained from final moments.
    untruncated_density_m3 : NumPy float64 array [m^-3]
        Final ion density before plug pitch reduction.
    density_pitch_integral : NumPy float64 array [dimensionless]
        Final dimensionless ion density pitch factor.
    parallel_pitch_integral : NumPy float64 array [dimensionless]
        Final dimensionless ion parallel-pressure pitch factor.
    perpendicular_pitch_integral : NumPy float64 array [dimensionless]
        Final dimensionless ion perpendicular-pressure pitch factor.
    iterations : Python int [iterations]
        Shared vectorized potential-bisection iteration count.
    converged : Python bool [dimensionless]
        Whether the potential solver completed successfully.

    Raises
    ------
    ValueError
        If required fields, profiles, reference-density masks, plug inputs or
        solver controls are invalid.
    RuntimeError
        If the bounded potential solve fails to bracket or converge, or the
        reevaluated terminal residual exceeds its declared tolerance.


    See Also
    --------
    scirel.closures.solve_quasineutral_potential : Bounded potential solver used by this composition.

    Notes
    -----
    The composition builds ion-moment profiles at trial potentials, evaluates
    the Boltzmann electron response, and solves logarithmic charge neutrality
    on the active surfaces. ``electron_density_ref_m3`` defaults to
    ``ion_charge_state * density_ref_m3``. Optional plug fields select the
    loss-cone moment branch. After convergence, ion moments and electron
    pressure are recomputed at the returned potential before total pressures
    are assembled. A zero reference-density surface is inactive and retains its
    reference potential. The returned mapping is a composed closure result, not
    a proof that the supplied moment model or plasma state is physically
    self-consistent.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.mirror import solve_mirror_quasineutral_closure
    >>> e = 1.602176634e-19
    >>> r = solve_mirror_quasineutral_closure(b_t=np.array([1.0, 1.4, 2.0]), psi=np.zeros(3), mass_kg=1.67262192595e-27, charge_c=e, density_ref_m3=2e18, temperature_parallel_j=1200*e, temperature_perpendicular_ref_j=2400*e, b_ref_t=1.0, electron_temperature_j=600*e)
    >>> b = np.array([1.0, 1.4, 2.0])
    >>> t_perp = b / ((b-1.0)/(1200*e) + 1.0/(2400*e))
    >>> expected = np.log(t_perp/(2400*e)) / (e/(1200*e) + e/(600*e))
    >>> np.testing.assert_allclose(r['electrostatic_potential'], expected, atol=2e-8)
    >>> assert np.max(np.abs(r['relative_charge_residual'])) < 1e-10
    >>> assert r['p_parallel'].shape == (3,) and r['converged']
    """
    from scirel._composition import compose
    from scirel.closures.boltzmann_quasineutrality import (
        compute_boltzmann_electron_state as _dependency_0,
    )
    from scirel.closures.quasineutral_potential import solve_quasineutral_potential as _dependency_1
    from scirel.closures.quasineutral_reference_density import (
        compute_reference_electron_density as _dependency_2,
    )
    from scirel.mirror.mirror_constrained_moments import (
        evaluate_mirror_constrained_moments as _dependency_3,
    )
    from scirel.mirror.mirror_total_pressure import assemble_mirror_total_pressure as _dependency_4

    result = compose(
        _run_composition,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.closures.boltzmann_quasineutrality": _dependency_0,
                "scirel.closures.quasineutral_potential": _dependency_1,
                "scirel.closures.quasineutral_reference_density": _dependency_2,
                "scirel.mirror.mirror_constrained_moments": _dependency_3,
                "scirel.mirror.mirror_total_pressure": _dependency_4,
            }
        },
    )
    return Result(result)


__all__ = ["solve_mirror_quasineutral_closure"]
