"""D2 derived magnetized PDRK candidate; independent qualification pending.

Species deck columns: q/e, m/mp, n[m^-3], Tparallel[eV], Tperp[eV],
alpha, Delta, parallel drift/c. Native constants and signed gyrofrequency,
first-species normalizations and truncation are kept. D2 corrects Hermitian
electric normalization, newly computed eigenpair state, stored coordinates,
causal Landau continuation for negative real parallel wavenumber, exact
perpendicular velocity moments, and precision-qualified J12/I16 Padé poles.
Frozen D0 887498b and D1 c41b remain read-only evidence. Eigenvalues and their d0 carrier are binary64; source post-eig symbolic
conversion is absorbed into a 17-digit numeric diagnostic serialization.
Each call owns a new Octave process and scratch copy. State names follow the
source; inactive undefined fields are empty arrays, never numerical zero.
Scientific numeric ports use source double/complex-double representation.
Promotion retains the caller's represented values, not lost input precision.
"""
from pathlib import Path
from types import MappingProxyType
import numpy as np
from ._transport import NativeAction, NativeTransport, NativeResult


# These are the normalized callable entry points represented by the PDRK
# catalog.  Internal helpers and legacy composition functions remain directly
# importable for compatibility but are intentionally excluded from star
# imports and discovery.
__all__ = [
    "initialize_equilibrium",
    "electromagnetic_matrix",
    "electrostatic_matrix",
    "eigensolve",
    "reconstruct_point_fields",
    "select_modes",
    "pole_coefficients",
    "loss_cone_partition",
    "render_spectrum",
    "select_preset",
    "interpolate_selected_dispersion",
    "source_output",
    "wavevector_coordinates",
    "render_selected_modes",
]

_ROOT = Path(__file__).parent / '_native'
CONTROLS = ('iem','N','J','sp','wg0','B0','ipa','ipb','iloga','ilogb',
            'pa1','pa2','dpa','pb1','pb2','dpb','iout')
SCENARIOS = ('default','beammode','coldplasma','dispersionsurface',
             'es1d_beam','es3d_losscone','loss_cone_mirror')
EQUILIBRIUM_FIELDS = tuple('c2 epsilon0 mu0 kB qs0 ms0 ns0 Tzs0 Tps0 alphas Deltas vds0 rsab Qtotal Jtotal qs ms Tzs Tps vds vtzs lambdaDs kDs wps wcs rhocs wps2 lmdT Tpsab lmdTab rhocsab betasz betasp vA cSs1 wcs1 wps1 cwp vAwp bzj czj S SNJ SNJ1 SNJ3 NN nw nw0 sp0 npa npb pa pb par ireturn strpa strpb strscan ipbtmp wg savepath'.split()) + CONTROLS
# Fields occur once; source controls wg0/sp etc also form the graph carrier.
EQUILIBRIUM_FIELDS = tuple(dict.fromkeys(EQUILIBRIUM_FIELDS))
MATRIX_COMMON = tuple('c2 epsilon0 mu0 S N J NN SNJ SNJ1 SNJ3 wps2 czj bzj vtzs vds wcs rhocsab rsab lmdTab kDs'.split())
SCAN_OUTPUTS = tuple('ww wwp kxx kzz kk tt par wg wg0 ppa ppb M d omega w wi ind d0_serialized Pola wws2 icalp k kx kz theta'.split())
EM_OUTPUTS = tuple('M k bsab bsab2 csnj b11 b12 b13 b21 b22 b23 b31 b32 b33 b11snj b12snj b13snj b21snj b22snj b23snj b31snj b32snj b33snj'.split())
ES_OUTPUTS = tuple('M k bsab bsab2 csnj bsnj'.split())

def _state(value):
    return value.state if isinstance(value, NativeResult) else value

def _real_values(value, name):
    raw=np.asarray(value)
    objects=np.asarray(value,dtype=object)
    if raw.size==0 or raw.dtype.kind not in 'iuf' or any(isinstance(x,(bool,np.bool_)) for x in objects.flat) or not np.all(np.isfinite(raw)):
        raise ValueError(name+' must contain finite real numbers')
    with np.errstate(over='ignore',invalid='ignore'):
        converted=raw.astype(np.float64,copy=False)
    if not np.all(np.isfinite(converted)):
        raise ValueError(name+' must be representable as finite native binary64 values')
    return converted

