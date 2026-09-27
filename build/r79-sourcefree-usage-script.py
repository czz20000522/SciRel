"""r79 source-free usage evidence: representative public API of the four
new neutral-merge-family assets, executed from an isolated directory
outside the repository with the installed dev56 wheel only."""
import os
import sys

print("cwd:", os.getcwd())
print("executable:", sys.executable)
print("PYTHONPATH:", repr(os.environ.get("PYTHONPATH")))
assert not os.environ.get("PYTHONPATH"), "PYTHONPATH must be unset"

import scirel

print("scirel.__file__:", scirel.__file__)
assert "site-packages" in scirel.__file__.replace("\\", "/").lower(), scirel.__file__
# -I legitimately keeps the venv root (which lives inside the repo path)
# on sys.path; what must be absent are the repo checkout root and any
# src/ source directory entry.
import importlib.util
from pathlib import Path

for entry in sys.path:
    normalized = entry.replace("\\", "/").rstrip("/").lower()
    assert not normalized.endswith("scirel-intake-20260925"), entry
    assert not normalized.endswith("/src"), entry
assert importlib.util.find_spec("tests") is None, "the repo tests package must not be importable"
import scirel.fusion.neutral_reservoir_merge as _probe

assert "site-packages" in _probe.__file__.replace("\\", "/").lower(), _probe.__file__
print("sys.path clean of the source checkout:", True)

import numpy as np
from scirel.fusion import (
    merge_neutral_population_cells,
    merge_neutral_population_density,
    merge_neutral_population_state,
    merge_neutral_reservoirs,
)

r1 = merge_neutral_population_density(
    target_population_density=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    source_population_density=[1.0, 0.0, -1.0, 0.0, 2.0, 0.5],
)
assert np.allclose(r1["target_population_density_after"], [2.0, 2.0, 2.0, 4.0, 7.0, 6.5])
assert np.allclose(r1["source_population_density_after"], [1.0, 0.0, -1.0, 0.0, 2.0, 0.5])
assert np.isclose(r1["density_contribution_sum"], 2.5)
print("neutral-population-density-merge ok")

r2 = merge_neutral_population_cells(
    target_population_density=np.ones((6, 2, 1, 1)),
    source_population_density=np.full((6, 2, 1, 1), 0.5),
)
assert r2["cell_shape"] == [2, 1, 1] and r2["cell_count"] == 2
assert np.allclose(r2["target_population_density_after"], 1.5)
assert r2["source_population_density_after"] is not None
print("neutral-population-grid-merge ok")

K = 50
def state(n, offset):
    weights = np.ones(K)
    velocities = np.zeros((K, 3))
    for index in range(1, min(n, K) + 1):
        weights[index - 1] = offset + index
        velocities[index - 1] = [offset + index, 2.0 * offset + index, -offset - index]
    return n, 101, 0.91, weights, velocities

n1, i1, w1, sw1, sv1 = state(4, 0)
n2, i2, w2, sw2, sv2 = state(5, 100)
r3 = merge_neutral_reservoirs(
    target_n=n1, target_i=i1, target_W=w1,
    target_slot_weights=sw1, target_slot_velocities_cm_s=sv1,
    source_n=n2, source_i=i2, source_W=w2,
    source_slot_weights=sw2, source_slot_velocities_cm_s=sv2,
    target_initialization_uniforms=[0.5, 0.5],
    transfer_replacement_indices=np.asarray([], dtype=np.int64),
    transfer_replacement_uniforms=np.empty((0, 2)),
    full_full_uniforms=np.asarray([]),
)
assert r3["branch"] == "both_nonfull" and r3["target_n"] == 9
assert np.allclose(r3["target_slot_weights"][3:8], [101, 102, 103, 104, 105])
assert np.array_equal(r3["source_slot_weights"], r3["target_slot_weights"])
print("neutral-reservoir-merge ok")

def reservoir_inputs(left, right):
    return {
        "target_n": left[0], "target_i": left[1], "target_W": left[2],
        "target_slot_weights": left[3], "target_slot_velocities_cm_s": left[4],
        "source_n": right[0], "source_i": right[1], "source_W": right[2],
        "source_slot_weights": right[3], "source_slot_velocities_cm_s": right[4],
        "target_initialization_uniforms": [0.5, 0.5],
        "transfer_replacement_indices": np.asarray([], dtype=np.int64),
        "transfer_replacement_uniforms": np.empty((0, 2)),
        "full_full_uniforms": np.asarray([]),
    }

r4 = merge_neutral_population_state(
    target_population_density=np.ones(6),
    source_population_density=np.full(6, 2.0),
    reservoir_merge_inputs=reservoir_inputs(state(4, 0), state(0, 100)),
)
assert np.allclose(r4["target_population_density_after"], 3.0)
assert r4["reservoir_merge"]["branch"] == "source_empty"
assert r4["diagnostics"]["graph_order"] == ["population_density_merge", "reservoir_merge"]
try:
    merge_neutral_population_state(
        target_population_density=np.ones(6),
        source_population_density=np.ones(6),
        reservoir_merge_inputs=None,
    )
except ValueError:
    pass
else:
    raise AssertionError("non-mapping reservoir state must fail closed")
print("neutral-population-state-merge ok (composition + fail-closed)")

print("R79-SOURCE-FREE-USAGE-PASSED")
