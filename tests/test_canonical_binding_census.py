import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_canonical_bindings import census  # noqa: E402


def test_current_canonical_binding_census_preserves_facade_and_exception_denominators():
    report = census(ROOT)
    counts = report["counts"]

    assert counts["total"] == 267
    assert counts["explicit"] == 0
    assert counts["candidate"] == 220
    assert counts["exception"] == 47
    assert report["unexpected_missing"] == []

    exception_ids = {
        row["asset_id"] for row in report["rows"] if row["status"] == "exception"
    }
    assert exception_ids == {
        "scirel.kinetic.generalized-small-k",
        *{
            f"scirel.kinetic.{name}"
            for name in (
                "pdrk-dispersion-workflow",
                "pdrk-electromagnetic-eigenmatrix",
                "pdrk-electrostatic-eigenmatrix",
                "pdrk-faddeeva-finite-order",
                "pdrk-fluid-deck",
                "pdrk-fluid-equilibrium",
                "pdrk-fluid-frequency-pencil",
                "pdrk-fluid-frequency-solve",
                "pdrk-fluid-plot",
                "pdrk-fluid-relative-rate-equilibrium",
                "pdrk-fluid-scan",
                "pdrk-frequency-eigensolve",
                "pdrk-loss-cone-partition",
                "pdrk-magnetized-mode-fields",
                "pdrk-parallel-em-continuation",
                "pdrk-parallel-em-plot",
                "pdrk-parallel-em-residual",
                "pdrk-polarization-workflow",
                "pdrk-preset-mode-selection",
                "pdrk-preset-output-workflow",
                "pdrk-rational-default-deck",
                "pdrk-rational-em-coordinates",
                "pdrk-rational-equilibrium",
                "pdrk-rational-jpole-coefficients",
                "pdrk-rational-jpole-evaluate",
                "pdrk-rational-jpole-generator",
                "pdrk-rational-jpole-grid-coordinates",
                "pdrk-rational-ordered-spectrum",
                "pdrk-rational-point-matrix",
                "pdrk-rational-pole-table",
                "pdrk-rational-reassemble-original-program",
                "pdrk-rational-solve-matrix",
                "pdrk-rational-z-poles",
                "pdrk-rendered-output-workflow",
                "pdrk-seed-mode-selection",
                "pdrk-selected-dispersion-interpolation",
                "pdrk-selected-fields-workflow",
                "pdrk-selected-mode-artifacts",
                "pdrk-selection-artifacts",
                "pdrk-species-equilibrium",
                "pdrk-spectral-scan-workflow",
                "pdrk-spectrum-artifacts",
                "pdrk-stored-program-workflow",
                "pdrk-wavevector-coordinates",
                "pdrk-whamp-overlay",
                "pdrk-whamp-reference",
            )
        },
    }
