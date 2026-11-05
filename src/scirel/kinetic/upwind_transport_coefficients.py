"""the neutral-transport formulation H/H2 Ak/Bk/Fk/Ck/Dk/Gk spatial transport coefficients."""

from __future__ import annotations

import numpy as np

__all__ = ["assemble_neutral_upwind_transport_coefficients"]


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


def assemble_neutral_upwind_transport_coefficients(
    x_m, vx, collision_frequency_m_inv, source_distribution
):
    r"""Assemble forward/backward trapezoidal spatial coefficients Ak/Bk/Fk/Ck/Dk/Gk from metre coordinates, dimensionless u_x, alpha=nu/Vth in m^-1 and normalized source Q/Vth in F/m.

    Parameters
    ----------
    x_m : real array-like, shape [nx]
        Spatial nodes. [m].
        Constraints: Finite, strictly increasing, at least two nodes, with representable finite positive spatial steps.
    vx : real array-like, shape [nvx]
        Dimensionless axial velocity u_x=v_x/Vth; use the same Vth as every inverse-length collision/source coefficient. [dimensionless (u=v/Vth)].
        Constraints: Finite one-dimensional; no zero nodes; must contain both positive and negative branches.
    collision_frequency_m_inv : real array-like, shape [nvr,nvx,nx]
        Inverse-length total-loss coefficient alpha=nu/Vth. [m^-1].
        Constraints: Finite and nonnegative, shape (nvr,nvx,nx).
    source_distribution : real array-like, shape [nvr,nvx,nx]
        Normalized spatial distribution source Q/Vth; divide a physical F/s source by the same Vth before calling. [m^-4 (F/m)].
        Constraints: Finite, same shape as collision_frequency_m_inv.

    Returns
    -------
    coefficients : mapping of [nvr,nvx,nx] float64 arrays and two index arrays, shape mapping
        The transport coefficient mapping. [mixed].
        Constraints: Exactly Ak, Bk, Fk, Ck, Dk, Gk (each [nvr,nvx,nx]), positive_vx_indices and negative_vx_indices. Ak/Ck are dimensionless, Bk/Dk are metres and Fk/Gk are in m^-3 (F).

    Raises
    ------
    ValueError
        Raises ValueError when x is not strictly increasing (>= 2 nodes), vx has a zero node or lacks a branch, alpha/source are not finite aligned 3-D, or alpha has negative entries. Raises ValueError if finite inputs overflow to non-finite transport coefficients. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.propagate_neutral_generation : Related neutral-transport operation.

    Notes
    -----
        Forward branch (positive vx): Ak = (2*vx - dx*alpha_k)/(2*vx + dx*alpha_{k+1}), Bk = dx/(2*vx + dx*alpha_{k+1}), Fk = dx*(source_{k+1}+source_k)/(2*vx + dx*alpha_{k+1}). Backward branch (negative vx): Ck/Dk/Gk analogous.
    x strictly increasing with >= 2 nodes and finite positive spatial steps, vx one-dimensional with no zero node, alpha/source finite 3-D aligned shapes, alpha nonnegative, vx must contain both positive and negative branches

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_neutral_upwind_transport_coefficients
    >>> x = np.linspace(0, 1, 3)
    >>> vx = np.array([-1.0, 1.0])
    >>> alpha = np.ones((2, 2, 3))
    >>> source = np.ones((2, 2, 3))
    >>> r = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    >>> assert r['Ak'].shape == (2, 2, 3)
    >>> assert np.all(r['Ak'][:, 0, :] == 0.0)  # vx[0]=-1 is negative
    >>> assert np.all(r['Ck'][:, 1, :] == 0.0)  # vx[1]=+1 is positive
    """
    x = _finite_real_array(x_m, "x_m")
    axial = _finite_real_array(vx, "vx")
    alpha = _finite_real_array(collision_frequency_m_inv, "collision_frequency_m_inv")
    source = _finite_real_array(source_distribution, "source_distribution")
    if (
        x.ndim != 1
        or axial.ndim != 1
        or x.size < 2
        or np.any(axial == 0.0)
        or alpha.ndim != 3
        or source.shape != alpha.shape
        or alpha.shape[1:] != (axial.size, x.size)
        or np.any(alpha < 0.0)
    ):
        raise ValueError("x/vx/alpha/source contract is invalid")
    with np.errstate(over="ignore", invalid="ignore"):
        spacings = np.diff(x)
    if not np.all(np.isfinite(spacings)) or np.any(spacings <= 0.0):
        raise ValueError("x_m must have finite positive spatial steps")
    positive, negative = np.flatnonzero(axial > 0.0), np.flatnonzero(axial < 0.0)
    if positive.size == 0 or negative.size == 0:
        raise ValueError("vx must contain positive and negative branches")
    a = np.zeros_like(alpha)
    b = np.zeros_like(alpha)
    f = np.zeros_like(alpha)
    c = np.zeros_like(alpha)
    d = np.zeros_like(alpha)
    g = np.zeros_like(alpha)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        # The spatial stencil is local, so all cells can be assembled in one
        # broadcasted operation.  The boundary column remains the exact zero
        # initialized above.
        dx = spacings[None, None, :]
        positive_v = axial[positive][None, :, None]
        positive_alpha = alpha[:, positive, :]
        positive_denominator = 2.0 * positive_v + dx * positive_alpha[:, :, 1:]
        a[:, positive, :-1] = (
            2.0 * positive_v - dx * positive_alpha[:, :, :-1]
        ) / positive_denominator
        b[:, positive, :-1] = dx / positive_denominator
        f[:, positive, :-1] = (
            dx * (source[:, positive, 1:] + source[:, positive, :-1]) / positive_denominator
        )

        negative_v = axial[negative][None, :, None]
        negative_alpha = alpha[:, negative, :]
        negative_denominator = -2.0 * negative_v + dx * negative_alpha[:, :, :-1]
        c[:, negative, 1:] = (
            -2.0 * negative_v - dx * negative_alpha[:, :, 1:]
        ) / negative_denominator
        d[:, negative, 1:] = dx / negative_denominator
        g[:, negative, 1:] = (
            dx * (source[:, negative, 1:] + source[:, negative, :-1]) / negative_denominator
        )
    if not all(np.all(np.isfinite(field)) for field in (a, b, f, c, d, g)):
        raise ValueError("transport coefficients must be finite")
    return {
        "Ak": a,
        "Bk": b,
        "Fk": f,
        "Ck": c,
        "Dk": d,
        "Gk": g,
        "positive_vx_indices": positive,
        "negative_vx_indices": negative,
    }
