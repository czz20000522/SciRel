"""One-dimensional linear profiles indexed by poloidal flux."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_flux_surface_profile"]


def evaluate_flux_surface_profile(
    *, psi_samples, values, target, left=None, right=None
) -> dict[str, np.ndarray]:
    """Scalar profile on a flux coordinate

    Parameters
    ----------
    psi_samples : real array-like
        Sample flux coordinates, flattened before sorting. [caller-consistent Wb/rad or Wb]
        Shape: ``array-like, flattened to [N_sample]``. Finite; paired with values; at least
        two original pairs and at least two unique coordinates.

    values : real array-like
        Scalar profile samples paired with psi_samples. [caller-defined profile unit] Shape:
        ``array-like, flattened to [N_sample]``. Finite and exactly the same flattened
        length as psi_samples.

    target : real array-like
        Query flux coordinates in the same convention as psi_samples. [same as psi_samples]
        Shape: ``scalar or array-like``. Finite; output values retain this shape.

    left : real scalar or None, optional
        Value returned below the minimum normalized sample coordinate. [same as values]
        Shape: ``scalar or null``. None selects the first normalized profile value;
        otherwise convertible to finite float. Optional; default ``None``.

    right : real scalar or None, optional
        Value returned above the maximum normalized sample coordinate. [same as values]
        Shape: ``scalar or null``. None selects the last normalized profile value; otherwise
        convertible to finite float. Optional; default ``None``.

    Returns
    -------
    values : float64
        Linearly interpolated or constant-extended profile at target. [same as input values]
        Shape: ``same as target``. Follows the declared endpoint policy.
    psi : float64
        Sorted unique sample coordinates used for interpolation, without unit conversion.
        [same as psi_samples] Shape: ``[N_unique]``. Strictly increasing with at least two
        entries.
    profile_values : float64
        Sample values retained after sorting and coordinate deduplication. [same as input
        values] Shape: ``[N_unique]``. Aligned with psi; duplicate coordinates retain the
        first occurrence after NumPy sorting, without a guaranteed original-input tie order.

    Raises
    ------
    ValueError
        Raises ValueError for unequal or insufficient paired samples, fewer than two unique flux coordinates, nonfinite inputs or nonfinite endpoint values.

    See Also
    --------
    compute_flux_surface_inverse_field_average : Polyline inverse-field measure and weighted mean.
    flux_surface_avg : B-weighted line reduction.

    Notes
    -----
    Flatten paired samples, sort by flux coordinate with NumPy argsort, retain the first
    occurrence in that sorted order for each duplicate coordinate, interpolate linearly
    between unique coordinates, and use constant left/right values beyond the interval.
    Equal-coordinate ties have no promised original-input ordering.

    **Coordinates.** psi_samples and target use the same caller-selected poloidal-flux
    coordinate convention, either psi=R A_phi in Wb/rad or complete linked flux in Wb; the
    operator applies no conversion

    **Boundary.** default endpoint values are the first and last normalized samples;
    caller-supplied finite left/right scalars override them

    **Preconditions.**

    * Caller supplies finite, paired samples and target coordinates in one consistent Wb/rad
      or Wb flux convention and compatible scalar-value units.

    **Limits.**

    * Construction of magnetic surfaces or field-line geometry.
    * Higher-order interpolation or extrapolation.
    * Physical resolution of conflicting duplicate-coordinate values.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile
    >>> result = evaluate_flux_surface_profile(psi_samples=[2.0, 0.0, 1.0, 1.0], values=[4.0, 0.0, 2.0, 3.0], target=[-1.0, 0.5, 3.0], left=-7.0, right=9.0)
    >>> np.testing.assert_allclose(result['values'], [-7.0, 1.0, 9.0])
    >>> np.testing.assert_allclose(result['psi'], [0.0, 1.0, 2.0])
    >>> np.testing.assert_allclose(result['profile_values'], [0.0, 2.0, 4.0])
    """
    coordinates = np.asarray(psi_samples, dtype=float).ravel()
    samples = np.asarray(values, dtype=float).ravel()
    query = np.asarray(target, dtype=float)
    if coordinates.size != samples.size or coordinates.size < 2:
        raise ValueError("psi_samples and values require at least two paired samples")
    if not (
        np.isfinite(coordinates).all() and np.isfinite(samples).all() and np.isfinite(query).all()
    ):
        raise ValueError("profile coordinates, values, and target must be finite")
    order = np.argsort(coordinates)
    coordinates, samples = coordinates[order], samples[order]
    coordinates, first = np.unique(coordinates, return_index=True)
    samples = samples[first]
    if coordinates.size < 2:
        raise ValueError("psi samples do not span a usable interval")
    left_value = float(samples[0] if left is None else left)
    right_value = float(samples[-1] if right is None else right)
    if not np.isfinite(left_value) or not np.isfinite(right_value):
        raise ValueError("profile endpoint values must be finite")
    result = np.interp(query.ravel(), coordinates, samples, left=left_value, right=right_value)
    return {
        "values": result.reshape(query.shape),
        "psi": coordinates,
        "profile_values": samples,
    }


scientific_function = evaluate_flux_surface_profile
