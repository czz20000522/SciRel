"""Pointwise firehose margin from the maintained combined diagnostic.

The pending intake at 647d5db keeps this relation separate so one-sample and
duplicate-field calls do not request the combined diagnostic's mirror branch.
"""
import numpy as np
MU0 = 4e-07 * np.pi

def compute_pointwise_firehose_margin(p_parallel, p_perp, magnetic_field, mu0=MU0):
    """Return the pointwise firehose margin B^2/mu0 + p_perp - p_parallel in Pa."""
    p_parallel = np.asarray(p_parallel, dtype=float)
    p_perp = np.asarray(p_perp, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError('p_parallel, p_perp, and magnetic_field must have the same shape')
    if p_parallel.size == 0:
        raise ValueError('p_parallel, p_perp, and magnetic_field must be nonempty')
    if not all((np.all(np.isfinite(value)) for value in (p_parallel, p_perp, magnetic_field))):
        raise ValueError('p_parallel, p_perp, and magnetic_field must contain only finite values')
    if np.ndim(mu0) != 0 or isinstance(mu0, (list, tuple, np.ndarray)):
        raise ValueError('mu0 must be a scalar')
    if not np.isfinite(mu0) or mu0 <= 0.0:
        raise ValueError('mu0 must be positive and finite')
    with np.errstate(over='ignore', invalid='ignore'):
        firehose_margin = magnetic_field * magnetic_field / float(mu0) + p_perp - p_parallel
    if not np.all(np.isfinite(firehose_margin)):
        raise ValueError('the pointwise firehose margin must be finite')
    return {'firehose_margin': firehose_margin}
__all__ = ['compute_pointwise_firehose_margin', 'MU0']
