"""Generalized normalized velocity distributions and electrostatic scans.

Lineage: GPDF frozen D1 operators gpdf_zetaph, calFp, hilb, residual,
small_k and root_scans. This D2 implementation uses resolved quadrature,
explicit distributional jumps, and a restricted expression interpreter.
Z=integral f(v)/(v-z) dv; Zp=dZ/dz includes jumps of f.
"""
import ast
import warnings

import numpy as np
from scipy.integrate import quad, IntegrationWarning
from scipy.optimize import root
from .cauchy_transform import evaluate_cauchy_transform
from .plasma_dispersion import evaluate_plasma_dispersion
from .maxwellian_electrostatic import evaluate_maxwellian_electrostatic, _susceptibility


class DensityExpression:
    """Safe arithmetic expression in v, with analytic first derivative.

    Supports numeric constants, pi, v, + - * / ** and exp/log/sqrt/sin/cos/
    sinh/cosh/tanh. MATLAB elementwise operators are accepted. Attributes,
    indexing, arbitrary names, and arbitrary calls are rejected. No eval or
    symbolic engine is used. Inputs must describe a real, integrable density;
    a caller-provided mesh must resolve its features. This is not verified by
    finitely many samples. Piecewise densities use the named selectors.
    """
    def __init__(self, expression):
        if not isinstance(expression,str) or len(expression)>4096:
            raise ValueError('expression must be a string of at most 4096 characters')
        expression=expression.replace('.^','**').replace('^','**').replace('.*','*').replace('./','/')
        try: self.tree=ast.parse(expression,mode='eval').body
        except (SyntaxError,RecursionError) as exc: raise ValueError('invalid density expression') from exc
        if len(list(ast.walk(self.tree)))>256:
            raise ValueError('density expression is too complex')
        allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.Call,ast.Name,ast.Load,ast.Constant,
                 ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.USub,ast.UAdd)
        for node in ast.walk(self.tree):
            if not isinstance(node,allowed): raise ValueError('unsupported density expression syntax')
            if isinstance(node,ast.Constant) and (type(node.value) not in (int,float) or not np.isfinite(node.value)):
                raise ValueError('only finite real constants are allowed')
            if isinstance(node,ast.Name) and node.id not in {'v','pi',*self._functions}:
                raise ValueError('unknown density expression name')
            if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in self._functions or len(node.args)!=1 or node.keywords):
                raise ValueError('unsupported density expression call')

    _functions={
        'exp':(np.exp,np.exp), 'log':(np.log,lambda x:1/x),
        'sqrt':(np.sqrt,lambda x:.5/np.sqrt(x)), 'sin':(np.sin,np.cos),
        'cos':(np.cos,lambda x:-np.sin(x)), 'sinh':(np.sinh,np.cosh),
        'cosh':(np.cosh,np.sinh), 'tanh':(np.tanh,lambda x:1/np.cosh(x)**2)}

    def _dual(self,node,v):
        if isinstance(node,ast.Constant): return node.value,0.
        if isinstance(node,ast.Name):
            if node.id=='v': return v,1.
            if node.id=='pi': return np.pi,0.
            raise ValueError('function name must be called')
        if isinstance(node,ast.UnaryOp):
            a,da=self._dual(node.operand,v)
            return (-a,-da) if isinstance(node.op,ast.USub) else (a,da)
        if isinstance(node,ast.Call):
            a,da=self._dual(node.args[0],v); f,df=self._functions[node.func.id]
            return f(a),df(a)*da
        a,da=self._dual(node.left,v); b,db=self._dual(node.right,v)
        if isinstance(node.op,ast.Add): return a+b,da+db
        if isinstance(node.op,ast.Sub): return a-b,da-db
        if isinstance(node.op,ast.Mult): return a*b,da*b+a*db
        if isinstance(node.op,ast.Div): return a/b,(da*b-a*db)/(b*b)
        if np.all(np.asarray(db)==0):
            if b==0: return np.ones_like(a),np.zeros_like(a)
            return a**b,b*a**(b-1)*da
        value=a**b
        return value,value*(db*np.log(a)+b*da/a)

    @staticmethod
    def _velocity(v):
        raw=np.asarray(v)
        if raw.dtype.kind not in 'iufc' or raw.size==0 or not np.isfinite(raw).all():
            raise ValueError('velocity must contain finite numeric values')
        return np.asarray(raw,dtype=complex if raw.dtype.kind=='c' else float)

    def __call__(self,v): return self._dual(self.tree,self._velocity(v))[0]
    def derivative(self,v): return self._dual(self.tree,self._velocity(v))[1]


