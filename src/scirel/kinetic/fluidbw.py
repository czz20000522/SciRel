"""Corrected full retained fluidBW family, executed by packaged Octave components.

Lineage: upstream 79829170 -> D0 7fd667f4 -> D1 1a6704a7 -> this D2.
The native directory is runtime implementation, never an external checkout.
Historical Python source-fidelity variants have different approximation, domain,
state and failure contracts; they are comparison inputs, not dependencies here.
Source redistribution and WHAMP/Faddeeva permission remain NOT_ESTABLISHED.
This private technical increment grants neither scientific human approval nor release.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

__all__ = ["evaluate_fluidbw_special", "derive_fluidbw_case", "evaluate_fluidbw_dispersion",
           "solve_fluidbw_bonk", "assemble_fluidbw_em", "solve_fluidbw_em",
           "render_fluidbw_materials"]


def _decode(value):
    if hasattr(value, "_fieldnames"):
        return {name: _decode(getattr(value, name)) for name in value._fieldnames}
    if isinstance(value, np.ndarray) and value.dtype == object:
        decoded = [_decode(item) for item in value.flat]
        if value.size == 1:
            return decoded[0]
        # np.asarray expands equal-shaped nested arrays even with dtype=object.
        # Allocate the MAT cell shape explicitly so each cell retains its array.
        cells = np.empty(value.shape, dtype=object)
        for index, item in enumerate(decoded):
            cells.flat[index] = item
        return cells
    if isinstance(value, np.ndarray) and value.dtype.kind in "US":
        return "".join(value.flat)
    return value


def _run(function, args, *, nout=1, output_directory=None):
    """One process owns all native globals and figures; arguments travel as MAT data."""
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise RuntimeError("fluidBW requires the pinned Linux amd64 runtime")
    octave = shutil.which("octave")
    if octave is None:
        raise RuntimeError("GNU Octave 7.3.0 is required")
    # MAT transport is only needed once a native Octave call is requested.
    # Keeping this import here lets direct module discovery avoid scipy.io and
    # preserves the existing load/save behavior inside the native boundary.
    from scipy.io import loadmat, savemat

    environment = os.environ.copy()
    environment.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    native = Path(__file__).with_name("_fluidbw_native").resolve()
    with tempfile.TemporaryDirectory(prefix="scirel-fluidbw-") as temporary:
        root = Path(temporary)
        cells = np.empty((1, len(args)), dtype=object)
        def encode(argument):
            if isinstance(argument, dict):
                return {key: encode(value) for key, value in argument.items()}
            array = np.asarray(argument)
            if array.dtype.kind in "iu":
                if np.any(np.abs(array.astype(object)) > 2**53):
                    raise ValueError("integer input exceeds exact double representation")
                return array.astype(np.float64)
            return argument
        for index, argument in enumerate(args):
            cells[0, index] = encode(argument)
        savemat(root / "input.mat", {"args": cells}, oned_as="row", long_field_names=True)
        quote = lambda path: str(path).replace("'", "''")
        script = root / "driver.m"
        script.write_text(
            f"addpath('{quote(native)}');\n"
            "if ~strcmp(OCTAVE_VERSION,'7.3.0'), error('fluidbw:runtime','Octave 7.3.0 required'); end\n"
            f"load('{quote(root / 'input.mat')}'); values=cell(1,{nout});\n"
            f"try; [values{{:}}]=feval('{function}',args{{:}}); ok=true; error_id=''; error_message='';\n"
            "catch err; ok=false; error_id=err.identifier; error_message=err.message; end;\n"
            f"save('-mat7-binary','{quote(root / 'output.mat')}','ok','values','error_id','error_message');\n",
            encoding="utf-8",
        )
        work = root if output_directory is None else Path(output_directory).resolve(strict=True)
        process = subprocess.run([octave, "--no-gui", "--quiet", str(script)], cwd=work,
                                 env=environment, capture_output=True, timeout=1800, check=False)
        if process.returncode or not (root / "output.mat").exists():
            raise RuntimeError(f"fluidBW runtime failed: {process.stderr.decode(errors='replace')[-2000:]}")
        result = loadmat(root / "output.mat", struct_as_record=False, squeeze_me=False)
        if not result["ok"].item():
            raise ValueError(f"{_decode(result['error_id'])}: {_decode(result['error_message'])}")
        values = [_decode(item) for item in result["values"].flat]
        return values[0] if nout == 1 else values


def evaluate_fluidbw_special(method, x, parameter=None):
    """Evaluate Gamma/Gamma' (order x, argument parameter), Z(x), or full R response.

    Methods are Gamman, Gammapn, zfun, RTAY, RASY, RINT, RYLA. All arguments
    are dimensionless. Gamma inputs broadcast by Octave elementwise rules; Z
    preserves array shape. R takes finite scalar Y=x, b=parameter and returns
    RC=[R, d(bR)/db; Y*dR/dY, Y*d/dY(d(bR)/db)]. Four historical algorithm
    requests now use the same corrected harmonic evaluator; no historical
    Taylor/asymptotic/quadrature execution is claimed. Genuine poles, overflow
    and cancellation beyond 1e-10*(1+|RC|) fail explicitly. b=0 and Y=0 use
    analytic limits. Full complex b is attempted with a bounded tail and
    roundoff check, at most 65536 terms; this is not arbitrary-precision science.
    """
    if method not in {"Gamman", "Gammapn", "zfun", "RTAY", "RASY", "RINT", "RYLA"}:
        raise ValueError("unknown special-function method")
    return _run("fb_special", [method, x] if parameter is None else [method, x, parameter])


def derive_fluidbw_case(family, jcase=None):
    """Return complete source-defined SI species/normalization state.

    family='bonk' supports jcase 1(default),2,3; 'em' supports 1,2(default).
    Source constants and eV conversion 1.6022e-19 J/eV are retained. Thermal
    speed sqrt(2 kB T/m), signed rho=sqrt(kB T/m)/Omega; wn=min|Omega|,
    kn=1/max|rho|. EM forces kz=0.1kn. These are listed-species response
    states; electron-only case2 does not establish global charge neutrality or
    a self-consistent background equilibrium. Unknown cases fail, never guess a model.
    """
    if family not in {"bonk", "em"}:
        raise ValueError("family must be bonk or em")
    return _run(f"fb_{family}_parameters", [] if jcase is None else [jcase])


def evaluate_fluidbw_dispersion(kx, state, method="fDR"):
    """Return determinant, K, Maxwell D and unmodified explicit SI state.

    state requires S,c2[m²/s²],wcs[rad/s],wps2[s^-2],rhocs[m],w[rad/s],
    kz[m^-1],vts[m/s]. kx is finite real/complex m^-1. Static isotropic
    Maxwellians, B along z, exp(i k.x-i wt), K=I-sigma/(i w epsilon0).
    fD/fDtensor use corrected stable symmetric cutoffs 5/15; fDR uses J8
    poles with corrected full harmonic R. No exact kinetic equivalence of
    those approximations is claimed. Real nonzero w and nonzero gyrofrequency,
    positive thermal/plasma scales and rho=vthermal/(sqrt(2)*Omega) required. Signed/zero kz and kx=0 are
    included via parity/analytic limits; true zero-kz harmonic poles fail.
    State is process-owned; success and failure cannot mutate caller globals.
    """
    if method not in {"fD", "fDR", "fDtensor"}:
        raise ValueError("method must be fD, fDR or fDtensor")
    return _run("fb_evaluate", [kx, state, method])


def solve_fluidbw_bonk(jcase=1, omegas=None):
    """Compose source cases -> fixed-seed fsolve sweep -> residual/status.

    omegas is a nonempty real nonzero rad/s vector; default (0.11:.05:3.95)*wn.
    Each row tries q=kx/kn seeds [0.6,0.6+0.1i,0.6-0.1i,1,2] in order,
    stopping at the first verified root. Real/imaginary residuals use a fixed
    per-attempt determinant scale. TolFun/TolX=1e-16 are retained; each attempt
    is bounded by MaxIter=400, MaxFunEvals=100. nf contains candidates; root_valid
    requires sigma_min(D)/max(1,sigma_max(D)) AND row-norm determinant residual
    <=1e-8. Raw solver termination and every attempt remain observable; a
    verified root may survive an overstrict solver stagnation flag. No branch
    continuation or complete physical-mode claim. Unsolved rows are explicit.
    """
    return _run("fb_bonk", [jcase] if omegas is None else [jcase, omegas, False])


def assemble_fluidbw_em(state, omega, j_order=8, max_harmonic=6):
    """Return the full finite L/J rational kx matrix and exact source pole tables.

    omega[rad/s] is real nonzero. state is derive_fluidbw_case('em') state.
    j_order is 8/12, max_harmonic N is integer 0..7 (all eight source tables).
    M maps mixed SI state X=[Jx_snl,Jy_snl,Jz_snl,Ey,Ez,By,Bz] via kx X=M X.
    Raw source pole tables are returned separately as cn_raw. Corrected n>=1
    residues are projected onto zero inverse moments, preserving conjugate pairs
    and the two leading large-z moments. All components use the same corrected
    Gamma, evaluated stably as z² sum_l (rl/pl²)/(z-pl) for n>=1; Gamma0 uses
    the raw sum_l rl/(z-pl). z=kx*abs(rho). This finite fit is an approximation
    on the positive-real kx side, not an identity for all complex kx. Invalid
    table controls or singular rational denominators fail explicitly. A
    finite rational model is returned; full Maxwellian accuracy is separate.
    """
    return _run("fb_assemble", [state, omega, j_order, max_harmonic])


def solve_fluidbw_em(jcase=2, j_order=8, max_harmonic=6, omegas=None):
    """Compose source EM state/tables -> M -> complete finite spectra and five candidates.

    Default omega axis (.05:.05:3.95)*wn[rad/s]. All eig values d and their
    original order are retained; Re(kx)>1e-5kn then ascending |Im(kx)| selects
    five heuristic candidates. Fewer than five raises ValueError. A separate
    eigenvector calculation reports componentwise errors and applies a physical
    state-scaled normwise backward-error gate <=2e-12; it never reorders/replaces d.
    E0=1 V/m, J0=epsilon0*abs(omega)*E0, B0=E0/c, k0=kn. The full finite
    matrix spectrum is accounted for; physical mode completeness, exact
    kinetic roots and cross-thread invariance are NOT established. GNU Octave
    7.3.0 Linux amd64, OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1 is required.
    """
    args = [jcase, j_order, max_harmonic]
    if omegas is not None:
        args += [omegas, False]
    return _run("fb_em", args)


def render_fluidbw_materials(result, family, output_directory, jplt=2):
    """Render source plot/material branches from a complete returned graph state.

    Explicit existing writable directory owns PNG/MAT files. family='bonk'
    retains case1/2/3 graphics; 'em' retains jplt1/2 and ICW/ECW MAT outputs.
    Wavenumbers are m^-1 or explicitly normalized by kn, frequencies rad/s
    or normalized by wn. Only display/serialization: no visual/physical truth
    claim. Plot clipping and backend warnings remain possible; figures are
    process-local. Paths of produced files are returned. No caller figures close.
    """
    if family not in {"bonk", "em"} or jplt not in (1, 2):
        raise ValueError("family must be bonk/em and jplt must be 1/2")
    directory = Path(output_directory).resolve(strict=True)
    written = _run("fb_materials", [result, family, jplt], output_directory=directory)
    return {"files": sorted(str(name) for name in np.atleast_1d(written["files"]).flat)}
