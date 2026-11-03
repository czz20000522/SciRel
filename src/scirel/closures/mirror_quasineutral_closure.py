"""Sequential ambipolar closure composed from a kinetic-moment evaluator."""
from __future__ import annotations
from scirel._validation import finite_scalar as _require_finite_scalar, integer_scalar as _require_integer_scalar, bool_scalar as _require_bool_scalar
import hashlib
from pathlib import Path
import numpy as np

def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    values = np.asarray(value, dtype=float)
    if values.ndim == 0:
        values = np.full(psi.shape, values, dtype=float)
    elif values.shape != psi.shape:
        raise ValueError(f'{name} must be scalar or match psi shape')
    if not np.all(np.isfinite(values)):
        raise ValueError(f'{name} must be finite')
    return values

def _broadcast_state(b_t, psi):
    """Controlled same-grid shape embedding for the two caller-owned fields."""
    psi_values = np.asarray(psi, dtype=float)
    b_values = np.asarray(b_t, dtype=float)
    if b_values.ndim == 0:
        b_values = np.full(psi_values.shape, b_values, dtype=float)
    elif b_values.shape != psi_values.shape:
        raise ValueError('b_t must be scalar or match psi shape')
    return (b_values, psi_values)

def _charge_state(charge_c):
    """Controlled scalar unit conversion from ion charge to charge state."""
    value = float(charge_c) / 1.602176634e-19
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError('charge_c must produce a finite positive ion charge state')
    return value