def _points(z):
    raw=np.asarray(z)
    if raw.size==0 or raw.dtype.kind not in 'iufc' or not np.isfinite(raw).all():
        raise ValueError('z must be finite nonempty numeric values')
    return np.asarray(raw,dtype=complex)


def _transform(z,density,derivative,mesh,bounds=None,analytic=None,epsabs=1e-10):
    """Use qualified Cauchy off axis and a subtracted PV on the real line."""
    points=_points(z); result=np.empty(points.shape,dtype=complex)
    for index in np.ndindex(points.shape):
        point=complex(points[index])
        if point.imag:
            result[index]=evaluate_cauchy_transform(point,density,bounds=bounds,
                integration_mesh=mesh,analytic_density=analytic,epsabs=epsabs)['G']
            continue
        x=point.real
        if bounds is not None and not bounds[0]<x<bounds[1]:
            if x in bounds: raise ValueError('real-axis endpoint singularity')
            edges=[*bounds[:1],*mesh,*bounds[1:]]
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('error',IntegrationWarning)
                    value=sum(quad(lambda v:density(v)/(v-x),a,b,epsabs=epsabs,epsrel=1e-10)[0]
                              for a,b in zip(sorted(set(edges))[:-1],sorted(set(edges))[1:]))
            except IntegrationWarning as exc:
                raise RuntimeError('generalized real-axis quadrature did not converge') from exc
            result[index]=value
            continue
        fx=float(density(x))
        # Subtract an even Gaussian: its full-line PV integral divided by
        # (v-x) vanishes exactly, leaving a removable singularity.
        def integrand(v):
            d=v-x
            if abs(d)<1e-7: return float(derivative(x))
            return (density(v)-fx*np.exp(-d*d))/d
        edges=sorted(set([-np.inf,*mesh,x,np.inf]))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',IntegrationWarning)
                value=sum(quad(integrand,a,b,epsabs=epsabs/len(edges),epsrel=1e-10)[0]
                          for a,b in zip(edges[:-1],edges[1:]))
        except IntegrationWarning as exc:
            raise RuntimeError('generalized principal-value quadrature did not converge') from exc
        result[index]=value+1j*np.pi*fx
    if not np.isfinite(result).all(): raise ValueError('generalized transform is not representable')
    return result


def evaluate_generalized_hilbert(z,expression,*,integration_mesh,continuation=True):
    """Return Z and Zp for an analytic expression with explicit feature mesh.

    Mesh includes the distribution's location and scale; infinite tails remain
    included. On the real axis returns the upper boundary PV+i*pi*f. Lower
    continuation adds 2*pi*i*f (and f') when continuation=True. Zp is the
    transform of the analytic derivative, requiring vanishing end values.
    At |z|>=12 the equivalent Cauchy[v*f′]/z avoids zero-mass
    cancellation; its absolute tolerance scales as1/|z|.
    """
    f=DensityExpression(expression)
    mesh=np.asarray(integration_mesh,dtype=float)
    if mesh.ndim!=1 or mesh.size<2 or not np.isfinite(mesh).all() or np.any(np.diff(mesh)<=0):
        raise ValueError('integration_mesh must be finite increasing points')
    # The derivative PV needs f'' only at its removable point; symmetric
    # differentiation here is local quadrature regularization, not Zp.
    second=lambda v:(f.derivative(v+1e-5)-f.derivative(v-1e-5))/2e-5
    points=_points(z)
    Z=_transform(points,f,f.derivative,mesh,analytic=f if continuation else None)
    Zp=np.empty(points.shape,dtype=complex)
    weighted=lambda v:v*f.derivative(v)
    weighted_prime=lambda v:f.derivative(v)+v*second(v)
    for index in np.ndindex(points.shape):
        point=complex(points[index])
        magnitude=np.abs(np.clongdouble(point))
        if magnitude>=12:
            # Integral f'=0 for the declared vanishing boundary values.
            # Cauchy[v*f'] = z*Cauchy[f']; the weighted density has a
            # nonzero leading mass and avoids cold-limit cancellation.
            tolerance=float(np.longdouble(1e-10)/magnitude)
            Zp[index]=_transform(point,weighted,weighted_prime,mesh,
                analytic=weighted if continuation else None,epsabs=tolerance)/point
        else:
            Zp[index]=_transform(point,f.derivative,second,mesh,
                analytic=f.derivative if continuation else None)
    if not np.isfinite(Zp).all():
        raise ValueError('analytic density derivative transform is not representable')
    return {'Z':Z,'Zp':Zp}



