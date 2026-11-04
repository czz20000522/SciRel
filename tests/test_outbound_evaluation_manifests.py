import hashlib
import json
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "docs" / "evaluations" / "outbound-progressive-projects" / "manifests"


def test_outbound_evaluation_manifests_are_valid_json():
    for path in sorted(MANIFEST_DIR.glob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))


def test_outbound_evaluation_manifests_keep_required_source_metadata():
    for path in sorted(MANIFEST_DIR.glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest.get("status"), path.name


def test_outbound_evaluation_manifests_keep_development_evidence_boundaries():
    required_not_claims = {"trusted_release", "expert_approval", "public_v1"}
    correction = json.loads(
        (MANIFEST_DIR / "2026-09-27-margin-review-boundary-correction.json").read_text(
            encoding="utf-8"
        )
    )
    corrected = set()
    for path in sorted(MANIFEST_DIR.glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        not_claims = set(manifest.get("not_claims", ()))
        if original := correction["originals"].get(path.name):
            corrected.add(path.name)
            assert original["original"] == str(path.relative_to(ROOT)).replace("\\", "/")
            assert hashlib.sha256(path.read_bytes()).hexdigest() == original["original_sha256"]
            not_claims.update(correction["additional_not_claims"])
        assert manifest.get("schema"), path.name
        assert required_not_claims <= not_claims, path.name
    assert corrected == set(correction["originals"])


def test_outbound_acceptance_v4_manifest_records_unbound_intermediate_boundary():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-outbound-acceptance-reuse-v4.json").read_text(
            encoding="utf-8"
        )
    )

    unbound = manifest["unbound_complex_field_profile"]
    assert unbound["reused_intermediate"] is False
    assert unbound["evidence_ceiling"] == "insufficient_intermediate_bindings"
    assert unbound["status_counts"] == {"not_sampled": 1}


def test_p4_dev12_manifest_records_vacuum_flux_relabel_without_coupling():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-p4-dev12-claude.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["status"] == "development_evaluation_claude_first_pass_with_scientific_overclaim"
    assert manifest["scientific_package"]["version"] == "0.1.0.dev12"
    assert manifest["scientific_package"]["catalog_coverage"] == "partial 53/68"
    assert manifest["contract_change"]["numeric_arrays_changed_from_dev5"] is False
    assert manifest["contract_change"]["summary_column"] == "psi_max_Wb_per_rad"
    assert "2*pi" in manifest["contract_change"]["equilibrium_coupling"]
    assert "equilibrium_coupling_approval" in manifest["not_claims"]
    assert manifest["result"]["checks_passed_per_setting"] == 9
    assert manifest["result"]["checks_total_per_setting"] == 9
    assert manifest["review_followup_manifest"] == "2026-09-25-p4-dev12-reviewed.json"
    assert manifest["review_followup"]["reviewed_manifest"].endswith(
        "2026-09-25-p4-dev12-reviewed.json"
    )
    assert manifest["review_followup"]["status"] == "superseded_for_final_p4_interpretation"


def test_p4_dev12_reviewed_manifest_records_maintainer_repair_boundary():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-p4-dev12-reviewed.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["status"] == "development_evaluation_maintainer_reviewed_repair"
    assert "autonomous_claude_repair" in manifest["not_claims"]
    assert manifest["review_findings"]["repair_owner"] == "maintainer, not Claude Code"
    assert manifest["review_findings"]["unresolved_candidates_within_0_03_m_of_filament"] == {
        "balanced": 6,
        "offset": 9,
        "preview": 8,
    }
    assert manifest["reviewed_result"]["checks_passed_per_setting"] == 8
    assert manifest["reviewed_result"]["checks_total_per_setting"] == 8
    assert manifest["reviewed_result"]["numeric_field_arrays_changed_from_dev5"] is False
    assert manifest["reviewed_project_archive_sha256"] == (
        "115113054e20564d23167f478443c448c49f1f33bb7e5333bcac6e1f517c25b7"
    )


def test_p4_dev12_reviewed_manifest_separates_claude_result_from_maintainer_repair():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-p4-dev12-reviewed.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["review_findings"]["repair_owner"] == "maintainer, not Claude Code"
    assert "autonomous_claude_repair" in manifest["not_claims"]
    assert manifest["reviewed_result"]["checks_passed_per_setting"] == 8
    assert manifest["reviewed_result"]["checks_total_per_setting"] == 8
    assert manifest["reviewed_project_archive"] != manifest["claude_first_archive"]


