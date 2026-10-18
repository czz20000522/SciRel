"""New bounded D2 independent analytic/consumer gates; source replay excluded."""
from types import SimpleNamespace
import inspect
import numpy as np
import pytest
from scipy.interpolate import CubicSpline as ReferenceSpline
from scirel.geometry import basis, fieldline, sampling, plotting
from scirel.geometry.numerics import diff_12_central, NumericalContractError
from matplotlib.patches import Rectangle
import os
if os.environ.get('ANALYSIS_SOURCE') == '1':
    import importlib.util
    import sys
    sys.path.insert(0,'/prior-delivery/artifact/source-bundle')
    spec=importlib.util.spec_from_file_location('source_helpers','/prior-delivery/artifact/source-bundle/pleiades/analysis/helpers.py')
    plotting=importlib.util.module_from_spec(spec);spec.loader.exec_module(plotting)


def test_natural_spline_boundary_continuity_and_reference():
    x=np.array([-.8,-.5,.1,.9,1.3,2.])
    y=np.cos(x)+x*x
    fit=basis.NaturalCubicSpline(x,y)
    ref=ReferenceSpline(x,y,bc_type='natural',extrapolate=False)
    q=np.linspace(x[0],x[-1],129)
    for d in range(3):
        np.testing.assert_allclose(fit(q,deriv=d),ref(q,nu=d),rtol=0,atol=8e-13)
    np.testing.assert_allclose(fit(x),y,rtol=0,atol=3e-15)
    np.testing.assert_allclose(fit(x[[0,-1]],deriv=2),[0,0],rtol=0,atol=3e-13)
    # Explicitly retained source extrapolation / derivative selector rules.
    for d in [0,1,2,3]:
        np.testing.assert_array_equal(fit(np.array([x[0]-1,x[-1]+1,np.nan]),deriv=d),[0,0,0])
    np.testing.assert_array_equal(fit(q,deriv=3),fit(q))


def test_natural_cubic_spline_public_docstring_declares_contract():
    doc = inspect.getdoc(basis.NaturalCubicSpline)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "deriv=1" in doc
    assert "outside the knot interval" in doc


def test_second_clamped_supported_origin_and_robin_residual():
    x=np.array([0.,.17,.5,1.1,1.8])
    y=np.array([0.,.2,.7,.3,.5])
    fit=basis.SecondClampedCubicSpline(x,y,m=3)
    k=np.asarray(fit.k).ravel();h=np.diff(x);dy=np.diff(y)
    upper=(2*k[:-1]+4*k[1:])/h-6*dy/h**2
    lower=6*dy/h**2-(4*k[:-1]+2*k[1:])/h
    np.testing.assert_allclose(upper[:-1],lower[1:],rtol=0,atol=5e-12)
    assert abs(lower[0])<5e-12
    assert abs(upper[-1]+k[-1]/x[-1]-9*y[-1]/x[-1]**2)<5e-12


def test_basis_factory_shapes_defaults_custom_columns_and_rejections():
    x=np.array([-.4,0.,.3,1.])
    obj=basis.BasisMatrix(''.join(['p','o','l','y']))
    assert obj.basis_dim == 3
    np.testing.assert_array_equal(obj(x),np.column_stack([x**0,x,x*x]))
    c=np.array([[1.,2.],[0.,-.3],[.2,0.]])
    custom=basis.BasisMatrix('poly',coeffs=c)
    np.testing.assert_allclose(custom(x),np.column_stack([1+.2*x*x,2-.3*x]),rtol=0,atol=2e-15)
    b=basis.BasisMatrix('natural_cubic_spline',n_knots=5)
    np.testing.assert_allclose(b(np.linspace(0,1,5)),np.eye(5),rtol=0,atol=2e-15)
    xd=np.column_stack([np.linspace(0,1,4),np.linspace(0,2,4)])
    fs=basis.build_basis('natural_cubic_spline',xdata=xd,ydata=np.column_stack([xd[:,0],2*xd[:,1]]))
    np.testing.assert_allclose(fs[0](np.array([.3,.7])),[.3,.7],rtol=0,atol=2e-14)
    np.testing.assert_allclose(fs[1](np.array([.3,.7])),[.6,1.4],rtol=0,atol=2e-14)
    with pytest.raises(NotImplementedError):basis.build_basis('quartic_spline')
    with pytest.raises(NotImplementedError):basis.build_basis('j0')
    with pytest.raises(KeyError):basis.build_basis('missing')
    with pytest.raises(TypeError, match='typo'):
        basis.build_basis('poly', typo=1)


