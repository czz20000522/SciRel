"""Pure-Python rational pole-table access used by the kinetic dispersion API."""

from types import MappingProxyType

import numpy as np

from .rational import _fixed_poles


def _real(value, name):
    raw = np.asarray(value)
    if (
        raw.ndim
        or raw.dtype.kind not in "iuf"
        or not np.isfinite(raw)
        or isinstance(value, (bool, np.bool_))
    ):
        raise ValueError(f"{name} must be a finite real scalar")
    return float(raw)


class _State:
    def __init__(self, state):
        self.state = MappingProxyType(state)


def pole_coefficients(J=8):
    r"""Return ordered J4/J8 tables or the precision-corrected J12/I16/K8 pole-residue table.

    Parameters
    ----------
    J : integer numeric
        Number of rational terms in Z(z)=sum_j bzj/(z-czj). [dimensionless] Shape: scalar. Default: 8.
        Exactly4,8 or12; J12/I16/K8 table is intentionally regenerated at high precision and rounded to
        binary64.

    Returns
    -------
    state : object
        J-pole table object; access J, bzj and czj through result.state. [mixed (J dimensionless, bzj/czj
        complex coefficients)] Shape: object with a mapping state. Accessible in returned operator
        result.state; scientific meaning applies only to a compatible completed predecessor. Empty inactive
        arrays are preserved.

    Raises
    ------
    ValueError
        Declared Python guards raise ValueError; unsupported J is rejected without a table fallback.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    Z_J(z)=sum_j bzj[j]/(z-czj[j]); paired tables obey sum b=-1,sum bc=0,sum bc^2=-1/2 within binary64
    precision. J12 regenerates the prescribed Padé relation at 80 digits, checked against a 120-digit
    construction before rounding to binary64; the J4/J8 tabulated values are kept as given. Explicit
    rational approximation or two-Gaussian representation for magnetized kinetic response. Assumptions:
    Linear small-amplitude response. Caller retains the explicit truncation, state provenance and
    normalization.

    References
    ----------
    Xie and Xiao, PDRK: A General Kinetic Dispersion Relation Solver for Magnetized Plasma, Plasma Science and Technology 18 (2016).

    Examples
    --------
    >>> from scirel.kinetic.dispersion import magnetized
    >>> r = magnetized.pole_coefficients(8)
    >>> assert r.state['bzj'].size == 8
    """
    value = _real(J, "J")
    if value not in (4, 8, 12):
        raise ValueError("J must be 4, 8 or 12")
    J = int(value)
    bzj, czj = _fixed_poles(J)
    return _State(
        {"J": np.array([[J]], float), "bzj": bzj.reshape(1, -1), "czj": czj.reshape(1, -1)}
    )


__all__ = ["pole_coefficients"]
