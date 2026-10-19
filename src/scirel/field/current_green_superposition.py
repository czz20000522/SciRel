"""Current-weighted contraction of ordered Green responses."""
import numpy as np


def superpose_current_green_field(currents, gpsi, gBR, gBZ):
    """Contract one scalar or a source vector with three Green arrays.

    A scalar current consumes one-dimensional response vectors.  A current
    vector consumes matrices whose first axis is the source-set axis; the
    final axis is left untouched by the matrix product.
    """
    current = np.asarray(currents, dtype=float)
    responses = tuple(np.asarray(value, dtype=float) for value in (gpsi, gBR, gBZ))
    if not np.all(np.isfinite(current)) or any(not np.all(np.isfinite(v)) for v in responses):
        raise ValueError("currents and Green responses must contain only finite values")
    if current.ndim == 0:
        if any(v.ndim != 1 or v.shape != responses[0].shape for v in responses):
            raise ValueError("scalar current requires same-shape one-dimensional Green responses")
        return {name: current * value for name, value in zip(("psi", "BR", "BZ"), responses)}
    if current.ndim == 1:
        if any(v.ndim != 2 or v.shape != responses[0].shape for v in responses):
            raise ValueError("vector currents require same-shape two-dimensional Green responses")
        if responses[0].shape[0] != current.size:
            raise ValueError("Green source axis must equal the number of currents")
        return {name: current @ value for name, value in zip(("psi", "BR", "BZ"), responses)}
    raise ValueError("currents must be a scalar or one-dimensional vector")


__all__ = ["superpose_current_green_field"]
