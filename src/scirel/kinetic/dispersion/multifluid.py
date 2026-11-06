"""Public multifluid the kinetic dispersion formulation operators and the packaged SI example deck."""

from . import _fluid_parallel as _core
from ._example_support import fluid_deck
from ._fluid_parallel import (
    fluid_equilibrium_relative_rates,
    fluid_equilibrium_si,
    fluid_frequency_pencil,
    fluid_solve_state,
)

__all__ = [
    "fluid_equilibrium_si",
    "fluid_equilibrium_relative_rates",
    "fluid_frequency_pencil",
    "fluid_solve_state",
    "scan_fluid_corrected",
    "fluid_deck",
]


def scan_fluid_corrected(inputs):
    r"""Scan a multifluid equilibrium over a declared wavevector grid.

    Parameters
    ----------
    state : mapping[str, numeric array or scalar]
        Explicit equilibrium mapping; no global state is read. Fluid fields are produced
        by fluid_equilibrium_si or fluid_equilibrium_relative_rates. Shape: mapping with
        S species. Constraints: Required fluid fields
        q,m,n,v,csz2,csp2,epsnx,epsny,rho,B0,gamma,c2,epsilon0,mu0,Pz,Pp,Delta,pressure_frame,velocity_collision;
        retain nullable beta fields for rendering. Units: [field-specific SI].
    method : int, optional
        Source scan family selector. Shape: scalar. Constraints: One of 1,2,3,4.
        Default: 2. Units: [dimensionless].
    state_scales : float64 array or None, optional
        Positive diagonal state-coordinate scales used only for numerical conditioning.
        Shape: (4*S+6,) or null. Constraints: Finite positive entries. None selects
        physical density/velocity/electric/magnetic scales; eigenvectors return in
        original coordinates. Default: None. Units: [field-specific SI].
    relativistic : bool, optional
        Use the derivative of relativistic momentum in each species velocity block.
        Shape: scalar. Constraints: If true, all species speeds must be below c and
        velocity_collision must vanish. Default: False. Units: [dimensionless].
    grid_controls : dict, optional
        Explicit mapping of grid keyword controls. Shape: mapping of scalars and
        vectors. Constraints: Keys scan_k,scan_theta,scan_kx,scan_kz,angle,wave_number
        only. Defaults: method1 k=0.1,theta=pi/3; method2 k=arange(101)*1e-5,theta=pi/3;
        method3 k=2,theta=arange(51)*pi/100; method4
        kx=.01+.04*arange(75),kz=.01+.04*arange(50). Explicit controls retain source
        endpoint and axis mapping. Default: {}. Units:
        [scan_k/scan_kx/scan_kz/wave_number m^-1; scan_theta/angle rad].

    Returns
    -------
    result : dict[str, numeric arrays or structured metadata]
        Physical scan mapping with kx,kz,axis_names,axis_values,w1,w2 and point solution
        records. Shape: kx,kz:(na,nb); w1,w2:(na,nb,d); points:length na*nb.
        Constraints: C-order point records include index and full original-unit
        solution. Canonical axis_names are (single,single) for method1, (k,theta) for
        methods2/3 and (kx,kz) for method4; method2 has singleton theta and method3
        singleton k. Units: [kx,kz m^-1; theta rad; omega rad/s].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    fluid_deck
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_equilibrium_si
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_equilibrium_relative_rates
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_frequency_pencil
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_solve_state
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        Methods 1 through 4 use the source scan axes and return canonical axis names and
        shapes. Any point-solver failure aborts the complete scan; no partially filled
        result is presented as a complete grid. Supported scope: Methods 1 through 4;
        default grids and explicitly bounded grids; Explicit state scaling and
        collision-free relativistic point solves. Excluded scope: Implicit root-to-root
        branch tracking across scan points.

    Examples
    --------
    >>> from scirel.kinetic.dispersion.multifluid import fluid_equilibrium_si, scan_fluid_corrected
    >>> r = scan_fluid_corrected(dict(state=fluid_equilibrium_si(), method=2, grid_controls=dict(scan_k=[1e-5, 2e-5])))
    >>> assert r["w1"].shape == (2, 1, 14)
    """

    ports = dict(inputs)
    grid_controls = ports.pop("grid_controls", {})
    return _core.scan_fluid_corrected(**ports, **grid_controls)