def test_build_basis_public_docstring_declares_contract():
    doc = inspect.getdoc(basis.build_basis)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "poly" in doc
    assert "cubic" in doc


def test_basis_matrix_public_docstring_declares_contract():
    doc = inspect.getdoc(basis.BasisMatrix)
    assert doc is not None
    assert "Parameters" in doc
    assert "Attributes" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "basis_dim" in doc


def test_clamped_reference_and_spline_refinement():
    # Natural spline sin(pi*x) has its stated natural boundary at x=0,1.
    errors=[]
    q=np.linspace(0,1,501)
    for n in [9,17,33]:
        x=np.linspace(0,1,n)
        fit=basis.NaturalCubicSpline(x,np.sin(np.pi*x))
        errors.append(np.max(np.abs(fit(q)-np.sin(np.pi*q))))
    assert errors[1]<errors[0]/12
    assert errors[2]<errors[1]/12
    x=np.array([-.6,-.4,.2,.9,1.4]); y=np.cos(x)
    fit=basis.ClampedCubicSpline(x,y,yp=-np.sin(x[[0,-1]]))
    ref=ReferenceSpline(x,y,bc_type=((1,-np.sin(x[0])),(1,-np.sin(x[-1]))))
    q=np.linspace(x[0],x[-1],91)
    for d in [0,1,2]:np.testing.assert_allclose(fit(q,deriv=d),ref(q,nu=d),rtol=0,atol=2e-12)


def test_cubic_spline_vectorized_query_shapes_and_retained_selector_rules():
    x=np.array([-.6,-.4,.2,.9,1.4])
    y=np.cos(x)
    fit=basis.NaturalCubicSpline(x,y)
    q=np.array([[-1.,x[0],x[1],x[-1]],[2.,np.nan,.3,.9]])
    for deriv in [0,1,2,3]:
        got=fit(q,deriv=deriv)
        assert got.shape==q.shape
        np.testing.assert_array_equal(got[0,0],0.)
        np.testing.assert_array_equal(got[1,:2],[0.,0.])
        if deriv==0:
            np.testing.assert_allclose(got[0,1:],y[[0,1,-1]],rtol=0,atol=3e-15)
        elif deriv==3:
            np.testing.assert_array_equal(got,fit(q,deriv=0))
        np.testing.assert_allclose(got,np.asarray([fit(value,deriv=deriv) for value in q.ravel()]).reshape(q.shape),rtol=0,atol=0)


def test_numerics_manufactured_and_refinement_contract():
    x=np.array([-.7,-.5,-.11,.3,.8,1.4]);y=2*x*x-3*x+.1
    d1,d2=diff_12_central(x,y)
    np.testing.assert_allclose(d1,4*x[1:-1]-3,rtol=0,atol=3e-14)
    np.testing.assert_allclose(d2,np.full(len(x)-2,4),rtol=0,atol=3e-14)
    np.testing.assert_array_equal(sampling.diff_central(x,y),d1)
    errors=[]
    for n in [33,65,129]:
        x=np.linspace(0,1,n); d1,d2=diff_12_central(x,np.exp(x))
        errors.append(np.max(np.abs(d1-np.exp(x[1:-1]))))
    assert errors[1]<errors[0]/3.8
    assert errors[2]<errors[1]/3.8
    for x,y in [([0,0,1],[0,1,2]),([1,0,-1],[0,1,2]),([0,1,np.nan],[0,1,2]),([0,1],[0,1])]:
        with pytest.raises(NumericalContractError):diff_12_central(x,y)


