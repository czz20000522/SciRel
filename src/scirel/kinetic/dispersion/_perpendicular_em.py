"""Finite-harmonic perpendicular Maxwell pencil assembly.

The local assembly keeps the full Maxwell constant and represents each
nonzero harmonic by a three-component current block. The six final state
entries are the physical electric and magnetic fields. SciPy is imported only
when a valid numeric call reaches the sparse matrix construction.
"""

import numpy as np


def _component_tuple(component):
    names = ("gyro", "wp2", "vtz", "vtp", "drift", "weight")
    values = tuple(float(component[name]) for name in names)
    if (
        not np.isfinite(values).all()
        or values[0] == 0
        or min(values[1:4]) <= 0
    ):
        raise ValueError("finite physical Gaussian component required")
    return values


def _add_block(blocks, pole, block):
    blocks[pole] = blocks.get(pole, np.zeros((3, 3), complex)) + block


def perpendicular_maxwell_pencil(*, components, kx, N, c2):
    """Assemble the exact perpendicular finite-harmonic Maxwell pencil."""

    if (
        not np.isfinite(kx)
        or int(N) != N
        or N < 0
        or not np.isfinite(c2)
        or c2 <= 0
    ):
        raise ValueError("finite kx,integer N>=0,positive c² required")

    normalized = [_component_tuple(component) for component in components]
    from scipy import sparse

    if kx != 0:
        from scipy.special import ive

    blocks = {}
    total_wp2 = 0.0
    for gyro, wp2, vtz, vtp, drift, weight in normalized:
        total_wp2 += weight * wp2
        if kx == 0:
            # The uniform-field limit has fundamental gyro poles even when
            # the requested harmonic cutoff is zero.
            for sign in (-1, 1):
                block = weight * wp2 / 2 * np.array(
                    [[1, 1j * sign, 0], [-1j * sign, 1, 0], [0, 0, 0]],
                    complex,
                )
                _add_block(blocks, sign * gyro, block)
            continue

        bessel_argument = (kx * vtp / gyro) ** 2 / 2
        for harmonic in range(-int(N), int(N) + 1):
            if harmonic == 0:
                continue
            gamma = ive(harmonic, bessel_argument)
            derivative = (
                ive(harmonic - 1, bessel_argument)
                + ive(harmonic + 1, bessel_argument)
                - 2 * gamma
            ) / 2
            xx = (harmonic * gyro / kx) ** 2 * gamma
            yy = vtp**2 / 2 * (
                harmonic**2 * gamma / bessel_argument
                - 2 * bessel_argument * derivative
            )
            xy = 1j * harmonic * vtp**2 / 2 * derivative
            xz = harmonic * gyro / kx * gamma * drift
            yz = -1j * drift * kx * vtp**2 / (2 * gyro) * derivative
            zz = (drift**2 + vtz**2 / 2) * gamma
            response = np.array(
                [[xx, xy, xz], [-xy, yy, yz], [xz, -yz, zz]], complex
            )
            block = weight * 2 * wp2 / vtp**2 * response
            _add_block(blocks, harmonic * gyro, block)

    constant = total_wp2 * np.eye(3) - sum(
        blocks.values(), np.zeros((3, 3), complex)
    )
    blocks = {0.0: constant, **blocks}
    poles = list(blocks)
    auxiliary_size = 3 * len(poles)
    matrix = sparse.lil_matrix(
        (auxiliary_size + 6, auxiliary_size + 6), dtype=complex
    )
    for index, pole in enumerate(poles):
        row = 3 * index
        matrix[row:row + 3, row:row + 3] = pole * np.eye(3)
        matrix[row:row + 3, auxiliary_size:auxiliary_size + 3] = -blocks[pole]
        matrix[auxiliary_size:auxiliary_size + 3, row:row + 3] = -np.eye(3)

    cross = np.array(
        [[0.0, 0.0, 0.0], [0.0, 0.0, -kx], [0.0, kx, 0.0]]
    )
    matrix[auxiliary_size:auxiliary_size + 3, auxiliary_size + 3:] = -c2 * cross
    matrix[auxiliary_size + 3:, auxiliary_size:auxiliary_size + 3] = cross
    matrix = matrix.tocsc()
    if not np.isfinite(matrix.data).all():
        raise FloatingPointError("perpendicular pencil not representable")

    return {
        "M": matrix,
        "pole_frequencies": np.asarray(poles),
        "pole_blocks": np.asarray([blocks[pole] for pole in poles]),
        "C0": constant,
        "totalwp2": total_wp2,
        "field_slice": (auxiliary_size, auxiliary_size + 6),
        "state_convention": (
            "three-current components per pole, then E3,B3; source G=-I convention"
        ),
        "finite_N_constant": "full Maxwell plasma constant retained; no sumGamma=1 substitution",
        "uniform_zero_k": kx == 0,
        "harmonic_cutoff_ignored_at_zero_k": kx == 0,
        "zero_frequency_modes": (
            "constraint/static/auxiliary diagnostics, not certified physical waves"
        ),
    }
