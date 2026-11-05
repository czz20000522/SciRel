"""Normalized charge-exchange source h*integral(alpha_CX*F_previous*d^3u)."""

from __future__ import annotations

import numpy as np

__all__ = ["assemble_simple_charge_exchange_source"]


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
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def assemble_simple_charge_exchange_source(
    target_distribution,
    charge_exchange_frequency_m_inv,
    previous_generation_distribution,
    cylindrical_weight,
    dvx,
):
    r"""Build the normalized cell-local charge-exchange source Q_CX/Vth by multiplying a caller-supplied dimensionless target shape by the velocity integral of alpha_CX times the previous generation distribution.

    Parameters
    ----------
    target_distribution : real array-like, shape [nvr,nvx,nx]
        Caller-provided dimensionless target shape h on the normalized velocity grid; this function neither normalizes h nor divides it by a density. [dimensionless].
        Constraints: Finite aligned three-dimensional shape; signed cells are accepted. Unit weighted integral is a separate caller condition for number-conserving CX regeneration, not a runtime gate.
    charge_exchange_frequency_m_inv : real array-like, shape [nvr,nvx,nx]
        Inverse-length charge-exchange coefficient alpha_CX=nu_CX/Vth, using the same Vth as the normalized quadrature. [m^-1].
        Constraints: Finite and nonnegative, aligned to the target.
    previous_generation_distribution : real array-like, shape [nvr,nvx,nx]
        The previous generation's distribution. [m^-3].
        Constraints: A finite three-dimensional field aligned to the target.
    cylindrical_weight : real array-like, shape [nvr,nvx]
        The cylindrical quadrature weight. [dimensionless normalized velocity-space measure].
        Constraints: Finite and nonnegative, aligned to the leading axes.
    dvx : real array-like, shape [nvx]
        The axial cell sizes. [dimensionless normalized velocity-space measure].
        Constraints: Finite and nonnegative, aligned to the velocity axis.

    Returns
    -------
    scattered_source : float64 array, shape [nvr,nvx,nx]
        Normalized spatial source h*integral(alpha_CX*F_previous*d^3u); the physical distribution-rate source is Vth times this field. [m^-4 (F/m)].
        Constraints: Finite; the target scaled by the per-cell rate.

    Raises
    ------
    ValueError
        Raises ValueError for implicit boolean, string or complex conversion, non-finite inputs, misaligned fields, or negative CX frequency or quadrature values. Raises ValueError when the evaluation produces a non-finite result where the contract demands finiteness; no fallback is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.reduce_atomic_scattered_sources : Related neutral-transport operation.

    Notes
    -----
        The cell-local construction: the rate contraction reduces the previous generation against the CX field, and the target shape is scaled per cell; no cross-cell transport enters
    finite aligned three-dimensional target/frequency/previous fields; finite nonnegative (nvr,nvx) weight and (nvx) dvx; nonnegative frequency, weight, and dvx

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_simple_charge_exchange_source
    >>> target = np.ones((1, 2, 2))
    >>> alpha = np.array([[[2.0, 3.0], [4.0, 5.0]]])
    >>> previous = np.ones((1, 2, 2))
    >>> weight = np.ones((1, 2))
    >>> dvx = np.array([0.5, 1.0])
    >>> result = assemble_simple_charge_exchange_source(target, alpha, previous, weight, dvx)
    >>> np.testing.assert_allclose(result, [[[5.0, 6.5], [5.0, 6.5]]])
    >>> try:
    ...     assemble_simple_charge_exchange_source(target, alpha, previous, weight, np.array([0.5, -1.0]))
    ... except ValueError as error:
    ...     assert 'finite and aligned' in str(error)
    ... else:
    ...     raise AssertionError('a negative dvx must be rejected')
    """
    target = _real_array(target_distribution, "target_distribution")
    alpha = _real_array(charge_exchange_frequency_m_inv, "charge_exchange_frequency_m_inv")
    previous = _real_array(previous_generation_distribution, "previous_generation_distribution")
    weight = _real_array(cylindrical_weight, "cylindrical_weight")
    axial_width = _real_array(dvx, "dvx")
    if (
        target.ndim != 3
        or alpha.shape != target.shape
        or previous.shape != target.shape
        or weight.shape != target.shape[:2]
        or axial_width.shape != (target.shape[1],)
    ):
        raise ValueError(
            "Simple_CX fields must be finite and aligned; rates and quadrature must be nonnegative"
        )
    if np.any(alpha < 0) or np.any(weight < 0) or np.any(axial_width < 0):
        raise ValueError(
            "Simple_CX fields must be finite and aligned; rates and quadrature must be nonnegative"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        # Contract the predecessor once in velocity space; the target field
        # is then scaled independently at every spatial node.
        weighted_previous = weight[:, :, None] * previous * axial_width[None, :, None]
        rate = np.sum(alpha * weighted_previous, axis=(0, 1))
        result = target * rate[None, None, :]
    if not np.all(np.isfinite(result)):
        raise ValueError("the assembled scattered source must be finite")
    return result
