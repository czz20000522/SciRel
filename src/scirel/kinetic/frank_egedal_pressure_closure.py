"""Compose the Frank--Egedal pressure closure from its explicit SciRel composition dependencies."""

from __future__ import annotations


def _run_composition(inputs, *, asset_loader):
    """Resolve the N4 pipeline without composition-local numerical implementation."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    if "params" not in inputs:
        raise ValueError("params is required by composition.yaml")
    if not isinstance(inputs["params"], dict):
        raise ValueError("params must be a mapping")
    params = dict(inputs["params"])
    if {"p0", "background_density"} & params.keys():
        raise ValueError(
            "params must use canonical pressure scale names; p0 and background_density are not accepted"
        )

    def option(name, default):
        return params[name] if name in params else default

    alpha = params["alpha"] if "alpha" in params else 1.0
    radial = asset_loader("scirel.kinetic.frank_egedal_radial_envelope")(
        inputs.get("psi"),
        psi_axis=params.get("psi_axis"),
        psi_edge=params.get("psi_edge"),
        alpha=alpha,
    )
    source = asset_loader("scirel.kinetic.frank_egedal_source_projection")(
        mirror_ratio=option("mirror_ratio", option("turning_b", 2.0)),
        legendre_terms=option("legendre_terms", 15),
        legendre_backend=option("legendre_backend", "truncated"),
        legendre_degrees=option("legendre_degrees", None),
        legendre_mode_count=option("legendre_mode_count", 6),
        legendre_spectrum_grid_points=option("legendre_spectrum_grid_points", 256),
        source_coefficients=option("source_coefficients", None),
        nbi_pitch_angle_deg=option("nbi_pitch_angle_deg", 45.0),
        spectrum_operator=asset_loader("scirel.kinetic.loss_cone_spectrum"),
    )
    hot = asset_loader("scirel.kinetic.frank_egedal_hot_ion_moments")(
        inputs.get("B"),
        params,
        source["degrees"],
        source["source_coefficients"],
        source["legendre_terms"],
        source["fractional_mode"],
    )
    result = asset_loader("scirel.kinetic.frank_egedal_pressure_state")(
        inputs.get("psi"),
        radial,
        hot["hot_parallel_shape"],
        hot["hot_perpendicular_shape"],
        hot["hot_density_shape"],
        hot_pressure_scale=(
            params["hot_pressure_scale"] if "hot_pressure_scale" in params else 1.0
        ),
        gas_dynamic_pressure=(
            params["gas_dynamic_pressure"] if "gas_dynamic_pressure" in params else 0.0
        ),
        gas_dynamic_density=params.get("gas_dynamic_density"),
        hot_density_scale=params.get("hot_density_scale"),
        electron_temperature=params.get("electron_temperature"),
    )
    result["closure_state"] = {
        "normalized_field": hot["normalized_field"],
        "radial_shape": radial,
        "xi_tp_mid": source["xi_tp_mid"],
        "degrees": source["degrees"],
        "source_coefficients": source["source_coefficients"],
        "degree_source": source["degree_source"],
        "legendre_backend": source.get("legendre_backend", "truncated"),
        "legendre_terms": source["legendre_terms"],
        "normalization": "pressure moments referenced to hot_parallel(b=1); density referenced to hot_density(b=1)",
        "quadrature": hot["quadrature"],
        "velocity_domain": hot["velocity_domain"],
        "quadrature_convergence": hot["quadrature_convergence"],
        "reference_raw_moments": hot["reference_raw_moments"],
    }
    return result


def solve_frank_egedal_pressure_closure(inputs=None, **kwargs):
    r"""Solve the Frank-Egedal pressure-closure composition from mapping ports.

    Parameters
    ----------
    inputs : mapping, optional
        Existing input mapping containing the mapping ports documented under Other
        Parameters. The default is None and is merged with named keyword ports by the
        composition boundary. Units: [mapping].
    **kwargs : mapping, optional
        Named mapping ports merged with inputs by the composition boundary. A keyword takes
        precedence over the same key in inputs. Units: [mapping].

    Other Parameters
    ----------------
    psi : real array-like converted to float64
        Caller flux-label grid used for the radial envelope and final pressure shape. Shape:
        nonempty [N_Z,N_R]. Constraints: Finite two-dimensional values. psi_axis and
        psi_edge default to its minimum and maximum; their finite difference must have
        absolute value at least 1e-30. A constant grid therefore needs explicit distinct
        axis and edge values. Units: [same flux coordinate as params.psi_axis/psi_edge;
        historical label Wb, or Wb/rad when coupled to current SciRel free-boundary Picard].
    B : real array-like converted to float64
        Local magnetic-field magnitude at the same samples as psi. Shape: [N_Z,N_R], exactly
        psi-shaped. Constraints: Finite and strictly positive; B0 is finite and strictly
        positive. Shape agreement with psi is checked by the terminal assembly. Units: [T].
    params : Python dict
        Caller-owned closure configuration passed to the four active operators; see
        constraints for nested names and defaults. Shape: mapping. Constraints: A dict is
        required. Radial keys: psi_axis=min(psi), psi_edge=max(psi), alpha=1 with alpha>=0;
        reversed edge orientation is permitted. Field/source keys: B0=median(B),
        mirror_ratio=turning_b if mirror_ratio absent, otherwise mirror_ratio (default 2),
        requiring >1; vc_over_v0=0.25 nonnegative; velocity_lower=perp_velocity_lower when
        the legacy alias is supplied, otherwise 0, within [0,1); both names must agree and
        define one common population; beta_m=zeff/2 if absent, otherwise beta_m (default
        zeff=1), finite. Explicit nonempty finite legendre_degrees bypasses spectrum
        evaluation; otherwise legendre_mode_count=6 and legendre_spectrum_grid_points=256
        control it. source_coefficients must be finite and match degrees if supplied;
        otherwise nbi_pitch_angle_deg=45 controls projection. legendre_terms=15 is a legacy
        count >=2; both backend names 'truncated' (default) and 'hypergeometric' use the
        corrected regular initial-value evaluator. velocity_nodes=pitch_nodes=24 by default,
        each int-converted value >=2. Pressure keys: hot_pressure_scale defaults to 1 Pa;
        gas_dynamic_pressure defaults to 0 Pa; gas_dynamic_density, hot_density_scale and
        electron_temperature are optional canonical keys. The pressure-state adapter passes
        these as keyword-only arguments and has no p0 or background_density fallback.
        Present pressure, density and electron-energy scales must be finite and nonnegative;
        the latter is J, not K. Some nested numeric conversions and Legendre evaluations can
        raise their native exceptions. Raw moments refine with quadrature_rtol=1e-7 and
        max_quadrature_nodes=max(768,2*max(initial counts)); zero-vc/zero-cutoff divergent
        density, zero normalizers or unresolved refinement fail explicitly. Units: [mixed;
        psi_axis/psi_edge same as psi, field T, pressure Pa, density m^-3, electron energy
        J, angle deg and dimensionless controls].

    Returns
    -------
    p_parallel : NumPy float64 array
        Gas-dynamic plus optional electron plus hot-ion parallel pressure. Shape: [N_Z,N_R].
        Constraints: Finite and nonnegative on successful return; hot term uses
        hot_parallel_shape normalized at b=1. Units: [Pa].
    p_perp : NumPy float64 array
        Gas-dynamic plus optional electron plus hot-ion perpendicular pressure. Shape:
        [N_Z,N_R]. Constraints: Finite and nonnegative on successful return; its hot term is
        normalized to the b=1 parallel moment, so it need not equal p_parallel at b=1.
        Units: [Pa].
    density : NumPy float64 array or None
        Gas-dynamic radial density plus radial hot-ion density when either density scale is
        supplied. Shape: [N_Z,N_R] or None. Constraints: None when both gas_dynamic_density
        and hot_density_scale are absent. The electron pressure is zero when
        electron_temperature is absent or no density scale is supplied. Units: [m^-3 or not
        applicable].
    electron_temperature : NumPy float64 array or None
        Constant electron thermal-energy field used for the optional electron pressure.
        Shape: [N_Z,N_R] or None. Constraints: None when unconfigured; may be an array even
        when density is None, in which case the electron pressure remains zero. Units: [J or
        not applicable].
    closure_state : Python dict containing NumPy arrays, strings, numbers and a quadrature dict
        Inspectable intermediate source and hot-moment state added by the graph, not a
        convergence certificate. Shape: mapping with [N_Z,N_R] normalized_field and
        radial_shape, [mode] degrees and source_coefficients, scalar xi_tp_mid,
        degree_source, legendre_backend, legendre_terms, normalization and quadrature,
        velocity_domain and quadrature_convergence, reference_raw_moments. Constraints:
        Initial quadrature counts, effective raw-moment convergence and common velocity
        domain are inspectable. They do not establish a physical force balance or kinetic
        equilibrium. Reference raw moments expose the normalization integrals before
        division. Units: [mixed; normalized fields and mode arrays are dimensionless].

    Raises
    ------
    ValueError
        If inputs is not a mapping, required params are missing, or the parameter mapping
        violates its declared normalization, shape, grid, source or control contract.
    RuntimeError
        If source normalization, spectrum evaluation, hot-moment quadrature or pressure
        assembly cannot produce a finite converged closure.

    See Also
    --------
    scirel.kinetic.evaluate_frank_egedal_radial_envelope
        Evaluate the radial pressure envelope.
    scirel.kinetic.project_frank_egedal_source_modes
        Project caller or spectral loss-cone source modes.
    scirel.kinetic.evaluate_frank_egedal_hot_ion_moments
        Evaluate the hot-ion moment closure state.
    scirel.kinetic.assemble_frank_egedal_pressure
        Assemble the returned pressure fields.

    Notes
    -----
        The public wrapper accepts the existing `inputs` mapping and named `**kwargs`
        mapping ports through the composition boundary. `psi` and `B` are caller-owned
        arrays; `params` is passed through to the bound radial-envelope, source-projection,
        hot-moment and pressure-state operators. The returned `closure_state` is an
        inspectable record of source and hot-moment intermediates, not a convergence or
        physical-force-balance certificate. Nested mappings remain ordinary Python
        dictionaries.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import solve_frank_egedal_pressure_closure
    >>> psi = np.array([[0.0, 0.5], [0.25, 1.0]])
    >>> B = np.array([[1.0, 1.1], [1.2, 1.3]])
    >>> r = solve_frank_egedal_pressure_closure({'psi': psi, 'B': B, 'params': {'psi_axis': 0.0, 'psi_edge': 1.0, 'B0': 1.0, 'hot_pressure_scale': 8.0, 'mirror_ratio': 2.0, 'legendre_degrees': [0.5], 'source_coefficients': [1.0], 'velocity_nodes': 6, 'pitch_nodes': 6}})
    >>> assert set(r) == {'p_parallel', 'p_perp', 'density', 'electron_temperature', 'closure_state'}
    >>> assert r['p_parallel'].shape == r['p_perp'].shape == (2, 2)
    >>> assert np.all(np.isfinite(r['p_parallel'])) and np.all(np.isfinite(r['p_perp']))
    >>> assert r['density'] is None and r['electron_temperature'] is None
    >>> assert r['closure_state']['degree_source'] == 'caller_supplied'
    >>> assert r['closure_state']['normalization'] == 'pressure moments referenced to hot_parallel(b=1); density referenced to hot_density(b=1)'
    """
    from scirel._composition import compose
    from scirel.kinetic.frank_egedal_hot_ion_moments import (
        evaluate_frank_egedal_hot_ion_moments as _dependency_0,
    )
    from scirel.kinetic.frank_egedal_pressure_state import (
        assemble_frank_egedal_pressure as _dependency_1,
    )
    from scirel.kinetic.frank_egedal_radial_envelope import (
        evaluate_frank_egedal_radial_envelope as _dependency_2,
    )
    from scirel.kinetic.frank_egedal_source_projection import (
        project_frank_egedal_source_modes as _dependency_3,
    )
    from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum as _dependency_4

    return compose(
        _run_composition,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.kinetic.frank_egedal_hot_ion_moments": _dependency_0,
                "scirel.kinetic.frank_egedal_pressure_state": _dependency_1,
                "scirel.kinetic.frank_egedal_radial_envelope": _dependency_2,
                "scirel.kinetic.frank_egedal_source_projection": _dependency_3,
                "scirel.kinetic.loss_cone_spectrum": _dependency_4,
            }
        },
    )


__all__ = ["solve_frank_egedal_pressure_closure"]
