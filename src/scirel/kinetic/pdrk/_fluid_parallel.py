"""SI multifluid and circular parallel Maxwellian dispersion implementation.

Lineage: PDRK frozen D0 887498b2 examples/beammode and coldplasma. This
successor changes scientific/numerical contracts explicitly; it does
not rewrite D1. Governing definitions and unresolved permission are recorded in
the associated development provenance. Human endorsement and public
redistribution are pending.
"""
import numpy as np

# Kept as a patch point for the continuation contract tests.  The concrete
# SciPy solver is still resolved only when this compatibility wrapper is used.
def root(*args, **kwargs):
    from scipy.optimize import root as _root
    return _root(*args, **kwargs)


def canonical_faddeeva(z):
    """Absorption proposal: maintained SciRel relation, no independent reimplementation.

    N16/N64 approximation controls are method variants, not aliases of this
    accurate full-function contract. Preserve the caller's exact array shape.
    """
    from scirel.kinetic.plasma_dispersion import evaluate_plasma_dispersion
    return evaluate_plasma_dispersion(z)


def collision_velocity_generator(rho, exchange, bath_drag=None):
    """Nonrelativistic momentum exchange; no electron/ion mass heuristic.

    rho [kg/m^3] positive; exchange K [kg/(m^3 s)] symmetric, nonnegative,
    zero diagonal. Force on j is sum_i K[j,i]*(v_i-v_j). Positive bath_drag
    [1/s] describes external stationary-bath momentum loss explicitly.
    This is NOT an adapter for the ambiguous five source nu constants.
    """
    rho=np.asarray(rho,dtype=float);K=np.asarray(exchange,dtype=float)
    if rho.ndim!=1 or not rho.size or not np.isfinite(rho).all() or np.any(rho<=0):
        raise ValueError('rho must be a positive finite species vector')
    if K.shape!=(rho.size,rho.size) or not np.isfinite(K).all() or np.any(K<0):
        raise ValueError('exchange must be a finite nonnegative species matrix')
    if not np.array_equal(K,K.T) or np.any(np.diag(K)!=0):
        raise ValueError('exchange must be symmetric with zero diagonal')
    drag=np.zeros_like(rho) if bath_drag is None else np.asarray(bath_drag,dtype=float)
    if drag.shape!=rho.shape or not np.isfinite(drag).all() or np.any(drag<0):
        raise ValueError('bath_drag must be a finite nonnegative species vector')
    L=K/rho[:,None]
    L[np.diag_indices(rho.size)]=-L.sum(axis=1)-drag
    return L


def fluid_equilibrium_si(deck=None, *, B0=100e-9, gamma=5/3, exchange=None, bath_drag=None, pressure_frame='field_following'):
    """Explicit ten-column SI state, source constants retained as a named convention.

    q,m,n,vx,vy,vz,cs_parallel,cs_perp,epsnx,epsny. cs are nonnegative
    speeds, pressure is rho*cs^2/gamma. B0 is signed along z.
    At genuine B0=0: Alfvén species scales are zero; beta is undefined
    (None, not an invented finite zero); only isotropic pressure has a unique
    zero-field limit of the specified gyrotropic B/|B| closure. A separate
    explicit fixed_z closure freezes the pressure axes and supports anisotropic
    zero-B data without pretending that the field-following limit exists.
    """
    if deck is None:
        from ._example_support import fluid_deck
        deck=fluid_deck()
    x=np.asarray(deck,dtype=float)
    if x.ndim!=2 or x.shape[1]!=10 or not x.shape[0] or not np.isfinite(x).all():
        raise ValueError('deck must be a nonempty finite Sx10 SI array')
    q,m,n,vx,vy,vz,cz,cp,ex,ey=x.T
    if np.any(m<=0) or np.any(n<=0) or np.any(cz<0) or np.any(cp<0):
        raise ValueError('mass/density must be positive and sound speeds nonnegative')
    B=float(B0);g=np.broadcast_to(np.asarray(gamma,dtype=float),(len(m),)).copy()
    if not np.isfinite(B) or not np.isfinite(g).all() or np.any(g<=0):
        raise ValueError('B0 finite and gamma positive finite required')
    c2=2.9979e8**2;eps0=8.854e-12;mu0=1/(c2*eps0)
    rho=m*n;Pz=rho*cz**2/g;Pp=rho*cp**2/g
    if pressure_frame not in ('field_following','fixed_z'):
        raise ValueError('explicit field_following or fixed_z pressure frame required')
    if B==0 and pressure_frame=='field_following' and not np.array_equal(Pz,Pp):
        raise ValueError('gyrotropic anisotropy has no specified zero-B direction/closure limit')
    # fixed_z is a different, explicit pressure-tensor closure, not a repair by zero-fill.
    delta=np.zeros_like(Pz) if B==0 or pressure_frame=='fixed_z' else (Pz-Pp)/B
    K=np.zeros((len(m),len(m))) if exchange is None else exchange
    return dict(q=q,m=m,n=n,v=np.column_stack((vx,vy,vz)),csz2=cz**2,csp2=cp**2,
        epsnx=ex,epsny=ey,rho=rho,B0=B,gamma=g,c2=c2,epsilon0=eps0,mu0=mu0,
        Pz=Pz,Pp=Pp,Delta=delta,pressure_frame=pressure_frame,beta_z=None if B==0 else 2*mu0*Pz/B**2,
        beta_p=None if B==0 else 2*mu0*Pp/B**2,vA_species=B/np.sqrt(mu0*rho),
        velocity_collision=collision_velocity_generator(rho,K,bath_drag),
        charge_density=np.sum(q*n),current_density=np.sum((q*n)[:,None]*np.column_stack((vx,vy,vz)),axis=0))