def test_unseen_p4_evolution_codex_manifest_records_stage1_boundary():
    manifest = json.loads(
        (
            MANIFEST_DIR / "2026-09-25-unseen-p4-evolution-codex.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["harness"]["successful_kind"] == "codex_cli"
    assert manifest["status"] == "development_evaluation_codex_stage1_success"
    assert manifest["continuation_manifest"] == "2026-09-25-unseen-p4-evolution-codex-followup.json"
    assert "claude_code_success" in manifest["not_claims"]
    assert "equilibrium_coupling_approval" in manifest["not_claims"]
    assert "heating_validation" in manifest["not_claims"]
    assert manifest["scirel_inputs"]["wheel_version"] == "0.1.0.dev12"
    assert manifest["scirel_inputs"]["partial_catalog_assets"] == "53/68"
    assert manifest["entrypoint_result"]["exit_code"] == 0
    assert manifest["entrypoint_result"]["unittest_summary"] == "Ran 3 tests, OK"
    assert manifest["entrypoint_result"]["states"] == ["balanced", "shifted"]
    assert manifest["scientific_result"]["asset"] == "scirel.field.multi-coil-vacuum-field"
    assert manifest["scientific_result"]["model"] == (
        "axisymmetric circular-filament vacuum field"
    )
    assert manifest["scientific_result"]["later_complete_current_table_supported_without_python_edits"] is True
    assert manifest["scientific_result"]["balanced_axis_center"]["B_Z_mT"] == 2.189331
    assert manifest["scientific_result"]["outer_sample_comparison"]["shifted_B_Z_mT"] == 3.299848
    assert any("synthetic vacuum-field fixture only" in item for item in manifest["limitations"])


def test_unseen_p4_evolution_followup_records_partial_failure_and_resume_recovery():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p4-evolution-codex-followup.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["successful_kind"] == "codex_cli"
    assert "unassisted_resume_success" in manifest["not_claims"]
    assert "read-only" in manifest["progressive_request"]["resume_failure"]
    assert manifest["result"]["usable_new_states"] == ["reverse", "idle"]
    assert manifest["result"]["missing_column"] == "D_kA"
    assert manifest["result"]["window_grid_nodes_per_state"] == 1681
    assert manifest["result"]["original_output_files_unchanged"] is True
    assert manifest["final_project_archive"] != manifest["stage1_project_archive"]


def test_user_acceptance_p4_followup_manifest_records_maintained_entrypoint_guard():
    manifest = json.loads(
        (
            MANIFEST_DIR / "2026-09-25-user-acceptance-p4-followup.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["status"] == "development_wheel_controlled_evaluation"
    assert "neutral_harness_natural_language_success" in manifest["not_claims"]
    assert "equilibrium_coupling_approval" in manifest["not_claims"]
    assert manifest["scientific_scope"]["asset"] == "scirel.field.multi-coil-vacuum-field"
    assert manifest["scientific_scope"]["model"] == (
        "axisymmetric circular-filament vacuum field"
    )
    p4_task = manifest["entrypoint_result"]["p4_task"]
    assert p4_task["passed"] is True
    assert p4_task["settings"] == ["balanced", "shifted", "reverse", "idle"]
    assert p4_task["initial_summary_digest_preserved"] is True
    assert p4_task["duplicate_current_row_rejected"] is True
    assert "duplicate setting/coil row" in p4_task["duplicate_current_row_error"]


def test_unseen_p3_codex_manifest_records_frozen_archive():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p3-codex.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["successful_kind"] == "codex_cli"
    assert "claude_code_success" in manifest["not_claims"]
    assert manifest["final_project_archive"] == (
        "build/verification/scirel-outbound-p3-unseen-codex-final-20260925.tgz"
    )
    assert manifest["final_project_archive_sha256"] == (
        "04a025aa408d7c37b9f5fbc96af0117ef67de551d7edbd4b8fbe22272455adb6"
    )
    assert manifest["entrypoint_result"]["exit_code"] == 0
    assert manifest["entrypoint_result"]["dashboard_estimates"] == 2


def test_unseen_p2_longform_manifest_keeps_first_error_and_review_boundary():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p2-longform-codex.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["successful_kind"] == "codex_cli"
    assert "unassisted_scientific_note_handling" in manifest["not_claims"]
    assert "502" in manifest["progressive_request"]["first_stage_failure"]
    assert "less_than?" in manifest["progressive_request"]["first_stage2_error"]
    assert len(manifest["progressive_request"]["review_interventions"]) == 2
    assert manifest["archives"]["stage2_first"] != manifest["archives"]["final"]
    assert manifest["final_result"]["ready_cases"] == ["alpha", "beta"]
    assert manifest["final_result"]["prior_output_hashes_unchanged"] is True
    assert manifest["final_result"]["field_scope"].startswith("poloidal-only")


def test_unseen_p2_longform_manifest_binds_all_stage_archives_and_traces():
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))
    pairs = {
        (pair.manifest_name, pair.path_key)
        for pair in verifier["_manifest_file_hash_pairs"]()
    }
    name = "2026-09-25-unseen-p2-longform-codex.json"
    assert {(name, f"archives.{stage}") for stage in (
        "stage1", "stage2_first", "reviewed_parser", "final"
    )} <= pairs
    assert {(name, f"traces.{stage}") for stage in (
        "claude_connectivity", "round1_502", "round1_resume", "round2_first",
        "review_fix", "boundary_fix"
    )} <= pairs


def test_unseen_p2_clarification_manifest_keeps_first_scientific_failure():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p2-clarification-codex.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["successful_kind"] == "codex_cli"
    assert "unassisted_followup_success" in manifest["not_claims"]
    assert "all-false reader mask" in manifest["chronology"]["stage2_first_error"]
    assert manifest["archives"]["stage2_first"] != manifest["archives"]["final"]
    assert manifest["final_result"]["grid_v2_exit_code"] == 1
    assert manifest["final_result"]["grid_v2_cedar_artifact"] == "mapping_diagnostic_only"
    assert manifest["final_result"]["grid_v2_quartz_status"] == "delivered"


def test_unseen_p2_clarification_manifest_binds_all_stages_and_traces():
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))
    pairs = {
        (pair.manifest_name, pair.path_key)
        for pair in verifier["_manifest_file_hash_pairs"]()
    }
    name = "2026-09-25-unseen-p2-clarification-codex.json"
    assert {(name, f"archives.{stage}") for stage in (
        "stage1", "stage2_first", "reviewed_first", "final"
    )} <= pairs
    assert {(name, f"traces.{stage}") for stage in (
        "round1", "round2_first", "review_fix", "reusability_fix"
    )} <= pairs


