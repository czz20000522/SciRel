import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_canonical_bindings import census  # noqa: E402


def test_current_canonical_binding_census_preserves_facade_and_exception_denominators():
    report = census(ROOT)
    counts = report["counts"]

    assert counts["total"] == 267
    assert counts["explicit"] == 129
    assert counts["candidate"] == 91
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


def test_geometry_and_field_slice_pins_package_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        asset_id
        for asset_id in rows
        if asset_id.startswith(
            (
                "scirel.basis.",
                "scirel.field.",
                "scirel.fieldline.",
                "scirel.geometry.",
                "scirel.numerics.",
                "scirel.plotting.",
                "scirel.sampling.",
            )
        )
    }
    assert len(selected) == 60
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    # Other non-PDRK records still exercise the legacy inferred facade path
    # until their own canonical fields are migrated.
    assert rows["scirel.kinetic.species-equilibrium-scales"] == "candidate"


def test_explicit_canonical_binding_is_checked_against_runtime_identity(tmp_path):
    source = ROOT / "catalog/examples/scirel.field.poloidal-field-from-flux.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["public_api"]["python"]["canonical_symbol"] = "MissingExport"
    candidate = tmp_path / source.name
    candidate.write_text(json.dumps(document), encoding="utf-8")

    report = census(ROOT, tmp_path)

    assert report["counts"] == {
        "total": 1,
        "explicit": 0,
        "candidate": 0,
        "exception": 0,
    }
    assert report["rows"] == [
        {
            "asset_id": "scirel.field.poloidal-field-from-flux",
            "status": "explicit_invalid",
        }
    ]
    assert report["unexpected_missing"][0]["canonical_symbol"] == "MissingExport"


def test_collision_and_electromagnetism_slice_pins_package_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        asset_id
        for asset_id in rows
        if asset_id.startswith(("scirel.collisions.", "scirel.electromagnetism."))
    }
    assert len(selected) == 30
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.species-equilibrium-scales"] == "candidate"


def test_closure_diagnostic_and_inference_slice_pins_package_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        asset_id
        for asset_id in rows
        if asset_id.startswith(
            ("scirel.closures.", "scirel.diagnostics.", "scirel.inference.")
        )
    }
    assert len(selected) == 19
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.species-equilibrium-scales"] == "candidate"


def test_equilibrium_io_and_small_domain_slice_pins_package_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        asset_id
        for asset_id in rows
        if asset_id.startswith(
            (
                "scirel.dielectric.",
                "scirel.equilibrium.",
                "scirel.fusion.",
                "scirel.io.",
                "scirel.plasma.",
            )
        )
    }
    assert len(selected) == 20
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.species-equilibrium-scales"] == "candidate"