def _physical_deck(deck):
    """Magnetized nonrelativistic charged Gaussian species, in source units.

    Zero density is allowed for nonreference species; the first species fixes
    frequency/length normalization and must have positive density. Zero B/T or
    a neutral species needs a different representation, never a silent clamp.
    Alpha=1 retains the source's explicitly declared bi-Maxwellian convention.
    """
    deck=_real_values(deck,'deck')
    if deck.ndim!=2 or deck.shape[0]==0 or deck.shape[1]!=8:
        raise ValueError('deck must have one or more rows and exactly eight columns')
    if np.any(deck[:,0]==0) or np.any(deck[:,1]<=0) or np.any(deck[:,2]<0) or deck[0,2]<=0:
        raise ValueError('charged species require positive mass, nonnegative density and positive reference density')
    if np.any(deck[:,3:6]<=0) or np.any((deck[:,6]<0)|(deck[:,6]>1)) or np.any(np.abs(deck[:,7])>=1):
        raise ValueError('positive temperatures/alpha, Delta in [0,1], and subluminal drift are required')
    return deck

def _controls(controls):
    controls=dict(controls)
    unknown=set(controls)-set(CONTROLS)
    if unknown:raise ValueError('unknown controls: '+repr(sorted(unknown)))
    integer_domains={'iem':{0,1},'J':{4,8,12},'sp':{0,1},'ipa':{1,2,3,4},'ipb':{1,2,3,4},'iloga':{0,1},'ilogb':{0,1},'iout':{1,2}}
    for key,value in controls.items():
        if key=='wg0':
            raw=np.asarray(value)
            if raw.shape!=() or raw.dtype.kind not in 'iufc' or not np.isfinite(raw):raise ValueError('wg0 must be a finite complex scalar')
            with np.errstate(over='ignore',invalid='ignore'):
                represented=raw.astype(np.complex128)
            if not np.isfinite(represented):raise ValueError('wg0 must be representable as native complex binary64')
            continue
        raw=_real_values(value,key)
        if raw.shape!=():raise ValueError(key+' must be scalar')
        number=float(raw)
        if key in integer_domains and number not in integer_domains[key]:raise ValueError(key+' has an unsupported selector')
        if key=='N' and (number<0 or number!=int(number)):raise ValueError('N must be a nonnegative integer')
        if key in ('B0','dpa','dpb') and number==0:raise ValueError(key+' must be nonzero')
    if 'ipa' in controls and 'ipb' in controls and (controls['ipa'],controls['ipb']) not in {(1,1),(2,2),(3,3),(4,4),(1,2),(3,4)}:
        raise ValueError('supported scan selector pairs are (1,1),(2,2),(3,3),(4,4),(1,2),(3,4)')
    return controls

def _call(action, inputs, outputs, *, merge=None, timeout=86400):
    from scipy import sparse

    converted={}
    for key,value in inputs.items():
        array=value if sparse.issparse(value) else np.asarray(value)
        kind=array.dtype.kind;size=array.dtype.itemsize
        target=np.float64 if kind in 'biu' or (kind=='f' and size!=8) else (np.complex128 if kind=='c' and size!=16 else None)
        converted[key]=array.astype(target) if target is not None else value
    inputs=converted
    decl = NativeAction('current/'+action+'.m', tuple(outputs), tuple(inputs))
    result = NativeTransport(_ROOT, {action: decl}, timeout_seconds=timeout).invoke(action, inputs)
    if merge is None:
        return result
    joined = dict(_state(merge)); joined.update(result.state)
    return NativeResult(MappingProxyType(joined), result.receipt)

def initialize_equilibrium(deck=None, *, scenario='default', controls=None, par=None):
    """Initialize the exact source state, including source-specific pole tables.

    `controls` overrides only named source setup variables, after its setup and
    before initialization. `par` replaces the explicit six-entry source vector;
    changing k/theta never implicitly recomputes its separately stored kx/kz.
    B0 must be nonzero, temperatures/masses/alpha positive, charged species
    each species charge nonzero, and reference density positive. Unsupported
    selectors and malformed decks fail explicitly instead of returning NaNs.
    """
    if scenario not in SCENARIOS:
        raise ValueError('unknown packaged source scenario')
    controls = _controls({} if controls is None else controls)
    if deck is None:
        relative='current/code/input/pdrk.in' if scenario=='default' else 'current/fixtures/'+scenario+'/pdrk.in'
        deck=np.loadtxt(_ROOT/relative,skiprows=1,ndmin=2)
    deck=_physical_deck(deck)
    if par is not None:
        par=_real_values(par,'par')
        if par.shape not in ((6,),(6,1),(1,6)):raise ValueError('par must be a vector of six coordinate controls')
    values = np.array([controls.get(k, np.nan) for k in CONTROLS], dtype=complex)
    result=_call('initialize', {'deck':deck,
        'setup_name':scenario, 'control_values':values,
        'par_override':np.empty((0,0)) if par is None else par}, EQUILIBRIUM_FIELDS+('undefined_pole_fields',))
    if bool(np.asarray(result.state['ireturn']).item()):raise ValueError('unsupported source scan selector pair')
    return result

