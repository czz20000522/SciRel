"""Scalar closed-form Green response for a collection of circular coils."""

from __future__ import annotations

import numpy as np

from scirel.electromagnetism.greens import compute_greens

MU0_OVER_2PI = 2.0e-7


def evaluate_filament_coil_green_field(
    regularized_radius_m,
    observation_z_m,
    coil_radius_m,
    coil_z_m,
    current_a,
    turns,
):
    """Return summed ``(psi, B_R, B_Z)`` for aligned coil arrays.

    ``regularized_radius_m`` is already offset by the geometry operator.  The
    response therefore applies no second axis shift.  Coincident rings are
    singular and rejected before any nonfinite response can escape.

    The per-ring response comes from
    :func:`scirel.electromagnetism.compute_greens`, the canonical
    circular-filament kernel.  That kernel uses a small-modulus
    hypergeometric branch below ``m = 0.5`` and the complementary elliptic
    form above it, so the flux and radial field stay accurate near the
    cylindrical axis where the ``(2-m)K-2E`` combination cancels (issue #10
    item 4).  Reusing it also removes a second, independent implementation of
    the same Green relation; the remaining duplicate between ``field`` and
    ``electromagnetism`` is tracked in #155.

    Parameters
    ----------
    regularized_radius_m : real scalar
        Finite strictly positive observation radius [m], already offset by
        ``compute_axisymmetric_coil_modulus``.
    observation_z_m : real scalar
        Finite observation height [m].
    coil_radius_m : array_like, shape (ncoil,)
        Finite strictly positive coil radii [m].
    coil_z_m : array_like, shape (ncoil,)
        Finite coil heights [m], matching the coil radii.
    current_a : array_like, shape (ncoil,)
        Finite coil currents [A], matching the coil radii.
    turns : array_like, shape (ncoil,)
        Finite winding multipliers [count], matching the coil radii.

    Returns
    -------
    flux_weber : float
        Summed poloidal flux ``psi = R*A_phi``
        [Wb/rad (per the psi = R A_phi convention; subject to the caller's current units)].
    radial_field_t : float
        Summed radial field [T].
    axial_field_t : float
        Summed axial field [T].

    Raises
    ------
    ValueError
        If observation coordinates or coil vectors are invalid, the target
        coincides with a ring, source weights overflow, or the wrapper's
        returned scalar values are nonfinite.
    FloatingPointError
        If overflow or invalid floating-point arithmetic occurs inside the
        circular-filament kernel. This exception propagates unchanged.

    See Also
    --------
    compute_axisymmetric_coil_modulus : Apply the observation-radius offset once.
    scirel.electromagnetism.compute_greens : Evaluate the circular-filament kernel.

    Notes
    -----
    The current of each source is ``current_a * turns``. Elliptic values are
    computed by the kernel; there are no caller-supplied elliptic inputs.

    References
    ----------
    See ``scirel.electromagnetism.compute_greens`` for the kernel relation.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.field import compute_axisymmetric_coil_modulus, evaluate_filament_coil_green_field
    >>> radius, modulus, _ = compute_axisymmetric_coil_modulus(
    ...     0.3, 0.0, np.array([0.2, 0.2]), np.array([-0.1, 0.1]))
    >>> flux, br, bz = evaluate_filament_coil_green_field(
    ...     radius, 0.0, np.array([0.2, 0.2]), np.array([-0.1, 0.1]),
    ...     np.array([10.0, 10.0]), np.array([2.0, 2.0]))
    >>> assert abs(br) < 1e-18
    >>> flux2, br2, bz2 = evaluate_filament_coil_green_field(
    ...     radius, 0.0, np.array([0.2, 0.2]), np.array([-0.1, 0.1]),
    ...     np.array([20.0, 20.0]), np.array([2.0, 2.0]))
    >>> assert flux2 == 2.0 * flux and bz2 == 2.0 * bz
    """
    radius = float(regularized_radius_m)
    observation_z_m = float(observation_z_m)
    coil_radius, coil_z, current, winding = (
        np.asarray(value, dtype=float) for value in (coil_radius_m, coil_z_m, current_a, turns)
    )
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError(
            "regularized observation coordinates must be finite and positive in radius"
        )
    if any(
        value.ndim != 1 or value.shape != coil_radius.shape for value in (coil_z, current, winding)
    ):
        raise ValueError(
            "coil inputs and elliptic values must be same-shape vectors with valid geometry"
        )
    if not all(
        np.all(np.isfinite(value)) for value in (coil_radius, coil_z, current, winding)
    ) or np.any(coil_radius <= 0.0):
        raise ValueError(
            "coil inputs and elliptic values must be same-shape vectors with valid geometry"
        )
    separation2 = (radius - coil_radius) ** 2 + (observation_z_m - coil_z) ** 2
    if np.any(separation2 <= 0.0):
        raise ValueError("singular coil geometry: observation point on a filament ring")

    sources = np.column_stack((coil_radius, coil_z, winding * current))
    targets = np.array([[radius, observation_z_m]])
    psi, b_r, b_z = compute_greens(sources, targets)
    result = (float(psi[0]), float(b_r[0]), float(b_z[0]))
    if not all(np.isfinite(value) for value in result):
        raise ValueError("filament-coil response overflowed to a non-finite value")
    return result


__all__ = ["evaluate_filament_coil_green_field"]