def test_sampling_grid_interpolation_and_nearest_location_contracts():
    x,y=np.meshgrid(np.linspace(-1,1,7),np.linspace(-.8,.8,6))
    q=3*x-2*y+.4
    xx,yy,out=sampling.regular_grid(x,y,q,nx=8,ny=9)
    assert xx.shape==yy.shape==out.shape==(8,9)
    np.testing.assert_allclose(out,3*xx-2*yy+.4,rtol=0,atol=2e-14)
    xx,yy=np.meshgrid(np.linspace(-.9,.9,6),np.linspace(-.7,.7,5))
    got=sampling.regular_grid(x,y,q,xi=xx,yi=yy)[2]
    np.testing.assert_allclose(got,3*xx-2*yy+.4,rtol=0,atol=2e-14)
    p=np.array([[.2,.3],[-.5,-.4],[.6,-.2]])
    np.testing.assert_allclose(sampling.locs_to_vals_griddata(x,y,q,p),3*p[:,0]-2*p[:,1]+.4,rtol=0,atol=2e-14)
    np.testing.assert_allclose(sampling.interp(x,y,q,p),3*p[:,0]-2*p[:,1]+.4,rtol=0,atol=2e-14)
    exact=[(x[2,3],y[2,3]),(x[4,1],y[4,1])]
    np.testing.assert_array_equal(sampling.locs_to_vals(x,y,q,exact),[q[2,3],q[4,1]])
    np.testing.assert_array_equal(sampling.locs_to_vals1D(x,y,q,exact),[q[2,3],q[4,1]])


def test_regular_grid_public_docstring_declares_contract():
    doc = inspect.getdoc(sampling.regular_grid)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "values" in doc
    assert "method" in doc


def test_poly_fit_cutoff_and_underdetermined_minimum_norm():
    x=np.linspace(-1,1,17);y=.2-1.3*x+.7*x*x-.4*x**3
    f,c=sampling.poly_fit(x,y)
    np.testing.assert_allclose(c,[.2,-1.3,.7,-.4],rtol=0,atol=3e-14)
    np.testing.assert_allclose(sum(ci*fi(x) for ci,fi in zip(c,f)),y,rtol=0,atol=3e-14)
    # ±1 yields exact splitting between indistinguishable even/odd columns.
    _,c=sampling.poly_fit(np.array([-1.,1.]),np.array([2.,4.]),order=3)
    np.testing.assert_allclose(c,[1.5,.5,1.5,.5],rtol=0,atol=3e-14)
    _,c=sampling.poly_fit(np.array([0.,1e-12,2e-12]),np.ones(3),order=2)
    assert abs(c[0]-1)<3e-14
    assert abs(c[1])<3e-11
    assert abs(c[2])<3e-22


def test_poly_fit_public_docstring_declares_contract():
    doc = inspect.getdoc(sampling.poly_fit)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "ascending-power" in doc
    assert "1e-10" in doc


def test_reflection_is_scalar_even_and_endpoint_unique():
    r,z=np.meshgrid([0.,.3,.8],[-.4,.2])
    q=r*r+z
    rr,zz,qq=sampling.reflect_and_hstack(r,z,q)
    np.testing.assert_array_equal(rr[0],[-.8,-.3,0,.3,.8])
    np.testing.assert_allclose(qq,rr*rr+zz,rtol=0,atol=2e-15)
    with pytest.raises(AssertionError):sampling.reflect_and_hstack(r,z,q[:1])


def test_flux_weighted_integral_analytic_and_refinement():
    r,z=np.meshgrid(np.linspace(0,1,11),np.linspace(-.2,.2,9))
    b=1+r; q=r
    errors=[]
    for n in [33,65,129]:
        p=np.column_stack([np.linspace(0,1,n),np.zeros(n)])
        inv=sampling.flux_surface_avg(r,z,b,p)
        avg=sampling.flux_surface_avg(r,z,b,p,q)
        errors.append(abs(inv-np.log(2)))
        if n==129:
            assert abs(inv-np.log(2))<5e-6
            assert abs(avg-(1-np.log(2))/np.log(2))<1e-5
            assert abs(sampling.flux_surface_avg(r,z,b,p,3*np.ones_like(q))-3)<1e-13
    assert errors[1]<errors[0]/3.99
    assert errors[2]<errors[1]/3.99
    p=np.array([[0.,0.],[3.,0.],[3.,4.]])
    np.testing.assert_array_equal(sampling.get_fieldline_distance(p),[0,3,7])