def fluid_frequency_pencil(state,kx,kz,*,relativistic=False):
    """PRIVATE derived omega pencil lambda A X=M X, lambda=-i omega.

    X=(dn_j,dvx_j,dvy_j,dvz_j,Ex,Ey,Ez,Bx,By,Bz), 4S+6. Isotropic/cold
    nonzero/zero-B and relativistic inertia are retained. Weak x/y density
    gradients are the source local-WKB model, not a global equilibrium proof.
    Gyrotropic pressure is Pperp I+(Ppar-Pperp)bb: z-force's Bx coefficient
    has factor ONE from its divergence. D0 factor TWO is a separately recorded
    contradiction, requiring independent tensor-perturbation validation.
    Collision model is explicit nonrelativistic friction; full relativistic
    collision four-force is not inferred from the source's ignored correction.
    """
    kx=complex(np.asarray(kx).item());kz=complex(np.asarray(kz).item())
    if not np.isfinite([kx,kz]).all():raise ValueError('kx/kz must be finite in 1/m')
    q,m,n=state['q'],state['m'],state['n'];s=len(q);f=4*s
    M=np.zeros((f+6,f+6),complex);A=np.eye(f+6,dtype=complex)
    L=state['velocity_collision']
    if relativistic and np.any(L):
        raise ValueError('nonrelativistic collision closure cannot claim relativistic four-force')
    for j in range(s):
        r=4*j;v=state['v'][j];adv=kx*v[0]+kz*v[2];inertia=np.eye(3)
        if relativistic:
            speed2=v@v
            if speed2>=state['c2']:raise ValueError('relativistic speed must be strictly below c')
            gamma=1/np.sqrt(1-speed2/state['c2'])
            inertia=gamma*np.eye(3)+gamma**3*np.outer(v,v)/state['c2']
        A[r+1:r+4,r+1:r+4]=inertia
        M[r,r]=-1j*adv
        M[r,r+1]=-n[j]*(1j*kx+state['epsnx'][j]);M[r,r+2]=-n[j]*state['epsny'][j];M[r,r+3]=-1j*kz*n[j]
        M[r+1:r+4,r+1:r+4]=-1j*adv*inertia
        M[r+1,r]=-1j*kx*state['csp2'][j]/n[j];M[r+3,r]=-1j*kz*state['csz2'][j]/n[j]
        wc=q[j]*state['B0']/m[j];M[r+1,r+2]+=wc;M[r+2,r+1]-=wc
        M[r+1:r+4,f:f+3]=np.eye(3)*q[j]/m[j]
        cross_v=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
        M[r+1:r+4,f+3:f+6]=q[j]/m[j]*cross_v
        D=state['Delta'][j]/state['rho'][j]
        M[r+1,f+3]+=-1j*kz*D;M[r+2,f+4]+=-1j*kz*D;M[r+3,f+3]+=-1j*kx*D
        M[f:f+3,r]=-q[j]*v/state['epsilon0'];M[f:f+3,r+1:r+4]=-np.eye(3)*q[j]*n[j]/state['epsilon0']
    for j in range(s):
        for i in range(s):M[4*j+1:4*j+4,4*i+1:4*i+4]+=L[j,i]*np.eye(3)
    cross_k=np.array([[0,-kz,0],[kz,0,-kx],[0,kx,0]])
    M[f:f+3,f+3:f+6]=1j*state['c2']*cross_k
    M[f+3:f+6,f:f+3]=-1j*cross_k
    return {'M':M,'A':A,'wcs':q*state['B0']/m,'wps':np.sqrt(n*q*q/(state['epsilon0']*m))}


