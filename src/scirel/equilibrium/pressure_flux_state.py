"""Pressure spline and derivative state for the isotropic flux solver."""

from __future__ import annotations

import numpy as np

from scirel._result import Result

from ._pressure_current import fit_pressure_spline, pressure_derivative as _pressure_derivative

__all__ = ["build_pressure_flux_state"]


def _finite_grid(name, value, shape=None):
    array = np.asarray(value, dtype=float)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional [Z,R] array")
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _representation(spline, psi_samples, pressure_samples):
    knots, coefficients, degree = spline._eval_args
    return {
        "psi_samples": np.asarray(psi_samples, dtype=float),
        "pressure_samples": np.asarray(pressure_samples, dtype=float),
        "knots": np.asarray(knots, dtype=float),
        "coefficients": np.asarray(coefficients, dtype=float),
        "degree": int(degree),
        "extrapolation": "zeros",
        "evaluation": "InterpolatedUnivariateSpline(psi_samples, pressure_samples, ext='zeros')",
    }


def build_pressure_flux_state(r_grid, z_grid, psi, pressure_of_radius, plasma_mask=None):
    """Fit the midplane pressure prefix and return its clipped flux derivative.

    Parameters
    ----------
    r_grid : real array-like, converted to float64
        Cylindrical radius grid used to sample pressure on the exact midplane row [m] Shape [N_Z,N_R]. Finite 2-D values matching z_grid and psi; midplane radii must be distinct. Only midplane traversal is sorted by radius; output layout is preserved.
    z_grid : real array-like, converted to float64
        Axial coordinate grid identifying the unique exact-zero midplane row [m] Shape [N_Z,N_R]. Finite and same shape as r_grid; exactly one complete row must equal 0.0, and exactly N_R cells in total may equal 0.0.
    psi : real array-like, converted to float64
        Axisymmetric psi=R A_phi at each R-Z grid point in the maintained chain [Wb/rad] Shape [N_Z,N_R]. Finite and same shape as r_grid; values on the midplane prefix through the first zero-pressure sample must be strictly increasing, with at least four samples.
    pressure_of_radius : callable returning real scalar values convertible to float64
        Callable returning scalar pressure for each exact-midplane radius [R input m; pressure output Pa] Shape callable(scalar R) -> scalar pressure. Finite nonnegative scalar at every midplane radius, called in increasing physical-radius order; an exact zero defines the boundary.
    plasma_mask : boolean array-like or None
        Optional mask whose true entries set the corresponding flattened pressure derivative to zero Shape [N_Z,N_R] or null. Must be genuinely boolean and shape-matched; numeric truth-value coercion is not accepted.

    Returns
    -------
    pressure_derivative : float64 array
        Finite spline derivative in C order after edge and boolean-mask clipping [Pa/(Wb/rad)] Shape [N_Z*N_R]. Nonfinite values fail before any clipping. Zero for psi > psi_edge and true mask entries.
    zero_currents : float64 array
        All-zero initial current vector aligned with pressure_derivative [A] Shape [N_Z*N_R]. C-order flattened all-zero array; no current is solved by this operator.
    psi_edge : float
        Flux at the first exact-zero-pressure midplane sample [Wb/rad] Shape scalar. Taken from the same midplane position as limiter_index.
    pressure_of_psi : mapping of float64 arrays, integer degree and string descriptors
        Plain-dict representation of the fitted pressure-versus-flux spline [psi fields Wb/rad; pressure fields Pa; degree and descriptors dimensionless] Shape mapping. psi_samples and pressure_samples contain exactly the fitted prefix through limiter_index; knots, coefficients, degree and extrapolation=zeros describe the same cubic spline. This nested value is not a Result.
    limiter_index : int
        First exact-zero pressure index in increasing physical-radius order [index] Shape scalar. Zero-based position in the physically sorted midplane, not a whole-grid or storage-order index.

    The complete result is returned as one ``scirel._result.Result`` mapping. No nested
    mapping is wrapped, and every field also supports attribute access.

    Raises
    ------
    FloatingPointError
        Raised when the corresponding declared input, numerical or convergence condition fails.
    ValueError
        Raised when the corresponding declared input, numerical or convergence condition fails.

    See Also
    --------
    pressure_flux_picard_step : Apply one isotropic Picard update.

    Notes
    -----
    Sort only the unique exact Z=0 midplane indices by physical radius, rejecting duplicate radii. Sample nonnegative finite P(R); fit the strictly increasing flux prefix of at least four points through the first outward exact zero-pressure edge. Serialize that exact prefix, knots, coefficients and cubic degree. Evaluate dP/dpsi in original C-order grid layout, reject nonfinite coefficients or derivatives before clipping, then zero values above psi_edge or at true boolean plasma_mask cells. Return the finite derivative and aligned zero-current vector.

    Axisymmetric isotropic cubic pressure-flux construction with physical radial traversal and exactly reconstructible fit

    The supplied pressure profile is a nonnegative scalar function of cylindrical radius and defines an exact zero-pressure boundary.

    Physical midplane radii are distinct; psi rises strictly along increasing physical radius through the first zero-pressure sample, independently of storage order.

    For the maintained isotropic Picard chain the caller supplies psi=R A_phi in Wb/rad; the spline alone does not independently establish physical equilibrium or enforce a flux normalization.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state
    >>> r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.8, 4), [-0.1, 0.0, 0.1])
    >>> mask = np.zeros_like(r_grid, dtype=bool)
    >>> mask[1, 2] = True
    >>> result = build_pressure_flux_state(r_grid, z_grid, r_grid.copy(), lambda radius: max(0.8 - radius, 0.0), plasma_mask=mask)
    >>> expected = np.full(r_grid.size, -1.0)
    >>> expected[6] = 0.0
    >>> assert isinstance(result, Result)
    >>> assert result.limiter_index == result['limiter_index']
    >>> assert type(result.pressure_of_psi) is dict
    >>> np.testing.assert_allclose(result.pressure_derivative, expected)
    >>> np.testing.assert_allclose(result.zero_currents, 0.0)
    >>> assert result.limiter_index == 3
    >>> assert result.psi_edge == 0.8
    >>> assert result.pressure_of_psi['extrapolation'] == 'zeros'
    """
    r_grid = _finite_grid("r_grid", r_grid)
    z_grid = _finite_grid("z_grid", z_grid, r_grid.shape)
    psi = _finite_grid("psi", psi, r_grid.shape)
    if not callable(pressure_of_radius):
        raise ValueError("pressure_of_radius must be callable as pressure_of_radius(R)")

    flat_r, flat_z, flat_psi = r_grid.ravel(), z_grid.ravel(), psi.ravel()
    midplane = np.where(flat_z == 0.0)[0]
    zero_rows = np.where(np.all(z_grid == 0.0, axis=1))[0]
    if zero_rows.size != 1 or midplane.size != r_grid.shape[1]:
        raise ValueError("z_grid must contain exactly one complete zero midplane row")
    midplane = midplane[np.argsort(flat_r[midplane])]
    radii = flat_r[midplane]
    if np.any(np.diff(radii) <= 0.0):
        raise ValueError("midplane radii must be distinct")

    pressure = np.asarray([pressure_of_radius(radius) for radius in radii], dtype=float)
    if pressure.ndim != 1 or not np.all(np.isfinite(pressure)) or np.any(pressure < 0.0):
        raise ValueError("pressure_of_radius must return finite nonnegative scalar values")
    zero = np.flatnonzero(pressure == 0.0)
    if zero.size == 0:
        raise ValueError("pressure_of_radius must define an exact zero-pressure boundary")
    limiter = int(zero[0])
    psi_prefix = flat_psi[midplane][: limiter + 1]
    if psi_prefix.size < 4 or not np.all(np.diff(psi_prefix) > 0.0):
        raise ValueError(
            "midplane psi samples must be strictly increasing with at least four points"
        )

    spline = fit_pressure_spline(psi_prefix, pressure[: limiter + 1])
    psi_edge = float(flat_psi[midplane][limiter])
    if plasma_mask is not None:
        mask = np.asarray(plasma_mask)
        if mask.shape != r_grid.shape or mask.dtype.kind != "b":
            raise ValueError("plasma_mask must have the same shape as r_grid and be boolean")
    else:
        mask = None
    derivative = _pressure_derivative(
        spline, flat_psi, psi_edge, None if mask is None else mask.ravel()
    )
    return Result(
        {
            "pressure_derivative": derivative,
            "zero_currents": np.zeros_like(derivative),
            "psi_edge": psi_edge,
            "pressure_of_psi": _representation(spline, psi_prefix, pressure[: limiter + 1]),
            "limiter_index": limiter,
        }
    )
