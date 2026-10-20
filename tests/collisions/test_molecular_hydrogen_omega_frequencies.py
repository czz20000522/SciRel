"""Regression for the former molecular zero-accumulator raw-moment error."""
import numpy as np
from scirel.collisions import assemble_molecular_hydrogen_omega_frequencies as op


def test_molecular_default_is_central_and_boost_invariant():
    f=np.array([[[1.],[3.]]]);z=np.zeros_like(f)
    def run(boost):
        return op(f,np.array([4.]),z,z,np.zeros((2,2)),np.ones(1),np.ones(2),
                  np.array([1.]),np.array([-1.,1.])+boost,1.,np.array([boost]),np.array([boost]),
                  H2_P_EL=False,H2_H_EL=False)
    a=run(0);b=run(.25)
    np.testing.assert_array_equal(a['Wperp_paraH2'],[-.5])
    np.testing.assert_array_equal(a['Wperp_paraH2'],b['Wperp_paraH2'])