def _positive_finite_tolerance(value, name):
    """Require a real scalar bound before and after binary64 narrowing."""
    raw = np.asarray(value)
    if raw.shape != () or raw.dtype.kind not in 'iuf' or not np.isfinite(raw) or raw <= 0:
        raise ValueError(name + ' must be a finite positive real scalar')
    narrowed = float(raw)
    if not np.isfinite(narrowed) or narrowed <= 0:
        raise ValueError(name + ' must be representable as a finite positive binary64 scalar')
    return narrowed


def solve_frequency_pencil(M,A,*,state_scales=None,backward_tolerance=1e-10):
    """Numerical correction: generalized QZ eigenproblem, same path for values/vectors.

    Explicit positive state_scales implements simultaneous D^-1 M D and D^-1 A D;
    returns eigenvectors in caller's original state units. No symbolic-eig path,
    no promise of 16 digits from double inputs, no hidden matrix inverse.
    Residual qualification is backward error only, not a forward accuracy proof
    for ill-conditioned or repeated modes. Acceptance also needs independent gates.
    """
    backward_tolerance = _positive_finite_tolerance(backward_tolerance, 'backward_tolerance')
    M=np.asarray(M,dtype=complex);A=np.asarray(A,dtype=complex)
    if M.ndim!=2 or M.shape[0]!=M.shape[1] or A.shape!=M.shape or not M.size or not np.isfinite(M).all()or not np.isfinite(A).all():
        raise ValueError('M/A must be finite nonempty square pencils of equal shape')
    d=np.ones(M.shape[0])if state_scales is None else np.asarray(state_scales,dtype=float)
    if d.shape!=(M.shape[0],)or not np.isfinite(d).all()or np.any(d<=0):raise ValueError('state_scales positive finite required')
    from scipy.linalg import eig, lstsq

    Ms=M*d[None,:]/d[:,None];As=A*d[None,:]/d[:,None]
    # Exact sparsity components prevent arbitrary mixing of degenerate modes
    # between mathematically uncoupled invariant subspaces. Only literal zeros
    # define components; no numerical drop tolerance is used.
    support=(Ms!=0)|(As!=0);support=support|support.T
    unseen=set(range(len(M)));components=[]
    while unseen:
        todo=[min(unseen)];component=[]
        while todo:
            i=todo.pop()
            if i not in unseen:continue
            unseen.remove(i);component.append(i)
            todo.extend(j for j in np.flatnonzero(support[i])if j in unseen)
        components.append(sorted(component))
    vals=np.empty(len(M),complex);U=np.zeros_like(M);offset=0
    for component in components:
        ix=np.array(component);values,vectors=eig(Ms[np.ix_(ix,ix)],As[np.ix_(ix,ix)])
        vals[offset:offset+len(ix)]=values;U[np.ix_(ix,np.arange(offset,offset+len(ix)))]=vectors;offset+=len(ix)
    refinement=[]
    # Gaussian rationals preserve the exact stored binary matrix. Rank powers
    # certify algebraic zero multiplicity, including defective cold neutral
    # sectors. Ordinary zero eigenvectors may repeat; no complete eigenbasis is
    # claimed where geometric multiplicity is smaller than algebraic multiplicity.
    from fractions import Fraction as F
    class Q:
        def __init__(self,r=0,i=0):self.r=F(r);self.i=F(i)
        def __add__(a,b):
            if not isinstance(b,Q):b=Q(b)
            return Q(a.r+b.r,a.i+b.i)
        __radd__=__add__
        def __neg__(a):return Q(-a.r,-a.i)
        def __sub__(a,b):return a+-b
        def __mul__(a,b):
            if not isinstance(b,Q):b=Q(b)
            return Q(a.r*b.r-a.i*b.i,a.r*b.i+a.i*b.r)
        __rmul__=__mul__
        def __truediv__(a,b):
            z=b.r*b.r+b.i*b.i
            return Q((a.r*b.r+a.i*b.i)/z,(a.i*b.r-a.r*b.i)/z)
        def __bool__(a):return bool(a.r or a.i)
        def __complex__(a):return complex(float(a.r),float(a.i))
    def rational(B):return [[Q(float(z.real),float(z.imag))for z in row]for row in B]
    def rref(B,pivot_columns):
        rows=[row[:]for row in B];piv=[];r=0
        for col in range(pivot_columns):
            found=next((i for i in range(r,len(rows))if rows[i][col]),None)
            if found is None:continue
            rows[r],rows[found]=rows[found],rows[r];v=rows[r][col];rows[r]=[x/v for x in rows[r]]
            for i in range(len(rows)):
                if i!=r and rows[i][col]:
                    a=rows[i][col];rows[i]=[x-a*y for x,y in zip(rows[i],rows[r])]
            piv.append(col);r+=1
        return rows,piv
    zero_blocks=[];offset=0
    # Bind exact zero reconstruction to each literal invariant subspace. QZ
    # nearzero order from another block cannot determine this block's zeros.
    for component in components:
        ix=np.array(component);n=len(ix);Rm=rational(M[np.ix_(ix,ix)]);Ra=rational(A[np.ix_(ix,ix)])
        rr,piv=rref(Rm,n);kernel=[]
        for col in range(n):
            if col in piv:continue
            v=[Q()for _ in range(n)];v[col]=Q(1)
            for i,pivot in enumerate(piv):v[pivot]=-rr[i][col]
            kernel.append(np.array([complex(x)for x in v])/d[ix])
        algebraic_zero=len(kernel);kernel_dimensions=[len(kernel)]
        if kernel:
            augmented,ap=rref([ar+mr for ar,mr in zip(Ra,Rm)],n)
            if len(ap)!=n:raise ArithmeticError('singular inertia pencil requires a separate infinite-mode contract')
            B=[row[n:]for row in augmented];power=B
            for order in range(2,n+2):
                power=[[sum((power[i][k]*B[k][j]for k in range(n)),Q())for j in range(n)]for i in range(n)]
                _,pp=rref(power,n);nullity=n-len(pp);kernel_dimensions.append(nullity)
                if nullity==algebraic_zero:break
                if nullity<algebraic_zero:raise ArithmeticError('exact rank-power invariant failed')
                algebraic_zero=nullity
            candidates=offset+np.argsort(abs(vals[offset:offset+n]))[:algebraic_zero]
            for position,index in enumerate(candidates):
                v=kernel[position%len(kernel)]
                if abs(vals[index])>1e-9*max(1.,np.linalg.norm(Ms[np.ix_(ix,ix)],ord=np.inf)):
                    raise ArithmeticError('QZ/exact zero algebraic multiplicity disagreement')
                vals[index]=0;U[:,index]=0;U[ix,index]=v/np.linalg.norm(v)
                refinement.append({'column':int(index),'method':'exact_original_binary_pencil_block_zero_generalized_eigenspace','iterations':0})
        zero_blocks.append(dict(component=[int(i)for i in ix],geometric_multiplicity=len(kernel),algebraic_multiplicity=algebraic_zero,kernel_dimensions_by_power=kernel_dimensions))
        offset+=n
    zero_structure=dict(geometric_multiplicity=sum(b['geometric_multiplicity']for b in zero_blocks),algebraic_multiplicity=sum(b['algebraic_multiplicity']for b in zero_blocks),blocks=zero_blocks,complete_eigenbasis_not_claimed=any(b['algebraic_multiplicity']>b['geometric_multiplicity']for b in zero_blocks))
    def pair_error(v,value):
        original=d*v;r=np.abs(M@original-value*(A@original));s=np.abs(M)@np.abs(original)+abs(value)*(np.abs(A)@np.abs(original))
        return np.divide(r,s,out=np.zeros_like(r),where=s!=0),bool(np.any((s==0)&(r!=0)))
    for j in range(len(vals)):
        v=U[:,j];value=vals[j];pivot=int(np.argmax(abs(v)));v=v/v[pivot]
        active=np.array(sorted({i for component in components if any(v[k]!=0 for k in component)for i in component}));local_pivot=int(np.flatnonzero(active==pivot)[0])
        for iteration in range(13):
            e,bad=pair_error(v,value)
            if not bad and np.max(e)<=backward_tolerance:break
            if iteration==12:
                # Precision fallback addresses cancellation, not a relaxed gate.
                # Start from the computed pair, use exact original binary M/A
                # coefficients and explicit D in 80-digit arithmetic, at most8
                # Newton steps. Round back to double, then recheck original units.
                import mpmath as mp
                with mp.workdps(80):
                    def mc(z):return mp.mpc(float(z.real),float(z.imag))
                    BM=mp.matrix([[mc(M[a,b])*mp.mpf(float(d[b]))/mp.mpf(float(d[a]))for b in active]for a in active])
                    BA=mp.matrix([[mc(A[a,b])*mp.mpf(float(d[b]))/mp.mpf(float(d[a]))for b in active]for a in active])
                    vv=mp.matrix([mc(v[a])for a in active]);ww=mc(value)
                    for hp_iteration in range(8):
                        rr=BM*vv-ww*(BA*vv);JJ=mp.matrix(len(active)+1);bb=mp.matrix(len(active)+1,1)
                        for a in range(len(active)):
                            for b in range(len(active)):JJ[a,b]=BM[a,b]-ww*BA[a,b]
                            JJ[a,len(active)]=-(BA*vv)[a];bb[a]=-rr[a]
                        JJ[len(active),local_pivot]=1
                        step=mp.lu_solve(JJ,bb)
                        for a in range(len(active)):vv[a]+=step[a]
                        ww+=step[len(active)]
                        if max(abs(z)for z in step)<mp.mpf('1e-65'):break
                    for a,i in enumerate(active):v[i]=complex(vv[a])
                    value=complex(ww)
                e,bad=pair_error(v,value)
                refinement.append({'column':j,'method':'original_binary_pencil_80digit_Newton','iterations':hp_iteration+1})
                if bad or np.max(e)>backward_tolerance:
                    raise ArithmeticError('componentwise eigenpair backward-error gate failed after precision refinement: '+repr(dict(column=j,value=value,max_error=float(np.max(e)),row=int(np.argmax(e)))))
                break
            J=np.zeros((len(active)+1,len(active)+1),complex);J[:-1,:-1]=(Ms-value*As)[np.ix_(active,active)];J[:-1,-1]=-(As@v)[active];J[-1,local_pivot]=1
            rhs=np.r_[-(Ms@v-value*(As@v))[active],0j]
            step=lstsq(J,rhs,lapack_driver='gelsy')[0];v[active]+=step[:-1];value+=step[-1]
        U[:,j]=v;vals[j]=value
        refinement.append({'column':j,'method':'normalized_eigenpair_Newton_lstsq','iterations':iteration})
    V=d[:,None]*U
    if not np.isfinite(vals).all()or not np.isfinite(V).all():raise ArithmeticError('finite physical eigenpairs not obtained')
    residual=np.abs(M@V-(A@V)*vals[None,:]);scale=np.abs(M)@np.abs(V)+(np.abs(A)@np.abs(V))*np.abs(vals)[None,:]
    error=np.divide(residual,scale,out=np.zeros_like(residual),where=scale!=0)
    if np.any((scale==0)&(residual!=0))or np.max(error)>backward_tolerance:raise ArithmeticError('componentwise eigenpair backward-error gate failed')
    omega=1j*vals;i1=np.argsort(-omega.real,kind='stable');i2=np.argsort(-omega.imag,kind='stable')
    return dict(w1=omega[i1],w2=omega[i2],X1=V[:,i1],X2=V[:,i2],componentwise_backward_errors=error,refinement=refinement,zero_structure=zero_structure)


