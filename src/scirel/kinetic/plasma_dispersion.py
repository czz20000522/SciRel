"""Analytic plasma dispersion function for dimensionless complex arguments."""

import numpy as np


def evaluate_plasma_dispersion(z):
    """Return the Faddeeva function ``w(z)`` and ``Z(z) = i*sqrt(pi)*w(z)``.

    Input shape is preserved. The caller supplies the dimensionless argument;
    velocity, frequency and wave-number conventions belong to the caller.
    """
    try:
        raw = np.asarray(z, dtype=object)
        values = np.asarray(z)
    except (TypeError, ValueError) as error:
        raise ValueError("z must contain finite numeric values") from error
    if (
        raw.size == 0
        or any(isinstance(value, (bool, np.bool_)) for value in raw.flat)
        or values.dtype.kind not in "iufc"
    ):
        raise ValueError("z must contain finite numeric values")
    values = np.asarray(values, dtype=np.complex128)
    if not np.all(np.isfinite(values)):
        raise ValueError("z must contain finite numeric values")

    # Keep the analytic backend out of import-time and rejected-input paths.
    # SciPy remains a declared core runtime dependency; loading it only after
    # the input contract is established keeps the public namespace cheap while
    # preserving the exact backend and numerical behavior for valid calls.
    from scipy.special import wofz

    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        w = np.asarray(wofz(values), dtype=np.complex128)
        dispersion = np.asarray(1j * np.sqrt(np.pi) * w, dtype=np.complex128)
    if not np.all(np.isfinite(w)) or not np.all(np.isfinite(dispersion)):
        raise ValueError("plasma dispersion value is not representable")
    return {"w": w, "Z": dispersion}


__all__ = ["evaluate_plasma_dispersion"]
