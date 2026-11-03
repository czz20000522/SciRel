"""Axisymmetric circular-filament Green operators.

The public functions in this module use one explicit coordinate convention:
``(R, Z)`` for points and ``(R, Z, weight)`` for weighted source rings.  The
kernel is assembled in target-sized NumPy arrays.  Keeping source rings in
caller order makes the resulting matrices suitable for direct current
contraction and keeps the discrete zero-self rule visible at the assembly
boundary.
"""

from __future__ import annotations

import numpy as np


def _load_special_functions():
    """Load optional numerical kernels only after a valid numerical call."""
    from scipy.special import ellipe, ellipkm1, hyp2f1

    return ellipkm1, ellipe, hyp2f1


def _as_real_table(value, width, name):
    """Validate a finite ``(N, width)`` real coordinate table."""
    if np.iscomplexobj(value):
        raise ValueError(f"{name} must contain real values")
    table = np.asarray(value, dtype=float)
    if table.ndim != 2 or table.shape[1] != width:
        raise ValueError(f"{name} must have shape (N, {width})")
    if not np.all(np.isfinite(table)) or np.any(table[:, 0] < 0.0):
        raise ValueError(f"{name} must be finite with non-negative cylindrical radius")
    return table


def _one_ring_response(source, targets, special):
    """Evaluate one weighted ring on a target table.

    The small-modulus hypergeometric form avoids cancellation in the flux
    expression.  The elliptic form handles the complementary part.  Both
    branches are differentiated analytically so ``B_R`` and ``B_Z`` remain
    consistent with ``psi`` near the axis.
    """
    radius, height, weight = source
    if radius == 0.0 or weight == 0.0 or targets.shape[0] == 0:
        return np.zeros((3, targets.shape[0]), dtype=float)

    if np.any((targets[:, 0] == radius) & (targets[:, 1] == height)):
        raise ValueError("target coincident with singular circular filament")

    ellipkm1, ellipe, hyp2f1 = special
    target_r = targets[:, 0]
    separation_z = targets[:, 1] - height
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        distance = np.hypot(target_r + radius, separation_z)
        modulus = 4.0 * (target_r / distance) * (radius / distance)
        complement = (np.hypot(target_r - radius, separation_z) / distance) ** 2
        small = modulus < 0.5
        response = np.zeros((3, targets.shape[0]), dtype=float)

        if np.any(small):
            r = target_r[small]
            h = separation_z[small]
            d = distance[small]
            m = modulus[small]
            h0 = hyp2f1(1.5, 1.5, 3.0, m)
            h1 = 0.75 * hyp2f1(2.5, 2.5, 4.0, m)
            scale = np.pi * 1.0e-7 * (radius / d) ** 2 / d
            dm_dr = 4.0 * (radius / d) / d - 2.0 * m * ((r + radius) / d) / d
            response[0, small] = scale * r**2 * h0
            response[1, small] = scale * (r / d) * (h / d) * (3.0 * h0 + 2.0 * m * h1)
            response[2, small] = scale * (
                (2.0 - 3.0 * (r / d) * ((r + radius) / d)) * h0 + r * h1 * dm_dr
            )

        if np.any(~small):
            r = target_r[~small]
            h = separation_z[~small]
            d = distance[~small]
            m = modulus[~small]
            q = complement[~small]
            k_value, e_value = ellipkm1(q), ellipe(1.0 - q)
            radial_gap2 = np.hypot(r - radius, h) ** 2
            response[0, ~small] = 1.0e-7 * d * ((2.0 - m) * k_value - 2.0 * e_value)
            response[1, ~small] = (
                2.0e-7
                * h
                / (r * d)
                * (-k_value + (radius * radius + r * r + h * h) / radial_gap2 * e_value)
            )
            response[2, ~small] = (
                2.0e-7
                / d
                * (k_value + ((radius - r) * (radius + r) - h * h) / radial_gap2 * e_value)
            )
    return weight * response


def compute_greens(rzw, rz_pts):
    """Return ordered aggregate ``(psi, BR, BZ)`` ring responses.

    ``rzw`` may be one source table or a list of independent source tables.
    The latter returns one ``(N_target,)`` result per list element.  Positive
    radius rings are retained down to subnormal scales; zero-radius and
    zero-weight rows are inactive.  Exact positive-radius coincidences are
    rejected because a line-current self field is outside this discrete
    contract.  Arithmetic overflow and invalid floating-point results are
    reported as :class:`FloatingPointError`.
    """
    targets = _as_real_table(rz_pts, 2, "rz_pts")
    if isinstance(rzw, list):
        grouped = [compute_greens(group, targets) for group in rzw]
        if not grouped:
            return tuple(np.zeros((0, len(targets)), dtype=float) for _ in range(3))
        return tuple(np.stack([item[index] for item in grouped]) for index in range(3))

    sources = _as_real_table(rzw, 3, "rzw")
    result = np.zeros((3, len(targets)), dtype=float)
    special = None
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        for source in sources:
            if source[0] == 0.0 or source[2] == 0.0:
                continue
            if np.any((targets[:, 0] == source[0]) & (targets[:, 1] == source[1])):
                raise ValueError("target coincident with singular circular filament")
            if special is None:
                special = _load_special_functions()
            result += _one_ring_response(source, targets, special)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("Green function output is not representable as finite float64")
    return tuple(result[index] for index in range(3))