def _gaussian_derivative(points,Z):
    """Use raw susceptibility rather than rounded epsilon or 1+z*Z.

    At k=1/sqrt(2), omega=z, raw chi is exactly 2*(1+z*Z),
    so Zp=-chi. This reuses the qualified Gaussian-moment derivation.
    At enormous |z| the next inverse-power term is unrepresentable in
    float64; wide arithmetic retains the leading term and continuation
    without Python complex abs overflow or an overflowing sqrt(2)*z.
    """
    values=np.empty(points.shape,dtype=complex)
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        for index in np.ndindex(points.shape):
            point=complex(points[index]); wide=np.clongdouble(point)
            magnitude=np.abs(wide)
            if magnitude<12:
                value=-2*(1+point*complex(Z[index]))
            elif magnitude<=1e150:
                value=-_susceptibility(point,1/np.sqrt(2),point)[0]
            else:
                inverse=1/wide
                value=inverse*inverse
                if point.imag<=0:
                    factor=4 if point.imag<0 else 2
                    logterm=-wide*wide+np.log(np.longdouble(factor)*np.sqrt(np.longdouble(np.pi)))+np.log(wide)
                    value-=1j*np.exp(logterm)
                value=complex(value)
            # Even real Gaussian density makes Zp purely real on iR.
            if point.real==0: value=complex(value.real,0.)
            values[index]=value
    if not np.isfinite(values).all():
        raise ValueError('Gaussian derivative is not representable')
    return values


def _top_hat_transform(points):
    """Stable real logarithm/contour angle near support; moments at |z|>=1.

    Z=-z^-1*sum((1/(2z))^(2n)/(2n+1)); the ratio magnitude is
    at most1/4 in the far region. This avoids both separate-log
    subtraction and tiny-complex-log1p loss. Zp=1/((z-.5)(z+.5))
    uses separated denominator parts (x-.5)*(x+.5)-y*y and2*x*y
    followed by one wide reciprocal, never reciprocal subtraction.
    """
    wide=points.astype(np.clongdouble)
    far=np.abs(wide)>=1
    Z=np.empty(points.shape,dtype=complex)
    if np.any(far):
        inverse=1/wide[far]
        ratio=(inverse/2)**2
        power=np.ones(inverse.shape,dtype=np.clongdouble)
        total=power.copy()
        for n in range(1,129):
            power*=ratio
            term=power/(2*n+1)
            total+=term
            if np.all(np.abs(term)<=np.finfo(float).eps*np.abs(total)/4):break
        Z[far]=np.asarray(-inverse*total,dtype=complex)
    if np.any(~far):
        near=wide[~far]
        x,y=near.real,near.imag
        center=np.abs(x)<=.25
        re=np.empty(x.shape,dtype=np.longdouble)
        # A real log1p preserves the odd-in-x response near the center;
        # unlike complex log1p it does not lose tiny contour components.
        denominator=(x[center]+.5)**2+y[center]**2
        re[center]=np.log1p(-2*x[center]/denominator)/2
        re[~center]=np.log(np.hypot(x[~center]-.5,y[~center]))-np.log(np.hypot(x[~center]+.5,y[~center]))
        # This single angle is the integrated Cauchy kernel's contour
        # angle. Subtracting two almost equal arguments loses tiny y.
        im=np.arctan2(y,(x-.5)*(x+.5)+y*y)
        im=np.where(y==0,np.pi*(np.abs(x)<.5),im)
        Z[~far]=np.asarray(re+1j*im,dtype=complex)
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        x,y=wide.real,wide.imag
        denominator=(x-.5)*(x+.5)-y*y+1j*(2*x*y)
        Zp=np.asarray(1/denominator,dtype=complex)
    if not np.isfinite(Z).all() or not np.isfinite(Zp).all():
        raise ValueError('top-hat transform is not representable')
    return {'Z':Z,'Zp':Zp}


