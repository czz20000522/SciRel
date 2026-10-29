import json
from pathlib import Path

from scirel.equilibrium import solve_finite_frc_feedback


def test_finite_frc_feedback_preserves_bounded_nonconvergence():
    path = Path(r"E:\SciRel-lab\_shared\outbound\portfolio-20261027\results\p0-demo-runtime-20261029\q10-input.json")
    if not path.exists():
        return
    result = solve_finite_frc_feedback(json.loads(path.read_text(encoding="utf-8")))
    assert result["psi_Wb"].shape == (17, 33)
    assert result["boundary_flux_Wb"].shape == (63,)
    assert result["boundary_counter"] >= 1
    assert result["coil_counter"] >= 1
    assert result["failure_reason"] == "maxiter_reached"
    assert result["converged"] is False
