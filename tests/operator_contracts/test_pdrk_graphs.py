"""Public mapping TaskGraphs preserve physical mode state and field conventions."""
import json
from pathlib import Path
import numpy as np
from scirel.kinetic.pdrk import magnetized as m,workflows as g
import _pdrk_oracle as oracle

F=json.loads((Path(__file__).resolve().parents[1]/'pdrk-holdout-fixtures.json').read_text())['cases'][0]

def _scan():
    return g.solve_dispersion(dict(deck=np.asarray(F['deck']),controls=dict(B0=F['B0'],N=1,J=4,iem=1,iout=2,sp=0,ipa=3,ipb=3,pa1=.25,pa2=.45,dpa=.1),par=np.array([.25,0,.25,.07,0,0])))

def _verify(result):
    s=result.state;p=np.asarray(s['Pola']);E=p[...,:3];B=p[...,3:6];shape=E.shape[:-1]
    np.testing.assert_allclose(np.sum(abs(E)**2,axis=-1),1,rtol=0,atol=1e-12)
    np.testing.assert_allclose(p[...,6]/(oracle.EPS0/2),1,rtol=0,atol=1e-12)
    kv=np.stack([s['kxx'],np.zeros_like(s['kxx']),s['kzz']],axis=-1)[:,:,None,:];w=np.asarray(s['wws2']).reshape(shape)*s['wcs1'].item()
    residual=np.linalg.norm(np.cross(kv,E)-w[...,None]*B,axis=-1)/(np.linalg.norm(kv,axis=-1)*np.linalg.norm(E,axis=-1)+abs(w)*np.linalg.norm(B,axis=-1))
    assert np.isfinite(residual).all()and residual.max()<=1e-7
    for i in np.ndindex(shape):
        pivot=np.argmax(abs(E[i]));assert abs(E[i][pivot].imag)<=1e-12 and E[i][pivot].real>=0
    d=np.asarray(s['D']).item();assert abs(np.asarray(s['d']).item()-d)<=1e-12*max(1,abs(d))

def test_public_selected_fields_graph():
    scan=_scan();roots=np.asarray(scan.state['ww']).reshape(3,1,-1);seed=np.array([[.25,0,roots[0,0,np.argmax(roots[0,0].real)]/scan.state['wcs1'].item()]])
    _verify(g.selected_fields(dict(scan_state=scan,seeds=seed,rng_seed=2718)))

def test_public_rendered_and_stored_seed_graphs():
    scan=_scan();roots=np.asarray(scan.state['ww']).reshape(3,1,-1);seed=np.array([[.25,0,roots[0,0,np.argmax(roots[0,0].real)]/scan.state['wcs1'].item()]])
    for result in [g.rendered_output(dict(scan_state=scan,seeds=seed,rng_seed=2718)),g.preset_output(dict(scan_state=scan,scenario='default',rng_seed=2718))]:
        _verify(result);assert result.state['output_completed'].item()
        assert np.asarray(result.state['figure_png'],np.uint8).tobytes().startswith(b'\x89PNG')
        assert np.asarray(result.state['workspace_mat'],np.uint8).size>0

def test_field_normalization_handles_zero_Ex_and_global_phase():
    E=np.array([0,1,1j]);B=np.array([.1,.2j,.3])/oracle.C;en,bn,ue,ub=oracle.field_oracle(E,B)
    for factor in [1,1j,-1,3+4j]:
        s=m._normalize_electromagnetic_fields(factor*E,factor*B,oracle.EPS0,oracle.MU0).state
        np.testing.assert_allclose(np.asarray(s['normalized_fields']).ravel(),np.r_[en,bn],rtol=1e-12,atol=1e-15)

def test_public_point_fields_obey_eigenproblem_and_maxwell_row():
    eq=m.initialize_equilibrium(np.asarray(F['deck']),controls=dict(B0=F['B0'],N=1,J=4,iem=1,iout=2,sp=0))
    kx=.07/eq.state['cwp'].item();kz=.25/eq.state['cwp'].item();matrix=m.electromagnetic_matrix(eq,kx=kx,kz=kz)
    spectrum=m.eigensolve(matrix);values=np.asarray(spectrum.state['d']).ravel();guess=values[np.argmax(values.real)]
    result=m.reconstruct_point_fields(matrix,frequency_guess=guess);s=result.state;E=np.asarray(s['dEB']).ravel()[:3];B=np.asarray(s['dEB']).ravel()[3:];w=np.asarray(s['D']).item();k=np.array([kx,0,kz])
    assert abs(np.vdot(E,E)-1)<=1e-12
    assert np.linalg.norm(np.cross(k,E)-w*B)/(np.linalg.norm(k)*np.linalg.norm(E)+abs(w)*np.linalg.norm(B))<=1e-7
    V=np.asarray(s['V']);M=s['M'];D=np.asarray(s['D']);assert np.linalg.norm(M@V-V@D)/(np.linalg.norm(M.toarray())*np.linalg.norm(V)+np.linalg.norm(V@D))<=1e-9
