"""Current-weighted contraction of ordered Green responses."""

import numpy as np

from scirel._result import Result


def superpose_current_green_field(currents, gpsi, gBR, gBZ):
    """Contract currents with ordered Green arrays as a named result.

    A scalar current consumes one-dimensional response vectors.  A current
    vector consumes matrices with one target row per output point and one
    source column per current; the contraction runs along the source columns
    and preserves target order.  A contraction that is not representable as
    finite float64 raises :class:`FloatingPointError` instead of returning a
    non-finite field.

    Parameters
    ----------
    currents : real array-like, shape scalar or [N_source]
        One drive current or one current per response source column [A].
        Finite; rank must be zero or one.
    gpsi : real array-like, shape [N_target] or [N_target,N_source]
        Flux Green response with target rows and source columns [Wb/rad/A].
        Finite and shape-compatible with currents and the other responses;
        the second axis must equal ``currents.size``.
    gBR : real array-like, shape [N_target] or [N_target,N_source]
        Radial-field Green response with target rows and source columns [T/A].
        Finite and the same shape as ``gpsi``.
    gBZ : real array-like, shape [N_target] or [N_target,N_source]
        Axial-field Green response with target rows and source columns [T/A].
        Finite and the same shape as ``gpsi``.

    Returns
    -------
    psi : ndarray of float64, shape [N_target]
        Field ``psi`` of the returned ``scirel._result.Result`` mapping:
        current-weighted flux [Wb/rad], preserving target row order.
    BR : ndarray of float64, shape [N_target]
        Field ``BR`` of the returned result mapping: current-weighted radial
        field [T], preserving target row order.
    BZ : ndarray of float64, shape [N_target]
        Field ``BZ`` of the returned result mapping: current-weighted axial
        field [T], preserving target row order.

    Raises
    ------
    ValueError
        If values are nonfinite, currents have unsupported rank, or response
        shapes are incompatible.
    FloatingPointError
        If the scalar or matrix contraction is not representable as finite
        float64.

    See Also
    --------
    scirel.field.circular_filament_green_response : Per-filament Green response.
    scirel.field.solve_multi_coil_vacuum_field : Multi-coil field composition.

    Notes
    -----
    The three fields are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import superpose_current_green_field
    >>> result = superpose_current_green_field(
    ...     [2.0, -1.0],
    ...     [[1.0, 4.0], [3.0, 5.0]],
    ...     [[2.0, 0.0], [1.0, 6.0]],
    ...     [[-1.0, 3.0], [2.0, 4.0]],
    ... )
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['psi', 'BR', 'BZ']
    >>> assert result.psi is result['psi']
    >>> np.testing.assert_allclose(result['psi'], [-2.0, 1.0])
    >>> np.testing.assert_allclose(result['BR'], [4.0, -4.0])
    >>> np.testing.assert_allclose(result['BZ'], [-5.0, 0.0])
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
    return Result(result)


__all__ = ["superpose_current_green_field"]
