"""Independent integral gates for repaired actual-coordinate loop matrix."""
import numpy as np
import pytest
from scipy.integrate import quad
from scirel.electromagnetism.greens import _psi_matrix, compute_greens, get_gpsi


def reference(R, Z):
    points=np.column_stack((R.ravel(),Z.ravel()))
    out=np.zeros((len(points),len(points)))
    for i,(r,z) in enumerate(points):
        for j,(a,z0) in enumerate(points):
            if r==0 or a==0 or i==j:continue
            out[i,j]=1e-7*a*r*quad(lambda phi:np.cos(phi)/np.sqrt((r-a)**2+4*r*a*np.sin(phi/2)**2+(z-z0)**2),0,2*np.pi,epsabs=1e-12,epsrel=1e-12)[0]
    return out


def scalar_kernel_reference(R, Z):
    """Reference the pre-batched per-source assembly through compute_greens."""
    points = np.column_stack((R.ravel(), Z.ravel()))
    out = np.zeros((len(points), len(points)))
    for j, (a, z0) in enumerate(points):
        if a == 0.0:
            continue
        off_self = np.arange(len(points)) != j
        out[off_self, j] = compute_greens(
            np.array([[a, z0, 1.0]]), points[off_self]
        )[0]
    return out

@pytest.mark.parametrize('z',[[-.5,0,.5],[-.5,0,.9]])
def test_original_grid_against_loop_integral(z):
    R,Z=np.meshgrid([.4,.8,1.2],z)
    np.testing.assert_allclose(get_gpsi(R,Z),reference(R,Z),rtol=1e-12,atol=1e-18)


def test_asymmetric_heldout_actual_coordinates_and_order():
    R=np.array([[.21,.67,1.04,1.83],[.26,.73,1.17,1.92],[.38,.81,1.24,2.05]])
    Z=np.array([[-.83,-.78,-.76,-.69],[-.11,.02,.07,.19],[.54,.71,.89,1.07]])
    got=get_gpsi(R,Z)
    np.testing.assert_allclose(got,reference(R,Z),rtol=1e-10,atol=1e-17)
    np.testing.assert_allclose(got,got.T,rtol=1e-12,atol=1e-18)
    permutation=np.array([9,1,6,3,10,0,5,11,2,4,8,7])
    perm=get_gpsi(R.ravel()[permutation].reshape(3,4),Z.ravel()[permutation].reshape(3,4))
    np.testing.assert_allclose(perm,got[np.ix_(permutation,permutation)],rtol=0,atol=1e-22)
    assert np.all(np.diag(got)==0)


def test_batched_source_blocks_are_bitwise_equal_to_scalar_kernel():
    ratio = 3.0 - 2.0 * np.sqrt(2.0)
    half_m_height = np.sqrt(7.0) / 2.0
    R = np.array([[0.0, 1.0, 0.5, ratio, np.nextafter(ratio, 0.0)],
                  [0.35, 1.7, 0.71, 1.23, 1.41]])
    Z = np.array([[0.0, 0.0, half_m_height, 0.0, 0.0],
                  [-0.4, 0.6, 0.2, 1.1, -0.8]])
    expected = scalar_kernel_reference(R, Z)
    np.testing.assert_array_equal(get_gpsi(R, Z), expected)

    points = np.column_stack((R.ravel(), Z.ravel()))
    active = points[:, 0] > 0.0
    np.testing.assert_array_equal(
        _psi_matrix(points, max_pairs=3), expected[:, active]
    )


def test_axis_zero_self_duplicate_and_failure_contract():
    R,Z=np.meshgrid([0,.4,.9],[-.3,.8])
    got=get_gpsi(R,Z)
    np.testing.assert_array_equal(got[:,[0,3]],0)
    np.testing.assert_array_equal(got[[0,3]],0)
    for r,z in [(R,Z[:,:2]),(-R,Z),(R,np.full_like(Z,np.nan))]:
        with pytest.raises(ValueError):get_gpsi(r,z)
    with pytest.raises(ValueError):get_gpsi(np.array([[.4,.4]]),np.array([[.3,.3]]))


def test_warning_policy_unchanged():
    import warnings
    R,Z=np.meshgrid([.4,.8,1.2],[-.5,0,.9])
    with warnings.catch_warnings():
        warnings.simplefilter('default')
        original=list(warnings.filters)
        get_gpsi(R,Z)
        assert warnings.filters==original

@pytest.mark.parametrize('coordinate',['R','Z'])
def test_complex_coordinates_rejected_without_discarding_imaginary_part(coordinate):
    R,Z=np.meshgrid([.4,.8],[-.3,.7])
    if coordinate=='R':R=R.astype(complex)+1j
    else:Z=Z.astype(complex)+1j
    with pytest.raises(ValueError,match='real'):get_gpsi(R,Z)