def _matrix(state, kx, kz, action, outputs):
    state = _state(state)
    if int(np.asarray(state['iem']).item())!=(1 if action=='em_matrix' else 0):
        raise ValueError('matrix family requires a matching initialized iem state')
    kx=_real_values(kx,'kx');kz=_real_values(kz,'kz')
    if kx.shape!=() or kz.shape!=():raise ValueError('kx and kz must be real scalars')
    if action=='es_matrix' and float(kx)==0 and float(kz)==0:
        raise ValueError('electrostatic response requires a nonzero wavevector')
    inputs = {k:state[k] for k in MATRIX_COMMON}; inputs.update(kx=kx,kz=kz,undefined_pole_fields=state.get('undefined_pole_fields','[]'))
    return _call(action, inputs, outputs, merge=state)

def electromagnetic_matrix(state, *, kx, kz):
    """EM eigenmatrix at SI kx,kz [m^-1], preserving source signed gyro terms."""
    return _matrix(state,kx,kz,'em_matrix',EM_OUTPUTS)

def electrostatic_matrix(state, *, kx, kz):
    """ES matrix, including parallel ES1D, at SI kx,kz [m^-1]."""
    return _matrix(state,kx,kz,'es_matrix',ES_OUTPUTS)

def scan_spectrum(state, *, rng_seed=None):
    """Source ordered scan -> dimensional omega spectrum and final guess state.

    The finite npa*npb schedule updates par, chooses EM/ES assembly, solves and
    sorts by descending imaginary omega, carries wg along a row, saves its first
    point as wg0 and restores that guess for the next row. Dense/sparse behavior
    and all six supported coordinate selectors are unchanged.
    """
    state=_state(state)
    inputs={k:state[k] for k in EQUILIBRIUM_FIELDS}
    inputs['undefined_pole_fields']=state.get('undefined_pole_fields','[]')
    if rng_seed is not None:inputs['rng_seed']=rng_seed
    return _call('scan',inputs,SCAN_OUTPUTS,merge=state)

def eigensolve(state, *, matrix=None, guess=None):
    """Point frequency eigensolve and growth ordering (icalp=0).

    Dense binary64 eig; sparse binary64 eigs near dimensional guess. The d0
    string is a numeric diagnostic, with no arbitrary-precision claim.
    """
    state=_state(state)
    inputs={k:state[k] for k in ('NN','iem','iout','sp','nw','wcs1','epsilon0','mu0')}
    inputs.update(M=state['M'] if matrix is None else matrix,
                  wg=state['wg'] if guess is None else guess,icalp=0)
    return _call('eigensolve',inputs,('d','omega','w','wi','ind','wg','d0_serialized','Pola','wws2'),merge=state)

def reconstruct_point_fields(state, *, frequency_guess):
    """One near-mode EM eigenpair with unit-Hermitian electric normalization.

    frequency_guess is dimensional rad/s. The shared native point kernel uses
    shift=frequency_guess+1e-8j rad/s, returns its newly computed V/D/frequency
    and fields Ex,Ey,Ez,Bx,By,Bz, with SI electric/magnetic energies. Its largest
    represented electric component is real nonnegative, first exact tie wins.
    This is the same point branch used by the finite polarization graph; it
    requests one sparse binary64 eigenpair and makes no uniqueness/accuracy
    promise beyond the separately checked residual. Zero electric modes fail.
    """
    st=_state(state)
    if int(np.asarray(st['iem']).item())!=1:
        raise ValueError('EM initialized matrix state required')
    raw=np.asarray(frequency_guess)
    if raw.shape!=() or raw.dtype.kind not in 'iufc' or not np.isfinite(raw):
        raise ValueError('finite complex scalar frequency_guess required')
    guess=complex(raw)
    if not np.isfinite(guess):raise ValueError('frequency_guess must be representable as complex128')
    inputs={k:st[k] for k in ('M','NN','wcs1','epsilon0','mu0')}
    inputs.update(iem=1,iout=2,sp=1,nw=1,icalp=1,jpa=1,jpb=1,jpl=1,
                  wg=guess,wws=np.array([[[guess/float(np.asarray(st['wcs1']).item())]]]))
    return _call('eigensolve',inputs,('V','D','dEB','UE','UB','d','w','wi','omega','wg','Pola','wws2','d0_serialized'),merge=st)