def normalize_plot_coordinates(k,omega,*,length_scale_m=None,frequency_scale_rad_s=None):
    """Explicit SI or caller-declared scales; never consult hidden plotting globals."""
    if (length_scale_m is None)!=(frequency_scale_rad_s is None):raise ValueError('supply both normalization scales or neither')
    k=np.asarray(k);w=np.asarray(omega)
    if length_scale_m is None:return dict(k=k,omega=w,k_units='m^-1',omega_units='rad/s')
    length=float(length_scale_m);freq=float(frequency_scale_rad_s)
    if not np.isfinite([length,freq]).all()or length<=0 or freq<=0:raise ValueError('normalization scales must be positive finite')
    return dict(k=k*length,omega=w/freq,k_units='dimensionless',omega_units='dimensionless')


class ContinuationFailure(RuntimeError):
    def __init__(self,record):self.record=record;super().__init__('root not accepted; continuation stopped before seed update')


def em1d_parallel_residual(state,omega,k,*,pm=1):
    """Parallel drifting Maxwellian S-species EM relation, SI rad/s and m^-1.

    f=omega^2-c^2 k^2+sum wp_s^2(omega-k vd_s)/(|k| vt_s) Z(z_s),
    z_s=(omega-k vd_s+pm wc_s)/(|k| vt_s); vt uses sqrt(2kBT/m).
    Causal Gaussian velocity integral uses |k| in both thermal denominators;
    Doppler k*vd remains signed, pm labels fixed-z circular polarization.
    From DLMF7.7.E2 Gaussian velocity integral; no helicity relabel on k reversal.
    All supplied species participate; pm=+/-1 is explicit.
    """
    kval=np.asarray(k)
    if kval.shape!=()or kval.dtype.kind not in 'iuf'or not np.isfinite(kval)or kval==0:raise ValueError('finite real nonzero k required; both signs supported')
    k=float(kval)
    if not np.isfinite(k):raise ValueError('k must be representable as finite binary64')
    wval=np.asarray(omega)
    if wval.shape!=()or wval.dtype.kind not in 'iufc'or not np.isfinite(wval):raise ValueError('finite complex scalar omega required')
    omega=complex(wval)
    if not np.isfinite(omega):raise ValueError('omega must be representable as finite complex128')
    if pm not in(-1,1):raise ValueError('pm +/-1 required')
    arrays=[np.asarray(state[n],dtype=float).reshape(-1)for n in ['wps2','vds','vtzs','wcs']]
    if not arrays[0].size or any(a.shape!=arrays[0].shape or not np.isfinite(a).all()for a in arrays)or np.any(arrays[2]<=0)or np.any(arrays[0]<0):raise ValueError('matching nonempty finite species vectors, nonnegative wp2 and positive vt required')
    if 'Tzs'in state and 'Tps'in state and not np.array_equal(np.asarray(state['Tzs']),np.asarray(state['Tps'])):
        raise ValueError('parallel reference relation assumes isotropic Maxwellian temperatures')
    if 'alphas'in state and np.any(np.asarray(state['alphas'])!=1):
        raise ValueError('loss-cone state is outside the declared Maxwellian reference relation')
    wp,vd,vt,wc=arrays;z=(omega-k*vd+pm*wc)/(abs(k)*vt);Z=canonical_faddeeva(z)['Z']
    terms=wp*(omega-k*vd)/(abs(k)*vt)*Z;vac=omega**2-k*k*float(np.asarray(state['c2']).item());f=vac+np.sum(terms)
    scale=max(abs(omega**2)+abs(k*k*float(np.asarray(state['c2']).item()))+np.sum(np.abs(terms)),np.finfo(float).tiny)
    if not np.isfinite(f)or not np.isfinite(scale):raise ValueError('parallel response not representable in binary64')
    return complex(f),float(scale)


