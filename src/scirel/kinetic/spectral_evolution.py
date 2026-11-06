"""Effective multi-fluid temporal dispersion, derived in the multi-fluid dispersion formulation D2.

Lineage: Xie, CPC 185 (2014) 670–675, DOI 10.1016/j.cpc.2013.10.012;
retained D0 ee25f53b91f54ff1b897af43c5b1b0118f7caa46, D1 573a40e4509e971a1960e2b6a9a40a41b833d655.
This Python implementation is newly authored, not a clean-room licensing claim.
Source/paper redistribution rights remain NOT_ESTABLISHED; local D2 candidate only.

The background is externally maintained by prescribed per-mass acceleration
and charge/current/particle sources with zero perturbation response. A fixed
force per volume would define a different denominator linearization. Gradients
form a local/eikonal effective symbol, not a global Maxwell-Gauss boundary
solution in an inhomogeneous plasma. The algebraic thermal closure is
P0_parallel/perpendicular = m*n*cs_parallel/perpendicular**2/gamma,
delta P_parallel/perpendicular = m*cs_parallel/perpendicular**2*delta n.
It is NOT full entropy evolution or CGL. B0 lies along z, k=(kx,0,kz),
grad log n=(epsx,epsy,0). At B0=0 the pressure director remains fixed z;
this is not the drift-directed rotation in the paper's Appendix A.
At nonzero B0 the director follows delta B transverse to z. The source's
empirical mirror factor two multiplies the complete longitudinal magnetic
pressure divergence, including its background-gradient terms. This is an
effective closure, not a first-principles kinetic mirror qualification.

D2 corrections: positive drag damps; reciprocal interspecies friction conserves
momentum; SI category thresholds use electron mass; initialization replaces
stale globals; beta at B0=0 is undefined (None); pressure-force denominator
and magnetic-pressure coefficient gradients are linearized; invalid inputs
fail before calculation; values/vectors share a numerical path; all return
arities and terminal scan fields are defined; plotting indices are bounded.
Original behavior and D1 assertions are preserved outside the runtime package.
"""

from __future__ import annotations

import io
import operator
from pathlib import Path

import numpy as np


__all__ = [
    "initialize_plasma_state",
    "assemble_spectral_matrix",
    "solve_temporal_spectrum",
    "evaluate_spectral_dispersion",
]


def _real(value, name):
    def boolean(item):
        if isinstance(item, (bool, np.bool_)):
            return True
        if isinstance(item, (list, tuple)):
            return any(boolean(v) for v in item)
        return isinstance(item, np.ndarray) and item.dtype.kind == "b"

    if boolean(value):
        raise ValueError(f"{name} cannot contain boolean pseudo-numbers")
    arr = np.asarray(value)
    if arr.dtype.kind not in "iuf" or not np.isfinite(arr).all():
        raise ValueError(f"{name} must be finite real numeric data")
    return np.array(arr, dtype=float, copy=True)


def _scalar(value, name, positive=False):
    arr = _real(value, name)
    if arr.ndim != 0 or (positive and arr <= 0):
        raise ValueError(f"{name} must be a {'positive ' if positive else ''}scalar")
    return float(arr)


