"""Proposed affected public tests; root executes after actual stable integration.

Independent analytic/Decimal relations are retained. These tests do not assert
that eigen backward error alone establishes physical correctness, or classify
source auxiliary aliases as waves. Private installed proofs are separate.
"""
from decimal import Decimal,localcontext
from pathlib import Path
import importlib.util
import json
import numpy as np
import pytest
import shutil
from scipy.special import wofz
from scirel.kinetic.pdrk import rational


pytestmark = pytest.mark.skipif(
    shutil.which("octave") is None,
    reason="PDRK rational contracts require GNU Octave",
)


def _schur(M,omega):
    M=M.toarray() if hasattr(M,'toarray') else np.asarray(M)
    na=len(M)-6;diag=np.diag(M[:na,:na])
    np.testing.assert_array_equal(M[:na,:na],np.diag(diag))
    Q=M[na:na+3,:na]@(M[:na,na:na+3]/(omega-diag)[:,None])
    return np.eye(3)-Q/omega


def _response_error(actual,expected):
    return max(np.max(abs(actual-expected)/np.maximum(1,abs(expected))),np.linalg.norm(actual-expected)/max(1,np.linalg.norm(expected)))


@pytest.mark.parametrize('N',[0,1,12])
@pytest.mark.parametrize('B0',[1e-7,-1e-7])
def test_uniform_k0_is_cold_gyro_response_including_N0(N,B0):
    # Unequal species eliminate accidental cancellation of the Hall component.
    deck=np.array([[1,1836,1e6,140,90,.0002],[-1,500,1e6,90,180,-.0001]])
    eq=rational.equilibrium('em',deck,B0=B0)['state'];tab=rational.pole_table('em',12)['state']
    q=deck[:,0]*1.6022e-19;m=deck[:,1]*9.1094e-31;g=B0*q/m;wp2=deck[:,2]*q*q/m/8.8542e-12;w=(2.2+3.1j)*max(abs(g))
    expected=np.eye(3,dtype=complex)
    for a,b in zip(wp2,g):
        expected[0,0]-=a/(w*w-b*b);expected[1,1]-=a/(w*w-b*b)
        expected[0,1]-=1j*a*b/(w*(w*w-b*b));expected[1,0]+=1j*a*b/(w*(w*w-b*b));expected[2,2]-=a/w**2
    point=rational.point_matrix('em',{**eq,**tab},kx=0,kz=0,N=N)['state']
    assert point['uniform_zero_k'] and point['harmonic_cutoff_ignored_at_zero_k']
    assert _response_error(_schur(point['M'],w),expected)<=1e-12
    solved=rational.solve_matrix(point['M'],model='em')
    assert max(solved['backward_residual'])<=1e-11
    assert 'not certified physical waves' in point['zero_frequency_modes']


@pytest.mark.parametrize('k',[.4,-.4])
def test_signed_es1d_causal_response_against_independent_Z(k):
    eq=rational.equilibrium('es1d',[[1,1,1,1,.17]])['state'];tab=rational.pole_table('es1d',12)['state'];before=tab['czj'].copy()
    point=rational.point_matrix('es1d',{**eq,**tab},k=k)['state'];w=1+2j;z=(w-k*.17)/(abs(k)*np.sqrt(2))
    expected=1+(1+z*1j*np.sqrt(np.pi)*wofz(z))/k**2
    actual=1+np.sum(np.asarray(point['bsj']).ravel()/(w-np.asarray(point['csj']).ravel()))
    assert abs(actual-expected)/max(1,abs(expected))<=5e-5
    np.testing.assert_array_equal(tab['czj'],before)


def test_descriptor_zero_constant_and_exact_cancellation_are_classified():
    zero=rational.solve_matrix({'constant':0,'poles':[1,2],'residues':[1,-2]},model='es3d')
    assert len(zero['omega'])==1 and abs(zero['omega'][0])<=1e-12
    assert zero['infinite_count']==2 and np.all(zero['accepted'])
    canceled=rational.solve_matrix({'constant':1,'poles':[1,1,2],'residues':[1,-1,1]},model='es3d')
    np.testing.assert_array_equal(canceled['canceled_poles'],[1]);assert len(canceled['omega'])==1
    assert max(canceled['rational_residual'])<=1e-8 and max(canceled['pencil_residual'])<=1e-11


def test_regenerated_j12_preserves_asymptotic_moments():
    for model in ['es1d','es3d','em']:
        p=rational.pole_table(model,12)['state'];b=np.asarray(p['bzj']).ravel();c=np.asarray(p['czj']).ravel()
        assert max(abs(sum(b)+1),abs(sum(b*c)),abs(sum(b*c*c)+.5))<=1e-10


def test_extended_finite_inputs_rejected_after_binary64_narrowing():
    wide=np.longdouble('1e400');tiny=np.longdouble('1e-400')
    assert np.isfinite(wide) and wide>np.finfo(float).max
    with pytest.raises(ValueError):rational.em_coordinates(wide,1)
    with pytest.raises(ValueError):rational.em_coordinates(1,tiny)
    with pytest.raises(ValueError):rational.equilibrium('es1d',np.array([[1,1,1,1,wide]],dtype=np.longdouble))
    complexwide=np.array(wide,dtype=np.clongdouble)[()];assert np.isfinite(complexwide)
    with pytest.raises(ValueError):rational.solve_matrix(np.eye(5),model='em',sp=1,nw=1,wg=complexwide)


def test_full_default_perpendicular_carrier_and_graph_projection(tmp_path):
    spec=importlib.util.spec_from_file_location('offset_oracle',Path(__file__).with_name('_pdrk_rational_offset_oracle.py'))
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    graph=rational.reassemble_original_program('es3d',tmp_path/'default',J=8,N=10,B0=1.)
    result=graph['result'];assert result['points'].shape==(50,2)
    # Native original loop controls are qualified separately; no Python arange reconstruction.
    assert np.all(result['points'][:,1]==0) and result['points'][0,0]==.05
    carriers=json.loads((tmp_path/'default/complete-frequency-carriers.json').read_text());assert len(carriers)==50
    for i,point in enumerate(result['spectra']):
        r=point['solution'];assert r['mode_count']==20
        m=r['mode_classification'];assert m['source_auxiliary_modes']==168 and m['total_canceled_source_auxiliary_modes']==148
        assert m['physical_zero_frequency_modes']==0 and m['associated_descriptor_infinite_constraint_modes']==1
        oracle.validate(point['matrix']['state']['perpendicular_inputs'],r)
        assert carriers[i]['frequency_offset_decimal']==r['frequency_offset_decimal']
    assert graph['artifacts']['plot_metadata']['visual_review']=='PENDING'
