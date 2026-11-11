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
high-temperature (quantum cutoff, ``b_min = lambda_dB``) branch, which the NRL
Plasma Formulary uses above ``T_e ~ 10 Z^2 eV``; for the Z=1 signatures here
that is 10 eV. Below it the classical cutoff ``b_cl = Z e^2/(4 pi eps0 k T)``
sets ``b_min`` and the quantum branch overstates the logarithm, so those two
relations warn below the boundary (issue #10 item 3). ``calculate_log_lambda_ii``
already uses the classical cutoff form and is not affected.
"""

from __future__ import annotations

import warnings

import numpy as np

from scirel import ApplicabilityWarning

# NRL Plasma Formulary low-temperature boundary for the electron branches: T_e ~ 10 Z^2 eV.
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


def _warn_below_quantum_branch(temperature_kev, name, contract_id):
    """Warn once per call when a sample sits below the NRL quantum-branch boundary."""
    if np.any(np.asarray(temperature_kev) < _QUANTUM_BRANCH_LOW_KEV):
        lowest_ev = float(np.min(np.asarray(temperature_kev))) * 1000.0
        warnings.warn(
            f"{name}: electron temperature below the NRL quantum-branch boundary of 10 Z^2 eV"
            f" (Z = 1 here, so 10 eV; lowest input {lowest_ev:.6g} eV) returns the high-temperature"
            " value of the Coulomb logarithm: relative to the NRL classical form below the boundary"
            " (23 - ln(n_e^0.5 Z T_e^-1.5), T_e in eV, n_e in cm^-3) it reads about +49% at"
            " 0.1 eV and +14% at 1 eV for n_e = 1e19 m^-3, because there the classical cutoff"
            f" b_cl = Z e^2/(4 pi eps0 k T) sets the minimum impact parameter ({contract_id})",
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
        If any input temperature is below 10 eV, the NRL Plasma Formulary
        boundary ``T_e ~ 10 Z^2 eV`` for this quantum-cutoff (``b_min =
        lambda_dB``) branch at Z = 1. Below it the classical cutoff
        ``b_cl = Z e^2/(4 pi eps0 k T)`` sets the minimum impact parameter and
        the value returned here overstates the logarithm relative to the NRL
        classical form: about +49% at 0.1 eV and +14% at 1 eV for
        ``n_e = 1e19 m^-3``. The value is returned unchanged; the classical
        branch is a separate relation.

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
    _warn_below_quantum_branch(T, "calculate_log_lambda_ee", "scirel.physics.coulomb-ee")
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
        If any input temperature is below 10 eV, the NRL Plasma Formulary
        boundary ``T_e ~ 10 Z^2 eV`` for this quantum-cutoff (``b_min =
        lambda_dB``) branch at Z = 1. Below it the classical cutoff
        ``b_cl = Z e^2/(4 pi eps0 k T)`` sets the minimum impact parameter and
        the value returned here overstates the logarithm, whose NRL classical
        form is ``23 - ln(n_e^0.5 Z T_e^-1.5)`` with ``T_e`` in eV and ``n_e``
        in cm^-3. The value is returned unchanged; the classical branch is a
        separate relation.

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
    _warn_below_quantum_branch(T, "calculate_log_lambda_ei", "scirel.physics.coulomb-ei")
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
    is what the NRL formulary uses for ion-ion collisions, so the
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
