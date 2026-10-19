"""Independent ordinary-Bessel quadrature axis oracles from Eq11/12."""
import numpy as np
from scipy.special import roots_laguerre,roots_hermite,jv
import _dispersion_oracle as io


def perpendicular(deck,B0,kx,omega,N,order):
    p=io.physical(deck,B0);u,wu=roots_laguerre(order);K=np.eye(3,dtype=complex)*(1-sum(p['wp2'])/omega**2)
    for s in range(len(p['q'])):
        for branch in range(2):
            r=p['weights'][branch,s]
            if r==0:continue
            vp=p['vtp'][s]*np.sqrt(1 if branch==0 else p['alpha'][s])*np.sqrt(u)
            vtp=p['vtp'][s]*np.sqrt(1 if branch==0 else p['alpha'][s]);g=p['gyro'][s];vd=p['vd'][s]
            for n in range(-N,N+1):
                if n==0:continue
                x=kx*vp/g;J=jv(n,x);D=(jv(n-1,x)-jv(n+1,x))/2;a=n*g/kx*J;b=vp*D
                def avg(v):return wu@v
                T=np.array([[avg(a*a),1j*avg(a*b),vd*avg(a*J)],[-1j*avg(a*b),avg(b*b),-1j*vd*avg(b*J)],[vd*avg(a*J),1j*vd*avg(b*J),(vd*vd+p['vtz'][s]**2/2)*avg(J*J)]])
                K+=r*p['wp2'][s]/omega**2*(-2*n*g/vtp**2)/(omega-n*g)*T
    return K


def parallel(deck,B0,kz,omega,order):
    p=io.physical(deck,B0);u,wu=roots_laguerre(order);x,wx=roots_hermite(order);weight=wu[:,None]*wx[None,:]/np.sqrt(np.pi);K=np.eye(3,dtype=complex)*(1-sum(p['wp2'])/omega**2)
    for s in range(len(p['q'])):
        vz=p['vd'][s]+p['vtz'][s]*x
        for branch in range(2):
            r=p['weights'][branch,s]
            if r==0:continue
            vtp=p['vtp'][s]*np.sqrt(1 if branch==0 else p['alpha'][s]);vp=vtp*np.sqrt(u)
            for n in [-1,0,1]:
                if n==0:a=b=np.zeros_like(vp);cc=np.broadcast_to(vz,(len(u),len(x)))
                else:a=vp/2;b=n*vp/2;cc=np.zeros((len(u),len(x)))
                den=omega-kz*vz[None,:]-n*p['gyro'][s];fac=-2*weight*(n*p['gyro'][s]/vtp**2+kz*x[None,:]/p['vtz'][s])/den
                def avg(v):return np.sum(fac*v)
                T=np.array([[avg(a[:,None]**2),avg(1j*a[:,None]*b[:,None]),avg(a[:,None]*cc)], [avg(-1j*a[:,None]*b[:,None]),avg(b[:,None]**2),avg(-1j*b[:,None]*cc)], [avg(a[:,None]*cc),avg(1j*b[:,None]*cc),avg(cc*cc)]])
                K+=r*p['wp2'][s]/omega**2*T
    return K