def continue_em1d(state,*,pm=1,k_grid=None,initial_guess=None,residual_tolerance=1e-10,solver_options=None):
    """Corrected stopping protocol: finite solver-success AND scaled residual required.

    Source defaults/grid/initial seed retained; no failed root becomes next seed.
    Stops with attempted value/flags/residual and complete accepted prefix. No
    interpolation, alternate-root rescue or solver-convergence fiction in glue.
    """
    residual_tolerance = _positive_finite_tolerance(residual_tolerance, 'residual_tolerance')
    if k_grid is not None:
        supplied=np.asarray(k_grid)
        if supplied.dtype.kind not in 'iuf'or not supplied.size or not np.isfinite(supplied).all()or np.any(supplied==0):raise ValueError('finite real nonzero continuation grid required; both signs supported')
    k=(np.arange(1,51)*.01/float(np.asarray(state['cwp']).item()))if k_grid is None else np.asarray(k_grid,dtype=float).reshape(-1)
    seed=complex((.05+.04j)*float(np.asarray(state['wcs1']).item()))if initial_guess is None else complex(initial_guess)
    solver = root
    accepted=[];records=[]
    for point in k:
        def fun(v):
            f,scale=em1d_parallel_residual(state,complex(*v),point,pm=pm)
            return np.array([f.real/scale,f.imag/scale])
        try:
            result=solver(fun,[seed.real,seed.imag],method='hybr',options=solver_options or {})
        except Exception as cause:
            raise ContinuationFailure(dict(k=float(point),guess=seed,accepted_prefix=tuple(accepted),evaluation_error=repr(cause))) from cause
        attempted=complex(*result.x);f,scale=em1d_parallel_residual(state,attempted,point,pm=pm)
        record=dict(k=float(point),guess=seed,attempted=attempted,solver_success=bool(result.success),solver_status=int(result.status),scaled_residual=abs(f)/scale,accepted_prefix=tuple(accepted))
        if not result.success or not np.isfinite(attempted)or not np.isfinite(f)or abs(f)/scale>residual_tolerance:raise ContinuationFailure(record)
        accepted.append(attempted);records.append(record);seed=attempted
    return dict(k=k,omega=np.asarray(accepted),records=records)