def evaluate_generalized_dispersion(z,selector=0,*,expression='exp(-v.^2)/sqrt(pi)',integration_mesh=None):
    """Return Z and Zp for all original GPDF selectors 0 through 6.

    0: analytic expression (default Maxwellian), 1: delta at zero,
    2: positive unit top-hat [-.5,.5], 3: unit triangular [-1,1],
    4: normalized kappa/gamma n=2, vt=1, 5: incomplete Maxwellian
    H(v-.1)*exp(-v²)/sqrt(pi), 6: truncated slowing-down |v|<=4.
    Selectors 2,3,5,6 use the real-contour transform below the real axis;
    no analytic extension of a discontinuity is inferred. Real-axis values
    are upper boundaries and exclude jumps/endpoints. Zp includes exact
    distributional jumps. Selector 5 is intentionally not renormalized;
    selector 6 retains the upstream finite-cutoff normalization.
    """
    z=_points(z)
    if isinstance(selector,(bool,np.bool_)) or not isinstance(selector,(int,np.integer)) or selector not in range(7):
        raise ValueError('selector must be an integer from 0 through 6')
    if selector==0:
        if expression in ('exp(-v.^2)/sqrt(pi)','exp(-v**2)/sqrt(pi)'):
            Z=np.asarray(evaluate_plasma_dispersion(z)['Z'])
            return {'Z':Z,'Zp':_gaussian_derivative(z,Z)}
        if integration_mesh is None: raise ValueError('custom expression requires integration_mesh')
        return evaluate_generalized_hilbert(z,expression,integration_mesh=integration_mesh)
    if selector==1:
        if np.any(z==0): raise ValueError('delta transform pole at zero')
        return {'Z':-1/z,'Zp':1/z**2}
    if selector==4:
        return evaluate_generalized_hilbert(z,'sqrt(2)/pi/(1+v**2/2)**2',integration_mesh=[-16,-4,-1,0,1,4,16])
    if selector==2:
        if np.any((z.imag==0)&(np.abs(z.real)==.5)): raise ValueError('top-hat endpoint singularity')
        return _top_hat_transform(z)
    if selector==3:
        f=lambda v:max(0.,1-abs(v))
        fp=lambda v:1. if -1<v<0 else (-1. if 0<v<1 else 0.)
        mesh=[-1.,0.,1.]; bounds=(-1.,1.); jumps=[]
    elif selector==5:
        f=lambda v:np.exp(-v*v)/np.sqrt(np.pi) if v>.1 else 0.
        fp=lambda v:-2*v*f(v)
        mesh=[.1,.5,1.,2.,4.,8.]; bounds=None; jumps=[(.1,np.exp(-.01)/np.sqrt(np.pi))]
    else:
        c=3*np.sqrt(3)/(4*np.pi)
        f=lambda v:c/(abs(v)**3+1) if abs(v)<4 else 0.
        fp=lambda v:-3*c*v*abs(v)/(abs(v)**3+1)**2 if abs(v)<4 else 0.
        mesh=[-4.,-2.,-1.,0.,1.,2.,4.]; bounds=(-4.,4.); jumps=[(-4,c/65),(4,-c/65)]
    singular=[*([0.] if selector==3 else []),*[p for p,_ in jumps],*(bounds or [])]
    if any(np.any((z.imag==0)&(z.real==p)) for p in singular):
        raise ValueError('real-axis distribution corner or endpoint singularity')
    second=lambda v:(fp(v+1e-5)-fp(v-1e-5))/2e-5
    Z=_transform(z,f,fp,mesh,bounds)
    Zp=_transform(z,fp,second,mesh,bounds)
    for location,jump in jumps: Zp+=jump/(location-z)
    return {'Z':Z,'Zp':Zp}


def evaluate_gpdf_residual(kind,x,k,*,ion_temperature=1.,ion_mass=1836.,beam_fraction=.1,beam_temperature=1.,beam_drift=5.,selector=0,expression='exp(-v.^2)/sqrt(pi)',integration_mesh=None):
    """Lifted source residual in phase x=omega/(sqrt(2)*k); k>0.

    Langmuir/generalized return D=k²-Zp/2. IAW and beam retain source
    temperature/mass/drift normalization. Shapes broadcast elementwise.
    """
    x=_points(x)
    if not np.isscalar(k) or not np.isreal(k) or not np.isfinite(k) or k<=0: raise ValueError('k must be finite positive scalar')
    response=lambda q:1+q*evaluate_plasma_dispersion(q)['Z']
    if kind=='langmuir': return evaluate_maxwellian_electrostatic(x*np.sqrt(2)*k,k)['D']
    if kind=='generalized':
        if selector==0 and expression=='exp(-v.^2)/sqrt(pi)':
            return evaluate_maxwellian_electrostatic(x*np.sqrt(2)*k,k)['D']
        return k*k-evaluate_generalized_dispersion(x,selector,expression=expression,integration_mesh=integration_mesh)['Zp']/2
    if kind=='iaw':
        if not np.isfinite([ion_temperature,ion_mass]).all() or min(ion_temperature,ion_mass)<=0: raise ValueError('ion temperature and mass must be positive')
        return k*k+response(x)+response(x/np.sqrt(ion_temperature/ion_mass))/ion_temperature
    if kind=='beam':
        if not np.isfinite([beam_fraction,beam_temperature,beam_drift]).all() or not 0<=beam_fraction<=1 or beam_temperature<=0: raise ValueError('invalid beam parameters')
        return k*k+(1-beam_fraction)*response(x)+beam_fraction/beam_temperature*response(x/np.sqrt(beam_temperature)-beam_drift)
    raise ValueError('unknown residual kind')


