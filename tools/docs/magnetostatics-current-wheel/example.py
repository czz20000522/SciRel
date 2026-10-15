"""Run the magnetostatics chapter against an installed SciRel package.

Usage: python example.py results.json
All distances are metres; currents are amperes; fields are tesla.
"""
import json
import sys
from pathlib import Path
import numpy as np
import scipy
from scirel.field import circular_filament_green_response, superpose_current_green_field, solve_multi_coil_vacuum_field

# %% single
# A circular filament: radius 0.35 m, one turn, current 1000 A.
z = np.linspace(-0.7, 0.7, 141)
points = np.column_stack((np.zeros_like(z), z))
green = circular_filament_green_response([[0.35, 0.0, 1.0]], points)
field = superpose_current_green_field(1000.0, green['gpsi'], green['gBR'], green['gBZ'])
bz_single = field['BZ']
# Independent on-axis check, using the same mu0 convention as this model.
mu0 = 4 * np.pi * 1e-7
analytic = mu0 * 1000.0 * 0.35**2 / (2 * (0.35**2 + z**2)**1.5)
np.testing.assert_allclose(bz_single, analytic, rtol=2e-13, atol=1e-16)

# %% pair
# Two equal loops: their separation equals their radius (Helmholtz geometry).
responses = [circular_filament_green_response([[0.35, z0, 1.0]], points)
             for z0 in [-0.175, 0.175]]
stacked = {key: np.stack([r[key] for r in responses]) for key in green}
pair = superpose_current_green_field([1000.0, 1000.0], stacked['gpsi'], stacked['gBR'], stacked['gBZ'])
opposed = superpose_current_green_field([1000.0, -1000.0], stacked['gpsi'], stacked['gBR'], stacked['gBZ'])
bz_pair = pair['BZ']
np.testing.assert_allclose(bz_pair, bz_pair[::-1], rtol=2e-13, atol=1e-16)
assert abs(opposed['BZ'][70]) < 1e-15
np.testing.assert_allclose(bz_pair[70], (4/5)**1.5 * mu0 * 1000/0.35, rtol=2e-13)

# %% rectangle
# Each rectangular cross-section represents total ampere-turns of 1000 A-turn.
# Discretization weights sum to one, so refinement does not add current.
r_grid, z_grid = np.meshgrid(np.linspace(0, 0.30, 61), np.linspace(-0.25, 0.25, 101))
def coil(n, z0):
    return dict(r0_m=0.45, z0_m=z0, nr=n, nz=n,
                dr_m=0.04/(n-1), dz_m=0.05/(n-1), current_a=1000.0,
                weights=np.full(n*n, 1/(n*n)))
result = solve_multi_coil_vacuum_field(r_grid=r_grid, z_grid=z_grid,
                                      rectangular_coils=[coil(8, -0.12), coil(8, 0.12)])
assert np.isfinite(result['b_z_vac']).all()
np.testing.assert_allclose(result['b_r_vac'][50], 0, atol=1e-15)
np.testing.assert_allclose(result['b_z_vac'], result['b_z_vac'][::-1], rtol=2e-13, atol=1e-16)

# %% checks
# Refinement is observed at a fixed point; it is not an arbitrary-grid error bound.
center_values = []
for n in [2, 4, 8, 16]:
    center = solve_multi_coil_vacuum_field(r_grid=np.array([[0.0]]), z_grid=np.array([[0.0]]),
                                         rectangular_coils=[coil(n, -0.12), coil(n, 0.12)])
    center_values.append(float(center['b_z_vac'][0, 0]))
midpoint = np.array([[0.1, 0.0], [0.2, 0.0], [0.3, 0.0]])
midgreen = circular_filament_green_response([[0.35, -0.175, 1], [0.35, 0.175, 1]], midpoint)
np.testing.assert_allclose(midgreen['gBR'], 0, atol=1e-18)
double = superpose_current_green_field([2000, 2000], stacked['gpsi'], stacked['gBR'], stacked['gBZ'])
np.testing.assert_allclose(double['BZ'], 2*bz_pair, rtol=2e-14, atol=1e-16)
checks = dict(axis_max_abs_error_T=float(np.max(np.abs(bz_single-analytic))),
              pair_midplane_max_abs_BR_T=float(np.max(np.abs(1000*midgreen['gBR']))),
              double_current_max_abs_error_T=float(np.max(np.abs(double['BZ']-2*bz_pair))))
output = dict(schema='scirel.chapter-results.v1', numpy=np.__version__, scipy=scipy.__version__,
              z_m=z.tolist(), single_BZ_T=bz_single.tolist(), pair_BZ_T=bz_pair.tolist(),
              opposed_BZ_T=opposed['BZ'].tolist(), center_single_T=float(bz_single[70]),
              center_pair_T=float(bz_pair[70]), refinement_n=[2,4,8,16], refinement_center_T=center_values,
              r_m=r_grid[0].tolist(), grid_z_m=z_grid[:,0].tolist(), rectangle_BZ_T=result['b_z_vac'].tolist(),
              checks=checks, all_checks_passed=True)
Path(sys.argv[1]).write_text(json.dumps(output, indent=2)+'\n')
print(json.dumps({k: output[k] for k in ['center_single_T','center_pair_T','refinement_center_T','checks','all_checks_passed']},indent=2))
