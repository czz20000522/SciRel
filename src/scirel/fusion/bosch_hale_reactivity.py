"""Bosch-Hale Maxwellian fusion reactivity for four light-ion channels."""

import numpy as np


# BG, MRC2, C1..C7 from the saved ASCOT5 Bosch-Hale relation.
_CHANNELS = {
    "DT": (34.3827, 1124656, 1.17302e-9, 1.51361e-2, 7.51886e-2,
           4.60643e-3, 1.35000e-2, -1.06750e-4, 1.36600e-5),
    "DHe3": (68.7508, 1124572, 5.51036e-10, 6.41918e-3, -2.02896e-3,
             -1.91080e-5, 1.35776e-4, 0.0, 0.0),
    "DD_Tp": (31.3970, 937814, 5.65718e-12, 3.41267e-3, 1.99167e-3,
              0.0, 1.05060e-5, 0.0, 0.0),
    "DD_He3n": (31.3970, 937814, 5.43360e-12, 5.85778e-3, 7.68222e-3,
                0.0, -2.96400e-6, 0.0, 0.0),
}


def evaluate_bosch_hale_reactivity(ion_temperature_kev, *, reaction="DT"):
    """Return Maxwellian ``<sigma v>`` in m^3/s, without temperature clipping.

    ``reaction`` is one of ``DT``, ``DHe3``, ``DD_Tp`` or ``DD_He3n``.
    Scalar input returns a float; an array retains its shape. Positive, finite
    temperatures are required, and unrepresentable fit values fail closed.
    This evaluates the fitted relation; it does not assert physical accuracy
    for every positive temperature.
    """
    if not isinstance(reaction, str) or reaction not in _CHANNELS:
        raise ValueError("reaction must be DT, DHe3, DD_Tp or DD_He3n")
    try:
        raw = np.asarray(ion_temperature_kev, dtype=object)
        values = np.asarray(ion_temperature_kev)
    except (TypeError, ValueError) as error:
        raise ValueError("ion_temperature_kev must contain positive finite real values") from error
    if (
        raw.size == 0
        or any(isinstance(value, (bool, np.bool_)) for value in raw.flat)
        or values.dtype.kind not in "iuf"
    ):
        raise ValueError("ion_temperature_kev must contain positive finite real values")
    try:
        temperatures = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("ion_temperature_kev must contain positive finite real values") from error
    if not np.all(np.isfinite(temperatures)) or np.any(temperatures <= 0):
        raise ValueError("ion_temperature_kev must contain positive finite real values")

    bg, mrc2, c1, c2, c3, c4, c5, c6, c7 = _CHANNELS[reaction]
    with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
        theta = temperatures / (
            1.0 - temperatures * (c2 + temperatures * (c4 + temperatures * c6))
            / (1.0 + temperatures * (c3 + temperatures * (c5 + temperatures * c7)))
        )
        xi = np.power(bg * bg / (4.0 * theta), 1.0 / 3.0)
        result = (
            c1 * theta * np.sqrt(xi / (mrc2 * temperatures ** 3))
            * np.exp(-3.0 * xi) * 1.0e-6
        )
    if not np.all(np.isfinite(theta)) or np.any(theta <= 0) or not np.all(np.isfinite(result)):
        raise ValueError("Bosch-Hale reactivity is not representable for these inputs")
    if temperatures.ndim == 0:
        return float(result)
    return result


__all__ = ["evaluate_bosch_hale_reactivity"]
