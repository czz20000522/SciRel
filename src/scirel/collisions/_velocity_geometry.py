"""Local geometry kernels shared by the atomic and molecular SIG assemblers."""

from __future__ import annotations

import numpy as np


def predecessor_state(vr, vx, radial_weight, axial_width, n_theta):
    """Build pairwise relative-speed tensors on the cylindrical velocity grid."""
    theta = np.pi * (np.arange(n_theta, dtype=float) + 0.5) / n_theta
    radial_i = vr[:, None, None, None, None]
    radial_k = vr[None, None, :, None, None]
    delta_axial = vx[None, :, None, None, None] - vx[None, None, None, :, None]
    radial_part = (
        radial_i**2
        + radial_k**2
        - 2.0 * radial_i * radial_k * np.cos(theta)[None, None, None, None, :]
    )
    relative_speed_squared = radial_part + delta_axial**2
    signed_stress = radial_part - 2.0 * delta_axial**2
    relative_speed = np.sqrt(relative_speed_squared)
    shape = (vr.size, vx.size, vr.size, vx.size)
    axial_difference = np.broadcast_to(
        vx[None, :, None, None] - vx[None, None, None, :], shape
    ).copy()
    quadrature_weight = np.broadcast_to(
        radial_weight[None, None, :, None] * axial_width[None, None, None, :], shape
    ).copy()
    return (
        relative_speed_squared,
        relative_speed,
        signed_stress,
        axial_difference,
        quadrature_weight,
    )


def averaged_matrix(kernel, weight, angular_weights, matrix_size):
    """Average an angular kernel and restore Fortran velocity ordering."""
    flattened = np.asarray(kernel).reshape(
        (matrix_size * matrix_size, angular_weights.size), order="F"
    )
    angular_average = (flattened @ angular_weights).reshape(weight.shape, order="F")
    return (weight * angular_average).reshape((matrix_size, matrix_size), order="F")
