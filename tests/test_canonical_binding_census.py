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
    assert counts["explicit"] == 217
    assert counts["candidate"] == 3
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
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


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
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


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
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


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
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_pdrf_gpdf_and_generalized_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.evaluate-faddeeva-dr",
        "scirel.kinetic.evaluate-faddeeva-gpdf",
        "scirel.kinetic.generalized-dispersion",
        "scirel.kinetic.generalized-expression-differentiation",
        "scirel.kinetic.generalized-hilbert",
        "scirel.kinetic.generalized-residual",
        "scirel.kinetic.generalized-root-scans",
        "scirel.kinetic.pdrf-dispersion-scan",
        "scirel.kinetic.pdrf-plasma-state",
        "scirel.kinetic.pdrf-temporal-matrix",
        "scirel.kinetic.pdrf-temporal-spectrum",
    }
    assert len(selected) == 11
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"
    assert rows["scirel.kinetic.generalized-small-k"] == "exception"


def test_fluidbw_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        asset_id
        for asset_id in rows
        if asset_id.startswith("scirel.kinetic.fluidbw-")
        or asset_id == "scirel.kinetic.kinetic-dispersion-sum-fluidbw"
    }
    assert len(selected) == 8
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_vlasov_poisson_and_maxwellian_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        asset_id
        for asset_id in rows
        if asset_id.startswith("scirel.kinetic.vp-")
        or asset_id
        in {
            "scirel.kinetic.evaluate-maxwellian-fft",
            "scirel.kinetic.evaluate-maxwellian-jpole",
            "scirel.kinetic.kinetic-dispersion-sum",
            "scirel.kinetic.maxwellian-electrostatic-mode",
            "scirel.kinetic.maxwellian-electrostatic-solver",
        }
    }
    assert len(selected) == 14
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_special_function_and_dispersion_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.bessel-gamma",
        "scirel.kinetic.gamma-lpole-coefficients",
        "scirel.kinetic.gpdf-cauchy-transform",
        "scirel.kinetic.plasma-dispersion-function",
        "scirel.kinetic.plasma-dispersion-weideman",
        "scirel.kinetic.ronnmark-r-function",
        "scirel.kinetic.z-pole-coefficients",
    }
    assert len(selected) == 7
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_terminal_and_neutral_basics_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.elastic-frequency-channels",
        "scirel.kinetic.generation-density-reduction",
        "scirel.kinetic.incoming-boundary-flux-normalization",
        "scirel.kinetic.neutral-total-collision-frequency",
        "scirel.kinetic.spatial-source-shape-normalization",
        "scirel.kinetic.terminal-conservation-diagnostic",
        "scirel.kinetic.terminal-energy-transfer-reduction",
        "scirel.kinetic.terminal-flux-velocity-reduction",
        "scirel.kinetic.terminal-heat-flux-reduction",
        "scirel.kinetic.terminal-ion-state-reduction",
        "scirel.kinetic.terminal-pressure-temperature-reduction",
    }
    assert len(selected) == 11
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_neutral_mesh_and_source_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.adaptive-neutral-velocity-mesh",
        "scirel.kinetic.atomic-scattered-sources-reduction",
        "scirel.kinetic.cross-mesh-scalar-interpolation",
        "scirel.kinetic.cylindrical-velocity-quadrature",
        "scirel.kinetic.elastic-regeneration-aggregation",
        "scirel.kinetic.molecular-scattered-sources-reduction",
        "scirel.kinetic.shifted-maxwellian-seed",
        "scirel.kinetic.simple-charge-exchange-source",
    }
    assert len(selected) == 8
    assert all(rows[asset_id] == "explicit" for asset_id in selected)


def test_alpha_contraction_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.atomic-alpha-contraction",
        "scirel.kinetic.molecular-alpha-contraction",
    }
    assert len(selected) == 2
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_neutral_convergence_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.generation-accumulation-update",
        "scirel.kinetic.kn1d-outer-convergence",
        "scirel.kinetic.neutral-generation-stopping",
        "scirel.kinetic.outer-seed-convergence",
        "scirel.kinetic.thermal-speed-scale",
    }
    assert len(selected) == 5
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_population_and_axisymmetric_moment_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.axisymmetric-neutral-moments",
        "scirel.kinetic.hydrogen-saha-equilibrium-population",
    }
    assert len(selected) == 2
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_transport_and_species_scale_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.neutral-boltzmann-rhs",
        "scirel.kinetic.neutral-generation-propagation",
        "scirel.kinetic.neutral-upwind-transport-coefficients",
        "scirel.kinetic.species-equilibrium-scales",
    }
    assert len(selected) == 4
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_direct_plasma_wave_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.dielectric-tensor-diagnostic",
        "scirel.kinetic.fluid-dispersion-matrix",
        "scirel.kinetic.fluid-wavevector-eigensolve",
        "scirel.kinetic.kinetic-dispersion-ronnmark",
        "scirel.kinetic.kinetic-wavevector-roots",
    }
    assert len(selected) == 5
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_mirror_direct_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.mirror-constrained-moments",
        "scirel.kinetic.mirror-invariant-distribution",
        "scirel.kinetic.mirror-total-pressure",
    }
    assert len(selected) == 3
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_loss_cone_spectrum_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {"scirel.kinetic.loss-cone-spectrum"}
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_wavevector_and_dispersion_graph_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.fluid-wavevector-scan",
        "scirel.kinetic.kinetic-dispersion-relation",
        "scirel.kinetic.kinetic-wavevector-scan",
    }
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"


def test_frank_egedal_direct_slice_pins_kinetic_facades_explicitly():
    report = census(ROOT)
    rows = {row["asset_id"]: row["status"] for row in report["rows"]}
    selected = {
        "scirel.kinetic.frank-egedal-hot-ion-moments",
        "scirel.kinetic.frank-egedal-pressure-state",
        "scirel.kinetic.frank-egedal-radial-envelope",
        "scirel.kinetic.frank-egedal-source-projection",
    }
    assert all(rows[asset_id] == "explicit" for asset_id in selected)
    assert rows["scirel.kinetic.cross-mesh-distribution-interpolation"] == "candidate"
