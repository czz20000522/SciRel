"""Velocity--pitch hot-ion moments for Frank--Egedal closure."""
import math
import numpy as np

def _mode_sum(xi0, speed, degrees, coefficients, vc, beta_m, n_terms, fractional_mode):
    u = np.power(np.clip((1.0 + vc ** 3) / (speed ** 3 + vc ** 3) * speed ** 3, 0.0, None), beta_m / 3.0)
    total = np.zeros(np.broadcast_shapes(np.shape(xi0), np.shape(speed)), dtype=float)
    for degree, coefficient in zip(degrees, coefficients):
        total += coefficient * fractional_mode(degree, xi0, n_terms) * np.power(u, degree * (degree + 1.0))
    return total

def evaluate_frank_egedal_hot_ion_moments(magnetic_field, params, degrees, source_coefficients, legendre_terms, fractional_mode):
    """Integrate density and both pressure moments of one common population.

    The default normalized speed interval is [0,1], as in the common-f
    moment definitions of Frank2509.17288v4 Eq16. Its Eq19b prints a
    perpendicular-only vc lower bound, inconsistent with that unchanged
    speed-variable substitution; no author-confirmed erratum is assumed.
    ``velocity_lower`` may select a common truncated population. The legacy
    ``perp_velocity_lower`` is a compatibility alias for this SAME lower
    bound for all three moments, not an independent tensor-component cut.
    Normalization still uses parallel pressure and density at b=1.
    For b<1 the supplied reference population has support only where
    xi>=sqrt(1-b); other orbits cannot reach B0 and are not supplied. The
    modal sum uses its declared nonnegative part, not an unmodified exact
    kinetic solution. With vc=0 the speed factor equals one and density
    diverges logarithmically at a zero lower cutoff; positive lower cutoffs
    remain supported. Empty or zero-normalization populations are rejected.
    Integrable zero-speed powers are factored into a Gauss-Jacobi weight,
    including admissible negative beta. Raw moments are refined before normalization; unresolved or divergent
    quadrature raises RuntimeError. A refinement agreement is a numerical
    estimate, not proof for an arbitrary caller-provided angular callable.
    This reconstruction does not validate a measured plasma population.
    """
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if magnetic_field.ndim != 2 or not np.all(np.isfinite(magnetic_field)):
        raise ValueError('B must be a finite two-dimensional [Z,R] grid')
    reference = float(params.get('B0', np.nanmedian(magnetic_field)))
    if not np.isfinite(reference) or reference <= 0.0 or np.any(magnetic_field <= 0.0):
        raise ValueError('B and B0 must be finite and strictly positive')
    normalized_field = magnetic_field / reference
    if not np.all(np.isfinite(normalized_field)) or np.any(normalized_field <= 0.0):
        raise ValueError('B/B0 must be representable as finite positive numbers')
    mirror_ratio = float(params.get('mirror_ratio', params.get('turning_b', 2.0)))
    if not np.isfinite(mirror_ratio) or mirror_ratio <= 1.0:
        raise ValueError('mirror_ratio must be finite and greater than one')
    xi_tp_mid = math.sqrt(1.0 - 1.0 / mirror_ratio)
    vc = float(params.get('vc_over_v0', 0.25))
    if not np.isfinite(vc) or vc < 0.0:
        raise ValueError('vc_over_v0 must be finite and nonnegative')
    lower = float(params.get('velocity_lower', params.get('perp_velocity_lower', 0.0)))
    if not np.isfinite(lower) or not 0.0 <= lower < 1.0:
        raise ValueError('velocity_lower must be finite and in [0,1)' )
    if 'velocity_lower' in params and 'perp_velocity_lower' in params and float(params['perp_velocity_lower']) != lower:
        raise ValueError('velocity_lower and legacy perp_velocity_lower must select the same population')
    if vc == 0.0 and lower == 0.0:
        raise ValueError('zero critical speed and zero lower cutoff give a divergent density; normalization is undefined')
    beta_m = float(params.get('beta_m', params.get('zeff', 1.0) / 2.0))
    velocity_nodes = int(params.get('velocity_nodes', 24))
    pitch_nodes = int(params.get('pitch_nodes', 24))
    if not np.isfinite(beta_m) or velocity_nodes < 2 or pitch_nodes < 2:
        raise ValueError('beta_m must be finite and quadrature nodes must be at least two')
    degrees, source_coefficients = (np.asarray(degrees, dtype=float), np.asarray(source_coefficients, dtype=float))
    if degrees.ndim != 1 or degrees.size == 0 or np.any(degrees < 0) or source_coefficients.shape != degrees.shape or (not np.all(np.isfinite(degrees))) or (not np.all(np.isfinite(source_coefficients))):
        raise ValueError('degrees and source_coefficients must be finite one-dimensional arrays of equal length')

    quadrature_rtol = float(params.get('quadrature_rtol', 1e-7))
    max_nodes = int(params.get('max_quadrature_nodes', max(768,2*max(velocity_nodes,pitch_nodes))))
    if not np.isfinite(quadrature_rtol) or quadrature_rtol <= 0 or max_nodes < 2*max(velocity_nodes,pitch_nodes):
        raise ValueError('quadrature_rtol must be positive and max_quadrature_nodes permit a refinement')
    active_powers = beta_m*degrees[source_coefficients != 0]*(degrees[source_coefficients != 0]+1)
    leading_power = float(np.min(active_powers)) if active_powers.size else 0.0
    weighted_endpoint = vc > 0.0 and lower == 0.0 and leading_power > -3.0
    def integrals(b, nv, nx):
        xi_tp_loc = math.sqrt(max(0.0, 1.0 - float(b) / max(mirror_ratio, 1e-12)))
        if xi_tp_loc <= 0.0 or xi_tp_mid <= 0.0:
            return (0.0, 0.0, 0.0)
        # Keep the public kinetic namespace dependency-light.  All input
        # validation above must complete before importing the quadrature
        # backend; invalid calls therefore preserve their old rejection
        # order without importing SciPy.  The guard above also avoids the
        # import when this field has no admissible pitch interval.
        from scipy.special import roots_jacobi, roots_legendre

        if weighted_endpoint:
            # Factor the exact small-speed density power v^(2+leading).
            # Gauss-Jacobi resolves integrable singularities near leading=-3
            # without evaluating an overflowing f and vanishing v² separately.
            speed_nodes, speed_weights = roots_jacobi(nv,0.0,2.0+leading_power)
            speed, speed_weights = .5*(speed_nodes+1.0), speed_weights/2.0**(3.0+leading_power)
        else:
            speed_nodes, speed_weights = roots_legendre(nv)
            speed, speed_weights = (0.5 * ((1.0-lower)*speed_nodes + 1.0+lower), 0.5*(1.0-lower)*speed_weights)
        pitch_nodes_raw, pitch_weights = roots_legendre(nx)
        # A distribution specified at B0 only supplies orbits reaching B0.
        # For b<1, xi²<1-b would make the invariant xi0 imaginary.
        xi_lower = math.sqrt(max(0.0, 1.0-b))
        xi, pitch_weights = (.5*((xi_tp_loc-xi_lower)*pitch_nodes_raw+xi_tp_loc+xi_lower), .5*(xi_tp_loc-xi_lower)*pitch_weights)
        speed_2d, xi_2d = (speed[:, None], xi[None, :])
        xi0 = np.sqrt(np.clip((xi_2d * xi_2d - (1.0 - b)) / b, 0.0, xi_tp_mid * xi_tp_mid))
        if weighted_endpoint:
            total = np.zeros((nv,nx))
            logc = np.log((1.0+vc**3)/(speed_2d**3+vc**3))
            for degree,coefficient in zip(degrees,source_coefficients):
                if coefficient == 0.0:
                    continue
                power = beta_m*degree*(degree+1)
                total += coefficient*fractional_mode(degree,xi0,legendre_terms)*np.exp((power/3.)*logc+(power-leading_power)*np.log(speed_2d))
            distribution = np.maximum(total/(speed_2d**3+vc**3),0.0)
            density_factor,pressure_factor = 1.0,speed_2d**2
        else:
            distribution = np.maximum(_mode_sum(xi0, speed_2d, degrees, source_coefficients, vc, beta_m, legendre_terms, fractional_mode) / (speed_2d ** 3 + vc ** 3), 0.0)
            density_factor,pressure_factor = speed_2d**2,speed_2d**4
        if not np.all(np.isfinite(distribution)):
            raise FloatingPointError('reference population distribution is not finite at quadrature nodes')
        weights = speed_weights[:, None] * pitch_weights[None, :]
        parallel = 4.0 * math.pi * np.sum(weights * pressure_factor * xi_2d ** 2 * distribution)
        density = 4.0 * math.pi * np.sum(weights * density_factor * distribution)
        perpendicular = 2.0 * math.pi * np.sum(weights * pressure_factor * (1.0-xi_2d ** 2) * distribution)
        return tuple((float(max(value, 0.0)) for value in (parallel, perpendicular, density)))
    fields = np.unique(np.r_[normalized_field.ravel(),1.0])
    nv, nx = velocity_nodes, pitch_nodes
    previous = np.asarray([integrals(float(b),nv,nx) for b in fields])
    # Compare RAW moments, not normalized ratios: a divergent reference
    # moment can otherwise cancel algebraically and appear converged.
    for refinement in range(32):
        nv, nx = min(2*nv,max_nodes), min(2*nx,max_nodes)
        current = np.asarray([integrals(float(b),nv,nx) for b in fields])
        reference = current[np.searchsorted(fields,1.0)]
        scales = np.maximum(np.maximum(np.abs(current),np.abs(previous)), np.abs(reference)*1e-12)
        differences = np.abs(current-previous)
        if np.all(np.isfinite(current)) and np.all(differences <= quadrature_rtol*scales):
            break
        if nv == max_nodes and nx == max_nodes:
            raise RuntimeError('hot-ion raw-moment quadrature did not converge; population may be nonintegrable or unresolved')
        previous = current
    else:
        raise RuntimeError('hot-ion raw-moment quadrature refinement limit reached')
    midplane = current[np.searchsorted(fields,1.0)]
    if not np.all(np.isfinite(midplane)) or midplane[0] <= 0.0 or midplane[2] <= 0.0:
        raise ValueError('reference population must have finite positive parallel pressure and density')
    values = current[np.searchsorted(fields,normalized_field.ravel())]
    parallel, perpendicular, density = (values[:,index].reshape(normalized_field.shape) for index in range(3))
    return {'normalized_field': normalized_field, 'xi_tp_mid': xi_tp_mid, 'hot_parallel_shape': parallel / midplane[0], 'hot_perpendicular_shape': perpendicular / midplane[0], 'hot_density_shape': density / midplane[2], 'quadrature': {'velocity_nodes': velocity_nodes, 'pitch_nodes': pitch_nodes}, 'reference_raw_moments':{'parallel':float(midplane[0]),'perpendicular':float(midplane[1]),'density':float(midplane[2])}, 'quadrature_convergence': {'velocity_nodes':nv,'pitch_nodes':nx,'relative_tolerance':quadrature_rtol,'raw_moments_checked':True,'velocity_rule':'jacobi_factored_density_power' if weighted_endpoint else 'legendre','factored_density_power':2.0+leading_power if weighted_endpoint else None}, 'velocity_domain': {'lower': lower, 'upper': 1.0, 'common_to_density_and_both_pressures': True}}
__all__ = ['evaluate_frank_egedal_hot_ion_moments']
