"""Complex trilinear interpolation on a strict rectilinear source grid."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from itertools import product

import numpy as np

from scirel._result import Result

__all__ = ["interpolate_complex_rectilinear_field"]
_AXIS_KEYS = ("x_m", "y_m", "z_m")
_CORNERS = tuple(product((0, 1), repeat=3))


def _source_axes(source_axes_m):
    if not isinstance(source_axes_m, Mapping):
        raise ValueError("source_axes_m must be a mapping of x_m, y_m, and z_m axes")
    result = []
    for name in _AXIS_KEYS:
        try:
            axis = np.asarray(source_axes_m[name], dtype=float)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"source_axes_m requires the {name} axis") from exc
        if axis.ndim != 1 or axis.size < 2:
            raise ValueError(f"source axis {name} must be a 1-D array with at least two points")
        if not np.isfinite(axis).all():
            raise ValueError(f"source axis {name} must contain only finite values")
        if np.any(axis[1:] <= axis[:-1]):
            raise ValueError(f"source axis {name} must be strictly increasing")
        result.append(axis)
    return tuple(result)


def _box_tolerance(axes):
    # The span may exceed float64 even though 32*eps*span is always finite.
    span = max(Fraction(1), *(Fraction(float(a[-1])) - Fraction(float(a[0])) for a in axes))
    return float(Fraction(32.0 * np.finfo(float).eps) * span)


def _corner_weights(axes, query, cells):
    # Independent endpoint distances preserve tiny weights near either node.
    # A failed vector operation requests exact evaluation, never a clipped value.
    try:
        with np.errstate(all="raise"):
            pairs = []
            for j, axis in enumerate(axes):
                lower, upper = axis[cells[j]], axis[cells[j] + 1]
                width = upper - lower
                pairs.append(((upper - query[:, j]) / width, (query[:, j] - lower) / width))
            return np.stack(
                [pairs[0][i] * pairs[1][j] * pairs[2][k] for i, j, k in _CORNERS], axis=1
            )
    except FloatingPointError:
        return None


def _exact_weights(axes, query, cells, row):
    pairs = []
    for j, axis in enumerate(axes):
        lower = Fraction(float(axis[cells[j][row]]))
        upper = Fraction(float(axis[cells[j][row] + 1]))
        point = Fraction(float(query[row, j]))
        pairs.append(((upper - point) / (upper - lower), (point - lower) / (upper - lower)))
    return [pairs[0][i] * pairs[1][j] * pairs[2][k] for i, j, k in _CORNERS]


def _exact_value(samples, weights):
    # Nonnegative rational weights sum to one. Each finite component therefore
    # lies within its finite corner extrema, including at subnormal scales.
    real = sum(w * Fraction(float(v.real)) for v, w in zip(samples, weights))
    imaginary = sum(w * Fraction(float(v.imag)) for v, w in zip(samples, weights))
    return complex(float(real), float(imaginary))


def _samples(axes, values, query, interpolator_type):
    cells = [np.searchsorted(axis[1:-1], query[:, j], side="right") for j, axis in enumerate(axes)]
    trailing = values.shape[3:]
    components = int(np.prod(trailing)) if trailing else 1
    corners = np.stack(
        [
            values[tuple(cell + offset for cell, offset in zip(cells, corner))]
            for corner in _CORNERS
        ],
        axis=1,
    ).reshape(len(query), 8, components)
    output = np.empty((len(query), components), dtype=complex)
    weights = _corner_weights(axes, query, cells)
    finite = np.isfinite(corners).all(axis=1)
    rows, columns = np.nonzero(finite)
    needs_exact = np.ones(len(rows), dtype=bool)
    if weights is not None:
        # Only the finite columns enter this screen. Nonfinite columns below
        # still evaluate every original corner, including zero-weight touches.
        selected = corners.transpose(0, 2, 1)[finite]
        try:
            with np.errstate(all="raise"):
                terms_real = selected.real * weights[rows]
                terms_imag = selected.imag * weights[rows]
                real, imaginary = terms_real.sum(axis=1), terms_imag.sum(axis=1)
                magnitude_real = np.abs(terms_real).sum(axis=1)
                magnitude_imag = np.abs(terms_imag).sum(axis=1)
                # 1/8 chooses arithmetic dispatch, not a physical cutoff. Severe
                # cancellation is recomputed from inputs rather than rounded terms.
                needs_exact = ((magnitude_real > 0) & (np.abs(real) < magnitude_real / 8)) | (
                    (magnitude_imag > 0) & (np.abs(imaginary) < magnitude_imag / 8)
                )
            output.real[rows, columns] = real
            output.imag[rows, columns] = imaginary
        except FloatingPointError:
            needs_exact = np.ones(len(rows), dtype=bool)

    exact_weights = {}
    for row, column in zip(rows[needs_exact], columns[needs_exact]):
        if row not in exact_weights:
            exact_weights[row] = _exact_weights(axes, query, cells, row)
        output[row, column] = _exact_value(corners[row, :, column], exact_weights[row])
    nonfinite_rows = np.flatnonzero((~finite).any(axis=1))
    if nonfinite_rows.size:
        # Preserve the original SciPy propagation, warnings and zero-weight
        # corner touches for nonfinite columns. Do not filter source samples.
        interpolator = interpolator_type(
            axes, values, method="linear", bounds_error=False, fill_value=np.nan + 1j * np.nan
        )
        original = np.asarray(interpolator(query[nonfinite_rows])).reshape(
            len(nonfinite_rows), components
        )
        row_output = output[nonfinite_rows]
        nonfinite = ~finite[nonfinite_rows]
        row_output[nonfinite] = original[nonfinite]
        output[nonfinite_rows] = row_output
    return output.reshape((len(query),) + trailing)


def interpolate_complex_rectilinear_field(source_axes_m, source_values, target_points_m):
    """Complex rectilinear field interpolation

    Parameters
    ----------
    source_axes_m : real array-like
        Mapping with keys x_m, y_m, and z_m holding the three strictly increasing source axes.
        [m] Shape: mapping of three [N_axis] arrays. Each axis is one-dimensional, finite, has
        at least two points, and is strictly increasing. Axes are consumed by x_m, y_m, z_m key
        order; the callable cannot detect a caller assigning the wrong physical axis to a key.

    source_values : complex array-like
        Complex field samples on the tensor-product source grid, indexed [x, y, z]; trailing
        axes are preserved. [caller-declared field units] Shape: ``[N_x,N_y,N_z] plus
        optional trailing axes``. Leading shape must equal (N_x, N_y, N_z); values are not
        required to be finite, and non-finite entries propagate into every target point
        whose stencil touches them.

    target_points_m : real array-like
        Target Cartesian points to sample, one point per row. [m] Shape: ``[N_point,3]``.
        Two-dimensional, exactly three columns, and finite; non-finite target points are
        rejected rather than masked.

    Returns
    -------
    interpolated_values : complex128
        Interpolated complex field value per target point, with the source trailing axes
        preserved. [caller-declared field units] Shape: ``[N_point] plus optional trailing
        axes``. nan+nanj wherever valid_mask is false; finite at every valid_mask point only
        when the touched source values are finite.
    valid_mask : bool
        Geometric containment predicate: true exactly when the target point lies inside the
        closed source box expanded by tol. [dimensionless] Shape: ``[N_point]``. Independent
        of source and result finiteness; a true entry does not guarantee a finite
        interpolated value.

    The complete result is returned as one ``scirel._result.Result`` mapping. No nested
    mapping is introduced, and non-colliding fields support attribute access.

    Raises
    ------
    ValueError
        Raises ValueError for a missing or non-mapping source_axes_m, an axis that is not one-dimensional, has fewer than two points, is non-finite, or is not strictly increasing, for a source_values leading shape that does not match the axes, and for target points that are not a finite (N,3) array.

    See Also
    --------
    scirel.numerics.interpolate.sample_rectilinear_field : Rectilinear R-Z bilinear sampling.
    scirel.geometry.map_axisymmetric_equilibrium_to_cartesian_grid : Axisymmetric equilibrium map to Cartesian solver grid.

    Notes
    -----
    Separable trilinear interpolation in [x, y, z] axis order with the source values indexed
    [N_x, N_y, N_z]; target points inside the closed source box expanded by tol are clamped
    onto the closed box and interpolated, and target points outside that expanded box return
    nan+nanj with valid_mask false.

    The box tolerance uses original-input spans without materializing a full
    floating-point span. Each corner weight is a product of endpoint-distance ratios
    (b-q)/(b-a) or (q-a)/(b-a) on the three enclosing intervals.
    Finite stencils use independent left/right endpoint weights; underflow, overflow or
    severe cancellation in the vector calculation requests an exact rational evaluation
    of the original binary64 coordinates and samples, separately for real and imaginary
    parts. This preserves representable small contributions without changing the
    trilinear relation. Non-finite samples still participate at zero-weight corners.

    **Coordinates.** caller-declared Cartesian axes in metres, indexed [x, y, z]

    **Boundary.** closed-box domain expanded by tol = 32 * eps * max(1, max axis span);
    outside the expansion no extrapolation is performed

    **Preconditions.**

    * The complex field is sampled on a tensor-product rectilinear grid that is dense enough
      for trilinear reconstruction to be meaningful over the region of interest.

    **Limits.**

    * Extrapolation beyond the tolerance-expanded source box.
    * Curvilinear, cylindrical, or unstructured source grids.
    * Masking or repairing non-finite source data; that decision belongs to the caller.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.numerics.interpolate import interpolate_complex_rectilinear_field
    >>> axes = {'x_m': np.array([0.0, 1.0, 2.0]), 'y_m': np.array([0.0, 1.0, 2.0]), 'z_m': np.array([0.0, 1.0, 2.0])}
    >>> values = np.zeros((3, 3, 3), dtype=complex)
    >>> values[1, 1, 1] = 4.0 + 2.0j
    >>> points = np.array([[1.0, 1.0, 1.0], [1.0 + 1.0e-15, 1.0, 1.0], [1.0, 1.0, 3.0]])
    >>> result = interpolate_complex_rectilinear_field(axes, values, points)
    >>> assert isinstance(result, Result)
    >>> assert result['valid_mask'].tolist() == [True, True, False]
    >>> assert np.isfinite(result['interpolated_values'][:2]).all()
    >>> assert np.isnan(result['interpolated_values'][2].real) and np.isnan(result['interpolated_values'][2].imag)
    """
    from scipy.interpolate import RegularGridInterpolator

    axes = _source_axes(source_axes_m)
    values = np.asarray(source_values, dtype=complex)
    expected = tuple(axis.size for axis in axes)
    if values.shape[:3] != expected:
        raise ValueError("source_values leading shape must match the three source axes")
    points = np.asarray(target_points_m, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("target_points_m must be a finite array with shape (n_points, 3)")

    lower = np.array([axis[0] for axis in axes])
    upper = np.array([axis[-1] for axis in axes])
    tolerance = _box_tolerance(axes)
    # Python scalar bounds may legitimately exceed float64; no intermediate
    # NumPy subtraction should overflow merely to compare finite queries.
    expanded_lower = np.array([float(a) - tolerance for a in lower])
    expanded_upper = np.array([float(a) + tolerance for a in upper])
    valid = np.all((points >= expanded_lower) & (points <= expanded_upper), axis=1)
    query = np.clip(points, lower, upper)
    output = _samples(axes, values, query, RegularGridInterpolator)
    output[~valid] = np.nan + 1j * np.nan
    return Result({"interpolated_values": output, "valid_mask": valid})
