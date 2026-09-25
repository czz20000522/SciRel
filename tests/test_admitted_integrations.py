"""Bind maintained library code to its explicit admitted-input integration records."""
import hashlib
import importlib
import json
from pathlib import Path

from _historical_admitted import historical_file


def test_historical_admitted_sources_remain_bound_and_callables_remain_available():
    root = Path(__file__).resolve().parents[1]
    records = json.loads((root / "provenance/admitted-assets.json").read_text(encoding="utf-8"))
    assert records["schema"] == "scirel.admitted-integrations.v1"
    assert records["distribution_status"] == "development_full_admission_candidate"
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
        source_path = Path("src", *module_name.split(".")).with_suffix(".py")
        source = historical_file(source_path).replace(b"\r\n", b"\n")
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
            "add_admitted_implementation",
            "maintain_compatible_library_implementation",
            "normalize_task_graph_wrapper",
        }
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


def test_current_formal_pleiades_batch_is_exact_and_dependency_closed():
    root = Path(__file__).resolve().parents[1]
    records = json.loads((root / "provenance/admitted-assets.json").read_text(encoding="utf-8"))
    batch = records["admission_batch"]
    assert batch["asset_count"] == 52
    assert batch["operator_count"] == 41
    assert batch["task_graph_count"] == 11
    assert len(records["integrations"]) == 52

    admissions = {
        record["admitted_input"]["admission"]["admission_ref"]
        for record in records["integrations"]
    }
    assert len(admissions) == 52
    kinds = [
        record["admitted_input"]["admission"]["asset_kind"]
        for record in records["integrations"]
    ]
    assert kinds.count("operator") == 41
    assert kinds.count("task_graph") == 11
    assert all(
        set(record["dependency_admission_refs"]) <= admissions
        for record in records["integrations"]
    )

    public_callables = {record["public_callable"] for record in records["integrations"]}
    assert "scirel.inference.anisotropic_trial_evaluation.evaluate_anisotropic_trial" in public_callables
    assert (
        "scirel.equilibrium.kinetic_mirror_hall_equilibrium."
        "solve_kinetic_mirror_hall_equilibrium"
    ) in public_callables


def test_support_modules_are_hash_bound_without_becoming_assets():
    root = Path(__file__).resolve().parents[1]
    records = json.loads((root / "provenance/admitted-assets.json").read_text(encoding="utf-8"))
    public_modules = {
        record["public_callable"].rsplit(".", 1)[0]
        for record in records["integrations"]
    }
    assert {item["module"] for item in records["support_modules"]} == {
        "scirel._composition",
        "scirel._validation",
    }
    for support in records["support_modules"]:
        assert support["module"] not in public_modules
        path = root / "src" / Path(*support["module"].split(".")).with_suffix(".py")
        source = path.read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(source).hexdigest() == support["library_source_lf_sha256"]
