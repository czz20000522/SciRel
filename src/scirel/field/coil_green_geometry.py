"""Observation geometry for the scalar axisymmetric filament Green form."""

from __future__ import annotations

import numpy as np

SOURCE_AXIS_OFFSET_M = 1.0e-8


def compute_axisymmetric_coil_modulus(
    observation_radius_m, observation_z_m, coil_radius_m, coil_z_m
):
    """Return the offset observation radius, ``m`` and the Green distance.

    Parameters
    ----------
    observation_radius_m : real scalar
        Finite nonnegative raw observation radius [m].
    observation_z_m : real scalar
        Finite observation height [m].
    coil_radius_m : array_like, shape (ncoil,)
        Finite strictly positive circular-coil radii [m].
    coil_z_m : array_like, shape (ncoil,)
        Finite coil heights [m], matching ``coil_radius_m``.

    Returns
    -------
    regularized_radius_m : float
        Raw radius plus the fixed ``1e-8`` axis offset [m].
    modulus_squared : ndarray
        Per-coil elliptic parameter ``m = 4*R*a / ((R+a)**2 + (Z-z)**2)``
        [dimensionless]. Coincident rings can produce ``m = 1`` here.
    distance_m : ndarray
        Per-coil distance ``sqrt((R+a)**2 + (Z-z)**2)`` [m].

    Raises
    ------
    ValueError
        If the coordinates are invalid, coil vectors are not aligned and
        finite with positive radii, distance/modulus becomes nonfinite, or
        the modulus underflows to zero.

    See Also
    --------
    evaluate_filament_coil_green_field : Use the already offset radius for fields.
    evaluate_complete_elliptic_integrals : Evaluate the standalone approximation.

    Notes
    -----
    The radius offset is applied exactly once. This function computes geometry;
    it does not reject a coincident ring's ``m = 1``. The field response rejects
    that singular geometry.

    References
    ----------
    See the defining geometry expression in Notes and the returned entries.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.field import compute_axisymmetric_coil_modulus
    >>> radius, modulus, distance = compute_axisymmetric_coil_modulus(
    ...     0.3, 0.0, np.array([0.2, 0.2]), np.array([-0.1, 0.1]))
    >>> assert radius == 0.3 + 1e-8
    >>> assert np.all((modulus > 0.0) & (modulus <= 1.0))
    >>> assert np.all(distance > 0.0)
    """
    raw_radius = float(observation_radius_m)
    radius = raw_radius + SOURCE_AXIS_OFFSET_M
    coil_radius = np.asarray(coil_radius_m, dtype=float)
    coil_z = np.asarray(coil_z_m, dtype=float)
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError("observation coordinates must be finite after source axis offset")
    if raw_radius < 0.0:
        raise ValueError("observation_radius_m must be nonnegative")
    if (
        coil_radius.ndim != 1
        or coil_z.shape != coil_radius.shape
        or np.any(coil_radius <= 0.0)
        or not np.all(np.isfinite(coil_radius))
        or not np.all(np.isfinite(coil_z))
    ):
        raise ValueError(
            "coil radii/z coordinates must be finite same-shape vectors with positive radii"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        denominator = (radius + coil_radius) ** 2 + (observation_z_m - coil_z) ** 2
        modulus_squared = 4.0 * radius * coil_radius / denominator
        distance = np.sqrt(denominator)
    if not np.all(np.isfinite(modulus_squared)) or not np.all(np.isfinite(distance)):
        raise ValueError("coil geometry overflowed to non-finite modulus/distance")
    if np.any(modulus_squared <= 0.0):
        raise ValueError("coil modulus underflowed to zero")
    return radius, modulus_squared, distance


__all__ = ["compute_axisymmetric_coil_modulus"]
