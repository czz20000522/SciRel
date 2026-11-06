"""Terminal H2 total-energy conservation error from caller-owned profiles."""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_qh2_total_conservation_diagnostic"]


def _real_numeric(name, value):
    try:
        if not isinstance(value, np.ndarray) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def _terminal_balance_terms(heat_flux, transfer, position):
    """Assemble the left and right finite-volume terms on interval faces."""
    spacing = np.diff(position)
    left = np.zeros_like(position)
    right = np.zeros_like(position)
    left[:-1] = np.diff(heat_flux) / spacing
    right[:-1] = 0.5 * (transfer[1:] + transfer[:-1])
    return left, right


def reduce_qh2_total_conservation_diagnostic(
    axial_position_m,
    total_heat_flux_profile_w_m2,
    total_energy_transfer_rate_profile_w_m3,
):
    """Evaluate the source-defined terminal H2 total-energy balance residual.

    Parameters
    ----------
    axial_position_m : array_like, shape (nx,)
        Finite axial positions with at least two nodes and nonzero, finite
        adjacent differences; decreasing and locally nonmonotonic positions are
        accepted. [m]
    total_heat_flux_profile_w_m2 : array_like, shape (nx,)
        Finite signed total H2 heat-flux profile aligned with ``axial_position_m``.
        [source-labeled W/m^2]
    total_energy_transfer_rate_profile_w_m3 : array_like, shape (nx,)
        Finite signed total H2 energy-transfer profile aligned with the positions.
        [source-labeled W/m^3]

    Returns
    -------
    total_energy_conservation_error_profile_dimensionless : ndarray, shape (nx,)
        Nonnegative normalized absolute difference between the interval flux
        gradient and adjacent transfer mean. The final entry is exactly zero by
        the endpoint convention. [dimensionless on the supplied profile normalization]

    Raises
    ------
    ValueError
        If profiles are non-real, non-finite, malformed, misaligned, have fewer than
        two nodes, have zero/non-finite spacing, or have zero/non-finite global
        normalization; a non-finite output is also rejected.

    See Also
    --------
    reduce_terminal_molecular_energy_transfer : Produces a total transfer profile.
    reduce_terminal_molecular_heat_flux : Produces a total heat-flux profile.

    Notes
    -----
    For each interval, the flux gradient is
    ``(flux[k+1]-flux[k])/(x[k+1]-x[k])`` and the transfer value is the average
    of adjacent nodes. The global normalization is the largest absolute value in
    the two assembled arrays. The diagnostic accepts signed incident profiles;
    the final zero is an endpoint convention, not a checked boundary equation,
    and individual normalized residuals may exceed one. No heat flux, transfer
    rate or terminal state is computed here.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_qh2_total_conservation_diagnostic
    >>> x = np.array([0.0, 1.0, 2.0])
    >>> r = reduce_qh2_total_conservation_diagnostic(x, np.array([0.0, 2.0, 4.0]), np.array([2.0, 2.0, 2.0]))
    >>> assert np.array_equal(r['total_energy_conservation_error_profile_dimensionless'], np.zeros(3))

    """
    position = _real_numeric("axial_position_m", axial_position_m)
    total_heat_flux = _real_numeric("total_heat_flux_profile_w_m2", total_heat_flux_profile_w_m2)
    total_energy_transfer = _real_numeric(
        "total_energy_transfer_rate_profile_w_m3",
        total_energy_transfer_rate_profile_w_m3,
    )
    valid = (
        position.ndim == 1
        and position.size >= 2
        and total_heat_flux.shape == position.shape
        and total_energy_transfer.shape == position.shape
        and np.all(np.isfinite(position))
        and np.all(np.isfinite(total_heat_flux))
        and np.all(np.isfinite(total_energy_transfer))
        and np.all(np.isfinite(np.diff(position)))
        and np.all(np.diff(position) != 0.0)
    )
    if not valid:
        raise ValueError(
            "QH2_total diagnostic requires finite one-dimensional profiles and nonzero axial spacing"
        )

    q1, q2 = _terminal_balance_terms(total_heat_flux, total_energy_transfer, position)
    normalization = np.max(np.abs(np.asarray([q1, q2])))
    if not np.isfinite(normalization):
        raise ValueError("QH2_total diagnostic produced a non-finite normalization")
    if normalization <= 0.0:
        raise ValueError("QH2_total diagnostic requires a strictly positive global normalization")
    error = np.abs(q1 - q2) / normalization
    if not np.all(np.isfinite(error)):
        raise ValueError("QH2_total diagnostic produced a non-finite profile")
    return {"total_energy_conservation_error_profile_dimensionless": error}
