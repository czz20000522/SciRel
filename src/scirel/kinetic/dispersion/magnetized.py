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
    """Exact current-source J=4/8/12 rational Z tables, ordered bzj/czj."""
    value = _real(J, "J")
    if value not in (4, 8, 12):
        raise ValueError("J must be 4, 8 or 12")
    J = int(value)
    bzj, czj = _fixed_poles(J)
    return _State(
        {"J": np.array([[J]], float), "bzj": bzj.reshape(1, -1), "czj": czj.reshape(1, -1)}
    )


__all__ = ["pole_coefficients"]