def _weighted_psi(rzw, rz_pts, *, zero_self=False, max_pairs=1_000_000):
    """Assemble a weighted flux vector in bounded source blocks."""
    sources = _as_real_table(rzw, 3, "rzw")
    targets = _as_real_table(rz_pts, 2, "rz_pts")
    result = np.zeros(len(targets), dtype=float)
    active = sources[(sources[:, 0] > 0.0) & (sources[:, 2] != 0.0)]
    if len(active) == 0 or len(targets) == 0:
        return result

    ellipkm1, ellipe, hyp2f1 = _load_special_functions()
    block_size = max(1, min(len(active), int(max_pairs) // max(1, len(targets))))
    r = targets[:, 0][None, :]
    z = targets[:, 1][None, :]
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        for start in range(0, len(active), block_size):
            block = active[start : start + block_size]
            a = block[:, 0, None]
            z0 = block[:, 1, None]
            h = z - z0
            self_mask = (r == a) & (z == z0) if zero_self else None
            if zero_self:
                h = np.where(self_mask, 1.0, h)
            d = np.hypot(r + a, h)
            m = 4.0 * (r / d) * (a / d)
            q = (np.hypot(r - a, h) / d) ** 2
            values = np.zeros_like(m)
            small = m < 0.5
            if np.any(small):
                ds = d[small]
                rs = np.broadcast_to(r, m.shape)[small]
                ms = m[small]
                aa = np.broadcast_to(a, m.shape)[small]
                values[small] = (
                    np.pi * 1.0e-7 * (aa / ds) ** 2 / ds * rs**2 * hyp2f1(1.5, 1.5, 3.0, ms)
                )
            if np.any(~small):
                dl, ql, ml = d[~small], q[~small], m[~small]
                k_value, e_value = ellipkm1(ql), ellipe(1.0 - ql)
                values[~small] = 1.0e-7 * dl * ((2.0 - ml) * k_value - 2.0 * e_value)
            if zero_self:
                values[self_mask] = 0.0
            result += np.add.reduce(block[:, 2, None] * values, axis=0)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("weighted Green psi output is not representable as finite float64")
    return result


def _psi_matrix(points, *, max_pairs=1_000_000):
    """Build the unit-weight flux matrix for positive-radius point sources."""
    point_table = _as_real_table(points, 2, "points")
    source_indices = np.flatnonzero(point_table[:, 0] > 0.0)
    matrix = np.zeros((len(point_table), len(source_indices)), dtype=float)
    if len(source_indices) == 0 or len(point_table) == 0:
        return matrix
    special = _load_special_functions()
    block_size = max(1, min(len(source_indices), int(max_pairs) // max(1, len(point_table))))
    for start in range(0, len(source_indices), block_size):
        indices = source_indices[start : start + block_size]
        for local, source_index in enumerate(indices):
            source = np.r_[point_table[source_index], 1.0]
            target_mask = np.ones(len(point_table), dtype=bool)
            target_mask[source_index] = False
            if np.any(target_mask):
                matrix[target_mask, start + local] = _one_ring_response(
                    source, point_table[target_mask], special
                )[0]
    if not np.all(np.isfinite(matrix)):
        raise FloatingPointError("Green psi matrix output is not representable as finite float64")
    return matrix


def get_gpsi(R, Z):
    """Return the actual-coordinate ``(target, source)`` flux matrix."""
    if np.iscomplexobj(R) or np.iscomplexobj(Z):
        raise ValueError("R,Z must be real coordinate arrays")
    radius, height = np.asarray(R, dtype=float), np.asarray(Z, dtype=float)
    if (
        radius.ndim != 2
        or height.shape != radius.shape
        or not np.all(np.isfinite(radius))
        or not np.all(np.isfinite(height))
        or np.any(radius < 0.0)
    ):
        raise ValueError("R,Z must be matching finite 2-D arrays with nonnegative R")
    points = np.column_stack((radius.ravel(), height.ravel()))
    active = points[points[:, 0] > 0.0]
    if len(np.unique(active, axis=0)) != len(active):
        raise ValueError("distinct positive-radius loop entries cannot be coincident")
    matrix = np.zeros((len(points), len(points)), dtype=float)
    active_indices = np.flatnonzero(points[:, 0] > 0.0)
    if len(active_indices):
        matrix[:, active_indices] = _psi_matrix(points)
    return matrix


def green_response_matrices(rz_pts, rzw=None):
    """Return ``(psi, BR, BZ)`` matrices with shape ``(target, source)``."""
    if np.iscomplexobj(rz_pts) or (rzw is not None and np.iscomplexobj(rzw)):
        raise ValueError("target and source coordinates/weights must be real")
    targets = _as_real_table(rz_pts, 2, "rz_pts")
    if rzw is None:
        active = targets[targets[:, 0] > 0.0]
        if len(np.unique(active, axis=0)) != len(active):
            raise ValueError("implicit positive-radius source nodes cannot be coincident")
        sources = np.column_stack((targets, np.ones(len(targets))))
    else:
        raw = np.asarray(rzw, dtype=float)
        if raw.ndim != 2 or raw.shape[1] not in (2, 3):
            raise ValueError("rzw must have shape (Nsource, 2) or (Nsource, 3)")
        sources = np.column_stack((raw, np.ones(len(raw)))) if raw.shape[1] == 2 else raw
        sources = _as_real_table(sources, 3, "rzw")

    response = np.zeros((3, len(targets), len(sources)), dtype=float)
    for index, source in enumerate(sources):
        if source[0] == 0.0 or source[2] == 0.0:
            continue
        off_self = ~((targets[:, 0] == source[0]) & (targets[:, 1] == source[1]))
        if np.any(off_self):
            response[:, off_self, index] = np.asarray(
                compute_greens(source[None, :], targets[off_self])
            )
    return tuple(response[index] for index in range(3))


__all__ = ["compute_greens", "get_gpsi", "green_response_matrices"]
