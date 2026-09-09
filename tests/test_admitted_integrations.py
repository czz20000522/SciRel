"""Bind maintained library code to its explicit admitted-input integration records."""
import hashlib
import importlib
import json
from pathlib import Path


def test_admitted_integrations_match_the_loaded_library():
    root = Path(__file__).resolve().parents[1]
    records = json.loads((root / "provenance/admitted-assets.json").read_text(encoding="utf-8"))
    assert records["schema"] == "scirel.admitted-integrations.v1"
    assert records["distribution_status"] == "development_partial_admission"
    assert records["integrations"]
    public_names = set()
    admissions = set()
    for record in records["integrations"]:
        public_name = record["public_callable"]
        assert public_name not in public_names
        public_names.add(public_name)
        module_name, symbol = public_name.rsplit(".", 1)
        assert module_name.startswith("scirel.")
        module = importlib.import_module(module_name)
        assert callable(getattr(module, symbol))
        source = Path(module.__file__).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(source).hexdigest() == record["library_source_lf_sha256"]
        exported = record["admitted_input"]
        assert exported["schema"] == "scirel.admitted-asset-export.v1"
        admission = exported["admission"]
        assert admission["admission_ref"] not in admissions
        admissions.add(admission["admission_ref"])
        assert admission["case_ref"] and admission["decision_ref"]
        assert admission["version_commit_ref"] and admission["root_digest"].startswith("sha256:")
        paths = [item["path"] for item in exported["files"]]
        assert len(paths) == len(set(paths))
        assert record["input_implementation_path"] in paths
        assert record["integration_action"] in {
            "reuse_equivalent_implementation", "adapt_input_shape", "replace_development_implementation"
        }
        if record["integration_action"] == "adapt_input_shape":
            assert record["input_adaptation"]
        for equivalent in record.get("equivalent_admitted_inputs", []):
            assert equivalent["relationship"] and equivalent["comparison"]
            exported = equivalent["admitted_input"]
            assert exported["schema"] == "scirel.admitted-asset-export.v1"
            admission = exported["admission"]
            assert admission["admission_ref"] not in admissions
            admissions.add(admission["admission_ref"])
            assert admission["case_ref"] and admission["decision_ref"]
            paths = [item["path"] for item in exported["files"]]
            assert len(paths) == len(set(paths))


def test_duplicate_human_admission_is_bound_to_the_existing_frank_egedal_implementation():
    root = Path(__file__).resolve().parents[1]
    records = json.loads((root / "provenance/admitted-assets.json").read_text(encoding="utf-8"))
    record = next(
        item for item in records["integrations"]
        if item["public_callable"].endswith(".evaluate_frank_egedal_radial_envelope")
    )

    duplicate = next(
        item for item in record["equivalent_admitted_inputs"]
        if item["admitted_input"]["admission"]["admission_ref"]
        == "scientific_asset_admission_bff7513f14eb910950e287a2"
    )
    assert duplicate["relationship"] == "byte_identical_implementation_and_tests"

    primary_files = {
        Path(item["path"]).name: item["sha256"]
        for item in record["admitted_input"]["files"]
    }
    duplicate_files = {
        Path(item["path"]).name: item["sha256"]
        for item in duplicate["admitted_input"]["files"]
    }
    for name in ("scientific_operator.py", "test_scientific_operator.py"):
        assert duplicate_files[name] == primary_files[name]
