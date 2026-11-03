"""Ambipolar end-loss potential closure for one magnetized ion species."""

from scirel._validation import (
    required_finite_scalar as _require_finite_scalar,
    required_integer_scalar as _require_integer_scalar,
)
import numpy as np
from scirel._mirror_numerics import _mirror_flux
from scirel._numerics import _potential_midpoint

ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837139e-31


def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    values = np.asarray(value, dtype=float)
    try:
        values = np.broadcast_to(values, np.shape(psi))
    except ValueError as exc:
        raise ValueError(f"{name} cannot be broadcast over psi") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def _one_way_flux(
    density,
    mass_kg,
    charge_c,
    temperature_parallel_j,
    temperature_perpendicular_j,
    b_reference_t,
    b_plug_t,
    phi_reference_v,
    phi_plug_v,
    refill,
):
    """Evaluate the one-way half-space flux above a mirror/electrostatic barrier."""
    return _mirror_flux(
        density,
        mass_kg,
        charge_c,
        temperature_parallel_j,
        temperature_perpendicular_j,
        b_reference_t,
        b_plug_t,
        phi_reference_v,
        phi_plug_v,
        refill,
    )


def solve_mirror_ambipolar_potential(
    b_reference_t,
    b_plug_t,
    psi,
    ion_mass_kg,
    ion_charge_c,
    ion_density_ref_m3,
    ion_temperature_parallel_j,
    ion_temperature_perpendicular_j,
    electron_temperature_j,
    phi_reference_v=0.0,
    electron_density_ref_m3=None,
    ion_loss_refill=1.0,
    electron_loss_refill=1.0,
    potential_tolerance_v=1e-06,
    current_tolerance=1e-10,
    max_iterations=100,
    initial_bracket_thermal=8.0,
    mode="solve",
    phi_plug_v=None,
):
    """Solve ``Z_i Gamma_i = Gamma_e`` independently on each flux surface.

    Barrier fluxes use bounded exponent differences. In evaluate mode
    converged retains its historical meaning of successful evaluation; the
    explicit current_balance_solved flag is False and the current residual
    must not be interpreted as a solved equilibrium. Fluxes use relative
    potentials before species scaling, and finite stable midpoints retain a
    large common gauge without changing the residual/width gates. Nonfinite states fail.

    Parameters
    ----------
    b_reference_t : real array-like converted to float64, shape scalar or array; jointly broadcast with b_plug_t, psi and phi_reference_v
        Reference magnetic-field magnitude [T]. Finite and strictly positive at
        every surface.
    b_plug_t : real array-like converted to float64, shape scalar or array; common broadcast shape
        Plug magnetic-field magnitude [T]. Finite and strictly positive at every
        surface; the implementation does not require b_plug_t >= b_reference_t.
    psi : real array-like converted to float64, shape scalar or array; common broadcast shape
        Caller-defined flux-surface coordinate for profiles [caller-defined flux
        coordinate]. Finite; no monotonicity or normalization requirement is
        enforced.
    ion_mass_kg : finite real scalar
        Mass of the positive ion species [kg]. Strictly positive.
    ion_charge_c : finite real scalar
        Positive ion charge; divided by elementary charge to form the
        charge-state multiplier [C]. Strictly positive; integer charge state is
        not enforced.
    ion_density_ref_m3 : real array-like or Python callable returning real array-like, shape scalar, array or callable output broadcastable to common shape
        Ion reference number density, optionally a callable of psi [m^-3].
        Finite and nonnegative. In solve mode it must be positive exactly where
        electron reference density is positive.
    ion_temperature_parallel_j : real array-like or Python callable returning real array-like, shape scalar, array or callable output broadcastable to common shape
        Ion parallel thermal-energy scale, optionally a callable of psi [J].
        Finite and strictly positive.
    ion_temperature_perpendicular_j : real array-like or Python callable returning real array-like, shape scalar, array or callable output broadcastable to common shape
        Ion perpendicular thermal-energy scale, optionally a callable of psi
        [J]. Finite and strictly positive.
    electron_temperature_j : real array-like or Python callable returning real array-like, shape scalar, array or callable output broadcastable to common shape
        Electron thermal-energy scale used in both pitch directions, optionally
        a callable of psi [J]. Finite and strictly positive.
    phi_reference_v : real array-like converted to float64, shape scalar or array; common broadcast shape, default 0.0
        Reference potential and returned potential on joint-vacuum surfaces in
        solve mode [V]. Finite; the solve bracket is centered on this field.
    electron_density_ref_m3 : real array-like or Python callable returning real array-like, shape scalar, array or callable output broadcastable to common shape, default None
        Optional electron reference density, or callable of psi [m^-3]. If
        absent, charge_state times ion_density_ref_m3 is used; if supplied,
        finite and nonnegative. Solve mode requires paired positive or paired
        zero density on each surface.
    ion_loss_refill : finite real scalar, default 1.0
        Multiplier of the modeled one-way ion loss flux. In [0,1]; solve mode
        requires strictly positive value, while evaluate mode permits zero.
    electron_loss_refill : finite real scalar, default 1.0
        Multiplier of the modeled one-way electron loss flux. In (0,1].
    potential_tolerance_v : finite real scalar, default 1e-06
        Maximum half-width of the active returned-potential bracket [V].
        Strictly positive; used together with current_tolerance.
    current_tolerance : finite real scalar, default 1e-10
        Maximum absolute log-current ratio at the tested midpoint. Strictly
        positive; a separate relative_current_residual is returned for
        diagnosis.
    max_iterations : Python or NumPy integer scalar, excluding bool, default 100
        Maximum number of shared vectorized bisection updates [iterations].
        Integer >= 1; float values are not truncated.
    initial_bracket_thermal : finite real scalar, default 8.0
        Initial bracket half-width in combined ion/electron thermal voltages.
        Strictly positive; expansion is additionally bounded to eight rounds.
    mode : string, default 'solve'
        Choose plug-potential solve or prescribed-potential flux evaluation
        [enum]. Exactly 'solve' or 'evaluate'; evaluate requires phi_plug_v.
    phi_plug_v : real array-like or Python callable returning real array-like, shape scalar, array or callable output broadcastable to common shape, default None
        Prescribed plug potential for evaluate mode, optionally a callable of
        psi [V]. Required and finite in evaluate mode. Ignored in solve mode.

    Returns
    -------
    potential_v : NumPy float64 array, shape common broadcast shape
        Plug potential phi_plug in the caller's voltage origin (not the drop);
        the drop is potential_v - phi_reference_v. Solved or prescribed;
        joint-vacuum surfaces retain phi_reference_v in solve mode [V]. Evaluate
        mode returns supplied phi_plug_v; solve mode returns only after all
        active surfaces meet the implemented stopping test.
    ion_particle_flux_m2_s : NumPy float64 array, shape common broadcast shape
        Modeled one-way ion end-loss particle flux after ion_loss_refill [m^-2
        s^-1]. Finite nonnegative; zero for absent ions or zero refill;
        underflow may round to zero.
    electron_particle_flux_m2_s : NumPy float64 array, shape common broadcast shape
        Modeled one-way electron end-loss particle flux after
        electron_loss_refill [m^-2 s^-1]. Finite nonnegative; zero for absent
        electrons; underflow may round to zero.
    log_current_ratio : NumPy float64 array, shape common broadcast shape
        Analytic log charge-weighted ion flux minus log electron flux for
        positive populations; inactive evaluation uses finite tiny-floor
        diagnostics. Finite. Active positive populations retain analytic logs
        when a reported flux underflows.
    relative_current_residual : NumPy float64 array, shape common broadcast shape
        tanh(log_current_ratio/2), avoiding flux-sum overflow. Evaluate mode can
        be unbalanced. Solve mode checks log_current_ratio at the very returned
        potential.
    iterations : Python int
        Shared bisection update count, or zero in evaluate mode [iterations].
        Evaluate returns 0; solve mode returns at least one update even if all
        surfaces are joint vacuum.
    converged : Python bool
        Whether the solve stopping test passed, or whether evaluate mode
        completed without solving [boolean]. Always True in a returned mapping.
        In evaluate mode this does not assert ambipolar balance; solve failures
        raise.
    evaluation_complete : Python bool
        The requested numerical evaluation completed [boolean]. True on
        successful return.
    current_balance_solved : Python bool
        Whether a bounded current-balance solve was performed [boolean]. True in
        solve mode, False in prescribed evaluate mode; not a model validity
        certificate.

    Raises
    ------
    FloatingPointError
        Raises RuntimeError if an active surface cannot be bracketed after eight
        expansion rounds. Nonfinite dimensionless barriers, fluxes or residuals
        raise FloatingPointError or ValueError; no NaN success is returned.
    RuntimeError
        Raises RuntimeError if an active surface cannot be bracketed after eight
        expansion rounds. Nonfinite dimensionless barriers, fluxes or residuals
        raise FloatingPointError or ValueError; no NaN success is returned.
        Raises RuntimeError unless all active surfaces meet half-bracket-width
        and absolute log-current-ratio tests at the same returned potential
        within max_iterations. A mathematically desired root that cannot be
        represented at the requested width and residual resolution still fails;
        no ULP-sized tolerance floor is silently introduced.
    TypeError
        Raises ValueError for unsupported mode, nonfinite/nonpositive required
        scalar controls, refill values outside their mode-specific bounds,
        nonfinite or nonpositive fields/temperatures, negative densities, absent
        evaluate-mode phi_plug_v, or one-sided-vacuum solve surfaces. Noninteger
        max_iterations raises ValueError; incompatible broadcasts, numeric
        conversion and caller profile failures may raise ValueError or
        TypeError.
    ValueError
        Raises ValueError for unsupported mode, nonfinite/nonpositive required
        scalar controls, refill values outside their mode-specific bounds,
        nonfinite or nonpositive fields/temperatures, negative densities, absent
        evaluate-mode phi_plug_v, or one-sided-vacuum solve surfaces. Noninteger
        max_iterations raises ValueError; incompatible broadcasts, numeric
        conversion and caller profile failures may raise ValueError or
        TypeError. Raises RuntimeError if an active surface cannot be bracketed
        after eight expansion rounds. Nonfinite dimensionless barriers, fluxes
        or residuals raise FloatingPointError or ValueError; no NaN success is
        returned.

    See Also
    --------
    scirel.field.solve_multi_coil_vacuum_field : Vacuum mirror field giving b_reference_t and b_plug_t.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.closures import solve_mirror_ambipolar_potential
    >>> e = 1.602176634e-19
    >>> m_i = 1.67262192595e-27
    >>> m_e = 9.1093837139e-31
    >>> r = solve_mirror_ambipolar_potential(1.0, 1.0, 0.0, m_i, e, 2.0e18, 2.0*e, 3.0*e, e, electron_density_ref_m3=3.0e18, ion_loss_refill=0.25, electron_loss_refill=0.5, mode='evaluate', phi_plug_v=1.0)
    >>> np.testing.assert_allclose(r['ion_particle_flux_m2_s'], 2.0e18*np.sqrt(2.0*e/(2.0*np.pi*m_i))*np.exp(-0.5)*0.25)
    >>> np.testing.assert_allclose(r['electron_particle_flux_m2_s'], 3.0e18*np.sqrt(e/(2.0*np.pi*m_e))*0.5)
    >>> assert r['iterations'] == 0 and r['converged']
    >>> assert r['evaluation_complete'] and not r['current_balance_solved']
    """
    if mode not in {"solve", "evaluate"}:
        raise ValueError("mode must be solve or evaluate")
    ion_mass_kg = _require_finite_scalar(ion_mass_kg, "ion_mass_kg", positive=True)
    ion_charge_c = _require_finite_scalar(ion_charge_c, "ion_charge_c", positive=True)
    ion_loss_refill = _require_finite_scalar(ion_loss_refill, "ion_loss_refill", nonnegative=True)
    electron_loss_refill = _require_finite_scalar(
        electron_loss_refill, "electron_loss_refill", positive=True
    )
    potential_tolerance_v = _require_finite_scalar(
        potential_tolerance_v, "potential_tolerance_v", positive=True
    )
    current_tolerance = _require_finite_scalar(
        current_tolerance, "current_tolerance", positive=True
    )
    max_iterations = _require_integer_scalar(max_iterations, "max_iterations", minimum=1)
    initial_bracket_thermal = _require_finite_scalar(
        initial_bracket_thermal, "initial_bracket_thermal", positive=True
    )
    if not 0.0 <= ion_loss_refill <= 1.0:
        raise ValueError("ion_loss_refill must lie in [0, 1]")
    if mode == "solve" and ion_loss_refill <= 0.0:
        raise ValueError(
            "a positive ion_loss_refill is required to determine an ambipolar end potential"
        )
    if electron_loss_refill > 1.0:
        raise ValueError("electron_loss_refill must lie in (0, 1]")
    b_reference_t, b_plug_t, psi, phi_reference_v = np.broadcast_arrays(
        np.asarray(b_reference_t, dtype=float),
        np.asarray(b_plug_t, dtype=float),
        np.asarray(psi, dtype=float),
        np.asarray(phi_reference_v, dtype=float),
    )
    if not all(
        (np.all(np.isfinite(value)) for value in (b_reference_t, b_plug_t, psi, phi_reference_v))
    ):
        raise ValueError("field, psi, and reference potential inputs must be finite")
    if np.any(b_reference_t <= 0.0) or np.any(b_plug_t <= 0.0):
        raise ValueError("reference and plug magnetic fields must be positive")
    ion_density = _field(ion_density_ref_m3, psi, "ion_density_ref_m3")
    ion_parallel = _field(ion_temperature_parallel_j, psi, "ion_temperature_parallel_j")
    ion_perpendicular = _field(
        ion_temperature_perpendicular_j, psi, "ion_temperature_perpendicular_j"
    )
    electron_temperature = _field(electron_temperature_j, psi, "electron_temperature_j")
    charge_state = ion_charge_c / ELEMENTARY_CHARGE_C
    electron_density = (
        charge_state * ion_density
        if electron_density_ref_m3 is None
        else _field(electron_density_ref_m3, psi, "electron_density_ref_m3")
    )
    if np.any(ion_density < 0.0) or np.any(electron_density < 0.0):
        raise ValueError("reference densities cannot be negative")
    if (
        np.any(ion_parallel <= 0.0)
        or np.any(ion_perpendicular <= 0.0)
        or np.any(electron_temperature <= 0.0)
    ):
        raise ValueError("temperatures must be positive")

    def fluxes(phi_plug_v):
        ion_flux = _one_way_flux(
            ion_density,
            ion_mass_kg,
            ion_charge_c,
            ion_parallel,
            ion_perpendicular,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            ion_loss_refill,
        )
        electron_flux = _one_way_flux(
            electron_density,
            ELECTRON_MASS_KG,
            -ELEMENTARY_CHARGE_C,
            electron_temperature,
            electron_temperature,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            electron_loss_refill,
        )
        log_ion = _mirror_flux(
            ion_density,
            ion_mass_kg,
            ion_charge_c,
            ion_parallel,
            ion_perpendicular,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            ion_loss_refill,
            return_log=True,
        ) + np.log(charge_state)
        log_electron = _mirror_flux(
            electron_density,
            ELECTRON_MASS_KG,
            -ELEMENTARY_CHARGE_C,
            electron_temperature,
            electron_temperature,
            b_reference_t,
            b_plug_t,
            phi_reference_v,
            phi_plug_v,
            electron_loss_refill,
            return_log=True,
        )
        # The inactive/vacuum evaluator keeps finite log diagnostics. Active
        # positive populations retain their analytic logs even when flux rounds
        # to zero, so underflow cannot manufacture a balanced root.
        both = (ion_density > 0) & (electron_density > 0) & (ion_loss_refill > 0)
        tiny_log = np.log(np.finfo(float).tiny)
        residual = np.empty(log_ion.shape)
        residual[both] = log_ion[both] - log_electron[both]
        residual[~both] = np.maximum(log_ion[~both], tiny_log) - np.maximum(
            log_electron[~both], tiny_log
        )
        if not np.all(np.isfinite(residual)):
            raise FloatingPointError("end-loss current residual must be finite")
        return (residual, ion_flux, electron_flux)

    if mode == "evaluate":
        if phi_plug_v is None:
            raise ValueError("phi_plug_v is required when mode=evaluate")
        potential = _field(phi_plug_v, psi, "phi_plug_v")
        log_ratio, ion_flux, electron_flux = fluxes(potential)
        return {
            "potential_v": potential,
            "ion_particle_flux_m2_s": ion_flux,
            "electron_particle_flux_m2_s": electron_flux,
            "log_current_ratio": log_ratio,
            "relative_current_residual": np.tanh(0.5 * log_ratio),
            "iterations": 0,
            "converged": True,
            "evaluation_complete": True,
            "current_balance_solved": False,
        }
    if np.any((ion_density > 0.0) != (electron_density > 0.0)):
        raise ValueError(
            "ion and electron reference densities must be both positive or both zero on each surface for solve mode"
        )
    active = (ion_density > 0.0) & (electron_density > 0.0)
    thermal_voltage = ion_parallel / ion_charge_c + electron_temperature / ELEMENTARY_CHARGE_C
    span = initial_bracket_thermal * thermal_voltage
    lower = phi_reference_v - span
    upper = phi_reference_v + span
    lower_residual = fluxes(lower)[0]
    upper_residual = fluxes(upper)[0]
    for _ in range(8):
        missing_lower = active & (lower_residual < 0.0)
        missing_upper = active & (upper_residual > 0.0)
        if not np.any(missing_lower | missing_upper):
            break
        span = upper - lower
        lower = np.where(missing_lower, lower - span, lower)
        upper = np.where(missing_upper, upper + span, upper)
        lower_residual = fluxes(lower)[0]
        upper_residual = fluxes(upper)[0]
    if np.any(active & ((lower_residual < 0.0) | (upper_residual > 0.0))):
        raise RuntimeError("failed to bracket the ambipolar end potential")
    potential = np.where(active, _potential_midpoint(lower, upper), phi_reference_v)
    converged = not np.any(active)
    iterations = 0
    for iterations in range(1, int(max_iterations) + 1):
        residual, _, _ = fluxes(potential)
        exact = active & (residual == 0.0)
        lower = np.where(exact, potential, lower)
        upper = np.where(exact, potential, upper)
        # Test the residual at the very potential we will return. The
        # predecessor tested this midpoint but returned the next midpoint.
        if not np.any(active) or (
            np.max(np.abs(upper[active] - lower[active])) <= 2 * potential_tolerance_v
            and np.max(np.abs(residual[active])) <= current_tolerance
        ):
            converged = True
            break
        lower = np.where(active & (residual > 0.0), potential, lower)
        upper = np.where(active & (residual <= 0.0), potential, upper)
        potential = np.where(active, _potential_midpoint(lower, upper), phi_reference_v)
    if not converged:
        raise RuntimeError("ambipolar end-potential solve did not converge")
    log_ratio, ion_flux, electron_flux = fluxes(potential)
    if np.any(active) and np.max(np.abs(log_ratio[active])) > current_tolerance:
        raise RuntimeError("returned ambipolar end potential does not satisfy current tolerance")
    return {
        "potential_v": potential,
        "ion_particle_flux_m2_s": ion_flux,
        "electron_particle_flux_m2_s": electron_flux,
        "log_current_ratio": log_ratio,
        "relative_current_residual": np.tanh(0.5 * log_ratio),
        "iterations": iterations,
        "converged": bool(converged),
        "evaluation_complete": True,
        "current_balance_solved": True,
    }


__all__ = ["solve_mirror_ambipolar_potential"]
