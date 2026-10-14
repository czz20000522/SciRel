"""Validated finite rational descriptor solver, source-independent."""
import numpy as np
from scipy.linalg import eig
from ._harris_descriptor import rational_frequency_descriptor

def solve_rational_frequency(*, constant, poles, residues):
    """Descriptor spectrum with explicit cancellation/infinity diagnostics.

    Exactly coincident poles are combined and exactly zero residue groups removed.
    No tolerance merges neighboring resonances. All generalized eigenpairs are
    returned; validated finite rational roots are a separately declared view.
    The residual metric compares cancellation to the sum of absolute terms, so it
    certifies the represented rational equation, not forward root accuracy.
    """
    p=rational_frequency_descriptor(constant=constant,poles=poles,residues=residues)
    groups={}
    for c,b in zip(p['poles'],p['residues']): groups[c]=groups.get(c,0j)+b
    kept=[(c,b) for c,b in groups.items() if b!=0]
    canceled=[c for c,b in groups.items() if b==0]
    if not kept:
        return dict(omega=np.empty(0,complex),all_finite=np.empty(0,complex),
            infinite_count=0,canceled_poles=np.asarray(canceled),
            rational_residual=np.empty(0),pencil_residual=np.empty(0),
            classification='IDENTICALLY_ZERO' if p['constant']==0 else 'NONZERO_CONSTANT_NO_ROOTS',
            constant=p['constant'],poles=np.empty(0,complex),residues=np.empty(0,complex))
    c=np.asarray([x[0] for x in kept]); b=np.asarray([x[1] for x in kept])
    p=rational_frequency_descriptor(constant=p['constant'],poles=c,residues=b)
    ab,V=eig(p['A'],p['H'],right=True,homogeneous_eigvals=True)
    alpha,beta=ab
    valid=beta!=0
    roots=alpha[valid]/beta[valid]
    norms=np.linalg.norm(p['A'],2)+abs(roots)*np.linalg.norm(p['H'],2)
    v=V[:,valid]
    pres=np.linalg.norm(p['A']@v-(p['H']@v)*roots,axis=0)/(norms*np.linalg.norm(v,axis=0))
    with np.errstate(divide='ignore',invalid='ignore'):
        terms=b[None,:]/(roots[:,None]-c[None,:])
        rres=abs(p['constant']+terms.sum(axis=1))/(abs(p['constant'])+abs(terms).sum(axis=1))
    accepted=np.isfinite(roots)&np.isfinite(rres)&(rres<=1e-8)&(pres<=max(1e-11,128*len(alpha)*np.finfo(float).eps))
    w=roots[accepted];w=w[np.argsort(-w.imag,kind='stable')]
    return dict(omega=w,all_finite=roots,accepted=accepted,infinite_count=int((~valid).sum()),
        canceled_poles=np.asarray(canceled),rational_residual=rres,pencil_residual=pres,
        classification='DESCRIPTOR_WITH_EXPLICIT_ROOT_QUALIFICATION',constant=p['constant'],poles=c,residues=b,
        alpha=alpha,beta=beta,A=p['A'],H=p['H'])