def _integer(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be an integer")
    try:
        return operator.index(value)
    except TypeError as error:
        raise ValueError(f"{name} must be an integer") from error


def _vector(value, size, name, positive=False, nonnegative=False):
    arr = _real(value, name)
    if arr.ndim == 0:
        arr = np.full(size, float(arr))
    if arr.shape != (size,) or (positive and np.any(arr <= 0)) or (nonnegative and np.any(arr < 0)):
        raise ValueError(f"invalid {name}: expected ({size},) with valid signs")
    return arr


def _assemble_legacy_collision_rates(rho, light, legacy):
    """Build the reciprocal pair-rate matrix from one canonical pair table."""
    count = rho.size
    rates = np.zeros((count, count), dtype=float)
    for i in range(count - 1):
        for j in range(i + 1, count):
            same_class = light[i] == light[j]
            if same_class:
                pair_rate = legacy["nuee"] if light[i] else legacy["nuii"]
                receiver, other = (i, j) if rho[i] <= rho[j] else (j, i)
            else:
                receiver, other, pair_rate = (
                    (i, j, legacy["nuei"]) if light[i] else (j, i, legacy["nuei"])
                )
            rates[receiver, other] = pair_rate
            rates[other, receiver] = pair_rate * (rho[receiver] / rho[other])
            if pair_rate > 0 and rates[other, receiver] == 0:
                raise ValueError("reciprocal collision rate exceeds finite numeric domain")
    return rates


def _species_data(species, unit):
    if species is None:
        # Scientific example inputs, not captured answers or source runtime files.
        if unit == "normalized":
            species = [[-1, 1, 4, 0, 0, 0, 0, 0, 0, 0], [1, 4, 4, 0, 0, 0, 0, 0, 0, 0]]
        else:
            species = [
                [-1.602e-19, 9.109e-31, 8.7e6, 0, 0, 0, 4.631e6, 4.631e6, 0, 0],
                [1.602e-19, 1.673e-27, 8.7e6, 0, 0, 0, 9.360e4, 9.360e4, 0, 0],
            ]
    if isinstance(species, str):
        try:
            species = np.loadtxt(io.StringIO(species), skiprows=1, ndmin=2)
        except (ValueError, TypeError) as error:
            raise ValueError("invalid ten-column species text (one header line)") from error
    data = _real(species, "species")
    if data.ndim != 2 or data.shape[1] != 10 or data.shape[0] < 1:
        raise ValueError("species must be a nonempty (s,10) table")
    if np.any(data[:, 1:3] <= 0) or np.any(data[:, 6:8] < 0):
        raise ValueError("mass/density must be positive and sound speeds nonnegative")
    return data


def initialize_plasma_state(species=None, *, unit="normalized", prior=None, cfg=None):
    r"""Initialize a caller-owned local multifluid plasma state.

    Parameters
    ----------
    species : real array-like or string, optional
        Rows q,m,n,vx,vy,vz,cs_parallel,cs_perpendicular,eps_x,eps_y; one header line
        for text. Shape: [s,10] or text. Constraints: s>=1, m/n>0, cs>=0; None uses
        documented example rows; rows are independent fluids, including equal rows.
        Default normalized rows: [-1,1,4,0,0,0,0,0,0,0], [1,4,4,0,0,0,0,0,0,0]. Default
        SI rows: [-1.602e-19,9.109e-31,8.7e6,0,0,0,4.631e6,4.631e6,0,0],
        [1.602e-19,1.673e-27,8.7e6,0,0,0,9.360e4,9.360e4,0,0]. Default: None. Units: [SI
        C,kg,m^-3,m/s,m^-1 by quantity; normalized units fixed by explicit c2,epsilon0
        and B0].
    unit : string, optional
        Unit convention and default constants. Shape: scalar. Constraints: normalized or
        si, without input conversion. Default: 'normalized'. Units: [dimensionless].
    prior : dict or None, optional
        Prior state accepted for call compatibility, never used as primary scientific
        input. Shape: mapping or null. Constraints: Every field is freshly derived;
        prior is not mutated. Default: None. Units: [state convention].
    cfg : dict or None, optional
        Constants B0,c2,epsilon0,gammaTs; collision controls and classification. Shape:
        mapping or null. Constraints: Only documented fields; c2/epsilon0/gammaTs>0.
        Explicit rates receiver i toward j, zero diagonal, nonnegative and rho
        reciprocal. drag_rates>=0. Legacy nue/nui light/heavy bath, nuei light-receiver
        cross-class, same-class nuee/nuii lower-rho receiver. Default mass classes
        normalized<=1 or SI<=9.1093837139e-31 kg; collision_classes explicit light/heavy
        (electron/ion aliases) overrides. These are numerical categories, not inferred
        species identities. Defaults normalized: B0=1,c2=1,epsilon0=1,gammaTs=1; SI:
        B0=8e-9 T,c2=(2.9979e8)^2,epsilon0=8.854e-12,gammaTs=5/3. All five legacy rates
        zero; absent explicit pair/drag rates derive from those zero controls. Default
        classes use the declared mass threshold. Default: None. Units: [B0 in T/SI or
        normalized; c2 speed squared; epsilon0 SI or normalized; rates s^-1 or
        normalized frequency].

    Returns
    -------
    s : int
        Number of fluid rows. Shape: scalar. Constraints: No deduplication or stale
        tail. Units: [dimensionless].
    unit : string
        Declared unit convention. Shape: scalar. Constraints: normalized or si. Units:
        [dimensionless].
    species : float64
        Owned copy of all primary species inputs. Shape: [s,10]. Constraints: Input
        order preserved. Units: [SI C,kg,m^-3,m/s,m^-1 by quantity; normalized units
        fixed by explicit c2,epsilon0 and B0].
    qs : float64
        Charges. Shape: [s]. Constraints: Finite. Units: [C or normalized charge].
    ms : float64
        Masses. Shape: [s]. Constraints: Positive. Units: [kg or normalized mass].
    ns0 : float64
        Number densities. Shape: [s]. Constraints: Positive. Units: [m^-3 or normalized
        density].
    vs0x : float64
        x drift. Shape: [s]. Constraints: Finite. Units: [m/s or normalized speed].
    vs0y : float64
        y drift. Shape: [s]. Constraints: Finite. Units: [m/s or normalized speed].
    vs0z : float64
        z drift. Shape: [s]. Constraints: Finite. Units: [m/s or normalized speed].
    csz2 : float64
        Parallel sound speed squared. Shape: [s]. Constraints: Nonnegative. Units:
        [m^2/s^2 or normalized speed squared].
    csp2 : float64
        Perpendicular sound speed squared. Shape: [s]. Constraints: Nonnegative. Units:
        [m^2/s^2 or normalized speed squared].
    epsnx : float64
        x logarithmic density gradient. Shape: [s]. Constraints: Finite. Units: [m^-1 or
        normalized inverse length].
    epsny : float64
        y logarithmic density gradient. Shape: [s]. Constraints: Finite. Units: [m^-1 or
        normalized inverse length].
    rhos0 : float64
        Mass density m*n. Shape: [s]. Constraints: Positive. Units: [kg/m^3 or
        normalized mass density].
    gammaTs : float64
        Algebraic pressure coefficient. Shape: [s]. Constraints: Positive. Units:
        [dimensionless].
    Psz : float64
        Parallel background pressure rho*csz2/gamma. Shape: [s]. Constraints:
        Nonnegative. Units: [Pa or normalized pressure].
    Psp : float64
        Perpendicular background pressure rho*csp2/gamma. Shape: [s]. Constraints:
        Nonnegative. Units: [Pa or normalized pressure].
    Deltas : float64
        Magnetic director pressure coefficient (Psz-Psp)/B0. Shape: [s]. Constraints:
        Exactly zero at B0=0, fixed z director. Units: [Pa/T or normalized
        pressure/field].
    vA : float64
        Signed Alfvén scale B0/sqrt(mu0*rho). Shape: [s]. Constraints: Exactly zero at
        B0=0. Units: [m/s or normalized speed].
    wcs : float64
        Signed gyrofrequency q*B0/m. Shape: [s]. Constraints: Zero is permitted. Units:
        [s^-1 or normalized frequency].
    wps : float64
        Plasma frequency sqrt(n*q^2/(epsilon0*m)). Shape: [s]. Constraints: Nonnegative.
        Units: [s^-1 or normalized frequency].
    betasz : float64 array or None
        Parallel beta 2*mu0*Psz/B0^2. Shape: [s] or null. Constraints: Undefined and
        returned None at B0=0, not a stale or invented zero. Units: [dimensionless].
    betasp : float64 array or None
        Perpendicular beta 2*mu0*Psp/B0^2. Shape: [s] or null. Constraints: Undefined at
        B0=0. Units: [dimensionless].
    Q0 : float64
        Total charge density sum(q*n). Shape: scalar. Constraints: May be nonzero under
        externally maintained background. Units: [C/m^3 or normalized charge density].
    J0x : float64
        x background current. Shape: scalar. Constraints: Finite; no unforced
        equilibrium claim. Units: [A/m^2 or normalized current density].
    J0y : float64
        y background current. Shape: scalar. Constraints: Finite. Units: [A/m^2 or
        normalized current density].
    J0z : float64
        z background current. Shape: scalar. Constraints: Finite. Units: [A/m^2 or
        normalized current density].
    B0 : float64
        z background field. Shape: scalar. Constraints: Finite including zero. Units: [T
        or normalized field].
    c2 : float64
        Speed of light squared. Shape: scalar. Constraints: Positive. Units: [m^2/s^2 or
        normalized speed squared].
    epsilon0 : float64
        Permittivity. Shape: scalar. Constraints: Positive. Units: [F/m or normalized
        permittivity].
    mu0 : float64
        Permeability 1/(c2*epsilon0). Shape: scalar. Constraints: Positive finite.
        Units: [H/m or normalized permeability].
    mirror_factor : float64
        Phenomenological longitudinal magnetic-pressure factor. Shape: scalar.
        Constraints: Exactly 2. Units: [dimensionless].
    nu : float64
        Velocity collision generator: positive pair couplings and diagonal minus bath
        and outgoing-rate sum. Shape: [s,s]. Constraints: Row sum=-drag_rates;
        rho-weighted pairwise momentum conservation. Units: [s^-1 or normalized
        frequency].
    collision_rates : float64
        Receiver-rate matrix. Shape: [s,s]. Constraints: Nonnegative, zero diagonal,
        rho_i rate_ij=rho_j rate_ji; finite nonunderflowing momentum flux. Units: [s^-1
        or normalized frequency].
    drag_rates : float64
        External stationary-bath rates. Shape: [s]. Constraints: Nonnegative. Units:
        [s^-1 or normalized frequency].
    collision_classes : string array
        Declared numerical collision classes. Shape: [s]. Constraints: light/heavy,
        preserved through assembly. Units: [dimensionless].
    background : string
        Prescribed background support convention. Shape: scalar. Constraints:
        externally-maintained-zero-perturbation-response. Units: [dimensionless].
    pressure_closure : string
        Thermal relation label. Shape: scalar. Constraints:
        algebraic-fixed-temperature-coefficients. Units: [dimensionless].
    zero_field_director : string
        Unmagnetized pressure orientation. Shape: scalar. Constraints: fixed-z. Units:
        [dimensionless].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    assemble_spectral_matrix
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_temporal_spectrum
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_spectral_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        All returned arrays are newly derived from the supplied rows or documented
        defaults. The prior mapping is retained only as a call-compatibility input and
        contributes no scientific state. Supported scope: Fresh normalized/SI
        primary-state derivation, diagnostics, explicit and legacy reciprocal collision
        rates, repeated calls and zero magnetic field. No eigenspectrum or scan is
        calculated. Excluded scope: Effective local algebraic thermal model; not full
        entropy evolution, CGL, kinetic physics, or the unmagnetized drift-directed
        Appendix A model; Background sources and prescribed acceleration per mass have
        zero perturbation response. Gradients define a local/eikonal symbol, not an
        inhomogeneous global Maxwell-Gauss boundary solution; The magnetic longitudinal
        pressure-divergence factor two is a phenomenological mirror correction; no
        universal kinetic mirror threshold or experimental accuracy claim; Relativistic
        inertia uses d(gamma*v)/dv with noncovariant pressure and friction; no fully
        covariant thermodynamics claim is made.

    Examples
    --------
    >>> from scirel.kinetic import initialize_plasma_state
    >>> s = initialize_plasma_state()
    >>> assert s['s'] == 2 and s['Q0'] == 0
    """
    if unit not in ("normalized", "si"):
        raise ValueError("unit must be normalized or si")
    if prior is not None and not isinstance(prior, dict):
        raise ValueError("prior must be a mapping or None")
    cfg = dict(cfg or {})
    allowed = {
        "B0",
        "c2",
        "epsilon0",
        "gammaTs",
        "nue",
        "nui",
        "nuee",
        "nuii",
        "nuei",
        "collision_rates",
        "drag_rates",
        "collision_classes",
    }
    if set(cfg) - allowed:
        raise ValueError(f"unknown configuration fields: {sorted(set(cfg) - allowed)}")
    data = _species_data(species, unit)
    s = len(data)
    B0 = _scalar(cfg.get("B0", 1.0 if unit == "normalized" else 8e-9), "B0")
    c2 = _scalar(cfg.get("c2", 1.0 if unit == "normalized" else 2.9979e8**2), "c2", True)
    epsilon0 = _scalar(
        cfg.get("epsilon0", 1.0 if unit == "normalized" else 8.854e-12), "epsilon0", True
    )
    gamma = _vector(
        cfg.get("gammaTs", 1.0 if unit == "normalized" else 5 / 3), s, "gammaTs", positive=True
    )
    qs, ms, ns = data[:, 0], data[:, 1], data[:, 2]
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        rho = ms * ns
        csz2, csp2 = data[:, 6] ** 2, data[:, 7] ** 2
        Psz, Psp = rho * csz2 / gamma, rho * csp2 / gamma
        mu0 = 1 / (c2 * epsilon0)
        current = np.sum((qs * ns)[:, None] * data[:, 3:6], axis=0)
        charge = np.sum(qs * ns)
        beta_z = 2 * mu0 * Psz / B0**2 if B0 != 0 else None
        beta_p = 2 * mu0 * Psp / B0**2 if B0 != 0 else None
        delta = (Psz - Psp) / B0 if B0 != 0 else np.zeros(s)
        va = B0 / np.sqrt(mu0 * rho)
        wcs = qs * B0 / ms
        wps = np.sqrt(ns / epsilon0 / ms) * np.abs(qs)
    if (
        np.any(rho <= 0)
        or not np.isfinite(
            np.r_[rho, csz2, csp2, Psz, Psp, delta, va, wcs, wps, current, charge, mu0]
        ).all()
    ):
        raise ValueError("derived plasma state exceeds finite numeric domain")
    if beta_z is not None and not np.isfinite(np.r_[beta_z, beta_p]).all():
        raise ValueError("beta exceeds finite numeric domain")
    legacy = {
        name: _scalar(cfg.get(name, 0.0), name) for name in ("nue", "nui", "nuee", "nuii", "nuei")
    }
    if any(value < 0 for value in legacy.values()):
        raise ValueError("collision rates must be nonnegative")
    if ("collision_rates" in cfg or "drag_rates" in cfg) and any(legacy.values()):
        raise ValueError("choose explicit collision rates or legacy controls")
    # Numerical mass categories, not inferred physical species identity.
    light = ms <= (1.0 if unit == "normalized" else 9.1093837139e-31)
    if "collision_classes" in cfg:
        classes = np.asarray(cfg["collision_classes"])
        if (
            classes.shape != (s,)
            or not np.isin(classes, ["light", "heavy", "electron", "ion"]).all()
        ):
            raise ValueError("collision_classes needs s light/heavy (electron/ion aliases) labels")
        light = np.isin(classes, ["light", "electron"])
    drag = _vector(
        cfg.get("drag_rates", np.where(light, legacy["nue"], legacy["nui"])),
        s,
        "drag_rates",
        nonnegative=True,
    )
    rates = np.zeros((s, s))
    if "collision_rates" in cfg:
        rates = _real(cfg["collision_rates"], "collision_rates")
        if rates.shape != (s, s) or np.any(rates < 0) or np.any(np.diag(rates) != 0):
            raise ValueError("collision_rates needs nonnegative (s,s) with zero diagonal")
    else:
        rates = _assemble_legacy_collision_rates(rho, light, legacy)
    # Both interfaces must meet the same physical and representability contract.
    # Positive rates with zero weighted flux cannot prove momentum reciprocity.
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        flux = rho[:, None] * rates
    if not np.isfinite(flux).all() or np.any((rates > 0) & (flux == 0)):
        raise ValueError("collision momentum flux exceeds finite numeric domain")
    scale = np.maximum(np.abs(flux), np.abs(flux.T))
    if np.any(np.abs(flux - flux.T) > 1e-12 * scale):
        raise ValueError("collision_rates must conserve pairwise momentum")
    collision = rates.copy()
    np.fill_diagonal(collision, -drag - rates.sum(axis=1))
    if not np.isfinite(collision).all():
        raise ValueError("collision matrix exceeds finite numeric domain")
    return {
        "s": s,
        "unit": unit,
        "species": data,
        "qs": qs.copy(),
        "ms": ms.copy(),
        "ns0": ns.copy(),
        "vs0x": data[:, 3].copy(),
        "vs0y": data[:, 4].copy(),
        "vs0z": data[:, 5].copy(),
        "csz2": csz2,
        "csp2": csp2,
        "epsnx": data[:, 8].copy(),
        "epsny": data[:, 9].copy(),
        "rhos0": rho,
        "Q0": float(charge),
        "J0x": float(current[0]),
        "J0y": float(current[1]),
        "J0z": float(current[2]),
        "nu": collision,
        "collision_rates": rates,
        "drag_rates": drag,
        "collision_classes": np.where(light, "light", "heavy"),
        "B0": B0,
        "c2": c2,
        "epsilon0": epsilon0,
        "mu0": mu0,
        "gammaTs": gamma,
        "Psz": Psz,
        "Psp": Psp,
        "betasz": beta_z,
        "betasp": beta_p,
        "Deltas": delta,
        "vA": va,
        "wcs": wcs,
        "wps": wps,
        "background": "externally-maintained-zero-perturbation-response",
        "pressure_closure": "algebraic-fixed-temperature-coefficients",
        "zero_field_director": "fixed-z",
        "mirror_factor": 2.0,
    }


def _cross(v):
    x, y, z = v
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])