def test_fieldline_geometry_shapes_selection_and_gradient():
    verts=np.column_stack([np.linspace(.2,1.2,9),np.zeros(9)])
    line=fieldline.FieldLine(.7,verts,npts=73)
    helper=fieldline.HelperFieldLine(.7,verts)
    assert line.verts.shape==(73,2); assert helper.verts.shape==(1000,2)
    assert abs(line.get_length()-1)<3e-14
    assert abs(helper.get_length()-1)<3e-14
    assert not line.is_closed(); assert not helper.is_closed()
    r,z=np.meshgrid(np.linspace(.1,1.3,13),np.linspace(-.2,.2,9))
    for obj in [line,helper]:
        grad_r,grad_z=obj.get_gradpsi(r,z,.3*np.ones_like(r),.8*np.ones_like(r))
        np.testing.assert_allclose(grad_r,.8*obj.verts[:,0],rtol=0,atol=4e-9)
        np.testing.assert_allclose(grad_z,-.3*obj.verts[:,0],rtol=0,atol=4e-9)
    contour=SimpleNamespace(levels=[.7],allsegs=[[verts]])
    assert isinstance(fieldline.contour_points(contour)[.7][0],fieldline.FieldLine)
    assert isinstance(fieldline.helper_contour_points(contour)[.7][0],fieldline.HelperFieldLine)
    assert isinstance(fieldline.FieldLineSet(contour,npts=37).flset[.7][0],fieldline.FieldLine)
    p=fieldline.Boundary(np.column_stack([np.linspace(0,1,6),np.linspace(0,1,6)]))
    np.testing.assert_allclose(p.interpolate([0,1]),[[0,1],[0,1]],rtol=0,atol=4e-14)


def test_closed_circle_flux_curvature_refinement():
    theta=np.linspace(0,2*np.pi,401)
    verts=np.column_stack([1.5+.4*np.cos(theta),.4*np.sin(theta)])
    errors=[]
    for n in [40,80,160]:
        r,z=np.meshgrid(np.linspace(.7,2.3,n),np.linspace(-.8,.8,n))
        psi=.5*((r-1.5)**2+z*z)
        obj=fieldline.FieldLine.__new__(fieldline.FieldLine); obj.verts=verts
        got=obj.get_kappa_n_2(r,z,psi,method='linear')
        expected=-np.column_stack([np.cos(theta),np.sin(theta)])/.4
        errors.append(np.max(np.linalg.norm(got-expected,axis=1)))
    assert errors[1]<errors[0]/3.4
    assert errors[2]<errors[1]/3.4
    assert errors[2]<.004


@pytest.mark.parametrize('operation',['mirror','scale','transpose'])
def test_affine_plotting_support_contracts(operation):
    p=Rectangle((.3,.4),.2,.1)
    v=np.array([[0,0],[1,1]])
    orig=p.get_transform().transform(v)
    if operation=='mirror':
        mirror=plotting.get_mirror_patches([p],axis=0,scale=2)[0]
        np.testing.assert_allclose(mirror.get_transform().transform(v),orig*np.array([2,-2]),rtol=0,atol=3e-15)
        np.testing.assert_array_equal(p.get_transform().transform(v),orig)
    elif operation=='scale':
        assert plotting.scale_patches([p],2)==[p]
        np.testing.assert_allclose(p.get_transform().transform(v),2*orig,rtol=0,atol=3e-15)
    else:
        assert plotting.transpose_patches([p]) is None
        np.testing.assert_allclose(p.get_transform().transform(v),orig[:,::-1],rtol=0,atol=3e-15)