def fluid_scan_plan(method=2,*,scan_k=None,scan_theta=None,scan_kx=None,scan_kz=None,angle=np.pi/3,wave_number=None):
    """Explicit original four scan modes; no eig or terminal-data reconstruction.

    Canonical shape is (n_first,n_second,n_modes); axis names are returned.
    Source defaults remain101k,51theta,75x50mesh, and one point. Endpoint/grid
    mapping can be checked without solving the expensive default2D grid.
    """
    if method==1:
        kk=np.array([.1 if wave_number is None else wave_number]);tt=np.array([angle]);K,T=np.meshgrid(kk,tt,indexing='ij');axes=('single','single')
    elif method==2:
        kk=np.arange(101)*1e-5 if scan_k is None else np.asarray(scan_k,dtype=float);tt=np.array([angle]);K,T=np.meshgrid(kk,tt,indexing='ij');axes=('k','theta')
    elif method==3:
        kk=np.array([2. if wave_number is None else wave_number]);tt=np.arange(51)*(np.pi/100)if scan_theta is None else np.asarray(scan_theta,dtype=float);K,T=np.meshgrid(kk,tt,indexing='ij');axes=('k','theta')
    elif method==4:
        x=.01+.04*np.arange(75)if scan_kx is None else np.asarray(scan_kx,dtype=float);z=.01+.04*np.arange(50)if scan_kz is None else np.asarray(scan_kz,dtype=float)
        X,Z=np.meshgrid(x,z,indexing='ij')
        if not np.isfinite(X).all()or not np.isfinite(Z).all():raise ValueError('finite scan coordinates required')
        return dict(kx=X,kz=Z,axis_names=('kx','kz'),axis_values=(x,z))
    else:raise ValueError('method must be one of1..4; no silent complement')
    if not np.isfinite(K).all()or not np.isfinite(T).all():raise ValueError('finite scan coordinates required')
    return dict(kx=K*np.sin(T),kz=K*np.cos(T),axis_names=axes,axis_values=(kk,tt))


