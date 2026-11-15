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


def _two_product(a, b):
    """Return a bounded product and its rounding residual (Dekker split)."""
    product = a * b
    split_a, split_b = 134_217_729.0 * a, 134_217_729.0 * b
    high_a, high_b = split_a - (split_a - a), split_b - (split_b - b)
    low_a, low_b = a - high_a, b - high_b
    error = ((high_a * high_b - product) + high_a * low_b + low_a * high_b) + low_a * low_b
    return product, error


def _product_parts(*factors, denominator=()):
    """Keep compensated bounded mantissas and separate binary exponents."""
    fraction = 1.0
    correction = 0.0
    exponent = 0
    for factor in factors:
        part, power = np.frexp(factor)
        product, error = _two_product(fraction, part)
        error = error + correction * part
        fraction = product + error
        correction = error - (fraction - product)
        exponent = exponent + power
    for factor in denominator:
        part, power = np.frexp(factor)
        quotient = fraction / part
        product, error = _two_product(quotient, part)
        remainder = ((fraction - product) - error + correction) / part
        fraction = quotient + remainder
        correction = remainder - (fraction - quotient)
        exponent = exponent - power
    return fraction, exponent


def _materialize(fraction, exponent):
    """Round a completed response, reporting genuine final overflow."""
    try:
        return np.ldexp(fraction, exponent)
    except FloatingPointError as error:
        raise FloatingPointError(
            "overflow encountered in multiply: Green response is not representable"
        ) from error


def _scaled_product(*factors, denominator=()):
    """Combine weights and geometry before rounding to a float64 response."""
    return _materialize(*_product_parts(*factors, denominator=denominator))


def _sum_products(*products):
    """Sum scaled terms before materializing an axial-field response."""
    normalized = []
    for fraction, exponent in products:
        fraction, adjustment = np.frexp(fraction)
        normalized.append((fraction, exponent + adjustment))
    common = np.maximum.reduce(
        [np.where(fraction == 0, -100_000, exponent) for fraction, exponent in normalized]
    )
    common = np.where(common == -100_000, 0, common)
    total = sum(np.ldexp(fraction, exponent - common) for fraction, exponent in normalized)
    return _materialize(total, common)


def _accumulate(total, correction, term):
    """Retain low bits when signed source responses nearly cancel."""
    updated = total + term
    correction = correction + np.where(
        np.abs(total) >= np.abs(term), (total - updated) + term, (term - updated) + total
    )
    return updated, correction


def _elliptic_values(gap, d, special):
    """Retain a positive separation even when its squared ratio underflows.

    For q below the smallest normal float, K(1-q)=log(4/sqrt(q))
    and E(1-q)=1 to relative corrections O(q*abs(log(q))), far below
    binary64 rounding. Form the logarithm from lengths, not a lost q.
    """
    ellipkm1, ellipe, _ = special
    q = (gap / d) ** 2
    tiny = q < np.finfo(float).tiny
    k_value, e_value = np.empty_like(q), np.empty_like(q)
    k_value[tiny] = np.log(4.0) + np.log(d[tiny]) - np.log(gap[tiny])
    e_value[tiny] = 1.0
    k_value[~tiny] = ellipkm1(q[~tiny])
    e_value[~tiny] = ellipe(1.0 - q[~tiny])
    return q, k_value, e_value


