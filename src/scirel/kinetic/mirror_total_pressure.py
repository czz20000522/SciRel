"""Combine ion and electron pressures into one finite mirror state with charge residual diagnostics."""

from __future__ import annotations

import numpy as np


def assemble_mirror_total_pressure(kinetic_moments, electron_state):
    """Add a supplied isotropic electron pressure to both broadcast ion pressure components and assemble a terminal state with pass-through densities, residual, optional potential and ion-moment fields.

    Parameters
    ----------
    kinetic_moments : dict; pressure entries convertible to float64 arrays, dict containing pressure values broadcast-compatible with electron pressure; other entries unconstrained
        Ion kinetic-moment mapping, including parallel and perpendicular pressure and ion number density; other ion entries are copied into the result. [p_parallel_pa and p_perpendicular_pa: Pa; density_m3: m^-3; other entries retain their own units] Constraints: Must contain p_parallel_pa, p_perpendicular_pa and density_m3. The two converted pressure arrays must broadcast with electron pressure and contain only finite values. Extra nonphysical metadata fields are not interpreted. Physical density/pressure values must be finite and nonnegative; residual and optional potential finite, with a common broadcast-compatible shape.
    electron_state : dict; electron_pressure_pa convertible to float64 array, dict containing pressure broadcast-compatible with ion pressure; other entries unconstrained
        Electron density, pressure and relative charge residual, optionally including an electrostatic potential. [electron_density_m3: m^-3; electron_pressure_pa: Pa; relative_charge_residual: dimensionless; electrostatic_potential when supplied: V] Constraints: Must contain electron_density_m3, electron_pressure_pa and relative_charge_residual. The converted electron-pressure array must broadcast with both ion pressures and be finite. Valid density, residual and optional potential objects retain their identity after numeric validation. Physical density/pressure values must be finite and nonnegative; residual and optional potential finite, with a common broadcast-compatible shape.

    Returns
    -------
    p_parallel : NumPy float64 array, common broadcast pressure shape
        Sum of ion parallel pressure and the supplied electron pressure. [Pa] Constraints: Finite sum on successful return.
    p_perpendicular : NumPy float64 array, common broadcast pressure shape
        Sum of ion perpendicular pressure and the supplied electron pressure. [Pa] Constraints: Finite sum on successful return.
    ion_density : original input value, unchanged input density shape
        Unconverted ion density from kinetic_moments['density_m3']. [m^-3 by caller contract] Constraints: Finite nonnegative and common-shape broadcastable; the caller's valid object is returned as is.
    ion_p_parallel : NumPy float64 array, common broadcast pressure shape
        Converted and broadcast ion parallel-pressure component. [Pa] Constraints: Finite on successful return.
    ion_p_perpendicular : NumPy float64 array, common broadcast pressure shape
        Converted and broadcast ion perpendicular-pressure component. [Pa] Constraints: Finite on successful return.
    electron_density : original input value, unchanged input density shape
        Unconverted electron density from electron_state['electron_density_m3']. [m^-3 by caller contract] Constraints: Finite nonnegative and common-shape broadcastable; the caller's valid object is returned as is.
    electron_pressure : NumPy float64 array, common broadcast pressure shape
        Converted and broadcast electron pressure added to both ion components. [Pa] Constraints: Finite on successful return.
    electrostatic_potential : original input value or None, unchanged input potential shape or None
        Optional electron-state potential, or None when absent. [V by caller contract when supplied] Constraints: If supplied, finite and broadcast-compatible; the caller's object is returned as is. Absent means None.
    relative_charge_residual : original input value, unchanged input residual shape
        Relative charge residual supplied by electron_state; not recalculated. [dimensionless by caller contract] Constraints: Finite and broadcast-compatible; observational residual is not required to be zero.
    kinetic_moments : dict identity, original dict
        Reference to the original ion-moment dict. [per contained field] Constraints: The result is a new shallow dict, but this entry is the original mapping by object identity; other ion fields are copied unless a named assembly output overwrites them.

    Raises
    ------
    ValueError
        For missing required fields, nonbroadcastable physical states,
        nonfinite fields, negative density/pressure, nonfinite residual or
        invalid optional potential. Numeric conversion may raise TypeError or
        ValueError.
    FloatingPointError
        If adding finite species pressures overflows the finite output range.
    See Also
    --------
    evaluate_mirror_constrained_moments
        Produce the ion moment fields consumed by this assembly.
    evaluate_mirror_invariant_distribution
        Evaluate the underlying invariant distribution.
    Notes
    -----
    The electron pressure is added equally to the ion parallel and perpendicular components. The returned mapping is a shallow copy of ``kinetic_moments``; extra ion fields are copied unless a named assembly output overwrites them. ``kinetic_moments`` itself is retained by object identity in the output, and valid density, residual and optional potential objects retain their original identities. The observational ``relative_charge_residual`` is passed through unchanged and is not required to be zero; this function does not correct a nonzero residual or certify quasineutrality.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import assemble_mirror_total_pressure
    >>> ion = {'p_parallel_pa': [2.0, 3.0], 'p_perpendicular_pa': [4.0, 5.0], 'density_m3': [1.0, 2.0], 'marker': 'ion'}
    >>> electron = {'electron_density_m3': [6.0, 7.0], 'electron_pressure_pa': 1.5, 'relative_charge_residual': [0.1, 0.2]}
    >>> r = assemble_mirror_total_pressure(ion, electron)
    >>> np.testing.assert_allclose(r['p_parallel'], [3.5, 4.5])
    >>> np.testing.assert_allclose(r['p_perpendicular'], [5.5, 6.5])
    >>> assert r['kinetic_moments'] is ion and r['marker'] == 'ion'
    >>> assert r['electrostatic_potential'] is None

    """
    required_ion = {"p_parallel_pa", "p_perpendicular_pa", "density_m3"}
    required_electron = {
        "electron_density_m3",
        "electron_pressure_pa",
        "relative_charge_residual",
    }
    if not isinstance(kinetic_moments, dict) or not required_ion <= kinetic_moments.keys():
        raise ValueError("kinetic_moments is missing required ion moment fields")
    if not isinstance(electron_state, dict) or not required_electron <= electron_state.keys():
        raise ValueError("electron_state is missing required electron fields")
    # Include all physical fields in the common broadcast shape; scalar
    # moments remain valid when an observational potential carries the grid.
    fields = [
        kinetic_moments["p_parallel_pa"],
        kinetic_moments["p_perpendicular_pa"],
        electron_state["electron_pressure_pa"],
        kinetic_moments["density_m3"],
        electron_state["electron_density_m3"],
        electron_state["relative_charge_residual"],
    ]
    if electron_state.get("electrostatic_potential") is not None:
        fields.append(electron_state["electrostatic_potential"])
    physical = np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in fields])
    p_parallel, p_perpendicular, electron_pressure = physical[:3]
    if not all(
        np.all(np.isfinite(value)) for value in (p_parallel, p_perpendicular, electron_pressure)
    ):
        raise ValueError("pressure state must be finite")
    for name, value in (
        ("ion density", kinetic_moments["density_m3"]),
        ("electron density", electron_state["electron_density_m3"]),
    ):
        values = np.asarray(value, dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError(f"{name} must be finite and nonnegative")
        try:
            np.broadcast_to(values, p_parallel.shape)
        except ValueError as exc:
            raise ValueError(f"{name} must match the pressure shape") from exc
    residual = np.asarray(electron_state["relative_charge_residual"], dtype=float)
    if not np.all(np.isfinite(residual)):
        raise ValueError("relative charge residual must be finite")
    try:
        np.broadcast_to(residual, p_parallel.shape)
    except ValueError as exc:
        raise ValueError("relative charge residual must match the pressure shape") from exc
    if any(np.any(x < 0) for x in (p_parallel, p_perpendicular, electron_pressure)):
        raise ValueError("species pressures must be nonnegative")
    if not np.all(np.isfinite(p_parallel + electron_pressure)) or not np.all(
        np.isfinite(p_perpendicular + electron_pressure)
    ):
        raise FloatingPointError("total pressure exceeds the finite output range")
    electrostatic_potential = electron_state.get("electrostatic_potential")
    if electrostatic_potential is not None:
        potential = np.asarray(electrostatic_potential, dtype=float)
        if not np.all(np.isfinite(potential)):
            raise ValueError("electrostatic potential must be finite")
        try:
            np.broadcast_to(potential, p_parallel.shape)
        except ValueError as exc:
            raise ValueError("electrostatic potential must match the pressure shape") from exc
    state = dict(kinetic_moments)
    state.update(
        {
            "p_parallel": p_parallel + electron_pressure,
            "p_perpendicular": p_perpendicular + electron_pressure,
            "ion_density": kinetic_moments["density_m3"],
            "ion_p_parallel": p_parallel,
            "ion_p_perpendicular": p_perpendicular,
            "electron_density": electron_state["electron_density_m3"],
            "electron_pressure": electron_pressure,
            "electrostatic_potential": electrostatic_potential,
            "relative_charge_residual": electron_state["relative_charge_residual"],
            "kinetic_moments": kinetic_moments,
        }
    )
    return state


__all__ = ["assemble_mirror_total_pressure"]
