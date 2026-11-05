"""Current-weighted contraction of ordered Green responses."""

import numpy as np


def superpose_current_green_field(currents, gpsi, gBR, gBZ):
    """Contract one scalar or a source vector with three Green arrays.

    A scalar current consumes one-dimensional response vectors.  A current
    vector consumes matrices with one target row per output point and one
    source column per current; the contraction runs along the source columns
    and preserves target order.  A contraction that is not representable as
    finite float64 raises :class:`FloatingPointError` instead of returning a
    non-finite field.
    """
    current = np.asarray(currents, dtype=float)
    responses = tuple(np.asarray(value, dtype=float) for value in (gpsi, gBR, gBZ))
    if not np.all(np.isfinite(current)) or any(not np.all(np.isfinite(v)) for v in responses):
        raise ValueError("currents and Green responses must contain only finite values")
    try:
        with np.errstate(over="raise", invalid="raise"):
            if current.ndim == 0:
                if any(v.ndim != 1 or v.shape != responses[0].shape for v in responses):
                    raise ValueError(
                        "scalar current requires same-shape one-dimensional Green responses"
                    )
                result = {
                    name: current * value for name, value in zip(("psi", "BR", "BZ"), responses)
                }
            elif current.ndim == 1:
                if any(v.ndim != 2 or v.shape != responses[0].shape for v in responses):
                    raise ValueError(
                        "vector currents require same-shape two-dimensional Green responses"
                    )
                if responses[0].shape[1] != current.size:
                    raise ValueError(
                        "Green source axis (columns) must equal the number of currents"
                    )
                result = {
                    name: value @ current for name, value in zip(("psi", "BR", "BZ"), responses)
                }
            else:
                raise ValueError("currents must be a scalar or one-dimensional vector")
    except FloatingPointError as error:
        raise FloatingPointError(
            "current-weighted Green response is not representable as finite float64"
        ) from error
    if any(not np.all(np.isfinite(value)) for value in result.values()):
        raise FloatingPointError(
            "current-weighted Green response is not representable as finite float64"
        )
    return result


__all__ = ["superpose_current_green_field"]
