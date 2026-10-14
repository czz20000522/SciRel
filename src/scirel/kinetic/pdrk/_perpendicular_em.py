"""Exact-perpendicular finite-harmonic Maxwell pencil, no source assembly imports.

Independent derivation: K=I-sum(wp²)/omega² I+sum R_p/[omega²(omega-p)].
Q=omega(I-K)=C0/omega+sum Cp/(omega-p), Cp=-R_p/p and
C0=sum(wp²)I-sum Cp. E/B remain the last six physical state entries.
Gaussian components may carry signed mixture weights, but caller owns whether
that mixture is a nonnegative physical distribution. No loss-cone guard is guessed.
"""
import numpy as np
from scipy.special import ive
from scipy import sparse


def perpendicular_maxwell_pencil(*,components,kx,N,c2):
    if not np.isfinite(kx) or int(N)!=N or N<0 or not np.isfinite(c2) or c2<=0:raise ValueError('finite kx,integer N>=0,positive c² required')
    terms={};totalwp2=0.
    for s in components:
        g,wp2,vtz,vtp,vd,weight=[float(s[k]) for k in ('gyro','wp2','vtz','vtp','drift','weight')]
        if not np.isfinite([g,wp2,vtz,vtp,vd,weight]).all() or g==0 or min(wp2,vtz,vtp)<=0:raise ValueError('finite physical Gaussian component required')
        totalwp2+=weight*wp2
        if kx==0:
            # Analytic uniform-field cold response: fundamental gyro poles are
            # necessary even when caller N=0; no harmonic cutoff approximation.
            for sign in [-1,1]:
                Cp=weight*wp2/2*np.array([[1,1j*sign,0],[-1j*sign,1,0],[0,0,0]],complex)
                pole=sign*g;terms[pole]=terms.get(pole,np.zeros((3,3),complex))+Cp
            continue
        b=(kx*vtp/g)**2/2
        for n in range(-int(N),int(N)+1):
            if n==0:continue
            gamma=ive(n,b);der=(ive(n-1,b)+ive(n+1,b)-2*gamma)/2
            xx=(n*g/kx)**2*gamma
            yy=vtp**2/2*(n*n*gamma/b-2*b*der)
            xy=1j*n*vtp**2/2*der
            xz=n*g/kx*gamma*vd
            yz=-1j*vd*kx*vtp**2/(2*g)*der
            zz=(vd*vd+vtz*vtz/2)*gamma
            T=np.array([[xx,xy,xz],[-xy,yy,yz],[xz,-yz,zz]],complex)
            Cp=weight*2*wp2/vtp**2*T
            pole=n*g;terms[pole]=terms.get(pole,np.zeros((3,3),complex))+Cp
    C0=totalwp2*np.eye(3)-sum(terms.values(),np.zeros((3,3),complex))
    terms={0.:C0,**terms};poles=list(terms);na=3*len(poles);dim=na+6
    M=sparse.lil_matrix((dim,dim),dtype=complex)
    for i,p in enumerate(poles):
        j=3*i;M[j:j+3,j:j+3]=p*np.eye(3);M[j:j+3,na:na+3]=-terms[p];M[na:na+3,j:j+3]=-np.eye(3)
    cross=np.array([[0.,0.,0.],[0.,0.,-kx],[0.,kx,0.]])
    M[na:na+3,na+3:]=-c2*cross;M[na+3:,na:na+3]=cross
    M=M.tocsc()
    if not np.isfinite(M.data).all():raise FloatingPointError('perpendicular pencil not representable')
    return {'M':M,'pole_frequencies':np.asarray(poles),'pole_blocks':np.asarray([terms[p] for p in poles]),'C0':C0,'totalwp2':totalwp2,'field_slice':(na,na+6),'state_convention':'three-current components per pole, then E3,B3; source G=-I convention','finite_N_constant':'full Maxwell plasma constant retained; no sumGamma=1 substitution','uniform_zero_k':kx==0,'harmonic_cutoff_ignored_at_zero_k':kx==0,'zero_frequency_modes':'constraint/static/auxiliary diagnostics, not certified physical waves'}
