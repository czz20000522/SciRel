"""Per-source axisymmetric Green response matrices."""

from __future__ import annotations

import numpy as np

from scirel._result import Result
from scirel.electromagnetism.greens import green_response_matrices


def dense_axisymmetric_green_response(rz_pts, source_rzw):
    """Return dense target/source Green matrices as a named result.

    Parameters
    ----------
    rz_pts : real array-like, shape [N_target,2]
        Target rows ``[R_m, Z_m]`` in [m,m]. Finite with nonnegative target
        radii; an empty target list must retain the two-column shape.
    source_rzw : real array-like, shape [N_source,3]
        Source rows ``[R0_m, Z0_m, weight]`` in [m,m,dimensionless]. Finite
        with nonnegative source radii; ``[]`` is accepted as an empty-source
        shorthand.

    Returns
    -------
    gpsi : ndarray of float64, shape [N_target,N_source]
        Field ``gpsi`` of the returned ``scirel._result.Result`` mapping:
        weighted ``psi=R A_phi`` response for each target/source pair
        [Wb/rad/A].
    gBR : ndarray of float64, shape [N_target,N_source]
        Field ``gBR`` of the returned result mapping: weighted radial-field
        response for each target/source pair [T/A].
    gBZ : ndarray of float64, shape [N_target,N_source]
        Field ``gBZ`` of the returned result mapping: weighted axial-field
        response for each target/source pair [T/A].

    Raises
    ------
    ValueError
        If target/source arrays are malformed, complex, nonfinite, or have
        negative radii.
    FloatingPointError
        If the kernel produces a nonfinite response.

    See Also
    --------
    scirel.field.circular_filament_green_response : Per-filament response.
    scirel.field.build_mirror_plasma_flux_green : Mirror-grid flux matrix.

    Notes
    -----
    The three matrices are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import dense_axisymmetric_green_response
    >>> targets = [[0.0, -0.1], [0.2, 0.15]]
    >>> result = dense_axisymmetric_green_response(
    ...     targets, [[0.35, -0.1, 1.0]]
    ... )
    >>> weighted = dense_axisymmetric_green_response(
    ...     targets, [[0.35, -0.1, -2.5]]
    ... )
    >>> empty = dense_axisymmetric_green_response(targets, [])
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['gpsi', 'gBR', 'gBZ']
    >>> assert result.gpsi is result['gpsi']
    >>> for name in ('gpsi', 'gBR', 'gBZ'):
    ...     assert result[name].shape == (2, 1)
    ...     np.testing.assert_allclose(weighted[name], -2.5 * result[name])
    ...     assert empty[name].shape == (2, 0)
    """
    if np.iscomplexobj(rz_pts) or np.iscomplexobj(source_rzw):
        raise ValueError("target/source coordinates and weights must be real")
    targets = np.asarray(rz_pts, dtype=float)
    sources = np.asarray(source_rzw, dtype=float)
    if sources.shape == (0,):
        sources = np.empty((0, 3), dtype=float)
    if targets.ndim != 2 or targets.shape[1] != 2:
        raise ValueError("rz_pts must have shape (n_targets, 2)")
    if sources.ndim != 2 or sources.shape[1] != 3:
        raise ValueError("source_rzw must have shape (n_sources, 3)")
    if not np.all(np.isfinite(targets)) or not np.all(np.isfinite(sources)):
        raise ValueError("rz_pts and source_rzw must contain only finite values")
    if np.any(targets[:, 0] < 0.0) or np.any(sources[:, 0] < 0.0):
        raise ValueError("cylindrical radii must be nonnegative")
    gpsi, gbr, gbz = green_response_matrices(targets, sources)
    return Result({"gpsi": gpsi, "gBR": gbr, "gBZ": gbz})


__all__ = ["dense_axisymmetric_green_response"]
