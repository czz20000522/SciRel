import numpy as np
from scirel.equilibrium import compute_equilibrium

def test_descending_axes_preserve_pressure_solution_and_order():
 R,Z=np.meshgrid(np.linspace(0,1.2,7),np.linspace(-1,1,5))
 vac=R**2/2
 G=np.full((R.size,R.size),1e-5)
 p=lambda r: (1-(r/.8)**2)**2 if r < .8 else 0.
 a=compute_equilibrium(R,Z,p,vac,G,maxiter=100)
 assert a.status=='converged'
 perm=np.arange(R.size).reshape(R.shape)[::-1,::-1].ravel()
 b=compute_equilibrium(R[::-1,::-1],Z[::-1,::-1],p,vac[::-1,::-1],G[np.ix_(perm,perm)],maxiter=100)
 assert b.status=='converged'
 np.testing.assert_allclose(b.psi,a.psi[::-1,::-1],rtol=1e-12,atol=1e-15)
 np.testing.assert_allclose(b.plas_currents,a.plas_currents[::-1,::-1],rtol=1e-12,atol=1e-15)
