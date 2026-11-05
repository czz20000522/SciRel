import json
from pathlib import Path
import numpy as np

from scirel.kinetic import solve_relativistic_codrift_spectrum


ROOT = Path(__file__).parents[1] / "fixtures" / "kinetic" / "relativistic_codrift"


def test_valid_shape_and_finite():
    case = json.loads((ROOT / "typed-input.json").read_text())
    result = solve_relativistic_codrift_spectrum(case)
    assert len(result["spectra"]) == len(case["k"])
    assert all(np.asarray(row["real_order"]).shape == (14, 2) for row in result["spectra"])
    assert all(
        np.isfinite(np.asarray(row["real_order"])).all()
        and np.isfinite(np.asarray(row["imag_order"])).all()
        for row in result["spectra"]
    )


def test_source_reference_first_row_close():
    case = json.loads((ROOT / "typed-input.json").read_text())
    expected = json.loads((ROOT / "source-output.json").read_text())
    got = solve_relativistic_codrift_spectrum(case)
    want = np.asarray(expected["spectra"][0], dtype=float)
    # Source output is real-order; its first row is the same ordering exposed by the neutral operator.
    assert np.allclose(np.asarray(got["spectra"][0]["real_order"]), want, rtol=2e-7, atol=2e-8)


def test_rejects_superluminal():
    case = json.loads((ROOT / "typed-input.json").read_text())
    case["species"][0]["v0"][2] = 1.0
    try:
        solve_relativistic_codrift_spectrum(case)
    except ValueError as exc:
        assert "less than c" in str(exc)
    else:
        raise AssertionError("superluminal input was accepted")
