import numpy as np
import pytest

from scirel.field import solve_multi_coil_vacuum_field
from scirel._composition import compose


def test_composition_does_not_mutate_inputs_and_preserves_keyword_precedence():
    original = {"x": 1}
    def calculation(values):
        values["changed"] = True
        return values["x"]
    assert compose(calculation, original, {"x": 2}, {}) == 2
    assert original == {"x": 1}


def test_composition_cannot_resolve_undeclared_dependencies():
    def calculation(values, *, asset_loader):
        return asset_loader("undeclared")
    with pytest.raises(KeyError):
        compose(calculation, {}, {}, {"asset_loader": {}})


def test_plain_public_composition_preserves_independent_coil_currents():
    r, z = np.meshgrid(np.linspace(0, 0.3, 5), np.linspace(-0.2, 0.2, 4))
    a = dict(r0_m=0.45, z0_m=0, nr=2, nz=2, dr_m=0.04, dz_m=0.05, current_a=700)
    b = dict(a, z0_m=0.08, current_a=-300)
    first = solve_multi_coil_vacuum_field(r_grid=r, z_grid=z, rectangular_coils=[a])
    second = solve_multi_coil_vacuum_field(r_grid=r, z_grid=z, rectangular_coils=[b])
    both = solve_multi_coil_vacuum_field(r_grid=r, z_grid=z, rectangular_coils=[a, b])
    for key in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(both[key], first[key] + second[key], rtol=2e-14, atol=1e-300)