def evaluate_gpdf_small_k(k):
    """Source asymptotic omega_r=1+1.5k², omega_i with exp(-1/(2k²))."""
    k=np.asarray(k)
    if k.dtype.kind not in 'iuf' or k.size==0 or not np.isfinite(k).all() or np.any(k<=0): raise ValueError('k must be finite positive real values')
    k=np.asarray(k,dtype=float)
    with np.errstate(over='ignore',under='ignore',divide='ignore'):
        damping=-np.exp(.5*np.log(np.pi/8)-.5/k**2-1.5-3*np.log(k))
    with np.errstate(over='ignore'):
        real=1+1.5*k*k
    if not np.isfinite(real).all() or not np.isfinite(damping).all():
        raise ValueError('small-k asymptotic is not representable')
    return {'omega_real':real,'omega_imag':damping}


def scan_gpdf_roots(kind,*,k_values=None,initial_guess=None,residual_tolerance=1e-9,max_evaluations=300,**parameters):
    """Seeded sequential legacy scans with explicit real-vector MINPACK solve.

    Preserves original grids, guesses, frequency scaling, and continuation
    order. Fixes the invalid fourth fsolve argument by closing over k, and
    exposes the complex residual as two real components. Failure rejects the
    scan, rather than returning an unqualified branch. No uniqueness claim.
    initial_guess is a phase x except for generalized (frequency omega), as
    in the source; returned omega is normalized by plasma frequency.
    """
    grids={'langmuir':np.r_[np.arange(1,11)/10,np.arange(2,11)],
           'iaw':np.arange(22,0,-1)/20,'beam':np.arange(80,9,-1)/200,
           'generalized':np.r_[np.arange(1,11)/10,np.arange(3,11)/2]}
    seeds={'langmuir':1-.1j,'iaw':.04-.02j,'beam':(1-.01j)*np.sqrt(2)*.4,'generalized':1.5-.001j}
    if kind not in grids: raise ValueError('unknown scan kind')
    ks=np.asarray(grids[kind] if k_values is None else k_values)
    if ks.ndim!=1 or ks.size==0 or ks.dtype.kind not in 'iuf' or not np.isfinite(ks).all() or np.any(ks<=0): raise ValueError('k_values must be finite positive vector')
    if not np.isfinite(residual_tolerance) or residual_tolerance<=0: raise ValueError('residual_tolerance must be positive')
    if isinstance(max_evaluations,bool) or not isinstance(max_evaluations,(int,np.integer)) or max_evaluations<1: raise ValueError('max_evaluations must be positive integer')
    guess=complex(seeds[kind] if initial_guess is None else initial_guess)
    if not np.isfinite(guess): raise ValueError('initial_guess must be finite')
    frequencies=[]; residuals=[]; evaluations=[]
    for k in ks:
        seed=guess/(np.sqrt(2)*k) if kind=='generalized' else guess
        def residual(parts):
            phase=complex(*parts)
            if kind in ('langmuir','generalized') and parameters.get('selector',0)==0 and parameters.get('expression','exp(-v.^2)/sqrt(pi)')=='exp(-v.^2)/sqrt(pi)':
                r=complex(evaluate_maxwellian_electrostatic(phase*np.sqrt(2)*k,k)['epsilon'])
            else: r=complex(evaluate_gpdf_residual(kind,phase,k,**parameters)/(k*k))
            return [r.real,r.imag]
        solved=root(residual,[seed.real,seed.imag],method='hybr',options={'xtol':1e-10,'maxfev':int(max_evaluations)})
        q=complex(*solved.x); norm=np.linalg.norm(residual(solved.x))
        if not solved.success or norm>residual_tolerance or solved.nfev>max_evaluations:
            raise RuntimeError(f'{kind} scan failed at k={k}: residual={norm}; {solved.message}')
        omega=q*np.sqrt(2)*k
        frequencies.append(omega); residuals.append(norm); evaluations.append(solved.nfev)
        if kind in ('iaw','beam'): guess=q
        elif kind=='generalized': guess=omega
    return {'k':ks,'omega':np.asarray(frequencies),'dielectric_residual':np.asarray(residuals),'evaluations':np.asarray(evaluations)}


__all__=['DensityExpression','evaluate_generalized_hilbert','evaluate_generalized_dispersion','evaluate_gpdf_residual','evaluate_gpdf_small_k','scan_gpdf_roots']
