"""the neutral-transport formulation first-flight and scattered-generation bidirectional propagation."""

from __future__ import annotations

import numpy as np

__all__ = ["propagate_neutral_generation"]


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


def _propagate_branch(generation, coefficient, source_term, indices, forward):
    """Apply one first-order upwind recurrence along a velocity branch."""
    if forward:
        for k in range(generation.shape[2] - 1):
            generation[:, indices, k + 1] = (
                generation[:, indices, k] * coefficient[:, indices, k] + source_term[:, indices, k]
            )
    else:
        for k in range(generation.shape[2] - 1, 0, -1):
            generation[:, indices, k - 1] = (
                generation[:, indices, k] * coefficient[:, indices, k] + source_term[:, indices, k]
            )


def propagate_neutral_generation(
    vx,
    Ak,
    Bk,
    Fk,
    Ck,
    Dk,
    Gk,
    generation_kind,
    incoming_boundary=None,
    scattered_source_distribution=None,
):
    r"""Propagate one neutral distribution generation in space with dimensionless axial nodes and normalized inverse-length transport/source coefficients.

    Parameters
    ----------
    vx : real array-like, shape [nvx]
        Velocity axis. [dimensionless (u=v/Vth)].
        Constraints: Finite one-dimensional with both positive and negative branches.
    Ak : real array-like, shape [nvr,nvx,nx]
        Forward diagonal coefficient. [dimensionless].
        Constraints: Finite 3-D.
    Bk : real array-like, shape [nvr,nvx,nx]
        Forward source coefficient (scattered branch). [m].
        Constraints: Finite 3-D.
    Fk : real array-like, shape [nvr,nvx,nx]
        Forward source term (first-flight branch). [m^-3].
        Constraints: Finite 3-D.
    Ck : real array-like, shape [nvr,nvx,nx]
        Backward diagonal coefficient. [dimensionless].
        Constraints: Finite 3-D.
    Dk : real array-like, shape [nvr,nvx,nx]
        Backward source coefficient (scattered). [m].
        Constraints: Finite 3-D.
    Gk : real array-like, shape [nvr,nvx,nx]
        Backward source term. [m^-3].
        Constraints: Finite 3-D.
    generation_kind : string scalar, shape scalar
        The generation branch selector. [dimensionless].
        Constraints: Exactly 'first_flight' or 'scattered'.
    incoming_boundary : real array-like, shape [nvr,nvx]
        The incoming boundary distribution (first_flight only). [m^-3].
        Constraints: Required for first_flight; must be finite and aligned; must be None for scattered.
        Default: None.
    scattered_source_distribution : real array-like, shape [nvr,nvx,nx]
        The scattered source distribution (scattered only). [m^-4 (F/m)].
        Constraints: Required for scattered; must be finite and aligned; must be None for first_flight.
        Default: None.

    Returns
    -------
    generation : float64 array, shape [nvr,nvx,nx]
        The propagated generation distribution. [m^-3].
        Constraints: Finite.

    Raises
    ------
    ValueError
        Raises ValueError when vx lacks branches, coefficient fields are not finite aligned 3-D, generation_kind is invalid, or the wrong source/boundary is supplied. Raises ValueError if finite inputs overflow to a non-finite generation. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.assemble_neutral_upwind_transport_coefficients : Related neutral-transport operation.

    Notes
    -----
        first_flight: forward from boundary on positive vx using Fk as source term, backward on negative vx using Gk as source term; scattered: forward on positive vx using Bk as source coefficient, backward on negative vx using Dk as source coefficient.
    vx one-dimensional with both positive and negative branches; six coefficient fields finite aligned 3-D; generation_kind in {first_flight, scattered}; first_flight requires incoming_boundary; scattered requires scattered_source_distribution; nx must be at least one (a zero-node spatial axis fails closed with a named ValueError rather than a raw IndexError)

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_neutral_upwind_transport_coefficients, propagate_neutral_generation
    >>> x = np.linspace(0, 1, 3)
    >>> vx = np.array([-1.0, 1.0])
    >>> alpha = np.ones((2, 2, 3))
    >>> source = np.ones((2, 2, 3))
    >>> r = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)
    >>> boundary = np.ones((2, 2))
    >>> gen = propagate_neutral_generation(vx, r['Ak'], r['Bk'], r['Fk'], r['Ck'], r['Dk'], r['Gk'], generation_kind='first_flight', incoming_boundary=boundary)
    >>> assert gen.shape == (2, 2, 3)
    >>> assert np.all(np.isfinite(gen))
    """
    axial = _finite_real_array(vx, "vx")
    coefficients = [
        _finite_real_array(value, name)
        for name, value in zip(("Ak", "Bk", "Fk", "Ck", "Dk", "Gk"), (Ak, Bk, Fk, Ck, Dk, Gk))
    ]
    a, b, f, c, d, g = coefficients
    if (
        axial.ndim != 1
        or any(value.ndim != 3 or value.shape != a.shape for value in coefficients)
        or a.shape[1] != axial.size
    ):
        raise ValueError("vx and coefficient fields are invalid")
    positive, negative = axial > 0.0, axial < 0.0
    if (
        not np.any(positive)
        or not np.any(negative)
        or not isinstance(generation_kind, str)
        or generation_kind not in ("first_flight", "scattered")
    ):
        raise ValueError("vx branches or generation_kind are invalid")
    if a.shape[2] < 1:
        raise ValueError("nx must be at least one for generation propagation")
    generation = np.zeros_like(a)
    if generation_kind == "first_flight":
        if incoming_boundary is None or scattered_source_distribution is not None:
            raise ValueError("first_flight needs exactly one finite incoming_boundary")
        boundary = _finite_real_array(incoming_boundary, "incoming_boundary")
        if boundary.shape != a.shape[:2]:
            raise ValueError("first_flight needs exactly one finite incoming_boundary")
        generation[:, positive, 0] = boundary[:, positive]
        with np.errstate(over="ignore", invalid="ignore"):
            _propagate_branch(generation, a, f, positive, True)
            _propagate_branch(generation, c, g, negative, False)
    else:
        if scattered_source_distribution is None or incoming_boundary is not None:
            raise ValueError("scattered needs exactly one finite scattered_source_distribution")
        source = _finite_real_array(scattered_source_distribution, "scattered_source_distribution")
        if source.shape != a.shape:
            raise ValueError("scattered needs exactly one finite scattered_source_distribution")
        with np.errstate(over="ignore", invalid="ignore"):
            positive_source = np.zeros_like(b)
            negative_source = np.zeros_like(d)
            positive_source[:, :, :-1] = b[:, :, :-1] * (source[:, :, 1:] + source[:, :, :-1])
            negative_source[:, :, 1:] = d[:, :, 1:] * (source[:, :, 1:] + source[:, :, :-1])
            _propagate_branch(generation, a, positive_source, positive, True)
            _propagate_branch(generation, c, negative_source, negative, False)
    if not np.all(np.isfinite(generation)):
        raise ValueError("generation must be finite")
    return generation
