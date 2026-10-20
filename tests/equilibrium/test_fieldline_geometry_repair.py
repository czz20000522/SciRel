import numpy as np
import pytest
from scirel.geometry.fieldline import FieldLine,HelperFieldLine,Boundary

@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
def test_intersection_transverse_endpoint_and_nonintersection(klass):
    line=klass(0,np.column_stack((np.linspace(1,3,9),np.zeros(9))))
    for r,expected in [(1.,0.),(1.6,.3),(3.,1.)]:
        bound=Boundary(np.column_stack((np.full(7,r),np.linspace(-1,1,7))))
        assert abs(line.intersection(bound)-expected)<1e-8
    separated=Boundary(np.column_stack((np.linspace(1,3,7),np.ones(7))))
    with pytest.raises(ValueError,match='intersection|crossing'):line.intersection(separated)
    with pytest.raises(ValueError,match='intersection|crossing'):
        line.apply_boundary(Boundary(np.column_stack((np.full(7,1.6),np.linspace(-1,1,7)))),separated)
    assert not hasattr(line,'ubound0') and not hasattr(line,'ubound1')

@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
def test_ordered_open_line_has_no_cyclic_interior_jump(klass):
    # Supplied order is an open smooth arc with an internal minimum R.
    t=np.linspace(-.9,.9,31);p=np.column_stack((1+t*t,t))
    obj=klass(0,p)
    np.testing.assert_allclose(obj.verts[[0,-1]],p[[0,-1]],rtol=0,atol=1e-12)
    assert np.max(np.linalg.norm(np.diff(obj.verts,axis=0),axis=1))<.02

@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
def test_boundary_state_recovery_and_multiple_crossing_failure(klass):
    line=klass(0,np.column_stack((np.linspace(1,3,9),np.zeros(9))))
    vertical=lambda r:Boundary(np.column_stack((np.full(7,r),np.linspace(-1,1,7))))
    line.apply_boundary(vertical(1.4),vertical(2.4))
    np.testing.assert_allclose(line.get_bounded_fl(13),[np.linspace(1.4,2.4,13),np.zeros(13)],rtol=0,atol=1e-10)
    previous=(line.ubound0,line.ubound1)
    with pytest.raises(ValueError):
        line.apply_boundary(vertical(1.8),Boundary(np.column_stack((np.linspace(1,3,7),np.ones(7)))))
    assert (line.ubound0,line.ubound1)==previous
    curve_x=np.linspace(1,3,11)
    crossing=Boundary(np.column_stack((curve_x,(curve_x-1.5)*(curve_x-2.5))))
    with pytest.raises(ValueError,match='multiple'):line.intersection(crossing)


def test_distinct_constructor_and_curvature_return_contracts():
    from types import SimpleNamespace
    from scirel.geometry.fieldline import FieldLineSet,contour_points,helper_contour_points
    p=np.column_stack((np.linspace(1,2,7),np.linspace(-.4,.6,7)))
    contour=SimpleNamespace(levels=[.7],allsegs=[[p]])
    assert FieldLineSet(contour,npts=73).flset[.7][0].verts.shape==(73,2)
    assert contour_points(contour)[.7][0].verts.shape==(1000,2)
    assert helper_contour_points(contour)[.7][0].verts.shape==(1000,2)

@pytest.mark.parametrize('kind',['axis','constant','irregular','nonfinite','complex','wrong-shape'])
def test_flux_gradient_curvature_rejects_undefined_or_nonuniform_support(kind):
    r,z=np.meshgrid([1.,2.,3.],[-1.,0.,1.]);psi=.5*((r-2)**2+z*z)
    line=FieldLine.__new__(FieldLine);line.verts=np.array([[1.4,.3],[1.5,.4],[1.6,.5]])
    if kind=='constant':psi=np.ones_like(r)
    elif kind=='irregular':r[:,1]=1.7;psi=.5*((r-2)**2+z*z)
    elif kind=='nonfinite':psi[0,0]=np.nan
    elif kind=='complex':psi=psi.astype(complex)+1j
    elif kind=='wrong-shape':psi=psi[:,:2]
    with pytest.raises(ValueError):line.get_kappa_n_2(r,z,psi)


def test_flux_gradient_curvature_rejects_outside_query_support():
    r,z=np.meshgrid(np.linspace(1,3,8),np.linspace(-1,1,8));psi=.5*((r-2)**2+z*z)
    line=FieldLine.__new__(FieldLine);line.verts=np.array([[3.4,.3],[3.5,.4],[3.6,.5]])
    with pytest.raises(ValueError,match='support'):line.get_kappa_n_2(r,z,psi)
