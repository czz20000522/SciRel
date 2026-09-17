from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "integration" / "codefusion-consumer-contract.md"


def test_consumer_contract_tracks_the_single_admission_producer_shape():
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
    assert "there is no batch `assets` wrapper in v1" in text
    assert "`owner_snapshot_digest`" not in text
    assert re.search(r"\b[0-9a-f]{40}\b", text) is None


def test_current_owner_gaps_are_not_manifest_decode_requirements():
    text = CONTRACT.read_text(encoding="utf-8")

    assert "`license_evidence`" in text
    assert "`source_provenance_ref`" in text
    assert "allowed gap fields in v1" in text
    assert "release/production blocker" in text
    assert "not a reason to reject or misdecode the admitted-input manifest" in text