def select_modes(state, seeds):
    """Select normalized frequencies omega/wcs1 using source seed/PCHIP order.

    Seeds are rows (pa,pb,Re-or-Im omega/wcs1). Exactly zero real seed chooses
    the imaginary discriminator. Ties choose the source's first index.
    """
    state=_state(state)
    inputs={k:state[k] for k in ('npa','npb','ipa','ipb','pa','pb')}
    inputs.update(ww=state['ww'],wcs1=state['wcs1'],wpdat=seeds)
    return _call('select',inputs,('wws','npl','pas','wwn','wpdat'),merge=state)

def reconstruct_polarization(state, *, rng_seed=None):
    """EM near-mode fields with unit Hermitian E norm and a stable phase pivot.

    Consumes selected normalized wws. Returns Pola[...,0:6]=Ex,Ey,Ez,Bx,By,Bz,
    Pola[...,6:8]=electric/magnetic energy. The largest electric component is
    real nonnegative (first wins an exact tie); B gets the same scale/phase.
    Zero electric modes cannot use this convention and fail explicitly.
    Requires electromagnetic mode and iout=2; this is not an ES field solver.
    """
    state=_state(state)
    if int(np.asarray(state['iem']).item())!=1 or int(np.asarray(state['iout']).item())!=2:
        raise ValueError('electromagnetic polarization requires iem=1 and iout=2')
    inputs=dict(state)
    for k in ('figure_png','figure_native'):inputs.pop(k,None)
    inputs.update(wws=state['wws'],npl=state['npl'],d=state['d'])
    if rng_seed is not None:inputs['rng_seed']=rng_seed
    return _call('polarization',inputs,('Pola','wws2','sp','nw','icalp','par','wg','wg0','wwp','M','ppa','ppb','kxx','kzz','kk','tt','d','omega','w','wi','ind','V','D','dEB','UE','UB','d0_serialized'),merge=state)


def _normalize_electromagnetic_fields(E, B, epsilon0, mu0):
    """Private test adapter to the exact native normalizer used by the kernel."""
    E=np.asarray(E);B=np.asarray(B)
    if E.size!=3 or B.size!=3:
        raise ValueError('E and B must each contain three components')
    return _call('normalize_fields',{'fields':np.concatenate((E.reshape(-1),B.reshape(-1))),
        'epsilon0':epsilon0,'mu0':mu0},('normalized_fields','UE','UB'))


def pole_coefficients(J=8):
    """Exact current-source J=4/8/12 rational Z tables, ordered bzj/czj."""
    value=_real_values(J,'J')
    if value.shape!=() or float(value) not in (4,8,12):raise ValueError('J must be 4, 8 or 12')
    return _call('poles', {'J':J}, ('bzj','czj'))


def loss_cone_partition(alphas, Deltas):
    """Source two-branch core/loss-cone weights; alpha==1 bypass preserved."""
    alphas=_real_values(alphas,'alphas');Deltas=_real_values(Deltas,'Deltas')
    if alphas.shape!=Deltas.shape or np.any(alphas<=0) or np.any((Deltas<0)|(Deltas>1)):
        raise ValueError('alpha and Delta must share shape, alpha>0 and Delta in [0,1]')
    return _call('partition', {'alphas':alphas,'Deltas':Deltas}, ('rsab',))


def render_spectrum(state, *, runtime=0.):
    """Source all-root plotting terminal; PNG/native FIG bytes are artifacts."""
    st=dict(_state(state));st['runtime']=runtime
    needed=tuple(dict.fromkeys(EQUILIBRIUM_FIELDS+('ww','kk','kxx','kzz','ppa','ppb','runtime')))
    return _call('render_all',{k:st[k] for k in needed},
        ('wwn','kkn','kxxn','kzzn','figstr','figure_png','figure_native'),merge=st)


def select_preset(state, *, scenario='default', runtime=0.):
    """Run stored wpdat, including rescaling and ES1D example interpolation.

    Source order requires render_spectrum state (wwn,figstr). Scientific modes
    and native artifacts are retained; source plot failures remain exceptions.
    """
    if scenario not in SCENARIOS: raise ValueError('unknown source scenario')
    st=dict(_state(state));st.update(runtime=runtime,setup_name=scenario)
    # Native output byte arrays from the prior rendering are not source state.
    for k in ('figure_png','figure_native'):st.pop(k,None)
    return _call('select_preset',st,('wws','npl','wpdat','rex','rey','rez','pas',
        'kinterp','winterp','pltc','figstr','figure_png','figure_native'),merge=st)


