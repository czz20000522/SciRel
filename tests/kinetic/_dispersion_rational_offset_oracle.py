"""Independent ordinary-J Laguerre coefficients and Decimal pole-shift residual.

No candidate coefficient/evaluator import. Canonical gyro squares use exact
binary64 inputs interpreted as real numbers in independent Decimal arithmetic.
Closure deficit uses the positive infinite-Bessel tail, avoiding cancellation
of1 against a finite sum. Additional32/64 tail orders are separately checked.
Every active weak coefficient must resolve relatively, never against scale1.
"""
from decimal import Decimal,localcontext
import numpy as np
from scipy.special import roots_laguerre,jv
D=Decimal.from_float


def coefficients(args,order,extra=64):
    u,w=roots_laguerre(order);N=int(args['N'])
    with localcontext() as ctx:
        ctx.prec=180;a=Decimal(1);groups={}
        for alpha,rho,gyro,lam in zip(args['alpha'],args['rho'],args['gyro'],args['temperature_ratio']):
            arg=np.sqrt(2)*args['kx']*float(rho)*np.sqrt(u)
            gammas=(jv(np.arange(N+extra+1)[:,None],arg[None,:])**2)@w
            aa=D(float(alpha));ll=D(float(lam));gg=D(float(gyro))
            a+=2*aa*sum((D(float(v)) for v in gammas[N+1:]),Decimal(0))
            for n in range(1,N+1):
                pole=(Decimal(n)*gg)**2;weight=2*aa*D(float(gammas[n]))*ll*pole
                if not np.isfinite(gammas[n]) or gammas[n]<=0:raise ArithmeticError('weak coefficient quadrature unresolved/nonpositive')
                groups[pole]=groups.get(pole,Decimal(0))+weight
        return a,sorted(groups),[groups[p] for p in sorted(groups)]


def validate(args,result):
    with localcontext() as ctx:
        ctx.prec=180
        a64,p64,w64=coefficients(args,64);a96,p96,w96=coefficients(args,96);a32,pp,ww=coefficients(args,96,extra=32)
        assert p64==p96==pp
        weak=max((abs(x-y)/abs(y) for x,y in zip(w64,w96)),default=Decimal(0))
        closure=abs(a64-a96)/max(Decimal(1),abs(a96));tail=abs(a32-a96)/max(Decimal(1),abs(a96))
        assert weak<=Decimal('1e-8') and closure<=Decimal('1e-8') and tail<=Decimal('1e-10')
        candidate_p=[Decimal(x) for x in result['pole_square_decimal']]
        assert len(candidate_p)==len(p96)
        for x,y in zip(candidate_p,p96):assert abs(x-y)<=Decimal('1e-65')*max(Decimal(1),abs(y))
        residual=[];conversion=[];rounding=[]
        scale=Decimal(result['frequency_scale_decimal'])
        for i,(ref,off) in enumerate(zip(result['reference_pole_index'],result['square_offset_decimal'])):
            delta=Decimal(off);terms=[weight/(p96[ref]-p+delta) for p,weight in zip(p96,w96)]
            res=abs(a96-sum(terms))/(abs(a96)+sum(abs(t) for t in terms));residual.append(float(res));assert res<=Decimal('1e-8')
            base=Decimal(result['frequency_base_decimal'][i]);offset=Decimal(result['frequency_offset_decimal'][i]);pb=Decimal(result['published_frequency_base_decimal'][i]);po=Decimal(result['published_frequency_offset_decimal'][i])
            assert abs(pb*scale-base)<=Decimal('1e-60')*max(Decimal(1),abs(base))
            if offset:assert abs(po*scale-offset)/abs(offset)<=Decimal('1e-60')
            assert float(base+offset)==result['omega'][i].real
            assert float(pb+po)==result['published_omega'][i].real
            rounding.append(float(base)==result['omega'][i].real and offset!=0)
        return {'weak_coefficient64to96_relative':float(weak),'closure64to96':float(closure),'tail32to64':float(tail),'max_independent_offset_residual':max(residual,default=0.),'sub_ulp_modes':sum(rounding)}


def refinement(a,b):
    with localcontext() as ctx:
        ctx.prec=180;mapping={(s,i):j for j,(s,i) in enumerate(zip(b['root_sign'],b['root_interval_index']))};errors=[]
        for j,(sign,index) in enumerate(zip(a['root_sign'],a['root_interval_index'])):
            k=mapping[(sign,index)];pa=Decimal(a['pole_square_decimal'][a['reference_pole_index'][j]]);pb=Decimal(b['pole_square_decimal'][b['reference_pole_index'][k]])
            da=Decimal(a['square_offset_decimal'][j]);db=pb-pa+Decimal(b['square_offset_decimal'][k]);err=abs(da-db)/abs(db);errors.append(float(err));assert err<=Decimal('1e-30')
        return max(errors,default=0.)
