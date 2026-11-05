"""Fixed-flux derivative evidence for pressure laws ``p(B, psi)``."""

import numpy as np


def fixed_flux_derivative(quantity, magnetic_field, *, derivative=None, field_axis=None, psi=None):
    """Use an explicit partial derivative or samples along a declared fixed-psi axis.

    An explicit derivative is an array/scalar in pressure/tesla, or a callable
    ``derivative(B, psi)``. Alternatively, ``field_axis`` identifies ordered,
    strictly monotonic B samples, and ``psi`` must be constant along each such
    line. Separate flux surfaces are never flattened or sorted together.
    Constant or duplicate B values alone cannot determine a derivative.
    """
    q, b = np.asarray(quantity, dtype=float), np.asarray(magnetic_field, dtype=float)
    if (
        q.shape != b.shape
        or q.size == 0
        or not np.all(np.isfinite(q))
        or not np.all(np.isfinite(b))
    ):
        raise ValueError("pressure and magnetic field must be nonempty finite same-shape samples")
    if np.any(b <= 0.0):
        raise ValueError("magnetic field magnitude must be strictly positive")
    if derivative is not None:
        if field_axis is not None:
            raise ValueError("provide an explicit derivative or a fixed-flux sample axis, not both")
        value = derivative(b, psi) if callable(derivative) else derivative
        try:
            value = np.broadcast_to(np.asarray(value, dtype=float), q.shape)
        except ValueError as exc:
            raise ValueError(
                "explicit fixed-flux derivative does not broadcast to pressure shape"
            ) from exc
        if not np.all(np.isfinite(value)):
            raise ValueError("explicit fixed-flux derivative must be finite")
        return np.array(value, copy=True), "explicit_fixed_flux_derivative"
    if field_axis is None or psi is None:
        raise ValueError("a fixed-flux derivative or field_axis plus fixed psi samples is required")
    if isinstance(field_axis, (bool, np.bool_)) or int(field_axis) != field_axis:
        raise ValueError("field_axis must be an integer axis")
    axis = int(field_axis)
    if axis < -q.ndim or axis >= q.ndim:
        raise ValueError("field_axis is outside the pressure-array dimensions")
    axis %= q.ndim
    if q.shape[axis] < 2:
        raise ValueError("fixed-flux derivative requires at least two distinct field samples")
    try:
        surfaces = np.broadcast_to(np.asarray(psi, dtype=float), q.shape)
    except ValueError as exc:
        raise ValueError("psi must broadcast to the pressure-array shape") from exc
    if not np.all(np.isfinite(surfaces)) or np.any(np.diff(surfaces, axis=axis) != 0.0):
        raise ValueError(
            "psi must be finite and exactly constant along each fixed-flux sample line"
        )
    qm, bm = np.moveaxis(q, axis, -1), np.moveaxis(b, axis, -1)
    result = np.empty_like(qm)
    for index in np.ndindex(qm.shape[:-1]):
        x, y = bm[index], qm[index]
        delta = np.diff(x)
        if not (np.all(delta > 0.0) or np.all(delta < 0.0)):
            raise ValueError(
                "fixed-flux magnetic-field samples must be unique and strictly monotonic"
            )
        result[index] = np.gradient(y, x, edge_order=2 if x.size >= 3 else 1)
    result = np.moveaxis(result, -1, axis)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("fixed-flux numerical derivative is not finite")
    return result, "declared_fixed_flux_axis_finite_difference"
