"""Atomic-hydrogen Saha equilibrium population on the saved scientific branch.

The saved the neutral-transport formulation ``nh_saha`` slice uses constants 3.310e-28 and 13.6057 eV.
Its non-scientific branches use a 1e32 sentinel; this callable rejects those
inputs. Its two density factors assume hydrogen-ion density equals electron
density. The comparison is historical development evidence, not a qualified
D1 freeze or external validation of the Saha model.
"""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_h_saha_equilibrium_population"]


def _real_vector(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def _saha_population(density, temperature, level_squared):
    """Evaluate the vectorized level population with the canonical ordering."""
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        return (
            density
            * (3.310e-28 * density)
            * level_squared
            * np.exp(13.6057 / (level_squared * temperature))
            / temperature**1.5
        )


def evaluate_h_saha_equilibrium_population(
    electron_density_m3,
    electron_temperature_ev,
    principal_level,
):
    """Return atomic-hydrogen Saha level populations on paired samples.

    Parameters
    ----------
    electron_density_m3 : real array_like, shape (N,)
        Electron number density per sample [m^-3], also used as hydrogen-ion
        density under the model assumption ``n_H+ = n_e``. Entries are finite,
        strictly positive, and below ``1e32``; boolean and numeric-string
        coercions are rejected.
    electron_temperature_ev : real array_like, shape (N,)
        Electron temperature paired with each density [eV]. Entries are finite,
        strictly positive, and below ``1e32``; shape must equal
        ``electron_density_m3``.
    principal_level : real scalar representing an integer
        Atomic-hydrogen principal quantum number [dimensionless]. Must be
        integral and at least one; booleans, strings, and non-integral values
        are rejected.

    Returns
    -------
    population_m3 : ndarray of float64, shape (N,)
        Saha equilibrium population density per paired sample [m^-3]. Every
        entry is finite and strictly positive; no sentinel or partial output is
        returned.

    Raises
    ------
    ValueError
        If inputs are non-real or non-finite, arrays are empty, not
        one-dimensional, or mismatched, density or temperature lies outside
        ``(0, 1e32)``, the principal level is not a scalar integral value at
        least one, or the computed population is non-finite or nonpositive.

    See Also
    --------
    scirel.kinetic.make_cylindrical_velocity_quadrature : Build velocity-space cell measures.
    scirel.kinetic.build_shifted_maxwellian_seed : Build a normalized velocity seed.

    Notes
    -----
    For principal level ``n``, the frozen relation is

    .. math:: n_n = n_e (3.310\\times10^{-28} n_e) n^2
        \\exp\\left(\\frac{13.6057}{n^2 T_e}\\right) T_e^{-3/2}.

    The constants and operation order are fixed by the saved scientific
    branch. The formula assumes Saha equilibrium and ``n_H+ = n_e``; neither
    assumption follows from the inputs. The source's ``1e32`` sentinel
    branches are rejected, and no external atomic-physics calibration is
    claimed.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_h_saha_equilibrium_population
    >>> density = np.array([1.0e18, 1.0e19])
    >>> temperature = np.array([1.0, 2.0])
    >>> actual = evaluate_h_saha_equilibrium_population(density, temperature, 2)
    >>> expected = density * (3.310e-28 * density) * 4.0 * np.exp(13.6057 / (4.0 * temperature)) / temperature**1.5
    >>> np.testing.assert_allclose(actual, expected, rtol=1e-15, atol=0.0)
    >>> assert actual.shape == density.shape and np.all(np.isfinite(actual)) and np.all(actual > 0.0)
    """
    density = _real_vector(electron_density_m3, "electron_density_m3")
    temperature = _real_vector(electron_temperature_ev, "electron_temperature_ev")
    if density.ndim != 1 or temperature.ndim != 1 or density.size == 0:
        raise ValueError(
            "electron density and temperature must be non-empty one-dimensional arrays"
        )
    if density.shape != temperature.shape:
        raise ValueError("electron density and temperature must have the same shape")
    if not np.all(np.isfinite(density)) or not np.all(np.isfinite(temperature)):
        raise ValueError("electron density and temperature must be finite")

    try:
        if isinstance(principal_level, (int, np.integer)) and not isinstance(
            principal_level, (bool, np.bool_)
        ):
            level = int(principal_level)
            level_value = None
        else:
            raw_level = np.asarray(principal_level)
            if raw_level.ndim != 0:
                raise ValueError
            if raw_level.dtype.kind in "iu" or (
                raw_level.dtype.kind == "O"
                and isinstance(raw_level.item(), int)
                and not isinstance(raw_level.item(), bool)
            ):
                level = int(raw_level.item())
                level_value = None
            elif raw_level.dtype.kind == "f":
                level_value = float(raw_level)
            else:
                raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("principal_level must be a scalar integer") from exc
    if level_value is not None:
        if not np.isfinite(level_value) or not level_value.is_integer() or level_value < 1:
            raise ValueError("principal_level must be an integer >= 1")
        level = int(level_value)
    if level < 1:
        raise ValueError("principal_level must be an integer >= 1")

    if np.any(density <= 0.0) or np.any(density >= 1.0e32):
        raise ValueError("electron density is outside the scientific domain")
    if np.any(temperature <= 0.0) or np.any(temperature >= 1.0e32):
        raise ValueError("electron temperature is outside the scientific domain")

    try:
        level_squared = float(level * level)
    except OverflowError as exc:
        raise ValueError("principal_level is outside the representable domain") from exc
    with np.errstate(all="ignore"):
        population = _saha_population(density, temperature, level_squared)
    if not np.all(np.isfinite(population)) or np.any(population <= 0.0):
        raise ValueError("Saha population is not finite and positive for the supplied inputs")
    return population
