"""Private D2 proposal: descriptor for a finite-harmonic rational Harris relation.

D(omega)=a+sum_l residues[l]/(omega-poles[l]). This independent elimination
corrects the finite-a scaling in frozen legacy PDRK ES3D; it does not establish
physical coefficient correctness, select modes, or import an original checkout.
Provenance/derivation and pending gates: ../DERIVATION_AND_NEXT_STEPS.md.
No eigenvalue solver or source programs run in this construction.
"""
import numpy as np


def rational_frequency_descriptor(*, constant, poles, residues):
    """Construct A*x=omega*H*x with x=(auxiliary amplitudes, field).

    Inputs use one consistent frequency unit: poles and residues have that unit;
    constant is dimensionless. Both vectors share a nonempty one-dimensional
    axis. Complex coefficients are supported. a=0 is retained without division.
    Output includes the algebraic field row, so infinite/constraint modes must
    be diagnosed by the subsequent generalized eigensolver and rational residual.
    No filtering or physical mode certification is performed here.
    """
    a=np.asarray(constant)
    c=np.asarray(poles)
    b=np.asarray(residues)
    if a.shape!=() or c.ndim!=1 or c.size==0 or b.shape!=c.shape:
        raise ValueError('constant must be scalar and poles/residues equal nonempty vectors')
    if any(v.dtype.kind not in 'iufc' for v in (a,c,b)):
        raise ValueError('coefficients must be finite numeric values')
    if not all(np.all(np.isfinite(v)) for v in (a,c,b)):
        raise ValueError('coefficients must be finite numeric values')
    a=complex(a); c=np.asarray(c,dtype=np.complex128); b=np.asarray(b,dtype=np.complex128)
    if not np.isfinite(a) or not np.isfinite(c).all() or not np.isfinite(b).all():
        raise ValueError('coefficients not representable in complex128')
    n=c.size
    A=np.zeros((n+1,n+1),dtype=np.complex128)
    H=np.zeros_like(A)
    A[:n,:n]=np.diag(c)
    A[:n,n]=-b
    A[n,:n]=1
    A[n,n]=-a
    H[:n,:n]=np.eye(n)
    return {'A':A,'H':H,'constant':a,'poles':c.copy(),'residues':b.copy(),
            'state_order':('auxiliary_pole_amplitudes','field'),
            'physical_root_filter':'NOT_PERFORMED'}
