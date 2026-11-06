"""Unit-explicit equilibrium point sampling for declared observations."""

from __future__ import annotations
from collections.abc import Mapping
import numpy as np

from scirel._result import Result

from .observation_residuals import _CHANNELS


def _mapping(value, name):
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _field(mapping, key, name):
    if key not in mapping or mapping[key] is None:
        raise ValueError(f"{name} requires non-null field {key}")
    return mapping[key]


def _unit(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} requires an explicit nonempty unit")
    return value


def _run_composition(equilibrium, R, Z, observations, *, asset_loader):
    """Sample raw psi or single-turn linked flux, and explicitly requested profiles.

    ``flux_loops.quantity`` is ``raw_psi`` or ``magnetic_flux``. Only declared
    ``equilibrium.psi_unit='Wb/rad'`` is multiplied by 2*pi for Wb magnetic
    flux; Wb inputs are unchanged. Raw psi retains its declared unit and gauge.
    Loop turns, reference subtraction and instrument response are not inferred.
    ``thomson`` is a legacy namespace for profile sampling, not scattering.
    """
    equilibrium = _mapping(equilibrium, "equilibrium")
    observations = _mapping(observations, "observations")
    if not observations or set(observations) - {"flux_loops", "thomson"}:
        raise ValueError("observations must request known nonempty flux_loops or thomson channels")
    sampler = asset_loader("scirel.geometry.bilinear_grid_sampling")

    def sample(values, points):
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or not points.shape[0]:
            raise ValueError("diagnostic points must have nonempty shape (N, 2)")
        return sampler(R, Z, values, points)["samples"]

    predicted, units = {}, {}
    if "flux_loops" in observations:
        request = _mapping(observations["flux_loops"], "observations.flux_loops")
        if set(request) - {"points", "quantity", "unit", "values", "sigma"}:
            raise ValueError(
                "unsupported flux-loop request fields; turns/reference subtraction are not implicit"
            )
        points = _field(request, "points", "observations.flux_loops")
        source_unit = _unit(equilibrium.get("psi_unit"), "equilibrium.psi_unit")
        target_unit = _unit(request.get("unit"), "observations.flux_loops.unit")
        quantity = request.get("quantity")
        if quantity == "raw_psi":
            if target_unit != source_unit:
                raise ValueError("raw_psi unit must equal equilibrium.psi_unit")
            factor = 1.0
        elif quantity == "magnetic_flux":
            if target_unit != "Wb" or source_unit not in ("Wb/rad", "Wb"):
                raise ValueError("magnetic_flux requires Wb output and Wb/rad or Wb source psi")
            factor = 2 * np.pi if source_unit == "Wb/rad" else 1.0
        else:
            raise ValueError("flux_loops quantity must explicitly be raw_psi or magnetic_flux")
        values = sample(_field(equilibrium, "psi", "equilibrium"), points) * factor
        if not np.all(np.isfinite(values)):
            raise FloatingPointError("magnetic flux conversion is not finite")
        predicted["flux_loops"], units["flux_loops"] = values, target_unit
    if "thomson" in observations:
        request = _mapping(observations["thomson"], "observations.thomson")
        if set(request) - set(_CHANNELS) - {"points"} or not any(k in request for k in _CHANNELS):
            raise ValueError("thomson must explicitly request known profile channels")
        points = _field(request, "points", "observations.thomson")
        profiles = _mapping(equilibrium.get("profiles"), "equilibrium.profiles")
        profile_units = _mapping(equilibrium.get("profile_units"), "equilibrium.profile_units")
        predicted["thomson"], units["thomson"] = {}, {}
        for key in _CHANNELS:
            if key not in request:
                continue
            channel = _mapping(request[key], f"thomson.{key}")
            unit = _unit(channel.get("unit"), f"thomson.{key}.unit")
            if unit != profile_units.get(key):
                raise ValueError(f"thomson.{key} unit must match equilibrium.profile_units")
            if key in ("p_parallel", "p_perp") and unit != "Pa":
                raise ValueError(f"thomson.{key} pressure unit must be Pa")
            if key == "density" and unit != "m^-3":
                raise ValueError("thomson.density unit must be m^-3")
            if key == "electron_temperature" and unit not in ("K", "eV", "J"):
                raise ValueError("electron_temperature unit must be explicitly K, eV or J")
            predicted["thomson"][key] = sample(
                _field(profiles, key, "equilibrium.profiles"), points
            )
            units["thomson"][key] = unit
    predicted["units"] = units
    return predicted


