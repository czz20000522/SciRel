"""Assemble alpha=nu/Vth [m^-1] on a normalized cylindrical velocity mesh."""

from __future__ import annotations

import numpy as np

__all__ = ["assemble_neutral_total_collision_frequency"]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain finite real values") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite real values")
    return result


def assemble_neutral_total_collision_frequency(
    vr,
    vx,
    base_loss_frequency_m_inv,
    elastic_frequency_m_inv,
    pipe_diameter_m,
    charge_exchange_frequency_m_inv=None,
    charge_exchange_enabled=True,
):
    r"""Assemble the inverse-length neutral total-loss coefficient alpha=nu/Vth from optional charge exchange, base and elastic losses, and wall loss 2*u_r/D on a normalized cylindrical velocity grid.

    Parameters
    ----------
    vr : real array-like, shape [nvr]
        The radial velocity axis. [dimensionless (u=v/Vth)].
        Constraints: Finite, strictly positive nodes.
    vx : real array-like, shape [nvx]
        The axial velocity axis. [dimensionless (u=v/Vth)].
        Constraints: Finite.
    base_loss_frequency_m_inv : real array-like, shape [nx]
        The base ionization/dissociation loss profile. This is the physical frequency divided by the same caller Vth used to normalize vr and vx. [m^-1].
        Constraints: Finite and nonnegative.
    elastic_frequency_m_inv : real array-like, shape [nx]
        The elastic frequency profile. This is the physical frequency divided by the same caller Vth used to normalize vr and vx. [m^-1].
        Constraints: Finite and nonnegative, same shape as the base loss.
    pipe_diameter_m : real array-like, shape [nx]
        The pipe diameter profile. [m].
        Constraints: Finite and nonnegative; exact zero diameter is a declared wall-off sentinel, not the D -> 0+ limit. The formula itself is only used where diameter is positive.
    charge_exchange_frequency_m_inv : real array-like, shape [nvr,nvx,nx]
        The optional CX frequency field. This is the physical frequency divided by the same caller Vth used to normalize vr and vx. [m^-1].
        Constraints: When enabled: required, finite and nonnegative. When disabled: ignored even if supplied.
        Default: None.
    charge_exchange_enabled : boolean scalar, shape scalar
        Whether the CX contribution is included. [dimensionless].
        Constraints: Whether the CX contribution is included.
        Default: True.

    Returns
    -------
    total_frequency_m_inv : float64 array, shape [nvr,nvx,nx]
        Total inverse-length loss coefficient alpha=nu/Vth for the spatial advance; multiply by the caller Vth only when a physical frequency is needed. [m^-1].
        Constraints: Finite; nonnegative on the declared domain (all inputs nonnegative).

    Raises
    ------
    ValueError
        Raises ValueError when the axes/profiles violate the real-value, finiteness, nonnegativity or alignment contract, when charge_exchange_enabled is not boolean, or when enabled charge exchange lacks its explicit field. Raises ValueError when the evaluation produces a non-finite result where the contract demands finiteness; no fallback is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.sum_elastic_frequency_channels : Related neutral-transport operation.

    Notes
    -----
        The assembly order (base + elastic + wall, then + CX when enabled); each spatial cell independently applies wall loss 2*u_r/D only where its diameter is positive, while an exact zero diameter is an explicit wall-off sentinel, not the D -> 0+ limit and not a closed or degenerate geometry model; closing or reflecting the stream is a caller-side transport-boundary decision outside this coefficient assembly; enabling charge exchange without a field fails closed
    finite one-dimensional axes with positive radial nodes; finite nonnegative base/elastic/diameter profiles of one common spatial shape; CX field (when enabled) finite nonnegative (nvr,nvx,nx)

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_neutral_total_collision_frequency
    >>> result = assemble_neutral_total_collision_frequency([1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], np.ones((2, 2, 2)))
    >>> np.testing.assert_allclose(result[:, :, 0], [[10.0, 10.0], [11.0, 11.0]])
    >>> np.testing.assert_allclose(result[:, :, 1], [[11.0, 11.0], [11.0, 11.0]])
    >>> disabled = assemble_neutral_total_collision_frequency([1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], charge_exchange_enabled=False)
    >>> np.testing.assert_allclose(disabled[:, :, 0], [[9.0, 9.0], [10.0, 10.0]])
    >>> try:
    ...     assemble_neutral_total_collision_frequency([1.0], [1.0], [1.0], [1.0], [0.0])
    ... except ValueError as error:
    ...     assert 'charge exchange' in str(error)
    ... else:
    ...     raise AssertionError('enabled CX without a field must fail closed')
    """
    if not isinstance(charge_exchange_enabled, (bool, np.bool_)):
        raise ValueError("charge_exchange_enabled must be a boolean scalar")
    radial = _real_array(vr, "vr")
    axial = _real_array(vx, "vx")
    base = _real_array(base_loss_frequency_m_inv, "base_loss_frequency_m_inv")
    elastic = _real_array(elastic_frequency_m_inv, "elastic_frequency_m_inv")
    diameter = _real_array(pipe_diameter_m, "pipe_diameter_m")
    if (
        radial.ndim != 1
        or axial.ndim != 1
        or base.ndim != 1
        or elastic.shape != base.shape
        or diameter.shape != base.shape
        or radial.size == 0
        or axial.size == 0
        or np.any(radial <= 0.0)
        or np.any(base < 0.0)
        or np.any(elastic < 0.0)
        or np.any(diameter < 0.0)
    ):
        raise ValueError("velocity axes and base/elastic/pipe profiles are invalid")
    shape = (radial.size, axial.size, base.size)
    positive_diameter = diameter > 0.0
    if charge_exchange_enabled:
        if charge_exchange_frequency_m_inv is None:
            raise ValueError("enabled charge exchange needs its explicit frequency field")
        charge_exchange = _real_array(
            charge_exchange_frequency_m_inv, "charge_exchange_frequency_m_inv"
        )
        if charge_exchange.shape != shape or np.any(charge_exchange < 0.0):
            raise ValueError("charge-exchange frequency must be nonnegative and (nvr,nvx,nx)")
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        wall = np.zeros(shape, dtype=float)
        wall[:, :, positive_diameter] = (
            2.0 * radial[:, None, None] / diameter[None, None, positive_diameter]
        )
        total = base[None, None, :] + elastic[None, None, :] + wall
        if charge_exchange_enabled:
            total = total + charge_exchange
    if not np.all(np.isfinite(total)):
        raise ValueError("the assembled total loss frequency is not finite")
    return total
