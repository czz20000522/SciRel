"""Linear current-weighted flux and poloidal-field superposition."""
import numpy as np

def superpose_current_green_field(currents, gpsi, gBR, gBZ):
    """Apply the SciRel rank-1/rank-2 current-to-Green contraction."""
    current = np.asarray(currents, dtype=float)
    responses = [np.asarray(value, dtype=float) for value in (gpsi, gBR, gBZ)]
    if not np.all(np.isfinite(current)) or any((not np.all(np.isfinite(value)) for value in responses)):
        raise ValueError('currents and Green responses must contain only finite values')
    if current.ndim == 0:
        if any((value.ndim != 1 or value.shape != responses[0].shape for value in responses)):
            raise ValueError('scalar current requires same-shape one-dimensional Green responses')
        return {'psi': current * responses[0], 'BR': current * responses[1], 'BZ': current * responses[2]}
    if current.ndim == 1:
        if any((value.ndim != 2 or value.shape != responses[0].shape for value in responses)):
            raise ValueError('vector currents require same-shape two-dimensional Green responses')
        if responses[0].shape[0] != current.size:
            raise ValueError('Green source axis must equal the number of currents')
        return {'psi': current @ responses[0], 'BR': current @ responses[1], 'BZ': current @ responses[2]}
    raise ValueError('currents must be a scalar or one-dimensional vector')
__all__ = ['superpose_current_green_field']