def scan_fluid_corrected(state,*,method=2,state_scales=None,relativistic=False,**grid_controls):
    plan=fluid_scan_plan(method,**grid_controls);shape=plan['kx'].shape;dim=4*len(state['q'])+6
    w1=np.empty(shape+(dim,),complex);w2=np.empty_like(w1);points=[]
    for index in np.ndindex(shape):
        result=fluid_solve_state(state,plan['kx'][index],plan['kz'][index],relativistic=relativistic,state_scales=state_scales)
        w1[index]=result['w1'];w2[index]=result['w2'];points.append(dict(index=index,**result))
    return dict(plan,w1=w1,w2=w2,points=points)


def pair_exchange_from_relative_rates(rho,species_classes,*,electron_bath_rate=0.,ion_bath_rate=0.,electron_pair_relative_rate=0.,ion_pair_relative_rate=0.,electron_ion_relative_rate=0.):
    """PRIVATE corrected five-control scientific VARIANT, NOT old nu equivalence.

    Each scalar is nonnegative [1/s]. Pair controls specify decay rate of the
    two-fluid relative velocity, not individual row's incoming coefficient.
    Kij=nu_relative*rho_i*rho_j/(rho_i+rho_j) therefore conserves momentum and
    gives d(vi-vj)/dt=-nu_relative*(vi-vj) for the isolated pair. Bath controls
    are externally anchored one-body drag. Explicit electron/ion roles include
    negative ions as ions; no mass<=1kg or charge-sign heuristic is used.
    These names/role inputs disclose a physical port change from ambiguous D0.
    """
    rho=np.asarray(rho,dtype=float);roles=tuple(species_classes)
    rates=np.asarray([electron_bath_rate,ion_bath_rate,electron_pair_relative_rate,ion_pair_relative_rate,electron_ion_relative_rate],dtype=float)
    if rho.ndim!=1 or not rho.size or len(roles)!=rho.size or np.any(rho<=0)or not np.isfinite(rho).all():raise ValueError('positive finite rho and matching roles required')
    if any(role not in ('electron','ion')for role in roles)or not np.isfinite(rates).all()or np.any(rates<0):raise ValueError('explicit electron/ion roles and positive rates required')
    K=np.zeros((rho.size,rho.size));drag=np.array([rates[0]if role=='electron'else rates[1]for role in roles])
    for i in range(rho.size):
        for j in range(i+1,rho.size):
            rate=rates[2]if roles[i]==roles[j]=='electron'else rates[3]if roles[i]==roles[j]=='ion'else rates[4]
            # Harmonic density factor, same relation with one avoided rho_i*rho_j overflow.
            factor=min(rho[i],rho[j])/(1+min(rho[i],rho[j])/max(rho[i],rho[j]))
            K[i,j]=K[j,i]=rate*factor
    return dict(exchange=K,bath_drag=drag,velocity_generator=collision_velocity_generator(rho,K,drag))