def _state(state):
    if not isinstance(state, dict) or "species" not in state:
        raise ValueError("state must be produced by initialize_plasma_state")
    # Re-derive all science from explicit primary inputs; stale derived fields
    # cannot silently enter the matrix. A changed primary field is a new state.
    return initialize_plasma_state(
        state["species"],
        unit=state["unit"],
        cfg={
            "B0": state["B0"],
            "c2": state["c2"],
            "epsilon0": state["epsilon0"],
            "gammaTs": state["gammaTs"],
            "collision_rates": state["collision_rates"],
            "drag_rates": state["drag_rates"],
            "collision_classes": state["collision_classes"],
        },
    )


def assemble_spectral_matrix(state, kx, kz, *, rel=0):
    r"""Assemble the local spectral time-generator matrix.

    Parameters
    ----------
    state : dict
        Fresh plasma state with explicit primary data and configuration. Shape: mapping.
        Constraints: Produced by initialize_plasma_state; primary inputs are revalidated
        and all derived fields recomputed. Units: [mixed physical quantities as declared
        by state].
    kx : finite complex scalar
        x wave number. Shape: scalar. Constraints: Complex values describe the local
        spatial analytic symbol. Units: [m^-1 SI or normalized inverse length].
    kz : finite complex scalar
        z wave number. Shape: scalar. Constraints: Same convention as kx. Units: [m^-1
        SI or normalized inverse length].
    rel : int, optional
        Relativistic inertia selector. Shape: scalar. Constraints: 0 or 1; rel=1
        requires |v0|<c. Default: 0. Units: [dimensionless].

    Returns
    -------
    M : complex128
        Temporal generator with species [dn,dvx,dvy,dvz] then [Ex,Ey,Ez,Bx,By,Bz].
        Shape: [4s+6,4s+6]. Constraints: Finite; lambda*A*x=M*x and omega=i*lambda.
        Units: [row output units per second divided by column state units; normalized
        analog].
    A : complex128
        Inertia matrix. Shape: [4s+6,4s+6]. Constraints: Identity except d(gamma*v)/dv
        in rel=1 velocity blocks. Units: [dimensionless within equally scaled velocity
        blocks].
    state : dict
        Revalidated fresh state used by the matrix. Shape: mapping. Constraints: No
        stale derived fields; preserves explicit collision classes. Units: [per-state
        quantity conventions].
    scales : float64
        Positive physical state-column scales for similarity transformation. Shape:
        [4s+6]. Constraints: Density=n_j, velocity=c, B=sqrt(sum(rho)/epsilon0), E=c*B;
        transforms rows and columns consistently. Units: [density,velocity,electric
        field,magnetic field by component].
    kx : complex
        Accepted wave number x. Shape: scalar. Constraints: Same as requested. Units:
        [m^-1 SI or normalized inverse length].
    kz : complex
        Accepted wave number z. Shape: scalar. Constraints: Same as requested. Units:
        [m^-1 SI or normalized inverse length].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    initialize_plasma_state
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_temporal_spectrum
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_spectral_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The local algebraic thermal model assembles the state matrix from the explicit
        species and configuration. Viscosity and relaxation fractions are clamped to the
        declared numerical range before assembly. Supported scope: Corrected local
        fluid/Maxwell generator, relativistic tangent inertia, algebraic anisotropic
        pressure response and physical similarity scales. No eigenspectrum, scans or
        plots are calculated. Excluded scope: Effective local algebraic thermal model;
        not full entropy evolution, CGL, kinetic physics, or the unmagnetized
        drift-directed Appendix A model; Background sources and prescribed acceleration
        per mass have zero perturbation response. Gradients define a local/eikonal
        symbol, not an inhomogeneous global Maxwell-Gauss boundary solution; The
        magnetic longitudinal pressure-divergence factor two is a phenomenological
        mirror correction; no universal kinetic mirror threshold or experimental
        accuracy claim; Relativistic inertia is d(gamma*v)/dv with noncovariant pressure
        and friction; no fully covariant thermodynamics claim.

    Examples
    --------
    >>> from scirel.kinetic import initialize_plasma_state, assemble_spectral_matrix
    >>> m = assemble_spectral_matrix(initialize_plasma_state(), .1, .2)
    >>> assert m['M'].shape == (14, 14)
    """
    state = _state(state)
    rel = _integer(rel, "rel")
    if rel not in (0, 1):
        raise ValueError("rel must be 0 or 1")
    k = np.asarray([kx, 0, kz], dtype=complex)
    if k.shape != (3,) or not np.isfinite(k).all():
        raise ValueError("kx/kz must be finite scalar wave numbers")
    s = state["s"]
    fields = 4 * s
    M = np.zeros((fields + 6, fields + 6), dtype=complex)
    A = np.eye(fields + 6, dtype=complex)
    for j, data in enumerate(state["species"]):
        q, mass, n = data[:3]
        v = data[3:6]
        eps = np.array([data[8], data[9], 0.0])
        density = 4 * j
        vel = slice(density + 1, density + 4)
        convective = -1j * (k @ v)
        M[density, density] = convective
        M[density, vel] = -n * (1j * k + eps)
        inertia = np.eye(3)
        if rel:
            speed2 = v @ v / state["c2"]
            if speed2 >= 1:
                raise ValueError("relativistic velocity must be strictly subluminal")
            gamma = 1 / np.sqrt(1 - speed2)
            inertia = gamma * np.eye(3) + gamma**3 * np.outer(v, v) / state["c2"]
        A[vel, vel] = inertia
        M[vel, vel] = convective * inertia - q / mass * _cross([0.0, 0.0, state["B0"]])
        thermal = np.array([state["csp2"][j], state["csp2"][j], state["csz2"][j]])
        M[vel, density] = (-1j * thermal * k + thermal * eps / state["gammaTs"][j]) / n
        M[vel, fields : fields + 3] = q / mass * np.eye(3)
        M[vel, fields + 3 : fields + 6] = q / mass * _cross(v)
        d = state["Deltas"][j] / state["rhos0"][j]
        M[density + 1, fields + 3] += -1j * k[2] * d
        M[density + 2, fields + 4] += -1j * k[2] * d
        # Empirical mirror correction applies to the entire z divergence.
        M[density + 3, fields + 3] += -2 * (1j * k[0] + eps[0]) * d
        M[density + 3, fields + 4] += -2 * eps[1] * d
        M[fields : fields + 3, density] = -q * v / state["epsilon0"]
        M[fields : fields + 3, vel] = -q * n / state["epsilon0"] * np.eye(3)
        for other in range(s):
            target = slice(4 * other + 1, 4 * other + 4)
            M[vel, target] += state["nu"][j, other] * np.eye(3)
    M[fields : fields + 3, fields + 3 : fields + 6] = 1j * state["c2"] * _cross(k)
    M[fields + 3 : fields + 6, fields : fields + 3] = -1j * _cross(k)
    if not np.isfinite(M).all() or not np.isfinite(A).all():
        raise ValueError("matrix exceeds finite numeric domain")
    # Positive physical state scales, independent of k and eigenvalues.
    c = np.sqrt(state["c2"])
    bscale = np.sqrt(np.sum(state["rhos0"]) / state["epsilon0"])
    scales = np.r_[
        np.column_stack([state["ns0"], np.full((s, 3), c)]).ravel(),
        np.full(3, c * bscale),
        np.full(3, bscale),
    ]
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("state scaling exceeds finite numeric domain")
    return {"M": M, "A": A, "state": state, "scales": scales, "kx": complex(kx), "kz": complex(kz)}


