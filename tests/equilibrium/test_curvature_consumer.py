"""End-to-end actual interpolation consumer: exact circular tangent field.

Frozen gate max component error2.5e-3 (radius0.7, 80x80 grid,257 linepoints).
No dependency monkeypatch: sampled B is normalized/interpolated by the class.
The original eight strict xfails become passing regressions only after the
corrected actual consumer passes this exact unchanged assertion. Original
failed observations remain evidence.160-grid cases retain the same tolerance.
"""
import numpy as np
import pytest
from scirel.geometry.fieldline import FieldLine, HelperFieldLine

@pytest.mark.parametrize('grid_n',[80,160])
@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
@pytest.mark.parametrize('reverse_vertices',[False,True])
@pytest.mark.parametrize('reverse_field',[False,True])
def test_actual_circular_field_curvature_consumer(klass,reverse_vertices,reverse_field,grid_n):
    theta=np.linspace(.23,2.5,257);a=.7
    p=np.column_stack([2.1+a*np.cos(theta),-.3+a*np.sin(theta)])
    expected=-np.column_stack([np.cos(theta),np.sin(theta)])/a
    if reverse_vertices:p=p[::-1];expected=expected[::-1]
    r,z=np.meshgrid(np.linspace(.95,3.25,grid_n),np.linspace(-1.45,.85,grid_n))
    br=-(z+.3);bz=r-2.1
    if reverse_field:br=-br;bz=-bz
    obj=klass.__new__(klass);obj.verts=p
    got=obj.get_kappa_n(r,z,br,bz)
    if klass is HelperFieldLine:got=np.column_stack(got)
    np.testing.assert_allclose(got,expected,rtol=0,atol=2.5e-3)

@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
@pytest.mark.parametrize('reverse_vertices',[False,True])
@pytest.mark.parametrize('reverse_field',[False,True])
def test_heldout_elliptic_affine_field_curvature(klass,reverse_vertices,reverse_field):
    theta=np.linspace(.17,2.37,321);a,b=.61,.93
    p=np.column_stack((1.87+a*np.cos(theta),.21+b*np.sin(theta)))
    v=np.column_stack((-a*np.sin(theta),b*np.cos(theta)))
    v2=np.column_stack((-a*np.cos(theta),-b*np.sin(theta)))
    speed2=np.sum(v*v,axis=1)
    expected=v2/speed2[:,None]-v*(np.sum(v*v2,axis=1)/speed2**2)[:,None]
    if reverse_vertices:p=p[::-1];expected=expected[::-1]
    r,z=np.meshgrid(np.linspace(.91,2.91,67),np.linspace(-.95,1.5,91))
    br=-(a/b)*(z-.21);bz=(b/a)*(r-1.87)
    if reverse_field:br=-br;bz=-bz
    obj=klass.__new__(klass);obj.verts=p
    got=obj.get_kappa_n(r,z,br,bz)
    if klass is HelperFieldLine:got=np.column_stack(got)
    np.testing.assert_allclose(got,expected,rtol=0,atol=2.5e-3)

@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
def test_curvature_refinement_and_null_outside_failure(klass):
    r,z=np.meshgrid(np.linspace(.95,3.25,80),np.linspace(-1.45,.85,80))
    errors=[]
    for n in [65,129,257]:
        t=np.linspace(.23,2.5,n);p=np.column_stack((2.1+.7*np.cos(t),-.3+.7*np.sin(t)))
        obj=klass.__new__(klass);obj.verts=p
        got=obj.get_kappa_n(r,z,-(z+.3),r-2.1)
        if klass is HelperFieldLine:got=np.column_stack(got)
        errors.append(np.max(np.abs(got+np.column_stack((np.cos(t),np.sin(t)))/.7)))
    assert errors[1]<errors[0]/3
    assert errors[2]<errors[1]/3
    with pytest.raises(ValueError,match='nonzero'):
        obj.get_kappa_n(r,z,np.zeros_like(r),np.zeros_like(z))
    obj.verts=np.array([[4.,.1],[4.1,.2],[4.2,.3]])
    with pytest.raises(ValueError,match='support'):
        obj.get_kappa_n(r,z,-(z+.3),r-2.1)

@pytest.mark.parametrize('klass',[FieldLine,HelperFieldLine])
def test_exact_sampled_field_null_has_no_curvature(klass):
    r,z=np.meshgrid(np.linspace(1,3,9),np.linspace(-1,1,9))
    obj=klass.__new__(klass);obj.verts=np.array([[1.9,0.],[2.,0.],[2.1,0.]])
    with pytest.raises(ValueError,match='nonzero'):
        obj.get_kappa_n(r,z,-z,r-2.)