def fluid_equilibrium_relative_rates(deck,*,species_classes,B0=100e-9,gamma=5/3,pressure_frame='field_following',**relative_rate_controls):
    """Production corrected variant: explicit roles and physical relative rates.

    The five named controls have the declared pair-relative/bath interpretation;
    legacy ambiguous nue/nui/nuee/nuii/nuei ports are not silently accepted.
    """
    state=fluid_equilibrium_si(deck,B0=B0,gamma=gamma,pressure_frame=pressure_frame)
    rates=pair_exchange_from_relative_rates(state['rho'],species_classes,**relative_rate_controls)
    state.update(velocity_collision=rates['velocity_generator'],exchange=rates['exchange'],bath_drag=rates['bath_drag'],species_classes=tuple(species_classes),collision_contract='explicit_relative_pair_rates_and_stationary_bath_variant')
    return state


def fluid_state_scales(state):
    """Explicit physical SI balancing, velocity unit1m/s, source c for density.

    d_n=n/c, d_v=1, d_E=m_ref*omega_p/|q_ref|, d_B=d_E/c. The reference
    is first charged species, omega_p quadrature sum; neutral-only states use
    Eunit1V/m. This changes basis only, never original M/A or returned units.
    """
    S=len(state['q']);speed=np.sqrt(state['c2']);d=np.ones(4*S+6)
    d[np.arange(S)*4]=state['n']/speed
    charged=np.flatnonzero(state['q']!=0)
    if charged.size:
        j=int(charged[0]);wp=np.sqrt(np.sum(state['n']*state['q']**2/(state['epsilon0']*state['m'])))
        E=state['m'][j]*wp/abs(state['q'][j])
    else:E=1.
    d[4*S:4*S+3]=E;d[4*S+3:]=E/speed
    if not np.isfinite(d).all()or np.any(d<=0):raise ValueError('physical state scales not representable; supply explicit positive scales')
    return d


def fluid_solve_state(state,kx,kz,*,relativistic=False,state_scales=None,backward_tolerance=1e-10):
    """Public-shaped corrected state→M/A→omega/eigenvectors composition.

    QZ/refinement replaces both oldmethod branches; outputs include the point
    pencil, both sorted spectra/eigenvectors, scales and qualification metadata.
    No claim that symbolic16-digit rounding creates16-digit forward accuracy.
    """
    pencil=fluid_frequency_pencil(state,kx,kz,relativistic=relativistic)
    scales=fluid_state_scales(state)if state_scales is None else state_scales
    result=solve_frequency_pencil(pencil['M'],pencil['A'],state_scales=scales,backward_tolerance=backward_tolerance)
    return dict(pencil,**result,state_scales=np.asarray(scales))
