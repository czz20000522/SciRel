import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "integration" / "codefusion-consumer-contract.md"
PLUGIN_REGISTRATION = (
    ROOT / "contracts" / "examples" / "scirel-plugin-registration.dev.json"
)


def test_consumer_contract_retires_the_legacy_admission_flow():
    text = CONTRACT.read_text(encoding="utf-8")

    assert "codefusion.scirel-admitted-input.v1" not in text
    assert "docs/domains/" not in text
    assert "no legacy admission-flow compatibility before v1" in text
    assert "No branch is retained for the retired CodeFusion-owned admission flow" in text


def test_active_binding_uses_one_pinned_scirel_plugin_release():
    text = CONTRACT.read_text(encoding="utf-8")
    registration = json.loads(PLUGIN_REGISTRATION.read_text(encoding="utf-8"))

    assert "plugin release reference" in text
    assert "wheel artifact reference and digest" in text
    assert "catalog artifact reference, release version, root digest" in text
    assert registration["plugin_id"] == "scirel"
    assert registration["skill_bundle"]["media_type"] == (
        "application/vnd.agent-skills.bundle+zip"
    )
    assert registration["catalog"]["media_type"] == (
        "application/vnd.scirel.catalog-snapshot+zip"
    )
    assert registration["connector"]["protocol_family"] == "mcp"
    assert registration["connector"]["capability_refs"] == [
        "catalog.discover",
        "asset.read",
        "callable.resolve",
        "callable.invoke",
    ]
    assert all(
        ref.startswith("runtime-dependency://")
        for ref in registration["runtime_dependency_refs"]
    )
    entrypoints = registration["skill_bundle"]["implicit_entrypoints"]
    assert {entry["name"] for entry in entrypoints} == {
        "scientific-computation-asset-extraction",
        "scirel-integration",
        "scirel-solving",
    }
    for entry in entrypoints:
        assert (ROOT / entry["path"]).is_file()
