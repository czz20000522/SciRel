"""Executed only inside a generated temporary fixture package."""
from scirel.fixture.identity import identity

def test_fixture_wiring():
    assert identity(3.0, 2.0) == {"value": 6.0}