def _ring_flux(radius, r, d, m, gap, weight, special):
    """Evaluate the same flux relation in scalar and blocked assemblies."""
    a, r, d, m, gap, weight = np.broadcast_arrays(radius, r, d, m, gap, weight)
    _, _, hyp2f1 = special
    values = np.zeros_like(m)
    small = m < 0.5
    if np.any(small):
        aa, rr, dd, mm, ww = (x[small] for x in (a, r, d, m, weight))
        values[small] = _scaled_product(
            np.pi * 1.0e-7,
            ww,
            aa,
            aa,
            rr,
            rr,
            hyp2f1(1.5, 1.5, 3.0, mm),
            denominator=(dd, dd, dd),
        )
    if np.any(~small):
        dd, mm, gg, ww = (x[~small] for x in (d, m, gap, weight))
        _, k_value, e_value = _elliptic_values(gg, dd, special)
        values[~small] = _scaled_product(
            1.0e-7,
            ww,
            dd,
            (2.0 - mm) * k_value - 2.0 * e_value,
        )
    return values


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

    _, _, hyp2f1 = special
    target_r = targets[:, 0]
    separation_z = targets[:, 1] - height
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        distance = np.hypot(target_r + radius, separation_z)
        modulus = 4.0 * (target_r / distance) * (radius / distance)
        separation = np.hypot(target_r - radius, separation_z)
        small = modulus < 0.5
        response = np.zeros((3, targets.shape[0]), dtype=float)
        response[0] = _ring_flux(radius, target_r, distance, modulus, separation, weight, special)

        if np.any(small):
            r = target_r[small]
            h = separation_z[small]
            d = distance[small]
            m = modulus[small]
            h0 = hyp2f1(1.5, 1.5, 3.0, m)
            h1 = 0.75 * hyp2f1(2.5, 2.5, 4.0, m)
            response[1, small] = _scaled_product(
                np.pi * 1.0e-7,
                weight,
                radius,
                radius,
                r,
                h,
                3.0 * h0 + 2.0 * m * h1,
                denominator=(d, d, d, d, d),
            )
            u = (r / d) * ((r + radius) / d)
            response[2, small] = _scaled_product(
                np.pi * 1.0e-7,
                weight,
                radius,
                radius,
                (2.0 - 3.0 * u) * h0 + m * h1 * (1.0 - 2.0 * u),
                denominator=(d, d, d),
            )

        if np.any(~small):
            r = target_r[~small]
            h = separation_z[~small]
            d = distance[~small]
            m = modulus[~small]
            gap = separation[~small]
            q, k_value, e_value = _elliptic_values(gap, d, special)
            response[1, ~small] = _scaled_product(
                2.0e-7,
                weight,
                h,
                d,
                -q * k_value + ((radius / d) ** 2 + (r / d) ** 2 + (h / d) ** 2) * e_value,
                denominator=(r, gap, gap),
            )
            response[2, ~small] = _sum_products(
                _product_parts(2.0e-7, weight, k_value, denominator=(d,)),
                _product_parts(
                    2.0e-7, weight, radius - r, radius + r, e_value, denominator=(d, gap, gap)
                ),
                _product_parts(-2.0e-7, weight, (h / gap) ** 2, e_value, denominator=(d,)),
            )
    return response


def compute_greens(rzw, rz_pts):
    """Return ordered aggregate ``(psi, BR, BZ)`` ring responses.

    ``rzw`` may be one source table or a list of independent source tables.
    The latter returns one ``(N_target,)`` result per list element.  Positive
    radius rings are retained down to subnormal scales; zero-radius and
    zero-weight rows are inactive.  Exact positive-radius coincidences are
    rejected because a line-current self field is outside this discrete
    contract.  Arithmetic overflow and invalid floating-point results are
    reported as :class:`FloatingPointError`.

    Parameters
    ----------
    rzw : finite float64, shape (Ns,3) or list of (Ns,3)
        Source rows or a list of independent source sets [m, m, dimensionless
        weight]. Non-negative source radius; signed weights; list output
        preserves set dimension.
    rz_pts : finite float64, shape (Nt,2)
        Target cylindrical coordinates [m]. Non-negative target radius.

    Returns
    -------
    response : float64, shape three arrays of (Nt,) or (Nset,Nt)
        Tuple psi, BR, BZ; list source input returns one target axis per set
        [Wb/rad per ampere; T per ampere]. Finite output or explicit
        FloatingPointError.

    Raises
    ------
    FloatingPointError
        FloatingPointError is raised when the finite response cannot be
        represented.
    ValueError
        ValueError is raised for malformed, complex, nonfinite, negative-radius,
        or coincident active inputs.

    See Also
    --------
    scirel.field.solve_multi_coil_vacuum_field : Field of rectangular coil blocks built from these filaments.

    Notes
    -----
    A single ``rzw`` table returns three target-sized arrays. A list of source
    tables returns three matrices with one source-set axis followed by the
    target axis. The exact positive-radius self term is rejected rather than
    assigned a finite-wire value.

    Products retain a separate binary exponent until source weights and all
    geometric factors have been combined. This preserves representable fields
    and fluxes when an unweighted intermediate would underflow, without
    changing the hypergeometric or elliptic relations.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.electromagnetism import compute_greens
    >>> psi, br, bz = compute_greens(np.array([[1.0, 0.0, 1.0]]), np.array([[0.2, 0.3], [0.4, -0.2]]))
    >>> assert psi.shape == br.shape == bz.shape == (2,)
    """
    targets = _as_real_table(rz_pts, 2, "rz_pts")
    if isinstance(rzw, list):
        grouped = [compute_greens(group, targets) for group in rzw]
        if not grouped:
            return tuple(np.zeros((0, len(targets)), dtype=float) for _ in range(3))
        return tuple(np.stack([item[index] for item in grouped]) for index in range(3))

    sources = _as_real_table(rzw, 3, "rzw")
    result = np.zeros((3, len(targets)), dtype=float)
    correction = np.zeros_like(result)
    special = None
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        for source in sources:
            if source[0] == 0.0 or source[2] == 0.0:
                continue
            if np.any((targets[:, 0] == source[0]) & (targets[:, 1] == source[1])):
                raise ValueError("target coincident with singular circular filament")
            if special is None:
                special = _load_special_functions()
            result, correction = _accumulate(
                result, correction, _one_ring_response(source, targets, special)
            )
        result = result + correction
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("Green function output is not representable as finite float64")
    return tuple(result[index] for index in range(3))