def run_composition(inputs, *, asset_loader):
    """Solve local quasineutrality by repeated calls to the emitted moment leaf."""
    if not isinstance(inputs, dict):
        raise ValueError('inputs must be a mapping')
    required = {'b_t', 'psi', 'mass_kg', 'charge_c', 'density_ref_m3', 'temperature_parallel_j', 'temperature_perpendicular_ref_j', 'b_ref_t', 'electron_temperature_j'}
    missing = sorted((key for key in required if key not in inputs))
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    if inputs['mass_kg'] <= 0.0 or inputs['charge_c'] <= 0.0:
        raise ValueError('this closure requires one positive ion species')
    tolerance = _require_finite_scalar(inputs.get('potential_tolerance_v'), 'potential_tolerance_v', 1e-08)
    residual_tolerance = _require_finite_scalar(inputs.get('quasineutral_tolerance'), 'quasineutral_tolerance', 1e-10)
    max_iterations = _require_integer_scalar(inputs.get('max_iterations'), 'max_iterations', 100, minimum=1)
    bracket_thermal = _require_finite_scalar(inputs.get('initial_bracket_thermal'), 'initial_bracket_thermal', 8.0)
    if tolerance <= 0.0 or residual_tolerance <= 0.0 or max_iterations < 1 or (bracket_thermal <= 0.0):
        raise ValueError('invalid quasineutral solver controls')
    b_t, psi = _broadcast_state(inputs['b_t'], inputs['psi'])
    moment_inputs = {key: inputs[key] for key in ('mass_kg', 'charge_c', 'density_ref_m3', 'temperature_parallel_j', 'temperature_perpendicular_ref_j', 'b_ref_t', 'phi_ref_v', 'b_plug_left_t', 'b_plug_right_t', 'phi_plug_left_v', 'phi_plug_right_v', 'loss_cone_refill', 'quadrature_order') if key in inputs}
    temperature_parallel = _field(inputs['temperature_parallel_j'], psi, 'temperature_parallel_j')
    if np.any(temperature_parallel <= 0.0):
        raise ValueError('temperature_parallel_j must be positive')
    moment_inputs['temperature_parallel_j'] = temperature_parallel
    phi_ion_ref = _field(inputs.get('phi_ref_v', 0.0), psi, 'phi_ref_v')
    t_e = _field(inputs['electron_temperature_j'], psi, 'electron_temperature_j')
    if np.any(t_e <= 0.0):
        raise ValueError('electron_temperature_j must be positive')
    z_i = _charge_state(inputs['charge_c'])
    n_i_ref = _field(inputs['density_ref_m3'], psi, 'density_ref_m3')
    reference_density = asset_loader('scirel.closures.quasineutral_reference_density')
    if inputs.get('electron_density_ref_m3') is None:
        n_e_ref = _field(reference_density(n_i_ref, z_i)['electron_density_ref_m3'], psi, 'electron_density_ref_m3')
    else:
        n_e_ref = _field(inputs['electron_density_ref_m3'], psi, 'electron_density_ref_m3')
    phi_e_ref = _field(inputs.get('electron_phi_ref_v', phi_ion_ref), psi, 'electron_phi_ref_v')
    if np.any(n_i_ref < 0.0) or np.any(n_e_ref < 0.0):
        raise ValueError('reference densities cannot be negative')
    if np.any((n_i_ref > 0.0) != (n_e_ref > 0.0)):
        raise ValueError('ion and electron reference densities must be both positive or both zero on each surface for quasineutral solve')
    active = (n_i_ref > 0.0) & (n_e_ref > 0.0)
    moment = asset_loader('scirel.kinetic.mirror_constrained_moments')
    electron_response = asset_loader('scirel.closures.boltzmann_quasineutrality')
    potential_solver = asset_loader('scirel.closures.quasineutral_potential')
    pressure_assembly = asset_loader('scirel.kinetic.mirror_total_pressure')

    def state_at(potential):
        return moment(b_t=b_t, psi=psi, potential_v=potential, **moment_inputs)

    def electron_state(potential, ion_density):
        return electron_response(potential_v=potential, electron_temperature_j=t_e, electron_density_ref_m3=n_e_ref, electron_phi_ref_v=phi_e_ref, ion_density_m3=ion_density, ion_charge_state=z_i)

    def residual(potential):
        ion = state_at(potential)['density_m3']
        return electron_state(potential, ion)
    solved = potential_solver(phi_ion_ref, temperature_parallel, t_e, inputs['charge_c'], active, residual, potential_tolerance_v=tolerance, quasineutral_tolerance=residual_tolerance, max_iterations=max_iterations, initial_bracket_thermal=bracket_thermal)
    if not solved.get('converged', False):
        raise RuntimeError('terminal quasineutral solve did not converge')
    potential = solved['potential_v']
    ion = state_at(potential)
    electrons = electron_state(potential, ion['density_m3'])
    terminal_residual = np.asarray(electrons['logarithmic_charge_residual'], dtype=float)
    if not np.all(np.isfinite(terminal_residual)) or np.any(np.abs(terminal_residual[active]) > residual_tolerance):
        raise RuntimeError('terminal quasineutral state does not meet the declared residual tolerance')
    state = pressure_assembly(ion, electrons)
    state.update({'electrostatic_potential': potential, 'iterations': solved['iterations'], 'converged': solved['converged']})
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
        boundary.
    **kwargs
        Named inputs merged with ``inputs`` by the composition
        boundary.

    Returns
    -------
    dict
        Final ion/electron pressures and densities, electrostatic potential,
        relative charge residual, nested ``kinetic_moments`` and solver
        status fields. Array outputs follow the ``psi`` sample shape.

    Raises
    ------
    ValueError
        If required fields, profiles, reference-density masks, plug inputs or
        solver controls are invalid.
    RuntimeError
        If the bounded potential solve fails to bracket or converge, or the
        reevaluated terminal residual exceeds its declared tolerance.
    """
    from scirel._composition import compose
    from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state as _dependency_0
    from scirel.closures.quasineutral_potential import solve_quasineutral_potential as _dependency_1
    from scirel.closures.quasineutral_reference_density import compute_reference_electron_density as _dependency_2
    from scirel.kinetic.mirror_constrained_moments import evaluate_mirror_constrained_moments as _dependency_3
    from scirel.kinetic.mirror_total_pressure import assemble_mirror_total_pressure as _dependency_4
    return compose(run_composition, inputs, kwargs, {'asset_loader': {'scirel.closures.boltzmann_quasineutrality': _dependency_0, 'scirel.closures.quasineutral_potential': _dependency_1, 'scirel.closures.quasineutral_reference_density': _dependency_2, 'scirel.kinetic.mirror_constrained_moments': _dependency_3, 'scirel.kinetic.mirror_total_pressure': _dependency_4}})
__all__ = ['solve_mirror_quasineutral_closure']
