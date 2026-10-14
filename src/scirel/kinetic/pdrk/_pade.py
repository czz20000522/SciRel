"""Private precision-qualified successor proposal for source two-sided Padé system.

Exact source expansion/order and linear equations are preserved, with explicit
mpmath precision replacing the ill-conditioned binary64 coefficient solve.
Separate approximation, precision-refinement and simple-pole gates are required.
"""
import numpy as np
import mpmath as mp


def construct_maxwellian_pade(*,J,I,precision):
    for value,name in [(J,'J'),(I,'I'),(precision,'precision')]:
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,np.integer)):
            raise ValueError(name+' must be an integer')
    if J<1 or not 0<=I<=2*J or precision<32:
        raise ValueError('J>=1, 0<=I<=2J and precision>=32 required')
    with mp.workdps(int(precision)):
        J=int(J);I=int(I);K=2*J-I
        anp=[mp.mpc(0)]*(2*J+4);anm=anp.copy()
        for n in range(J+2):
            anp[2*n]=(-1)**n*mp.j*mp.sqrt(mp.pi)/mp.gamma(n+1)
            anp[2*n+1]=-(-1)**n*mp.gamma(mp.mpf('0.5'))/mp.gamma(n+mp.mpf('1.5'))
            anm[2*n+1]=-mp.gamma(n+mp.mpf('0.5'))/mp.gamma(mp.mpf('0.5'))
        A=mp.matrix(2*J);B=mp.matrix(2*J,1)
        for j in range(1,I+1):
            B[j-1]=anp[j-1]
            if j<=J:A[j-1,j-1]=1
            for k in range(1,j):
                if j<=J+k:A[j-1,J+j-k-1]=-anp[k-1]
        for j in range(1,K+1):
            if j<=J:A[I+j-1,J-j]=1
            for k in range(1,j+1):
                if j<2*J+k:A[I+j-1,2*J-j+k-1]=-anm[k]
            if j>J:B[I+j-1]=-anm[1]
        pq=mp.lu_solve(A,B)
        p=list(reversed([pq[i] for i in range(J)]))
        q=list(reversed([pq[J+i] for i in range(J)]))+[mp.mpf(1)]
        seed=np.roots(np.asarray([complex(v) for v in q]))
        derivative=[q[i]*(J-i) for i in range(J)]
        roots=[];root_errors=[]
        target=mp.power(10,-int(precision)+10)
        for value in seed:
            z=mp.mpc(float(value.real),float(value.imag))
            for iteration in range(100):
                f=mp.polyval(q,z);df=mp.polyval(derivative,z)
                if df==0:raise ArithmeticError('repeated or unresolved polynomial root requires higher-order-pole contract')
                step=f/df;z-=step
                if abs(step)<=target*max(1,abs(z)):break
            else:raise ArithmeticError('high-precision Padé root refinement did not converge')
            error=abs(mp.polyval(q,z))/max(1,sum(abs(co)*max(1,abs(z))**(J-i) for i,co in enumerate(q)))
            if error>target:raise ArithmeticError('Padé root polynomial residual exceeds declared precision')
            roots.append(z);root_errors.append(error)
        for i,z in enumerate(roots):
            if any(abs(z-zz)<=mp.sqrt(target)*max(1,abs(z)) for zz in roots[:i]):
                raise ArithmeticError('root refinement collapsed distinct seeds; simple-pole representation unresolved')
        residues=[mp.polyval(p,z)/mp.polyval(derivative,z) for z in roots]
        linear=mp.norm(A*pq-B)/(mp.norm(A)*mp.norm(pq)+mp.norm(B))
        if linear>target:raise ArithmeticError('high-precision Padé linear residual exceeds declared precision')
        def arr(values):return np.asarray([complex(v) for v in values],complex)
        b,c=arr(residues),arr(roots)
        if not np.isfinite(b).all() or not np.isfinite(c).all():raise FloatingPointError('Padé poles/residues not representable in binary64')
        return dict(J=J,I=I,K=K,precision_digits=int(precision),bzj=b,czj=c,
            p=arr(p),q=arr(q),pq=arr(pq),Mpq=np.asarray([[complex(A[i,j]) for j in range(2*J)] for i in range(2*J)]),B=arr(B),
            moments=np.asarray([sum(b),sum(b*c),sum(b*c*c)]),
            high_precision_linear_residual=mp.nstr(linear,int(precision)),
            high_precision_root_residual=[mp.nstr(v,int(precision)) for v in root_errors],
            high_precision_poles=[mp.nstr(v,int(precision)) for v in roots],
            high_precision_residues=[mp.nstr(v,int(precision)) for v in residues],
            precision_claim='coefficient/root construction at declared decimal precision; output numeric ports binary64; Z applicability separately qualified')
