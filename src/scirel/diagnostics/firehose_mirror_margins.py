"""SciRel firehose and mirror stability-margin diagnostic."""
import numpy as np
MU0 = 4e-07 * np.pi

def _derivative_with_respect_to_field(quantity, field, floor=1e-30):
    q = np.asarray(quantity, dtype=float).ravel()
    b = np.asarray(field, dtype=float).ravel()
    order = np.argsort(b)
    sorted_b, sorted_q = (b[order], q[order])
    sorted_derivative = np.zeros_like(sorted_q)
    if sorted_b.size > 1 and np.ptp(sorted_b) > floor:
        if np.any(np.diff(sorted_b) <= floor):
            raise ValueError('magnetic_field samples must be unique unless all values are equal')
        sorted_derivative = np.gradient(sorted_q, sorted_b, edge_order=1)
        if not np.all(np.isfinite(sorted_derivative)):
            raise ValueError('the pressure derivative with respect to magnetic_field must be finite')
    derivative = np.empty_like(sorted_derivative)
    derivative[order] = sorted_derivative
    return derivative.reshape(np.shape(field))

def compute_firehose_mirror_margins(p_parallel, p_perp, magnetic_field, mu0=MU0, parallel_equilibrium=None):
    """Return source-defined firehose and mirror stability margins."""
    p_parallel = np.asarray(p_parallel, dtype=float)
    p_perp = np.asarray(p_perp, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError('p_parallel, p_perp, and magnetic_field must have the same shape')
    if not all((np.all(np.isfinite(value)) for value in (p_parallel, p_perp, magnetic_field))):
        raise ValueError('p_parallel, p_perp, and magnetic_field must contain only finite values')
    if not np.isfinite(mu0) or mu0 <= 0.0:
        raise ValueError('mu0 must be positive and finite')
    dpperp_db = _derivative_with_respect_to_field(p_perp, magnetic_field)
    firehose_margin = magnetic_field * magnetic_field / mu0 + p_perp - p_parallel
    mirror_margin = magnetic_field * magnetic_field / mu0 - magnetic_field * dpperp_db
    if not np.all(np.isfinite(firehose_margin)) or not np.all(np.isfinite(mirror_margin)):
        raise ValueError('firehose and mirror margins must be finite')
    parallel_error = None
    max_parallel_error = None
    if parallel_equilibrium is not None:
        if not isinstance(parallel_equilibrium, dict):
            raise ValueError('parallel_equilibrium must be a mapping when provided')
        parallel_error = parallel_equilibrium.get('error')
        max_parallel_error = parallel_equilibrium.get('max_relative_error')
    return {'firehose_margin': firehose_margin, 'mirror_margin': mirror_margin, 'firehose_stable': bool(np.nanmin(firehose_margin) > 0.0), 'mirror_stable': bool(np.nanmin(mirror_margin) > 0.0), 'min_firehose_margin': float(np.nanmin(firehose_margin)), 'min_mirror_margin': float(np.nanmin(mirror_margin)), 'parallel_equilibrium_error': parallel_error, 'max_parallel_equilibrium_error': max_parallel_error}
__all__ = ['compute_firehose_mirror_margins']
