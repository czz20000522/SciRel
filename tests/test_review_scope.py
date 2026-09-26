import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import review_scope as scope_module  # noqa: E402


def _document(asset_id, *, version="0.1.0.dev15", dependencies=(), evidence="initial"):
    return {
        "asset_id": asset_id,
        "version": {
            "implementation_version": version,
            "dependencies": [{"asset_id": item} for item in dependencies],
        },
        "public_api": {"python": {"module": f"scirel.field.{asset_id}", "symbol": "evaluate"}},
        "verification": {"tests": [f"tests/operator_contracts/test_{asset_id}.py"], "scope": evidence},
    }


def _snapshot(root: Path, commit: str, documents: list[dict]) -> Path:
    root.mkdir()
    entries = []
    partitions = []
    for document in documents:
        relative = f"exact-documents/catalog/examples/{document['asset_id']}.json"
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")
        entries.append({
            "snapshot_path": relative,
            "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        record_relative = f"records/{document['asset_id']}.json"
        record = root / "catalog" / record_relative
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_bytes(path.read_bytes())
        payload = record.read_bytes()
        partitions.append({
            "path": record_relative,
            "bytes": len(payload),
            "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
        })
    catalog_release = {
        "schema": "scirel.catalog-release.v1",
        "release_version": "0.1.0.dev15",
        "coverage": {"included_asset_count": len(entries)},
        "partitions": partitions,
    }
    catalog_payload = json.dumps(
        catalog_release, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    catalog_release["root_digest"] = "sha256:" + hashlib.sha256(catalog_payload).hexdigest()
    (root / "catalog/release.json").write_text(
        json.dumps(catalog_release), encoding="utf-8"
    )
    artifacts = {}
    for name, relative in (
        ("review_dossier", "review-dossier/review.md"),
        ("test_evidence", "test-evidence.md"),
        ("wheel", "wheel/scirel.whl"),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "wheel":
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "scirel-0.1.0.dist-info/METADATA",
                    "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0\n"
                    "Requires-Python: >=3.10\nRequires-Dist: numpy>=1.24\n",
                )
        else:
            path.write_bytes(name.encode("ascii"))
        artifacts[name] = {
            "path": relative,
            "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifest = {
        "schema": "scirel.review-version.dev",
        "git_commit": commit,
        "exact_documents": entries,
        "catalog": {
            "path": "catalog/release.json",
            "root_digest": catalog_release["root_digest"],
            "coverage": catalog_release["coverage"],
        },
        **artifacts,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _replace_wheel_metadata(root: Path, *, version: str, dependency: str) -> None:
    wheel = root / "wheel/scirel.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"scirel-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: scirel\nVersion: {version}\n"
            f"Requires-Python: >=3.10\nRequires-Dist: {dependency}\n",
        )
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["wheel"]["sha256"] = scope_module._sha256(wheel)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_first_review_includes_all_frozen_assets(tmp_path: Path):
    snapshot = _snapshot(
        tmp_path / "candidate", "a" * 40,
        [_document("a"), _document("b", dependencies=("a",))],
    )

    result = scope_module.review_scope(snapshot)

    assert result["mode"] == "first_review"
    assert result["candidate_manifest_digest"] == scope_module._sha256(snapshot / "manifest.json")
    assert result["comparison_manifest_digest"] is None
    assert result["baseline_approval_verified"] is False
    assert result["review_asset_ids"] == ["a", "b"]


def test_comparison_excludes_version_only_edits_and_includes_dependents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    baseline = _snapshot(
        tmp_path / "baseline", "a" * 40,
        [_document("a"), _document("b"), _document("c", dependencies=("a",))],
    )
    candidate = _snapshot(
        tmp_path / "candidate", "b" * 40,
        [
            _document("a", evidence="new direct evidence"),
            _document("b", version="0.1.0.dev16"),
            _document("c", dependencies=("a",)),
        ],
    )
    monkeypatch.setattr(scope_module, "_changed_paths", lambda *_: ["catalog/examples/a.json"])

    result = scope_module.review_scope(candidate, baseline)

    assert result["candidate_manifest_digest"] == scope_module._sha256(candidate / "manifest.json")
    assert result["comparison_manifest_digest"] == scope_module._sha256(baseline / "manifest.json")
    assert result["changed_document_ids"] == ["a"]
    assert result["mechanical_only_document_ids"] == ["b"]
    assert result["review_asset_ids"] == ["a", "c"]


def test_source_change_uses_existing_impact_selector_and_reverse_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    docs = [_document("a"), _document("c", dependencies=("a",))]
    baseline = _snapshot(tmp_path / "baseline", "a" * 40, docs)
    candidate = _snapshot(tmp_path / "candidate", "b" * 40, docs)
    changed_path = "src/scirel/field/a.py"
    monkeypatch.setattr(scope_module, "_changed_paths", lambda *_: [changed_path])

    def impact(paths, baseline_commit, candidate_commit, documents):
        assert paths == [changed_path]
        assert baseline_commit == "a" * 40
        assert candidate_commit == "b" * 40
        assert set(documents) == {"a", "c"}
        return {"a"}, []

    monkeypatch.setattr(scope_module, "_source_impact", impact)

    result = scope_module.review_scope(candidate, baseline)

    assert result["changed_document_ids"] == []
    assert result["review_asset_ids"] == ["a", "c"]


def test_runtime_dependency_change_reopens_scientific_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    docs = [_document("a"), _document("b", dependencies=("a",))]
    baseline = _snapshot(tmp_path / "baseline", "a" * 40, docs)
    candidate = _snapshot(tmp_path / "candidate", "b" * 40, docs)
    _replace_wheel_metadata(baseline, version="0.1.0", dependency="numpy>=1.24")
    _replace_wheel_metadata(candidate, version="0.1.0", dependency="numpy>=2")
    monkeypatch.setattr(scope_module, "_changed_paths", lambda *_: ["pyproject.toml"])

    result = scope_module.review_scope(candidate, baseline)

    assert result["runtime_requirements_changed"] is True
    assert result["review_asset_ids"] == ["a", "b"]


def test_package_version_only_change_does_not_reopen_scientific_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    docs = [_document("a")]
    baseline = _snapshot(tmp_path / "baseline", "a" * 40, docs)
    candidate = _snapshot(tmp_path / "candidate", "b" * 40, docs)
    _replace_wheel_metadata(baseline, version="0.1.0.dev17", dependency="numpy>=1.24")
    _replace_wheel_metadata(candidate, version="0.1.0.dev18", dependency="numpy>=1.24")
    monkeypatch.setattr(scope_module, "_changed_paths", lambda *_: ["pyproject.toml"])

    result = scope_module.review_scope(candidate, baseline)

    assert result["runtime_requirements_changed"] is False
    assert result["review_asset_ids"] == []


def test_invalid_comparison_wheel_metadata_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    docs = [_document("a")]
    baseline = _snapshot(tmp_path / "baseline", "a" * 40, docs)
    candidate = _snapshot(tmp_path / "candidate", "b" * 40, docs)
    wheel = candidate / "wheel/scirel.whl"
    wheel.write_bytes(b"not a wheel")
    manifest_path = candidate / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["wheel"]["sha256"] = scope_module._sha256(wheel)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(scope_module, "_changed_paths", lambda *_: [])

    with pytest.raises(zipfile.BadZipFile):
        scope_module.review_scope(candidate, baseline)


def test_tampered_snapshot_is_rejected(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    path = snapshot / "exact-documents/catalog/examples/a.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(ValueError, match="digest differs"):
        scope_module.review_scope(snapshot)


def test_review_material_digest_is_checked_and_old_snapshot_still_reads(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    assert scope_module.review_scope(snapshot)["review_asset_ids"] == ["a"]

    material = snapshot / "review-materials/docs/domains/field.md"
    material.parent.mkdir(parents=True)
    material.write_text("# Field\n", encoding="utf-8")
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["review_materials"] = [{
        "path": "docs/domains/field.md",
        "snapshot_path": "review-materials/docs/domains/field.md",
        "sha256": "sha256:" + hashlib.sha256(material.read_bytes()).hexdigest(),
    }]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert scope_module.review_scope(snapshot)["review_asset_ids"] == ["a"]

    material.write_text("# Changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="digest differs"):
        scope_module.review_scope(snapshot)


def test_review_material_path_cannot_escape_snapshot(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["review_materials"] = [{
        "path": "docs/domains/field.md",
        "snapshot_path": "../elsewhere.md",
        "sha256": "sha256:" + "0" * 64,
    }]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid material entry"):
        scope_module.review_scope(snapshot)


def test_review_material_entry_must_be_structured(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["review_materials"] = [None]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid material entry"):
        scope_module.review_scope(snapshot)


def test_candidate_batch_materials_are_accepted_as_listed_by_the_freeze(tmp_path: Path):
    """Since the r66 v2 freeze the manifest may list exact candidate-batch
    shapes (review.md + proposal/*.py|*.json); the scope reader must accept
    the same restricted contract the freeze script writes."""
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    accepted = []
    for relative in (
        "review_candidates/2026-09-27-batch/review.md",
        "review_candidates/2026-09-27-batch/proposal/module.py",
        "review_candidates/2026-09-27-batch/proposal/doc.json",
        "review_candidates/2026-09-27-batch/proposal/test_module.py",
    ):
        material = snapshot / "review-materials" / relative
        material.parent.mkdir(parents=True, exist_ok=True)
        material.write_bytes(relative.encode("utf-8"))
        accepted.append({
            "path": relative,
            "snapshot_path": f"review-materials/{relative}",
            "sha256": "sha256:" + hashlib.sha256(material.read_bytes()).hexdigest(),
        })
    manifest["review_materials"] = accepted
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert scope_module.review_scope(snapshot)["review_asset_ids"] == ["a"]


@pytest.mark.parametrize("relative", [
    "review_candidates/2026-09-27-batch/README.md",
    "review_candidates/2026-09-27-batch/notes/review.md",
    "review_candidates/2026-09-27-batch/proposal/extra.md",
    "review_candidates/2026-09-27-batch/proposal/nested/x.py",
    "review_candidates/2026-09-27-batch/proposal/data.csv",
    "other/review_candidates/2026-09-27-batch/review.md",
])
def test_candidate_material_outside_the_freeze_shape_is_rejected(tmp_path: Path, relative: str):
    """Paths the freeze script would refuse must also fail closed here; the
    consumer reuses the freeze predicate instead of a second diverging rule."""
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    material = snapshot / "review-materials" / relative
    material.parent.mkdir(parents=True, exist_ok=True)
    material.write_bytes(b"x")
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["review_materials"] = [{
        "path": relative,
        "snapshot_path": f"review-materials/{relative}",
        "sha256": "sha256:" + hashlib.sha256(material.read_bytes()).hexdigest(),
    }]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid material entry"):
        scope_module.review_scope(snapshot)


def test_tampered_catalog_partition_is_rejected(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    path = snapshot / "catalog/records/a.json"
    path.write_bytes(path.read_bytes().replace(b'"a"', b'"b"', 1))

    with pytest.raises(ValueError, match="catalog partition digest differs"):
        scope_module.review_scope(snapshot)


def test_catalog_release_formatting_does_not_change_its_digest(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    path = snapshot / "catalog/release.json"
    path.write_text(
        json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2),
        encoding="utf-8",
    )

    assert scope_module.review_scope(snapshot)["review_asset_ids"] == ["a"]


def test_manifest_formatting_changes_exact_snapshot_identity_not_science_scope(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    before = scope_module.review_scope(snapshot)
    manifest_path = snapshot / "manifest.json"
    manifest_path.write_text(
        json.dumps(json.loads(manifest_path.read_text(encoding="utf-8")), indent=2),
        encoding="utf-8",
    )

    after = scope_module.review_scope(snapshot)
    assert after["candidate_manifest_digest"] != before["candidate_manifest_digest"]
    assert after["review_asset_ids"] == before["review_asset_ids"]


def test_catalog_manifest_digest_mismatch_is_rejected(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    path = snapshot / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["catalog"]["root_digest"] = "sha256:" + "0" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="catalog differs from its manifest"):
        scope_module.review_scope(snapshot)


def test_catalog_record_must_match_frozen_exact_document(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "a" * 40, [_document("a")])
    record_path = snapshot / "catalog/records/a.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["verification"]["scope"] = "catalog-only change"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    payload = record_path.read_bytes()

    release_path = snapshot / "catalog/release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["partitions"][0]["bytes"] = len(payload)
    release["partitions"][0]["sha256"] = "sha256:" + hashlib.sha256(payload).hexdigest()
    unsigned = {key: value for key, value in release.items() if key != "root_digest"}
    release["root_digest"] = "sha256:" + hashlib.sha256(
        json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    release_path.write_text(json.dumps(release), encoding="utf-8")

    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["catalog"]["root_digest"] = release["root_digest"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="catalog records differ from exact documents"):
        scope_module.review_scope(snapshot)


def test_removed_assets_are_not_silently_approved_by_current_reverse_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    baseline = _snapshot(
        tmp_path / "baseline", "a" * 40,
        [_document("a", dependencies=("retired",)), _document("retired")],
    )
    candidate = _snapshot(
        tmp_path / "candidate", "b" * 40,
        [_document("a", dependencies=("retired",))],
    )
    monkeypatch.setattr(scope_module, "_changed_paths", lambda *_: [])

    result = scope_module.review_scope(candidate, baseline)

    assert result["removed_asset_ids"] == ["retired"]
    assert result["removed_assets_require_manual_review"] is True
    assert result["review_asset_ids"] == ["a"]


def test_snapshot_commit_must_be_a_full_hex_revision(tmp_path: Path):
    snapshot = _snapshot(tmp_path / "candidate", "--help", [_document("a")])

    with pytest.raises(ValueError, match="invalid Git commit"):
        scope_module.review_scope(snapshot)


# ---------------------------------------------------------------------------
# Pure public-export attribution for __init__.py changes
# ---------------------------------------------------------------------------

BASELINE = "a" * 40
CANDIDATE = "b" * 40
MAXWELLIAN_CALLABLE = (
    "scirel.collisions.maxwellian_relative_speed_rate_average"
    ".average_cross_section_over_maxwellian"
)
MAXWELLIAN_ASSET = "scirel.collisions.maxwellian-relative-speed-rate-average"


def _maxwellian_document():
    document = _document(MAXWELLIAN_ASSET)
    document["public_api"] = {
        "python": {
            "module": "scirel.collisions.maxwellian_relative_speed_rate_average",
            "symbol": "average_cross_section_over_maxwellian",
        }
    }
    return document


def _patch_git_show(monkeypatch, before: str, after: str) -> None:
    monkeypatch.setattr(
        scope_module,
        "_git_show",
        lambda commit, path: before if commit == BASELINE else after,
    )


def _patch_head_guard(monkeypatch) -> None:
    real_git = scope_module._git

    def fake_git(*args):
        if args[:2] == ("rev-parse", "HEAD"):
            return CANDIDATE
        if args[:1] == ("status",):
            return ""
        return real_git(*args)

    monkeypatch.setattr(scope_module, "_git", fake_git)


def test_pure_package_export_addition_is_attributed_to_the_added_asset(monkeypatch):
    before = (
        "from .momentum_scales import normalized_momentum\n"
        "\n"
        "__all__ = ['normalized_momentum']\n"
    )
    after = (
        "from .momentum_scales import normalized_momentum\n"
        "from .maxwellian_relative_speed_rate_average import "
        "average_cross_section_over_maxwellian\n"
        "\n"
        "__all__ = ['normalized_momentum', 'average_cross_section_over_maxwellian']\n"
    )
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed == {MAXWELLIAN_ASSET}


def test_pure_package_export_removal_is_attributed_to_the_removed_asset(monkeypatch):
    before = (
        "from .momentum_scales import normalized_momentum\n"
        "from .maxwellian_relative_speed_rate_average import "
        "average_cross_section_over_maxwellian\n"
        "\n"
        "__all__ = ['normalized_momentum', 'average_cross_section_over_maxwellian']\n"
    )
    after = (
        "from .momentum_scales import normalized_momentum\n"
        "\n"
        "__all__ = ['normalized_momentum']\n"
    )
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed == {MAXWELLIAN_ASSET}


def test_all_membership_change_without_import_change_is_attributed(monkeypatch):
    before = (
        "from .maxwellian_relative_speed_rate_average import "
        "average_cross_section_over_maxwellian\n"
        "\n"
        "__all__ = []\n"
    )
    after = (
        "from .maxwellian_relative_speed_rate_average import "
        "average_cross_section_over_maxwellian\n"
        "\n"
        "__all__ = ['average_cross_section_over_maxwellian']\n"
    )
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed == {MAXWELLIAN_ASSET}


def test_non_export_init_change_stays_unattributable(monkeypatch):
    before = "from .momentum_scales import normalized_momentum\n"
    after = (
        "from .momentum_scales import normalized_momentum\n"
        "\n"
        "def _helper():\n"
        "    return 1\n"
    )
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed is None


def test_unmapped_export_name_stays_unattributable(monkeypatch):
    before = "from .momentum_scales import normalized_momentum\n"
    after = (
        "from .momentum_scales import normalized_momentum\n"
        "from .ghost import phantom\n"
        "\n"
        "__all__ = ['normalized_momentum', 'phantom']\n"
    )
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed is None


def test_non_scirel_import_change_stays_unattributable(monkeypatch):
    before = "from .momentum_scales import normalized_momentum\n"
    after = "from .momentum_scales import normalized_momentum\nfrom os import sep\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed is None


def test_star_import_stays_unattributable(monkeypatch):
    before = "from .momentum_scales import normalized_momentum\n"
    after = "from .momentum_scales import normalized_momentum\nfrom .ghost import *\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {MAXWELLIAN_CALLABLE: MAXWELLIAN_ASSET},
    )

    assert attributed is None


def test_alias_rebinding_between_scirel_imports_stays_unattributable(monkeypatch):
    before = "from .a import old as x\n"
    after = "from .a import new as x\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {"scirel.collisions.a.x": "scirel.collisions.some-asset"},
    )

    assert attributed is None


def test_alias_rebinding_between_non_scirel_imports_stays_unattributable(monkeypatch):
    before = "from os import path as x\n"
    after = "from os import sep as x\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {},
    )

    assert attributed is None


def test_duplicate_local_alias_stays_unattributable(monkeypatch):
    before = "from .a import old as x\n"
    after = "from .a import old as x\nfrom .a import new as x\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {
            "scirel.collisions.a.old": "asset-old",
            "scirel.collisions.a.new": "asset-new",
        },
    )

    assert attributed is None


def test_import_reordering_stays_unattributable(monkeypatch):
    before = "from .a import p\nfrom .b import q\n"
    after = "from .b import q\nfrom .a import p\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {
            "scirel.collisions.a.p": "asset-a",
            "scirel.collisions.b.q": "asset-b",
        },
    )

    assert attributed is None


def test_alias_rebinding_with_both_symbols_mapped_includes_both_assets(monkeypatch):
    before = "from .a import old as x\n"
    after = "from .a import new as x\n"
    _patch_git_show(monkeypatch, before, after)

    attributed = scope_module._attributed_export_assets(
        "src/scirel/collisions/__init__.py",
        BASELINE,
        CANDIDATE,
        {
            "scirel.collisions.a.old": "asset-old",
            "scirel.collisions.a.new": "asset-new",
        },
    )

    assert attributed == {"asset-old", "asset-new"}


def test_pure_init_export_change_scopes_review_to_the_added_asset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    baseline = _snapshot(tmp_path / "baseline", BASELINE, [_document("b")])
    candidate = _snapshot(
        tmp_path / "candidate", CANDIDATE, [_document("b"), _maxwellian_document()]
    )
    monkeypatch.setattr(
        scope_module, "_changed_paths", lambda *_: ["src/scirel/collisions/__init__.py"]
    )
    _patch_head_guard(monkeypatch)
    before = "from .momentum_scales import normalized_momentum\n"
    after = (
        "from .momentum_scales import normalized_momentum\n"
        "from .maxwellian_relative_speed_rate_average import "
        "average_cross_section_over_maxwellian\n"
    )
    _patch_git_show(monkeypatch, before, after)

    result = scope_module.review_scope(candidate, baseline)

    assert result["unresolved_source_paths"] == []
    assert result["review_asset_ids"] == [MAXWELLIAN_ASSET]


def test_non_export_init_change_still_expands_to_full_suite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    baseline = _snapshot(tmp_path / "baseline", BASELINE, [_document("b")])
    candidate = _snapshot(
        tmp_path / "candidate", CANDIDATE, [_document("b"), _maxwellian_document()]
    )
    monkeypatch.setattr(
        scope_module, "_changed_paths", lambda *_: ["src/scirel/collisions/__init__.py"]
    )
    _patch_head_guard(monkeypatch)
    before = "from .momentum_scales import normalized_momentum\n"
    after = (
        "from .momentum_scales import normalized_momentum\n"
        "\n"
        "def _helper():\n"
        "    return 1\n"
    )
    _patch_git_show(monkeypatch, before, after)

    result = scope_module.review_scope(candidate, baseline)

    assert result["unresolved_source_paths"] == ["src/scirel/collisions/__init__.py"]
    assert set(result["review_asset_ids"]) == {"b", MAXWELLIAN_ASSET}