def synthesize_equilibrium_diagnostics(equilibrium, R, Z, observations):
    """Sample declared equilibrium diagnostics at caller-supplied points.

    Parameters
    ----------
    equilibrium : mapping
        Equilibrium state in ``[physical units declared by the individual
        fields]``.  Flux sampling uses ``psi`` and ``psi_unit``; profile
        sampling uses ``profiles`` and ``profile_units``.  The relevant fields
        must be finite and shaped ``[N_Z, N_R]`` like ``R`` and ``Z``.
    R : array_like, shape (N_Z, N_R)
        Radial coordinate grid in ``[m]``.  It must be finite, constant along
        each grid column, strictly increasing across columns, and contain at
        least two columns.
    Z : array_like, shape (N_Z, N_R)
        Axial coordinate grid in ``[m]``.  It must be finite, have the same
        shape as ``R``, be constant along each grid row, strictly increase down
        rows, and contain at least two rows.
    observations : mapping
        Nonempty mapping containing ``flux_loops`` and/or ``thomson``.  Its
        point coordinates use ``[points in m; each channel unit is explicitly
        declared]``.  A flux request contains ``points``, an explicit
        ``quantity`` (``raw_psi`` or ``magnetic_flux``), and an explicit
        ``unit``; it may also carry inversion metadata ``values`` and ``sigma``
        that this sampler does not consume.  A ``thomson`` request contains
        ``points`` and explicitly requested ``density``,
        ``electron_temperature``, ``p_parallel``, and/or ``p_perp`` channels,
        each with an explicit ``unit``.  The legacy ``thomson`` name here means
        a profile namespace, not a scattering instrument model.

    Returns
    -------
    flux_loops : ndarray of float64, shape (N_flux,), optional
        Field ``flux_loops`` of the returned ``scirel._result.Result`` mapping,
        containing requested raw-psi or single-turn linked-flux samples in
        point order in ``[raw_psi: original unit; magnetic_flux: Wb]``.  The
        key is absent unless requested.
    thomson : dict, optional
        Field ``thomson`` of the returned result mapping, containing requested
        profile arrays in ``[pressure in Pa; density in m^-3; electron
        temperature as declared]``.  Each value has shape ``(N_point,)``; the
        key is absent unless requested.  This nested mapping remains a plain
        ``dict``.
    units : dict
        Field ``units`` of the returned result mapping, containing one-to-one
        unit labels for the actual outputs in ``[identifier]``.  Flux units are
        a string; Thomson units are a channel-to-string mapping.  This nested
        mapping remains a plain ``dict``.

    Raises
    ------
    ValueError
        If required fields or observations are missing or empty, a request is
        unknown or incomplete, points or grids are invalid or outside the
        bilinear domain, a profile is missing, or units conflict with the
        declared equilibrium metadata.
    TypeError
        If a required top-level argument is missing, an old ``inputs`` mapping
        or unknown keyword is supplied, or a numeric value cannot be converted
        to a floating-point array.
    FloatingPointError
        If a magnetic-flux conversion produces a nonfinite value.

    See Also
    --------
    scirel.diagnostics.reduce_observation_residuals
        Compare a prediction mapping with declared observations.
    scirel.geometry.sample_rectilinear_field
        Bilinear scalar-field sampler used by this diagnostic.

    Notes
    -----
    Fields are indexed ``[Z, R]`` and each observation row is ``[R, Z]``.
    Sampling is bilinear inside the closed rectangular grid; no extrapolation
    is performed.  For ``flux_loops.quantity='raw_psi'``, ``psi_unit`` is
    retained unchanged.  For ``'magnetic_flux'``, output is in Wb and
    ``Wb/rad`` input is multiplied by ``2*pi``; a ``Wb`` input is unchanged.
    Profile units must match ``equilibrium.profile_units`` exactly.  Pressures
    must be in Pa and density in ``m^-3``; electron temperature may be K, eV, or
    J without conversion here.

    Only explicitly requested outputs are returned.  Coil turns, reference-loop
    subtraction, instrument response, and temperature or density inversion are
    never inferred.  The top-level fields are returned in a
    ``scirel._result.Result`` mapping, which retains dictionary access and also
    exposes each field as an attribute; nested ``thomson`` and ``units``
    mappings remain plain ``dict`` objects.  The caller's equilibrium mapping
    and arrays are not modified.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.diagnostics import synthesize_equilibrium_diagnostics
    >>> R,Z=np.meshgrid([0.,1.,2.],[-1.,0.,1.])
    >>> r=synthesize_equilibrium_diagnostics(equilibrium={'psi':R**2,'psi_unit':'Wb/rad'},R=R,Z=Z,observations={'flux_loops':{'points':[[1.,0.]],'quantity':'magnetic_flux','unit':'Wb'}})
    >>> assert isinstance(r, Result)
    >>> assert r.flux_loops is r['flux_loops']
    >>> np.testing.assert_allclose(r['flux_loops'],[2*np.pi],rtol=1e-14)
    >>> assert r['units']['flux_loops']=='Wb'
    """
    from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field

    return Result(
        _run_composition(
            equilibrium,
            R,
            Z,
            observations,
            asset_loader=lambda _: sample_rectilinear_field,
        )
    )


__all__ = ["synthesize_equilibrium_diagnostics"]