def test_unseen_p2_negation_manifest_separates_autonomy_and_assisted_repair():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p2-negation-codex.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["successful_kind"] == "codex_cli"
    assert "unassisted_followup_delivery" in manifest["not_claims"]
    assert "not greater_than?" in manifest["chronology"]["stage1"]
    assert "no new files" in manifest["chronology"]["round2_read_only"]
    assert "overwrote the original" in manifest["chronology"]["round2_write_recovery"]
    assert manifest["reviewed_result"]["entrypoint_exit_codes"] == {
        "scan_a": 0, "scan_b": 0
    }
    assert manifest["reviewed_result"]["material_support_points"]["scan_b"] == {
        "birch": 12, "opal": 60
    }
    assert len(manifest["limitations"]) >= 4


def test_unseen_p2_negation_manifest_binds_stage_and_trace_evidence():
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))
    pairs = {
        (pair.manifest_name, pair.path_key)
        for pair in verifier["_manifest_file_hash_pairs"]()
    }
    name = "2026-09-25-unseen-p2-negation-codex.json"
    assert {(name, f"archives.{stage}") for stage in (
        "stage1", "stage2_first", "reviewed_final"
    )} <= pairs
    assert {(name, f"traces.{stage}") for stage in (
        "round1", "round2_read_only", "round2_write_recovery", "review_fix"
    )} <= pairs


def test_unseen_p2_same_path_followup_records_historical_grid_boundary():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p2-negation-same-path-followup.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["prior_review_feedback_in_context"] is True
    assert "fresh_unassisted_project" in manifest["not_claims"]
    result = manifest["result"]
    assert result["historical_grid_parsed_values_match_original"] is True
    assert result["historical_grid_is_original_byte_archive"] is False
    assert result["historical_grid_recompute_matches_old_npz_bytes"] is True
    assert result["prior_npz_files_preserved"] == 8
    assert result["new_corrected_npz_files"] == 2
    assert result["old_scan_b_npz_sha256"] != result["corrected_scan_b_npz_sha256"]


