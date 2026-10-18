"""Effective multi-fluid temporal dispersion, derived in PDRF D2.

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

from scirel._optional import import_optional_module

__all__ = ["initialize_pdrf_plasma", "assemble_pdrf_matrix",
           "solve_pdrf_spectrum", "evaluate_pdrf_dispersion"]


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


def _species_data(species, unit):
    if species is None:
        # Scientific example inputs, not captured answers or source runtime files.
        if unit == "normalized":
            species = [[-1, 1, 4, 0, 0, 0, 0, 0, 0, 0],
                       [1, 4, 4, 0, 0, 0, 0, 0, 0, 0]]
        else:
            species = [[-1.602e-19, 9.109e-31, 8.7e6, 0, 0, 0, 4.631e6, 4.631e6, 0, 0],
                       [1.602e-19, 1.673e-27, 8.7e6, 0, 0, 0, 9.360e4, 9.360e4, 0, 0]]
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


def initialize_pdrf_plasma(species=None, *, unit="normalized", prior=None, cfg=None):
    """Build fresh caller-owned state; ten columns q,m,n,vx,vy,vz,csz,csp,epsx,epsy.

    SI uses C, kg, m^-3, m/s and m^-1; normalized uses c=epsilon0=1
    defaults. gamma defaults to 1 normalized or 5/3 SI. Explicit constants
    define the normalization. ``prior`` is accepted only as a mapping and
    deliberately contributes no scientific fields: every input is recomputed.
    The externally maintained background permits nonzero charge/current/gradient;
    it does not claim unforced equilibrium. Equal rows remain distinct fluids.
    ``collision_rates[i,j]`` is receiver i's nonnegative rate toward j;
    its diagonal is zero, rho_i*rate_ij=rho_j*rate_ji. ``drag_rates`` couples
    each fluid to a stationary external bath. Legacy rate controls use explicit
    numerical light/heavy mass categories (normalized <=1 or SI
    <=9.1093837139e-31 kg), not inferred physical species. collision_classes
    overrides them with light/heavy labels (electron/ion are aliases). nue/nui
    denote light/heavy bath rates; nuei is the light receiver's rate toward a
    heavy fluid. For a same-class pair, nuee/nuii is the lower-rho receiver's
    rate. Reverse rates enforce rho reciprocity; ordering does not change them.
    """
    if unit not in ("normalized", "si"):
        raise ValueError("unit must be normalized or si")
    if prior is not None and not isinstance(prior, dict):
        raise ValueError("prior must be a mapping or None")
    cfg = dict(cfg or {})
    allowed = {"B0", "c2", "epsilon0", "gammaTs", "nue", "nui", "nuee", "nuii", "nuei",
               "collision_rates", "drag_rates", "collision_classes"}
    if set(cfg) - allowed:
        raise ValueError(f"unknown configuration fields: {sorted(set(cfg)-allowed)}")
    data = _species_data(species, unit)
    s = len(data)
    B0 = _scalar(cfg.get("B0", 1. if unit == "normalized" else 8e-9), "B0")
    c2 = _scalar(cfg.get("c2", 1. if unit == "normalized" else 2.9979e8**2), "c2", True)
    epsilon0 = _scalar(cfg.get("epsilon0", 1. if unit == "normalized" else 8.854e-12), "epsilon0", True)
    gamma = _vector(cfg.get("gammaTs", 1. if unit == "normalized" else 5/3), s, "gammaTs", positive=True)
    qs, ms, ns = data[:, 0], data[:, 1], data[:, 2]
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        rho = ms*ns
        csz2, csp2 = data[:, 6]**2, data[:, 7]**2
        Psz, Psp = rho*csz2/gamma, rho*csp2/gamma
        mu0 = 1/(c2*epsilon0)
        current = np.sum((qs*ns)[:, None]*data[:, 3:6], axis=0)
        charge = np.sum(qs*ns)
        beta_z = 2*mu0*Psz/B0**2 if B0 != 0 else None
        beta_p = 2*mu0*Psp/B0**2 if B0 != 0 else None
        delta = (Psz-Psp)/B0 if B0 != 0 else np.zeros(s)
        va = B0/np.sqrt(mu0*rho)
        wcs = qs*B0/ms
        wps = np.sqrt(ns/epsilon0/ms)*np.abs(qs)
    if np.any(rho <= 0) or not np.isfinite(np.r_[rho, csz2, csp2, Psz, Psp, delta, va, wcs, wps, current, charge, mu0]).all():
        raise ValueError("derived plasma state exceeds finite numeric domain")
    if beta_z is not None and not np.isfinite(np.r_[beta_z, beta_p]).all():
        raise ValueError("beta exceeds finite numeric domain")
    legacy = {name: _scalar(cfg.get(name, 0.), name) for name in ("nue", "nui", "nuee", "nuii", "nuei")}
    if any(value < 0 for value in legacy.values()):
        raise ValueError("collision rates must be nonnegative")
    if ("collision_rates" in cfg or "drag_rates" in cfg) and any(legacy.values()):
        raise ValueError("choose explicit collision rates or legacy controls")
    # Numerical mass categories, not inferred physical species identity.
    light = ms <= (1. if unit == "normalized" else 9.1093837139e-31)
    if "collision_classes" in cfg:
        classes = np.asarray(cfg["collision_classes"])
        if classes.shape != (s,) or not np.isin(classes, ["light", "heavy", "electron", "ion"]).all():
            raise ValueError("collision_classes needs s light/heavy (electron/ion aliases) labels")
        light = np.isin(classes, ["light", "electron"])
    drag = _vector(cfg.get("drag_rates", np.where(light, legacy["nue"], legacy["nui"])), s, "drag_rates", nonnegative=True)
    rates = np.zeros((s, s))
    if "collision_rates" in cfg:
        rates = _real(cfg["collision_rates"], "collision_rates")
        if rates.shape != (s, s) or np.any(rates < 0) or np.any(np.diag(rates) != 0):
            raise ValueError("collision_rates needs nonnegative (s,s) with zero diagonal")
    else:
        for i in range(s):
            for j in range(i+1, s):
                if light[i] == light[j]:
                    rate = legacy["nuee"] if light[i] else legacy["nuii"]
                    receiver, other = (i, j) if rho[i] <= rho[j] else (j, i)
                else:
                    receiver, other, rate = (i, j, legacy["nuei"]) if light[i] else (j, i, legacy["nuei"])
                rates[receiver, other] = rate
                rates[other, receiver] = rate*(rho[receiver]/rho[other])
                if rate > 0 and rates[other, receiver] == 0:
                    raise ValueError("reciprocal collision rate exceeds finite numeric domain")
    # Both interfaces must meet the same physical and representability contract.
    # Positive rates with zero weighted flux cannot prove momentum reciprocity.
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        flux = rho[:, None]*rates
    if not np.isfinite(flux).all() or np.any((rates > 0) & (flux == 0)):
        raise ValueError("collision momentum flux exceeds finite numeric domain")
    scale = np.maximum(np.abs(flux), np.abs(flux.T))
    if np.any(np.abs(flux-flux.T) > 1e-12*scale):
        raise ValueError("collision_rates must conserve pairwise momentum")
    collision = rates.copy()
    np.fill_diagonal(collision, -drag-rates.sum(axis=1))
    if not np.isfinite(collision).all():
        raise ValueError("collision matrix exceeds finite numeric domain")
    return {"s": s, "unit": unit, "species": data, "qs": qs.copy(), "ms": ms.copy(), "ns0": ns.copy(),
            "vs0x": data[:, 3].copy(), "vs0y": data[:, 4].copy(), "vs0z": data[:, 5].copy(),
            "csz2": csz2, "csp2": csp2, "epsnx": data[:, 8].copy(), "epsny": data[:, 9].copy(),
            "rhos0": rho, "Q0": float(charge), "J0x": float(current[0]), "J0y": float(current[1]), "J0z": float(current[2]),
            "nu": collision, "collision_rates": rates, "drag_rates": drag, "collision_classes": np.where(light, "light", "heavy"), "B0": B0, "c2": c2,
            "epsilon0": epsilon0, "mu0": mu0, "gammaTs": gamma, "Psz": Psz, "Psp": Psp,
            "betasz": beta_z, "betasp": beta_p, "Deltas": delta, "vA": va, "wcs": wcs, "wps": wps,
            "background": "externally-maintained-zero-perturbation-response", "pressure_closure": "algebraic-fixed-temperature-coefficients",
            "zero_field_director": "fixed-z", "mirror_factor": 2.}


def _cross(v):
    x, y, z = v
    return np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])


def _state(state):
    if not isinstance(state, dict) or "species" not in state:
        raise ValueError("state must be produced by initialize_pdrf_plasma")
    # Re-derive all science from explicit primary inputs; stale derived fields
    # cannot silently enter the matrix. A changed primary field is a new state.
    return initialize_pdrf_plasma(state["species"], unit=state["unit"], cfg={
        "B0": state["B0"], "c2": state["c2"], "epsilon0": state["epsilon0"],
        "gammaTs": state["gammaTs"], "collision_rates": state["collision_rates"],
        "drag_rates": state["drag_rates"], "collision_classes": state["collision_classes"]})


def assemble_pdrf_matrix(state, kx, kz, *, rel=0):
    """Assemble lambda*A*x=M*x, omega=i*lambda; species (dn,dvx,dvy,dvz), then E,B.

    k components may be finite complex scalars in declared inverse-length units.
    rel=1 uses d(gamma*v)/dv, requires |v0|<c, and retains this effective
    model's noncovariant algebraic pressure/friction terms. No relativistic
    kinetic or covariant thermodynamic claim is made. rel=0 uses unit inertia.
    """
    state = _state(state)
    rel = _integer(rel, "rel")
    if rel not in (0, 1):
        raise ValueError("rel must be 0 or 1")
    k = np.asarray([kx, 0, kz], dtype=complex)
    if k.shape != (3,) or not np.isfinite(k).all():
        raise ValueError("kx/kz must be finite scalar wave numbers")
    s = state["s"]
    fields = 4*s
    M = np.zeros((fields+6, fields+6), dtype=complex)
    A = np.eye(fields+6, dtype=complex)
    for j, data in enumerate(state["species"]):
        q, mass, n = data[:3]
        v = data[3:6]
        eps = np.array([data[8], data[9], 0.])
        density = 4*j
        vel = slice(density+1, density+4)
        convective = -1j*(k @ v)
        M[density, density] = convective
        M[density, vel] = -n*(1j*k+eps)
        inertia = np.eye(3)
        if rel:
            speed2 = v @ v / state["c2"]
            if speed2 >= 1:
                raise ValueError("relativistic velocity must be strictly subluminal")
            gamma = 1/np.sqrt(1-speed2)
            inertia = gamma*np.eye(3)+gamma**3*np.outer(v, v)/state["c2"]
        A[vel, vel] = inertia
        M[vel, vel] = convective*inertia - q/mass*_cross([0., 0., state["B0"]])
        thermal = np.array([state["csp2"][j], state["csp2"][j], state["csz2"][j]])
        M[vel, density] = (-1j*thermal*k+thermal*eps/state["gammaTs"][j])/n
        M[vel, fields:fields+3] = q/mass*np.eye(3)
        M[vel, fields+3:fields+6] = q/mass*_cross(v)
        d = state["Deltas"][j]/state["rhos0"][j]
        M[density+1, fields+3] += -1j*k[2]*d
        M[density+2, fields+4] += -1j*k[2]*d
        # Empirical mirror correction applies to the entire z divergence.
        M[density+3, fields+3] += -2*(1j*k[0]+eps[0])*d
        M[density+3, fields+4] += -2*eps[1]*d
        M[fields:fields+3, density] = -q*v/state["epsilon0"]
        M[fields:fields+3, vel] = -q*n/state["epsilon0"]*np.eye(3)
        for other in range(s):
            target = slice(4*other+1, 4*other+4)
            M[vel, target] += state["nu"][j, other]*np.eye(3)
    M[fields:fields+3, fields+3:fields+6] = 1j*state["c2"]*_cross(k)
    M[fields+3:fields+6, fields:fields+3] = -1j*_cross(k)
    if not np.isfinite(M).all() or not np.isfinite(A).all():
        raise ValueError("matrix exceeds finite numeric domain")
    # Positive physical state scales, independent of k and eigenvalues.
    c = np.sqrt(state["c2"])
    bscale = np.sqrt(np.sum(state["rhos0"])/state["epsilon0"])
    scales = np.r_[np.column_stack([state["ns0"], np.full((s, 3), c)]).ravel(),
                   np.full(3, c*bscale), np.full(3, bscale)]
    if not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError("state scaling exceeds finite numeric domain")
    return {"M": M, "A": A, "state": state, "scales": scales, "kx": complex(kx), "kz": complex(kz)}


def _residuals(M, A, values, V):
    # Normalize the producer before forming products, avoiding overflow in
    # the norm or |lambda|*norm(A). This is backward error, not mode accuracy.
    f = max(float(np.max(np.abs(M))), float(np.max(np.abs(A)))*max(1., float(np.max(np.abs(values)))))
    if not np.isfinite(f):
        raise ValueError("eigenproblem residual scale exceeds finite numeric domain")
    if f == 0:
        return np.zeros(len(values)), 0.
    m, a = M/f, A/f
    residual = m @ V-(a @ V)*values
    component = np.abs(m) @ np.abs(V)+(np.abs(a) @ np.abs(V))*np.abs(values)
    global_scale = np.max(component, axis=0)
    floor = np.maximum(global_scale*np.finfo(float).eps, np.finfo(float).tiny)
    errors = np.max(np.abs(residual), axis=0)/np.maximum(global_scale, np.finfo(float).tiny)
    perrow = np.abs(residual)/np.maximum(component, floor[None, :])
    active = component > global_scale[None, :]*1e-12
    worst = float(np.max(np.where(active, perrow, 0.)))
    if not np.isfinite(errors).all() or not np.isfinite(worst):
        raise ArithmeticError("nonfinite eigensolution residual")
    return errors, worst


def solve_pdrf_spectrum(M, A, *, vectors=False, oldmethod=2, scales=None, output_count=None):
    """Conditioned eigensystem with component checks and genuine precision fallback.

    oldmethod=1 is generalized eig; 2 explicitly solves A^-1*M. Both always
    compute eigenvectors so requested arity cannot select different precision.
    vpa conversion after double eig does not improve accuracy and is removed.
    A radix-two similarity balance follows optional physical state scaling.
    If active component backward errors exceed 1e-12, independently solve the
    same rounded input matrix at 50 decimal digits using mpmath, then convert
    to complex128. This is genuine arithmetic refinement of the specified
    matrix, not accuracy beyond the supplied double-precision physical inputs.
    Sorting real/imag parts independently is not branch tracking. Returned
    residuals use scaled coordinates; they establish backward error, not
    forward accuracy for ill-conditioned or degenerate eigenvalues.
    Optional output_count 0..6 returns (M,A,w1,w2,X1,X2)[:output_count].
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
    Ms = M/scale[:, None]*scale[None, :]
    As = A/scale[:, None]*scale[None, :]
    if not np.isfinite(Ms).all() or not np.isfinite(As).all():
        raise ValueError("scaled matrices must be finite")
    # SciPy is a core runtime dependency, but only spectrum solving needs its
    # linear-algebra backend. Keep state initialization and matrix assembly
    # usable without importing the heavy backend, and preserve all input
    # validation before the backend boundary.
    from scipy import linalg

    radix = linalg.matrix_balance(Ms, permute=False, separate=True)[1][0]
    Ms = Ms/radix[:, None]*radix[None, :]
    As = As/radix[:, None]*radix[None, :]
    scale = scale*radix
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
        vv, vectors_mp = mp.eig(mp.inverse(aa)*mm)
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
        logs = np.log(amplitudes)+np.log(scale[:, None])
    offset = np.max(logs, axis=0)
    phase = np.divide(V, amplitudes, out=np.zeros_like(V), where=amplitudes != 0)
    V = phase*np.exp(logs-offset)
    if not np.isfinite(values).all() or not np.isfinite(V).all() or np.any(np.max(np.abs(V), axis=0) == 0):
        raise ArithmeticError("unscaled eigenvectors or values are nonfinite/zero")
    omega = 1j*values
    i1 = np.argsort(-omega.real, kind="stable")
    i2 = np.argsort(-omega.imag, kind="stable")
    out = {"w1": omega[i1], "w2": omega[i2], "residual1": errors[i1], "residual2": errors[i2],
           "precision": precision, "oldmethod": oldmethod, "component_residual": worst}
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
    Figure = import_optional_module(
        "matplotlib.figure",
        extra="plot",
        feature="PDRF dispersion plotting",
    ).Figure
    FigureCanvasAgg = import_optional_module(
        "matplotlib.backends.backend_agg",
        extra="plot",
        feature="PDRF dispersion plotting",
    ).FigureCanvasAgg
    fig = Figure(figsize=(10, 4))
    FigureCanvasAgg(fig)
    real = fig.add_subplot(121, projection="3d" if out["method"] == 4 else None)
    imag = fig.add_subplot(122, projection="3d" if out["method"] == 4 else None)
    if out["method"] == 4:
        x, z = out["kkx"], out["kkz"]
        for mode in range(out["ww1"].shape[-1]):
            real.plot_surface(x, z, out["ww1"][..., mode].real, alpha=.4)
            imag.plot_surface(x, z, out["ww2"][..., mode].imag, alpha=.4)
        for ax in (real, imag):
            ax.set_xlabel("kx"); ax.set_ylabel("kz")
    else:
        grid = out["tt"] if out["method"] == 3 else out["kk"]
        modes = 2*out["state"]["s"]+1 if out["unit"] == "normalized" or out["method"] == 3 else out["ww1"].shape[-1]
        for mode in range(modes):
            real.plot(grid, out["ww1"][:, mode].real)
            imag.plot(grid, out["ww2"][:, mode].imag, ".")
        for ax in (real, imag):
            ax.set_xlabel("theta (rad)" if out["method"] == 3 else "k")
    for ax, label in ((real, "Re omega"), (imag, "Im omega")):
        (ax.set_zlabel if out["method"] == 4 else ax.set_ylabel)(label)
    fig.suptitle(f"Effective multi-fluid ({out['unit']}); separately sorted roots")
    stream = io.BytesIO()
    fig.savefig(stream, format="png")
    png = stream.getvalue()
    if path is not None:
        Path(path).write_bytes(png)
    return {"axes_count": 2, "mode_count": modes if out["method"] != 4 else out["ww1"].shape[-1]}, png