def _residuals(M, A, values, V):
    """Return global and active-component backward residuals.

    The worst component metric excludes rows below 1e-12 of the per-column
    global scale. Those inactive rows still enter ``errors`` and the finite
    checks; a nonfinite residual is never hidden by the active mask.
    """
    # Normalize the producer before forming products, avoiding overflow in
    # the norm or |lambda|*norm(A). This is backward error, not mode accuracy.
    f = max(
        float(np.max(np.abs(M))), float(np.max(np.abs(A))) * max(1.0, float(np.max(np.abs(values))))
    )
    if not np.isfinite(f):
        raise ValueError("eigenproblem residual scale exceeds finite numeric domain")
    if f == 0:
        return np.zeros(len(values)), 0.0
    m, a = M / f, A / f
    residual = m @ V - (a @ V) * values
    component = np.abs(m) @ np.abs(V) + (np.abs(a) @ np.abs(V)) * np.abs(values)
    global_scale = np.max(component, axis=0)
    floor = np.maximum(global_scale * np.finfo(float).eps, np.finfo(float).tiny)
    errors = np.max(np.abs(residual), axis=0) / np.maximum(global_scale, np.finfo(float).tiny)
    perrow = np.abs(residual) / np.maximum(component, floor[None, :])
    active = component > global_scale[None, :] * 1e-12
    worst = float(np.max(np.where(active, perrow, 0.0)))
    if not np.isfinite(errors).all() or not np.isfinite(worst):
        raise ArithmeticError("nonfinite eigensolution residual")
    return errors, worst