def test_unseen_p2_same_path_followup_binds_archive_trace_and_input():
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))
    pairs = {
        (pair.manifest_name, pair.path_key)
        for pair in verifier["_manifest_file_hash_pairs"]()
    }
    name = "2026-09-25-unseen-p2-negation-same-path-followup.json"
    assert {(name, key) for key in (
        "archives.prior_reviewed_project", "archives.same_path_followup",
        "examiner_inputs.followup_request", "examiner_inputs.corrected_grid",
        "examiner_inputs.original_grid", "traces.same_path_followup"
    )} <= pairs


def test_outbound_artifact_verifier_includes_acceptance_v4_manifest():
    verifier = (ROOT / "scripts" / "verify_outbound_evaluation_manifests.py").read_text(
        encoding="utf-8"
    )

    assert "2026-09-25-outbound-acceptance-reuse-v4.json" in verifier


def test_affected_selector_manifest_records_scirel_solving_skill_mapping():
    manifest = json.loads(
        (
            MANIFEST_DIR / "2026-09-25-affected-selector-scirel-solving-skill.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["status"] == "development_evaluation"
    assert manifest["evidence"]["path"] == (
        "build/verification/affected-selector-scirel-solving-skill-20260925.json"
    )
    assert manifest["selector_result"]["full_suite_required"] is False
    assert manifest["selector_result"]["test_paths"] == [
        "tests/test_scientific_request_workflow_docs.py"
    ]


def test_outbound_artifact_verifier_includes_affected_selector_manifest():
    verifier = (ROOT / "scripts" / "verify_outbound_evaluation_manifests.py").read_text(
        encoding="utf-8"
    )

    assert "2026-09-25-affected-selector-scirel-solving-skill.json" in verifier


def test_clean_source_manifest_test_records_no_build_directory():
    manifest = json.loads(
        (
            MANIFEST_DIR / "2026-09-25-clean-source-manifest-pytest.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["status"] == "development_evaluation"
    assert manifest["evidence"]["path"] == (
        "build/verification/clean-artifact-manifest-pytest-20260925-v11.json"
    )
    assert manifest["clean_source_result"]["has_build_directory"] is False
    assert manifest["clean_source_result"]["exit_code"] == 0
    assert "17 passed" in manifest["clean_source_result"]["output"]
    assert manifest["clean_source_result"]["manifest_count"] == 11


def test_outbound_artifact_verifier_includes_clean_source_manifest():
    verifier = (ROOT / "scripts" / "verify_outbound_evaluation_manifests.py").read_text(
        encoding="utf-8"
    )

    assert "2026-09-25-clean-source-manifest-pytest.json" in verifier


def test_outbound_artifact_verifier_reports_missing_evidence_file():
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))

    errors = verifier["_check_file"](
        "build/verification/does-not-exist-for-test.json",
        "0" * 64,
        "synthetic missing evidence",
    )

    assert errors == [
        "synthetic missing evidence: missing file "
        "build/verification/does-not-exist-for-test.json"
    ]


def test_outbound_artifact_verifier_reports_hash_mismatch(tmp_path):
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("actual evidence", encoding="utf-8")
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))
    verifier["_check_file"].__globals__["ROOT"] = tmp_path

    errors = verifier["_check_file"](
        "evidence.txt",
        "0" * 64,
        "synthetic mismatched evidence",
    )

    assert len(errors) == 1
    assert errors[0].startswith("synthetic mismatched evidence: expected " + "0" * 64)
    assert errors[0].endswith(" for evidence.txt")


def test_outbound_artifact_verifier_discovers_manifest_file_hash_pairs():
    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))

    pairs = {
        (pair.manifest_name, pair.path_key, pair.hash_key)
        for pair in verifier["_manifest_file_hash_pairs"]()
    }

    for manifest_name in (
        "2026-09-25-outbound-acceptance-reuse.json",
        "2026-09-25-outbound-acceptance-reuse-v4.json",
    ):
        assert (manifest_name, "wheel.path", "wheel.sha256") in pairs

    assert (
        "2026-09-25-p3-append-codex-line-profile.json",
        "final_project_archive",
        "final_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-unseen-p3-claude.json",
        "final_project_archive",
        "final_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-p3-append-codex-line-profile.json",
        "codex_trace",
        "codex_trace_sha256",
    ) in pairs
    assert (
        "2026-09-25-p4-dev12-claude.json",
        "final_project_archive",
        "final_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-p4-dev12-claude.json",
        "claude_trace",
        "claude_trace_sha256",
    ) in pairs
    assert (
        "2026-09-25-p4-dev12-reviewed.json",
        "reviewed_project_archive",
        "reviewed_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-unseen-p3-codex.json",
        "final_project_archive",
        "final_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-unseen-p4-evolution-codex.json",
        "final_project_archive",
        "final_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-unseen-p4-evolution-codex.json",
        "codex_trace",
        "codex_trace_sha256",
    ) in pairs
    assert (
        "2026-09-25-unseen-p4-evolution-codex-followup.json",
        "final_project_archive",
        "final_project_archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-unseen-p4-evolution-codex-followup.json",
        "traces.round2_read_only",
        "traces.round2_read_only_sha256",
    ) in pairs
    assert (
        "2026-09-25-user-acceptance-p4-followup.json",
        "archive",
        "archive_sha256",
    ) in pairs
    assert (
        "2026-09-25-user-acceptance-p4-followup.json",
        "summary",
        "summary_sha256",
    ) in pairs