def _weighted_psi(rzw, rz_pts, *, zero_self=False, max_pairs=1_000_000):
    """Assemble a weighted flux vector in bounded source blocks."""
    sources = _as_real_table(rzw, 3, "rzw")
    targets = _as_real_table(rz_pts, 2, "rz_pts")
    result = np.zeros(len(targets), dtype=float)
    correction = np.zeros_like(result)
    active = sources[(sources[:, 0] > 0.0) & (sources[:, 2] != 0.0)]
    if len(active) == 0 or len(targets) == 0:
        return result

    special = _load_special_functions()
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
            gap = np.hypot(r - a, h)
            values = _ring_flux(a, r, d, m, gap, block[:, 2, None], special)
            if zero_self:
                values[self_mask] = 0.0
            for row in values:
                result, correction = _accumulate(result, correction, row)
        result = result + correction
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
    """Return the dense actual-coordinate circular-filament flux matrix.

    Parameters
    ----------
    R : real array-like, shape [N_Z,N_R]
        Cylindrical target/source radii [m]. Must be finite, nonnegative, and
        have the same shape as ``Z``. Active positive-radius coordinate pairs
        must be distinct.
    Z : real array-like, shape [N_Z,N_R]
        Cylindrical target/source heights [m]. Must be finite and match
        ``R``. C-order flattening fixes matrix row and column order.

    Returns
    -------
    G : ndarray of float64, shape (R.size,R.size)
        Dense target-row/source-column flux response [Wb/rad/A]. The diagonal is
        zero by the discrete zero-self convention, and rows or columns with
        zero-radius sources are zero.

    Raises
    ------
    ValueError
        If ``R`` or ``Z`` is malformed, complex, nonfinite, negative-radius,
        or contains duplicate active positive-radius nodes.
    FloatingPointError
        If any matrix entry is not representable as finite float64.

    See Also
    --------
    scirel.electromagnetism.green_response_matrices : Build per-source psi, BR and BZ matrices.
    scirel.electromagnetism.compute_greens : Evaluate circular-filament responses on arbitrary targets.

    Notes
    -----
    This function evaluates the same axisymmetric ideal-filament kernel with
    the target nodes also serving as sources. The matrix is dense and has
    quadratic work and storage in ``R.size``. The zero diagonal is a discrete
    self-response convention, not a finite-wire inductance model.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.electromagnetism import get_gpsi
    >>> R,Z=np.meshgrid([.4,.8,1.2],[-.5,0.,.9])
    >>> G=get_gpsi(R,Z)
    >>> assert G.shape==(9,9) and np.all(np.diag(G)==0)
    """
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
    """Return ordered circular-filament psi, BR, and BZ response matrices.

    Parameters
    ----------
    rz_pts : real array-like, shape (Ntarget,2)
        Target cylindrical ``(R, Z)`` coordinates [m]. Must be finite with
        nonnegative radius.
    rzw : real array-like, shape (Nsource,2) or (Nsource,3), optional
        Ordered source ``(R, Z)`` coordinates with optional signed weights
        [m,m,dimensionless]. Rows with a zero radius or zero weight are
        inactive. If omitted, ``rz_pts`` itself supplies unit-weight sources.

    Returns
    -------
    psi : ndarray of float64, shape (Ntarget,Nsource)
        Flux response indexed by target row and source column [Wb/rad/A].
        Exact source-target coincidences have zero entries.
    BR : ndarray of float64, shape (Ntarget,Nsource)
        Radial-field response indexed by target row and source column [T/A].
    BZ : ndarray of float64, shape (Ntarget,Nsource)
        Axial-field response indexed by target row and source column [T/A].

    Raises
    ------
    ValueError
        If target or source tables are malformed, complex, nonfinite, have a
        negative radius, or an implicit source set has duplicate positive-
        radius nodes.
    FloatingPointError
        If a kernel response is not representable as finite float64.

    See Also
    --------
    scirel.electromagnetism.compute_greens : Evaluate aggregate responses on arbitrary targets.
    scirel.electromagnetism.get_gpsi : Build the dense target-as-source flux matrix.

    Notes
    -----
    Each source column is evaluated independently and source weights are
    applied once. Explicit source rows may repeat because their columns remain
    independent. The exact self term is set to zero by the discrete convention;
    this is not a finite-conductor self-field model.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.electromagnetism import green_response_matrices
    >>> targets=np.array([[0.,.2],[.8,-.3]])
    >>> sources=np.array([[.4,.1,1.],[1.2,-.7,-2.],[.6,.9,.5]])
    >>> gpsi,gbr,gbz=green_response_matrices(targets,sources)
    >>> assert gpsi.shape==(2,3) and np.all(gpsi[0]==0.)
    >>> field_bz=gbz@np.array([3.,-4.,2.])
    >>> assert np.all(np.isfinite(field_bz))
    """
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