def evaluate_pdrf_dispersion(species=None, *, unit="normalized", method=2, rel=0,
                             vectors=False, oldmethod=2, prior=None, cfg=None,
                             k_grid=None, theta_grid=None, kx_grid=None, kz_grid=None,
                             k=.1, theta=np.pi/3, max_points=10000, plot_path=None,
                             output_count=None):
    """Ordered initialization -> assembly -> spectrum graph; bounded scan then plot.

    Methods 0/1 and unknown nonnegative integers select a single point. 2 scans
    magnitude (default angle pi/4 normalized, zero SI), 3 scans angle at k=2,
    4 scans a Cartesian mesh in row-major (kz,kx) order. Default source grids
    are retained: 101/196 magnitude points, 51 angles, 50x75 mesh. Controls
    k/theta apply to single-point branch; custom grids apply to their scan.
    At most max_points (default 10000) points; no feedback or iteration.
    Always returns defined scan fields and last-point matrices/state. Modes are
    sorted independently at each point, not tracked. Default plots for 2/3/4
    are produced in memory using Agg; other selectors have no axes/export.
    output_count normalized 0..4 or SI 0..17 returns original-position tuple
    with formerly undefined outputs now defined; ordinary return is a dict.
    """
    state = initialize_pdrf_plasma(species, unit=unit, prior=prior, cfg=cfg)
    method = _integer(method, "method")
    limit = _integer(max_points, "max_points")
    if method < 0 or limit < 1:
        raise ValueError("method must be nonnegative and max_points positive")
    kk = tt = xx = zz = np.empty(0)
    if method == 2:
        default = np.arange(101)*.1 if unit == "normalized" else np.r_[np.arange(101)*1e-7, 2e-5+np.arange(37)*5e-6, 3e-4+np.arange(58)*1e-4]
        kk = _grid(k_grid, default, "k_grid")
        angle = np.pi/4 if unit == "normalized" else 0.
        kxs, kzs = kk*np.sin(angle), kk*np.cos(angle)
        shape = (len(kk),)
    elif method == 3:
        tt = _grid(theta_grid, np.arange(51)*np.pi/100, "theta_grid")
        kxs, kzs = 2*np.sin(tt), 2*np.cos(tt)
        kk = np.full(len(tt), 2.)
        shape = (len(tt),)
    elif method == 4:
        x = _grid(kx_grid, .01+np.arange(75)*.04, "kx_grid")
        z = _grid(kz_grid, .01+np.arange(50)*.04, "kz_grid")
        if len(x)*len(z) > limit:
            raise ValueError("scan exceeds max_points")
        xx, zz = np.meshgrid(x, z)
        kxs, kzs, shape = xx.ravel(), zz.ravel(), xx.shape
        kk = np.sqrt(xx**2+zz**2)
    else:
        kval = np.asarray(k)
        if kval.ndim != 0 or kval.dtype.kind not in "iufc" or not np.isfinite(kval):
            raise ValueError("k must be a finite complex scalar")
        angle = _scalar(theta, "theta")
        kxs, kzs = [complex(kval)*np.sin(angle)], [complex(kval)*np.cos(angle)]
        kk = np.asarray([complex(kval)])
        shape = (1,)
    if len(kxs) > limit:
        raise ValueError("scan exceeds max_points")
    w1, w2 = [], []
    for x, z in zip(kxs, kzs):
        matrix = assemble_pdrf_matrix(state, x, z, rel=rel)
        spectrum = solve_pdrf_spectrum(matrix["M"], matrix["A"], vectors=vectors,
                                        oldmethod=oldmethod, scales=matrix["scales"])
        w1.append(spectrum["w1"]); w2.append(spectrum["w2"])
    out = dict(matrix, **spectrum, method=method, unit=unit, kk=kk, tt=tt, kkx=xx, kkz=zz,
               ww1=np.asarray(w1).reshape(shape+(-1,)), ww2=np.asarray(w2).reshape(shape+(-1,)),
               points=len(kxs), execution_order="initialize; row-major assemble/spectrum; plot", max_points=limit,
               graphics={"axes_count": 0, "mode_count": 0})
    if method in (2, 3, 4):
        out["graphics"], out["plot_png"] = _plot(out, plot_path)
    elif plot_path is not None:
        raise ValueError("single-point selector has no plot; plot_path requires method 2/3/4")
    if output_count is not None:
        count = _integer(output_count, "output_count")
        maximum = 4 if unit == "normalized" else 17
        if not 0 <= count <= maximum:
            raise ValueError(f"public output_count must be 0..{maximum}")
        fields = (out["M"], out["A"], out["w1"], out["w2"], out["kk"], out["ww1"], out["ww2"],
                  state["betasz"], state["vA"], state["csz2"], state["c2"], state["rhos0"], state["wcs"],
                  state["qs"], state["ms"], state["wps"], state["B0"])
        return fields[:count]
    return out