def interpolate_selected_dispersion(state, *, coordinate=.2, rex=None, rez=None):
    """Exact ES1D example interp1 mapping; source out-of-range NaN preserved."""
    st=_state(state)
    return _call('interpolate',{'pas':st['pas'],'wws':st['wws'],
        'rex':st['rex'] if rex is None else rex,'rez':st['rez'] if rez is None else rez,
        'kinterp':coordinate},('winterp',))


class SourceOutputError(RuntimeError):
    """Original output stage failed; result retains partial source artifacts/state."""
    def __init__(self, result):
        self.result=result
        self.receipt=result.receipt
        super().__init__('source output failed: '+str(result.state['output_error']))


def source_output(state, *, runtime=0., rng_seed=None):
    """Original polarization/plot/workspace writer terminal; failures retain partial results."""
    st=dict(_state(state));st['runtime']=runtime
    for k in ('figure_png','figure_native'):st.pop(k,None)
    if rng_seed is not None:st['rng_seed']=rng_seed
    result=_call('output',st,('output_completed','output_error','output_error_identifier','Pola','wws2','figure_png','figure_native','workspace_mat','par','wg','wg0','wwp','M','ppa','ppb','kxx','kzz','kk','tt','d','omega','w','wi','ind','sp','nw','icalp','V','D','dEB','UE','UB','d0_serialized'),merge=st)
    if not bool(result.state['output_completed'].item()):raise SourceOutputError(result)
    return result


def solve_dispersion(deck=None, *, scenario='default', controls=None, par=None):
    """Noninteractive scientific graph with the main source early-return gate."""
    eq=initialize_equilibrium(deck,scenario=scenario,controls=controls,par=par)
    if bool(eq.state['ireturn'][0,0]):return eq
    return scan_spectrum(eq)


def original_program(*, scenario='default', timeout=86400, rng_seed=None):
    """Full source reassembly, alongside the reusable mappings above.

    Both interactive continuation prompts receive an empty response. Raw native
    MAT/PNG/FIG bytes are captured from the original writer. `program_completed`
    and `program_error` expose the source semantic terminal separately from the
    transport exit status; a caught source failure is never application success.
    The source's clear resets native wrapper state before scientific execution.
    An optional seed sets rand/randn once before the untouched main program;
    None retains its uncontrolled startup state.
    """
    if scenario not in SCENARIOS: raise ValueError('unknown source scenario')
    outputs=('program_completed','program_error','mat_bytes','all_png','select_png',
        'pola_png','all_fig','select_fig','pola_fig','native_defined_ports')+tuple('ww wws wws2 Pola par wg wg0 kk kxx kzz tt wwp M d cwp wcs1 vtzs qs ms Tzs Tps wps2 rsab lmdTab rhocsab kDs bzj czj S NN npa npb nw nw0 sp sp0 icalp iout iem ipa ipb pa pb wpdat rex rey rez figstr k kx kz theta epsilon0 mu0 c2'.split())
    inputs={'setup_name':scenario}
    if rng_seed is not None:inputs['rng_seed']=rng_seed
    decl=NativeAction('current/program.m',outputs,tuple(inputs),stdin='\n\n')
    return NativeTransport(_ROOT,{'program':decl},timeout_seconds=timeout).invoke('program',inputs)


def wavevector_coordinates(state, *, row=1, column=1):
    """Literal source coordinate update for one1-based scan index pair.

    Preserves abs(k), log selection, direct kx/kz selector complement, atan phase
    convention and updated par. This is the same block owned by native kernel.
    """
    st=_state(state);ports={k:st[k] for k in ('iloga','ilogb','ipa','ipb','pa','pb','par','cwp')}
    ports.update(jpa=row,jpb=column)
    return _call('coordinates',ports,('par','kx','kz','k','theta'),merge=st)


def render_selected_modes(state, *, scales=(1.,1.,1.), runtime=0.):
    """Source selected-mode presentation, without repeating mode selection.

    Produces plot environment (pltc,figstr,rescaling) consumed by source_output.
    It preserves scientific wws and does not claim visual inspection acceptance.
    """
    st=dict(_state(state));st.update(rex=scales[0],rey=scales[1],rez=scales[2],runtime=runtime)
    for k in ('figure_png','figure_native'):st.pop(k,None)
    if 'figstr' not in st:
        st['figstr']='S=%d_J=%d_N=%d_npa=%d_npb=%d'%tuple(int(np.asarray(st[k]).item()) for k in ('S','J','N','npa','npb'))
    return _call('render_select',st,('pltc','figstr','rex','rey','rez','figure_png','figure_native'),merge=st)
