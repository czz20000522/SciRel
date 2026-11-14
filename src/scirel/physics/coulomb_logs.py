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
high-temperature (quantum cutoff, ``b_min = lambda_dB``) branch. Below it the
classical cutoff ``b_cl = Z e^2/(4 pi eps0 k T)`` sets ``b_min`` and the quantum
branch differs from the low-temperature estimate, so both relations warn below
10 eV (issue #10 item 3).

The two pairs are not the same reference, and the boundary is not the same
statement. The NRL *Plasma Formulary* (2016, printed p. 34) gives the e-e relation
as a single expression,
``23.5 - ln(sqrt(n_e) T_e^(-5/4)) - sqrt(1e-5 + (ln T_e - 2)^2/16)``, with no
``10 Z^2 eV`` branch condition; that condition belongs to the e-i branches
(``T_e > 10 Z^2 eV`` for ``24 - ln(sqrt(n_e)/T_e)``, below it
``23 - ln(sqrt(n_e) Z T_e^(-3/2))``). Here 10 eV is therefore a
repository-conservative advisory line applied to both relations, while the e-i
switching condition is the source's own. ``calculate_log_lambda_ii`` already uses
the classical cutoff form and is not affected. In those table expressions,
temperatures are in eV and densities in cm^-3, unlike the callable inputs.

The e-i entries of that table are conditioned on three quantities, not on
``T_e`` alone: ``T_i m_e/m_i < T_e < 10 Z^2 eV`` selects the low-temperature
form, ``T_i m_e/m_i < 10 Z^2 eV < T_e`` the high-temperature one, and the table
lists a ``T_e < T_i m_e/m_i`` branch as well. ``calculate_log_lambda_ei`` accepts
neither ``T_i`` nor an ion mass and fixes ``Z = 1`` for electrons, so it can only
see the ``10 Z^2 eV`` boundary; whether a call sits inside the transcribed
conditions remains the caller's judgement, and the warning reports only the part
of them this interface can evaluate.

The value returned here is also not the formulary's high-temperature expression
numerically. Converted to these units that expression is
``(24 + ln 1000) + ln(1000*T_e) - 0.5 ln n_e``, with ``T_e`` in keV and
``n_e`` in m^-3. The first ``ln 1000`` converts the density convention; the
``1000*T_e`` converts keV to eV. Its constant before ``ln(T_e[eV])`` is
``24 + ln 1000`` = 30.907755..., whereas the existing implementation keeps
31.3. The difference is about 0.392 in the logarithm. The historical
Wesson/Sauter attribution of 31.3 and the origin of that difference remain
UNKNOWN; neither expression is substituted for the other.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from scirel import ApplicabilityWarning

# Advisory boundary below which both electron relations warn, 10 eV = 0.01 keV.
#
# It is a repository-conservative advisory line, not a branch condition of the e-e relation: the
# NRL Plasma Formulary (2016, printed p. 34) gives the e-e relation as a single expression, while
# its ``T_e > 10 Z^2 eV`` condition belongs to the two e-i branches. Z = 1 for these signatures,
# so the e-i switching condition is 10 eV as well, but the two must not be conflated in wording.
# The e-e reference below is transcribed from that table (the maintainer checked the transcription
# against the original; this implementation only re-evaluates the transcribed formula); the e-i branch
# conditions carry their own (previously recorded) provenance note.
_ADVISORY_BOUNDARY_KEV = 0.01

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
    if not np.any(values < _ADVISORY_BOUNDARY_KEV):
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


def _ee_classical_value(temperature_ev, density_m3):
    """NRL e-e relation value at one sample (``T_e`` eV, ``n_e`` cm^-3).

    ``23.5 - ln(sqrt(n_e) T_e^(-5/4)) - sqrt(1e-5 + (ln T_e - 2)^2/16)``, evaluated in
    logarithmic form so a subnormal temperature or the largest finite density cannot overflow.
    """
    log_temperature = math.log(temperature_ev)
    log_density = math.log(density_m3) - math.log(1e6)
    correction = math.sqrt(1e-5 + (log_temperature - 2.0) ** 2 / 16.0)
    return 23.5 - 0.5 * log_density + 1.25 * log_temperature - correction


def _ee_deviation_at(temperature_kev, density_m3):
    """e-e deviation against the NRL original e-e relation (not its high-T limit)."""
    temperature, density = _lowest_sample(temperature_kev, density_m3)
    temperature_ev = temperature * 1000.0
    if not (temperature_ev > 0.0 and density > 0.0):
        return None
    quantum = 31.0 + math.log(1000.0) + math.log(temperature) - 0.5 * math.log(density)
    try:
        classical_value = _ee_classical_value(temperature_ev, density)
    except (OverflowError, ValueError):
        return None
    if classical_value == 0.0 or not math.isfinite(classical_value):
        return None
    deviation = quantum / classical_value - 1.0
    return deviation if math.isfinite(deviation) else None


def _ei_deviation_at(temperature_kev, density_m3):
    """e-i deviation against ``23 - ln(n_e^0.5 Z T_e^-1.5)``."""
    return _deviation_at(temperature_kev, density_m3, 31.3, 23.0, 1.5)


def _warn_below_quantum_branch_ee(temperature_kev, density_m3):
    """Warn once per call for e-e samples below the quantum-branch boundary.

    The reference is the NRL *Plasma Formulary* (2016, printed p. 34) e-e relation itself,
    ``23.5 - ln(sqrt(n_e) T_e^(-5/4)) - sqrt(1e-5 + (ln T_e - 2)^2/16)`` (``T_e`` in eV,
    ``n_e`` in cm^-3), not its high-temperature limit ``24 - ln(sqrt(n_e)/T_e)``; the two differ
    by ~+49% at 0.1 eV.  The deviation is computed at the offending sample instead of quoting a
    fixed percentage, because it grows with density.  The trigger temperature below is a
    repository-conservative advisory line, not a branch condition of this relation: the
    formulary's ``T_e > 10 Z^2 eV`` condition belongs to the e-i branches.
    """
    lowest_ev = _lowest_ev(temperature_kev)
    if lowest_ev is None:
        return
    deviation = _ee_deviation_at(temperature_kev, density_m3)
    sample_temperature, sample_density = _lowest_sample(temperature_kev, density_m3)
    warnings.warn(
        "calculate_log_lambda_ee: electron temperature is below this repository's conservative"
        f" advisory boundary of 10 eV (lowest input {lowest_ev:.6g} eV). Below it the classical"
        " cutoff b_cl = e^2/(4 pi eps0 k T) sets the minimum impact parameter, and the NRL e-e"
        " relation 23.5 - ln(sqrt(n_e) T_e^(-5/4)) - sqrt(1e-5 + (ln T_e - 2)^2/16)"
        " (T_e in eV, n_e in cm^-3; as transcribed from the formulary (see #197); the transcription was checked by the maintainer against the original table) reads this"
        f" apart: at n_e = {sample_density:.6g} m^-3, T_e = {sample_temperature * 1000.0:.6g} eV,"
        f" the returned value is {_format_deviation(deviation)} above it. That is an algebraic"
        " difference between two estimates, not an error against measured physics, and it grows"
        " with density. The boundary is advisory: the formulary's 10 Z^2 eV condition belongs to"
        " the e-i branches, not to this relation. The returned value is unchanged; the classical"
        " forms are separate relations (scirel.physics.coulomb-ee)",
        ApplicabilityWarning,
        stacklevel=3,
    )


def _warn_below_quantum_branch_ei(temperature_kev, density_m3):
    """Warn once per call for e-i samples below the quantum-branch boundary.

    The e-i branches in the same source are: ``24 - ln(sqrt(n_e)/T_e)`` for ``T_e > 10 Z^2 eV``
    and ``23 - ln(sqrt(n_e) Z T_e^(-3/2))`` below it, with ``T_e`` in eV and ``n_e`` in cm^-3,
    each conditioned on ``T_i m_e/m_i`` as well (module docstring).  The relation here is a
    high-temperature estimate of the same quantity, not that branch numerically: converted to
    these units the formulary constant is ``24 + ln 1000`` = 30.907755..., while this relation
    uses 31.3, about 0.392 apart in the logarithm.  The ~16.2 eV intersection with the
    low-temperature form is an algebraic crossing with a formula extrapolated outside its own
    low-temperature range, not a physical switch or an accuracy criterion.  The deviation is
    computed at the offending sample rather than quoted as a fixed percentage, because it grows
    with density.  The transcription of the NRL table was checked by the maintainer (see #197,
    #212); the Wesson attribution, edition and section remain UNKNOWN, and the two provenance
    facts are recorded separately in the contract.
    """
    lowest_ev = _lowest_ev(temperature_kev)
    if lowest_ev is None:
        return
    deviation = _ei_deviation_at(temperature_kev, density_m3)
    sample_temperature, sample_density = _lowest_sample(temperature_kev, density_m3)
    warnings.warn(
        "calculate_log_lambda_ei: electron temperature is below the 10 Z^2 eV branch condition"
        f" (Z = 1 here, so 10 eV; lowest input {lowest_ev:.6g} eV) under which the source switches"
        " the electron-ion relation to its low-temperature form. The formulary conditions both"
        " branches on T_i m_e/m_i as well; this signature accepts no T_i or ion mass, so only the"
        " 10 Z^2 eV part is evaluated here and the rest stays the caller's judgement. The returned"
        " relation is a high-temperature estimate of the same quantity, not that branch numerically:"
        " the formulary constant is 24 + ln 1000 = 30.907755..., this relation uses 31.3. The"
        " low-temperature form is"
        " 23 - ln(sqrt(n_e) Z T_e^(-1.5)) (T_e in eV, n_e in cm^-3); at"
        f" n_e = {sample_density:.6g} m^-3, T_e = {sample_temperature * 1000.0:.6g} eV the returned"
        f" value is {_format_deviation(deviation)} above it. The ~16.2 eV crossing with the"
        " low-temperature form is an algebraic extrapolation, not a physical switch or an accuracy"
        " criterion; the relative gap grows with density. The returned value is unchanged; the"
        " low-temperature forms are separate relations (scirel.physics.coulomb-ei)",
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
        If any input temperature is below 10 eV, a repository-conservative advisory
        boundary for this quantum-cutoff (``b_min = lambda_dB``) branch. Below it
        the classical cutoff ``b_cl = e^2/(4 pi eps0 k T)`` sets the minimum impact
        parameter, and the NRL Plasma Formulary e-e relation
        ``23.5 - ln(sqrt(n_e) T_e^(-5/4)) - sqrt(1e-5 + (ln T_e - 2)^2/16)``
        (``T_e`` in eV, ``n_e`` in cm^-3, as transcribed from the 2016 printed
        p. 34 table; the transcription was checked by the maintainer, see #197) reads the
        value here about +48.99% higher at 0.1 eV, +13.60% at
        1 eV and +0.81% at 10 eV for ``n_e = 1e19 m^-3``; the gap grows with
        density (+32.60% at 1e17 m^-3 and +98.54% at 1e21 m^-3 at 0.1 eV), so the
        warning computes it per sample instead of quoting a fixed percentage.
        That difference is algebraic between two estimates, not an error against
        measured physics. The 10 eV trigger is advisory: the formulary's
        ``10 Z^2 eV`` condition belongs to the e-i branches, not to this relation.
        Do not reuse the e-i numbers here. The value is returned unchanged; the
        low-temperature estimates are separate relations.

    See Also
    --------
    calculate_log_lambda_ei : Electron-ion estimate (31.3); Sauter (1999) attribution unverified.
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
        If any input temperature is below ``10 Z^2 eV`` (10 eV at Z = 1), the
        source's own switch to its low-temperature e-i branch: the formulary gives
        ``24 - ln(sqrt(n_e)/T_e)`` above that condition and
        ``23 - ln(sqrt(n_e) Z T_e^(-3/2))`` below it (``T_e`` in eV, ``n_e`` in
        cm^-3, as transcribed from the 2016 printed p. 34 table; the transcription was
        checked by the maintainer, see #197 and #212). The formulary conditions both
        branches on ``T_i m_e/m_i`` as well; this signature accepts no ``T_i`` or ion
        mass and fixes ``Z = 1``, so only the ``10 Z^2 eV`` part is evaluated here and
        the remaining conditions stay the caller's judgement. The relation returned is
        a high-temperature estimate of the same quantity, not that branch numerically:
        with density in m^-3 and temperature in eV, the formulary constant is
        ``24 + ln 1000`` = 30.907755..., against 31.3 here; the keV input still
        requires ``ln(1000*T_e)``. The value returned is about +55.5% above
        the low-temperature branch at 0.1 eV and +17.3% at 1 eV for
        ``n_e = 1e19 m^-3``. The ~16.2 eV intersection with that branch is
        algebra on a formula extrapolated outside its own range; it is not a
        physical switching point and not an accuracy criterion. The value is
        returned unchanged; the low-temperature estimates are separate relations.

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
