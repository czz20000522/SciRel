"""Named exact-document ports preserve original positional numerical paths.

The pre-adapter source failures are retained in keyword-ports-before.stdout.
"""
import numpy as np
import pytest
from scirel import sampling

def test_regular_grid_named_values_match_legacy_positional_fields():
    x,y=np.meshgrid(np.linspace(0,1,4),np.linspace(0,1,4))
    q=x+2*y
    old=sampling.regular_grid(x,y,q,nx=5,ny=6)
    named=sampling.regular_grid(x,y,values=[q],nx=5,ny=6)
    assert len(named)==len(old)==3
    for a,b in zip(named,old):np.testing.assert_array_equal(a,b)
    with pytest.raises(ValueError):sampling.regular_grid(x,y,q,values=[q])

def test_reflection_named_quantities_match_legacy_positional_fields():
    x,y=np.meshgrid([0.,.5,1.],[-.2,.2]);q=x*x+y
    old=sampling.reflect_and_hstack(x,y,q)
    named=sampling.reflect_and_hstack(x,y,quantities=[q])
    assert len(named)==len(old)==3
    for a,b in zip(named,old):np.testing.assert_array_equal(a,b)
    with pytest.raises(ValueError):sampling.reflect_and_hstack(x,y,q,quantities=[q])
