"""Focused checks for the scientific capability progress contract."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from validate_capability_progress import (
    _validate_comparison_receipt,
    _file_hash_digest,
    _validate_execution_rebind,
    _validate_full_freeze_delivery_surface,
    bundle_file_hashes,
    compute_bundle_digest,
    compute_file_sha256,
    load_progress_document,
    validate_external_bindings,
    validate_progress_document,
)


def frozen_document() -> dict:
    return {
        "schema_version": "1.0",
        "snapshot_id": "freeze-001",
        "scope": {
            "scope_id": "bounded-source-scope",
            "census_status": "frozen",
            "scope_manifest_digest": "a" * 64,
            "capability_evidence_matrix_digest": "b" * 64,
            "ledger_digest": "c" * 64,
            "bundle_digest": "d" * 64,
            "source_partitions_mapped": 2,
            "source_partitions_total": 2,
            "target_paths_traced": 1,
            "target_paths_total": 1,
        },
        "source_partitions": [
            {
                "partition_id": "S-SCIENCE",
                "material_role": "scientific_source",
                "status": "mapped",
                "evidence_refs": ["manifest:science"],
            },
            {
                "partition_id": "S-SUPPORT",
                "material_role": "support_runtime",
                "status": "mapped",
                "evidence_refs": ["manifest:support"],
            },
        ],
        "equation_anchors": [
            {
                "equation_id": "EQ-FORCE-BALANCE",
                "equation_role": "governing_equation",
                "target_paths": ["T-EQUILIBRIUM"],
                "authority_refs": ["source:eq_solve"],
            }
        ],
        "work_units": [
            {
                "capability_id": "C-EQUATION",
                "anchor_kind": "governing_equation",
                "node_role": "operator_node",
                "equation_anchor_ids": ["EQ-FORCE-BALANCE"],
                "priority": "P0_primary_solution",
                "disposition": "emitted",
                "required_for": ["T-EQUILIBRIUM"],
                "gates": {
                    "mapped": "passed",
                    "contract": "passed",
                    "implemented": "passed",
                    "source_free": "passed",
                    "independent_validation": "passed",
                },
                "blocker": None,
            },
            {
                "capability_id": "C-DIAGNOSTIC",
                "anchor_kind": "diagnostic_definition",
                "node_role": "operator_node",
                "equation_anchor_ids": ["EQ-FORCE-BALANCE"],
                "priority": "P3_principal_diagnostic",
                "disposition": "terminally_classified",
                "required_for": [],
                "gates": {
                    "mapped": "passed",
                    "contract": "not_applicable",
                    "implemented": "not_applicable",
                    "source_free": "not_applicable",
                    "independent_validation": "not_applicable",
                },
                "blocker": {
                    "classification": "cannot_complete",
                    "reason": "source has no defined terminal result",
                    "next_action": "none unless the source contract changes",
                    "owner": "external_evidence",
                },
            },
        ],
        "web_edges": [],
        "coverage_partitions": [
            {
                "partition_id": "B-PRIMARY",
                "required_for": ["T-EQUILIBRIUM"],
                "status": "proved",
            }
        ],
        "target_paths": [
            {
                "target_id": "T-EQUILIBRIUM",
                "trace_status": "traced",
                "evidence_refs": ["target:equilibrium"],
                "required_capabilities": ["C-EQUATION"],
                "status": "passed",
                "earliest_unresolved": None,
                "reassembly_evidence": reassembly_evidence(),
            }
        ],
        "active_frontier": [],
        "milestones": completed_milestones(),
        "progress": {
            "census_maturity": 1.0,
            "extraction_resolution": 1.0,
            "usable_core_closure": 1.0,
            "composition_edge_closure": 1.0,
            "branch_domain_coverage": 1.0,
            "target_path_reassembly": 1.0,
            "overall": 1.0,
        },
    }


def completed_milestones() -> dict:
    return {
        "M0_equation_census": {"status": "completed"},
        "M1_minimal_golden_path": {
            "status": "completed",
            "target_ids": ["T-EQUILIBRIUM"],
        },
        "M2_replaceable_scientific_slices": {
            "status": "completed",
            "capability_ids": ["C-EQUATION"],
            "edge_ids": [],
        },
        "M3_branch_lifecycle_expansion": {
            "status": "completed",
            "partition_ids": ["B-PRIMARY"],
        },
        "M4_extraction_freeze": {"status": "completed"},
    }


def reassembly_evidence() -> dict:
    def case(case_id: str, kind: str, input_digest: str) -> dict:
        return {
            "case_id": case_id,
            "kind": kind,
            "source_oracle_kind": "source_runtime",
            "source_oracle_ref": f"evidence:source:{case_id}",
            "source_oracle_sha256": "3" * 64,
            "bundle_execution_ref": f"evidence:bundle:{case_id}",
            "bundle_execution_sha256": "4" * 64,
            "comparison_receipt_ref": f"evidence:comparison:{case_id}",
            "comparison_receipt_sha256": "5" * 64,
            "tolerance_contract_ref": "contract:equilibrium-terminal-tolerances",
            "tolerance_contract_sha256": "6" * 64,
            "source_input_digest": input_digest,
            "bundle_input_digest": input_digest,
            "compared_terminal_output_ids": ["equilibrium_state"],
            "status": "passed",
        }

    return {
        "source_scope_digest": "a" * 64,
        "bundle_digest": "d" * 64,
        "entry_kind": "terminal_operator",
        "entry_asset_refs": ["operators/equilibrium@sha256:example"],
        "terminal_output_ids": ["equilibrium_state"],
        "cases": [
            case("canonical-001", "canonical", "1" * 64),
            case("holdout-001", "sealed_holdout", "2" * 64),
        ],
    }


def check_report_only_execution_rebind() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        bundle = root / "candidate_bundle"
        evidence = root / "evidence"
        operator = bundle / "operators" / "example" / "scientific_operator.py"
        operator.parent.mkdir(parents=True)
        evidence.mkdir()
        operator.write_text("def calculate(): return 1\n", encoding="utf-8")
        report = bundle / "extraction_report.md"
        report.write_text("initial report\n", encoding="utf-8")
        baseline_files = bundle_file_hashes(bundle)
        baseline_digest = compute_bundle_digest(bundle)
        manifest_path = evidence / "baseline-files.json"
        manifest_path.write_text(
            json.dumps({
                "schema_version": "scirel.bundle-file-manifest.v1",
                "bundle_digest": baseline_digest,
                "files": baseline_files,
            }),
            encoding="utf-8",
        )
        report.write_text("corrected report\n", encoding="utf-8")
        current_digest = compute_bundle_digest(bundle)
        case = {
            "case_id": "canonical",
            "kind": "canonical",
            "source_input_digest": "b" * 64,
            "bundle_input_digest": "b" * 64,
            "tolerance_contract_sha256": "c" * 64,
            "compared_terminal_output_ids": ["result"],
            "bundle_execution_ref": "evidence/execution.json",
            "bundle_execution_sha256": "d" * 64,
        }
        execution = {
            "bundle_digest": baseline_digest,
            "cases": {"T-EXAMPLE::canonical": {"input_digest": "b" * 64}},
        }
        probe = {"image_id": "sha256:" + "e" * 64}
        receipt = {
            "target_id": "T-EXAMPLE",
            "bundle_digest": current_digest,
            "source_scope_digest": "a" * 64,
            "execution_rebind_ref": "evidence/rebind.json",
            "bundle_execution_receipt_ref": "evidence/probe.json",
            "bundle_execution_receipt_sha256": "f" * 64,
        }
        rebind = {
            "schema_version": "scirel.execution-rebind.v1",
            "target_id": receipt["target_id"],
            "case_id": case["case_id"],
            "baseline_bundle_digest": baseline_digest,
            "current_bundle_digest": current_digest,
            "baseline_manifest_ref": "evidence/baseline-files.json",
            "baseline_manifest_sha256": compute_file_sha256(manifest_path),
            "changed_report_paths": ["extraction_report.md"],
            "scientific_identity_digest": _file_hash_digest({
                path: digest for path, digest in baseline_files.items()
                if path != "extraction_report.md"
            }),
            "source_scope_digest": receipt["source_scope_digest"],
            "source_input_digest": case["source_input_digest"],
            "bundle_input_digest": case["bundle_input_digest"],
            "tolerance_contract_digest": case["tolerance_contract_sha256"],
            "bundle_execution_ref": case["bundle_execution_ref"],
            "bundle_execution_sha256": case["bundle_execution_sha256"],
            "bundle_execution_receipt_ref": receipt["bundle_execution_receipt_ref"],
            "bundle_execution_receipt_sha256": receipt["bundle_execution_receipt_sha256"],
            "runtime_image_id": probe["image_id"],
        }
        rebind_path = evidence / "rebind.json"

        def verify() -> list[str]:
            rebind_path.write_text(json.dumps(rebind), encoding="utf-8")
            receipt["execution_rebind_sha256"] = compute_file_sha256(rebind_path)
            errors: list[str] = []
            _validate_execution_rebind(
                receipt, case, execution, probe,
                run_root=root, bundle_root=bundle, errors=errors,
            )
            return errors

        assert verify() == []
        regressions: list[str] = []
        # Without the original file manifest, changed code must not be able to
        # claim that only its report moved or changed.
        operator.write_text("def calculate(): return 999\n", encoding="utf-8")
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        for missing_ref in (None, ""):
            if missing_ref is None:
                rebind.pop("baseline_manifest_ref", None)
            else:
                rebind["baseline_manifest_ref"] = missing_ref
            if not any("baseline_manifest_ref is required" in error for error in verify()):
                regressions.append(f"missing baseline manifest reference accepted: {missing_ref!r}")
        rebind["baseline_manifest_ref"] = "evidence/baseline-files.json"
        operator.write_text("def calculate(): return 1\n", encoding="utf-8")
        receipt["bundle_digest"] = current_digest
        rebind["current_bundle_digest"] = current_digest

        # The first final report is legitimately absent from the execution
        # bundle. Adding it must retain the same scientific execution evidence.
        without_report = {path: value for path, value in baseline_files.items()
                          if path != "extraction_report.md"}
        no_report_digest = _file_hash_digest(without_report)
        manifest_path.write_text(json.dumps({
            "schema_version": "scirel.bundle-file-manifest.v1",
            "bundle_digest": no_report_digest,
            "files": without_report,
        }), encoding="utf-8")
        execution["bundle_digest"] = no_report_digest
        rebind["baseline_bundle_digest"] = no_report_digest
        rebind["baseline_manifest_sha256"] = compute_file_sha256(manifest_path)
        report_added_errors = verify()
        if report_added_errors:
            regressions.append(f"first final report rejected: {report_added_errors}")

        manifest_path.write_text(json.dumps({
            "schema_version": "scirel.bundle-file-manifest.v1",
            "bundle_digest": baseline_digest,
            "files": baseline_files,
        }), encoding="utf-8")
        execution["bundle_digest"] = baseline_digest
        rebind["baseline_bundle_digest"] = baseline_digest
        rebind["baseline_manifest_sha256"] = compute_file_sha256(manifest_path)
        report.unlink()
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        report_removed_errors = verify()
        if report_removed_errors:
            regressions.append(f"report removal rejected: {report_removed_errors}")
        report.write_text("corrected report\n", encoding="utf-8")

        # A code file addition/removal is still a scientific file-set change.
        extra_code = operator.parent / "new_relation.py"
        extra_code.write_text("def new_relation(): return 2\n", encoding="utf-8")
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        assert any("only to root project reports" in error for error in verify())
        extra_code.unlink()
        operator.unlink()
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        assert any("only to root project reports" in error for error in verify())
        operator.write_text("def calculate(): return 1\n", encoding="utf-8")
        receipt["bundle_digest"] = current_digest
        rebind["current_bundle_digest"] = current_digest
        assert not regressions, regressions
        assert verify() == []
        execution_path = evidence / "execution.json"
        execution_path.write_text(json.dumps(execution), encoding="utf-8")
        probe_path = evidence / "probe.json"
        probe_path.write_text(json.dumps({"exit_code": 0, **probe}), encoding="utf-8")
        case["bundle_execution_sha256"] = compute_file_sha256(execution_path)
        receipt["bundle_execution_receipt_sha256"] = compute_file_sha256(probe_path)
        rebind["bundle_execution_sha256"] = case["bundle_execution_sha256"]
        rebind["bundle_execution_receipt_sha256"] = receipt["bundle_execution_receipt_sha256"]
        assert verify() == []
        comparison = {
            **receipt,
            "schema_version": "scirel.extraction-reassembly-comparison.v2",
            "status": "passed",
            "case_id": case["case_id"],
            "kind": case["kind"],
            "source_input_digest": case["source_input_digest"],
            "bundle_input_digest": case["bundle_input_digest"],
            "tolerance_contract_digest": case["tolerance_contract_sha256"],
            "bundle_execution_ref": case["bundle_execution_ref"],
            "bundle_execution_sha256": case["bundle_execution_sha256"],
            "terminal_output_ids": ["result"],
            "comparisons": [{
                "output_id": "result", "status": "passed", "metric": "absolute_error",
                "observed_error": 0.0, "allowed_error": 1.0,
            }],
        }
        comparison_path = evidence / "comparison.json"

        def validate_comparison() -> list[str]:
            comparison_path.write_text(json.dumps(comparison), encoding="utf-8")
            errors: list[str] = []
            _validate_comparison_receipt(
                comparison_path, run_root=root, bundle_root=bundle,
                bundle_execution_path=execution_path, target_id="T-EXAMPLE",
                case=case, scope_manifest_digest=receipt["source_scope_digest"],
                bundle_digest=current_digest, require_detailed=True, errors=errors,
            )
            return errors

        assert validate_comparison() == []
        comparison.pop("execution_rebind_ref")
        assert any("rebind is required" in error for error in validate_comparison())
        comparison["execution_rebind_ref"] = receipt["execution_rebind_ref"]
        operator.write_text("def calculate(): return 2\n", encoding="utf-8")
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        assert any("only to root project reports" in error for error in verify())
        operator.write_text("def calculate(): return 1\n", encoding="utf-8")
        receipt["bundle_digest"] = current_digest
        rebind["current_bundle_digest"] = current_digest
        altered_case = dict(case, bundle_input_digest="0" * 64)
        case, saved_case = altered_case, case
        assert any("bundle_input_digest" in error for error in verify())
        case = saved_case
        probe["image_id"] = "sha256:" + "0" * 64
        assert any("runtime_image_id" in error for error in verify())

        probe["image_id"] = "sha256:" + "e" * 64
        document_path = operator.parent / "operator.md"
        document_path.write_text("final source-backed contract\n", encoding="utf-8")
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        rebind["schema_version"] = "scirel.execution-rebind.v2"
        rebind.pop("changed_report_paths")
        changed_documents = ["extraction_report.md", "operators/example/operator.md"]
        rebind["changed_document_paths"] = changed_documents
        review = {
            "schema_version": "scirel.documentation-rebind-review.v1",
            "review_id": "review-001",
            "reviewer_role": "independent_subagent",
            "verdict": "pass",
            "source_scope_digest": receipt["source_scope_digest"],
            "baseline_bundle_digest": baseline_digest,
            "current_bundle_digest": receipt["bundle_digest"],
            "scientific_identity_digest": rebind["scientific_identity_digest"],
            "reviewed_document_paths": changed_documents,
            "code_and_science_consistent": True,
            "findings": [],
        }
        review_path = evidence / "documentation-review.json"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        rebind["documentation_review_ref"] = "evidence/documentation-review.json"
        rebind["documentation_review_sha256"] = compute_file_sha256(review_path)
        assert verify() == []
        current_digest = receipt["bundle_digest"]
        comparison["bundle_digest"] = current_digest
        comparison["execution_rebind_sha256"] = receipt["execution_rebind_sha256"]
        assert validate_comparison() == []

        saved_case = case
        saved_cases = execution["cases"]
        for jcase in (1, 2, 3):
            for kind in ("canonical", "sealed_holdout"):
                case_id = f"jcase{jcase}-{kind}"
                case = dict(saved_case, case_id=case_id, kind=kind)
                rebind["case_id"] = case_id
                row = {
                    "target_id": "T-EXAMPLE",
                    "jcase": jcase,
                    "case_id": kind,
                    "controls": {"case_tag": case_id, "case_kind": kind, "jcase": jcase},
                    "input_digest": case["bundle_input_digest"],
                }
                execution["cases"] = {case_id: row}
                assert verify() == []
                for container, field, wrong_value in (
                    (row, "target_id", "T-OTHER"),
                    (row, "jcase", jcase + 1),
                    (row, "case_id", "sealed_holdout" if kind == "canonical" else "canonical"),
                    (row["controls"], "case_tag", "other-case"),
                    (row["controls"], "case_kind", "other-kind"),
                    (row["controls"], "jcase", jcase + 1),
                    (row, "input_digest", "0" * 64),
                ):
                    original = container[field]
                    container[field] = wrong_value
                    assert any("bundle_input_digest" in error for error in verify())
                    container[field] = original
                execution["cases"] = {"other-case": row}
                assert any("bundle_input_digest" in error for error in verify())
                execution["cases"] = {case_id: row, f"T-EXAMPLE::{case_id}": {"input_digest": "0" * 64}}
                assert any("bundle_input_digest" in error for error in verify())
        case = saved_case
        rebind["case_id"] = case["case_id"]
        execution["cases"] = saved_cases

        rebind.pop("documentation_review_ref")
        assert any("documentation review" in error for error in verify())
        rebind["documentation_review_ref"] = "evidence/documentation-review.json"
        review["verdict"] = "fail"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        rebind["documentation_review_sha256"] = compute_file_sha256(review_path)
        assert any("documentation_review.verdict" in error for error in verify())
        review["verdict"] = "pass"
        review_path.write_text(json.dumps(review), encoding="utf-8")
        rebind["documentation_review_sha256"] = compute_file_sha256(review_path)
        operator.write_text("def calculate(): return 2\n", encoding="utf-8")
        receipt["bundle_digest"] = compute_bundle_digest(bundle)
        rebind["current_bundle_digest"] = receipt["bundle_digest"]
        changed_code_errors = verify()
        assert any("only to documentation files" in error for error in changed_code_errors), changed_code_errors


def check_full_freeze_requires_entry_receipt_reference() -> None:
    with TemporaryDirectory() as directory:
        bundle = Path(directory) / "candidate_bundle"
        bundle.mkdir()
        (bundle / "asset_entry.py").write_text("# entry fixture\n", encoding="utf-8")
        for binding in ({}, {"receipt_ref": ""}):
            document = {"closure_signal": {
                "kind": "full_freeze", "asset_entry_validation": binding,
            }}
            errors: list[str] = []
            _validate_full_freeze_delivery_surface(document, bundle, errors)
            assert any("asset_entry_validation.receipt_ref is required" in error
                       for error in errors), errors


def main() -> None:
    check_full_freeze_requires_entry_receipt_reference()
    frozen = frozen_document()
    assert validate_progress_document(frozen) == []

    incomplete = deepcopy(frozen)
    incomplete.pop("milestones")
    assert validate_progress_document(incomplete)

    staged_frozen = deepcopy(frozen)
    assert validate_progress_document(staged_frozen) == []

    current_major, current_minor = map(int, staged_frozen["schema_version"].split("."))
    unsupported_versions = (
        f"{current_major}.{current_minor + 1}",
        f"{current_major + 1}.{current_minor}",
        f"{current_major}.{current_minor}.0",
        "latest",
        "",
        None,
    )
    for unsupported_version in unsupported_versions:
        unsupported = deepcopy(staged_frozen)
        unsupported["schema_version"] = unsupported_version
        assert validate_progress_document(unsupported)

    missing_reassembly = deepcopy(staged_frozen)
    missing_reassembly["target_paths"][0].pop("reassembly_evidence")
    assert any(
        "reassembly_evidence must be an object" in error
        for error in validate_progress_document(missing_reassembly)
    )

    missing_holdout = deepcopy(staged_frozen)
    missing_holdout["target_paths"][0]["reassembly_evidence"]["cases"] = [
        missing_holdout["target_paths"][0]["reassembly_evidence"]["cases"][0]
    ]
    assert any(
        "missing required kinds" in error
        for error in validate_progress_document(missing_holdout)
    )

    mismatched_inputs = deepcopy(staged_frozen)
    mismatched_inputs["target_paths"][0]["reassembly_evidence"]["cases"][1][
        "bundle_input_digest"
    ] = "3" * 64
    assert any(
        "source_input_digest and bundle_input_digest must be identical" in error
        for error in validate_progress_document(mismatched_inputs)
    )

    wrong_bundle = deepcopy(staged_frozen)
    wrong_bundle["target_paths"][0]["reassembly_evidence"]["bundle_digest"] = "e" * 64
    assert any(
        "bundle_digest must match scope.bundle_digest" in error
        for error in validate_progress_document(wrong_bundle)
    )

    full_freeze_signal = deepcopy(staged_frozen)
    full_freeze_signal["closure_signal"] = {
        "kind": "full_freeze",
        "claim_ceiling": "full declared source scope",
        "next_action": "none unless the source scope changes",
        "reopen_condition": "a new source snapshot or explicit scope revision",
        "owner": "scientific-operator-review",
        "evidence_refs": ["evidence:freeze-001"],
        "delivered_target_ids": ["T-EQUILIBRIUM"],
        "unresolved_ids": [],
    }
    assert validate_progress_document(full_freeze_signal, require_closure_signal=True) == []

    bounded_signal = deepcopy(staged_frozen)
    bounded_signal["closure_signal"] = {
        "kind": "bounded_delivery",
        "claim_ceiling": "delivered target paths only",
        "next_action": "submit this batch to SciRel assembly",
        "reopen_condition": "assembly identifies a missing capability or full_freeze is required",
        "owner": "scientific-computation-asset-extraction",
        "evidence_refs": ["evidence:bounded-001"],
        "delivered_target_ids": ["T-EQUILIBRIUM"],
        "unresolved_ids": [],
        "bounded_delivery_review": {
            "receipt_ref": "evidence/bounded-review.json",
            "receipt_sha256": "7" * 64,
        },
    }
    assert validate_progress_document(bounded_signal, require_closure_signal=True) == []

    missing_review = deepcopy(bounded_signal)
    missing_review["closure_signal"].pop("bounded_delivery_review")
    assert any(
        "requires bounded_delivery_review" in error
        for error in validate_progress_document(missing_review, require_closure_signal=True)
    )

    partial_delivered = deepcopy(bounded_signal)
    partial_delivered["target_paths"][0]["status"] = "partial"
    partial_delivered["target_paths"][0]["earliest_unresolved"] = "C-EQUATION"
    assert any(
        "requires every delivered target to have status=passed" in error
        for error in validate_progress_document(partial_delivered, require_closure_signal=True)
    )

    state_bound_freeze = deepcopy(full_freeze_signal)
    state_bound_freeze["state"] = "full_freeze"
    state_bound_freeze["state_digest"] = "e" * 64
    assert validate_progress_document(state_bound_freeze, require_closure_signal=True) == []

    contradictory_state = deepcopy(state_bound_freeze)
    contradictory_state["state"] = "active"
    assert any(
        "state must equal closure_signal.kind" in error
        for error in validate_progress_document(contradictory_state, require_closure_signal=True)
    )

    missing_closure_signal = deepcopy(full_freeze_signal)
    missing_closure_signal.pop("closure_signal")
    assert any(
        "closure_signal is required" in error
        for error in validate_progress_document(
            missing_closure_signal, require_closure_signal=True
        )
    )

    missing_milestones = deepcopy(staged_frozen)
    missing_milestones.pop("milestones")
    assert any(
        "milestones" in error
        for error in validate_progress_document(missing_milestones)
    )

    provisional = deepcopy(frozen)
    provisional["snapshot_id"] = "checkpoint-001"
    provisional["scope"]["census_status"] = "provisional"
    provisional["scope"]["source_partitions_mapped"] = 1
    provisional["source_partitions"][1]["status"] = "unmapped"
    provisional["work_units"][0]["disposition"] = "in_progress"
    provisional["work_units"][0]["gates"]["implemented"] = "pending"
    provisional["work_units"][0]["gates"]["source_free"] = "pending"
    provisional["work_units"][0]["gates"]["independent_validation"] = "pending"
    provisional["work_units"][0]["blocker"] = {
        "classification": "extraction_gap",
        "reason": "state producer is not emitted",
        "next_action": "capture the declared producer boundary",
        "owner": "scientific-runtime-dataset-construction",
    }
    provisional["target_paths"][0]["status"] = "partial"
    provisional["target_paths"][0]["earliest_unresolved"] = "C-EQUATION"
    provisional["active_frontier"] = [
        {
            "target_id": "T-EQUILIBRIUM",
            "capability_or_edge": "C-EQUATION",
            "classification": "extraction_gap",
            "reason": "state producer is not emitted",
            "next_action": "capture the declared producer boundary",
            "owner": "scientific-runtime-dataset-construction",
        }
    ]
    provisional["progress"] = {
        "census_maturity": 0.5,
        "extraction_resolution": 0.5,
        "usable_core_closure": 0.0,
        "composition_edge_closure": 1.0,
        "branch_domain_coverage": 1.0,
        "target_path_reassembly": 0.0,
        "overall": None,
    }
    staged_provisional = deepcopy(provisional)
    staged_provisional["milestones"] = completed_milestones()
    staged_provisional["milestones"]["M0_equation_census"]["status"] = "in_progress"
    staged_provisional["milestones"]["M1_minimal_golden_path"]["status"] = "in_progress"
    staged_provisional["milestones"]["M2_replaceable_scientific_slices"][
        "status"
    ] = "in_progress"
    staged_provisional["milestones"]["M3_branch_lifecycle_expansion"][
        "status"
    ] = "in_progress"
    staged_provisional["milestones"]["M4_extraction_freeze"]["status"] = "pending"
    assert validate_progress_document(staged_provisional) == []

    staged_provisional["closure_signal"] = {
        "kind": "active",
        "claim_ceiling": "lower-bound checkpoint only",
        "next_action": "capture the declared producer boundary",
        "reopen_condition": "the next source probe or contract revision",
        "owner": "scientific-runtime-dataset-construction",
        "evidence_refs": ["evidence:checkpoint-001"],
        "delivered_target_ids": [],
        "unresolved_ids": ["C-EQUATION"],
    }
    assert validate_progress_document(staged_provisional, require_closure_signal=True) == []

    reopened = deepcopy(staged_provisional)
    reopened["state"] = "reopened"
    reopened["state_digest"] = "f" * 64
    reopened["reopened_from_digest"] = "d" * 64
    reopened["boundary_events"] = [
        {
            "event_id": "boundary-001",
            "kind": "tooling_defect",
            "observed_claim": "validator rejected a valid package shape",
            "evidence_refs": ["test:validator-001"],
            "current_action": "repair the validator fixture",
            "forbidden_action": "change the scientific contract",
            "owner": "scientific-computation-asset-extraction",
            "reopen_condition": "validator regression passes",
            "predecessor_digest": "d" * 64,
        }
    ]
    assert validate_progress_document(reopened, require_closure_signal=True) == []

    malformed_event = deepcopy(reopened)
    malformed_event["boundary_events"][0]["evidence_refs"] = []
    assert any(
        "boundary_events[0].evidence_refs" in error
        for error in validate_progress_document(malformed_event, require_closure_signal=True)
    )

    false_milestone_completion = deepcopy(staged_provisional)
    false_milestone_completion["milestones"]["M1_minimal_golden_path"][
        "status"
    ] = "completed"
    assert any(
        "M1_minimal_golden_path.status" in error
        for error in validate_progress_document(false_milestone_completion)
    )

    unknown_milestone_reference = deepcopy(staged_frozen)
    unknown_milestone_reference["milestones"]["M2_replaceable_scientific_slices"][
        "capability_ids"
    ] = ["C-NOT-FOUND"]
    assert any(
        "M2_replaceable_scientific_slices.capability_ids" in error
        for error in validate_progress_document(unknown_milestone_reference)
    )

    capability_contradiction = deepcopy(staged_frozen)
    capability_contradiction["work_units"][0]["disposition"] = "in_progress"
    capability_contradiction["work_units"][0]["gates"]["implemented"] = "pending"
    capability_contradiction["work_units"][0]["blocker"] = {
        "classification": "extraction_gap",
        "reason": "required producer is not emitted",
        "next_action": "emit and validate the producer",
        "owner": "scientific-computation-asset-extraction",
    }
    capability_contradiction["progress"]["extraction_resolution"] = 0.5
    capability_contradiction["progress"]["usable_core_closure"] = 0.0
    capability_contradiction["progress"]["overall"] = 0.0
    assert any(
        "passed target requires fully passed capability" in error
        for error in validate_progress_document(capability_contradiction)
    )

    milestone_ordering = deepcopy(staged_frozen)
    milestone_ordering["scope"]["census_status"] = "provisional"
    milestone_ordering["scope"]["source_partitions_mapped"] = 1
    milestone_ordering["source_partitions"][1]["status"] = "unmapped"
    milestone_ordering["progress"]["census_maturity"] = 0.5
    milestone_ordering["progress"]["overall"] = None
    milestone_ordering["milestones"]["M0_equation_census"]["status"] = "in_progress"
    milestone_ordering["milestones"]["M1_minimal_golden_path"]["status"] = "completed"
    milestone_ordering["milestones"]["M2_replaceable_scientific_slices"][
        "status"
    ] = "completed"
    milestone_ordering["milestones"]["M3_branch_lifecycle_expansion"][
        "status"
    ] = "completed"
    milestone_ordering["milestones"]["M4_extraction_freeze"]["status"] = "pending"
    assert any(
        "M1_minimal_golden_path.status" in error
        for error in validate_progress_document(milestone_ordering)
    )

    omitted_internal_edge = deepcopy(staged_frozen)
    update_unit = deepcopy(omitted_internal_edge["work_units"][0])
    update_unit["capability_id"] = "C-UPDATE"
    update_unit["anchor_kind"] = "numerical_state_transition"
    omitted_internal_edge["work_units"].append(update_unit)
    omitted_internal_edge["target_paths"][0]["required_capabilities"].append("C-UPDATE")
    omitted_internal_edge["web_edges"] = [
        {
            "edge_id": "E-EQUATION-TO-UPDATE",
            "from_node_id": "C-EQUATION",
            "from_port": "residual",
            "to_node_id": "C-UPDATE",
            "to_port": "residual",
            "edge_role": "port_binding",
            "required_for": ["T-EQUILIBRIUM"],
            "closure_status": "proved",
            "blocker": None,
        }
    ]
    omitted_internal_edge["milestones"]["M2_replaceable_scientific_slices"][
        "capability_ids"
    ] = ["C-EQUATION", "C-UPDATE"]
    assert any(
        "edge_ids must equal the material incident edges" in error
        for error in validate_progress_document(omitted_internal_edge)
    )

    omitted_branch_partition = deepcopy(staged_frozen)
    omitted_branch_partition["coverage_partitions"].append(
        {
            "partition_id": "B-HOLDOUT",
            "required_for": ["T-EQUILIBRIUM"],
            "status": "proved",
        }
    )
    assert any(
        "partition_ids must equal the declared coverage denominator" in error
        for error in validate_progress_document(omitted_branch_partition)
    )

    pending_branch_work = deepcopy(staged_frozen)
    pending_branch_work["coverage_partitions"][0]["status"] = "pending"
    pending_branch_work["progress"]["branch_domain_coverage"] = 0.0
    pending_branch_work["progress"]["overall"] = 0.0
    pending_branch_work["milestones"]["M3_branch_lifecycle_expansion"][
        "status"
    ] = "in_progress"
    pending_branch_work["milestones"]["M4_extraction_freeze"]["status"] = "pending"
    assert validate_progress_document(pending_branch_work) == []

    wrong_total = deepcopy(frozen)
    wrong_total["progress"]["extraction_resolution"] = 0.5
    assert any("extraction_resolution" in error for error in validate_progress_document(wrong_total))

    denominator_gaming = deepcopy(frozen)
    denominator_gaming["scope"]["source_partitions_total"] = 1
    assert any("source_partitions_total" in error for error in validate_progress_document(denominator_gaming))

    unbound_snapshot = deepcopy(frozen)
    unbound_snapshot["scope"]["scope_manifest_digest"] = "not-a-digest"
    assert any("scope_manifest_digest" in error for error in validate_progress_document(unbound_snapshot))

    terminal_inflation = deepcopy(frozen)
    terminal_inflation["work_units"][0]["disposition"] = "terminally_classified"
    terminal_inflation["work_units"][0]["blocker"] = {
        "classification": "cannot_complete",
        "reason": "bounded source defect",
        "next_action": "none unless scientific authority changes",
        "owner": "external_evidence",
    }
    assert any("usable_core_closure" in error for error in validate_progress_document(terminal_inflation))

    missing_frontier = deepcopy(provisional)
    missing_frontier["active_frontier"] = []
    assert any("active_frontier" in error for error in validate_progress_document(missing_frontier))

    fake_frontier = deepcopy(provisional)
    fake_frontier["target_paths"][0]["earliest_unresolved"] = "E-NOT-FOUND"
    fake_frontier["active_frontier"][0]["capability_or_edge"] = "E-NOT-FOUND"
    assert any("earliest_unresolved" in error for error in validate_progress_document(fake_frontier))

    bad_kind = deepcopy(frozen)
    bad_kind["work_units"][0]["anchor_kind"] = "source_file"
    assert any("anchor_kind" in error for error in validate_progress_document(bad_kind))

    detached_node = deepcopy(frozen)
    detached_node["work_units"][0]["equation_anchor_ids"] = []
    assert any("equation_anchor_ids" in error for error in validate_progress_document(detached_node))

    fake_scientific_leaf = deepcopy(frozen)
    fake_scientific_leaf["work_units"][0]["node_role"] = "task_graph_node"
    assert any("node_role" in error for error in validate_progress_document(fake_scientific_leaf))

    unnamed_subweb = deepcopy(frozen)
    unnamed_subweb["work_units"][0]["node_role"] = "task_graph_subweb"
    assert any("participating_node_ids" in error for error in validate_progress_document(unnamed_subweb))
    assert any("participating_edge_ids" in error for error in validate_progress_document(unnamed_subweb))

    named_subweb = deepcopy(unnamed_subweb)
    update_node = deepcopy(named_subweb["work_units"][0])
    update_node["capability_id"] = "C-UPDATE"
    update_node["anchor_kind"] = "numerical_state_transition"
    update_node["node_role"] = "operator_node"
    update_node["priority"] = "P3_principal_diagnostic"
    update_node.pop("participating_node_ids", None)
    update_node.pop("participating_edge_ids", None)
    named_subweb["work_units"].append(update_node)
    named_subweb["work_units"][0]["participating_node_ids"] = ["C-DIAGNOSTIC", "C-UPDATE"]
    named_subweb["work_units"][0]["participating_edge_ids"] = ["E-DIAGNOSTIC-TO-UPDATE"]
    named_subweb["web_edges"] = [
        {
            "edge_id": "E-DIAGNOSTIC-TO-UPDATE",
            "from_node_id": "C-DIAGNOSTIC",
            "from_port": "diagnostic",
            "to_node_id": "C-UPDATE",
            "to_port": "input_state",
            "edge_role": "port_binding",
            "required_for": ["T-EQUILIBRIUM"],
            "closure_status": "proved",
            "blocker": None,
        }
    ]
    assert validate_progress_document(named_subweb) == []

    imaginary_membership = deepcopy(named_subweb)
    imaginary_membership["work_units"][0]["participating_node_ids"] = ["C-NOT-FOUND"]
    assert any("unknown ids" in error for error in validate_progress_document(imaginary_membership))

    edge_outside_subweb = deepcopy(named_subweb)
    edge_outside_subweb["web_edges"][0]["from_node_id"] = "C-EQUATION"
    assert any("endpoints" in error for error in validate_progress_document(edge_outside_subweb))

    unresolved_edge_on_passed_target = deepcopy(named_subweb)
    unresolved_edge_on_passed_target["web_edges"][0]["closure_status"] = "blocked"
    unresolved_edge_on_passed_target["web_edges"][0]["blocker"] = {
        "classification": "ai_completable_glue",
        "reason": "port adapter is not emitted",
        "next_action": "implement and validate the bounded adapter",
        "owner": "scientific-computation-asset-extraction",
    }
    unresolved_edge_on_passed_target["progress"]["composition_edge_closure"] = 0.0
    unresolved_edge_on_passed_target["progress"]["overall"] = 0.0
    assert any(
        "passed target" in error
        for error in validate_progress_document(unresolved_edge_on_passed_target)
    )

    empty_branch_denominator = deepcopy(frozen)
    empty_branch_denominator["coverage_partitions"] = []
    assert any(
        "coverage_partitions must be a non-empty list" in error
        for error in validate_progress_document(empty_branch_denominator)
    )

    with TemporaryDirectory() as temp_dir:
        progress_path = Path(temp_dir) / "capability_progress.json"
        progress_path.write_text(json.dumps(frozen), encoding="utf-8")
        loaded, error = load_progress_document(progress_path, max_bytes=16)
        assert loaded is None
        assert error is not None and "exceeds" in error

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        scope_manifest = root / "scope_manifest.json"
        evidence_matrix = root / "capability_evidence_matrix.md"
        ledger = root / "extraction_ledger.md"
        bundle_root = root / "bundle"
        bundle_root.mkdir()
        scope_manifest.write_text("scope", encoding="utf-8")
        evidence_matrix.write_text("matrix", encoding="utf-8")
        ledger.write_text("ledger", encoding="utf-8")
        (bundle_root / "asset.txt").write_text("asset", encoding="utf-8")
        bound = deepcopy(provisional)
        bound["scope"]["scope_manifest_digest"] = compute_file_sha256(scope_manifest)
        bound["scope"]["capability_evidence_matrix_digest"] = compute_file_sha256(
            evidence_matrix
        )
        bound["scope"]["ledger_digest"] = compute_file_sha256(ledger)
        bound["scope"]["bundle_digest"] = compute_bundle_digest(bundle_root)
        assert validate_external_bindings(
            bound,
            scope_manifest=scope_manifest,
            capability_evidence_matrix=evidence_matrix,
            ledger=ledger,
            bundle_root=bundle_root,
        ) == []
        (bundle_root / "asset.txt").write_text("tampered", encoding="utf-8")
        assert any(
            "bundle_digest" in error
            for error in validate_external_bindings(
                bound,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        scope_manifest = root / "scope_manifest.json"
        evidence_matrix = root / "capability_evidence_matrix.md"
        ledger = root / "extraction_ledger.md"
        bundle_root = root / "candidate_bundle"
        evidence_root = root / "evidence"
        bundle_root.mkdir()
        evidence_root.mkdir()
        scope_manifest.write_text("scope", encoding="utf-8")
        evidence_matrix.write_text("matrix", encoding="utf-8")
        ledger.write_text("ledger", encoding="utf-8")
        (bundle_root / "asset.txt").write_text("asset", encoding="utf-8")
        (bundle_root / "asset_entry.py").write_text(
            "def load_asset_bundle(root=None):\n    return None\n",
            encoding="utf-8",
        )

        externally_bound = deepcopy(full_freeze_signal)
        externally_bound["scope"]["scope_manifest_digest"] = compute_file_sha256(scope_manifest)
        externally_bound["scope"]["capability_evidence_matrix_digest"] = compute_file_sha256(
            evidence_matrix
        )
        externally_bound["scope"]["ledger_digest"] = compute_file_sha256(ledger)
        externally_bound["scope"]["bundle_digest"] = compute_bundle_digest(bundle_root)
        entry_receipt_path = evidence_root / "asset-entry-validation.json"
        entry_receipt = {
            "validator": "validate_asset_entry.py",
            "sandbox": "CODEFUSION_ASSET_SANDBOX=1",
            "exit_code": 0,
            "asset_entry_sha256": compute_file_sha256(bundle_root / "asset_entry.py"),
            "bundle_digest": externally_bound["scope"]["bundle_digest"],
            "operators": 1,
            "task_graphs": 0,
        }
        entry_receipt_path.write_text(json.dumps(entry_receipt), encoding="utf-8")
        externally_bound["closure_signal"]["asset_entry_validation"] = {
            "receipt_ref": entry_receipt_path.relative_to(root).as_posix(),
            "receipt_sha256": compute_file_sha256(entry_receipt_path),
        }
        reassembly = externally_bound["target_paths"][0]["reassembly_evidence"]
        reassembly["source_scope_digest"] = externally_bound["scope"]["scope_manifest_digest"]
        reassembly["bundle_digest"] = externally_bound["scope"]["bundle_digest"]

        for case in reassembly["cases"]:
            case_id = case["case_id"]
            source_path = evidence_root / f"{case_id}-source.json"
            bundle_path = evidence_root / f"{case_id}-bundle.json"
            execution_receipt_path = evidence_root / f"{case_id}-execution-receipt.json"
            tolerance_path = evidence_root / f"{case_id}-tolerance.json"
            comparison_path = evidence_root / f"{case_id}-comparison.json"
            source_path.write_text(json.dumps({"source": case_id}), encoding="utf-8")
            bundle_path.write_text(
                json.dumps({"bundle": case_id, "bundle_digest": reassembly["bundle_digest"]}),
                encoding="utf-8",
            )
            execution_receipt_path.write_text(
                json.dumps({"exit_code": 0, "image_id": "sha256:" + "a" * 64}),
                encoding="utf-8",
            )
            tolerance_path.write_text(json.dumps({"rtol": 1e-12}), encoding="utf-8")
            case["source_oracle_ref"] = source_path.relative_to(root).as_posix()
            case["source_oracle_sha256"] = compute_file_sha256(source_path)
            case["bundle_execution_ref"] = bundle_path.relative_to(root).as_posix()
            case["bundle_execution_sha256"] = compute_file_sha256(bundle_path)
            case["tolerance_contract_ref"] = tolerance_path.relative_to(root).as_posix()
            case["tolerance_contract_sha256"] = compute_file_sha256(tolerance_path)
            receipt = {
                "schema_version": "scirel.extraction-reassembly-comparison.v2",
                "status": "passed",
                "target_id": "T-EQUILIBRIUM",
                "case_id": case_id,
                "kind": case["kind"],
                "source_scope_digest": reassembly["source_scope_digest"],
                "bundle_digest": reassembly["bundle_digest"],
                "source_input_digest": case["source_input_digest"],
                "bundle_input_digest": case["bundle_input_digest"],
                "tolerance_contract_digest": case["tolerance_contract_sha256"],
            "bundle_execution_receipt_ref": execution_receipt_path.relative_to(root).as_posix(),
            "bundle_execution_receipt_sha256": compute_file_sha256(execution_receipt_path),
            "bundle_execution_ref": case["bundle_execution_ref"],
            "bundle_execution_sha256": case["bundle_execution_sha256"],
                "terminal_output_ids": case["compared_terminal_output_ids"],
                "comparisons": [
                    {
                        "output_id": "equilibrium_state",
                        "status": "passed",
                        "metric": "relative_error",
                        "observed_error": 0.0,
                        "allowed_error": 1e-12,
                    }
                ],
            }
            comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
            case["comparison_receipt_ref"] = comparison_path.relative_to(root).as_posix()
            case["comparison_receipt_sha256"] = compute_file_sha256(comparison_path)

        assert validate_progress_document(externally_bound) == []
        assert validate_external_bindings(
            externally_bound,
            scope_manifest=scope_manifest,
            capability_evidence_matrix=evidence_matrix,
            ledger=ledger,
            bundle_root=bundle_root,
        ) == []

        missing_entry_receipt = deepcopy(externally_bound)
        missing_entry_receipt["closure_signal"].pop("asset_entry_validation")
        assert any(
            "requires asset_entry_validation" in error
            for error in validate_external_bindings(
                missing_entry_receipt,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        stale_entry_receipt = deepcopy(externally_bound)
        entry_receipt["asset_entry_sha256"] = "0" * 64
        entry_receipt_path.write_text(json.dumps(entry_receipt), encoding="utf-8")
        stale_entry_receipt["closure_signal"]["asset_entry_validation"]["receipt_sha256"] = (
            compute_file_sha256(entry_receipt_path)
        )
        assert any(
            "asset_entry_validation.asset_entry_sha256" in error
            for error in validate_external_bindings(
                stale_entry_receipt,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        entry_receipt["asset_entry_sha256"] = compute_file_sha256(bundle_root / "asset_entry.py")
        entry_receipt_path.write_text(json.dumps(entry_receipt), encoding="utf-8")

        wrong_execution_binding = deepcopy(externally_bound)
        receipt = json.loads(comparison_path.read_text(encoding="utf-8"))
        receipt["bundle_execution_ref"] = "evidence/another-bundle.json"
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        wrong_execution_binding["target_paths"][0]["reassembly_evidence"]["cases"][-1][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert any(
            "bundle_execution_ref does not match" in error
            for error in validate_external_bindings(
                wrong_execution_binding,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        receipt["bundle_execution_ref"] = case["bundle_execution_ref"]
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")

        bad_entry = deepcopy(externally_bound)
        entry_receipt["exit_code"] = 1
        entry_receipt_path.write_text(json.dumps(entry_receipt), encoding="utf-8")
        bad_entry["closure_signal"]["asset_entry_validation"]["receipt_sha256"] = (
            compute_file_sha256(entry_receipt_path)
        )
        assert any(
            "asset_entry_validation.exit_code must equal 0" in error
            for error in validate_external_bindings(
                bad_entry,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        entry_receipt["exit_code"] = 0
        entry_receipt_path.write_text(json.dumps(entry_receipt), encoding="utf-8")

        first_case = externally_bound["target_paths"][0]["reassembly_evidence"]["cases"][0]
        comparison_path = root / first_case["comparison_receipt_ref"]
        receipt = json.loads(comparison_path.read_text(encoding="utf-8"))
        legacy_receipt = deepcopy(receipt)
        legacy_receipt["schema_version"] = "scirel.extraction-reassembly-comparison.v1"
        legacy_receipt.pop("bundle_execution_receipt_ref")
        legacy_receipt.pop("bundle_execution_receipt_sha256")
        legacy_receipt["comparisons"] = [{"output_id": "equilibrium_state", "status": "passed"}]
        comparison_path.write_text(json.dumps(legacy_receipt), encoding="utf-8")
        legacy_working = deepcopy(externally_bound)
        legacy_working["closure_signal"]["kind"] = "active"
        legacy_working["target_paths"][0]["reassembly_evidence"]["cases"][0][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert validate_external_bindings(
            legacy_working,
            scope_manifest=scope_manifest,
            capability_evidence_matrix=evidence_matrix,
            ledger=ledger,
            bundle_root=bundle_root,
        ) == []
        legacy_delivery = deepcopy(externally_bound)
        legacy_delivery["target_paths"][0]["reassembly_evidence"]["cases"][0][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert any(
            "requires v2 for delivery closure" in error
            for error in validate_external_bindings(
                legacy_delivery,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        legacy_state_freeze = deepcopy(legacy_working)
        legacy_state_freeze["state"] = "full_freeze"
        assert any(
            "requires v2 for delivery closure" in error
            for error in validate_external_bindings(
                legacy_state_freeze,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        failed_metric = deepcopy(externally_bound)
        receipt["comparisons"][0]["observed_error"] = 2e-12
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        failed_metric["target_paths"][0]["reassembly_evidence"]["cases"][0][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert any(
            "observed_error exceeds allowed_error" in error
            for error in validate_external_bindings(
                failed_metric,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

        receipt["comparisons"][0]["observed_error"] = 0.0
        execution_receipt_path = root / receipt["bundle_execution_receipt_ref"]
        execution_receipt_path.write_text(json.dumps({"exit_code": 1}), encoding="utf-8")
        receipt["bundle_execution_receipt_sha256"] = compute_file_sha256(execution_receipt_path)
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        failed_execution = deepcopy(externally_bound)
        failed_execution["target_paths"][0]["reassembly_evidence"]["cases"][0][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert any(
            "exit_code must equal 0" in error
            for error in validate_external_bindings(
                failed_execution,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

        missing_execution = deepcopy(externally_bound)
        receipt.pop("bundle_execution_receipt_ref")
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        missing_execution["target_paths"][0]["reassembly_evidence"]["cases"][0][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert any(
            "bundle_execution_receipt_ref is required" in error
            for error in validate_external_bindings(
                missing_execution,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

        execution_receipt_path.write_text(json.dumps({"exit_code": 0}), encoding="utf-8")
        receipt["bundle_execution_receipt_ref"] = execution_receipt_path.relative_to(root).as_posix()
        receipt["bundle_execution_receipt_sha256"] = compute_file_sha256(execution_receipt_path)
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        first_case["comparison_receipt_sha256"] = compute_file_sha256(comparison_path)

        receipt["comparisons"][0]["observed_error"] = 10**400
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        huge_error = deepcopy(externally_bound)
        huge_error["target_paths"][0]["reassembly_evidence"]["cases"][0][
            "comparison_receipt_sha256"
        ] = compute_file_sha256(comparison_path)
        assert any(
            "observed_error must be finite and non-negative" in error
            for error in validate_external_bindings(
                huge_error,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        receipt["comparisons"][0]["observed_error"] = 0.0
        comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
        first_case["comparison_receipt_sha256"] = compute_file_sha256(comparison_path)

        bounded_external = deepcopy(externally_bound)
        bounded_external["closure_signal"] = deepcopy(bounded_signal["closure_signal"])
        bounded_external["closure_signal"]["bounded_delivery_review"][
            "receipt_sha256"
        ] = "0" * 64
        review_path = root / "evidence" / "bounded-review.json"
        review_receipt = {
            "review_id": "bounded-review-001",
            "reviewer_role": "independent_subagent",
            "verdict": "pass",
            "source_scope_digest": externally_bound["scope"]["scope_manifest_digest"],
            "bundle_digest": externally_bound["scope"]["bundle_digest"],
            "reviewed_target_ids": ["T-EQUILIBRIUM"],
            "reviewed_evidence_refs": [
                *bounded_external["closure_signal"]["evidence_refs"],
                *(
                    case[name]
                    for case in reassembly["cases"]
                    for name in (
                        "source_oracle_ref",
                        "bundle_execution_ref",
                        "comparison_receipt_ref",
                        "tolerance_contract_ref",
                    )
                ),
            ],
            "claim_ceiling": "delivered target paths only",
            "reopen_condition": bounded_external["closure_signal"]["reopen_condition"],
            "findings": ["target reassembly is runnable"],
        }
        review_path.write_text(json.dumps(review_receipt), encoding="utf-8")
        bounded_external["closure_signal"]["bounded_delivery_review"][
            "receipt_sha256"
        ] = compute_file_sha256(review_path)
        assert validate_external_bindings(
            bounded_external,
            scope_manifest=scope_manifest,
            capability_evidence_matrix=evidence_matrix,
            ledger=ledger,
            bundle_root=bundle_root,
        ) == []

        omitted_evidence = deepcopy(bounded_external)
        review_receipt["reviewed_evidence_refs"] = ["evidence:unrelated"]
        review_path.write_text(json.dumps(review_receipt), encoding="utf-8")
        omitted_evidence["closure_signal"]["bounded_delivery_review"]["receipt_sha256"] = (
            compute_file_sha256(review_path)
        )
        assert any(
            "reviewed_evidence_refs must include" in error
            for error in validate_external_bindings(
                omitted_evidence,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        review_receipt["reviewed_evidence_refs"] = [
            *bounded_external["closure_signal"]["evidence_refs"],
            *(
                case[name]
                for case in reassembly["cases"]
                for name in (
                    "source_oracle_ref",
                    "bundle_execution_ref",
                    "comparison_receipt_ref",
                    "tolerance_contract_ref",
                )
            ),
        ]
        review_receipt["claim_ceiling"] = "entire source scope"
        review_path.write_text(json.dumps(review_receipt), encoding="utf-8")
        omitted_evidence["closure_signal"]["bounded_delivery_review"]["receipt_sha256"] = (
            compute_file_sha256(review_path)
        )
        assert any(
            "claim_ceiling does not match" in error
            for error in validate_external_bindings(
                omitted_evidence,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        review_receipt["claim_ceiling"] = bounded_external["closure_signal"]["claim_ceiling"]
        review_receipt["reopen_condition"] = "never"
        review_path.write_text(json.dumps(review_receipt), encoding="utf-8")
        omitted_evidence["closure_signal"]["bounded_delivery_review"]["receipt_sha256"] = (
            compute_file_sha256(review_path)
        )
        assert any(
            "reopen_condition does not match" in error
            for error in validate_external_bindings(
                omitted_evidence,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )
        review_receipt["reopen_condition"] = bounded_external["closure_signal"]["reopen_condition"]
        review_path.write_text(json.dumps(review_receipt), encoding="utf-8")

        failed_review = deepcopy(bounded_external)
        failed_review["closure_signal"]["bounded_delivery_review"][
            "receipt_sha256"
        ] = compute_file_sha256(review_path)
        review_receipt["verdict"] = "fail"
        review_path.write_text(json.dumps(review_receipt), encoding="utf-8")
        failed_review["closure_signal"]["bounded_delivery_review"][
            "receipt_sha256"
        ] = compute_file_sha256(review_path)
        assert any(
            "verdict must equal pass" in error
            for error in validate_external_bindings(
                failed_review,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

        (bundle_root / "asset_entry.py").unlink()
        externally_bound["scope"]["bundle_digest"] = compute_bundle_digest(bundle_root)
        reassembly["bundle_digest"] = externally_bound["scope"]["bundle_digest"]
        for case in reassembly["cases"]:
            comparison_path = root / case["comparison_receipt_ref"]
            receipt = json.loads(comparison_path.read_text(encoding="utf-8"))
            receipt["bundle_digest"] = externally_bound["scope"]["bundle_digest"]
            comparison_path.write_text(json.dumps(receipt), encoding="utf-8")
            case["comparison_receipt_sha256"] = compute_file_sha256(comparison_path)
        missing_entry_errors = validate_external_bindings(
            externally_bound,
            scope_manifest=scope_manifest,
            capability_evidence_matrix=evidence_matrix,
            ledger=ledger,
            bundle_root=bundle_root,
        )
        assert any("root asset_entry.py" in error for error in missing_entry_errors)

        active_without_entry = deepcopy(externally_bound)
        active_without_entry["closure_signal"] = {
            "kind": "active",
            "claim_ceiling": "incomplete working snapshot",
            "next_action": "continue extraction",
            "reopen_condition": "frontier changes",
            "owner": "scientific-computation-asset-extraction",
            "evidence_refs": ["evidence:working"],
            "delivered_target_ids": [],
            "unresolved_ids": ["C-EQUATION"],
        }
        assert not any(
            "root asset_entry.py" in error
            for error in validate_external_bindings(
                active_without_entry,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

        first_case = externally_bound["target_paths"][0]["reassembly_evidence"]["cases"][0]
        comparison_path = root / first_case["comparison_receipt_ref"]
        comparison_path.write_text("{}", encoding="utf-8")
        assert any(
            "digest does not match" in error
            for error in validate_external_bindings(
                externally_bound,
                scope_manifest=scope_manifest,
                capability_evidence_matrix=evidence_matrix,
                ledger=ledger,
                bundle_root=bundle_root,
            )
        )

    malformed_lists = deepcopy(named_subweb)
    malformed_lists["work_units"][0]["required_for"] = None
    malformed_lists["equation_anchors"][0]["target_paths"] = None
    malformed_lists["web_edges"][0]["from_node_id"] = ["C-DIAGNOSTIC"]
    malformed_errors = validate_progress_document(malformed_lists)
    assert any("required_for" in error for error in malformed_errors)
    assert any("target_paths" in error for error in malformed_errors)
    assert any("from_node_id" in error for error in malformed_errors)

    check_report_only_execution_rebind()
    print("capability progress validator: PASS")


if __name__ == "__main__":
    main()
