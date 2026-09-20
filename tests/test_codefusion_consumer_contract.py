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


def test_active_binding_uses_one_pinned_scirel_plugin_release():
    text = CONTRACT.read_text(encoding="utf-8")
    registration = json.loads(PLUGIN_REGISTRATION.read_text(encoding="utf-8"))
    release = registration["release"]
    artifacts = {
        artifact["media_type"]: artifact for artifact in release["artifacts"]
    }

    assert "plugin release reference" in text
    assert "wheel artifact reference and digest" in text
    assert "catalog artifact reference, release version, root digest" in text
    assert registration["plugin_id"] == "scirel"
    assert set(registration) == {
        "plugin_id",
        "release",
        "capabilities",
        "required_scopes",
        "ui_extensions",
        "view_descriptors",
    }
    assert release["plugin_release_ref"].startswith("plugin-release://scirel/")
    assert "application/vnd.agent-skills.bundle+zip" in artifacts
    assert "application/vnd.scirel.catalog-snapshot+zip" in artifacts
    assert all(
        artifact["artifact_ref"].startswith("cf://artifact/")
        and artifact["digest"].startswith("sha256:")
        and len(artifact["digest"]) == 71
        for artifact in artifacts.values()
    )
    connector = release["connectors"][0]
    assert connector["protocol_family"] == "mcp"
    assert connector["capability_refs"] == [
        "catalog.discover",
        "asset.read",
        "callable.resolve",
        "callable.invoke",
    ]
    assert all(
        ref.startswith("runtime-dependency://")
        for ref in release["runtime_dependency_refs"]
    )
    entrypoints = release["skill_entrypoints"]
    assert {entry["name"] for entry in entrypoints} == {
        "scientific-computation-asset-extraction",
        "scirel-integration",
        "scirel-solving",
    }
    for entry in entrypoints:
        assert entry["artifact_ref"] == artifacts[
            "application/vnd.agent-skills.bundle+zip"
        ]["artifact_ref"]
        assert (ROOT / entry["path"]).is_file()

    assert all("implicit" not in entry for entry in entrypoints)