def test_p3_takeover_manifest_separates_science_result_from_assisted_history_repair():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p3-takeover-codex.json").read_text(
            encoding="utf-8"
        )
    )

    result = manifest["result"]
    assert result["unassisted_independently_checked_real_imag_components"] == 24
    assert result["unassisted_earlier_report_and_json_byte_preserved"] is False
    assert result["reviewed_repair_used_examiner_supplied_prior_file_backup"] is True
    assert result["reviewed_prior_files_byte_match_stage0"] == 3
    assert "autonomous_complete_delivery" in manifest["not_claims"]


def test_p3_same_path_correction_manifest_preserves_inherited_project_boundary():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p3-same-path-correction-codex.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["fresh_session_on_previously_reviewed_project"] is True
    assert manifest["harness"]["reviewer_feedback_during_session"] is False
    assert manifest["result"]["archived_location_pair_byte_matches_previous_current"] is True
    assert manifest["result"]["corrected_estimates"] == 4
    assert manifest["result"]["corrected_unavailable"] == 2
    assert "greenfield_project_creation" in manifest["not_claims"]
    assert "complete_historical_input_byte_provenance" in manifest["not_claims"]
    assert "autonomous_second_correction_session" in manifest["not_claims"]


def test_p3_longform_manifest_separates_fresh_project_from_harness_recovery():
    manifest = json.loads(
        (MANIFEST_DIR / "2026-09-25-unseen-p3-longform-greenfield-codex.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["harness"]["fresh_project_session"] is True
    assert manifest["harness"]["round2_read_only_interruption"] is True
    assert manifest["harness"]["round2b_workspace_write_recovery"] is True
    assert manifest["result"]["read_only_continuation_delivered_files"] == 0
    assert manifest["result"]["earlier_three_outputs_byte_preserved"] is True
    assert manifest["result"]["independent_real_imag_components_checked"] == 108
    assert "uninterrupted_autonomous_progressive_delivery" in manifest["not_claims"]
    assert "independent_cold_plasma_physics_validation" in manifest["not_claims"]


def test_p3_longform_correction_manifest_binds_first_passes_and_history():
    name = "2026-09-25-unseen-p3-longform-corrections-codex.json"
    manifest = json.loads((MANIFEST_DIR / name).read_text(encoding="utf-8"))

    assert manifest["harness"]["reviewer_feedback_in_these_two_rounds"] is False
    assert manifest["harness"]["inherited_project_had_prior_write_permission_recovery"] is True
    assert manifest["result"]["stage4_archived_result_files_byte_preserved"] == 8
    assert manifest["result"]["stage4_repeated_command_unchanged_result_files"] == 14
    assert manifest["result"]["stage4_real_imag_components_checked"] == 108
    assert manifest["result"]["longitudinal_formula_grid_point_frequency_pairs_checked"] == 1404
    assert manifest["result"]["single_supported_tensor_entry_perturbation_rejected"] is True
    assert "complete_historical_input_byte_provenance" in manifest["not_claims"]
    assert "independent_cold_plasma_physics_validation" in manifest["not_claims"]

    verifier = runpy.run_path(str(ROOT / "scripts" / "verify_outbound_evaluation_manifests.py"))
    pairs = {
        (pair.manifest_name, pair.path_key)
        for pair in verifier["_manifest_file_hash_pairs"]()
    }
    assert {(name, f"archives.{stage}") for stage in (
        "stage3_inputs", "stage3_first_delivery", "stage4_inputs", "stage4_first_delivery"
    )} <= pairs
    assert {(name, f"traces.{round_name}") for round_name in (
        "round3_first", "round4_first"
    )} <= pairs
    assert (name, "examiner_inputs.longitudinal_checker") in pairs
