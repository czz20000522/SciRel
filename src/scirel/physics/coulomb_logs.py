"""Dimensionless Coulomb-logarithm estimates used by SciRel collision models.

Temperatures are in keV, densities in m^-3, charge numbers are dimensionless,
and each result is dimensionless.  These are mathematical weak-coupling
estimates: positive finite inputs are required, while deciding whether a
computed logarithm is physically adequate (for example, positive and large
enough for a selected collision model) remains the caller's responsibility.

The relations are evaluated in logarithmic form so the dimensional product
``1000*T`` is never formed. They are mathematical weak-coupling estimates;
the caller remains responsible for selecting a collision model and checking
whether a returned logarithm is physically adequate.

``calculate_log_lambda_ee`` and ``calculate_log_lambda_ei`` evaluate the
high-temperature (quantum cutoff, ``b_min = lambda_dB``) branch, which the standard classical-cutoff convention
switches at ``T_e ~ 10 Z^2 eV`` (source provenance pending, see below); for the Z=1 signatures here
that is 10 eV. Below it the classical cutoff ``b_cl = Z e^2/(4 pi eps0 k T)``
sets ``b_min`` and the quantum branch overstates the logarithm, so those two
relations warn below the boundary (issue #10 item 3). ``calculate_log_lambda_ii``
already uses the classical cutoff form and is not affected.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from scirel import ApplicabilityWarning

# Low-temperature boundary for the electron branches, T_e ~ 10 Z^2 eV. The attribution of this
# value (and of the classical forms below) is NOT verified against an original source: the
# Formulary PDF was unavailable, so the contracts say "a classical-cutoff form (source pending)"
# rather than naming it as a verified citation.
# These signatures carry no charge number, so Z = 1 and the boundary is 10 eV = 0.01 keV.
_QUANTUM_BRANCH_LOW_KEV = 0.01

__all__ = [
    "calculate_log_lambda_ee",
    "calculate_log_lambda_ei",
    "calculate_log_lambda_ii",
]


def _positive_broadcast(*values):
    """Convert and broadcast named positive real inputs."""
    arrays = []
    for name, value in values:
        try:
            raw = np.asarray(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a finite positive real value") from exc
        if (
            raw.dtype.kind not in "iuf"
            or raw.size == 0
            or np.ma.isMaskedArray(value)
            or any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError(f"{name} must be a finite positive real value")
        arr = np.asarray(raw, dtype=np.float64)
        if np.any(~np.isfinite(arr)) or np.any(arr <= 0):
            raise ValueError(f"{name} must be finite and strictly positive")
        arrays.append(arr)
    try:
        return np.broadcast_arrays(*arrays)
    except ValueError as exc:
        raise ValueError("Coulomb-log inputs must be broadcast-compatible") from exc


def _finite_result(value, name):
    """Reject a valid input whose result left binary64 range."""
    if not np.all(np.isfinite(value)):
        raise FloatingPointError(f"{name} is not representable")
    return value


def _lowest_sample(temperature_kev, density_m3):
    """Return the (temperature, density) pair of the lowest-temperature sample."""
    temperatures, densities = np.broadcast_arrays(
        np.asarray(temperature_kev, dtype=float), np.asarray(density_m3, dtype=float)
    )
    index = np.unravel_index(np.argmin(temperatures), temperatures.shape)
    return float(temperatures[index]), float(densities[index])


def _lowest_ev(temperature_kev):
    """Return the lowest input temperature in eV, or None when no sample is below the boundary."""
    values = np.asarray(temperature_kev)
    if not np.any(values < _QUANTUM_BRANCH_LOW_KEV):
        return None
    return float(np.min(values)) * 1000.0


def _format_deviation(deviation):
    """Render a deviation for the warning, or say it is not representable."""
    if deviation is None:
        return "a deviation that is not representable at this extreme sample"
    return f"{deviation:+.2%}"


def _deviation_at(temperature_kev, density_m3, constant, offset, slope):
    """Return quantum/classical - 1 at the lowest-temperature sample, or None.

    Both forms are evaluated in logarithmic form, exactly as the public relations
    are: the classical-cutoff value is ``offset - 0.5*ln(n_e/1e6) + slope*ln(T_eV)``,
    which cannot overflow for a subnormal temperature or the largest finite
    density.  When the classical value is zero or non-finite the numeric deviation
    is undefined, so the warning reports that instead of quoting a number.
    """
    temperature, density = _lowest_sample(temperature_kev, density_m3)
    t_eV = temperature * 1000.0
    if not (t_eV > 0.0 and density > 0.0):
        return None
    log_temperature = math.log(t_eV)
    # log(n_e / 1e6) is formed as a difference so a subnormal density cannot
    # underflow to zero before the logarithm is taken.
    log_density = math.log(density) - math.log(1e6)
    quantum = constant + math.log(1000.0) + math.log(temperature) - 0.5 * math.log(density)
    classical_value = offset - 0.5 * log_density + slope * log_temperature
    if classical_value == 0.0 or not math.isfinite(classical_value):
        return None
    deviation = quantum / classical_value - 1.0
    return deviation if math.isfinite(deviation) else None


def _ee_deviation_at(temperature_kev, density_m3):
    """e-e deviation against ``24 - ln(n_e^0.5 T_e^-1)``."""
    return _deviation_at(temperature_kev, density_m3, 31.0, 24.0, 1.0)


def _ei_deviation_at(temperature_kev, density_m3):
    """e-i deviation against ``23 - ln(n_e^0.5 Z T_e^-1.5)``."""
    return _deviation_at(temperature_kev, density_m3, 31.3, 23.0, 1.5)


def _warn_below_quantum_branch_ee(temperature_kev, density_m3):
    """Warn once per call for e-e samples below the quantum-branch boundary.

    The e-e pair has its own classical reference, ``24 - ln(n_e^0.5 T_e^-1)``
    (``T_e`` in eV, ``n_e`` in cm^-3), and the two branches share the same
    temperature dependence, so the gap is small.  The deviation is computed at
    the offending sample instead of quoting a fixed percentage: the relative gap
    grows with density (the same absolute offset is divided by a smaller
    logarithm), so a fixed number would mislead at other densities.
    """
    lowest_ev = _lowest_ev(temperature_kev)
    if lowest_ev is None:
        return
    deviation = _ee_deviation_at(temperature_kev, density_m3)
    warnings.warn(
        "calculate_log_lambda_ee: electron temperature below the 10 Z^2 eV quantum-branch boundary"
        f" of (Z = 1 here, so 10 eV; lowest input {lowest_ev:.6g} eV) returns the high-temperature"
        " value of the electron-electron Coulomb logarithm. Below the boundary the classical cutoff"
        " b_cl = e^2/(4 pi eps0 k T) sets the minimum impact parameter and a classical-cutoff e-e"
        " form 24 - ln(n_e^0.5 T_e^-1) (T_e in eV, n_e in cm^-3; source provenance pending,"
        f" UNKNOWN) applies. At that sample (n_e = {_lowest_sample(temperature_kev, density_m3)[1]:.6g}"
        f" m^-3) the returned value is {_format_deviation(deviation)} above that form; the relative"
        " gap grows with density because the absolute offset is divided by a smaller logarithm."
        " The value is returned unchanged; the classical branch is a separate relation"
        " (scirel.physics.coulomb-ee)",
        ApplicabilityWarning,
        stacklevel=3,
    )


def _warn_below_quantum_branch_ei(temperature_kev, density_m3):
    """Warn once per call for e-i samples below the quantum-branch boundary.

    The e-i classical reference is ``23 - ln(n_e^0.5 Z T_e^-1.5)`` (``T_e`` in eV,
    ``n_e`` in cm^-3).  Its temperature dependence differs, so the gap is large
    below the boundary and the two forms cross near 16.2 eV -- above the crossing
    the quantum form reads *lower*, which is why the boundary is not a "below is
    wrong, above is right" rule.  The deviation is computed at the offending
    sample rather than quoted as a fixed percentage, because it grows with
    density.
    """
    lowest_ev = _lowest_ev(temperature_kev)
    if lowest_ev is None:
        return
    deviation = _ei_deviation_at(temperature_kev, density_m3)
    warnings.warn(
        "calculate_log_lambda_ei: electron temperature below the 10 Z^2 eV quantum-branch boundary"
        f" of (Z = 1 here, so 10 eV; lowest input {lowest_ev:.6g} eV) returns the high-temperature"
        " value of the electron-ion Coulomb logarithm. Below the boundary the classical cutoff"
        " b_cl = Z e^2/(4 pi eps0 k T) sets the minimum impact parameter and a classical-cutoff"
        " e-i form 23 - ln(n_e^0.5 Z T_e^-1.5) (T_e in eV, n_e in cm^-3; source provenance"
        f" pending, UNKNOWN) applies. At that sample (n_e = {_lowest_sample(temperature_kev, density_m3)[1]:.6g}"
        f" m^-3) the returned value is {_format_deviation(deviation)} above that form, and the two"
        " forms cross near 16.2 eV, above which this quantum form reads lower; the relative gap"
        " grows with density. The value is returned unchanged; the classical branch is a separate"
        " relation (scirel.physics.coulomb-ei)",
        ApplicabilityWarning,
        stacklevel=3,
    )


def calculate_log_lambda_ee(T_e, n_e):
    """Return ``31 - 0.5*ln(n_e) + ln(1000*T_e)`` for e-e collisions.

    Parameters
    ----------
    T_e : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Electron temperature [keV]. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.
    n_e : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Electron density [m^-3]. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.

    Returns
    -------
    result : float64 scalar or array, shape broadcast shape
        Coulomb logarithm. Finite signed mathematical formula value; physical
        suitability for a collision model is caller-owned.

    Raises
    ------
    FloatingPointError
        Raises FloatingPointError if accepted finite inputs produce an
        unrepresentable output; no fallback is returned.
    ValueError
        Raises ValueError for boolean/string/complex/masked or empty input,
        non-finite values, malformed or incompatible shape, and the nonpositive
        or singular domains named by the callable contract.
    ApplicabilityWarning
        Emitted rather than raised, and listed here because the contract's
        ``failure_semantics`` names it: any input temperature below ``10 eV``
        returns the value below with this warning instead of raising (see
        Warns).

    Warns
    -----
    ApplicabilityWarning
        If any input temperature is below 10 eV, the ``T_e ~ 10 Z^2 eV``
        boundary for this quantum-cutoff (``b_min = lambda_dB``) branch at Z = 1.
        Below it the classical cutoff ``b_cl = e^2/(4 pi eps0 k T)`` sets the
        minimum impact parameter and a classical-cutoff **electron-electron** form
        ``24 - ln(n_e^0.5 T_e^-1)`` (source provenance pending, UNKNOWN)
        (``T_e`` in eV, ``n_e`` in cm^-3) applies. The two e-e branches share the
        same temperature dependence, so the value returned here stays close to
        that form: about +1.37% at 0.1 eV and +1.02% at 1 eV for
        ``n_e = 1e19 m^-3``. Do not reuse the e-i numbers here -- the e-i pair
        has a different classical form and a much larger gap. The value is
        returned unchanged; the classical branch is a separate relation.

    See Also
    --------
    calculate_log_lambda_ei : Electron-ion form (31.3), the lnLambda_e of Sauter (1999).
    calculate_log_lambda_ii : Ion-ion form.

    Examples
    --------
    >>> import warnings
    >>> import numpy as np
    >>> from scirel.physics import calculate_log_lambda_ee
    >>> r=calculate_log_lambda_ee(2., 1e19)
    >>> assert np.isfinite(r)
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter('always')
    ...     low = calculate_log_lambda_ee(0.005, 1e19)
    >>> assert np.isfinite(low) and len(caught) == 1
    """
    T, n = _positive_broadcast(("T_e", T_e), ("n_e", n_e))
    _warn_below_quantum_branch_ee(T, n)
    with np.errstate(over="ignore", invalid="ignore"):
        result = 31.0 + np.log(1000.0) + np.log(T) - 0.5 * np.log(n)
    return _finite_result(result, "electron-electron Coulomb logarithm")


def calculate_log_lambda_ei(T_e, n_e):
    """Return ``31.3 - 0.5*ln(n_e) + ln(1000*T_e)`` for e-i collisions.

    Parameters
    ----------
    T_e : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Electron temperature [keV]. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.
    n_e : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Electron density [m^-3]. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.

    Returns
    -------
    result : float64 scalar or array, shape broadcast shape
        Coulomb logarithm. Finite signed mathematical formula value; physical
        suitability for a collision model is caller-owned.

    Raises
    ------
    FloatingPointError
        Raises FloatingPointError if accepted finite inputs produce an
        unrepresentable output; no fallback is returned.
    ValueError
        Raises ValueError for boolean/string/complex/masked or empty input,
        non-finite values, malformed or incompatible shape, and the nonpositive
        or singular domains named by the callable contract.
    ApplicabilityWarning
        Emitted rather than raised, and listed here because the contract's
        ``failure_semantics`` names it: any input temperature below ``10 eV``
        returns the value below with this warning instead of raising (see
        Warns).

    Warns
    -----
    ApplicabilityWarning
        If any input temperature is below 10 eV, the ``T_e ~ 10 Z^2 eV``
        boundary for this quantum-cutoff (``b_min = lambda_dB``) branch at Z = 1.
        Below it the classical cutoff ``b_cl = Z e^2/(4 pi eps0 k T)`` sets the
        minimum impact parameter and a classical-cutoff **electron-ion** form
        (source provenance pending, UNKNOWN)
        ``23 - ln(n_e^0.5 Z T_e^-1.5)`` (``T_e`` in eV, ``n_e`` in cm^-3)
        applies; the value returned here is about +55% above it at 0.1 eV and
        +17% at 1 eV for ``n_e = 1e19 m^-3``. The two forms cross near 16.2 eV,
        and above the crossing this quantum form reads *lower*, so the boundary
        is not a "below is wrong, above is right" rule. The value is returned
        unchanged; the classical branch is a separate relation.

    See Also
    --------
    calculate_log_lambda_ee : Wesson electron-electron form (31.0).
    calculate_log_lambda_ii : Ion-ion form.

    Examples
    --------
    >>> import warnings
    >>> import numpy as np
    >>> from scirel.physics import calculate_log_lambda_ei
    >>> r=calculate_log_lambda_ei(2., 1e19)
    >>> assert np.isfinite(r)
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter('always')
    ...     low = calculate_log_lambda_ei(0.005, 1e19)
    >>> assert np.isfinite(low) and len(caught) == 1
    """
    T, n = _positive_broadcast(("T_e", T_e), ("n_e", n_e))
    _warn_below_quantum_branch_ei(T, n)
    with np.errstate(over="ignore", invalid="ignore"):
        result = 31.3 + np.log(1000.0) + np.log(T) - 0.5 * np.log(n)
    return _finite_result(result, "electron-ion Coulomb logarithm")


def calculate_log_lambda_ii(T_i, n_i, Z_i):
    """Return ``30 - .5 ln(n_i) + 1.5 ln(1000*T_i) - 3 ln(Z_i)``.

    Parameters
    ----------
    T_i : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Ion temperature [keV]. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.
    n_i : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Ion density [m^-3]. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.
    Z_i : real integer/float numeric scalar or array-like; converted to float64, shape broadcast
        Ion charge number. finite and strictly positive; nonempty,
        boolean/string/complex/masked values rejected.

    Returns
    -------
    result : float64 scalar or array, shape broadcast shape
        Coulomb logarithm. Finite signed mathematical formula value; physical
        suitability for a collision model is caller-owned.

    Raises
    ------
    FloatingPointError
        Raises FloatingPointError if accepted finite inputs produce an
        unrepresentable output; no fallback is returned.
    ValueError
        Raises ValueError for boolean/string/complex/masked or empty input,
        non-finite values, malformed or incompatible shape, and the nonpositive
        or singular domains named by the callable contract.

    See Also
    --------
    calculate_log_lambda_ei : Electron-ion form.
    calculate_log_lambda_ee : Electron-electron form.

    Notes
    -----
    This relation already uses the classical cutoff branch (``T_i^1.5``), which
    is the classical-cutoff form used for ion-ion collisions, so the
    ``T_e ~ 10 Z^2 eV`` boundary that applies to the electron forms does not
    trigger a warning here (issue #10 item 3).

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.physics import calculate_log_lambda_ii
    >>> r=calculate_log_lambda_ii(3., 2e19, 2.)
    >>> assert np.isfinite(r)
    """
    T, n, z = _positive_broadcast(("T_i", T_i), ("n_i", n_i), ("Z_i", Z_i))
    with np.errstate(over="ignore", invalid="ignore"):
        result = 30.0 + 1.5 * (np.log(1000.0) + np.log(T)) - 0.5 * np.log(n) - 3.0 * np.log(z)
    return _finite_result(result, "ion-ion Coulomb logarithm")
