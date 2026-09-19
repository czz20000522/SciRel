from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "integration" / "codefusion-consumer-contract.md"


def test_consumer_contract_keeps_single_admission_shape_as_historical_fixture():
    text = CONTRACT.read_text(encoding="utf-8")

    assert "`codefusion.scirel-admitted-input.v1`" in text
    for field in (
        "`tenant_id`",
        "`admission`",
        "`owner_snapshot_ref`",
        "`owner_snapshot_root_digest`",
        "`dependency_bindings`",
        "`scientific_contract_ref`",
        "`files`",
        "`gaps`",
    ):
        assert field in text
    assert "old experimental path" in text
    assert "only for reproducing the 52-asset development fixture" in text
    assert "does not treat its decision fields as current approval" in text
    assert "`owner_snapshot_digest`" not in text
    assert re.search(r"\b[0-9a-f]{40}\b", text) is None


def test_active_binding_uses_scirel_release_artifacts_not_admission_state():
    text = CONTRACT.read_text(encoding="utf-8")

    assert "SciRel `candidate_id`/candidate digest" in text
    assert "the exact SciRel release manifest artifact and digest" in text
    assert "wheel reference and SHA-256" in text
    assert "CodeFusion consumes the released identities and bindings" in text
    assert "without adding another SciRel admission state" in text
