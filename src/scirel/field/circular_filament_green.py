"""Aggregate weighted circular-filament field responses."""

import numpy as np

from scirel._result import Result
from scirel.electromagnetism.greens import compute_greens


def circular_filament_green_response(rzw, rz_pts):
    """Sum ordered weighted ring responses as a named result.

    Rows with zero radius or zero weight are inactive.  Positive-radius exact
    source/target coincidences retain the discrete zero-self convention.  The
    returned values are per ampere: ``gpsi`` is Wb/rad, and ``gBR``/``gBZ``
    are tesla.

    Parameters
    ----------
    rzw : real array-like, shape [N_filament,3]
        Source rows ``[R_m, Z_m, weight]`` in [m,m,dimensionless]. Finite with
        nonnegative source radii; an empty source set is allowed.
    rz_pts : real array-like, shape [N_point,2]
        Target rows ``[R_m, Z_m]`` in [m,m]. Finite with nonnegative target
        radii.

    Returns
    -------
    gpsi : ndarray of float64, shape [N_point]
        Field ``gpsi`` of the returned ``scirel._result.Result`` mapping:
        flux response per drive current [Wb/rad/A].
    gBR : ndarray of float64, shape [N_point]
        Field ``gBR`` of the returned result mapping: radial-field response
        per drive current [T/A].
    gBZ : ndarray of float64, shape [N_point]
        Field ``gBZ`` of the returned result mapping: axial-field response per
        drive current [T/A].

    Raises
    ------
    ValueError
        If source or target arrays are malformed, complex, nonfinite, or have
        negative radii.
    FloatingPointError
        If the summed finite response is not representable.

    See Also
    --------
    scirel.electromagnetism.compute_greens : Circular-filament Green kernel.
    scirel.field.dense_axisymmetric_green_response : Dense response matrices.

    Notes
    -----
    The three arrays are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import circular_filament_green_response
    >>> result = circular_filament_green_response(
    ...     [[0.35, 0.0, 1.0]], [[0.2, -0.1], [0.2, 0.1]]
    ... )
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['gpsi', 'gBR', 'gBZ']
    >>> assert result.gpsi is result['gpsi']
    >>> for value in result.values():
    ...     assert value.shape == (2,)
    ...     assert np.isfinite(value).all()
    """
    if np.iscomplexobj(rzw) or np.iscomplexobj(rz_pts):
        raise ValueError("source and target coordinates/weights must be real")
    sources = np.asarray(rzw, dtype=float)
    if sources.size == 0:
        sources = np.empty((0, 3), dtype=float)
    targets = np.asarray(rz_pts, dtype=float)
    if sources.ndim != 2 or sources.shape[1] != 3:
        raise ValueError("rzw must have shape (n_filaments, 3)")
    if targets.ndim != 2 or targets.shape[1] != 2:
        raise ValueError("rz_pts must have shape (n_points, 2)")
    if not np.all(np.isfinite(sources)) or not np.all(np.isfinite(targets)):
        raise ValueError("rzw and rz_pts must contain only finite values")
    if np.any(sources[:, 0] < 0.0) or np.any(targets[:, 0] < 0.0):
        raise ValueError("source and target cylindrical radii must be nonnegative")

    response = np.zeros((3, len(targets)), dtype=float)
    for source in sources:
        if source[0] == 0.0 or source[2] == 0.0:
            continue
        off_self = ~((targets[:, 0] == source[0]) & (targets[:, 1] == source[1]))
        if np.any(off_self):
            values = compute_greens(source[None, :], targets[off_self])
            response[:, off_self] += np.asarray(values)
    if not np.all(np.isfinite(response)):
        raise FloatingPointError("circular filament response is not representable")
    return Result(zip(("gpsi", "gBR", "gBZ"), response))


__all__ = ["circular_filament_green_response"]
