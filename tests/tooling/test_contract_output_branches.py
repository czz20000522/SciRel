"""Pin solve_matrix's per-branch return key sets against the contract's declared outputs.

Why this exists
---------------
`scirel.kinetic.rational-solve-matrix` declares 46 outputs, but one call returns one of
three key sets (T-2026-1202). The contract states the union, so a consumer cannot read
from `outputs` alone which keys its call returns. Option C keeps all 46 fields and pins
the branch dimension here instead of widening the `port` schema.

What this catches
-----------------
A declared output that no branch returns, a branch that starts returning an undeclared
key, and a branch whose key set drifts without the contract saying so. It does not judge
whether a returned value is physically right; the direct tests in `verification.tests`
own that.
"""

import json
from pathlib import Path

from scirel.kinetic.dispersion import rational

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "catalog" / "examples" / "scirel.kinetic.rational-solve-matrix.json"

ES1D_EM = {
    "d",
    "omega",
    "V",
    "w",
    "wi",
    "ind",
    "indices",
    "backward_residual",
    "wg",
}
ES3D_DESCRIPTOR = {
    "A",
    "H",
    "accepted",
    "all_finite",
    "alpha",
    "beta",
    "canceled_poles",
    "classification",
    "constant",
    "infinite_count",
    "omega",
    "pencil_residual",
    "poles",
    "rational_residual",
    "residues",
}
ES3D_DESCRIPTOR_NO_KEPT_POLES = {
    "omega",
    "all_finite",
    "infinite_count",
    "canceled_poles",
    "rational_residual",
    "pencil_residual",
    "classification",
    "constant",
    "poles",
    "residues",
}
ES3D_PERPENDICULAR = {
    "N",
    "classification",
    "constant_decimal",
    "frequency_base",
    "frequency_base_decimal",
    "frequency_offset",
    "frequency_offset_decimal",
    "frequency_scale_decimal",
    "mode_classification",
    "mode_count",
    "omega",
    "pole_square_decimal",
    "precision_digits",
    "precision_limit",
    "published_frequency_base_decimal",
    "published_frequency_offset_decimal",
    "published_omega",
    "reference_pole_index",
    "root_brackets_delta_decimal",
    "root_interval_index",
    "root_sign",
    "shift_chart_residual_decimal",
    "source_pole_order",
    "square_offset_decimal",
    "w",
    "weights_decimal",
}


def branch_key_sets():
    """Return each public branch's actual return keys, reached through public entry points."""
    eq = rational.equilibrium("es1d", [[1, 1, 1, 1, 0]])["state"]
    tab = rational.pole_table("es1d", 4)["state"]
    matrix = rational.point_matrix("es1d", {**eq, **tab}, k=0.4)["state"]["M"]
    eq3 = rational.equilibrium("es3d", [[1, 1, 1, 1, 1, 0]])["state"]
    tab3 = rational.pole_table("es3d", 4)["state"]
    perpendicular = rational.point_matrix("es3d", {**eq3, **tab3}, kx=0.3, kz=0.0)["state"]
    return {
        "es1d": set(rational.solve_matrix(matrix, model="es1d")),
        "es1d_sparse": set(rational.solve_matrix(matrix, model="es1d", sp=1, nw=1, wg=0.2 + 0.1j)),
        "es3d_descriptor": set(
            rational.solve_matrix(
                {"constant": 1.0, "poles": [0.3, 0.7], "residues": [1.0, 0.5]}, model="es3d"
            )
        ),
        "es3d_descriptor_no_kept_poles": set(
            rational.solve_matrix(
                {"constant": 1.0, "poles": [0.3, 0.3], "residues": [1.0, -1.0]}, model="es3d"
            )
        ),
        "es3d_perpendicular": set(rational.solve_matrix(perpendicular, model="es3d")),
    }


def test_each_branch_returns_its_pinned_key_set():
    keys = branch_key_sets()
    assert keys["es1d"] == ES1D_EM
    assert keys["es1d_sparse"] == ES1D_EM
    assert keys["es3d_descriptor"] == ES3D_DESCRIPTOR
    assert keys["es3d_descriptor_no_kept_poles"] == ES3D_DESCRIPTOR_NO_KEPT_POLES
    assert keys["es3d_perpendicular"] == ES3D_PERPENDICULAR


def test_declared_outputs_are_the_union_of_the_branches():
    declared = [
        port["name"] for port in json.loads(CONTRACT.read_text(encoding="utf-8"))["outputs"]
    ]
    union = set().union(*branch_key_sets().values())
    assert len(declared) == len(set(declared)), "duplicate output names in the contract"
    assert union == set(declared), sorted(set(declared) ^ union)