def solve_temporal_spectrum(M, A, *, vectors=False, oldmethod=2, scales=None, output_count=None):
    r"""Solve the local spectral temporal eigenproblem.

    Parameters
    ----------
    M : complex array-like
        Temporal generator. Shape: [N,N]. Constraints: Nonempty finite square matrix.
        Units: [row derivative units divided by column state units].
    A : complex array-like
        Inertia matrix of same size. Shape: [N,N]. Constraints: Nonsingular for finite
        modes. Units: [inertia conventions paired with M].
    vectors : bool, optional
        Expose corresponding eigenvector columns. Shape: scalar. Constraints: Does not
        change the eigenvalue calculation path. Default: False. Units: [dimensionless].
    oldmethod : int, optional
        Numerical initial solver selector. Shape: scalar. Constraints: 1 generalized
        SciPy eig; 2 eig of solve(A,M); both use balanced coordinates and the same
        refinement checks. Default: 2. Units: [dimensionless].
    scales : real array-like or None, optional
        Optional positive physical similarity scales. Shape: [N] or null. Constraints:
        Both M and A transformed identically; radix-two balance follows. None uses
        balancing alone. Default: None. Units: [state units per component].
    output_count : int or None, optional
        Optional positional local return count. Shape: scalar or null. Constraints: 0..6
        returns (M,A,w1,w2,X1,X2) prefix; five now has a defined X1. None returns the
        documented mapping. Default: None. Units: [dimensionless].

    Returns
    -------
    w1 : complex128
        Frequencies sorted by decreasing real part. Shape: [N]. Constraints:
        omega=i*lambda; stable ties; not mode tracking. Units: [s^-1 SI or normalized
        frequency].
    w2 : complex128
        Same modes sorted by decreasing imaginary part. Shape: [N]. Constraints:
        Independent sort order. Units: [s^-1 SI or normalized frequency].
    X1 : complex128
        Eigenvector columns corresponding to w1. Shape: [N,N]. Constraints: Only
        vectors=True (or positional return); arbitrary phase and degenerate basis.
        Units: [mixed state units with max-absolute normalization].
    X2 : complex128
        Eigenvector columns corresponding to w2. Shape: [N,N]. Constraints: Only
        vectors=True (or positional return). Units: [mixed state units with max-absolute
        normalization].
    residual1 : float64
        Scaled global backward error for w1. Shape: [N]. Constraints: Finite and at
        most1e-10; not a forward-accuracy certificate. Units: [dimensionless].
    residual2 : float64
        Scaled global backward error for w2. Shape: [N]. Constraints: Same criterion.
        Units: [dimensionless].
    component_residual : float64
        Maximum active component backward error. Shape: scalar. Constraints: 50-decimal
        fallback if double exceeds1e-12; reject if final exceeds1e-10. Units:
        [dimensionless].
    precision : string
        Actual arithmetic path. Shape: scalar. Constraints: complex128 or
        mpmath-50-decimal-to-complex128; original input coefficients remain double
        precision. Units: [dimensionless].
    oldmethod : int
        Selected initial method. Shape: scalar. Constraints: 1 or2. Units:
        [dimensionless].

    Raises
    ------
    ArithmeticError
        If eigenvalue qualification cannot establish a finite numerical result.
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    initialize_plasma_state
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_spectral_matrix
        Related kinetic amplitude or dispersion operator in the same workflow.
    evaluate_spectral_dispersion
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The generalized eigensolver returns frequencies sorted independently by real
        part, together with paired eigenvalues and eigenvectors. Residual and
        conditioning values qualify the numerical solve but do not establish continuous
        branch identity. Supported scope: Dense generalized temporal eigenproblem with
        coherent values/vectors, stable independent real/imaginary sorts and
        backward-residual-controlled arithmetic. Excluded scope: No species
        initialization, unit conversion, physical sign/relativity validation, scan
        scheduling, plotting or mode tracking; No universal forward eigenvalue accuracy,
        unique degenerate polarizations or recovery of precision lost in input
        coefficients; Evaluated locally under the declared authorization only;
        redistribution rights remain NOT_ESTABLISHED.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import solve_temporal_spectrum
    >>> r = solve_temporal_spectrum(np.diag([-1j, 2j]), np.eye(2), vectors=True)
    >>> np.testing.assert_allclose(r['w1'], [1, -2])
    """
    M, A = np.asarray(M, dtype=complex), np.asarray(A, dtype=complex)
    if M.ndim != 2 or M.shape[0] != M.shape[1] or M.size == 0 or A.shape != M.shape:
        raise ValueError("M,A must be equally sized nonempty square matrices")
    if not np.isfinite(M).all() or not np.isfinite(A).all():
        raise ValueError("M,A must be finite")
    if not isinstance(vectors, (bool, np.bool_)):
        raise ValueError("vectors must be boolean")
    oldmethod = _integer(oldmethod, "oldmethod")
    if oldmethod not in (1, 2):
        raise ValueError("oldmethod must be 1 or 2")
    # Standalone callers may not carry physical state scales. LAPACK radix-two
    # similarity balancing of M then supplies a data-dependent conditioning
    # transformation; A receives exactly the same transform.
    scale = np.ones(len(M)) if scales is None else _vector(scales, len(M), "scales", positive=True)
    Ms = M / scale[:, None] * scale[None, :]
    As = A / scale[:, None] * scale[None, :]
    if not np.isfinite(Ms).all() or not np.isfinite(As).all():
        raise ValueError("scaled matrices must be finite")
    # SciPy is a core runtime dependency, but only spectrum solving needs its
    # linear-algebra backend. Keep state initialization and matrix assembly
    # usable without importing the heavy backend, and preserve all input
    # validation before the backend boundary.
    from scipy import linalg

    radix = linalg.matrix_balance(Ms, permute=False, separate=True)[1][0]
    Ms = Ms / radix[:, None] * radix[None, :]
    As = As / radix[:, None] * radix[None, :]
    scale = scale * radix
    if not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("combined similarity scaling exceeds numeric domain")
    if oldmethod == 1:
        values, V = linalg.eig(Ms, As)
    else:
        values, V = linalg.eig(linalg.solve(As, Ms))
    if not np.isfinite(values).all() or not np.isfinite(V).all():
        raise ValueError("eigensolution is nonfinite; check singular inertia or conditioning")
    errors, worst = _residuals(Ms, As, values, V)
    precision = "complex128"
    if worst > 1e-12:
        import mpmath

        mp = mpmath.mp.clone()
        mp.dps = 50
        mm, aa = mp.matrix(Ms.tolist()), mp.matrix(As.tolist())
        # No double A^-1 precomputation in the high precision path.
        vv, vectors_mp = mp.eig(mp.inverse(aa) * mm)
        values = np.asarray([complex(v) for v in vv])
        V = np.asarray(vectors_mp.tolist(), dtype=complex)
        precision = "mpmath-50-decimal-to-complex128"
        errors, worst = _residuals(Ms, As, values, V)
    if np.max(errors) > 1e-10 or worst > 1e-10:
        raise ArithmeticError("eigensolution global/component backward residual exceeds 1e-10")
    # Normalize in logarithmic coordinates before unscaling, so a valid
    # vector is never destroyed by an overflowing intermediate product.
    amplitudes = np.abs(V)
    with np.errstate(divide="ignore", invalid="ignore"):
        logs = np.log(amplitudes) + np.log(scale[:, None])
    offset = np.max(logs, axis=0)
    phase = np.divide(V, amplitudes, out=np.zeros_like(V), where=amplitudes != 0)
    V = phase * np.exp(logs - offset)
    if (
        not np.isfinite(values).all()
        or not np.isfinite(V).all()
        or np.any(np.max(np.abs(V), axis=0) == 0)
    ):
        raise ArithmeticError("unscaled eigenvectors or values are nonfinite/zero")
    omega = 1j * values
    i1 = np.argsort(-omega.real, kind="stable")
    i2 = np.argsort(-omega.imag, kind="stable")
    out = {
        "w1": omega[i1],
        "w2": omega[i2],
        "residual1": errors[i1],
        "residual2": errors[i2],
        "precision": precision,
        "oldmethod": oldmethod,
        "component_residual": worst,
    }
    if vectors or output_count is not None:
        out.update(X1=V[:, i1], X2=V[:, i2])
    if output_count is not None:
        count = _integer(output_count, "output_count")
        if not 0 <= count <= 6:
            raise ValueError("local output_count must be 0..6")
        return (M, A, out["w1"], out["w2"], out["X1"], out["X2"])[:count]
    return out


