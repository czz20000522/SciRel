"""Historical source parity is superseded only for proved defective branches.

The immutable original tests/source/checksums are retained in the continuation
receipt. This regression states the corrected non-floor behavior explicitly.
"""
import numpy as np
import pytest
from scirel.collisions import assemble_atomic_hydrogen_omega_frequencies as atomic
from scirel.collisions import assemble_molecular_hydrogen_omega_frequencies as molecular


@pytest.mark.parametrize('op,name',[(atomic,'H_P'),(molecular,'H2_P')])
def test_weak_nonzero_drift_is_not_floored(op,name):
    f=np.array([[[1.],[3.]]]);z=np.zeros_like(f);alpha=np.full_like(f,2e-8)
    r=op(f,np.array([4.]),alpha,z,np.zeros((2,2)),np.ones(1),np.ones(2),
         np.array([1.]),np.array([-1.,1.]),1.,np.array([.5-1e-8]),np.zeros(1))
    np.testing.assert_allclose(r['Omega_'+name],2e-8/(.5-(.5-1e-8)),rtol=1e-14,atol=0)
