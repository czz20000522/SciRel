"""Finite-N perpendicular Harris roots, nearest-pole offset representation.

Positive bi-Maxwellian species give D(x)=a-sum W/(x-p), x=omega²,
W>0,p>0,a>=1. A first midpoint test chooses the nearest endpoint chart;
weak roots near either pole are resolved without subtracting large frequencies.
Numerical brackets are not rigorous interval certificates. Independent gates
and root-owner admission are separate. No source/default grid is reduced.
"""
import numpy as np
import mpmath as mp


def solve_perpendicular_harris(*,alpha,rho,gyro,temperature_ratio,kx,N,source_pole_order=8,precision=80,frequency_scale=1.):
    arrays=[np.asarray(v) for v in (alpha,rho,gyro,temperature_ratio)]
    if any(v.ndim!=1 or v.shape!=arrays[0].shape or v.dtype.kind not in 'iuf' or not np.isfinite(v).all() for v in arrays) or arrays[0].size==0:
        raise ValueError('finite aligned species vectors required')
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        arrays=[np.asarray(v,dtype=np.float64) for v in arrays]
    if not all(np.isfinite(v).all() for v in arrays):raise ValueError('species values not representable in float64')
    if np.any(arrays[0]<=0) or np.any(arrays[3]<=0) or np.any(arrays[1]<=0) or np.any(arrays[2]==0):raise ValueError('alpha/rho/temperature ratio positive, gyro nonzero required')
    for v,name,minimum in [(N,'N',0),(source_pole_order,'source_pole_order',1),(precision,'precision',32)]:
        if isinstance(v,(bool,np.bool_)) or int(v)!=v or v<minimum:raise ValueError(name+' integer outside declared domain')
    if not np.isfinite(kx) or kx==0 or not np.isfinite(frequency_scale) or frequency_scale<=0:raise ValueError('finite nonzero kx and positive frequency_scale required')
    N=int(N);J=int(source_pole_order);digits=int(precision)
    with mp.workdps(digits):
        a=mp.mpf(1);groups={};source_groups={}
        for aa,rr,gg,ll in zip(*arrays):
            aa,rr,gg,ll=[mp.mpf(float(v)) for v in (aa,rr,gg,ll)]
            b=(mp.mpf(float(kx))*rr)**2
            gammas=[mp.exp(-b)*mp.besseli(n,b) for n in range(N+1)]
            a+=aa*(1-gammas[0]-2*sum(gammas[1:]))
            for n in range(-N,N+1):source_groups[n*gg]=source_groups.get(n*gg,0)+J
            for n in range(1,N+1):
                p=(n*gg)**2;groups[p]=groups.get(p,mp.mpf(0))+2*aa*gammas[n]*ll*p
        if a<=0:raise ArithmeticError('positive finite-Harris closure violated')
        poles=sorted(groups);weights=[groups[p] for p in poles]
        if any(w<=0 for w in weights):raise ArithmeticError('positive interlacing weight violated')
        target=mp.power(10,-digits//2);roots=[]
        for i,p in enumerate(poles):
            center=i;lo=mp.mpf(0);hi=poles[i+1]-p if i+1<len(poles) else sum(weights)/a+1
            def evaluate(center,delta):
                # Critical denominator is delta itself, including upper-pole chart.
                terms=[W/delta if j==center else W/(poles[center]-pp+delta) for j,(pp,W) in enumerate(zip(poles,weights))]
                return a-sum(terms),terms
            if i+1<len(poles):
                half=hi/2;D,_=evaluate(i,half)
                if D<0:center=i+1;lo=-half;hi=mp.mpf(0)
                else:hi=half
            minweight=min(weights[i:i+2]) if i+1<len(poles) else weights[i]
            maxiter=max(1000,8*digits+4*int(abs(mp.log10(minweight/a)))+128)
            for iteration in range(maxiter):
                mid=(lo+hi)/2;D,terms=evaluate(center,mid)
                if D>0:hi=mid
                else:lo=mid
                if hi-lo<=target*abs(mid):break
            else:raise ArithmeticError('nearest-pole root bracket did not converge')
            delta=(lo+hi)/2;D,terms=evaluate(center,delta);res=abs(D)/(abs(a)+sum(abs(x) for x in terms))
            if res>4*target:raise ArithmeticError('offset-coordinate rational residual failed')
            base=mp.sqrt(poles[center]);offset=delta/(mp.sqrt(poles[center]+delta)+base)
            roots.append(dict(interval=i,reference=center,delta=delta,base=base,offset=offset,residual=res,bracket=(lo,hi)))
        modes=[];scale=mp.mpf(float(frequency_scale))
        for sign in [-1,1]:
            for index,r in enumerate(roots):
                base=sign*r['base'];off=sign*r['offset'];modes.append(dict(sign=sign,index=index,root=r,base=base,offset=off,
                    published_base=base/scale,published_offset=off/scale,rounded=float(base+off),published_rounded=float(base/scale+off/scale)))
        modes.sort(key=lambda m:m['rounded']) # stable deterministic tie-break, all physical Im omega=0
        if any(not np.isfinite([m['rounded'],m['published_rounded']]).all() for m in modes):raise FloatingPointError('frequency midpoint not representable')
        strings=lambda xs:[mp.nstr(x,digits) for x in xs]
        rawcount=len(arrays[0])*(2*N+1)*J;physicalcount=2*len(poles);zerocount=source_groups.get(mp.mpf(0),0)
        result={'omega':np.asarray([m['rounded'] for m in modes],complex),'w':np.asarray([m['rounded'] for m in modes],complex),
            'frequency_base':np.asarray([float(m['base']) for m in modes]),'frequency_offset':np.asarray([float(m['offset']) for m in modes]),
            'frequency_base_decimal':strings([m['base'] for m in modes]),'frequency_offset_decimal':strings([m['offset'] for m in modes]),
            'published_omega':np.asarray([m['published_rounded'] for m in modes],complex),
            'published_frequency_base_decimal':strings([m['published_base'] for m in modes]),'published_frequency_offset_decimal':strings([m['published_offset'] for m in modes]),
            'frequency_scale_decimal':mp.nstr(scale,digits),'pole_square_decimal':strings(poles),'weights_decimal':strings(weights),'constant_decimal':mp.nstr(a,digits),
            'root_interval_index':[m['root']['interval'] for m in modes],'reference_pole_index':[m['root']['reference'] for m in modes],'root_sign':[m['sign'] for m in modes],
            'square_offset_decimal':strings([m['root']['delta'] for m in modes]),'shift_chart_residual_decimal':strings([m['root']['residual'] for m in modes]),
            'root_brackets_delta_decimal':[[mp.nstr(x,digits) for x in m['root']['bracket']] for m in modes],
            'precision_digits':digits,'N':N,'source_pole_order':J,'mode_count':physicalcount,
            'classification':'PERPENDICULAR_INTERLACING_NEAREST_POLE_OFFSET_CARRIER',
            'mode_classification':{'source_auxiliary_modes':rawcount,'physical_finite_simple_modes':physicalcount,'physical_zero_frequency_modes':0,
                'zero_residue_source_pole_aliases':zerocount,'repeated_nonzero_source_pole_aliases':rawcount-zerocount-physicalcount,
                'total_canceled_source_auxiliary_modes':rawcount-physicalcount,'associated_descriptor_infinite_constraint_modes':1,
                'associated_descriptor_constructed':False,'source_pole_groups':[{'frequency_decimal':mp.nstr(p,digits),'multiplicity':count,'physical_pole':p!=0} for p,count in sorted(source_groups.items())]},
            'precision_limit':'Canonical/published omega are binary64 rounded midpoints. Decimal nearest-base+signed-offset pairs retain sub-ulp displacement and are separately normalized before rounding; numerical brackets not rigorous intervals.'}
        return result
