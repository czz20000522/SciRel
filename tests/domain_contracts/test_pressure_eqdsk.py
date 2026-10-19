"""Explicit SI pressure profiles over the retained equilibrium exchange dialect."""
import numpy as np
import pytest
from scirel.equilibrium import compute_equilibrium
from scirel.io import write_pressure_equilibrium_eqdsk, read_eqdsk


def test_pressure_terminal_and_profile_round_trip(tmp_path):
    # Dyadic nodes include the exact zero edge R=1: the fitted relation is
    # then the declared quadratic in psi, without an extra zero knot beyond
    # a rounded decimal edge (which changes the finite spline relation).
    R,Z=np.meshgrid(np.linspace(0,1.5,13),np.linspace(-1,1,11))
    pressure=lambda r: (1-r**2)**2 if r<1. else 0.
    state=compute_equilibrium(R,Z,pressure,R**2/2,np.zeros((R.size,R.size)))
    assert state.status=='converged'
    path=tmp_path/'pressure.eqdsk'
    axis=write_pressure_equilibrium_eqdsk(R,Z,state,path,'pressure')
    loaded=read_eqdsk(path)
    # P(R(psi))=(1-2psi)² within this analytic pressure region.
    expected=(1-2*axis)**2
    prime=-4*(1-2*axis)
    np.testing.assert_allclose(loaded['p_flux'],expected,rtol=2e-8,atol=1e-12)
    np.testing.assert_allclose(loaded['pprime_flux'],prime,rtol=2e-8,atol=1e-12)
    np.testing.assert_allclose(loaded['psi'],state.psi,rtol=2e-8,atol=1e-12)
    np.testing.assert_allclose(loaded['Ip'],state.plas_currents.sum(),rtol=2e-8,atol=1e-12)


def test_nonconverged_state_is_rejected_before_output(tmp_path):
    R,Z=np.meshgrid(np.linspace(0,1.2,13),np.linspace(-1,1,11))
    state=compute_equilibrium(R,Z,lambda r: max(1-r,0),R**2/2,
                              np.zeros((R.size,R.size)),maxiter=0)
    path=tmp_path/'invalid.eqdsk'
    with pytest.raises(ValueError,match='converged'):
        write_pressure_equilibrium_eqdsk(R,Z,state,path,'invalid')
    assert not path.exists()


def test_mismatched_or_missing_midplane_grid_is_rejected(tmp_path):
    R,Z=np.meshgrid(np.linspace(0,1.5,13),np.linspace(-1,1,11))
    state=compute_equilibrium(R,Z,lambda r: (1-r*r)**2 if r<1 else 0.,
                              R**2/2,np.zeros((R.size,R.size)))
    for rr,zz in [(R[:,:-1],Z[:,:-1]),(R,Z+.01)]:
        path=tmp_path/'invalid.eqdsk'
        with pytest.raises(ValueError):
            write_pressure_equilibrium_eqdsk(rr,zz,state,path,'invalid')
        assert not path.exists()
