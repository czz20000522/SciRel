"""Cauchy transform with explicit finite support/feature resolution.

The callback-only whole-line contract was unsound: adaptive QUADPACK can sample
zero outside a narrow shifted feature and report zero error. This successor
requires finite bounds, or an explicit increasing ``integration_mesh`` whose
panels resolve callback features. With no bounds the two infinite tails are
also integrated. For a general callback automatic support discovery is impossible.
"""
import warnings
import math
import numpy as np


def _mesh(value):
    if value is None:
        return None
    try:
        raw=np.asarray(value)
        objects=np.asarray(value,dtype=object)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('integration_mesh must be finite increasing real points') from exc
    if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in 'iuf' or any(isinstance(v,(bool,np.bool_)) for v in objects.flat):
        raise ValueError('integration_mesh must be finite increasing real points')
    try: arr=np.asarray(raw,dtype=float)
    except (TypeError,ValueError,OverflowError) as exc: raise ValueError('integration_mesh must be finite increasing real points') from exc
    if arr.ndim != 1 or arr.size < 2 or not np.all(np.isfinite(arr)) or np.any(np.diff(arr)<=0):
        raise ValueError('integration_mesh must be finite increasing points')
    return arr


def evaluate_cauchy_transform(z,density,*,bounds=None,analytic_density=None,epsabs=1e-10,epsrel=1e-10,limit=200,integration_mesh=None):
    """Return ``G(z)=integral density(v)/(v-z) dv`` and panel error estimates.

    ``density`` is a real scalar callback. ``bounds`` must be finite and
    ordered; if omitted, ``integration_mesh`` is required, and both infinite
    tails outside its endpoints are integrated. The caller must partition all
    material features into panels resolved by adaptive quadrature; there must
    be no unresolved features in the infinite tails. Finite bounds alone assert
    their interval is already resolved. Narrow features require explicit mesh
    panels containing their location and scale. This is an input condition,
    not a property that finitely many callback evaluations can certify.

    The known Cauchy kernel peak is resolved independently of the density mesh
    using v=Re(z)+abs(Im(z))*sinh(t) on near-projection finite panels. Both
    transformed components have bounded kernel factors, tanh(t) and sech(t);
    bounded t panels resolve their tails over widely separated scales. Smooth
    far panels and the two infinite tails use real-coordinate quadrature.

    Summed QUADPACK estimates plus floating accumulation allowances are
    conditional local error indicators, not global
    accuracy bounds, and exclude finite-domain truncation and callback error.
    Failure of any panel rejects the complete call. Im(z)<0 returns the real
    contour, or adds 2*pi*i*analytic_density(z) when that analytic extension is
    explicitly supplied. The extension must represent the same density, and
    for finite bounds continuation applies only across its interior support.
    """
    raw=np.asarray(z)
    if raw.dtype.kind not in 'iufc' or raw.size==0:
        raise ValueError('z must be a nonempty finite numeric array')
    values=np.asarray(raw,dtype=np.complex128)
    if not np.all(np.isfinite(values)) or np.any(values.imag==0):
        raise ValueError('z must be finite and off the real axis')
    if not callable(density) or (analytic_density is not None and not callable(analytic_density)):
        raise ValueError('density and supplied analytic_density must be callable')
    mesh=_mesh(integration_mesh)
    infinite_tails = bounds is None
    if bounds is None:
        if mesh is None:
            raise ValueError('finite bounds or integration_mesh is required for callback support resolution')
        a,b=-np.inf,np.inf
    else:
        try:
            raw_bounds=np.asarray(bounds)
            object_bounds=np.asarray(bounds,dtype=object)
            if raw_bounds.shape != (2,) or raw_bounds.dtype.kind not in 'iuf' or any(isinstance(v,(bool,np.bool_)) for v in object_bounds.flat):
                raise ValueError('bounds must be an ordered finite real pair')
            a,b=float(raw_bounds[0]),float(raw_bounds[1])
        except (TypeError,ValueError,OverflowError) as exc: raise ValueError('bounds must be an ordered finite real pair') from exc
        if not np.isfinite(a) or not np.isfinite(b) or a>=b:
            raise ValueError('bounds must be an ordered finite pair')
        if mesh is not None and (mesh[0] < a or mesh[-1] > b):
            raise ValueError('integration_mesh must lie within bounds')
    if mesh is None: mesh=np.array([a,b],dtype=float)
    elif infinite_tails:
        # Explicit mesh resolves the finite feature; tails complete (-inf,inf).
        mesh=np.asarray(mesh,dtype=float)
    elif abs(mesh[0]-a)>0 or abs(mesh[-1]-b)>0:
        mesh=np.concatenate(([a],mesh[(mesh>a)&(mesh<b)],[b]))
    for tolerance in (epsabs,epsrel):
        try: raw_tolerance=np.asarray(tolerance)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('epsabs and epsrel must be finite positive real numeric scalars') from exc
        if raw_tolerance.shape != () or raw_tolerance.dtype.kind not in 'iuf':
            raise ValueError('epsabs and epsrel must be finite positive real numeric scalars')
    try: epsabs,epsrel=float(epsabs),float(epsrel)
    except (TypeError,ValueError,OverflowError) as exc: raise ValueError('epsabs and epsrel must be finite positive scalars') from exc
    if not np.isfinite([epsabs,epsrel]).all() or epsabs<=0 or epsrel<=0:
        raise ValueError('epsabs and epsrel must be finite positive scalars')
    if isinstance(limit,(bool,np.bool_)) or not isinstance(limit,(int,np.integer)) or limit<1:
        raise ValueError('limit must be a positive integer')

    # Keep the numerical backend out of import-time and rejected-input paths.
    # SciPy remains a required runtime dependency for a valid quadrature call;
    # loading it here preserves the public function identity and all backend
    # warning/error semantics while keeping discovery and contract failures
    # dependency-light.
    from scipy.integrate import IntegrationWarning, quad

    G=np.empty(values.size,dtype=complex); errors=np.empty((values.size,2),dtype=float)
    for index,point in enumerate(values.flat):
        x,h=float(point.real),abs(float(point.imag))
        sign=math.copysign(1.,point.imag)
        logh=math.log(h)

        def sample(v):
            value=np.asarray(density(v))
            if value.shape!=() or value.dtype.kind not in 'iuf' or not np.isfinite(value):
                raise ValueError('density must return finite real numeric scalars')
            return float(value)

        def ordinary(v):
            return sample(v)/(v-point)

        def coordinate(v):
            delta=v-x
            if not math.isfinite(delta):
                raise ValueError('Cauchy coordinate difference is not representable')
            if delta == 0.:
                return 0.
            # Avoid forming an overflowing delta/h for subnormal pole heights.
            ratio_log=math.log(abs(delta))-logh
            if ratio_log > 20.:
                return math.copysign(ratio_log+math.log(2.),delta)
            return math.asinh(delta/h)

        def transformed(t):
            # v=x+h*sinh(t) gives dv/(v-z)=tanh(t)+i*sign(y)*sech(t).
            # Thus the known pole-height scale is removed from the kernel.
            # Evaluate h*sinh(t) without overflowing sinh for tiny h.
            at=abs(t)
            if at < 20.:
                offset=h*math.sinh(t)
            else:
                offset=math.copysign(math.exp(logh+at-math.log(2.))*(-math.expm1(-2.*at)),t)
            v=x+offset
            if not math.isfinite(v):
                raise ValueError('Cauchy integration coordinate is not representable')
            e=math.exp(-at)
            return sample(v)*complex(math.tanh(t),sign*2.*e/(1.+e*e))

        # Split at the pole projection even when the caller supplied no mesh
        # point there. Whole-line tails start away from the known kernel peak;
        # they retain the caller's separate density-feature precondition.
        edges=list(mesh)
        if infinite_tails:
            radius=max(1.,h,4.*abs(float(np.spacing(x))))
            extra=[x-radius,x,x+radius]
            if not all(math.isfinite(v) for v in extra):
                raise ValueError('Cauchy tail partition is not representable')
            edges.extend(extra)
        elif a < x < b:
            edges.append(x)
        edges=sorted(set(edges))
        panels=[]
        if infinite_tails:
            panels.append((ordinary,-np.inf,edges[0]))
            panels.append((ordinary,edges[-1],np.inf))
        for left,right in zip(edges[:-1],edges[1:]):
            distance=min(abs(left-x),abs(right-x)) if not left<=x<=right else 0.
            # Far from the projection, a panel narrower than half its distance
            # has no narrow kernel feature. Stay in v to avoid cancellation of
            # nearly equal asinh endpoints (e.g. z far outside finite bounds).
            if distance > 0. and right-left <= .5*distance:
                panels.append((ordinary,left,right))
                continue
            tl,tr=coordinate(left),coordinate(right)
            # A bounded t span resolves sech(t) and its cross-scale tails.
            # Merely adding x +/- h in v can still miss the long kernel tails.
            count=max(1,int(math.ceil((tr-tl)/2.)))
            cuts=np.linspace(tl,tr,count+1)
            panels.extend((transformed,float(l),float(r)) for l,r in zip(cuts[:-1],cuts[1:]))
        real_parts=[]; imag_parts=[]; real_errors=[]; imag_errors=[]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',IntegrationWarning)
                for function,left,right in panels:
                    re,er=quad(lambda v:function(v).real,left,right,epsabs=epsabs/len(panels),epsrel=epsrel,limit=int(limit))
                    im,ei=quad(lambda v:function(v).imag,left,right,epsabs=epsabs/len(panels),epsrel=epsrel,limit=int(limit))
                    real_parts.append(re); imag_parts.append(im)
                    real_errors.append(er); imag_errors.append(ei)
        except IntegrationWarning as exc:
            raise RuntimeError('Cauchy quadrature did not converge') from exc
        result=complex(math.fsum(real_parts),math.fsum(imag_parts))
        if point.imag<0 and analytic_density is not None and (infinite_tails or a < point.real < b):
            continuation=np.asarray(analytic_density(complex(point)))
            if continuation.shape!=() or continuation.dtype.kind not in 'iufc' or not np.isfinite(continuation):
                raise ValueError('analytic_density must return a finite numeric scalar')
            correction=2j*np.pi*complex(continuation)
            result+=correction
            real_parts.append(correction.real); imag_parts.append(correction.imag)
        # Component estimates propagate quadrature errors and a floating-point
        # accumulation allowance, including cancellation/continuation. Callback
        # and analytic-extension errors remain outside this conditional estimate.
        u=np.finfo(float).eps
        er_total=math.fsum(real_errors)+8*u*math.fsum(abs(v) for v in real_parts)
        ei_total=math.fsum(imag_errors)+8*u*math.fsum(abs(v) for v in imag_parts)
        if not np.isfinite(result) or not np.isfinite([er_total,ei_total]).all():
            raise ValueError('Cauchy transform is not representable')
        G[index],errors[index]=result,(er_total,ei_total)
    return {'G':G.reshape(values.shape),'quadrature_error':errors.reshape(values.shape+(2,))}

__all__=['evaluate_cauchy_transform']