def _grid(value, default, name):
    arr = _real(default if value is None else value, name)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name} must be a nonempty vector")
    return arr


def _plot(out, path):
    """Return presentation metadata without importing a plotting backend."""
    if out["method"] == 4:
        modes = out["ww1"].shape[-1]
    else:
        modes = (
            2 * out["state"]["s"] + 1
            if out["unit"] == "normalized" or out["method"] == 3
            else out["ww1"].shape[-1]
        )
    png = b""
    if path is not None:
        Path(path).write_bytes(png)
    return {"axes_count": 2, "mode_count": modes}, png


def evaluate_spectral_dispersion(
    species=None,
    *,
    unit="normalized",
    method=2,
    rel=0,
    vectors=False,
    oldmethod=2,
    prior=None,
    cfg=None,
    k_grid=None,
    theta_grid=None,
    kx_grid=None,
    kz_grid=None,
    k=0.1,
    theta=np.pi / 3,
    max_points=10000,
    plot_path=None,
    output_count=None,
):
    r"""Scan the local spectral multifluid dispersion graph.

    Parameters
    ----------
    species : real array-like or string, optional
        Rows q,m,n,vx,vy,vz,cs_parallel,cs_perpendicular,eps_x,eps_y; one header line
        for text. Shape: [s,10] or text. Constraints: s>=1, m/n>0, cs>=0; None uses
        documented example rows; rows are independent fluids, including equal rows.
        Default normalized rows: [-1,1,4,0,0,0,0,0,0,0], [1,4,4,0,0,0,0,0,0,0]. Default
        SI rows: [-1.602e-19,9.109e-31,8.7e6,0,0,0,4.631e6,4.631e6,0,0],
        [1.602e-19,1.673e-27,8.7e6,0,0,0,9.360e4,9.360e4,0,0]. Default: None. Units: [SI
        C,kg,m^-3,m/s,m^-1 by quantity; normalized units fixed by explicit c2,epsilon0
        and B0].
    unit : string, optional
        Unit convention and default constants. Shape: scalar. Constraints: normalized or
        si, without input conversion. Default: 'normalized'. Units: [dimensionless].
    method : int, optional
        Scan selector. Shape: scalar. Constraints: 0/1 and unknown nonnegative integers
        single point;2 magnitude,3 angle,4 Cartesian mesh. Default: 2. Units:
        [dimensionless].
    rel : int, optional
        Inertia selector passed unchanged to matrix assembly. Shape: scalar.
        Constraints: 0 or1; rel1 strictly subluminal. Default: 0. Units:
        [dimensionless].
    vectors : bool, optional
        Expose corresponding eigenvector columns. Shape: scalar. Constraints: Does not
        change the eigenvalue calculation path. Default: False. Units: [dimensionless].
    oldmethod : int, optional
        Numerical initial solver selector. Shape: scalar. Constraints: 1 generalized
        SciPy eig; 2 eig of solve(A,M); both use balanced coordinates and the same
        refinement checks. Default: 2. Units: [dimensionless].
    prior : dict or None, optional
        Prior state accepted for call compatibility, never used as primary scientific
        input. Shape: mapping or null. Constraints: Every field is freshly derived;
        prior is not mutated. Default: None. Units: [state convention].
    cfg : dict or None, optional
        Constants B0,c2,epsilon0,gammaTs; collision controls and classification. Shape:
        mapping or null. Constraints: Only documented fields; c2/epsilon0/gammaTs>0.
        Explicit rates receiver i toward j, zero diagonal, nonnegative and rho
        reciprocal. drag_rates>=0. Legacy nue/nui light/heavy bath, nuei light-receiver
        cross-class, same-class nuee/nuii lower-rho receiver. Default mass classes
        normalized<=1 or SI<=9.1093837139e-31 kg; collision_classes explicit light/heavy
        (electron/ion aliases) overrides. These are numerical categories, not inferred
        species identities. Defaults normalized: B0=1,c2=1,epsilon0=1,gammaTs=1; SI:
        B0=8e-9 T,c2=(2.9979e8)^2,epsilon0=8.854e-12,gammaTs=5/3. All five legacy rates
        zero; absent explicit pair/drag rates derive from those zero controls. Default
        classes use the declared mass threshold. Default: None. Units: [B0 in T/SI or
        normalized; c2 speed squared; epsilon0 SI or normalized; rates s^-1 or
        normalized frequency].
    k_grid : real array-like or None, optional
        Magnitude scan override. Shape: [K] or null. Constraints: Finite nonempty;
        method2 only. Default101 normalized or196 SI literal-source samples. Default:
        None. Units: [m^-1 SI or normalized inverse length].
    theta_grid : real array-like or None, optional
        Angle scan override. Shape: [T] or null. Constraints: Finite nonempty; method3
        only. Default51 samples0..pi/2. Default: None. Units: [rad].
    kx_grid : real array-like or None, optional
        Cartesian x scan override. Shape: [X] or null. Constraints: Finite nonempty;
        method4 only. Default75 samples. Shape order [Z,X,N]. Default: None. Units:
        [m^-1 SI or normalized inverse length].
    kz_grid : real array-like or None, optional
        Cartesian z scan override. Shape: [Z] or null. Constraints: Finite nonempty;
        method4 only. Default50 samples. Default: None. Units: [m^-1 SI or normalized
        inverse length].
    k : complex numeric, optional
        Single-point wave number. Shape: scalar. Constraints: Finite; applies only
        single branch. Angle sweep retains source k=2. Default: 0.1. Units: [m^-1 SI or
        normalized inverse length].
    theta : real numeric, optional
        Single-point propagation angle from z. Shape: scalar. Constraints: Finite;
        method2 takes the declared pi/4 angle in normalized units, or 0 in SI. Default:
        1.0471975511965976. Units: [rad].
    max_points : int, optional
        Upper bound on solved scan points. Shape: scalar. Constraints: Positive; whole
        requested scan must fit. No feedback or iteration. Default: 10000. Units:
        [dimensionless].
    plot_path : path-like or None, optional
        Optional compatibility path; current implementation does not render an image.
        Shape: scalar or null. Constraints: Accepted by the signature; no PNG is
        produced by the current implementation. Default: None. Units: [filesystem path].
    output_count : int or None, optional
        Optional source-position public return prefix. Shape: scalar or null.
        Constraints: normalized0..4,SI0..17. All branches now define kk,ww1,ww2. None
        returns mapping. Default: None. Units: [dimensionless].

    Returns
    -------
    M : complex128
        Temporal generator with species [dn,dvx,dvy,dvz] then [Ex,Ey,Ez,Bx,By,Bz].
        Shape: [4s+6,4s+6]. Constraints: Finite; lambda*A*x=M*x and omega=i*lambda.
        Units: [row output units per second divided by column state units; normalized
        analog].
    A : complex128
        Inertia matrix. Shape: [4s+6,4s+6]. Constraints: Identity except d(gamma*v)/dv
        in rel=1 velocity blocks. Units: [dimensionless within equally scaled velocity
        blocks].
    state : dict
        Revalidated fresh state used by the matrix. Shape: mapping. Constraints: No
        stale derived fields; preserves explicit collision classes. Units: [per-state
        quantity conventions].
    scales : float64
        Positive physical state-column scales for similarity transformation. Shape:
        [4s+6]. Constraints: Density=n_j, velocity=c, B=sqrt(sum(rho)/epsilon0), E=c*B;
        transforms rows and columns consistently. Units: [density,velocity,electric
        field,magnetic field by component].
    kx : complex
        Accepted wave number x. Shape: scalar. Constraints: Same as requested. Units:
        [m^-1 SI or normalized inverse length].
    kz : complex
        Accepted wave number z. Shape: scalar. Constraints: Same as requested. Units:
        [m^-1 SI or normalized inverse length].
    w1 : complex128
        Frequencies sorted by decreasing real part. Shape: [N]. Constraints:
        omega=i*lambda; stable ties; not mode tracking. Units: [s^-1 SI or normalized
        frequency].
    w2 : complex128
        Same modes sorted by decreasing imaginary part. Shape: [N]. Constraints:
        Independent sort order. Units: [s^-1 SI or normalized frequency].
    X1 : complex128
        Eigenvector columns corresponding to w1. Shape: [N,N]. Constraints: Only the
        mapping with vectors=True exposes corresponding last-point vectors; public
        positional prefixes do not contain vectors. Arbitrary phase and degenerate
        basis. Units: [mixed state units with max-absolute normalization].
    X2 : complex128
        Eigenvector columns corresponding to w2. Shape: [N,N]. Constraints: Only the
        mapping with vectors=True exposes corresponding last-point vectors; public
        positional prefixes do not contain vectors. Arbitrary phase and degenerate
        basis. Units: [mixed state units with max-absolute normalization].
    residual1 : float64
        Scaled global backward error for w1. Shape: [N]. Constraints: Finite and at
        most1e-10; not a forward-accuracy certificate. Units: [dimensionless].
    residual2 : float64
        Scaled global backward error for w2. Shape: [N]. Constraints: Same criterion.
        Units: [dimensionless].
    component_residual : float64
        Maximum active component backward error. Shape: scalar. Constraints: 50-decimal
        fallback if double exceeds1e-12; reject if final exceeds1e-10. Units:
        [dimensionless].
    precision : string
        Actual arithmetic path. Shape: scalar. Constraints: complex128 or
        mpmath-50-decimal-to-complex128; original input coefficients remain double
        precision. Units: [dimensionless].
    oldmethod : int
        Selected initial method. Shape: scalar. Constraints: 1 or2. Units:
        [dimensionless].
    method : int
        Executed selector. Shape: scalar. Constraints: Exact supplied method. Units:
        [dimensionless].
    unit : string
        Unit convention. Shape: scalar. Constraints: normalized or si. Units:
        [dimensionless].
    kk : numeric array
        Magnitude data. Shape: [K], [T], [Z,X], or[1]. Constraints: Always defined; SI
        nonscan arities do not return undefined fields. Units: [m^-1 SI or normalized
        inverse length].
    tt : float64 array
        Angle-scan abscissa. Shape: [T] or empty. Constraints: Populated only method3.
        Units: [rad].
    kkx : float64 array
        Cartesian mesh x component. Shape: [Z,X] or empty. Constraints: Only method4.
        Units: [m^-1 SI or normalized inverse length].
    kkz : float64 array
        Cartesian mesh z component. Shape: [Z,X] or empty. Constraints: Only method4.
        Units: [m^-1 SI or normalized inverse length].
    ww1 : complex128
        Real-part independently sorted frequencies at every point. Shape:
        [K,N],[T,N],[Z,X,N],or[1,N]. Constraints: Full scan arrays; not continuous mode
        tracking. Units: [s^-1 SI or normalized frequency].
    ww2 : complex128
        Imaginary-part independently sorted frequencies at every point. Shape: same as
        ww1. Constraints: Full scan arrays. Units: [s^-1 SI or normalized frequency].
    points : int
        Number of solved points. Shape: scalar. Constraints: At most max_points. Units:
        [dimensionless].
    execution_order : string
        Explicit sequencing. Shape: scalar. Constraints: initialize; row-major
        assemble/spectrum; plot. Units: [dimensionless].
    max_points : int
        Enforced point limit. Shape: scalar. Constraints: Same as supplied. Units:
        [dimensionless].
    graphics : dict
        Axes and plotted mode counts. Shape: mapping. Constraints: Two axes for2/3/4,
        zero axes for other selectors; no one-species mass title indexing or zero color
        index. Units: [dimensionless].
    plot_png : bytes
        Empty bytes in the current implementation; retained for signature compatibility.
        Shape: bytes or absent. Constraints: Empty payload; no image is rendered. Units:
        [bytes].

    Raises
    ------
    ArithmeticError
        If eigenvalue qualification cannot establish a finite numerical result.
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    initialize_plasma_state
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_spectral_matrix
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_temporal_spectrum
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The graph initializes a local state, assembles each requested matrix, solves its
        ordinary or generalized eigenproblem, and then records plotting metadata. Mode
        branches are sorted independently at each point and are not tracked
        continuously. Supported scope: The complete normalized/SI local multi-fluid
        mapping, the declared scan selectors and caller-owned state under the explicitly
        declared effective closure. Excluded scope: Effective local algebraic thermal
        model; not full entropy evolution, CGL, kinetic physics, or the unmagnetized
        drift-directed Appendix A model; Background sources and prescribed acceleration
        per mass have zero perturbation response. Gradients define a local/eikonal
        symbol, not an inhomogeneous global Maxwell-Gauss boundary solution; The
        magnetic longitudinal pressure-divergence factor two is a phenomenological
        mirror correction; no universal kinetic mirror threshold or experimental
        accuracy claim; Relativistic inertia uses d(gamma*v)/dv with noncovariant
        pressure and friction; no fully covariant thermodynamics claim is made.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_spectral_dispersion
    >>> r = evaluate_spectral_dispersion(method=2, k_grid=[0, .1])
    >>> assert r['ww1'].shape == (2, 14) and r['graphics']['axes_count'] == 2
    """
    state = initialize_plasma_state(species, unit=unit, prior=prior, cfg=cfg)
    method = _integer(method, "method")
    limit = _integer(max_points, "max_points")
    if method < 0 or limit < 1:
        raise ValueError("method must be nonnegative and max_points positive")
    kk = tt = xx = zz = np.empty(0)
    if method == 2:
        default = (
            np.arange(101) * 0.1
            if unit == "normalized"
            else np.r_[
                np.arange(101) * 1e-7, 2e-5 + np.arange(37) * 5e-6, 3e-4 + np.arange(58) * 1e-4
            ]
        )
        kk = _grid(k_grid, default, "k_grid")
        angle = np.pi / 4 if unit == "normalized" else 0.0
        kxs, kzs = kk * np.sin(angle), kk * np.cos(angle)
        shape = (len(kk),)
    elif method == 3:
        tt = _grid(theta_grid, np.arange(51) * np.pi / 100, "theta_grid")
        kxs, kzs = 2 * np.sin(tt), 2 * np.cos(tt)
        kk = np.full(len(tt), 2.0)
        shape = (len(tt),)
    elif method == 4:
        x = _grid(kx_grid, 0.01 + np.arange(75) * 0.04, "kx_grid")
        z = _grid(kz_grid, 0.01 + np.arange(50) * 0.04, "kz_grid")
        if len(x) * len(z) > limit:
            raise ValueError("scan exceeds max_points")
        xx, zz = np.meshgrid(x, z)
        kxs, kzs, shape = xx.ravel(), zz.ravel(), xx.shape
        kk = np.sqrt(xx**2 + zz**2)
    else:
        kval = np.asarray(k)
        if kval.ndim != 0 or kval.dtype.kind not in "iufc" or not np.isfinite(kval):
            raise ValueError("k must be a finite complex scalar")
        angle = _scalar(theta, "theta")
        kxs, kzs = [complex(kval) * np.sin(angle)], [complex(kval) * np.cos(angle)]
        kk = np.asarray([complex(kval)])
        shape = (1,)
    if len(kxs) > limit:
        raise ValueError("scan exceeds max_points")
    w1, w2 = [], []
    for x, z in zip(kxs, kzs):
        matrix = assemble_spectral_matrix(state, x, z, rel=rel)
        spectrum = solve_temporal_spectrum(
            matrix["M"], matrix["A"], vectors=vectors, oldmethod=oldmethod, scales=matrix["scales"]
        )
        w1.append(spectrum["w1"])
        w2.append(spectrum["w2"])
    out = dict(
        matrix,
        **spectrum,
        method=method,
        unit=unit,
        kk=kk,
        tt=tt,
        kkx=xx,
        kkz=zz,
        ww1=np.asarray(w1).reshape(shape + (-1,)),
        ww2=np.asarray(w2).reshape(shape + (-1,)),
        points=len(kxs),
        execution_order="initialize; row-major assemble/spectrum; plot",
        max_points=limit,
        graphics={"axes_count": 0, "mode_count": 0},
    )
    if method in (2, 3, 4):
        out["graphics"], out["plot_png"] = _plot(out, plot_path)
    elif plot_path is not None:
        raise ValueError("single-point selector has no plot; plot_path requires method 2/3/4")
    if output_count is not None:
        count = _integer(output_count, "output_count")
        maximum = 4 if unit == "normalized" else 17
        if not 0 <= count <= maximum:
            raise ValueError(f"public output_count must be 0..{maximum}")
        fields = (
            out["M"],
            out["A"],
            out["w1"],
            out["w2"],
            out["kk"],
            out["ww1"],
            out["ww2"],
            state["betasz"],
            state["vA"],
            state["csz2"],
            state["c2"],
            state["rhos0"],
            state["wcs"],
            state["qs"],
            state["ms"],
            state["wps"],
            state["B0"],
        )
        return fields[:count]
    return out
