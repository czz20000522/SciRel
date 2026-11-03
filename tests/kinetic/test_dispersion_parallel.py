"""Signed-wavevector causal response from direct Gaussian velocity integrals."""
import numpy as np
import pytest
from scipy.special import roots_hermite
from scirel.kinetic.dispersion.parallel import em1d_parallel_residual
from scirel.kinetic.dispersion.parallel_continuation import ContinuationFailure, continue_em1d

STATE=dict(wps2=np.array([1.,2.,.4]),vds=np.array([.2,-.1,.3]),vtzs=np.array([.7,1.1,.5]),wcs=np.array([.4,-.7,.2]),c2=9.,cwp=1.,wcs1=1.)

def _integral(state,w,k,pm,Q):
    x,h=roots_hermite(Q);out=w*w-k*k*state['c2']
    for wp,vd,vt,wc in zip(state['wps2'],state['vds'],state['vtzs'],state['wcs']):
        out-=wp*(w-k*vd)*np.sum(h/np.sqrt(np.pi)/(w-k*(vd+vt*x)+pm*wc))
    return out

@pytest.mark.parametrize('k',[-.3,.3])
@pytest.mark.parametrize('pm',[-1,1])
def test_causal_signed_k_direct_velocity_integral(k,pm):
    w=2.1+.8j;a=_integral(STATE,w,k,pm,96);b=_integral(STATE,w,k,pm,160)
    f,scale=em1d_parallel_residual(STATE,w,k,pm=pm)
    assert abs(a-b)/max(1,abs(b))<=1e-12
    assert abs(f-b)/scale<=1e-12
    reflected=dict(STATE,vds=-STATE['vds']);mirror,_=em1d_parallel_residual(reflected,w,-k,pm=pm)
    assert abs(f-mirror)/scale<=1e-12

def test_parallel_rejects_complex_and_unrepresentable_wavevectors():
    for k in [0,1+1j,True,np.longdouble('1e400')]:
        with pytest.raises(ValueError):em1d_parallel_residual(STATE,2+.7j,k)
    with pytest.raises(ValueError):em1d_parallel_residual(STATE,np.clongdouble('1e400'),.3)
    for k in [[],[0],[.1+1j]]:
        with pytest.raises(ValueError):continue_em1d(dict(state=STATE,k_grid=k))


def test_vacuum_continuation_matches_analytic_branch_and_zero_residual():
    state = dict(wps2=[0.0], vds=[0.0], vtzs=[1.0], wcs=[0.0], c2=1.0)
    result = continue_em1d(dict(state=state, k_grid=[0.2, 0.21], initial_guess=0.2 + 0j))
    np.testing.assert_allclose(result["omega"], [0.2, 0.21], rtol=0, atol=1e-15)
    assert all(record["scaled_residual"] == 0.0 for record in result["records"])


def test_default_seed_fails_closed_at_first_unaccepted_root():
    # The source-shaped default seed accepts the early points on this fixture
    # and stops at the first unaccepted root; it never returns a partial
    # continuation.
    with pytest.raises(ContinuationFailure) as caught:
        continue_em1d(dict(state=STATE))
    record = caught.value.record
    assert record["k"] > 0.0
    assert isinstance(record["guess"], complex)
    assert record["solver_success"] is False
    assert record["solver_status"] >= 0
    assert record["scaled_residual"] > 0.0
    assert isinstance(record["accepted_prefix"], tuple)
    assert record["accepted_prefix"]
    assert all(abs(root) < 1.0 for root in record["accepted_prefix"])

def test_explicit_seed_continuation_accepts_only_gated_roots():
    state = dict(wps2=[0.0], vds=[0.0], vtzs=[1.0], wcs=[0.0], c2=1.0)
    result = continue_em1d(dict(state=state, k_grid=[0.2, 0.21], initial_guess=0.2 + 0j, residual_tolerance=1e-12))
    assert len(result["records"]) == 2
    assert all(record["solver_success"] for record in result["records"])
    assert all(record["scaled_residual"] <= 1e-12 for record in result["records"])


def test_failed_root_never_becomes_next_seed(monkeypatch):
    from types import SimpleNamespace
    import scirel.kinetic.dispersion.parallel_continuation as continuation

    calls = []

    def failing_root(fun, x0, **kwargs):
        calls.append((list(x0), kwargs))
        return SimpleNamespace(x=np.asarray(x0, dtype=float), success=False, status=5)

    monkeypatch.setattr(continuation, "root", failing_root)
    with pytest.raises(ContinuationFailure) as caught:
        continue_em1d(dict(state=STATE, k_grid=[0.01, 0.02]))
    assert len(calls) == 1
    assert caught.value.record["accepted_prefix"] == ()
    assert caught.value.record["k"] == pytest.approx(0.01)


def test_continuation_failure_is_not_silently_rescued(monkeypatch):
    from types import SimpleNamespace
    import scirel.kinetic.dispersion.parallel_continuation as continuation

    def successful_but_wrong_root(fun, x0, **kwargs):
        return SimpleNamespace(x=np.asarray([0.0, 0.0]), success=True, status=1)

    monkeypatch.setattr(continuation, "root", successful_but_wrong_root)
    with pytest.raises(ContinuationFailure) as caught:
        continue_em1d(dict(state=STATE, k_grid=[0.01], residual_tolerance=1e-30))
    record = caught.value.record
    assert record["solver_success"] is True
    assert record["scaled_residual"] > 1e-30
    assert record["accepted_prefix"] == ()
