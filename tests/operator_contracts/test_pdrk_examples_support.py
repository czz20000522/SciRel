"""Native support data, finite approximations and explicit plot-axis mappings."""
import numpy as np
import mpmath as mp
import pytest
import shutil
from scirel.kinetic.pdrk import multifluid as f, plotting as p, reference, special


pytestmark = pytest.mark.skipif(
    shutil.which("octave") is None,
    reason="PDRK native support contracts require GNU Octave",
)

def test_stored_data_and_deck_are_attributed_independent_values():
    a=f.fluid_deck(); b=f.fluid_deck(); a[0,0]=0
    assert b.shape[1]==10 and b[0,0]!=0
    table=reference.whamp_reference().state
    assert table['whpdat'].shape==(40,4)
    np.testing.assert_allclose(table['whpdat'][0],[.5,.025,.036828034,-.00115],rtol=0,atol=0)
    np.testing.assert_array_equal(table['wrwhp'].ravel(),table['whpdat'][:,2])

@pytest.mark.parametrize('N,tolerance',[(16,1e-6),(64,2e-13)])
def test_finite_order_faddeeva_against_independent_eighty_digit_identity(N,tolerance):
    z=np.array([[0,.7+.2j],[-1.3+.6j,2.1+.4j]])
    with mp.workdps(80):
        expected=np.array([complex(mp.exp(-mp.mpc(complex(x))**2)*mp.erfc(-1j*mp.mpc(complex(x)))) for x in z.ravel()]).reshape(z.shape)
    result=special.evaluate_faddeeva_finite_order(z,N).state['w']
    assert result.shape==z.shape
    np.testing.assert_allclose(result,expected,rtol=tolerance,atol=tolerance)

@pytest.mark.parametrize('method,grid,lines,surfaces',[
 (1,dict(wave_number=1e-4),0,0),
 (2,dict(scan_k=[1e-4,2e-4]),28,0),
 (3,dict(wave_number=1e-4,scan_theta=[0,.37,np.pi/2]),10,0),
 (4,dict(scan_kx=[0,1e-4],scan_kz=[0,2e-4]),0,28)])
def test_fluid_renderers_consume_declared_scan_axes(method,grid,lines,surfaces):
    deck=np.array([[1.,1.,1.,0,0,0,0,0,0,0],[-1.,1.,1.,0,0,0,0,0,0,0]])
    state=f.fluid_equilibrium_si(deck,B0=0)
    assert state['beta_z'] is None and state['beta_p'] is None
    graph=f.scan_fluid_corrected(dict(state=state,method=method,grid_controls=grid))
    result=p.fluid_plot_scan(graph,state,method=method).state
    assert result['plot_line_count'].item()==lines
    assert result['plot_surface_count'].item()==surfaces
    if method!=1:assert np.asarray(result['png_bytes'],np.uint8).tobytes().startswith(b'\x89PNG')

def test_explicit_parallel_plot_and_reference_overlay_artifacts():
    graph=dict(k=np.array([.1,.2,.3]),omega=np.array([1+.01j,1.2+.02j,1.4+.03j]))
    first=p.em1d_plot(graph,dict(cwp=2.,wcs1=3.),pm=1)
    overlay=p.whamp_overlay(first)
    for result in (first,overlay):
        assert np.asarray(result.state['figure_native'],np.uint8).size>0
        assert np.asarray(result.state['figure_png'],np.uint8).tobytes().startswith(b'\x89PNG')
    assert len(overlay.state['line_offsets'].ravel())>len(first.state['line_offsets'].ravel())
