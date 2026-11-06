"""Assemble the explicit neutral Boltzmann RHS state used by the neutral-transport formulation diagnostics."""

from __future__ import annotations

import numpy as np

__all__ = ["assemble_neutral_boltzmann_rhs"]


def _finite_real_array(value, name):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def _assemble_collision_balance(arrays):
    """Form the signed local source balance before applying the speed scale."""
    return (
        arrays["coefficient_source_distribution"]
        + arrays["charge_exchange_source_sum"]
        - arrays["collision_frequency_m_inv"] * arrays["total_distribution"]
        + arrays["elastic_source_sum"]
        + arrays["wall_source_sum"]
    )


def assemble_neutral_boltzmann_rhs(
    thermal_speed_m_s,
    coefficient_source_distribution,
    charge_exchange_source_sum,
    collision_frequency_m_inv,
    total_distribution,
    elastic_source_sum,
    wall_source_sum,
):
    r"""Convert the normalized spatial source balance S+Beta_CX-alpha*F+OmegaM+Swall from F/m to the physical Boltzmann distribution-rate RHS in F/s by one explicit Vth multiplication.

    Parameters
    ----------
    thermal_speed_m_s : real scalar, shape scalar
        The thermal speed. [m/s].
        Constraints: Finite and strictly positive.
    coefficient_source_distribution : real array-like, shape [nvr,nvx,nx]
        The coefficient source term. Supply the normalized spatial source Q/Vth, not a physical F/s source. [m^-4 (F/m)].
        Constraints: Finite 3-D.
    charge_exchange_source_sum : real array-like, shape [nvr,nvx,nx]
        The CX source sum. Supply the normalized spatial source Q/Vth, not a physical F/s source. [m^-4 (F/m)].
        Constraints: Finite 3-D.
    collision_frequency_m_inv : real array-like, shape [nvr,nvx,nx]
        Inverse-length collision coefficient alpha=nu/Vth; the explicit final thermal-speed multiplication restores the physical loss nu*F. [m^-1].
        Constraints: Finite 3-D.
    total_distribution : real array-like, shape [nvr,nvx,nx]
        The total distribution. [m^-3].
        Constraints: Finite 3-D.
    elastic_source_sum : real array-like, shape [nvr,nvx,nx]
        The elastic source sum. Supply the normalized spatial source Q/Vth, not a physical F/s source. [m^-4 (F/m)].
        Constraints: Finite 3-D.
    wall_source_sum : real array-like, shape [nvr,nvx,nx]
        The wall source sum. Supply the normalized spatial source Q/Vth, not a physical F/s source. [m^-4 (F/m)].
        Constraints: Finite 3-D.

    Returns
    -------
    rhs : float64 array, shape [nvr,nvx,nx]
        Physical distribution-rate RHS; one Vth multiplication converts every normalized spatial balance term from F/m to F/s. [m^-3 s^-1 (F/s)].
        Constraints: Finite.

    Raises
    ------
    ValueError
        Raises ValueError when the thermal speed is not finite and positive, any field is non-finite, or the fields do not share one common 3-D shape. Raises ValueError if finite inputs overflow to a non-finite RHS. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.assemble_neutral_upwind_transport_coefficients : Related neutral-transport operation.

    Notes
    -----
        The signed sum: rhs = Vth * (coeff_source + charge_exchange_source_sum - collision_frequency * total_distribution + elastic_source_sum + wall_source_sum).
    thermal speed finite and positive; all six fields finite 3-D arrays with one common shape

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_neutral_boltzmann_rhs
    >>> ones = np.ones((1, 1, 1))
    >>> r = assemble_neutral_boltzmann_rhs(5000.0, ones, ones, ones, ones, ones, ones)
    ... # Vth * (1 + 1 - 1*1 + 1 + 1) = 5000 * 3
    >>> assert r['rhs'][0, 0, 0] == 15000.0
    >>> try:
    ...     assemble_neutral_boltzmann_rhs(float('nan'), ones, ones, ones, ones, ones, ones)
    ... except ValueError as error:
    ...     assert 'positive and finite' in str(error)
    ... else:
    ...     raise AssertionError('NaN thermal speed must be rejected')
    """
    try:
        raw_speed = np.asarray(thermal_speed_m_s)
        if raw_speed.ndim != 0 or raw_speed.dtype.kind not in "iuf":
            raise ValueError
        vth = float(raw_speed)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("thermal_speed_m_s must be positive and finite") from exc
    if not np.isfinite(vth) or vth <= 0.0:
        raise ValueError("thermal_speed_m_s must be positive and finite")
    fields = {
        "coefficient_source_distribution": coefficient_source_distribution,
        "charge_exchange_source_sum": charge_exchange_source_sum,
        "collision_frequency_m_inv": collision_frequency_m_inv,
        "total_distribution": total_distribution,
        "elastic_source_sum": elastic_source_sum,
        "wall_source_sum": wall_source_sum,
    }
    arrays = {name: _finite_real_array(value, name) for name, value in fields.items()}
    reference_shape = arrays["total_distribution"].shape
    if len(reference_shape) != 3 or any(
        array.shape != reference_shape for array in arrays.values()
    ):
        raise ValueError("all RHS fields must be finite three-dimensional arrays with one shape")
    with np.errstate(over="ignore", invalid="ignore"):
        rhs = vth * _assemble_collision_balance(arrays)
    if not np.all(np.isfinite(rhs)):
        raise ValueError("rhs must be finite")
    return {"rhs": rhs}
