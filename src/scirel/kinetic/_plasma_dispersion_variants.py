"""Private J-pole evaluation for the Maxwellian dispersion family."""

import numpy as np

from scirel._result import Result
from ._generalized_pole_data import POLES


def _evaluate_jpole(z, n):
    """Evaluate validated points with a validated tabulated pole count."""
    a = z
    bhalf, chalf = POLES[n]
    b = np.r_[bhalf, np.conj(bhalf)]
    c = np.r_[chalf, -np.conj(chalf)]
    upper = np.where(a.imag < 0, np.conj(a), a)
    value = np.sum(b / (upper[..., None] - c), axis=-1)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        value = np.where(
            a.imag < 0,
            np.conj(value)
            + 2j * np.sqrt(np.pi) * np.exp(-(a.astype(np.clongdouble) ** 2)).astype(complex),
            value,
        )
    if not np.all(np.isfinite(value)):
        raise FloatingPointError(
            "Z must be finite complex128; received nonfinite J-pole continuation; "
            "legal results: finite w and Z; see scirel.kinetic.plasma-dispersion-function"
        )
    # The same finite-order approximation in Faddeeva normalization, not exact w.
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        w = np.asarray(value / (1j * np.sqrt(np.pi)), dtype=np.complex128)
    if not np.all(np.isfinite(w)):
        raise FloatingPointError(
            "w must be finite complex128; received nonfinite normalized J-pole value; "
            "legal results: finite w and Z; see scirel.kinetic.plasma-dispersion-function"
        )
    return Result(w=w, Z=np.asarray(value, dtype=np.complex128))
